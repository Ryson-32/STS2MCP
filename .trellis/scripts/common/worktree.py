#!/usr/bin/env python3
"""Bounded Git worktree lifecycle for Trellis tasks.

The task's ``task.json`` is the registry.  Git remains the authority for
worktree registration and repository identity; this module never force-removes
a worktree or deletes a branch.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import shutil
import stat
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterator, Sequence

from .config import get_worktree_branch_prefix, get_worktree_root
from .git import main_worktree_root
from .io import read_json_checked, write_json
from .paths import get_tasks_dir


@dataclass
class WorktreeInspection:
    path: Path
    exists: bool = False
    registered: bool = False
    primary: bool = False
    same_repository: bool = False
    branch: str | None = None
    head: str | None = None
    detached: bool = False
    tracked_changes: list[str] = field(default_factory=list)
    untracked: list[str] = field(default_factory=list)
    ignored: list[str] = field(default_factory=list)
    unsafe_link: bool = False
    lock_available: bool | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def dirty(self) -> bool:
        return bool(self.tracked_changes or self.untracked)


@dataclass
class LifecycleOutcome:
    status: str
    path: Path
    reason: str
    recovery: str | None = None
    safety_checks_complete: bool = False
    manual_delete_allowed: bool = False


def _run_git(repo: Path, args: Sequence[str]) -> subprocess.CompletedProcess[str]:
    command = ["git"]
    if os.name == "nt":
        command += ["-c", "core.longpaths=true"]
    return subprocess.run(
        [*command, *args], cwd=repo, text=True, encoding="utf-8",
        errors="replace", capture_output=True, check=False,
    )


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.path.expanduser(str(path))))


def _path_key(path: Path) -> str:
    return os.path.normcase(str(_absolute(path)))


def _is_reparse_or_link(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    if stat.S_ISLNK(info.st_mode):
        return True
    attrs = getattr(info, "st_file_attributes", 0)
    return bool(attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def _path_chain_has_link(path: Path) -> bool:
    """Check existing path components without resolving or following them."""
    current = _absolute(path)
    while current != current.parent:
        if _is_reparse_or_link(current):
            return True
        current = current.parent
    return False


def _is_within(path: Path, root: Path) -> bool:
    try:
        _absolute(path).relative_to(_absolute(root))
        return True
    except ValueError:
        return False


def _common_git_dir(repo: Path) -> Path | None:
    result = _run_git(repo, ["rev-parse", "--git-common-dir"])
    if result.returncode:
        return None
    raw = Path(result.stdout.strip())
    return _absolute(raw if raw.is_absolute() else repo / raw)


def _parse_worktree_list(repo: Path) -> list[dict[str, str | bool]]:
    result = _run_git(repo, ["worktree", "list", "--porcelain", "-z"])
    if result.returncode:
        return []
    records: list[dict[str, str | bool]] = []
    current: dict[str, str | bool] = {}
    for token in result.stdout.split("\0"):
        if not token:
            if current:
                records.append(current)
                current = {}
            continue
        key, _, value = token.partition(" ")
        current[key] = value if value else True
    if current:
        records.append(current)
    return records


def _registration(repo: Path, path: Path) -> tuple[dict[str, str | bool] | None, bool]:
    records = _parse_worktree_list(repo)
    target = _path_key(path)
    exact = next((r for r in records if _path_key(Path(str(r.get("worktree", "")))) == target), None)
    primary = bool(records and exact is records[0])
    return exact, primary


def _status_entries(path: Path) -> tuple[list[str], list[str], list[str], str | None]:
    result = _run_git(path, ["status", "--porcelain=v1", "--untracked-files=all", "--ignored=matching"])
    if result.returncode:
        return [], [], [], result.stderr.strip() or "git status failed"
    tracked: list[str] = []
    untracked: list[str] = []
    ignored: list[str] = []
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        name = line[3:].strip().strip('"')
        if line.startswith("!!"):
            ignored.append(name.rstrip("/"))
        elif line.startswith("??"):
            untracked.append(name)
        else:
            tracked.append(name)
    return tracked, untracked, ignored, None


def _lock_path(repo: Path, target: Path) -> Path:
    common = _common_git_dir(repo)
    if common is None:
        raise RuntimeError(f"not a Git repository: {repo}")
    digest = hashlib.sha256(_path_key(target).encode("utf-8")).hexdigest()[:24]
    return common / "trellis-worktree-locks" / f"{digest}.lock"


@contextlib.contextmanager
def lifecycle_lock(repo: Path, target: Path, *, exclusive: bool, blocking: bool = True) -> Iterator[None]:
    """Coordinate Trellis-managed use and lifecycle operations for one path."""
    lock_path = _lock_path(repo, target)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+b")
    try:
        if os.name == "nt":
            import msvcrt
            if handle.tell() == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            mode = msvcrt.LK_LOCK if blocking else msvcrt.LK_NBLCK
            msvcrt.locking(handle.fileno(), mode, 1)
        else:
            import fcntl
            mode = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
            if not blocking:
                mode |= fcntl.LOCK_NB
            fcntl.flock(handle.fileno(), mode)
        yield
    finally:
        try:
            if os.name == "nt":
                import msvcrt
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def _lock_is_available(repo: Path, target: Path) -> bool:
    path = _lock_path(repo, target)
    if not path.exists():
        return True
    handle = None
    try:
        handle = path.open("r+b")
        if os.name == "nt":
            import msvcrt
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return True
    except (OSError, RuntimeError):
        return False
    finally:
        if handle is not None:
            handle.close()


def inspect_worktree(repo: Path, target: Path) -> WorktreeInspection:
    repo, target = _absolute(repo), _absolute(target)
    item = WorktreeInspection(path=target, exists=target.exists())
    item.unsafe_link = _is_reparse_or_link(target)
    record, item.primary = _registration(repo, target)
    item.registered = record is not None
    if record:
        item.branch = str(record.get("branch")) if record.get("branch") else None
        item.head = str(record.get("HEAD")) if record.get("HEAD") else None
        item.detached = bool(record.get("detached"))
    if item.exists and item.registered and not item.unsafe_link:
        expected = _common_git_dir(repo)
        actual = _common_git_dir(target)
        item.same_repository = expected is not None and actual is not None and _path_key(expected) == _path_key(actual)
        if item.same_repository:
            item.tracked_changes, item.untracked, item.ignored, error = _status_entries(target)
            if error:
                item.errors.append(error)
    item.lock_available = _lock_is_available(repo, target)
    return item


def inspect_for_write(repo: Path, task_dir: Path, target: Path, expected_owner: str | None) -> dict:
    """Verify that ``target`` is the current, task-owned managed write lane."""
    repo, task_dir, target = _absolute(repo), _absolute(task_dir), _absolute(target)
    item = inspect_worktree(repo, target)
    checks: dict[str, bool] = {}
    errors: list[str] = []

    def require(name: str, condition: bool, message: str) -> None:
        checks[name] = condition
        if not condition:
            errors.append(message)

    require("current_checkout", _path_key(repo) == _path_key(target), f"current repository checkout is '{repo}', not requested lane '{target}'")
    require("exists", item.exists, f"worktree path does not exist: {target}")
    require("registered", item.registered, f"worktree is not registered with Git: {target}")
    require("non_primary", not item.primary, f"managed write lane must not be the primary checkout: {target}")
    require("safe_path", not item.unsafe_link, f"worktree path is a link or reparse point: {target}")
    require("same_repository", item.same_repository, f"worktree does not share the current repository identity: {target}")
    require("attached_head", bool(item.head) and not item.detached and bool(item.branch), f"worktree HEAD is missing or detached: {target}")
    require("branch_names_head", _named_ref_matches(repo, item.branch, item.head), f"checked-out branch does not name worktree HEAD: {item.branch or '<none>'}")
    if item.errors:
        checks["inspection_errors"] = False
        errors.extend(f"worktree inspection error: {message}" for message in item.errors)
    else:
        checks["inspection_errors"] = True

    records, _legacy, registry_error = _ownership_registry(task_dir)
    require("task_registry", registry_error is None and records is not None, registry_error or f"task registry is unreadable: {task_dir / 'task.json'}")
    matching: list[dict] = []
    if records is not None:
        target_key = _path_key(target)
        for row in records:
            row_path = row.get("path")
            if isinstance(row_path, str) and _based_path_key(row_path, repo) == target_key:
                matching.append(row)
    require("recorded_path", len(matching) == 1, f"task must record exactly one ownership entry for lane: {target}")

    record = matching[0] if len(matching) == 1 else {}
    owner = record.get("owner")
    recorded_owner = owner.strip() if isinstance(owner, str) and owner.strip() else None
    expected_owner = expected_owner.strip() if isinstance(expected_owner, str) and expected_owner.strip() else None
    require("managed", record.get("managed") is True, "task ownership entry does not mark the lane managed")
    require("expected_owner", expected_owner is not None, "expected owner is required; rerun with --owner <expected-owner>")
    require(
        "owner",
        recorded_owner is not None and expected_owner is not None and recorded_owner == expected_owner,
        "task ownership entry has no non-empty owner" if recorded_owner is None else f"task ownership entry owner {recorded_owner!r} does not match expected owner {expected_owner!r}",
    )
    require("recorded_branch", isinstance(record.get("branch"), str) and record.get("branch") == item.branch, f"task branch {record.get('branch')!r} does not match Git branch {item.branch!r}")
    common = _common_git_dir(repo)
    recorded_common = record.get("common_git_dir")
    require(
        "recorded_repository",
        common is not None and isinstance(recorded_common, str) and _based_path_key(recorded_common, repo) == _path_key(common),
        "task ownership entry does not match the Git common directory",
    )
    return {
        "ok": not errors,
        "for_write": True,
        "repo": repo,
        "task": task_dir,
        "path": target,
        "owner": recorded_owner,
        "expected_owner": expected_owner,
        "branch": item.branch,
        "head": item.head,
        "dirty": item.dirty,
        "checks": checks,
        "errors": errors,
    }


def _task_data(task_dir: Path) -> tuple[dict | None, Path]:
    path = task_dir / "task.json"
    data, _ = read_json_checked(path)
    return data if isinstance(data, dict) else None, path


def _records(data: dict) -> list[dict]:
    value = data.get("worktrees")
    return [dict(row) for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def task_worktree_paths(task_dir: Path) -> list[Path]:
    """Return unique paths recorded in list metadata plus the legacy scalar."""
    data, _ = _task_data(task_dir)
    if data is None:
        return []
    paths: list[Path] = []
    for row in _records(data):
        if isinstance(row.get("path"), str) and row["path"].strip():
            paths.append(_absolute(Path(row["path"])))
    scalar = data.get("worktree_path")
    if isinstance(scalar, str) and scalar.strip():
        paths.append(_absolute(Path(scalar)))
    unique: dict[str, Path] = {}
    for path in paths:
        unique.setdefault(_path_key(path), path)
    return list(unique.values())


def _write_record(repo: Path, task_dir: Path, record: dict) -> bool:
    from .task_store import _serialized_task_write
    @_serialized_task_write
    def update(repo_root: Path) -> str:
        data, path = _task_data(task_dir)
        if data is None:
            return "error"
        records = _records(data)
        key = _path_key(Path(record["path"]))
        records = [row for row in records if not isinstance(row.get("path"), str) or _path_key(Path(row["path"])) != key]
        records.append(record)
        data["worktrees"] = records
        return "ok" if write_json(path, data) else "error"
    return update(repo) == "ok"


def _replace_recorded_path(repo: Path, task_dir: Path, source: Path, destination: Path | None) -> bool:
    from .task_store import _serialized_task_write
    @_serialized_task_write
    def update(repo_root: Path) -> str:
        data, path = _task_data(task_dir)
        if data is None:
            return "error"
        source_key = _path_key(source)
        changed = False
        records: list[dict] = []
        for row in _records(data):
            if isinstance(row.get("path"), str) and _path_key(Path(row["path"])) == source_key:
                changed = True
                if destination is None:
                    continue
                row["path"] = str(_absolute(destination))
            records.append(row)
        if changed or "worktrees" in data:
            data["worktrees"] = records
        scalar = data.get("worktree_path")
        if isinstance(scalar, str) and _path_key(Path(scalar)) == source_key:
            data["worktree_path"] = str(_absolute(destination)) if destination else None
            changed = True
        return "ok" if (write_json(path, data) if changed else True) else "error"
    return update(repo) == "ok"


def _safe_component(value: str) -> str:
    result = "".join(c.lower() if c.isalnum() else "-" for c in value).strip("-")
    while "--" in result:
        result = result.replace("--", "-")
    return result or "task"


def canonical_worktree_path(repo: Path, task_dir: Path, branch: str) -> Path:
    main_root = main_worktree_root(repo)
    repo_name = _safe_component((main_root or repo).name)
    leaf = f"{_safe_component(task_dir.name)}--{_safe_component(branch)}"
    return _absolute(get_worktree_root(repo) / repo_name / leaf)


def default_branch(repo: Path, task_dir: Path) -> str:
    prefix = get_worktree_branch_prefix(repo).strip().strip("/")
    return f"{prefix}/{_safe_component(task_dir.name)}" if prefix else _safe_component(task_dir.name)


def _managed_record(repo: Path, task_dir: Path, target: Path) -> dict | None:
    data, _ = _task_data(task_dir)
    if data is None:
        return None
    key = _path_key(target)
    common = _common_git_dir(repo)
    if common is None:
        return None
    for row in _records(data):
        if not isinstance(row.get("path"), str) or _path_key(Path(row["path"])) != key:
            continue
        owner = row.get("owner")
        recorded_common = row.get("common_git_dir")
        if (
            row.get("managed") is True
            and isinstance(owner, str) and bool(owner.strip())
            and isinstance(recorded_common, str)
            and _path_key(Path(recorded_common)) == _path_key(common)
        ):
            return row
    return None


def _ownership_scan_error(action: str, path: Path, error: BaseException | None = None) -> RuntimeError:
    detail = f": {error}" if error else ""
    return RuntimeError(f"task ownership scan incomplete; could not {action} '{path}'{detail}")


def _ownership_task_stores(repo: Path) -> Iterator[Path]:
    """Yield each physical task store visible from this Git repository."""
    result = _run_git(repo, ["worktree", "list", "--porcelain", "-z"])
    if result.returncode:
        detail = result.stderr.strip() or "git worktree list failed"
        raise _ownership_scan_error("enumerate registered checkouts for", repo, RuntimeError(detail))
    roots: list[Path] = []
    for token in result.stdout.split("\0"):
        key, _, value = token.partition(" ")
        if key == "worktree":
            if not value:
                raise _ownership_scan_error("read a registered checkout path from", repo)
            roots.append(_absolute(Path(value)))
    if not roots:
        raise _ownership_scan_error("find a registered checkout for", repo)

    seen: set[str] = set()
    for root in roots:
        try:
            root_info = root.stat()
        except (OSError, RuntimeError) as exc:
            raise _ownership_scan_error("inspect registered checkout", root, exc) from exc
        if not stat.S_ISDIR(root_info.st_mode):
            raise _ownership_scan_error("use non-directory registered checkout", root)
        tasks = get_tasks_dir(root)
        try:
            info = tasks.stat()
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise _ownership_scan_error("inspect task store", tasks, exc) from exc
        if not stat.S_ISDIR(info.st_mode):
            raise _ownership_scan_error("use non-directory task store", tasks)
        try:
            resolved = tasks.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise _ownership_scan_error("resolve task store", tasks, exc) from exc
        key = _path_key(resolved)
        if key not in seen:
            seen.add(key)
            yield tasks


def _scan_directory(path: Path, action: str) -> list[Path]:
    try:
        return sorted(path.iterdir(), key=lambda entry: entry.name)
    except (OSError, RuntimeError) as exc:
        raise _ownership_scan_error(action, path, exc) from exc


def _scan_candidate(candidate: Path, tasks_resolved: Path, *, require_registry: bool = True) -> Path | None:
    try:
        info = candidate.lstat()
    except (OSError, RuntimeError) as exc:
        raise _ownership_scan_error("inspect task candidate", candidate, exc) from exc
    attrs = getattr(info, "st_file_attributes", 0)
    if stat.S_ISLNK(info.st_mode) or bool(attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)):
        raise _ownership_scan_error("follow linked task candidate", candidate)
    if not stat.S_ISDIR(info.st_mode):
        return None
    try:
        resolved = candidate.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise _ownership_scan_error("resolve task candidate", candidate, exc) from exc
    if resolved == tasks_resolved or tasks_resolved not in resolved.parents:
        raise _ownership_scan_error("validate task candidate containment for", candidate)
    if not require_registry:
        return candidate
    task_json = resolved / "task.json"
    try:
        task_info = task_json.stat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise _ownership_scan_error("inspect task registry", task_json, exc) from exc
    if not stat.S_ISREG(task_info.st_mode):
        raise _ownership_scan_error("use non-file task registry", task_json)
    return candidate


def _iter_task_dirs(repo: Path) -> Iterator[Path]:
    """Yield all task directories, or raise when ownership cannot be scanned completely."""
    for tasks in _ownership_task_stores(repo):
        try:
            tasks_resolved = tasks.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise _ownership_scan_error("resolve task store", tasks, exc) from exc
        candidates: list[Path] = []
        for entry in _scan_directory(tasks, "enumerate task store"):
            if entry.name != "archive":
                candidates.append(entry)
                continue
            archive = _scan_candidate(entry, tasks_resolved, require_registry=False)
            if archive is None:
                continue
            for month in _scan_directory(archive, "enumerate task archive"):
                checked_month = _scan_candidate(month, tasks_resolved, require_registry=False)
                if checked_month is None:
                    continue
                candidates.extend(_scan_directory(checked_month, "enumerate task archive month"))
        for candidate in candidates:
            checked = _scan_candidate(candidate, tasks_resolved)
            if checked is not None:
                yield checked


def _task_relative_path(task_dir: Path) -> str | None:
    """Return a task-store-relative identity using its explicit tasks/ base."""
    for tasks in task_dir.parents:
        if tasks.name != "tasks" or tasks.parent.name != ".trellis":
            continue
        try:
            relative = task_dir.resolve().relative_to(tasks.resolve())
        except (OSError, RuntimeError, ValueError):
            return None
        return relative.as_posix() if relative.parts else None
    return None


def _based_path_key(value: str, base: Path) -> str | None:
    """Normalize a stored path against an explicit base with host semantics."""
    try:
        path = Path(value)
        return _path_key(path if path.is_absolute() else base / path)
    except (OSError, RuntimeError, ValueError):
        return None


def _ownership_registry(task_dir: Path) -> tuple[list[dict] | None, str | None, str | None]:
    """Read ownership-bearing fields without treating malformed data as unowned."""
    data, path = _task_data(task_dir)
    if data is None:
        return None, None, f"task registry '{path}' is unreadable; ownership cannot be established"
    value = data.get("worktrees", [])
    if (
        not isinstance(value, list)
        or any(
            not isinstance(row, dict)
            or not isinstance(row.get("path"), str)
            or not row["path"].strip()
            for row in value
        )
    ):
        return None, None, f"task registry '{path}' has invalid worktree metadata; ownership cannot be established"
    scalar = data.get("worktree_path")
    if scalar is not None and not isinstance(scalar, str):
        return None, None, f"task registry '{path}' has invalid legacy worktree metadata; ownership cannot be established"
    legacy = scalar.strip() if isinstance(scalar, str) and scalar.strip() else None
    return [dict(row) for row in value], legacy, None


def _current_adoption_state(repo: Path, task_dir: Path, target: Path) -> tuple[bool, bool, str | None]:
    """Return managed/external state from one validated current-registry read."""
    records, legacy, error = _ownership_registry(task_dir)
    if error or records is None:
        return False, False, error
    if legacy is not None and _based_path_key(legacy, repo) is None:
        return False, False, "current task legacy worktree path could not be normalized before adoption"
    key = _path_key(target)
    common = _common_git_dir(repo)
    if common is None:
        return False, False, "repository identity could not be established before adoption"
    common_key = _path_key(common)
    record_keys = [_based_path_key(row["path"], repo) for row in records]
    if any(record_key is None for record_key in record_keys):
        return False, False, "current task worktree path could not be normalized before adoption"
    matching = [row for row, record_key in zip(records, record_keys) if record_key == key]
    managed = any(
        row.get("managed") is True
        and isinstance(row.get("owner"), str) and bool(row["owner"].strip())
        and isinstance(row.get("common_git_dir"), str)
        and _based_path_key(row["common_git_dir"], repo) == common_key
        for row in matching
    )
    return managed, bool(matching), None


def _other_task_claim(repo: Path, task_dir: Path, target: Path) -> str | None:
    """Describe a valid managed/external claim held by another task."""
    common = _common_git_dir(repo)
    if common is None:
        return "repository identity could not be established before adoption"
    current_relative = _task_relative_path(task_dir)
    if current_relative is None:
        return "current task identity could not be established before adoption"
    target_key = _path_key(target)
    common_key = _path_key(common)
    try:
        for candidate in _iter_task_dirs(repo):
            candidate_relative = _task_relative_path(candidate)
            if candidate_relative is None:
                return f"task ownership scan incomplete; identity could not be established for '{candidate}'"
            if candidate_relative == current_relative:
                continue
            records, legacy, error = _ownership_registry(candidate)
            if error or records is None:
                return error
            task_name = candidate_relative
            if legacy is not None:
                legacy_key = _based_path_key(legacy, repo)
                if legacy_key is None:
                    return f"task ownership scan incomplete; legacy path in task '{task_name}' could not be normalized"
                if legacy_key == target_key:
                    return f"another task '{task_name}' has incomplete legacy ownership metadata for this worktree"
            for row in records:
                row_path = row.get("path")
                if not isinstance(row_path, str):
                    continue
                row_key = _based_path_key(row_path, repo)
                if row_key is None:
                    return f"task ownership scan incomplete; path in task '{task_name}' could not be normalized"
                if row_key != target_key:
                    continue
                owner = row.get("owner")
                managed = row.get("managed")
                recorded_common = row.get("common_git_dir")
                if (
                    not isinstance(owner, str)
                    or not owner.strip()
                    or (managed is not True and managed is not False)
                    or not isinstance(recorded_common, str)
                    or _based_path_key(recorded_common, repo) != common_key
                ):
                    return f"another task '{task_name}' has incomplete ownership metadata for this worktree"
                kind = "managed" if managed is True else "external"
                return f"another task '{task_name}' already records this worktree as {kind} (owner: {owner.strip()})"
    except RuntimeError as exc:
        return str(exc)
    return None


def _record(repo: Path, task_dir: Path, target: Path, branch: str | None, owner: str, adopted: bool = False) -> bool:
    common = _common_git_dir(repo)
    return _write_record(repo, task_dir, {
        "path": str(_absolute(target)),
        "branch": branch,
        "owner": owner,
        "managed": True,
        "adopted": adopted,
        "common_git_dir": str(common) if common else None,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    })


def _owner(repo: Path, task_dir: Path, explicit: str | None) -> str:
    if explicit and explicit.strip():
        return explicit.strip()
    data, _ = _task_data(task_dir)
    assignee = data.get("assignee") if data else None
    if isinstance(assignee, str) and assignee.strip():
        return assignee.strip()
    from .paths import get_developer
    return get_developer(repo) or "trellis"


def create_worktree(
    repo: Path, task_dir: Path, *, branch: str | None = None,
    base: str = "HEAD", owner: str | None = None, existing_branch: bool = False,
) -> LifecycleOutcome:
    repo, task_dir = _absolute(repo), _absolute(task_dir)
    branch = branch or default_branch(repo, task_dir)
    target = canonical_worktree_path(repo, task_dir, branch)
    configured_root = _absolute(get_worktree_root(repo))
    if not _is_within(target, configured_root) or _path_chain_has_link(target) or target.exists() or _registration(repo, target)[0]:
        return LifecycleOutcome("preserved", target, "destination already exists or is registered")
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with lifecycle_lock(repo, target, exclusive=True):
            if target.exists() or _registration(repo, target)[0] or _path_chain_has_link(target):
                return LifecycleOutcome("preserved", target, "destination changed before create")
            args = ["worktree", "add"]
            if not existing_branch:
                args += ["-b", branch]
            args += [str(target), branch if existing_branch else base]
            result = _run_git(repo, args)
            if result.returncode:
                return LifecycleOutcome("error", target, result.stderr.strip() or "git worktree add failed")
            check = inspect_worktree(repo, target)
            if not (check.exists and check.registered and check.same_repository):
                return LifecycleOutcome("error", target, "post-create registration or repository identity check failed")
            if not _record(repo, task_dir, target, check.branch, _owner(repo, task_dir, owner)):
                return LifecycleOutcome("error", target, "worktree created but task metadata update failed")
            return LifecycleOutcome("created", target, "created and recorded", safety_checks_complete=True)
    except OSError as exc:
        return LifecycleOutcome("error", target, f"lifecycle lock failed: {exc}")


def move_worktree(
    repo: Path, task_dir: Path, source: Path, *, destination: Path | None,
    confirm_inactive: bool, adopt_owned: bool, owner: str | None = None,
    before_lock: Callable[[], None] | None = None,
) -> LifecycleOutcome:
    repo, task_dir, source = _absolute(repo), _absolute(task_dir), _absolute(source)
    before = inspect_worktree(repo, source)
    destination = _absolute(destination or canonical_worktree_path(repo, task_dir, before.branch or "detached"))
    if not confirm_inactive:
        return LifecycleOutcome("preserved", source, "activity is unknown; --confirm-inactive is required")
    if before.primary:
        return LifecycleOutcome("preserved", source, "primary checkout is permanent")
    if before.dirty or before.errors:
        return LifecycleOutcome("preserved", source, "worktree is dirty or could not be inspected")
    if before.unsafe_link or _path_chain_has_link(source) or not before.exists or not before.registered or not before.same_repository:
        return LifecycleOutcome("preserved", source, "source failed exact physical, registration, link, or repository checks")
    managed, external, registry_error = _current_adoption_state(repo, task_dir, source)
    if registry_error:
        return LifecycleOutcome("preserved", source, registry_error)
    if not managed:
        if external:
            return LifecycleOutcome("preserved", source, "task metadata marks the source external or lacks verified ownership")
        if not adopt_owned:
            return LifecycleOutcome("preserved", source, "source is not task-owned; --adopt-owned is required")
        claim = _other_task_claim(repo, task_dir, source)
        if claim:
            return LifecycleOutcome("preserved", source, claim)
    configured_root = _absolute(get_worktree_root(repo))
    if not _is_within(destination, configured_root) or destination.exists() or _registration(repo, destination)[0] or _path_chain_has_link(destination):
        return LifecycleOutcome("preserved", destination, "destination already exists, is registered, or is a link")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if before_lock:
        before_lock()
    lock_acquired = False
    try:
        with lifecycle_lock(repo, source, exclusive=True, blocking=False):
            lock_acquired = True
            locked = inspect_worktree(repo, source)
            if locked.dirty or locked.errors or locked.primary or locked.unsafe_link or not locked.exists or not locked.registered or not locked.same_repository:
                return LifecycleOutcome("preserved", source, "source changed before move; re-inspection refused it")
            managed, external, registry_error = _current_adoption_state(repo, task_dir, source)
            if registry_error:
                return LifecycleOutcome("preserved", source, f"source ownership changed before move: {registry_error}")
            if not managed:
                claim = _other_task_claim(repo, task_dir, source) if adopt_owned else None
                if external or not adopt_owned or claim:
                    if claim:
                        return LifecycleOutcome("preserved", source, f"source ownership changed before move: {claim}")
                    return LifecycleOutcome("preserved", source, "source ownership changed before move")
            if not _is_within(destination, configured_root) or destination.exists() or _registration(repo, destination)[0] or _path_chain_has_link(destination):
                return LifecycleOutcome("preserved", destination, "destination changed before move")
            result = _run_git(repo, ["worktree", "move", str(source), str(destination)])
            if result.returncode:
                return LifecycleOutcome("error", source, result.stderr.strip() or "git worktree move failed")
            after = inspect_worktree(repo, destination)
            if not (after.exists and after.registered and after.same_repository and not source.exists() and _registration(repo, source)[0] is None):
                return LifecycleOutcome("error", destination, "post-move physical or registration check failed")
            if not _replace_recorded_path(repo, task_dir, source, destination):
                return LifecycleOutcome("error", destination, "moved but task metadata update failed")
            if _managed_record(repo, task_dir, destination) is None and not _record(repo, task_dir, destination, after.branch, _owner(repo, task_dir, owner), adopted=True):
                return LifecycleOutcome("error", destination, "moved but adoption metadata update failed")
            return LifecycleOutcome("moved", destination, "moved and verified", safety_checks_complete=True)
    except OSError as exc:
        if not lock_acquired:
            return LifecycleOutcome("preserved", source, "lifecycle lock is held; worktree may be active")
        return LifecycleOutcome("error", source, f"move filesystem operation failed: {exc}")


def _relative_cache_paths(target: Path, declared: Sequence[str]) -> tuple[list[Path], str | None]:
    result: list[Path] = []
    for raw in declared:
        relative = Path(raw)
        if relative.is_absolute() or ".." in relative.parts or str(relative) in ("", "."):
            return [], f"invalid reproducible-cache path: {raw}"
        candidate = _absolute(target / relative)
        # Reject a linked cache root or ancestor, but allow links inside an
        # explicitly declared, Git-ignored cache. shutil.rmtree unlinks those
        # entries without following symlinks or Windows junctions (Python 3.8+).
        if not _is_within(candidate, target) or _path_chain_has_link(candidate):
            return [], f"cache path is outside the worktree or crosses a link: {raw}"
        result.append(candidate)
    return result, None


def _ignored_is_declared(ignored: str, declared: Sequence[str]) -> bool:
    item = Path(ignored).as_posix().rstrip("/")
    for raw in declared:
        root = Path(raw).as_posix().rstrip("/")
        if item == root or item.startswith(root + "/"):
            return True
    return False


def _cache_is_ignored(target: Path, cache: Path) -> bool:
    try:
        relative = cache.relative_to(target).as_posix()
    except ValueError:
        return False
    result = _run_git(target, ["check-ignore", "-q", "--", relative])
    return result.returncode == 0


def _named_ref_matches(repo: Path, ref: str | None, head: str | None) -> bool:
    if not ref or not head or not ref.startswith("refs/heads/"):
        return False
    valid = _run_git(repo, ["check-ref-format", ref])
    if valid.returncode:
        return False
    result = _run_git(repo, ["show-ref", "--verify", "--hash", ref])
    return result.returncode == 0 and result.stdout.strip() == head


def _cleanup_preflight(
    repo: Path, task_dir: Path, target: Path, *, confirm_inactive: bool,
    adopt_owned: bool, reproducible_caches: Sequence[str], recovery_ref: str | None,
) -> tuple[WorktreeInspection, list[Path], str | None]:
    item = inspect_worktree(repo, target)
    if not confirm_inactive:
        return item, [], "activity is unknown; --confirm-inactive is required"
    if item.primary:
        return item, [], "primary checkout is permanent"
    if item.unsafe_link or _path_chain_has_link(target) or not item.exists or not item.registered or not item.same_repository:
        return item, [], "target failed exact physical, registration, link, or repository checks"
    if item.errors:
        return item, [], "worktree inspection failed"
    managed, external, registry_error = _current_adoption_state(repo, task_dir, target)
    if registry_error:
        return item, [], registry_error
    if not managed:
        if external:
            return item, [], "task metadata marks the target external or lacks verified ownership"
        if not adopt_owned:
            return item, [], "target is not task-owned; --adopt-owned is required"
        claim = _other_task_claim(repo, task_dir, target)
        if claim:
            return item, [], claim
    if item.dirty:
        return item, [], "tracked or untracked changes are present"
    if item.detached and not _named_ref_matches(repo, recovery_ref, item.head):
        return item, [], "detached HEAD lacks an exact pre-created recovery ref"
    if not item.detached and not _named_ref_matches(repo, item.branch, item.head):
        return item, [], "checked-out branch is missing or no longer names the worktree HEAD"
    unknown_ignored = [name for name in item.ignored if not _ignored_is_declared(name, reproducible_caches)]
    if unknown_ignored:
        return item, [], "ignored data is present outside explicitly declared reproducible caches"
    caches, cache_error = _relative_cache_paths(target, reproducible_caches)
    if cache_error is None:
        for cache in caches:
            if cache.exists() and not _cache_is_ignored(target, cache):
                return item, [], f"declared cache is not Git-ignored: {cache.relative_to(target)}"
    return item, caches, cache_error


def cleanup_worktree(
    repo: Path, task_dir: Path, target: Path, *, confirm_inactive: bool,
    adopt_owned: bool = False, reproducible_caches: Sequence[str] = (),
    recovery_ref: str | None = None,
    before_lock: Callable[[], None] | None = None,
) -> LifecycleOutcome:
    """Remove a verified inactive worktree, re-inspecting under its exclusive lock.

    ``before_lock`` is a deterministic test seam for the use/cleanup race.
    """
    repo, task_dir, target = _absolute(repo), _absolute(task_dir), _absolute(target)
    _, _, reason = _cleanup_preflight(
        repo, task_dir, target, confirm_inactive=confirm_inactive,
        adopt_owned=adopt_owned, reproducible_caches=reproducible_caches,
        recovery_ref=recovery_ref,
    )
    if reason:
        return LifecycleOutcome("preserved", target, reason)
    if before_lock:
        before_lock()
    lock_acquired = False
    try:
        with lifecycle_lock(repo, target, exclusive=True, blocking=False):
            lock_acquired = True
            _, caches, reason = _cleanup_preflight(
                repo, task_dir, target, confirm_inactive=confirm_inactive,
                adopt_owned=adopt_owned, reproducible_caches=reproducible_caches,
                recovery_ref=recovery_ref,
            )
            if reason:
                return LifecycleOutcome("preserved", target, f"re-inspection refused cleanup: {reason}")
            for cache in caches:
                if not cache.exists():
                    continue
                if cache.is_dir():
                    shutil.rmtree(cache)
                else:
                    cache.unlink()
            final, _, reason = _cleanup_preflight(
                repo, task_dir, target, confirm_inactive=confirm_inactive,
                adopt_owned=adopt_owned, reproducible_caches=(), recovery_ref=recovery_ref,
            )
            if reason or final.dirty or final.ignored:
                return LifecycleOutcome("preserved", target, f"post-cache re-inspection refused cleanup: {reason or 'content changed'}")
            result = _run_git(repo, ["worktree", "remove", str(target)])
            if result.returncode:
                return LifecycleOutcome("error", target, result.stderr.strip() or "git worktree remove failed")
            if target.exists() or _registration(repo, target)[0] is not None:
                return LifecycleOutcome("error", target, "post-remove physical or registration check failed")
            protected_ref = recovery_ref if final.detached else final.branch
            if not _named_ref_matches(repo, protected_ref, final.head):
                return LifecycleOutcome("error", target, "worktree was removed but its branch or recovery ref failed post-remove verification")
            if not _replace_recorded_path(repo, task_dir, target, None):
                return LifecycleOutcome("error", target, "removed but task metadata update failed")
            return LifecycleOutcome("removed", target, "removed and verified", safety_checks_complete=True)
    except OSError as exc:
        if not lock_acquired:
            return LifecycleOutcome("preserved", target, "lifecycle lock is held; worktree may be active")
        return LifecycleOutcome("error", target, f"cleanup filesystem operation failed: {exc}")


def use_worktree(
    repo: Path, target: Path, command: Sequence[str],
    *, before_lock: Callable[[], None] | None = None,
) -> int:
    """Run a command while holding the task worktree's cooperative use lock."""
    repo, target = _absolute(repo), _absolute(target)
    if before_lock:
        before_lock()
    try:
        with lifecycle_lock(repo, target, exclusive=False):
            item = inspect_worktree(repo, target)
            if item.primary or item.unsafe_link or not item.exists or not item.registered or not item.same_repository:
                print("Error: worktree changed before use; safety checks refused the command", file=sys.stderr)
                return 1
            return subprocess.run(list(command), cwd=target, check=False).returncode
    except OSError as exc:
        print(f"Error: could not acquire or use worktree lifecycle lock: {exc}", file=sys.stderr)
        return 1


