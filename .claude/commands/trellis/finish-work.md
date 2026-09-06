# Finish Work

Use this after the task's actual work and proportionate checks are complete. This command archives task state and records the session; it does not make the work commit for you.

## Review the current state

```bash
python ./.trellis/scripts/get_context.py --mode record
git status --short
```

Separate current-task changes from unrelated work already present in the checkout. Leave unrelated files untouched.

If current-task code or documentation is still uncommitted, return to workflow Phase 3.4 and commit only that task's coherent changes. If ownership is unclear, report the exact paths and resolve ownership before staging them.

Before archiving, reuse workflow Phase 3.3's conditional route: when the task produced a verified, reusable conclusion, update its one current owner—a spec for reusable execution contracts, active docs for durable human-facing science, architecture, route or evidence, or the local knowledge owner for research facts. If no stable conclusion changed, continue without writing an explicit `none`, checklist artifact, research backlink or other closeout artifact.

## Archive the task

Archive the active task only after its acceptance criteria are met and required work is complete:

```bash
python ./.trellis/scripts/task.py archive <task-name>
```

Archive other completed tasks only when the user asked for that cleanup or their ownership and completion are already clear. The script may create a bookkeeping commit according to `.trellis/config.yaml`; report what actually happened.

If there is no active completed task, skip archiving.

## Record the session

When a durable session journal is useful, record the work commit hashes and a short outcome:

```bash
python ./.trellis/scripts/add_session.py --title "Session Title" --commit "hash1,hash2" --summary "Brief summary"
```

Do not list archive bookkeeping commits as work results. A journal entry is useful for cross-session recovery, but it is not evidence that code, tests, simulation, or documentation passed.

Finish with the real outcome, verification performed, anything skipped or blocked, external actions taken, and the remaining next step if one exists. No fixed commit count or report layout is required.
