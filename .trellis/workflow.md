# Development Workflow

---

## Core Principles

1. **Plan before code** — figure out what to do before you start
2. **Specs injected, not remembered** — guidelines are injected via hook/skill, not recalled from memory
3. **Persist what matters** — write decisions and evidence to files when reuse, handoff, or recovery benefits
4. **Incremental development** — one task at a time
5. **Capture durable learnings** — update the owning spec only when a task establishes reusable knowledge or a durable contract

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

Every task has its own directory under `.trellis/tasks/{MM-DD-name}/` holding `task.json`, `prd.md`, optional `design.md`, optional `implement.md`, optional `research/`, and optional context manifests (`implement.jsonl`, `check.jsonl`) when explicit sub-agent handoff is useful.

```bash
# Task lifecycle
python ./.trellis/scripts/task.py create "<title>" [--slug <name>] [--parent <dir>]
python ./.trellis/scripts/task.py start <name>          # set active task (session-scoped when available)
python ./.trellis/scripts/task.py current --source      # show active task and source
python ./.trellis/scripts/task.py finish                # clear active task (triggers after_finish hooks)
python ./.trellis/scripts/task.py archive <name>        # move to archive/{year-month}/
python ./.trellis/scripts/task.py list [--mine] [--status <s>]
python ./.trellis/scripts/task.py list-archive

# Code-spec context (injected into implement/check agents via JSONL).
# `implement.jsonl` / `check.jsonl` are created on demand by `add-context` or by
# direct editing only when a task benefits from explicit sub-agent context handoff.
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
python ./.trellis/scripts/get_context.py                            # full session runtime
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
    [workflow-state:completed]    → currently DEAD: cmd_archive flips
                                    status and moves the dir in the same
                                    call, so the resolver loses the
                                    pointer (block kept for a future
                                    explicit in_progress→completed
                                    transition)

  Editing checklist:
    - When you change a [workflow-state:STATUS] block, also check the
      matching phase's `[required · once]` walkthrough steps for sync
    - Run `trellis update` after editing to push the new bodies to
      downstream user projects (block-level managed replacement)
    - Installed runtime contract and sources:
      .trellis/workflow.md, .trellis/scripts/task.py,
      .trellis/scripts/common/task_store.py, .trellis/scripts/common/active_task.py,
      .codex/hooks/inject-workflow-state.py, .claude/hooks/inject-workflow-state.py
-->

## Phase Index

```
Phase 1: Plan    → classify, persist when useful, then write planning artifacts
Phase 2: Execute → implement only after task status is in_progress
Phase 3: Finish  → verify affected scope, capture durable knowledge when present, commit, and wrap up
```

### Request Triage

- Simple conversation, read-only review, or small task: continue inline when persistence would not help.
- Complex, multi-step, cross-session, release/install, production, or high-risk work: create a Trellis task directly and enter planning unless the user explicitly opts out.
- Ask the user only when scope, risk, or a required product decision is unclear; never ask solely to confirm task creation. Creating planning metadata does not broaden implementation authority.

### Planning Artifacts

- `prd.md` — requirements, constraints, and acceptance criteria. Do not put technical design or execution checklists here.
- `design.md` — optional technical design when boundaries, contracts, tradeoffs, or rollout need a durable explanation.
- `implement.md` — optional execution plan when ordering, coordination, validation, or rollback benefits from a checklist.
- `implement.jsonl` / `check.jsonl` — optional spec and research manifests for explicit sub-agent context handoff. They do not replace `implement.md`.
- A concise PRD is enough when it captures the goal and acceptance criteria. Add `design.md` or `implement.md` only when they materially improve execution or handoff.

### Parent / Child Task Trees

Use a parent task when one user request contains several independently verifiable deliverables. The parent task owns the source requirement set, the task map, cross-child acceptance criteria, and final integration review; it normally should not be the implementation target unless it also has direct work.

Use child tasks for deliverables that can be planned, implemented, checked, and archived independently. Parent/child structure is not a dependency system: if one child must wait for another, write that ordering in the child `prd.md` / `implement.md` and keep each child's acceptance criteria testable.

Create new children with `task.py create "<title>" --slug <name> --parent <parent-dir>`. Link existing tasks with `task.py add-subtask <parent> <child>`, and unlink mistakes with `task.py remove-subtask <parent> <child>`.

<!-- Per-turn breadcrumb: shown when there is no active task (before Phase 1) -->

[workflow-state:no_task]
No active task. First classify the current turn, then decide whether Trellis persistence is useful.
Simple conversation, read-only review, or small task: continue inline when persistence would not help.
Complex multi-step, release/install, production, cross-session, or high-risk work: create a Trellis task directly and enter planning unless the user explicitly opts out.
Ask the user only when scope, risk, or a required product decision is unclear; never ask solely to confirm task creation. Creating planning metadata does not broaden implementation authority.
[/workflow-state:no_task]

<!-- Per-turn breadcrumb: shown when the active task record cannot be read. -->

[workflow-state:task_error]
The active task record could not be read. Do not create or activate another task.
Inspect the task directory named above and repair its task.json. It must be a valid JSON object with a non-empty status.
Preserve existing task fields and artifacts. If the correct status cannot be determined safely, ask the user before reconstructing the record.
[/workflow-state:task_error]

### Phase 1: Plan
- 1.0 Create task `[required · once]` (when persistence is useful; no separate consent gate)
- 1.1 Clarify requirements `[when scope or product decisions are unclear]` (`prd.md`; add design or implementation notes when useful)
- 1.2 Research `[optional · repeatable]`
- 1.3 Configure context `[optional · repeatable]` — Claude Code, Cursor, OpenCode, Codex, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Snow, Reasonix, Grok, Kimi Code (sub-agent-dispatch platforms only; inline platforms skip)
- 1.4 Activate task `[required · once]` (after planning converges and implementation is authorized; status → in_progress)
- 1.5 Completion criteria

<!-- Per-turn breadcrumb: shown throughout Phase 1 (status='planning') -->

[workflow-state:planning]
If scope or a required product decision is unclear, load `trellis-brainstorm`; otherwise write the proportional planning artifacts and continue.
Keep the planning artifacts proportional to the work. A PRD can be enough; add design or implementation notes only when they improve decisions, coordination, validation, or recovery.
Multi-deliverable scope: consider a parent task plus independently verifiable child tasks; dependencies must be written in child artifacts, not implied by tree position.
Sub-agent mode: create or curate `implement.jsonl` and `check.jsonl` only when explicit context handoff is useful.
[/workflow-state:planning]

<!-- Per-turn breadcrumb: shown throughout Phase 1 when codex.dispatch_mode=inline.
     Codex-only opt-in alternate to [workflow-state:planning]. The main agent
     edits code directly in Phase 2, so jsonl curation is skipped —
     the inline workflow loads `trellis-before-dev` instead of injecting JSONL
     into a sub-agent. -->

[workflow-state:planning-inline]
If scope or a required product decision is unclear, load `trellis-brainstorm`; otherwise write the proportional planning artifacts and continue.
Keep the planning artifacts proportional to the work. A PRD can be enough; add design or implementation notes only when they improve decisions, coordination, validation, or recovery.
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
- 3.3 Spec update `[when durable knowledge exists]`
- 3.4 Commit changes `[required · once]`
- 3.5 Wrap-up reminder

<!-- Per-turn breadcrumb: shown while status='completed'.
     Currently DEAD in normal flow: cmd_archive writes status='completed' in
     the same call that moves the task dir to archive/, so the active-task
     resolver loses the pointer and the hook never fires on archived tasks.
     Block preserved for a future status-transition redesign (e.g. an
     explicit in_progress→completed command). Edit through the same spec
     channel as the live blocks. -->

[workflow-state:completed]
Code committed. Run `/trellis:finish-work`; if dirty, return to Phase 3.4 first.
[/workflow-state:completed]

### Rules

1. Identify which Phase you're in, then continue from the next step there
2. Run required steps in order; conditional steps are triggered by their stated evidence, not by ceremony
3. Phases can roll back (e.g., Execute reveals a prd defect → return to Plan to fix, then re-enter Execute)
4. Steps tagged `[once]` are skipped if the output already exists; don't re-run
5. Artifact presence informs the next step; missing optional `design.md` / `implement.md` is valid when the PRD is sufficient.

### Active Task Routing

When a user request matches one of these intents inside an active task, route first, then load the detailed phase step if needed.

[Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Snow, Reasonix, Trae, Grok, Kimi Code]

- Unclear requirements or unresolved product decisions -> `trellis-brainstorm`.
- `in_progress` implementation -> use `trellis-implement` when delegation helps; request `trellis-check` only when independent review is warranted.
- Repeated debugging -> `trellis-break-loop`; spec updates -> `trellis-update-spec`.

[/Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Snow, Reasonix, Trae, Grok, Kimi Code]

[codex-inline, Kilo, Antigravity, Devin, DeepSeek Harness]

- Unclear requirements or unresolved product decisions -> `trellis-brainstorm`.
- Before editing -> `trellis-before-dev`; after editing -> run affected checks and use `trellis-check` when independent review is warranted.
- Repeated debugging -> `trellis-break-loop`; spec updates -> `trellis-update-spec`.

[/codex-inline, Kilo, Antigravity, Devin, DeepSeek Harness]

### Guardrails

- Creating a task does not broaden implementation authority. When the user already authorized implementation and the final scope has not expanded, artifact review does not require a formal second approval.
- A PRD may be enough; use `design.md` and `implement.md` only when they improve execution or handoff.
- Planning must be persisted to task artifacts when a task exists; relevant checks must run before reporting completion.

### Loading Step Detail

At each step, run this to fetch detailed guidance:

```bash
python ./.trellis/scripts/get_context.py --mode phase --step <step>
# e.g. python ./.trellis/scripts/get_context.py --mode phase --step 1.1
```

---

## Phase 1: Plan

Goal: classify the request, persist non-trivial work when useful, and produce the planning artifacts required before implementation.

#### 1.0 Create task `[required · once]`

Create the task directory when persistence is useful; task creation itself needs no separate process approval. The command sets status to `planning`, writes `task.json`, creates a default `prd.md`, and auto-targets the new task when session identity is available:

```bash
python ./.trellis/scripts/task.py create "<task title>" --slug <name>
```

`--slug` is the human-readable name only. Do **not** include the `MM-DD-` date prefix; `task.py create` adds that prefix automatically.

For task trees, create the parent task first and then create each child with `--parent <parent-dir>`. Do not start the parent just because children exist; start the child that owns the next independently verifiable deliverable.

After this command succeeds, the per-turn breadcrumb auto-switches to `[workflow-state:planning]`, telling the AI to stay in planning.

Run only `create` here — do not also run `start`. `start` flips status to `in_progress`, which switches the breadcrumb to the implementation phase before planning artifacts are reviewed. Save `start` for step 1.4.

Skip when `python ./.trellis/scripts/task.py current --source` already points to a task.

#### 1.1 Clarify requirements `[when scope or product decisions are unclear]`

If the user's request already fixes the goal, scope, constraints, and acceptance criteria, record them in a concise `prd.md` and continue without a ceremonial question round.

Load the `trellis-brainstorm` skill only when requirements, tradeoffs, or a required product decision remain unclear. Use it to resolve the smallest useful set of questions, update the task artifacts as decisions arrive, and return here whenever requirements materially change.

During clarification, ask one high-value question at a time, prefer inspecting code or authoritative material over asking the user for discoverable facts, offer concrete options when they make tradeoffs easier to judge, and update `prd.md` promptly as decisions settle.

For independently verifiable deliverables, use a parent task only when the split improves ownership, validation, handoff, or recovery. Do not build a task tree merely because the request has several steps.

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

#### 1.3 Configure context `[optional · repeatable]`

[Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Snow, Reasonix, Trae, Grok, Kimi Code]

When explicit context handoff is useful, create or curate `implement.jsonl` and `check.jsonl` so Phase 2 sub-agents get the right spec/research context. Small or self-contained tasks omit these manifests.

**Location**: `{TASK_DIR}/implement.jsonl` and `{TASK_DIR}/check.jsonl` (created on first `add-context` use or by direct editing).

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

Do not create placeholder rows. Every manifest that exists should contain only real, relevant context entries.

When a manifest is used, every real entry must resolve to an existing relevant file. A seed-only manifest is treated as absent and does not block `task.py start`.

Skip this step when the task does not benefit from an explicit context manifest or when the needed manifests are already curated.

[/Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Snow, Reasonix, Trae, Grok, Kimi Code]

[codex-inline, Kilo, Antigravity, Devin, DeepSeek Harness]

Skip this step. Context is loaded directly by the `trellis-before-dev` skill in Phase 2.

[/codex-inline, Kilo, Antigravity, Devin, DeepSeek Harness]

#### 1.4 Activate task `[required · once]`

After planning converges and the current user authorization covers the final implementation scope, flip the task status to `in_progress` without requiring a formal second approval:

```bash
python ./.trellis/scripts/task.py start <task-dir>
```

A concise `prd.md` is sufficient when it captures the goal and acceptance criteria. Add `design.md`, `implement.md`, or JSONL context only when they materially improve decisions, coordination, validation, handoff, or recovery.

After this command succeeds, the breadcrumb auto-switches to `[workflow-state:in_progress]`, and the rest of Phase 2 / 3 follows.

If `task.py start` errors with a session-identity message (no context key from hook input, `TRELLIS_CONTEXT_ID`, or platform-native session env), follow the hint in the error to set up session identity, then retry.

#### 1.5 Completion criteria

| Condition | Required |
|------|:---:|
| `prd.md` exists | ✅ |
| Implementation is authorized and final scope has not expanded | ✅ |
| `task.py start` has been run (status = in_progress) | ✅ |
| `research/`, `design.md`, or `implement.md` exists | when useful |

[Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Snow, Reasonix, Trae, Grok, Kimi Code]

| Used JSONL manifests contain valid curated entries; otherwise they may be absent or seed-only | when used |

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

The implementer performs local self-checks and fixes findings. Use a separate `trellis-check` agent when the triggers in 2.3 apply or a clean independent pass has clear value. Its prompt starts with `Active task: <task path>` and names the affected contracts, baseline and expected result. A read-only reviewer may use the shared checkout; a reviewer authorized to change production code uses an isolated worktree and does not recursively spawn implement/check.

The check role reads `check.jsonl` when present plus the task artifacts, reviews against the owning specs, fixes scoped findings, and reruns the checks that cover those findings. If no independent review trigger applies, the main session can perform this affected-scope validation itself.

[/Claude Code, Cursor, OpenCode, codex-sub-agent, Kiro, Gemini, Qoder, CodeBuddy, Copilot, Droid, Pi, Oh My Pi, ZCode, Snow, Reasonix, Trae, Grok, Kimi Code]

[codex-inline, Kilo, Antigravity, Devin, DeepSeek Harness]

Run the affected checks directly. When 2.3 applies, load the `trellis-check` skill for an independent pass. Fix findings and re-run their checks until green or until a real blocker is reported.

[/codex-inline, Kilo, Antigravity, Devin, DeepSeek Harness]

Small/local changes do not require a whole-repository test merely because one exists. Use full-scope checks for releases, validation-infrastructure changes, broad refactors, genuinely unclear impact, or an explicit project acceptance contract. For multi-package work, list affected packages and read each affected package's Quality Check section; unrelated packages do not become gates.

#### 2.3 Independent review `[when evidence warrants]`

- Request independent review for scientific meaning, cross-module contracts, high-impact acceptance, or unresolved uncertainty. It is also reasonable when a second perspective is cheap and likely to reveal a different failure mode.
- Ordinary small changes may be author-checked. Independence means a separate problem formulation or clean context. A different model family is preferred when available and suitable, but it is not a qualification or completion gate.
- Review affected contracts and evidence, not every file by default. A reviewer may repair findings in scope; if a finding changes requirements, return to Phase 1 before continuing.

#### 2.4 Rollback `[on demand]`

- `check` reveals a prd defect → return to Phase 1, fix `prd.md`, then redo 2.1
- Implementation went wrong → revert code, redo 2.1
- Need more research → research (same as Phase 1.2), write findings into `research/`

---

## Phase 3: Finish

Goal: preserve useful evidence and finish the authorized change cleanly.

#### 3.2 Debug retrospective `[on demand]`

If this task involved repeated debugging (the same issue was fixed multiple times), load the `trellis-break-loop` skill to:
- Classify the root cause
- Explain why earlier fixes failed
- Propose prevention

The goal is to capture debugging lessons so the same class of issue doesn't recur.

#### 3.3 Spec update `[when durable knowledge exists]`

Update the owning spec only when the task produced reusable knowledge such as:
- Newly discovered patterns or conventions
- A recurring pitfall and its prevention
- A durable technical decision or acceptance boundary

Do not create a spec change merely to complete a workflow step. If no durable contract changed, continue without one.

#### 3.4 Commit changes `[required · once]`

The AI drives a batched commit of this task's code changes so `/finish-work` can run cleanly afterwards. Goal: produce work commits FIRST, then bookkeeping (archive + journal) commits land after — never interleaved.

**Step-by-step**:

1. **Inspect dirty state**:
   ```bash
   git status --porcelain
   ```
   Snapshot every dirty path. If the working tree is clean, skip to 3.5.

2. **Learn commit style** from recent history (so drafted messages blend in):
   ```bash
   git log --oneline -5
   ```
   Note the prefix convention (`feat:` / `fix:` / `chore:` / `docs:` ...), language (中文/English), and length style.

3. **Classify dirty files into two groups**:
   - **AI-edited this session** — files you wrote/edited via Edit/Write/Bash tool calls in this session. You know what changed and why.
   - **Unrecognized** — dirty files you did NOT touch this session (could be the user's manual edits, leftover WIP from a previous session, or unrelated work). Do NOT silently include these.

4. **Draft a commit plan**. Group AI-edited files into logical commits (1 commit per coherent change unit, not 1 commit per file). Each entry: `<commit message>` + file list. List unrecognized files separately at the bottom.

5. **Review authorization and ownership once**. Keep unrecognized dirty files outside the commit plan unless their ownership and inclusion are explicitly resolved.

If current user authorization and project rules already cover the task's commit and ordinary push, proceed without a formal second confirmation. Ask only when file ownership, final scope, repository visibility/upstream, or external effects remain unresolved.

6. **Commit within authority**: run `git add <files>` + `git commit -m "<msg>"` for each batch in order. Do not amend. After committing, use an ordinary push only when current authorization and project rules allow it, after rechecking the exact upstream, branch, visibility, and candidate SHA.

7. **Stop on unresolved authority**: if commit or push authorization, file ownership, or the exact remote target remains unclear, stop and hand off the reviewed plan instead of guessing or broadening scope.

**Rules**:
- No `git commit --amend` anywhere — three-stage three-commit flow (work commits → archive commit → journal commit).
- Never force-push, guess a remote, include unrecognized work, or exceed the current repository's commit/push contract.
- Ordinary commit and push authority follows current user instructions, project rules, repository visibility, and the shared authority-and-change-safety contract.
- When existing authorization covers the exact action, do not add a ceremonial confirmation prompt per commit or per push.

#### 3.5 Wrap-up reminder

After the above, remind the user they can run `/finish-work` to wrap up (archive the task, record the session).

---

## Customizing Trellis (for forks)

This section is for developers who want to modify the Trellis workflow itself. All customization is done by editing this file; the scripts are parsers only.

### Changing what a step means

Edit the corresponding step's walkthrough body in the Phase 1 / 2 / 3 sections above. Critical invariants:
- No active task must triage first; create Trellis persistence when useful without a separate process-approval gate.
- Planning artifacts must be proportional: a PRD can stand alone, while design and implementation notes are added only when useful.
- Every required execution path must validate affected behavior and keep the Phase 3.4 commit reminder reachable before `/trellis:finish-work`.

All tag blocks live in the `## Phase Index` section above, immediately after each phase summary:

| Scope | Corresponding tag |
|---|---|
| No active task (before Phase 1) | `[workflow-state:no_task]` (after the Phase Index ASCII art) |
| Active task record unreadable | `[workflow-state:task_error]` (repair the existing task before continuing) |
| All of Phase 1 (task created → ready for implementation) | `[workflow-state:planning]` (after Phase 1 summary) |
| Codex inline Phase 1 | `[workflow-state:planning-inline]` |
| Phase 2 + Phase 3.2–3.4 (implementation + check + wrap-up) | `[workflow-state:in_progress]` (after Phase 2 summary) |
| Codex inline Phase 2 + Phase 3.2–3.4 | `[workflow-state:in_progress-inline]` |
| After Phase 3.5 (archived) | `[workflow-state:completed]` (after Phase 3 summary; **currently DEAD**) |

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
