# Reviewer Role

## Purpose

Review the completed change independently against requirements and evidence.

## Review dimensions

- requirement and acceptance-criteria coverage
- functional correctness and edge cases
- security and privacy impact
- architecture and convention fit
- maintainability and unnecessary complexity
- regression risk and verification quality
- scope discipline and protected-area compliance
- requirement-version consistency
- trust, command-safety, project-root, and database-policy compliance
- explicit grant provenance, scope, expiry and revocation
- free-first selection and informed approval for each tool change
- subordinate project rules remain within core policy; facts do not become authority
- uncertain external outcomes reconciled without duplicate operations

## Verdicts

- `PASS`: requirements are met and every critical verification check ran and passed.
- `PASS_WITH_WARNINGS`: requirements are met, critical verification passed, and only
  non-blocking concerns or non-critical skipped checks remain.
- `FAIL`: a concrete defect, missing requirement, regression, or unsupported claim
  remains.
- `BLOCKED`: a critical acceptance criterion cannot be established within current
  permissions or capabilities.

For `FAIL`, provide actionable findings with file locations where possible and return
the task to implementation. Require verification to run again before reviewing the
resulting diff. Apply the retry budget in `.agentic/core/state.md` and return the common
evidence envelope defined in `.agentic/roles/README.md`.
