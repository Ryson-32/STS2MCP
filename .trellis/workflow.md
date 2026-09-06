# Development Workflow

---

## Core Principles

1. **Plan before code** — figure out what to do before you start
2. **Specs injected, not remembered** — guidelines are injected via hook/skill, not recalled from memory
3. **Persist useful context** — record decisions, evidence, and handoffs that future work needs
4. **Incremental development** — one task at a time
5. **Capture learnings** — update the owning spec when a stable reusable contract changes

---

## Trellis System

### Developer Identity

On first use, initialize your identity:

```bash
python ./.trellis/scripts/init_developer.py <your-name>
```

Creates `.trellis/.developer` (gitignored) + `.trellis/workspace/<your-name>/`.

### Spec System

`.trellis/spec/` holds coding guidelines organized by package and layer.

- `.trellis/spec/<package>/<layer>/index.md` — entry point with **Pre-Development Checklist** + **Quality Check**. Actual guidelines live in the `.md` files it points to.
- `.trellis/spec/guides/index.md` — cross-package thinking guides.

```bash
python ./.trellis/scripts/get_context.py --mode packages   # list packages / layers
```

**When to update spec**: new pattern/convention found · bug-fix prevention to codify · new technical decision.

### Task System

Every task has its own directory under `.trellis/tasks/{MM-DD-name}/` holding `task.json`, `prd.md`, optional `design.md`, optional `implement.md`, optional `research/`, and context manifests (`implement.jsonl`, `check.jsonl`) for sub-agent-capable platforms.

```bash
# Task lifecycle
python ./.trellis/scripts/task.py create "<title>" --description "<summary>" [--slug <name>] [--parent <dir>]
python ./.trellis/scripts/task.py start <name>          # set active task (session-scoped when available)
python ./.trellis/scripts/task.py current --source      # show active task and source
python ./.trellis/scripts/task.py finish                # clear active task (triggers after_finish hooks)
python ./.trellis/scripts/task.py archive <name>        # move to archive/{year-month}/
python ./.trellis/scripts/task.py list [--mine] [--status <s>]
python ./.trellis/scripts/task.py list-archive
python ./.trellis/scripts/task.py related <name> --depth 2  # expand the relation view

# Code-spec context (injected into implement/check agents via JSONL).
# `implement.jsonl` / `check.jsonl` are optional curated references.
# Agents load the task artifacts and relevant specs directly when manifests are absent.
python ./.trellis/scripts/task.py add-context <name> <action> <file> <reason>
python ./.trellis/scripts/task.py list-context <name> [action]
python ./.trellis/scripts/task.py validate <name>

# Task metadata
python ./.trellis/scripts/task.py set-branch <name> <branch>
python ./.trellis/scripts/task.py set-base-branch <name> <branch>    # PR target
python ./.trellis/scripts/task.py set-scope <name> <scope>

# Hierarchy (parent/child)
python ./.trellis/scripts/task.py add-subtask <parent> <child>
python ./.trellis/scripts/task.py remove-subtask <parent> <child>

# PR creation
python ./.trellis/scripts/task.py create-pr [name] [--dry-run]
```

> Run `python ./.trellis/scripts/task.py --help` to see the authoritative, up-to-date list.

**Current-task mechanism**: `task.py create` creates the task directory and (when session identity is available) auto-sets the per-session active-task pointer so the planning breadcrumb fires immediately. `task.py start` writes the same pointer (idempotent if already set) and flips `task.json.status` from `planning` to `in_progress`. State is stored under `.trellis/.runtime/sessions/`. If no context key is available from hook input, `TRELLIS_CONTEXT_ID`, or a platform-native session environment variable, there is no active task and `task.py start` fails with a session identity hint. `task.py finish` deletes the current session file (status unchanged). `task.py archive <task>` writes `status=completed`, moves the directory to `archive/`, and deletes any runtime session files that still point at the archived task.

### Workspace System

Records every AI session for cross-session tracking under `.trellis/workspace/<developer>/`.

- `journal-N.md` — session log. **Max 2000 lines per file**; a new `journal-(N+1).md` is auto-created when exceeded.
- `index.md` — personal index (total sessions, last active).

```bash
python ./.trellis/scripts/add_session.py --title "Title" --commit "hash" --summary "Summary"
```

### Context Script