def format_outcome(outcome: LifecycleOutcome) -> str:
    label = {
        "removed": "REMOVED", "created": "CREATED", "moved": "MOVED",
        "preserved": "PRESERVED", "policy_denied": "POLICY DENIED",
        "error": "ERROR",
    }.get(outcome.status, outcome.status.upper())
    lines = [f"[{label}] {outcome.path}", f"  Reason: {outcome.reason}"]
    if outcome.recovery:
        lines.append(f"  Recovery: {outcome.recovery}")
    if outcome.status == "policy_denied" and outcome.safety_checks_complete and outcome.manual_delete_allowed:
        lines += ["  Manual deletion candidate (review before deleting):", f"    {outcome.path}"]
    return "\n".join(lines)


def print_closeout_hint(repo: Path, task_dir: Path, event: str) -> None:
    """Read-only worktree residue hint; silent for tasks without metadata."""
    paths = task_worktree_paths(task_dir)
    if not paths:
        return
    print(f"[WORKTREE] {event} left {len(paths)} recorded worktree(s); cleanup is separate:", file=sys.stderr)
    for path in paths:
        item = inspect_worktree(repo, path)
        state = "registered" if item.registered else "not registered"
        content = "dirty" if item.dirty else ("ignored data" if item.ignored else "clean")
        print(f"  - {path} ({state}, {content}, activity unknown)", file=sys.stderr)
    print("  Inspect with .trellis/scripts/worktree.py inspect <task> before move or cleanup.", file=sys.stderr)
