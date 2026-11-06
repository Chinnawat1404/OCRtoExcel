## Required return envelope

Each role returns:

- `status`: `PASS`, `PASS_WITH_LIMITATIONS`, `PASS_WITH_WARNINGS`, `FAIL`, or
  `BLOCKED`, as applicable to the phase
- `summary`
- `evidence`
- `files_read`
- `files_changed`
- `checks_run`
- `skipped_checks`
- `risks_or_warnings`
- `blockers`
- `recommended_next_action`

The coordinator verifies returned evidence against the repository before changing
state. Tester and Reviewer must evaluate the diff and check results rather than rely
on the Implementer's claims.