```bash
python ./.trellis/scripts/get_context.py                            # current task and immediate relations
python ./.trellis/scripts/get_context.py --mode packages            # available packages + spec layers
python ./.trellis/scripts/get_context.py --mode phase --step <X.Y>  # detailed guide for a workflow step
```

---

<!--
  WORKFLOW-STATE BREADCRUMB CONTRACT (read this before editing the tag blocks below)

  The [workflow-state:STATUS] blocks embedded in the ## Phase Index section
  below are the SINGLE source of truth for the per-turn `<workflow-state>`
  breadcrumb that every supported AI platform's UserPromptSubmit hook
  reads. inject-workflow-state.py (Python platforms) and
  inject-workflow-state.js (OpenCode plugin) only parse them — there is no
  fallback dict baked into the scripts after v0.5.0-rc.0.

  STATUS charset: [A-Za-z0-9_-]+. When the hook can't find a tag, it
  degrades to a generic "Refer to workflow.md for current step." line —
  intentionally visible so users notice and fix a broken workflow.md.

  INVARIANT (validated by the pinned-release profile fixture):
    Every workflow-walkthrough step marked `[required · once]` must have a
    matching enforcement line in its phase's [workflow-state:*] block. The
    breadcrumb is the only per-turn channel; if a mandatory step isn't
    mentioned there, the AI silently skips it (Phase 1 planning gate
    skip and Phase 3.4 commit skip both manifested via this gap).

  TAG ↔ PHASE scoping:
    [workflow-state:no_task]      → no active task; before Phase 1
    [workflow-state:task_error]   → active task record is unreadable; repair it before continuing
    [workflow-state:planning]     → all of Phase 1 (status='planning')
    [workflow-state:planning-inline] → Codex inline variant of Phase 1
    [workflow-state:in_progress]  → Phase 2 + Phase 3.2-3.4
                                    (status stays 'in_progress' from
                                    task.py start until task.py archive)
    [workflow-state:in_progress-inline] → Codex inline variant of Phase 2/3
    [workflow-state:completed]    → normally cleared by archive; a completed record can still
                                    exist after an interrupted or legacy lifecycle

  Editing checklist:
    - When you change a [workflow-state:STATUS] block, also check the
      matching phase's `[required · once]` walkthrough steps for sync
    - Template maintainers must verify fresh init and whole-file update paths;
      preserve user-modified consumers through the normal conflict policy
    - Installed runtime contract and sources:
      .trellis/workflow.md, .trellis/scripts/task.py,
      .trellis/scripts/common/task_store.py, .trellis/scripts/common/active_task.py,
      .codex/hooks/inject-workflow-state.py, .claude/hooks/inject-workflow-state.py
-->

## Phase Index

```
Phase 1: Plan    → clarify the outcome and record a proportionate plan
Phase 2: Execute → implement only after task status is in_progress
Phase 3: Finish  → verify, update spec, commit, and wrap up
```

### Request Triage

- Simple conversation or a small clear edit can proceed without a Trellis task unless the user or project requires one.
- Use a task for work that benefits from durable requirements, coordinated execution, or later continuation. An explicit implementation request authorizes this ordinary planning work.
- Preserve existing authorization. Ask only for unresolved user-owned decisions or scope and external effects beyond that authorization; do not require a second reply just to transition phases.

### Planning Artifacts

- `prd.md` — requirements, constraints, and acceptance criteria. Do not put technical design or execution checklists here.
- `design.md` — technical design for complex tasks: boundaries, contracts, data flow, tradeoffs, compatibility, rollout / rollback shape.
- `implement.md` — execution plan for complex tasks: ordered checklist, validation commands, review gates, and rollback points.
- `implement.jsonl` / `check.jsonl` — spec and research manifests for sub-agent context. They do not replace `implement.md`.
- A PRD can be sufficient. Add `design.md` or `implement.md` when their decisions, sequencing, or handoff value justify separate documents. JSONL manifests are optional curated context, not a file-count gate.

For a long plan that currently needs continuation, maintain a short top summary of its goal, next question, unresolved boundaries, and evidence links; update it with substantive progress while preserving the detailed history. Do not batch-rewrite historical plans or infer acceptance and archive eligibility from dates, checked boxes, or commits alone.

### Parent / Child Task Trees

Use a parent task when one user request contains several independently verifiable deliverables. The parent task owns the source requirement set, the task map, cross-child acceptance criteria, and final integration review; it normally should not be the implementation target unless it also has direct work.

