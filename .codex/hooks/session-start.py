#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Restore pinned shared Trellis rules after a Codex compact event."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


if sys.platform.startswith("win"):
    import io as _io

    for _stream_name in ("stdin", "stdout", "stderr"):
        _stream = getattr(sys, _stream_name, None)
        if _stream is None:
            continue
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
            except Exception:
                pass  # Optional Windows stream setup; keep hook startup non-fatal.
        elif hasattr(_stream, "detach"):
            try:
                setattr(
                    sys,
                    _stream_name,
                    _io.TextIOWrapper(
                        _stream.detach(), encoding="utf-8", errors="replace"
                    ),
                )
            except Exception:
                pass  # Optional Windows stream setup; keep hook startup non-fatal.


def _normalize_windows_shell_path(path_str: str) -> str:
    """Normalize common Git Bash, Cygwin, and WSL drive mount spellings."""
    if not isinstance(path_str, str) or not path_str or not sys.platform.startswith("win"):
        return path_str
    value = path_str.strip()
    if re.match(r"^[A-Za-z]:[\\/]", value):
        return value
    for pattern in (
        r"^/([A-Za-z])/(.*)",
        r"^/cygdrive/([A-Za-z])/(.*)",
        r"^/mnt/([A-Za-z])/(.*)",
    ):
        match = re.match(pattern, value)
        if match:
            drive, rest = match.group(1).upper(), match.group(2)
            return f"{drive}:\\{rest.replace('/', chr(92))}"
    return path_str


def should_skip_injection() -> bool:
    return (
        os.environ.get("TRELLIS_HOOKS") == "0"
        or os.environ.get("TRELLIS_DISABLE_HOOKS") == "1"
        or os.environ.get("CODEX_NON_INTERACTIVE") == "1"
    )


def _find_project_dir(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        if (candidate / ".trellis").is_dir():
            return candidate
    return None


def configure_project_encoding(project_dir: Path) -> None:
    scripts_dir = project_dir / ".trellis" / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    try:
        from common import configure_encoding  # type: ignore[import-not-found]

        configure_encoding()
    except Exception:
        pass  # Optional helper; explicit stream setup above remains active.


def _shared_specs_declared(project_dir: Path) -> bool:
    try:
        config = project_dir / ".trellis" / "config.yaml"
        return "shared_specs:" in config.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False


def _shared_spec_context(project_dir: Path, hook_input: dict) -> str:
    scripts_dir = project_dir / ".trellis" / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    try:
        from common.shared_spec_cache import (  # type: ignore[import-not-found]
            ensure_shared_spec_context,
            render_shared_spec_context,
        )

        context = ensure_shared_spec_context(
            project_dir,
            platform_input=hook_input,
            platform="codex",
            allow_remote=False,
        )
        return render_shared_spec_context(context)
    except Exception:
        if not _shared_specs_declared(project_dir):
            return ""
        return (
            '<shared-spec-context status="blocked">\n'
            "Shared specs are configured but the cache runtime could not be loaded. "
            "Run `python .trellis/scripts/shared_spec_cache.py ensure` before relying on shared rules.\n"
            "</shared-spec-context>"
        )


def main() -> None:
    if should_skip_injection():
        return
    try:
        hook_input = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        hook_input = {}
    if not isinstance(hook_input, dict):
        hook_input = {}
    cwd = hook_input.get("cwd")
    start = Path(
        _normalize_windows_shell_path(cwd if isinstance(cwd, str) else ".")
    ).resolve()
    project_dir = _find_project_dir(start)
    if project_dir is None:
        return
    configure_project_encoding(project_dir)

    context = _shared_spec_context(project_dir, hook_input)
    if not context:
        return
    result = {
        "suppressOutput": True,
        "systemMessage": f"Trellis context injected ({len(context)} chars)",
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        },
    }
    print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
