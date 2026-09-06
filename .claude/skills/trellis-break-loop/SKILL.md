---
name: trellis-break-loop
description: "Investigate repeated failed fixes or an unclear root cause. Use decisive evidence to explain the cause and choose useful prevention; update specs only for new reusable knowledge."
---

# Break the Loop - Bug Analysis

Use after repeated failed fixes, an unclear root cause, or a failure whose lesson would change future work.

## Find the Cause

Explain the observed failure and the evidence connecting it to the cause. If earlier fixes failed, identify the assumption or missed path that explains why. Missing contracts, change propagation, test gaps, and implicit assumptions are useful prompts; do not fill every category by default.

When several causes remain plausible, compare what each predicts and run the smallest check that distinguishes them. State uncertainty honestly. Numeric probabilities are optional and need evidence; do not invent priors or use fixed confidence thresholds to authorize a fix.

## Choose Useful Prevention

Consider whether the fix, an affected behavior regression, a clearer boundary, or a short owner-spec update would prevent recurrence. Follow adjacent occurrences only when evidence suggests the same cause. Avoid turning one bug into a broad refactor or a permanent checklist without a demonstrated benefit.

Record the cause, decisive evidence, fix, remaining uncertainty, and useful follow-up in the task when they matter for continuation. A short explanation can be sufficient.

## Capture and Close Out

Update the smallest owning spec only when a stable reusable contract or lesson is new or changed. Reuse existing sections and link evidence; no spec edit is a valid result when the existing rule is already sufficient.

Template synchronization applies only when this repository actually maintains distributable template sources and the affected file has a documented generated counterpart. Follow that repository's source and generator contract; ordinary Trellis consumers do not copy their private specs into Trellis templates.

Commit and external actions follow the current project's workflow and existing user authorization. This skill does not itself authorize a commit, push, publication, or unrelated change.