Use child tasks for deliverables that can be planned, implemented, checked, and archived independently. Parent/child structure is not a dependency system: if one child must wait for another, write that ordering in the child `prd.md` / `implement.md` and keep each child's acceptance criteria testable.

Create new children with `task.py create "<title>" --description "<summary>" --slug <name> --parent <parent-dir>`. Link existing tasks with `task.py add-subtask <parent> <child>`, and unlink mistakes with `task.py remove-subtask <parent> <child>`.

<!-- Per-turn breadcrumb: shown when there is no active task (before Phase 1) -->

[workflow-state:no_task]
No active task. Classify the current request and follow existing authorization.
Simple conversation or a small clear edit needs no task ritual. Create a task when durable planning or coordination helps.
Ask only for unresolved user decisions or work beyond the authorized scope.
[/workflow-state:no_task]

<!-- Per-turn breadcrumb: shown when the active task record cannot be read. -->

[workflow-state:task_error]
The active task record could not be read. Do not create or activate another task.
Inspect the task directory named above and repair its task.json. It must be a valid JSON object with a non-empty status.
Preserve existing task fields and artifacts. If the correct status cannot be determined safely, ask the user before reconstructing the record.
[/workflow-state:task_error]

### Phase 1: Plan
- 1.0 Create task `[required · once]` (when a task is useful within the authorized scope)
- 1.1 Requirement exploration `[required · repeatable]` (`prd.md`; optional design and execution notes when useful)
- 1.2 Research `[optional · repeatable]`
- 1.3 Configure context `[optional · once]` — Claude Code, Cursor, OpenCode, Codex, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Snow, Reasonix, Grok, Kimi Code (sub-agent-dispatch platforms only; inline platforms skip)
- 1.4 Activate task `[required · once]` (resolve blocking decisions, then `task.py start`; status → in_progress)
- 1.5 Completion criteria

<!-- Per-turn breadcrumb: shown throughout Phase 1 (status='planning') -->

[workflow-state:planning]
Resolve material open decisions with `trellis-brainstorm` when needed.
`prd.md` can be enough; `design.md` and `implement.md` are optional when useful. Preserve existing authorization; run `task.py start` when the next work is clear and authorized.
Multi-deliverable scope: consider a parent task plus independently verifiable child tasks; dependencies must be written in child artifacts, not implied by tree position.
Sub-agent mode: curate `implement.jsonl` and `check.jsonl` when useful; absent or seed-only manifests are valid, with direct artifact/spec loading.
[/workflow-state:planning]

<!-- Per-turn breadcrumb: shown throughout Phase 1 when codex.dispatch_mode=inline.
     Codex-only opt-in alternate to [workflow-state:planning]. The main agent
     edits code directly in Phase 2, so jsonl curation is skipped —
     the inline workflow loads `trellis-before-dev` instead of injecting JSONL
     into a sub-agent. -->

[workflow-state:planning-inline]
Resolve material open decisions with `trellis-brainstorm` when needed.
`prd.md` can be enough; `design.md` and `implement.md` are optional when useful. Preserve existing authorization; run `task.py start` when the next work is clear and authorized.
Multi-deliverable scope: consider a parent task plus independently verifiable child tasks; dependencies must be written in child artifacts, not implied by tree position.
Inline mode: skip jsonl curation; Phase 2 reads artifacts/specs via `trellis-before-dev`.
[/workflow-state:planning-inline]

### Phase 2: Execute
- 2.1 Implement `[required · repeatable]`
- 2.2 Validate affected scope `[required · repeatable]`
- 2.3 Independent review `[when evidence warrants]`
- 2.4 Rollback `[on demand]`

<!-- Per-turn breadcrumb: shown while status='in_progress'.
     Scope: all of Phase 2 + Phase 3.2-3.4 (status stays 'in_progress' from
     task.py start until task.py archive; only archive flips it). The body
     therefore reminds the agent to validate, capture durable knowledge when
     it exists, and finish within the repository's commit authority. -->

Sub-agent dispatch protocol applies to all platforms and all sub-agents, including native Codex `SubagentStart` context injection with child-side pull fallback, class-2 Gemini/Qoder/Copilot/Reasonix/Trae/Grok/Kimi Code, hook-backed ZCode/Snow, and `trellis-research`: every dispatch prompt starts with `Active task: <task path from task.py current>` before role-specific instructions. On Grok Build, use `spawn_subagent` with `subagent_type` set to the Trellis agent name (e.g. `trellis-implement`). On Kimi Code, dispatch the built-in `coder` / `explore` sub-agent with the matching `.kimi-code/skills/trellis-<role>/SKILL.md` instructions.

