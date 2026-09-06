# Continue Current Task

Resume the active task using current evidence and existing authorization.

## Load Missing Context

```bash
python ./.trellis/scripts/get_context.py
python ./.trellis/scripts/get_context.py --mode phase
```

The default context shows the current task and its immediate relations, including reverse references. Inspect missing or ambiguous links before depending on them. Expand only when needed:

```bash
python ./.trellis/scripts/task.py related <task> --depth 2
python ./.trellis/scripts/task.py list
python ./.trellis/scripts/task.py list-archive
```

Reuse current context already loaded in this session. Read the task PRD, relevant optional design/execution notes, and the latest evidence.

## Resume the Next Unfinished Step

- `planning`: resolve material open decisions. A PRD may be sufficient; missing optional design, execution, or JSONL files do not automatically block starting.
- `in_progress`: inspect the actual implementation and evidence to determine whether to implement, check, or close out. Status alone does not prove a step finished.
- `completed`: verify the completion record before following the archive flow.

Preserve implementation and commit authorization already provided. Ask only for a missing user decision or a scope change that exceeds it. Do not repeat planning, approval, or checks whose result is still applicable.

For long plans, maintain a concise goal, next unresolved question, remaining boundaries, and evidence links without rewriting their history.

## Load the Applicable Step

```bash
python ./.trellis/scripts/get_context.py --mode phase --step <X.X> --platform claude
```

Follow `.trellis/workflow.md`, including project-specific required checks and external-action boundaries. This command is an entry point; it does not replace the workflow.
