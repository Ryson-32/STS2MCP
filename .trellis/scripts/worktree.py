#!/usr/bin/env python3
"""Create, inspect, move, use, and clean Trellis task worktrees."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
from dataclasses import asdict
from pathlib import Path

from common.paths import get_repo_root, get_tasks_dir
from common.git import main_worktree_root
from common.task_utils import resolve_task_dir
from common.worktree import (
    cleanup_worktree,
    create_worktree,
    format_outcome,
    inspect_for_write,
    inspect_worktree,
    move_worktree,
    _owner,
    task_worktree_paths,
    use_worktree,
)


def _validated_task_dir(candidate: Path | None, repo: Path) -> Path | None:
    """Return a task path only when its physical location is under tasks/."""
    if candidate is None:
        return None
    tasks = get_tasks_dir(repo)
    try:
        resolved = candidate.resolve()
        tasks_resolved = tasks.resolve()
    except (OSError, RuntimeError):
        return None
    if resolved == tasks_resolved or tasks_resolved not in resolved.parents:
        return None
    if not resolved.is_dir() or not (resolved / "task.json").is_file():
        return None
    return tasks / resolved.relative_to(tasks_resolved)


def _task_dir(value: str, repo: Path) -> Path | None:
    raw = Path(os.path.abspath(os.path.expanduser(value)))
    if raw.is_dir() and (raw / "task.json").is_file():
        return _validated_task_dir(raw, repo)
    resolved = _validated_task_dir(resolve_task_dir(value, repo), repo)
    if resolved is not None:
        return resolved
    tasks = get_tasks_dir(repo)
    matches = list((tasks / "archive").glob(f"*/*{value}")) if (tasks / "archive").is_dir() else []
    validated = [_validated_task_dir(match, repo) for match in matches]
    valid_matches = [match for match in validated if match is not None]
    return valid_matches[0] if len(valid_matches) == 1 else None


def _path_json(value):
    if isinstance(value, Path):
        return str(value)
    raise TypeError(type(value).__name__)


def _shell_quote(value: object) -> str:
    """Quote one argument for the current platform's interactive shell."""
    text = str(value)
    if os.name == "nt":
        return "'" + text.replace("'", "''") + "'"
    return shlex.quote(text)


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
    inspect.add_argument("--for-write", action="store_true")
    inspect.add_argument("--owner")

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
    current_repo = get_repo_root().resolve()
    repo = (args.repo or current_repo).resolve()
    if args.command == "use":
        command = args.child_command[1:] if args.child_command[:1] == ["--"] else args.child_command
        if not command:
            parser.error("use requires a command after --")
        return use_worktree(repo, args.path, command)

    if args.command == "inspect" and args.for_write:
        if args.path is None:
            parser.error("inspect --for-write requires --path")
        if args.repo is not None:
            error = "inspect --for-write must run from the target checkout; remove --repo and change to the lane first"
            if args.json:
                print(json.dumps({
                    "ok": False, "for_write": True,
                    "repo": current_repo, "requested_repo": repo,
                    "task": args.task, "path": args.path,
                    "owner": None, "expected_owner": args.owner,
                    "branch": None, "head": None, "dirty": None,
                    "checks": {"repo_override": False}, "errors": [error],
                }, default=_path_json, ensure_ascii=False, indent=2))
            else:
                print(f"Error: {error}", file=sys.stderr)
            return 1
        repo = current_repo
    authoritative_commands = {"create"}
    if args.command == "inspect" and args.for_write:
        authoritative_commands.add("inspect")
    task_repo = (main_worktree_root(repo) or repo) if args.command in authoritative_commands else repo
    task = _task_dir(args.task, task_repo)
    if task is None:
        error = f"task not found or outside .trellis/tasks: {args.task}"
        if args.command == "inspect" and args.for_write and args.json:
            expected_owner = args.owner.strip() if isinstance(args.owner, str) and args.owner.strip() else None
            errors = [error]
            if expected_owner is None:
                errors.append("expected owner is required; rerun with --owner <expected-owner>")
            print(json.dumps({
                "ok": False, "for_write": True, "repo": repo,
                "task": args.task, "path": args.path,
                "owner": None, "expected_owner": expected_owner,
                "branch": None, "head": None, "dirty": None,
                "checks": {"task_registry": False, "expected_owner": expected_owner is not None},
                "errors": errors,
            }, default=_path_json, ensure_ascii=False, indent=2))
        else:
            print(f"Error: {error}", file=sys.stderr)
        return 1
    create_owner: str | None = None
    if args.command == "create":
        create_owner = _owner(repo, task, args.owner)
        outcome = create_worktree(repo, task, branch=args.branch, base=args.base, owner=create_owner, existing_branch=args.existing_branch)
    elif args.command == "move":
        outcome = move_worktree(repo, task, args.source, destination=args.destination, confirm_inactive=args.confirm_inactive, adopt_owned=args.adopt_owned, owner=args.owner)
    elif args.command == "cleanup":
        outcome = cleanup_worktree(repo, task, args.path, confirm_inactive=args.confirm_inactive, adopt_owned=args.adopt_owned, reproducible_caches=args.reproducible_cache, recovery_ref=args.recovery_ref)
    else:
        if args.for_write:
            result = inspect_for_write(repo, task, args.path, args.owner)
            if args.json:
                print(json.dumps(result, default=_path_json, ensure_ascii=False, indent=2))
            else:
                print(f"{result['path']}: for_write={result['ok']} owner={result['owner']} branch={result['branch']} head={result['head']}")
                for error in result["errors"]:
                    print(f"  - {error}")
            return 0 if result["ok"] else 1
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
    if outcome.status == "created":
        assert create_owner is not None
        print("  Before writing, run from the worktree:")
        print(f"    cd {_shell_quote(outcome.path)}")
        print(f"    python .trellis/scripts/worktree.py inspect {_shell_quote(task)} --path {_shell_quote(outcome.path)} --for-write --owner {_shell_quote(create_owner)} --json")
    return 0 if outcome.status in ("created", "moved", "removed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