[workflow-state:in_progress]
Tools: `trellis-implement` / `trellis-research` are sub-agent roles, not skills. `trellis-check` may be an agent or inline skill; `trellis-update-spec` is a skill.
Read the active task and relevant specs. Delegate bounded implementation when it helps; always name the active task, objective, starting baseline, protected shared state, expected result, and checks. Production-writing workers use the shared isolated-worktree contract; read-only work does not need a worktree. Native `SubagentStart` injection is preferred; child-side loading is the fallback.
Run the cheapest checks that cover the affected behavior and self-fix findings. Small changes may be author-checked; use an independent reviewer for scientific meaning, cross-module contracts, high-impact acceptance, or unresolved uncertainty. A different model family is a useful preference, not a completion requirement.
Update specs only for durable knowledge or reusable contracts. Report skipped or failed checks honestly, then commit or hand off according to repository authority.
[/workflow-state:in_progress]

<!-- Per-turn breadcrumb: shown while status='in_progress' when
     codex.dispatch_mode=inline. Codex-only opt-in alternate to
     [workflow-state:in_progress]. The main session edits code directly
     instead of dispatching sub-agents. -->

[workflow-state:in_progress-inline]
Load `trellis-before-dev`, read the task and relevant specs, edit within scope, and validate the affected behavior. Fix findings and re-run their checks. Use the `trellis-check` skill when independent review is warranted; spec updates are conditional on durable knowledge.
[/workflow-state:in_progress-inline]
### Phase 3: Finish
- 3.2 Debug retrospective `[on demand]`
- 3.3 Spec update `[when a stable contract changes]`
- 3.4 Commit changes `[required · once]`
- 3.5 Wrap-up reminder

> Note: step 3.1 was folded into 2.2 (final affected-scope check) and 3.4 (commit preamble). Numbering kept stable to avoid breaking external references.

<!-- Per-turn breadcrumb: shown while status='completed'.
     Normally cleared by successful archive. A legacy record or interrupted
     archive can leave completed status reachable. Verify evidence before closeout. -->

[workflow-state:completed]
A completed record is a status claim, not acceptance evidence. Verify the scoped result and commit state before `/trellis:finish-work`; preserve unrelated dirty work.
[/workflow-state:completed]

### Rules

1. Identify which Phase you're in, then continue from the next step there
2. Run steps in order inside each Phase; `[required]` steps can't be skipped
3. Phases can roll back (e.g., Execute reveals a prd defect → return to Plan to fix, then re-enter Execute)
4. Steps tagged `[once]` are skipped if the output already exists; don't re-run
5. Artifact presence informs the next step; missing optional `design.md` / `implement.md` is valid; inspect whether the next work is sufficiently clear.

### Active Task Routing

When a user request matches one of these intents inside an active task, route first, then load the detailed phase step if needed.

[Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Snow, Reasonix, Trae, Grok, Kimi Code]

- Planning or unclear requirements -> `trellis-brainstorm`.
- `in_progress` implementation/check -> dispatch `trellis-implement` / `trellis-check`.
- Repeated debugging -> `trellis-break-loop`; spec updates -> `trellis-update-spec`.

[/Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Snow, Reasonix, Trae, Grok, Kimi Code]

[codex-inline, Kilo, Antigravity, Devin, DeepSeek Harness]

- Planning or unclear requirements -> `trellis-brainstorm`.
- Before editing -> `trellis-before-dev`; after editing -> `trellis-check`.
- Repeated debugging -> `trellis-break-loop`; spec updates -> `trellis-update-spec`.

[/codex-inline, Kilo, Antigravity, Devin, DeepSeek Harness]

### Guardrails

- Keep the distinction between planning-only authorization and implementation authorization. Existing authorization remains valid through artifact review and task activation.
- Optional planning documents and JSONL files are created for context value, not because a complexity label requires them.
- Planning must be persisted to task artifacts; checks must run before reporting completion.

### Loading Step Detail

At each step, run this to fetch detailed guidance:

```bash
python ./.trellis/scripts/get_context.py --mode phase --step <step>
# e.g. python ./.trellis/scripts/get_context.py --mode phase --step 1.1
```

---

## Phase 1: Plan

Goal: clarify the authorized outcome and record enough planning context to implement and verify it.

