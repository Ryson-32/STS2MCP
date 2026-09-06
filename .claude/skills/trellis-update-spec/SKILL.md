---
name: trellis-update-spec
description: "Update the smallest owning spec when a stable reusable contract or convention is established or changed. Preserve concrete evidence and reuse existing sections."
---

# Update the Owning Spec

Use when implementation, debugging, or discussion establishes or changes a stable reusable contract. The goal is a clear current owner that helps future work.

## Decide What Belongs

Read the affected spec and current implementation first. Record new boundaries, interface or data invariants, error semantics, conventions, or a non-obvious lesson that changes how future work should proceed. Keep one-off progress and historical evidence in the task. If the existing spec is sufficient, report that briefly and make no edit.

Follow the project's actual package/layer structure. A guide routes thinking across concerns; an owning spec explains the concrete contract. Avoid repeating the same rule in both.

## Make the Smallest Useful Update

1. Identify the contract, why it matters, and its owner.
2. Edit the existing section where possible. Include signatures, fields, errors, and validation evidence when they are relevant to the changed behavior.
3. Add examples only when they clarify a meaningful boundary or common mistake. A small field change need not introduce a new scenario document.
4. Update an index only when navigation or ownership changes.
5. Check that links, claims, and commands match the implementation and the evidence available.

For a complex new interface, scope, signatures, contracts, error cases, examples, and assertion points can help organize the explanation. These are optional prompts, not a mandatory seven-section recipe; use only what the reader needs. Preserve real project requirements for scientific, database, API, infrastructure, and compatibility evidence.

## Verification and Ownership

Review the final diff for accuracy, duplication, and scope. Run checks appropriate to the changed document or contract. Do not invent test results or turn an untested example into a verified guarantee.

Synchronize generated copies only through a documented owner/generator in a repository that actually maintains those templates. Preserve project-private rules and local customizations. Commit and publication remain governed by the current workflow and existing authorization.

Related: /trellis:break-loop investigates recurring failures; /trellis:finish-work closes out verified task work.
