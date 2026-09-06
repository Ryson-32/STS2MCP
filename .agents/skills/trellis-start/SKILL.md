---
name: trellis-start
description: "Load missing Trellis project context when starting a development session. Reuse context already loaded by hooks or the current session; use continue to resume an existing task."
---

# Start Session

Load missing project context at the start of a Trellis development session. Reuse context already loaded by a hook or earlier in the session.

---

## Step 1: Current state
Identity, git status, current task and immediate relations, journal location. The relation scan includes reverse references; missing and ambiguous links remain visible.

```bash
python ./.trellis/scripts/get_context.py
```

If this output includes a line beginning `Trellis update available:`, copy the full line verbatim when summarizing session context. Do not shorten operational command hints.

## Step 2: Workflow overview
Compact Phase Index, request triage rules, planning artifact contract, and the step-detail command.

```bash
python ./.trellis/scripts/get_context.py --mode phase
```

Full guide in `.trellis/workflow.md` (read on demand).

## Step 3: Guideline indexes
Discover packages + spec layers, then read each relevant index file.

```bash
python ./.trellis/scripts/get_context.py --mode packages
cat .trellis/spec/guides/index.md             # only for relevant cross-cutting concerns
cat .trellis/spec/<package>/<layer>/index.md   # for each relevant layer
```

Index files list the specific guideline docs to read when you actually start coding.

## Step 4: Decide next action
From Step 1 you know the current task and status. Check the task directory:

- **Active task status `planning` + no `prd.md`** → Phase 1.1. Load the `trellis-brainstorm` skill.
- **Active task status `planning` + `prd.md` exists** → inspect unresolved decisions and existing authorization. Add optional design/execution notes only when useful, then load the relevant Phase 1 step before starting.
- **Active task status `in_progress`** → inspect evidence and continue the next unfinished step; use `trellis-continue` when resuming. For implementation, load:
  ```bash
  python ./.trellis/scripts/get_context.py --mode phase --step 2.1 --platform codex
  ```
- **No active task** → follow the current workflow's request triage and existing authorization. Simple conversation needs no task ritual; material open decisions may need `trellis-brainstorm`.

For a wider relation view use `task.py related <task> --depth 2`. Full inventories remain available through `task.py list` and `task.py list-archive`; do not print them again by default.

---

## Skill routing (quick reference)

| User intent | Skill |
|---|---|
| Unresolved product or scope decisions | `trellis-brainstorm` |
| About to write code | `trellis-before-dev` |
| Affected behavior needs review | `trellis-check` |
| Stuck / fixed same bug multiple times | `trellis-break-loop` |
| Learned something worth capturing | `trellis-update-spec` |

Full phase and authorization rules live in `.trellis/workflow.md`.