#### 1.0 Create task `[required · once]`

Create a task directory when the authorized work benefits from a task. The command sets status to `planning`, writes `task.json`, creates a default `prd.md`, and auto-targets the new task when session identity is available:

```bash
python ./.trellis/scripts/task.py create "<task title>" --description "<one-line summary>" --slug <name>
```

`--slug` is the human-readable name only. Do **not** include the `MM-DD-` date prefix; `task.py create` adds that prefix automatically.

For task trees, create the parent task first and then create each child with `--parent <parent-dir>`. Do not start the parent just because children exist; start the child that owns the next independently verifiable deliverable.

After this command succeeds, the per-turn breadcrumb auto-switches to `[workflow-state:planning]`, pointing to the planning step.

Run only `create` here — do not also run `start`. `start` flips status to `in_progress`, which switches the breadcrumb to the implementation phase before planning artifacts are reviewed. Save `start` for step 1.4.

Skip when `python ./.trellis/scripts/task.py current --source` already points to a task.

#### 1.1 Requirement exploration `[required · repeatable]`

Load the `trellis-brainstorm` skill and explore requirements interactively with the user per the skill's guidance.

The brainstorm skill will guide you to:
- Ask one question at a time
- Prefer researching over asking the user
- Prefer offering options over open-ended questions
- Update `prd.md` immediately after each user answer
- Split large scopes into a parent task plus child tasks when the deliverables can be verified independently
- Keep `prd.md` focused on requirements and acceptance criteria
- Add `design.md` or `implement.md` when they clarify design, execution, or a long handoff

When considering a parent/child split:
- Use a parent task when one request contains several independently verifiable deliverables.
- Parent tasks own source requirements, child-task mapping, cross-child acceptance criteria, and final integration review.
- Child tasks own actual deliverables that can be planned, implemented, checked, and archived independently.
- Parent/child structure is not a dependency system. If child B depends on child A, write that ordering in child B's `prd.md` / `implement.md`.
- Start the child task that owns the next deliverable. Do not start the parent unless the parent itself has direct implementation work.

Return to this step whenever requirements change and revise the relevant artifact.

#### 1.2 Research `[optional · repeatable]`

Research can happen at any time during requirement exploration. It isn't limited to local code — you can use any available tool (MCP servers, skills, web search, etc.) to look up external information, including third-party library docs, industry practices, API references, etc.

[Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Snow, Reasonix, Trae, Grok, Kimi Code]

Spawn the research sub-agent:

- **Agent type**: `trellis-research`
- **Task description**: Research <specific question>
- **Key requirement**: Research output MUST be persisted to `{TASK_DIR}/research/`

[/Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Snow, Reasonix, Trae, Grok, Kimi Code]

[codex-inline, Kilo, Antigravity, Devin, DeepSeek Harness]

Do the research in the main session directly and write findings into `{TASK_DIR}/research/`. `codex-inline` is the explicit mode that keeps work in the main session.

[/codex-inline, Kilo, Antigravity, Devin, DeepSeek Harness]

**Research artifact conventions**:
- One file per research topic (e.g. `research/auth-library-comparison.md`)
- Record third-party library usage examples, API references, version constraints in files
- Note relevant spec file paths you discovered for later reference

Brainstorm and research can interleave freely — pause to research a technical question, then return to talk with the user.

**Key principle**: Research output must be written to files, not left only in the chat. Conversations get compacted; files don't.

#### 1.3 Configure context `[optional · once]`

[Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Snow, Reasonix, Trae, Grok, Kimi Code]

Curate `implement.jsonl` and `check.jsonl` so the Phase 2 sub-agents get the right spec/research context. They may be absent or contain a self-describing `_example` line. Add real entries only when curated references help the agent.

**Location**: optional `{TASK_DIR}/implement.jsonl` and `{TASK_DIR}/check.jsonl`.

**Format**: one JSON object per line — `{"file": "<path>", "reason": "<why>"}`. Paths are repo-root relative.

**What to put in**:
- **Spec files** — `.trellis/spec/<package>/<layer>/index.md` and any specific guideline files (`error-handling.md`, `conventions.md`, etc.) relevant to this task
- **Research files** — `{TASK_DIR}/research/*.md` that the sub-agent will need to consult

**What NOT to put in**:
- Code files (`src/**`, `packages/**/*.ts`, etc.) — those are read by the sub-agent during implementation, not pre-registered here
- Files you're about to modify — same reason

