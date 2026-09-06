"""
Task data access layer.

Single source of truth for loading and iterating task directories.
Replaces scattered task.json parsing across 9+ files.

Provides:
    load_task          — Load a single task by directory path
    iter_active_tasks  — Iterate all non-archived tasks (sorted)
    get_all_statuses   — Get {dir_name: status} map for children progress
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

from .io import describe_json_read_failure, read_json_checked
from .paths import FILE_TASK_JSON
from .types import TaskInfo


def load_task(task_dir: Path) -> TaskInfo | None:
    """Load task from a directory containing task.json.

    Args:
        task_dir: Absolute path to the task directory.

    Returns:
        TaskInfo if task.json exists and is valid, None otherwise.

    A directory without task.json is not a task, so it is skipped silently.
    A task.json that exists but cannot be loaded is different: the task
    disappears from `task.py list` and from every context the iterator feeds.
    Callers stay tolerant, but the skip is announced on stderr so a task
    cannot vanish from the workflow with no diagnostic anywhere.
    """
    task_json = task_dir / FILE_TASK_JSON
    if not task_json.is_file():
        return None

    data, reason = read_json_checked(task_json)
    if data is None:
        problem, hint = describe_json_read_failure(task_json, reason)
        print(f"[WARN] Skipping task '{task_dir.name}': {problem}", file=sys.stderr)
        print(f"       {hint}", file=sys.stderr)
        return None

    return TaskInfo(
        dir_name=task_dir.name,
        directory=task_dir,
        title=data.get("title") or data.get("name") or "unknown",
        status=data.get("status", "unknown"),
        assignee=data.get("assignee", ""),
        priority=data.get("priority", "P2"),
        children=tuple(dict.fromkeys(c for c in data.get("children", []) if isinstance(c, str))) if isinstance(data.get("children"), list) else (),
        parent=data.get("parent") if isinstance(data.get("parent"), str) else None,
        package=data.get("package"),
        raw=data,
    )


def iter_active_tasks(tasks_dir: Path) -> Iterator[TaskInfo]:
    """Iterate all active (non-archived) tasks, sorted by directory name.

    Skips the "archive" directory and directories without valid task.json.

    Args:
        tasks_dir: Path to the tasks directory.

    Yields:
        TaskInfo for each valid task.
    """
    if not tasks_dir.is_dir():
        return

    for d in sorted(tasks_dir.iterdir()):
        if not d.is_dir() or d.name == "archive":
            continue
        info = load_task(d)
        if info is not None:
            yield info


def get_all_statuses(tasks_dir: Path) -> dict[str, str]:
    """Get statuses for exact paths and unique names, including archived tasks.

    Useful for computing children progress without loading full TaskInfo.

    Args:
        tasks_dir: Path to the tasks directory.

    Returns:
        Dict mapping directory names to status strings.
    """
    from .task_relations import TaskRelations
    graph = TaskRelations(tasks_dir, read_plans=False)
    statuses: dict[str, str] = {}
    for ref in {*graph.tasks, *graph.names}:
        targets = graph.resolve(ref)
        status = graph.tasks[targets[0]].status if len(targets) == 1 else "ambiguous"
        for alias in (ref, f".trellis/tasks/{ref}", f"tasks/{ref}"):
            statuses[alias] = status
    return statuses


def iter_all_tasks(tasks_dir: Path) -> Iterator[TaskInfo]:
    """Read unarchived tasks and monthly archives without inferring completion."""
    yield from iter_active_tasks(tasks_dir)
    archive = tasks_dir / "archive"
    if archive.is_dir():
        for month in sorted(archive.iterdir()):
            if month.is_dir():
                yield from iter_active_tasks(month)


def children_progress(
    children: tuple[str, ...] | list[str],
    all_statuses: dict[str, str],
) -> str:
    """Format children progress string like " [2/3 done]".

    Args:
        children: List of child directory names.
        all_statuses: Status map from get_all_statuses().

    Returns:
        Formatted string, or "" if no children.
    """
    if not children:
        return ""
    unique: dict[tuple[bool, str], str] = {}
    for child in children:
        status = all_statuses.get(child)
        resolved = status is not None and status != "ambiguous"
        name = Path(child.replace("\\", "/")).name
        identity = name if resolved and all_statuses.get(name) not in (None, "ambiguous") else child
        unique.setdefault((resolved, identity), child)
    children = list(unique.values())
    done = sum(
        1 for c in children
        if all_statuses.get(c) in ("completed", "done")
    )
    unknown = sum(c not in all_statuses or all_statuses[c] == "ambiguous" for c in children)
    suffix = f"; {unknown} missing/ambiguous" if unknown else ""
    return f" [{done}/{len(children)} done{suffix}]"
