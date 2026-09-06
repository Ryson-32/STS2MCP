---
name: trellis-brainstorm
description: "Clarify unresolved product or scope decisions and record a proportionate Trellis plan before implementation. Use when material user decisions remain, preserving authorization already given."
---

# Trellis Brainstorm

Clarify unresolved requirements and keep a proportionate plan under the active task. The current project's `.trellis/workflow.md` owns task creation and phase routing.

## Authorization and Questions

A clear request to build, implement, fix, refactor, or continue authorizes that work within its stated scope. Preserve authorization already given; do not require another reply merely because planning artifacts were written or a session resumed.

Inspect code, tests, configuration, current docs, and relevant task evidence before asking questions. Ask only for an unresolved user-owned decision that materially changes the outcome, scope, compatibility, acceptance, or external effects. Explain the decision, your recommendation, and its trade-off. Continue independent authorized work while that answer is pending; do not guess the dependent decision.

## Planning Flow

1. Reuse the active task when it owns the requested work. If a task is needed, follow the project workflow and create it with a non-empty title and description:
   ```bash
   python ./.trellis/scripts/task.py create "<short title>" --description "<one-line summary>" --slug <slug>
   ```
   The command adds the date prefix; do not include it in the slug.
2. Record the goal, requirements, constraints, and observable acceptance criteria in `prd.md`.
3. Inspect the actual producer, consumers, failure modes, and existing checks. Resolve repository-answerable questions directly.
4. Add `design.md` only when design decisions need durable explanation. Add `implement.md` only when sequencing, parallel ownership, or a long handoff benefits from it. Complexity alone does not require three documents.
5. Use `implement.jsonl` / `check.jsonl` when curated context helps a dispatched agent. Missing or seed-only manifests are valid; agents still read the task artifacts and relevant specs directly. Existing real entries must remain accurate.
6. Run the requirement convergence gate, then the PRD convergence pass.
7. Give a short planning summary and proceed to `task.py start` when the work is authorized and no blocking user decision remains. If authorization is absent or scope materially expands beyond it, obtain the missing decision first.

Use parent/child tasks when deliverables can be verified independently. Record actual ordering explicitly; tree position alone does not establish a dependency. Preserve project-specific scientific evidence, publication, and external-action boundaries.

## Requirement Convergence Gate

Before starting, confirm the outcome, scope, constraints, and acceptance behavior are clear enough for the next implementation step. Research material technical unknowns, or record their bounded uncertainty without claiming they are resolved. Do not invent a question just to satisfy a planning ritual.

For a long continuing plan, keep a concise current goal, next unresolved question, remaining boundaries, and evidence links. Preserve useful history and update the summary as work progresses.

## PRD Convergence Pass

Review the PRD for contradictions, duplication, and lost decisions. Edit only where that review reveals a problem; do not rewrite a sound document solely to pass a gate.

- Fold temporary brainstorm sections such as `What I already know`, `Assumptions`, and resolved `Open Questions` into their owning sections when it improves clarity.
- Preserve every file:line anchor, decision, constraint, requirement ID, and acceptance-criteria mapping.
- Keep unresolved questions explicit and distinguish a blocker from a deferred follow-up.
- Check for no unresolved temporary brainstorm sections, no duplicate facts across sections that add no information, and no lost evidence.

A brief PRD can be enough. Planning is ready when the next work is clear, authorized, and verifiable; file counts and a fresh approval reply are not readiness evidence.
