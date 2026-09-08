#!/usr/bin/env python3
"""Manage the optional immutable shared-spec cache.

Usage:
    python .trellis/scripts/shared_spec_cache.py ensure [--offline] [--json]
    python .trellis/scripts/shared_spec_cache.py resolve <logical-ref> [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
from common.paths import get_repo_root
from common.shared_spec_cache import (
    ensure_shared_spec_context,
    render_shared_spec_context,
    resolve_shared_spec_reference,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare or resolve the shared-spec cache")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ensure_parser = subparsers.add_parser("ensure", help="load the configured shared-spec ref")
    ensure_parser.add_argument("--offline", action="store_true", help="do not contact the registry")
    ensure_parser.add_argument("--json", action="store_true", help="emit machine-readable output")

    resolve_parser = subparsers.add_parser("resolve", help="resolve a logical shared-spec reference")
    resolve_parser.add_argument("reference")
    resolve_parser.add_argument("--json", action="store_true", help="emit machine-readable output")

    args = parser.parse_args()
    repo_root = get_repo_root()

    if args.command == "ensure":
        context = ensure_shared_spec_context(
            repo_root,
            allow_remote=not args.offline,
        )
        payload = context.to_dict()
        # The explicit recovery CLI returns every readable selected body. Hook
        # callers keep the renderer's bounded default.
        payload["context"] = render_shared_spec_context(context, max_bytes=0)
        if args.json:
            print(json.dumps(payload, ensure_ascii=False))
        else:
            rendered = payload["context"] or "Shared specs are not configured."
            encoded = f"{rendered}\n".encode("utf-8")
            binary_stdout = getattr(sys.stdout, "buffer", None)
            if binary_stdout is not None:
                binary_stdout.write(encoded)
            else:
                sys.stdout.write(encoded.decode("utf-8"))
        return 0 if not context.write_blocked else 2

    resolved = resolve_shared_spec_reference(args.reference, repo_root)
    payload = {"reference": args.reference, "path": str(resolved) if resolved else None}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    elif resolved:
        print(resolved)
    return 0 if resolved else 2


if __name__ == "__main__":
    sys.exit(main())
