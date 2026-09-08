#!/usr/bin/env python3
"""Verified immutable cache for centrally published shared specs.

The feature is opt-in through ``.trellis/config.yaml``. Cache objects live
outside the consumer repository so a shared-rule release does not dirty
consumer Git state.
"""

from __future__ import annotations

import hashlib
from html import escape as html_escape
import io
import json
import os
import re
import shutil
import stat
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
DEFAULT_AUTO_INJECT_CONTEXT_BYTES = 128 * 1024
MAX_AUTO_INJECT_FILES = 64
MAX_AUTO_INJECT_PATH_BYTES = 512
AUTO_INJECT_MARKER = "[全文已随本次上下文注入，同版本一般无需重读]"
REPARSE_POINT_ATTRIBUTE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


@dataclass(frozen=True)
class SharedSpecConfig:
    registry: str
    ref: str
    path: str
    registry_key: str
    auto_inject: tuple[str, ...] = ()


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
    auto_inject: list[dict[str, str]] | None = None

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


def _safe_auto_inject_path(value: str) -> str | None:
    """Normalize one Markdown path without accepting absolute-path spellings."""
    normalized = value.strip().replace("\\", "/")
    if (
        not normalized
        or normalized.startswith("/")
        or re.match(r"^[A-Za-z]:", normalized)
        or normalized.endswith("/")
    ):
        return None
    path = PurePosixPath(normalized)
    if any(part in ("", ".", "..") for part in path.parts):
        return None
    safe = path.as_posix()
    return safe if PurePosixPath(safe).suffix.lower() == ".md" else None


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
    auto_inject_value = section.get("auto_inject", [])
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

    if not isinstance(auto_inject_value, list):
        return None, "shared_specs.auto_inject must be a list of relative Markdown paths"
    if len(auto_inject_value) > MAX_AUTO_INJECT_FILES:
        return None, f"shared_specs.auto_inject may contain at most {MAX_AUTO_INJECT_FILES} paths"
    auto_inject: list[str] = []
    seen_auto_inject: set[str] = set()
    for value in auto_inject_value:
        if not isinstance(value, str):
            return None, "shared_specs.auto_inject must contain only relative Markdown paths"
        normalized = _safe_auto_inject_path(value)
        if normalized is None:
            return None, f"shared_specs.auto_inject contains an unsafe Markdown path: {value!r}"
        if len(normalized.encode("utf-8")) > MAX_AUTO_INJECT_PATH_BYTES:
            return None, f"shared_specs.auto_inject path exceeds {MAX_AUTO_INJECT_PATH_BYTES} UTF-8 bytes"
        if normalized in seen_auto_inject:
            return None, f"shared_specs.auto_inject contains a duplicate path: {normalized}"
        seen_auto_inject.add(normalized)
        auto_inject.append(normalized)

    key_material = json.dumps(
        {"registry": registry, "ref": ref, "path": source_path},
        sort_keys=True,
        separators=(",", ":"),
    )
    return SharedSpecConfig(
        registry,
        ref,
        source_path,
        _hash(key_material),
        tuple(auto_inject),
    ), None


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


