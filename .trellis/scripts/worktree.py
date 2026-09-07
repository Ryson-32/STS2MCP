#!/usr/bin/env python3
"""Create, inspect, move, use, and clean Trellis task worktrees."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

from common.paths import get_repo_root, get_tasks_dir
from common.task_utils import resolve_task_dir
from common.worktree import (
    cleanup_worktree,
    create_worktree,
    format_outcome,
    inspect_worktree,
    move_worktree,
    task_worktree_paths,
    use_worktree,
)


def _task_dir(value: str, repo: Path) -> Path | None:
    raw = Path(os.path.abspath(os.path.expanduser(value)))
    tasks = get_tasks_dir(repo).resolve()
    if raw.is_dir() and (raw / "task.json").is_file():
        try:
            raw.resolve().relative_to(tasks)
            return raw
        except ValueError:
            return None
    resolved = resolve_task_dir(value, repo)
    if resolved:
        return resolved
    matches = list((tasks / "archive").glob(f"*/*{value}")) if (tasks / "archive").is_dir() else []
    return matches[0] if len(matches) == 1 and (matches[0] / "task.json").is_file() else None


def _path_json(value):
    if isinstance(value, Path):
        return str(value)
    raise TypeError(type(value).__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, help="repository checkout (defaults to current repo)")
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create")
    create.add_argument("task")
    create.add_argument("--branch")
    create.add_argument("--base", default="HEAD")
    create.add_argument("--owner")
    create.add_argument("--existing-branch", action="store_true")

    inspect = commands.add_parser("inspect")
    inspect.add_argument("task")
    inspect.add_argument("--path", type=Path)
    inspect.add_argument("--json", action="store_true")

    move = commands.add_parser("move")
    move.add_argument("task")
    move.add_argument("source", type=Path)
    move.add_argument("destination", nargs="?", type=Path)
    move.add_argument("--confirm-inactive", action="store_true")
    move.add_argument("--adopt-owned", action="store_true")
    move.add_argument("--owner")

    cleanup = commands.add_parser("cleanup")
    cleanup.add_argument("task")
    cleanup.add_argument("path", type=Path)
    cleanup.add_argument("--confirm-inactive", action="store_true")
    cleanup.add_argument("--adopt-owned", action="store_true")
    cleanup.add_argument("--reproducible-cache", action="append", default=[])
    cleanup.add_argument("--recovery-ref")

    use = commands.add_parser("use")
    use.add_argument("path", type=Path)
    use.add_argument("child_command", nargs=argparse.REMAINDER)

    args = parser.parse_args()
    repo = (args.repo or get_repo_root()).resolve()
    if args.command == "use":
        command = args.child_command[1:] if args.child_command[:1] == ["--"] else args.child_command
        if not command:
            parser.error("use requires a command after --")
        return use_worktree(repo, args.path, command)

    task = _task_dir(args.task, repo)
    if task is None:
        print(f"Error: task not found or outside .trellis/tasks: {args.task}", file=sys.stderr)
        return 1
    if args.command == "create":
        outcome = create_worktree(repo, task, branch=args.branch, base=args.base, owner=args.owner, existing_branch=args.existing_branch)
    elif args.command == "move":
        outcome = move_worktree(repo, task, args.source, destination=args.destination, confirm_inactive=args.confirm_inactive, adopt_owned=args.adopt_owned, owner=args.owner)
    elif args.command == "cleanup":
        outcome = cleanup_worktree(repo, task, args.path, confirm_inactive=args.confirm_inactive, adopt_owned=args.adopt_owned, reproducible_caches=args.reproducible_cache, recovery_ref=args.recovery_ref)
    else:
        paths = [args.path] if args.path else task_worktree_paths(task)
        rows = [asdict(inspect_worktree(repo, path)) for path in paths]
        if args.json:
            print(json.dumps(rows, default=_path_json, ensure_ascii=False, indent=2))
        else:
            if not rows:
                print("No worktrees recorded for this task.")
            for row in rows:
                print(f"{row['path']}: registered={row['registered']} primary={row['primary']} same_repository={row['same_repository']} dirty={bool(row['tracked_changes'] or row['untracked'])} ignored={len(row['ignored'])} lock_available={row['lock_available']}")
        return 0
    print(format_outcome(outcome))
    return 0 if outcome.status in ("created", "moved", "removed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
