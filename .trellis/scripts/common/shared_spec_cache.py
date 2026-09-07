#!/usr/bin/env python3
"""Immutable, session-pinned cache for centrally published shared specs.

The feature is opt-in through ``.trellis/config.yaml``.  Cache objects and
pin records live outside the consumer repository so a shared-rule release does
not dirty consumer Git state.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tarfile
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlsplit

from .config import _load_config


LOGICAL_SHARED_PREFIX = ".trellis/spec/shared"
MANIFEST_FILE = ".trellis-shared-spec-manifest.json"
FETCH_TIMEOUT_SECONDS = 8
ARCHIVE_TIMEOUT_SECONDS = 2
LOCK_WAIT_SECONDS = 1
LOCK_STALE_SECONDS = 30
SHA_RE = re.compile(r"^[0-9a-f]{40,64}$")


@dataclass(frozen=True)
class SharedSpecConfig:
    registry: str
    ref: str
    path: str
    registry_key: str


@dataclass(frozen=True)
class SharedSpecContext:
    configured: bool
    available: bool
    status: str
    sha: str | None = None
    index_path: str | None = None
    owners: dict[str, str] | None = None
    warning: str | None = None
    write_blocked: bool = False
    source: str | None = None
    routes: list[dict[str, str]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _hash(value: str, length: int = 32) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def _safe_relative_path(value: str) -> str | None:
    normalized = value.replace("\\", "/").strip().strip("/")
    if not normalized:
        return None
    path = PurePosixPath(normalized)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        return None
    return path.as_posix()


def _contains_embedded_credentials(value: str) -> bool:
    if "://" not in value:
        return False
    try:
        parsed = urlsplit(value)
    except ValueError:
        return True
    return parsed.username is not None or parsed.password is not None


def load_shared_spec_config(repo_root: Path) -> tuple[SharedSpecConfig | None, str | None]:
    """Read and validate the optional shared-spec registry configuration."""
    section = _load_config(repo_root).get("shared_specs")
    if section is None:
        return None, None
    if not isinstance(section, dict):
        return None, "shared_specs must be a mapping"

    registry = section.get("registry")
    ref = section.get("ref", "main")
    source_path = section.get("path", "spec/shared")
    if (
        not isinstance(registry, str)
        or not registry.strip()
        or not isinstance(ref, str)
        or not ref.strip()
        or not isinstance(source_path, str)
        or not source_path.strip()
    ):
        return None, "shared_specs.registry, ref, and path must be non-empty strings"

    registry = registry.strip()
    ref = ref.strip()
    source_path = _safe_relative_path(source_path)
    if source_path is None:
        return None, "shared_specs.path must be a repository-relative path"
    if ref.startswith("-") or any(ch.isspace() or ord(ch) < 32 for ch in ref):
        return None, "shared_specs.ref is not a safe Git ref"
    if _contains_embedded_credentials(registry):
        return None, "shared_specs.registry must not contain embedded credentials"

    key_material = json.dumps(
        {"registry": registry, "ref": ref, "path": source_path},
        sort_keys=True,
        separators=(",", ":"),
    )
    return SharedSpecConfig(registry, ref, source_path, _hash(key_material)), None


def get_shared_spec_cache_root() -> Path:
    override = os.environ.get("TRELLIS_SHARED_SPEC_CACHE_ROOT", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA", "").strip()
        if base:
            return (Path(base) / "Trellis" / "shared-specs").resolve()
    xdg = os.environ.get("XDG_CACHE_HOME", "").strip()
    if xdg:
        return (Path(xdg) / "trellis" / "shared-specs").resolve()
    if sys_platform() == "darwin":
        return (Path.home() / "Library" / "Caches" / "Trellis" / "shared-specs").resolve()
    return (Path.home() / ".cache" / "trellis" / "shared-specs").resolve()


def sys_platform() -> str:
    # Kept as a tiny seam for platform-path tests without mutating sys.platform.
    import sys

    return sys.platform


def _registry_dir(config: SharedSpecConfig) -> Path:
    return get_shared_spec_cache_root() / "registries" / config.registry_key


def _repo_key(repo_root: Path) -> str:
    """Return one local identity for a checkout and all of its worktrees."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=repo_root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError("Git common-dir identity probe failed") from exc
    common_dir = result.stdout.strip() if result.returncode == 0 else ""
    if not common_dir:
        raise RuntimeError("Git common-dir identity probe returned no path")
    identity = Path(common_dir).resolve()
    return _hash(os.path.normcase(str(identity)))


