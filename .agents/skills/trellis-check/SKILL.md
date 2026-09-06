---
name: trellis-check
description: "Review affected behavior against task requirements and relevant specs, run required project checks, and fix local findings only within an explicitly authorized isolated write scope."
---

# Code Quality Check

Review affected behavior against task requirements, relevant specs, and proportionate evidence.

---

## Step 1: Identify What Changed

```bash
git diff --name-only HEAD
git status
```

## Step 2: Read Task Artifacts and Applicable Specs

Read the current task artifacts in order:

- `prd.md`
- `design.md` if present
- `implement.md` if present

```bash
python ./.trellis/scripts/get_context.py --mode packages
```

For each changed package/layer, read the spec index and follow its **Quality Check** section:

```bash
cat .trellis/spec/<package>/<layer>/index.md
```

Read the specific guideline files referenced — the index is a pointer, not the goal.

## Step 3: Run Project Checks

Run the affected checks required by the project: these may be tests, builds, lint, type checks, document validation, or a direct behavior probe. Select commands from current project configuration and specs; do not assume every repository has lint or typecheck. Report failures and unavailable checks accurately.

## Step 4: Review Against Checklist

Apply only the checks relevant to this change and required by the project. Report the reason when an applicable check is skipped or unavailable; the checklist does not introduce extra lint, typecheck, or test requirements.

### Code Quality

- [ ] Linter passes?
- [ ] Type checker passes (if applicable)?
- [ ] Tests pass?
- [ ] No debug logging left in?
- [ ] No suppressed warnings or type-safety bypasses?

### Test Coverage

- [ ] Do checks exercise the changed behavior and material failure modes?
- [ ] Would a regression test detect the original bug, rather than mirror implementation details?
- [ ] Is existing evidence sufficient, or does a boundary change need an additional check?

### Spec Sync

- [ ] Does `.trellis/spec/` need updates? (new patterns, conventions, lessons learned)

> "If I fixed a bug or discovered something non-obvious, should I document it so future me won't hit the same issue?" → If YES, update the relevant spec doc.

### Scope Discipline

- [ ] Any tidying of code the task did not require?
- [ ] Any abstraction, config or extension point added for a case that does not exist yet?
- [ ] Any speculative fallback for a state that cannot occur?
- [ ] Any file changed that the acceptance criteria do not mention?
- [ ] Any workaround added at the caller instead of a fix where the behavior actually lives?

## Step 5: Cross-Layer Dimensions (if applicable)

Skip this step if your change is confined to a single layer.

### A. Data Flow (changes cross a contract boundary)

- [ ] Read flow traces correctly: Storage → Service → API → UI
- [ ] Write flow traces correctly: UI → API → Service → Storage
- [ ] Types/schemas correctly passed between layers?
- [ ] Errors properly propagated to caller?

### B. Code Reuse (modifying constants, creating utilities)

- [ ] Searched for existing similar code before creating new?
  ```bash
  rg "pattern" <affected-path>
  ```
- [ ] If the same value repeats, does it represent one stable concept whose callers must change together? Extract only then — two literals that merely happen to match today should stay separate.
- [ ] After batch modification, all occurrences updated?

### C. Import/Dependency (creating new files)

- [ ] Correct import paths (relative vs absolute)?
- [ ] No circular dependencies?

### D. Same-Layer Consistency

- [ ] Other places using the same concept are consistent?

---

## Step 6: Report and Fix

Report every violation you find. Then:

- Read-only review → report findings without editing, even if write tools are available.
- Mechanical and local fix within an explicitly authorized, isolated write scope → fix in place, then re-run affected checks. Preserve other writers' changes.
- Design changes, unclear ownership, or edits beyond the authorized scope → record evidence and a recommendation for the owning session; do not silently expand the review.

If a fix would touch files outside the current task's scope, say so and stop instead of widening the change.
