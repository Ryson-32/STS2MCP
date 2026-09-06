"""Read task relationships and their evidence; never repair metadata on query."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from .tasks import load_task


class TaskRelations:
    """One scan of metadata and planning artifacts, including reverse references."""

    def __init__(self, tasks_dir: Path, read_plans: bool = True) -> None:
        self.tasks_dir = tasks_dir
        self.scan_issues: list[dict] = []
        self.tasks = {}
        def entries(directory: Path) -> list[Path]:
            try:
                return sorted(directory.iterdir())
            except OSError as exc:
                self.scan_issues.append({"task": directory.relative_to(tasks_dir).as_posix(), "message": f"unreadable directory: {type(exc).__name__}"})
                return []
        directories = []
        if tasks_dir.is_dir():
            for directory in entries(tasks_dir):
                if directory.name == "archive" and directory.is_dir():
                    for month in entries(directory):
                        if month.is_dir():
                            directories.extend(d for d in entries(month) if d.is_dir())
                elif directory.is_dir():
                    directories.append(directory)
        for directory in directories:
            key = directory.relative_to(tasks_dir).as_posix()
            task = load_task(directory)
            if task is None:
                self.scan_issues.append({"task": key, "message": "missing or unreadable task.json; task omitted from relationship scan"})
            else:
                self.tasks[key] = task
        self.names: dict[str, list[str]] = defaultdict(list)
        self.edges: list[dict] = []
        self.issues: list[dict] = []
        for key, task in self.tasks.items():
            aliases = {task.dir_name}
            aliases.update(value for field in ("id", "name") if isinstance(value := task.raw.get(field), str) and value)
            for alias in aliases:
                self.names[alias].append(key)
        for alias, keys in self.names.items():
            if len(keys) > 1:
                for key in keys:
                    self.issue(key, f"ambiguous task alias: {alias} -> {', '.join(keys)}")
        for key, task in self.tasks.items():
            for field in ("parent", "children", "subtasks", "dependencies", "depends_on", "blocked_by"):
                value = task.raw.get(field)
                if value is None:
                    continue
                values = [value] if field == "parent" and isinstance(value, str) else value
                if not isinstance(values, list):
                    self.issue(key, f"invalid {field}: expected task references; inspect task.json")
                    continue
                seen: set[str] = set()
                for ref in values:
                    if not isinstance(ref, str) or not ref.strip():
                        self.issue(key, f"invalid {field} entry: {ref!r}")
                        continue
                    if ref in seen:
                        self.issue(key, f"duplicate {field}: {ref}")
                        continue
                    seen.add(ref)
                    self.edge(key, ref, field, f"{key}/task.json:{field}")
            if read_plans:
                self.plan_edges(key)
        self.check_hierarchy()

    def resolve(self, ref: str) -> list[str]:
        """Exact paths/names only: never choose a suffix or an archive collision."""
        ref = ref.replace("\\", "/").rstrip("/")
        marker = ".trellis/tasks/"
        if marker in ref:
            ref = ref.split(marker, 1)[1]
        elif ref.startswith("tasks/"):
            ref = ref[len("tasks/"):]
        if "/" in ref:
            return [ref] if ref in self.tasks else []
        # An old unarchived address may now live in archive. If that address
        # was reused, retain every candidate instead of binding to the new task.
        return self.names.get(ref, [])

    def issue(self, task: str, message: str) -> None:
        item = {"task": task, "message": message}
        if item not in self.issues:
            self.issues.append(item)

    def edge(self, source: str, ref: str, kind: str, evidence: str) -> None:
        targets = self.resolve(ref)
        state = "resolved" if len(targets) == 1 else "ambiguous" if targets else "missing"
        item = {"source": source, "reference": ref, "kind": kind, "targets": targets, "state": state, "evidence": evidence}
        if item not in self.edges:
            self.edges.append(item)
        if state != "resolved":
            self.issue(source, f"{state} {kind}: {ref}" + (f" -> {', '.join(targets)}" if targets else ""))

    def plan_edges(self, key: str) -> None:
        # A mention is evidence for inspection, never a dependency assertion.
        pattern = re.compile(
            r"\.trellis/tasks/(?:archive/\d{4}-\d{2}/)?[A-Za-z0-9_-]+"
            r"|(?<![A-Za-z0-9_-])(?:archive/\d{4}-\d{2}/)?\d{2}-\d{2}-[A-Za-z0-9][A-Za-z0-9_-]*"
        )
        for name in ("prd.md", "design.md", "implement.md"):
            path = self.tasks[key].directory / name
            if not path.is_file():
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeError) as exc:
                self.issue(key, f"unreadable {name}: {type(exc).__name__}")
                continue
            for number, line in enumerate(lines, 1):
                for ref in dict.fromkeys(pattern.findall(line)):
                    if self.resolve(ref) == [key]:
                        continue
                    self.edge(key, ref, "plan_reference", f"{key}/{name}:{number}")

    def hierarchy(self) -> dict[str, set[str]]:
        graph: dict[str, set[str]] = defaultdict(set)
        for edge in self.edges:
            if edge["state"] != "resolved":
                continue
            source, target = edge["source"], edge["targets"][0]
            if edge["kind"] == "parent":
                graph[target].add(source)
            elif edge["kind"] in ("children", "subtasks"):
                graph[source].add(target)
        return graph

    def check_hierarchy(self) -> None:
        graph = self.hierarchy()
        parents: dict[str, set[str]] = defaultdict(set)
        for parent, children in graph.items():
            for child in children:
                parents[child].add(parent)
                p, c = self.tasks[parent], self.tasks[child]
                if self.resolve(c.parent or "") != [parent] or not any(self.resolve(ref) == [child] for ref in p.children):
                    self.issue(child, f"inconsistent parent/children: {parent} -> {child}")
                # Iterative reachability also handles rootless cycles and deep trees.
                pending, visited = [child], set()
                while pending:
                    node = pending.pop()
                    if node == parent:
                        self.issue(parent, f"cycle in hierarchy through {child}")
                        break
                    if node not in visited:
                        visited.add(node)
                        pending.extend(graph.get(node, ()))
        for child, refs in parents.items():
            if len(refs) > 1:
                self.issue(child, f"ambiguous parents: {', '.join(sorted(refs))}")
        dependencies: dict[str, set[str]] = defaultdict(set)
        for edge in self.edges:
            if edge["kind"] in ("dependencies", "depends_on", "blocked_by") and edge["state"] == "resolved":
                dependencies[edge["source"]].add(edge["targets"][0])
        for source, targets in dependencies.items():
            pending, seen = list(targets), set()
            while pending:
                node = pending.pop()
                if node == source:
                    self.issue(source, "cycle in explicit dependencies")
                    break
                if node not in seen:
                    seen.add(node)
                    pending.extend(dependencies.get(node, ()))

    def view(self, target: str | None, depth: int = 1) -> dict:
        roots = self.resolve(target) if target else []
        selected, frontier = set(roots), set(roots)
        edges: list[dict] = []
        for _ in range(depth):
            following: set[str] = set()
            for edge in self.edges:
                if edge["source"] in frontier or frontier.intersection(edge["targets"]):
                    if edge not in edges:
                        edges.append(edge)
                    following.add(edge["source"])
                    following.update(edge["targets"])
            frontier = following - selected
            selected.update(following)
        issues = [i for i in self.issues if i["task"] in selected]
        if target and len(roots) != 1:
            issues.insert(0, {"task": target, "message": "ambiguous task" if roots else "missing task"})
        return {
            "target": target, "roots": roots, "depth": depth,
            "tasks": [{"path": k, "status": self.tasks[k].status, "title": self.tasks[k].title,
                       "archived": k.startswith("archive/")} for k in sorted(selected)],
            "relations": edges, "issues": issues,
            "scanned": len(self.tasks), "scan_issues": self.scan_issues,
            "scan_complete": not self.scan_issues,
            "note": "Reverse references checked across readable unarchived tasks and archives; this is a live scan, not a transaction snapshot. Plan references are mentions, not inferred dependencies; prose-only ordering needs artifact review.",
        }


def render_relations(view: dict) -> list[str]:
    lines = [f"Scanned: {view['scanned']} task(s); showing depth {view['depth']}."]
    for task in view["tasks"]:
        suffix = "; archived" if task["archived"] else ""
        lines.append(f"- {task['path']}/ ({task['status']}{suffix})")
    grouped: dict[tuple, list[str]] = {}
    for edge in view["relations"]:
        source, target, kind = edge["source"], edge["reference"], edge["kind"]
        if edge["state"] == "resolved":
            target = edge["targets"][0]
            if kind == "parent":
                source, target = target, source
            if kind in ("parent", "children"):
                kind = "parent/child"
        key = (source, target, kind, edge["state"])
        grouped.setdefault(key, []).append(edge["evidence"])
    for (source, target, kind, state), evidence in grouped.items():
        lines.append(f"  {source} --{kind}--> {target} [{state}] ({'; '.join(dict.fromkeys(evidence))})")
    for issue in [*view["issues"], *view.get("scan_issues", [])]:
        lines.append(f"[!] {issue['task']}: {issue['message']}")
    if not view["target"]:
        lines.append("No current task. Pass an exact task name to task.py related.")
    lines.append(view["note"])
    lines.append("Expand: task.py related <task> --depth 2; full lists: task.py list / task.py list-archive")
    return lines