def _snapshot_dir(config: SharedSpecConfig, sha: str) -> Path:
    return _registry_dir(config) / "snapshots" / sha


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    temp.write_text(json.dumps(data, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temp, path)


def _write_json_once(path: Path, data: dict[str, Any]) -> dict[str, Any]:
    """Atomically create a pin and return the winning record."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with _SourceLock(path.with_name(f"{path.name}.lock")) as acquired:
        if not acquired:
            return _read_json(path) or {}
        existing = _read_json(path)
        if existing is not None or path.exists():
            return existing or {}
        _atomic_write_json(path, data)
        return data


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _build_manifest(
    snapshot: Path,
    config: SharedSpecConfig,
    sha: str,
    source_tree: str,
) -> dict[str, Any]:
    source_root = snapshot.joinpath(*PurePosixPath(config.path).parts)
    if not (source_root / "index.md").is_file():
        raise ValueError("shared spec snapshot has no index.md")

    files: dict[str, str] = {}
    for path in sorted(source_root.rglob("*")):
        if path.is_symlink():
            raise ValueError("shared spec snapshot contains a symlink")
        if not path.is_file():
            continue
        relative = path.relative_to(snapshot).as_posix()
        path.resolve().relative_to(snapshot.resolve())
        if path.suffix.lower() == ".md":
            path.read_text(encoding="utf-8")
        files[relative] = _file_hash(path)
    if not files:
        raise ValueError("shared spec snapshot is empty")
    return {
        "schema": 2,
        "sha": sha,
        "source_path": config.path,
        "source_tree": source_tree,
        "files": files,
    }


def _validate_snapshot(config: SharedSpecConfig, sha: str) -> tuple[Path | None, str | None]:
    if not SHA_RE.fullmatch(sha):
        return None, "invalid pinned shared-spec SHA"
    snapshot = _snapshot_dir(config, sha)
    manifest = _read_json(snapshot / MANIFEST_FILE)
    if not manifest:
        return None, "shared-spec snapshot manifest is missing or unreadable"
    schema = manifest.get("schema")
    if schema not in (1, 2) or manifest.get("sha") != sha or manifest.get("source_path") != config.path:
        return None, "shared-spec snapshot manifest does not match the configured source"
    expected = manifest.get("files")
    if not isinstance(expected, dict) or not expected:
        return None, "shared-spec snapshot manifest has no files"
    # Schema 1 snapshots remain usable only when the local Git object cache can
    # independently reproduce their complete archived file set and bytes.
    source_tree, source_files, source_error = _git_source_manifest(config, sha)
    if source_error:
        return None, source_error
    if schema == 2 and manifest.get("source_tree") != source_tree:
        return None, "shared-spec snapshot manifest does not match the recorded Git tree"
    if expected != source_files:
        return None, "shared-spec snapshot manifest does not match the recorded Git source"
    try:
        actual_paths = {
            path.relative_to(snapshot).as_posix()
            for path in snapshot.rglob("*")
            if path.is_file() and path.name != MANIFEST_FILE
        }
        if actual_paths != set(expected):
            return None, "shared-spec snapshot file set failed validation"
        for relative, digest in expected.items():
            if not isinstance(relative, str) or not isinstance(digest, str):
                return None, "shared-spec snapshot manifest contains an invalid entry"
            candidate = snapshot.joinpath(*PurePosixPath(relative).parts)
            candidate.resolve().relative_to(snapshot.resolve())
            if candidate.is_symlink() or not candidate.is_file() or _file_hash(candidate) != digest:
                return None, "shared-spec snapshot bytes failed validation"
            if candidate.suffix.lower() == ".md":
                candidate.read_text(encoding="utf-8")
        source_root = snapshot.joinpath(*PurePosixPath(config.path).parts)
        if not (source_root / "index.md").is_file():
            return None, "shared-spec snapshot index.md is missing"
    except (OSError, UnicodeError, RuntimeError, ValueError):
        return None, "shared-spec snapshot could not be validated"
    return snapshot, None


class _SourceLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.token = uuid.uuid4().hex
        self.acquired = False

    def __enter__(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + LOCK_WAIT_SECONDS
        while time.monotonic() < deadline:
            try:
                fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                try:
                    stale = time.time() - self.path.stat().st_mtime > LOCK_STALE_SECONDS
                except OSError:
                    stale = False
                if stale:
                    try:
                        self.path.unlink()
                    except OSError:
                        pass
                time.sleep(0.05)
                continue
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(self.token)
            self.acquired = True
            return True
        return False

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        if not self.acquired:
            return
        try:
            if self.path.read_text(encoding="utf-8") == self.token:
                self.path.unlink()
        except OSError:
            pass


def _git_env() -> dict[str, str]:
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GCM_INTERACTIVE"] = "Never"
    return env


def _run_git(args: list[str], cwd: Path | None, timeout: int, *, binary: bool = False) -> subprocess.CompletedProcess[Any]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=_git_env(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=not binary,
        encoding=None if binary else "utf-8",
        errors=None if binary else "replace",
        timeout=timeout,
        check=False,
    )


def _source_tree_id(config: SharedSpecConfig, sha: str) -> tuple[str | None, str | None]:
    git_dir = _registry_dir(config) / "objects.git"
    if not (git_dir / "HEAD").is_file():
        return None, "shared-spec Git object cache is missing"
    try:
        commit_type = _run_git(["cat-file", "-t", sha], git_dir, ARCHIVE_TIMEOUT_SECONDS)
        if commit_type.returncode != 0 or commit_type.stdout.strip() != "commit":
            return None, "recorded shared-spec revision is not a Git commit"
        resolved = _run_git(
            ["rev-parse", f"{sha}:{config.path}"],
            git_dir,
            ARCHIVE_TIMEOUT_SECONDS,
        )
        tree = resolved.stdout.strip().lower() if resolved.returncode == 0 else ""
        if not SHA_RE.fullmatch(tree):
            return None, "recorded shared-spec commit or path is unavailable in the Git object cache"
        object_type = _run_git(["cat-file", "-t", tree], git_dir, ARCHIVE_TIMEOUT_SECONDS)
    except (OSError, subprocess.TimeoutExpired):
        return None, "recorded shared-spec Git tree validation failed"
    if object_type.returncode != 0 or object_type.stdout.strip() != "tree":
        return None, "recorded shared-spec source is not a Git tree"
    return tree, None


def _git_source_manifest(
    config: SharedSpecConfig,
    sha: str,
) -> tuple[str | None, dict[str, str] | None, str | None]:
    """Return the Git tree and digests using snapshot materialization semantics."""
    source_tree, tree_error = _source_tree_id(config, sha)
    if source_tree is None:
        return None, None, tree_error

    git_dir = _registry_dir(config) / "objects.git"
    try:
        archived = _run_git(
            ["-c", "core.autocrlf=false", "archive", "--format=tar", sha, "--", config.path],
            git_dir,
            ARCHIVE_TIMEOUT_SECONDS,
            binary=True,
        )
        if archived.returncode != 0 or not archived.stdout:
            return None, None, "recorded shared-spec Git source could not be archived"
        files: dict[str, str] = {}
        with tarfile.open(fileobj=io.BytesIO(archived.stdout), mode="r:") as archive:
            for member in archive.getmembers():
                member_path = PurePosixPath(member.name)
                if (
                    member.issym()
                    or member.islnk()
                    or not (member.isdir() or member.isreg())
                    or member_path.is_absolute()
                    or ".." in member_path.parts
                ):
                    return None, None, "recorded shared-spec Git archive contains an unsafe member"
                if not member.isreg():
                    continue
                stream = archive.extractfile(member)
                if stream is None:
                    return None, None, "recorded shared-spec Git archive could not be read"
                files[member_path.as_posix()] = hashlib.sha256(stream.read()).hexdigest()
    except (OSError, subprocess.TimeoutExpired, tarfile.TarError):
        return None, None, "recorded shared-spec Git source validation failed"
    if not files:
        return None, None, "recorded shared-spec Git source is empty"
    return source_tree, files, None


def _fetch_snapshot(config: SharedSpecConfig) -> tuple[str | None, str | None]:
    registry_dir = _registry_dir(config)
    with _SourceLock(registry_dir / "update.lock") as acquired:
        if not acquired:
            return None, "shared-spec registry update is busy"

        git_dir = registry_dir / "objects.git"
        if not (git_dir / "HEAD").is_file():
            registry_dir.mkdir(parents=True, exist_ok=True)
            init = _run_git(["init", "--bare", str(git_dir)], None, ARCHIVE_TIMEOUT_SECONDS)
            if init.returncode != 0:
                return None, "could not initialize the shared-spec object cache"

        try:
            fetched = _run_git(
                ["fetch", "--no-tags", "--depth=1", config.registry, config.ref],
                git_dir,
                FETCH_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            return None, "shared-spec registry update timed out"
        if fetched.returncode != 0:
            return None, "shared-spec registry update failed"

        resolved = _run_git(["rev-parse", "FETCH_HEAD^{commit}"], git_dir, ARCHIVE_TIMEOUT_SECONDS)
        sha = resolved.stdout.strip().lower() if resolved.returncode == 0 else ""
        if not SHA_RE.fullmatch(sha):
            return None, "shared-spec registry returned an invalid commit"

        source_tree, tree_error = _source_tree_id(config, sha)
        if source_tree is None:
            return None, tree_error or "shared-spec registry returned an invalid source tree"

        existing, existing_error = _validate_snapshot(config, sha)
        if existing is None and existing_error and _snapshot_dir(config, sha).exists():
            return None, "the fetched shared-spec SHA already has an invalid immutable snapshot"

        if existing is None:
            try:
                archived = _run_git(
                    ["-c", "core.autocrlf=false", "archive", "--format=tar", sha, "--", config.path],
                    git_dir,
                    ARCHIVE_TIMEOUT_SECONDS,
                    binary=True,
                )
            except subprocess.TimeoutExpired:
                return None, "shared-spec snapshot extraction timed out"
            if archived.returncode != 0 or not archived.stdout:
                return None, "shared-spec snapshot path was not published at the selected commit"

            snapshots_dir = registry_dir / "snapshots"
            snapshots_dir.mkdir(parents=True, exist_ok=True)
            temp: Path | None = snapshots_dir / f".tmp-{uuid.uuid4().hex}"
            temp.mkdir()
            try:
                with tarfile.open(fileobj=io.BytesIO(archived.stdout), mode="r:") as archive:
                    members = archive.getmembers()
                    for member in members:
                        member_path = PurePosixPath(member.name)
                        if (
                            member.issym()
                            or member.islnk()
                            or not (member.isdir() or member.isreg())
                            or member_path.is_absolute()
                            or ".." in member_path.parts
                        ):
                            raise ValueError("unsafe shared-spec archive member")
                    archive.extractall(temp, members=members)
                manifest = _build_manifest(temp, config, sha, source_tree)
                (temp / MANIFEST_FILE).write_text(
                    json.dumps(manifest, sort_keys=True, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                destination = _snapshot_dir(config, sha)
                if destination.exists():
                    checked, _ = _validate_snapshot(config, sha)
                    if checked is None:
                        return None, "concurrent shared-spec snapshot validation failed"
                else:
                    temp.rename(destination)
                    temp = None
            except (OSError, tarfile.TarError, UnicodeError, ValueError):
                return None, "shared-spec snapshot validation failed"
            finally:
                if temp is not None and temp.exists():
                    shutil.rmtree(temp, ignore_errors=True)

        snapshot, validation_error = _validate_snapshot(config, sha)
        if snapshot is None:
            return None, validation_error or "shared-spec snapshot validation failed"
        _atomic_write_json(registry_dir / "latest.json", {"sha": sha})
        return sha, None


def _latest_snapshot(config: SharedSpecConfig) -> tuple[str | None, str | None]:
    registry_dir = _registry_dir(config)
    latest = _read_json(registry_dir / "latest.json")
    if latest is not None and isinstance(latest.get("sha"), str):
        sha = latest["sha"].lower()
        snapshot, error = _validate_snapshot(config, sha)
        if snapshot is not None:
            return sha, None
        return None, error or "latest shared-spec snapshot is invalid"

    snapshots_dir = registry_dir / "snapshots"
    if snapshots_dir.is_dir():
        candidates = sorted(
            (path for path in snapshots_dir.iterdir() if path.is_dir() and SHA_RE.fullmatch(path.name)),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for candidate in candidates:
            snapshot, _ = _validate_snapshot(config, candidate.name)
            if snapshot is not None:
                _atomic_write_json(registry_dir / "latest.json", {"sha": candidate.name})
                return candidate.name, None
    return None, "no verified shared-spec snapshot is available"


def _resolve_context_key(
    repo_root: Path,
    context_key: str | None,
    platform_input: dict[str, Any] | None,
    platform: str | None,
) -> str:
    if context_key:
        return context_key
    try:
        from .active_task import resolve_context_key

        resolved = resolve_context_key(platform_input, platform)
    except Exception:
        resolved = None
    return resolved or f"process-{os.getppid()}"


def _active_task_dir(
    repo_root: Path,
    task_dir: str | Path | None,
    platform_input: dict[str, Any] | None,
    platform: str | None,
) -> Path | None:
    if task_dir:
        candidate = Path(task_dir)
        if not candidate.is_absolute():
            candidate = repo_root / candidate
        return candidate.resolve() if candidate.is_dir() else None
    try:
        from .active_task import resolve_active_task, resolve_task_ref

        active = resolve_active_task(repo_root, platform_input, platform)
        return resolve_task_ref(active.task_path, repo_root) if active.task_path else None
    except Exception:
        return None


def _task_family_key(repo_root: Path, task_dir: Path | None) -> str | None:
    if task_dir is None:
        return None
    current = task_dir
    seen: set[Path] = set()
    try:
        from .task_utils import resolve_task_dir
    except Exception:
        return _hash(current.as_posix())

    for _ in range(32):
        resolved = current.resolve()
        if resolved in seen:
            return None
        seen.add(resolved)
        data = _read_json(current / "task.json") or {}
        parent = data.get("parent")
        if not isinstance(parent, str) or not parent.strip():
            try:
                relative = current.resolve().relative_to(repo_root.resolve()).as_posix()
            except ValueError:
                return None
            return _hash(relative)
        next_dir = resolve_task_dir(parent, repo_root)
        if next_dir is None or not next_dir.is_dir():
            return None
        current = next_dir
    return None


def _pin_paths(config: SharedSpecConfig, repo_key: str, context_key: str, family_key: str | None) -> tuple[Path, Path | None]:
    base = _registry_dir(config) / "pins" / repo_key
    session = base / "sessions" / f"{_hash(context_key)}.json"
    family = base / "tasks" / f"{family_key}.json" if family_key else None
    return session, family


def _pin_sha(record: dict[str, Any] | None, config: SharedSpecConfig) -> str | None:
    if not record or record.get("registry_key") != config.registry_key:
        return None
    sha = record.get("sha")
    return sha.lower() if isinstance(sha, str) and SHA_RE.fullmatch(sha.lower()) else None


def _routing_rows(source_root: Path) -> list[dict[str, str]]:
    """Extract the published Markdown routing table without duplicating it."""
    try:
        lines = (source_root / "index.md").read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return []
    routes: list[dict[str, str]] = []
    row_re = re.compile(
        r"^\|\s*\[([^\]]+)\]\(([^)]+\.md)\)\s*\|\s*(.*?)\s*\|\s*$"
    )
    for line in lines:
        match = row_re.match(line.strip())
        if not match:
            continue
        label, relative, when = match.groups()
        safe_relative = _safe_relative_path(relative)
        if safe_relative is None:
            continue
        path = source_root.joinpath(*PurePosixPath(safe_relative).parts).resolve()
        try:
            path.relative_to(source_root.resolve())
        except ValueError:
            continue
        if path.is_file():
            routes.append({"owner": label, "when": when, "path": str(path)})
    return routes


def _owners(
    config: SharedSpecConfig, sha: str
) -> tuple[str, dict[str, str], list[dict[str, str]]]:
    snapshot = _snapshot_dir(config, sha)
    source_root = snapshot.joinpath(*PurePosixPath(config.path).parts)
    owners: dict[str, str] = {}
    for path in sorted(source_root.rglob("*.md")):
        relative = path.relative_to(source_root).as_posix()
        owners[f"{LOGICAL_SHARED_PREFIX}/{relative}"] = str(path.resolve())
    return (
        str((source_root / "index.md").resolve()),
        owners,
        _routing_rows(source_root),
    )


def _blocked(message: str) -> SharedSpecContext:
    return SharedSpecContext(
        configured=True,
        available=False,
        status="blocked",
        warning=message,
        write_blocked=True,
    )


def ensure_shared_spec_context(
    repo_root: Path,
    *,
    context_key: str | None = None,
    task_dir: str | Path | None = None,
    platform_input: dict[str, Any] | None = None,
    platform: str | None = None,
    allow_remote: bool = True,
) -> SharedSpecContext:
    """Select and pin one immutable snapshot for the session/task family."""
    repo_root = repo_root.resolve()
    config, config_error = load_shared_spec_config(repo_root)
    if config_error:
        return _blocked(f"Shared specs are configured but invalid: {config_error}. Read-only diagnostics may continue; writes that depend on shared rules are blocked.")
    if config is None:
        return SharedSpecContext(False, False, "disabled")

    key = _resolve_context_key(repo_root, context_key, platform_input, platform)
    active_dir = _active_task_dir(repo_root, task_dir, platform_input, platform)
    family_key = _task_family_key(repo_root, active_dir)
    try:
        repo_key = _repo_key(repo_root)
    except RuntimeError:
        return _blocked(
            "The stable Git common-dir identity could not be determined; existing session/task pins will not be replaced. "
            "Read-only diagnostics may continue; writes that depend on shared rules are blocked."
        )
    session_pin, family_pin = _pin_paths(config, repo_key, key, family_key)
    attempt_path = _registry_dir(config) / "attempts" / repo_key / f"{_hash(key)}.json"
    attempted = attempt_path.exists()
    session_sha = _pin_sha(_read_json(session_pin), config)
    family_sha = _pin_sha(_read_json(family_pin), config) if family_pin else None

    if session_pin.exists() and session_sha is None:
        return _blocked("The current session shared-spec pin is unreadable or invalid; it will not be replaced automatically.")
    if family_pin and family_pin.exists() and family_sha is None:
        return _blocked("The current task-family shared-spec pin is unreadable or invalid; it will not be replaced automatically.")
    if session_sha and family_sha and session_sha != family_sha:
        return _blocked("The session and task-family shared-spec pins conflict; neither pin will be overwritten.")

    pinned_sha = session_sha or family_sha
    if pinned_sha:
        snapshot, error = _validate_snapshot(config, pinned_sha)
        if snapshot is None:
            return _blocked(f"Pinned shared-spec snapshot {pinned_sha} is unavailable or corrupt: {error}. It will not fall back to another SHA.")
        record = {"registry_key": config.registry_key, "sha": pinned_sha}
        if family_pin is not None and not family_sha:
            family_winner = _write_json_once(family_pin, record)
            if _pin_sha(family_winner, config) != pinned_sha:
                return _blocked("A concurrent task-family pin conflicts with the current session pin.")
        if not session_sha:
            winner = _write_json_once(session_pin, record)
            if _pin_sha(winner, config) != pinned_sha:
                return _blocked("A concurrent session pin conflicts with the inherited task-family pin.")

        remote_error = None
        if allow_remote and not attempted and family_sha is None:
            _, remote_error = _fetch_snapshot(config)
            _atomic_write_json(attempt_path, {"attempted": True})
        index_path, owners, routes = _owners(config, pinned_sha)
        return SharedSpecContext(
            True,
            True,
            "pinned",
            pinned_sha,
            index_path,
            owners,
            warning=(
                "Remote shared-spec update was unavailable; the existing pinned snapshot remains active."
                if remote_error
                else None
            ),
            source="session" if session_sha else "task-family",
            routes=routes,
        )

    selected_sha: str | None = None
    remote_error: str | None = None
    source = "verified-cache"
    if allow_remote and not attempted:
        selected_sha, remote_error = _fetch_snapshot(config)
        _atomic_write_json(attempt_path, {"attempted": True})
        if selected_sha:
            source = "remote"

    if selected_sha is None:
        selected_sha, cache_error = _latest_snapshot(config)
        if selected_sha is None:
            reason = remote_error or cache_error
            if attempted and not allow_remote:
                reason = cache_error
            return _blocked(f"Shared-spec cache is unavailable: {reason}. Read-only diagnostics may continue; writes that depend on shared rules are blocked.")

    record = {"registry_key": config.registry_key, "sha": selected_sha}
    if family_pin is not None:
        family_winner = _write_json_once(family_pin, record)
        winner_sha = _pin_sha(family_winner, config)
        if winner_sha != selected_sha:
            if winner_sha:
                winner_snapshot, error = _validate_snapshot(config, winner_sha)
                if winner_snapshot is None:
                    return _blocked(f"The winning task-family pin is unavailable or corrupt: {error}.")
                selected_sha = winner_sha
                record = {"registry_key": config.registry_key, "sha": selected_sha}
                source = "task-family"
            else:
                return _blocked("A concurrent task-family pin write produced an invalid record.")
    session_winner = _write_json_once(session_pin, record)
    if _pin_sha(session_winner, config) != selected_sha:
        return _blocked("A concurrent session pin conflicts with the selected task-family pin.")

    snapshot, error = _validate_snapshot(config, selected_sha)
    if snapshot is None:
        return _blocked(f"Selected shared-spec snapshot failed validation: {error}.")
    index_path, owners, routes = _owners(config, selected_sha)
    warning = None
    status = "ready"
    if source == "verified-cache":
        status = "offline"
        warning = "Remote shared-spec update was unavailable or skipped; using an existing verified immutable snapshot."
    return SharedSpecContext(
        True,
        True,
        status,
        selected_sha,
        index_path,
        owners,
        warning,
        False,
        source,
        routes,
    )


def is_shared_spec_reference(reference: str) -> bool:
    normalized = reference.replace("\\", "/").rstrip("/")
    return normalized == LOGICAL_SHARED_PREFIX or normalized.startswith(f"{LOGICAL_SHARED_PREFIX}/")


def resolve_shared_spec_reference(
    reference: str,
    repo_root: Path,
    *,
    context_key: str | None = None,
    task_dir: str | Path | None = None,
    platform_input: dict[str, Any] | None = None,
    platform: str | None = None,
) -> Path | None:
    """Resolve an old logical shared path to the pinned immutable snapshot.

    A physical consumer-owned legacy path wins.  This preserves unknown local
    files while Profile removes only hash-proven Registry-owned copies.
    """
    if not isinstance(reference, str) or not reference.strip():
        return None
    candidate = Path(reference)
    local = candidate if candidate.is_absolute() else repo_root / candidate
    if local.exists():
        return local.resolve()
    if not is_shared_spec_reference(reference):
        return None

    context = ensure_shared_spec_context(
        repo_root,
        context_key=context_key,
        task_dir=task_dir,
        platform_input=platform_input,
        platform=platform,
        allow_remote=False,
    )
    if not context.available or not context.sha:
        return None
    config, _ = load_shared_spec_config(repo_root)
    if config is None:
        return None
    suffix = reference.replace("\\", "/").rstrip("/")[len(LOGICAL_SHARED_PREFIX):].lstrip("/")
    suffix_path = _safe_relative_path(suffix) if suffix else ""
    if suffix and suffix_path is None:
        return None
    source_root = _snapshot_dir(config, context.sha).joinpath(*PurePosixPath(config.path).parts)
    resolved = source_root.joinpath(*PurePosixPath(suffix_path).parts).resolve() if suffix_path else source_root.resolve()
    try:
        resolved.relative_to(source_root.resolve())
    except ValueError:
        return None
    return resolved if resolved.exists() else None


def render_shared_spec_context(context: SharedSpecContext) -> str:
    if not context.configured:
        return ""
    if not context.available:
        return (
            "<shared-spec-context status=\"blocked\">\n"
            f"{context.warning}\n"
            "Do not perform writes that depend on shared Trellis rules until `.trellis/scripts/shared_spec_cache.py ensure` succeeds.\n"
            "</shared-spec-context>"
        )
    lines = [
        f'<shared-spec-context status="{context.status}" sha="{context.sha}">',
        f"Central shared Trellis rules are pinned for this session/task family. Published index: {context.index_path}",
        "Select every directly matching owner from this published when-to-read index, then read its full body on demand:",
    ]
    for route in context.routes or []:
        lines.append(f"- {route['when']} -> {route['owner']}: {route['path']}")
    if not context.routes:
        for logical, absolute in (context.owners or {}).items():
            lines.append(f"- {logical} -> {absolute}")
    if context.warning:
        lines.append(f"Warning: {context.warning}")
    lines.append("</shared-spec-context>")
    return "\n".join(lines)