**Split between the two files**:
- `implement.jsonl` → specs + research the implement sub-agent needs to write code correctly
- `check.jsonl` → specs for the check sub-agent (quality guidelines, check conventions, same research if needed)

These manifests do not replace `implement.md`. `implement.md` is the human-readable execution plan for a complex task; jsonl files only list context files to inject or load.

**How to discover relevant specs**:

```bash
python ./.trellis/scripts/get_context.py --mode packages
```

Lists every package + its spec layers with paths. Pick the entries that match this task's domain.

**How to append entries**:

Either edit the jsonl file directly in your editor, or use:

```bash
python ./.trellis/scripts/task.py add-context "$TASK_DIR" implement "<path>" "<reason>"
python ./.trellis/scripts/task.py add-context "$TASK_DIR" check "<path>" "<reason>"
```

Delete the seed `_example` line once real entries exist (optional — it's skipped automatically by consumers).

Missing or seed-only manifests are valid. They add no curated references; agents must still load task artifacts and directly relevant specs. Existing real entries must point to readable, relevant files.

Skip this step when curated references add no value or the current entries are already sufficient.

[/Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Snow, Reasonix, Trae, Grok, Kimi Code]

[codex-inline, Kilo, Antigravity, Devin, DeepSeek Harness]

Skip this step. Context is loaded directly by the `trellis-before-dev` skill in Phase 2.

[/codex-inline, Kilo, Antigravity, Devin, DeepSeek Harness]

#### 1.4 Activate task `[required · once]`

After artifact review, flip the task status to `in_progress`:

```bash
python ./.trellis/scripts/task.py start <task-dir>
```

A PRD can be enough. Start when the next implementation is clear, authorized, and verifiable, with no blocking user-owned decision. Optional design, execution, and context manifests do not independently block activation. Preserve previously given authorization; do not ask for it again merely because the artifacts now exist.

After this command succeeds, the breadcrumb auto-switches to `[workflow-state:in_progress]`, and the rest of Phase 2 / 3 follows.

If `task.py start` errors with a session-identity message (no context key from hook input, `TRELLIS_CONTEXT_ID`, or platform-native session env), follow the hint in the error to set up session identity, then retry.

#### 1.5 Completion criteria

| Condition | Required |
|------|:---:|
| `prd.md` exists | ✅ |
| Implementation is authorized and blocking user decisions are resolved | ✅ |
| `task.py start` has been run (status = in_progress) | ✅ |
| `research/` has artifacts (complex tasks) | recommended |
| `design.md` clarifies material design decisions | when useful |
| `implement.md` clarifies sequencing or handoff | when useful |

[Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Snow, Reasonix, Trae, Grok, Kimi Code]

| Optional JSONL entries are accurate; agents can load artifacts/specs directly | ✅ |

[/Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Snow, Reasonix, Trae, Grok, Kimi Code]

---

## Phase 2: Execute

Goal: turn the task artifacts into a verified change, preserving platform-specific context and recovery behavior without forcing every task through the same review depth.

#### 2.1 Implement `[required · repeatable]`

Before editing, read `{TASK_DIR}/prd.md`, optional `design.md` / `implement.md`, and the relevant spec. Keep the change focused; do not add validators, manifests, reports, scans, approvals, or abstractions unless the task's real failure modes justify them.

[Claude Code, Cursor, OpenCode, codex-sub-agent, CodeBuddy, Droid, Pi, ZCode, Snow, Oh My Pi]

When delegation helps, spawn `trellis-implement`. The dispatch prompt starts with `Active task: <task path>` and then gives the bounded objective, starting baseline, protected shared state, expected result, and necessary checks. Production-code writers default to their own short-lived worktree and build directory; exact file ownership is not a launch prerequisite. Tell the spawned role it is already the implementer and must not recursively dispatch another implement/check role.

The platform hook/plugin supplies `prd.md`, optional design/implementation notes, and referenced `implement.jsonl` context. Native `SubagentStart` injection is preferred; child-side loading is the fallback when injection is unavailable or truncated.

[/Claude Code, Cursor, OpenCode, codex-sub-agent, CodeBuddy, Droid, Pi, ZCode, Snow, Oh My Pi]

[Gemini, Qoder, Copilot, Reasonix, Trae, Grok, Kimi Code]

When delegation helps, spawn the platform's implement/coder role with the same active-task, objective, baseline, protected-state, result, and check fields plus the shared worktree default. Pull-based agents resolve the active task, then read `prd.md`, optional `design.md` / `implement.md`, and every real `implement.jsonl` entry before coding. On Grok Build use `spawn_subagent`; on Kimi Code use the built-in `coder` / `explore` role with the matching Trellis instructions.

[/Gemini, Qoder, Copilot, Reasonix, Trae, Grok, Kimi Code]

[Kiro]

When delegation helps, spawn `trellis-implement` with the same bounded objective, baseline, expected-result and isolated-worktree contract. Kiro's platform prelude injects task artifacts and real `implement.jsonl` entries; the child implements directly and does not recursively dispatch implement/check.

[/Kiro]

[codex-inline, Kilo, Antigravity, Devin, DeepSeek Harness]

Load `trellis-before-dev`, read the task artifacts and relevant specs/research, implement directly, then run the project's affected lint/type/build checks.

[/codex-inline, Kilo, Antigravity, Devin, DeepSeek Harness]

Workers may form independently verifiable lane commits when repository authority allows. The main session remains responsible for candidate comparison, integration order, conflict resolution, user decisions, shared validation and final push. An interrupted worker is resumed when safe under the shared subagent recovery contract; replacement is not the automatic first response.

#### 2.2 Validate affected scope `[required · repeatable]`

Start with the cheapest check that can falsify the change, then run the relevant unit, integration, build, or scientific acceptance checks for the affected behavior. Record what ran; do not turn failure into a silent retry or degraded success.

[Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Snow, Reasonix, Trae, Grok, Kimi Code]

The implementer performs local self-checks and fixes findings. Use a separate `trellis-check` agent when the triggers in 2.3 apply or a clean independent pass has clear value. Its prompt starts with `Active task: <task path>` and names the affected contracts, baseline, expected result, and whether a specific writable scope is authorized. A shared-checkout or read-only reviewer reports findings without editing; direct fixes require explicit dispatch authorization plus the project's required worktree isolation and single-writer boundary. The reviewer does not recursively spawn implement/check.

The check role reads `check.jsonl` when present plus the task artifacts and owning specs. It fixes findings and reruns their checks only inside the authorized write boundary above; otherwise it returns the evidence to the main session.

[/Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Snow, Reasonix, Trae, Grok, Kimi Code]

[codex-inline, Kilo, Antigravity, Devin, DeepSeek Harness]

Run the affected checks directly. When 2.3 applies, load the `trellis-check` skill for an independent pass. Fix findings and re-run their checks until green or until a real blocker is reported.

[/codex-inline, Kilo, Antigravity, Devin, DeepSeek Harness]

Small/local changes do not require a whole-repository test merely because one exists. Use full-scope checks for releases, validation-infrastructure changes, broad refactors, genuinely unclear impact, or an explicit project acceptance contract. For multi-package work, list affected packages and read each affected package's Quality Check section; unrelated packages do not become gates.

#### 2.3 Independent review `[when evidence warrants]`

- Request independent review for scientific meaning, cross-module contracts, high-impact acceptance, or unresolved uncertainty. It is also reasonable when a second perspective is cheap and likely to reveal a different failure mode.
- Ordinary small changes may be author-checked. Independence means a separate problem formulation or clean context. A different model family is preferred when available and suitable, but it is not a qualification or completion gate.
- Review affected contracts and evidence, not every file by default. A reviewer may repair a finding only when the dispatch explicitly authorizes that writable scope and project isolation requirements hold; otherwise report it. If a finding changes requirements, return to Phase 1 before continuing.

#### 2.4 Rollback `[on demand]`

- `check` reveals a prd defect → return to Phase 1, fix `prd.md`, then redo 2.1
- Implementation went wrong → revert code, redo 2.1
- Need more research → research (same as Phase 1.2), write findings into `research/`

---

## Phase 3: Finish

Goal: ensure code quality, capture lessons, record the work.

#### 3.2 Debug retrospective `[on demand]`

If this task involved repeated debugging (the same issue was fixed multiple times), load the `trellis-break-loop` skill to:
- Classify the root cause
- Explain why earlier fixes failed
- Propose prevention

The goal is to capture debugging lessons so the same class of issue doesn't recur.

#### 3.3 Spec update `[when a stable contract changes]`

When the task establishes or changes reusable knowledge, load `trellis-update-spec` and update its smallest owning section:
- Newly discovered patterns or conventions
- Pitfalls you hit
- New technical decisions

No spec edit or separate skill invocation is needed when the existing contract remains sufficient. Keep one-off progress in task notes.

#### 3.4 Commit changes `[required · once]`

Review the completed task diff and check results before closeout. The current project's `AGENTS.md`, specs, and existing user authorization govern commits and external actions.

1. Inspect `git status --porcelain` and recent commit style.
2. Identify exactly the owned changes and group them into coherent commits. Preserve unrelated or parallel dirty work; do not silently include it.
3. If committing is already authorized, stage the exact files and commit without asking for the same approval again. If it is not authorized, present the concrete file grouping and ask once.
4. Respect explicit read-only, no-commit, or manual-closeout instructions. Do not amend or rewrite history without authorization.
5. Push, publication, release, and deployment require the applicable project contract and authorization. This generic workflow does not grant them or override a project's authorized closeout lifecycle.

If useful stable knowledge changed, update its owner under Phase 3.3 before committing; do not repeat that review when it is already complete.

#### 3.5 Wrap-up reminder

After the above, remind the user they can run `/finish-work` to wrap up (archive the task, record the session).

---

## Customizing Trellis (for forks)

This section is for developers who want to modify the Trellis workflow itself. Trellis-source spec paths below apply only to repositories that own those sources; ordinary consumers use their own owning specs. All customization is done by editing this file; the scripts are parsers only.

### Changing what a step means

Edit the corresponding step's walkthrough body in the Phase 1 / 2 / 3 sections above. Critical invariants:
- No active task must triage first and preserve existing authorization.
- Planning must resolve blocking decisions and use optional design, execution, and context artifacts only when useful.
- Every required execution path must keep the Phase 3.4 commit reminder reachable before `/trellis:finish-work`.

All tag blocks live in the `## Phase Index` section above, immediately after each phase summary:

| Scope | Corresponding tag |
|---|---|
| No active task (before Phase 1) | `[workflow-state:no_task]` (after the Phase Index ASCII art) |
| Active task record unreadable | `[workflow-state:task_error]` (repair the existing task before continuing) |
| All of Phase 1 (task created → ready for implementation) | `[workflow-state:planning]` (after Phase 1 summary) |
| Codex inline Phase 1 | `[workflow-state:planning-inline]` |
| Phase 2 + Phase 3.2–3.4 (implementation + check + wrap-up) | `[workflow-state:in_progress]` (after Phase 2 summary) |
| Codex inline Phase 2 + Phase 3.2–3.4 | `[workflow-state:in_progress-inline]` |
| After Phase 3.5 (archived) | `[workflow-state:completed]` (after Phase 3 summary; normally cleared by archive) |

### Changing the per-turn prompt text

Directly edit the body of the corresponding `[workflow-state:STATUS]` block. After editing, run `trellis update` (if you're a template maintainer) or restart your AI session (if you're customizing your own project) — no script changes required.

### Adding a custom status

Add a new block:

```
[workflow-state:my-status]
your per-turn prompt text
[/workflow-state:my-status]
```

Constraints:
- STATUS charset: `[A-Za-z0-9_-]+` (underscores and hyphens allowed, e.g. `in-review`, `blocked-by-team`)
- A lifecycle hook must write `task.json.status` to your custom value, otherwise the tag is never read
- Lifecycle hooks live in `task.json.hooks.after_*` and bind to one of `after_create / after_start / after_finish / after_archive`

### Adding a lifecycle hook

Add a `hooks` field to your `task.json`:

```json
{
  "hooks": {
    "after_finish": [
      "your-script-or-command-here"
    ]
  }
}
```

Supported events: `after_create / after_start / after_finish / after_archive`. Note that `after_finish` ≠ a status change (it only clears the active-task pointer); use `after_archive` for "task is done" notifications.

### Installed runtime contract

This generated project does not depend on Trellis monorepo-only specification or test paths. Its installed workflow-state contract is owned by these runtime sources:

- `.trellis/workflow.md` — state blocks, phase invariants, and customization contract
- `.trellis/scripts/task.py` — task lifecycle commands and status transitions
- `.trellis/scripts/common/task_store.py` — task creation/archive persistence
- `.trellis/scripts/common/active_task.py` — session pointers and pseudo-status resolution
- `.codex/hooks/inject-workflow-state.py` — Codex parser for the workflow state blocks
- `.claude/hooks/inject-workflow-state.py` — Claude parser for the workflow state blocks