def _snapshot_dir(config: SharedSpecConfig, sha: str) -> Path:
    return _registry_dir(config) / "snapshots" / sha


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    temp.write_text(json.dumps(data, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temp, path)


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


def _path_is_link(path: Path) -> bool:
    """Detect symlinks and Windows reparse points on Python 3.9+."""
    if path.is_symlink():
        return True
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except FileNotFoundError:
        return False
    return bool(attributes & REPARSE_POINT_ATTRIBUTE)


def _snapshot_path(snapshot: Path, relative: str) -> Path:
    """Join a safe lexical path while rejecting every linked segment."""
    safe_relative = _safe_relative_path(relative)
    if safe_relative != relative:
        raise ValueError("shared-spec snapshot contains an unsafe path")
    current = snapshot
    if _path_is_link(current):
        raise ValueError("shared-spec snapshot contains a link")
    for part in PurePosixPath(relative).parts:
        current = current / part
        if _path_is_link(current):
            raise ValueError("shared-spec snapshot contains a link")
    return current


def _regular_snapshot_files(root: Path) -> list[Path]:
    """Enumerate regular files without following symlinks or reparse points."""
    if _path_is_link(root):
        raise ValueError("shared-spec snapshot contains a link")
    if not root.is_dir():
        raise ValueError("shared-spec snapshot directory is missing")

    files: list[Path] = []
    pending = [root]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            for entry in sorted(entries, key=lambda item: item.name):
                path = Path(entry.path)
                if _path_is_link(path):
                    raise ValueError("shared-spec snapshot contains a link")
                if entry.is_dir(follow_symlinks=False):
                    pending.append(path)
                elif entry.is_file(follow_symlinks=False):
                    files.append(path)
                else:
                    raise ValueError("shared-spec snapshot contains an unsupported entry")
    return sorted(files)


def _build_manifest(
    snapshot: Path,
    config: SharedSpecConfig,
    sha: str,
    source_tree: str,
) -> dict[str, Any]:
    source_root = _snapshot_path(snapshot, config.path)
    if not (source_root / "index.md").is_file():
        raise ValueError("shared spec snapshot has no index.md")

    files: dict[str, str] = {}
    for path in _regular_snapshot_files(source_root):
        relative = path.relative_to(snapshot).as_posix()
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
        return None, "invalid shared-spec SHA"
    snapshot = _snapshot_dir(config, sha)
    try:
        manifest_path = _snapshot_path(snapshot, MANIFEST_FILE)
    except ValueError as error:
        return None, str(error)
    except OSError:
        return None, "shared-spec snapshot could not be validated"
    manifest = _read_json(manifest_path)
    if not manifest:
        return None, "shared-spec snapshot manifest is missing or unreadable"
    schema = manifest.get("schema")
    if schema not in (1, 2) or manifest.get("sha") != sha or manifest.get("source_path") != config.path:
        return None, "shared-spec snapshot manifest does not match the configured source"
    expected = manifest.get("files")
    if not isinstance(expected, dict) or not expected:
        return None, "shared-spec snapshot manifest has no files"
    source_blobs: dict[str, str] | None = None
    object_format: str | None = None
    if schema == 1:
        # Legacy manifests did not record a tree identity. Reproduce their
        # source once per validation so existing verified caches stay usable.
        _, source_files, source_error = _git_source_manifest(config, sha)
        if source_error:
            return None, source_error
        if expected != source_files:
            return None, "shared-spec snapshot manifest does not match the recorded Git source"
    else:
        # Enumerating the tree is much cheaper than replaying a full archive and
        # still ties every snapshot byte to a blob in the recorded Git source.
        source_tree, source_blobs, object_format, source_error = _git_source_blobs(config, sha)
        if source_error:
            return None, source_error
        if manifest.get("source_tree") != source_tree:
            return None, "shared-spec snapshot manifest does not match the recorded Git tree"
        if set(expected) != set(source_blobs or {}):
            return None, "shared-spec snapshot file set does not match the recorded Git source"
    try:
        actual_paths = {
            path.relative_to(snapshot).as_posix()
            for path in _regular_snapshot_files(snapshot)
            if path.name != MANIFEST_FILE
        }
        if actual_paths != set(expected):
            return None, "shared-spec snapshot file set failed validation"
        for relative, digest in expected.items():
            if not isinstance(relative, str) or not isinstance(digest, str):
                return None, "shared-spec snapshot manifest contains an invalid entry"
            safe_relative = _safe_relative_path(relative)
            if safe_relative != relative:
                return None, "shared-spec snapshot manifest contains an unsafe path"
            candidate = _snapshot_path(snapshot, relative)
            if not candidate.is_file():
                return None, "shared-spec snapshot bytes failed validation"
            data = candidate.read_bytes()
            if hashlib.sha256(data).hexdigest() != digest:
                return None, "shared-spec snapshot bytes failed validation"
            if source_blobs is not None and object_format is not None:
                if _git_blob_hash(data, object_format) != source_blobs.get(relative):
                    return None, "shared-spec snapshot bytes do not match the recorded Git source"
            if candidate.suffix.lower() == ".md":
                data.decode("utf-8", errors="strict")
        source_root = _snapshot_path(snapshot, config.path)
        if not (source_root / "index.md").is_file():
            return None, "shared-spec snapshot index.md is missing"
    except ValueError as error:
        return None, str(error)
    except (OSError, UnicodeError, RuntimeError):
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


def _git_source_blobs(
    config: SharedSpecConfig,
    sha: str,
) -> tuple[str | None, dict[str, str] | None, str | None, str | None]:
    """Return the source tree and blob identities without replaying an archive."""
    source_tree, tree_error = _source_tree_id(config, sha)
    if source_tree is None:
        return None, None, None, tree_error

    git_dir = _registry_dir(config) / "objects.git"
    try:
        listed = _run_git(
            ["ls-tree", "-r", "-z", source_tree],
            git_dir,
            ARCHIVE_TIMEOUT_SECONDS,
            binary=True,
        )
        object_format_result = _run_git(
            ["rev-parse", "--show-object-format"],
            git_dir,
            ARCHIVE_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None, None, None, "recorded shared-spec Git tree validation failed"
    object_format = object_format_result.stdout.strip().lower()
    if listed.returncode != 0 or object_format_result.returncode != 0 or object_format not in ("sha1", "sha256"):
        return None, None, None, "recorded shared-spec Git tree could not be enumerated"

    blobs: dict[str, str] = {}
    try:
        for entry in listed.stdout.split(b"\0"):
            if not entry:
                continue
            metadata, raw_path = entry.split(b"\t", 1)
            mode, object_type, raw_oid = metadata.split(b" ", 2)
            if object_type != b"blob" or mode not in (b"100644", b"100755"):
                return None, None, None, "recorded shared-spec Git tree contains a non-file entry"
            relative = raw_path.decode("utf-8", errors="strict")
            safe_relative = _safe_relative_path(relative)
            oid = raw_oid.decode("ascii").lower()
            if safe_relative is None or not SHA_RE.fullmatch(oid):
                return None, None, None, "recorded shared-spec Git tree contains an unsafe entry"
            source_path = f"{config.path}/{safe_relative}"
            if source_path in blobs:
                return None, None, None, "recorded shared-spec Git tree contains a duplicate entry"
            blobs[source_path] = oid
    except (UnicodeError, ValueError):
        return None, None, None, "recorded shared-spec Git tree could not be decoded"
    if not blobs:
        return None, None, None, "recorded shared-spec Git source is empty"
    return source_tree, blobs, object_format, None


def _git_blob_hash(data: bytes, object_format: str) -> str:
    digest = hashlib.new(object_format)
    digest.update(f"blob {len(data)}\0".encode("ascii"))
    digest.update(data)
    return digest.hexdigest()


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
    latest_error: str | None = None
    latest = _read_json(registry_dir / "latest.json")
    if latest is not None and isinstance(latest.get("sha"), str):
        sha = latest["sha"].lower()
        snapshot, error = _validate_snapshot(config, sha)
        if snapshot is not None:
            return sha, None
        latest_error = error or "latest shared-spec snapshot is invalid"

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
    return None, latest_error or "no verified shared-spec snapshot is available"


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
        try:
            path = _snapshot_path(source_root, safe_relative)
        except (OSError, ValueError):
            continue
        if path.is_file():
            routes.append({"owner": label, "when": when, "path": str(path.resolve())})
    return routes


def _owners(
    config: SharedSpecConfig, sha: str
) -> tuple[str, dict[str, str], list[dict[str, str]], list[dict[str, str]]]:
    snapshot = _snapshot_dir(config, sha)
    source_root = snapshot.joinpath(*PurePosixPath(config.path).parts)
    owners: dict[str, str] = {}
    for path in sorted(source_root.rglob("*.md")):
        relative = path.relative_to(source_root).as_posix()
        owners[f"{LOGICAL_SHARED_PREFIX}/{relative}"] = str(path.resolve())
    auto_inject = [
        {
            "path": relative,
            "logical": f"{LOGICAL_SHARED_PREFIX}/{relative}",
            "absolute": str(source_root.joinpath(*PurePosixPath(relative).parts).resolve()),
        }
        for relative in config.auto_inject
    ]
    return (
        str((source_root / "index.md").resolve()),
        owners,
        _routing_rows(source_root),
        auto_inject,
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
    allow_remote: bool = True,
) -> SharedSpecContext:
    """Load the configured ref or fall back to the latest verified cache."""
    repo_root = repo_root.resolve()
    config, config_error = load_shared_spec_config(repo_root)
    if config_error:
        return _blocked(f"Shared specs are configured but invalid: {config_error}. Read-only diagnostics may continue; writes that depend on shared rules are blocked.")
    if config is None:
        return SharedSpecContext(False, False, "disabled")

    selected_sha: str | None = None
    remote_error: str | None = None
    source = "verified-cache"
    if allow_remote:
        selected_sha, remote_error = _fetch_snapshot(config)
        if selected_sha:
            source = "remote"

    if selected_sha is None:
        selected_sha, cache_error = _latest_snapshot(config)
        if selected_sha is None:
            reason = remote_error or cache_error
            return _blocked(f"Shared-spec cache is unavailable: {reason}. Read-only diagnostics may continue; writes that depend on shared rules are blocked.")

    snapshot, error = _validate_snapshot(config, selected_sha)
    if snapshot is None:
        return _blocked(f"Selected shared-spec snapshot failed validation: {error}.")
    index_path, owners, routes, auto_inject = _owners(config, selected_sha)
    warning = None
    status = "ready"
    if source == "verified-cache":
        status = "offline"
        warning = (
            "The configured shared-spec Registry ref could not be refreshed; using an existing verified cache. Freshness is unconfirmed."
            if remote_error
            else "Registry access was skipped; using an existing verified shared-spec cache. Freshness against the configured ref is unconfirmed."
        )
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
        auto_inject,
    )


def is_shared_spec_reference(reference: str) -> bool:
    normalized = reference.replace("\\", "/").rstrip("/")
    return normalized == LOGICAL_SHARED_PREFIX or normalized.startswith(f"{LOGICAL_SHARED_PREFIX}/")


def resolve_shared_spec_reference(
    reference: str,
    repo_root: Path,
) -> Path | None:
    """Resolve an old logical shared path through the latest available context.

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

    context = ensure_shared_spec_context(repo_root)
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


def _auto_inject_recovery(logical: str, *, restore_cache: bool) -> str:
    resolve = f"python .trellis/scripts/shared_spec_cache.py resolve {logical}"
    if restore_cache:
        return (
            "Run `python .trellis/scripts/shared_spec_cache.py ensure` to diagnose or restore the "
            f"verified cache, then run `{resolve}` and read the returned file."
        )
    return f"Run `{resolve}` and read the returned file."


def render_shared_spec_context(
    context: SharedSpecContext,
    *,
    max_bytes: int = DEFAULT_AUTO_INJECT_CONTEXT_BYTES,
) -> str:
    """Render one truthful shared-spec block, including only whole selected bodies.

    ``max_bytes`` limits the complete UTF-8 block. Zero disables that renderer
    budget for explicit CLI recovery; hook callers use the safe default.
    """
    if not context.configured:
        return ""
    if not context.available:
        return (
            "<shared-spec-context status=\"blocked\">\n"
            f"{context.warning}\n"
            "Do not perform writes that depend on shared Trellis rules until `.trellis/scripts/shared_spec_cache.py ensure` succeeds.\n"
            "</shared-spec-context>"
        )
    readable: list[tuple[dict[str, str], str]] = []
    read_failures: dict[str, str] = {}
    for entry in context.auto_inject or []:
        relative = entry.get("path", "(unknown)")
        logical = entry.get("logical", f"{LOGICAL_SHARED_PREFIX}/{relative}")
        absolute = entry.get("absolute", "")
        try:
            raw = Path(absolute).read_bytes()
            body = raw.decode("utf-8")
        except (OSError, UnicodeError):
            read_failures[relative] = (
                f"- {relative}: full body was not injected because the selected file could not be read. "
                + _auto_inject_recovery(logical, restore_cache=True)
            )
            continue
        readable.append((entry, body))

    included: list[tuple[dict[str, str], str]] = []
    budget_failures: dict[str, str] = {
        entry["path"]: (
            f"- {entry['path']}: full body was not injected because the {max_bytes}-byte context budget was exhausted. "
            + _auto_inject_recovery(entry["logical"], restore_cache=False)
        )
        for entry, _ in readable
    } if max_bytes > 0 else {}

    def build_output(*, include_routes: bool) -> str:
        included_paths = {
            os.path.normcase(entry["absolute"]) for entry, _ in included
        }
        lines = [
            f'<shared-spec-context status="{context.status}" sha="{context.sha}">',
            f"Central shared Trellis rules were loaded from the configured ref or verified cache. Published index: {context.index_path}",
            "Select every directly matching owner from this published when-to-read index, then read its full body on demand:",
        ]
        if include_routes:
            route_rows = context.routes or []
            for route in route_rows:
                marker = (
                    f" {AUTO_INJECT_MARKER}"
                    if os.path.normcase(route["path"]) in included_paths
                    else ""
                )
                lines.append(f"- {route['when']} -> {route['owner']}: {route['path']}{marker}")
            if not route_rows:
                for logical, absolute in (context.owners or {}).items():
                    marker = (
                        f" {AUTO_INJECT_MARKER}"
                        if os.path.normcase(absolute) in included_paths
                        else ""
                    )
                    lines.append(f"- {logical} -> {absolute}{marker}")
        else:
            lines.append("- Routing rows were omitted to keep this hook context within budget; read the published index above.")
        if context.warning:
            lines.append(f"Warning: {context.warning}")
        if included:
            lines.extend(["", "Selected shared rule bodies:"])
            for entry, body in included:
                relative = html_escape(entry["path"], quote=True)
                sha = html_escape(context.sha or "", quote=True)
                body_block = (
                    f'<shared-spec-body path="{relative}" sha="{sha}" whole="true">'
                    f"\n{body}"
                )
                if not body.endswith(("\n", "\r")):
                    body_block += "\n"
                lines.append(body_block + "</shared-spec-body>")
        failures = [
            read_failures.get(entry.get("path", ""))
            or budget_failures.get(entry.get("path", ""))
            for entry in context.auto_inject or []
        ]
        failures = [failure for failure in failures if failure]
        if failures:
            lines.extend(["", "Auto-inject recovery:", *failures])
        lines.append("</shared-spec-context>")
        return "\n".join(lines)

    if max_bytes <= 0:
        included.extend(readable)
        budget_failures.clear()
        return build_output(include_routes=True)

    include_routes = True
    output = build_output(include_routes=include_routes)
    if len(output.encode("utf-8")) > max_bytes:
        include_routes = False
        output = build_output(include_routes=include_routes)

    for entry, body in readable:
        included.append((entry, body))
        del budget_failures[entry["path"]]
        candidate = build_output(include_routes=include_routes)
        if len(candidate.encode("utf-8")) <= max_bytes:
            output = candidate
            continue
        included.pop()
        budget_failures[entry["path"]] = (
            f"- {entry['path']}: full body was not injected because the {max_bytes}-byte context budget was exhausted. "
            + _auto_inject_recovery(entry["logical"], restore_cache=False)
        )

    output = build_output(include_routes=include_routes)
    if len(output.encode("utf-8")) > max_bytes:
        # Validated auto-inject path/count bounds keep the compact recovery form
        # below the normal limit. This last guard protects synthetic callers.
        return (
            f'<shared-spec-context status="{context.status}" sha="{context.sha}">\n'
            f"Published index: {context.index_path}\n"
            "Shared rule bodies were not injected because the context budget was exhausted. "
            "Run `python .trellis/scripts/shared_spec_cache.py ensure`, then resolve and read each configured auto_inject path.\n"
            "</shared-spec-context>"
        )
    return output
