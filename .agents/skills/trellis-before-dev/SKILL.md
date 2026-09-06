---
name: trellis-before-dev
description: "Loads the active task and only the project rules and current docs that directly affect the planned change. Use before implementation begins or when switching to another package."
---

# Before Development

Read enough current context to make the change correctly; do not turn preparation into a repository-wide reading exercise.

1. Read the active task's `prd.md`. Read `design.md`, `implement.md`, and task `research/` only when present and relevant.
2. Locate the code or document that owns the behavior and inspect its current implementation, callers, and nearby tests or examples.
3. Read the spec index for each affected package or layer, then open only the linked rules that match this change. Use:

   ```bash
   python ./.trellis/scripts/get_context.py --mode packages
   ```

   when package ownership or available spec layers are unclear.
4. Read shared guides only when the task actually raises the concern they cover. Do not load every guide by default.
5. If a task manifest exists, treat it as a curated starting point. It may reference relevant specs, research, or current human documentation; it does not replace inspecting the affected implementation.
6. For a non-trivial change, state the intended behavior gap, likely owner, affected files, and deliberate exclusions in the task plan or working update when that will help coordination or recovery. A small, clear change can proceed directly.
7. If inspection reveals a materially larger scope, new external effect, or unresolved user-owned decision, surface it before expanding the work. Otherwise continue under the existing authorization.

The goal is correct, focused implementation with enough context—not completion of a fixed checklist.
