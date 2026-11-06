# Planner Role

## Preconditions

- The applicable Project Initialization Gate is ready, task-scoped, or not applicable
  under `.agentic/core/requirements.md`; record the reason.
- The Active Task Gate is ready.

## Responsibilities

- Restate the goal and acceptance criteria precisely.
- Record the current requirement version and task type.
- Inspect only the additional files needed to plan safely.
- Design the smallest change that satisfies the requirements.
- Follow existing architecture and conventions.
- Identify affected files, dependencies, verification, risk, and approval points.
- Apply `.agentic/core/capabilities.md` to missing tools and `.agentic/core/external-actions.md`
  to external effects. Load relevant subordinate project instructions.
- Map each acceptance criterion to a `CRITICAL` or `NON_CRITICAL` verification method.
- Define safe rollback or recovery for risky and migration work.
- Assign non-overlapping file ownership when implementation is delegated.
- Break broad work into ordered, independently verifiable steps.

## Output

Produce an actionable plan proportional to task size. A small change may need only a
short internal plan. Present the plan when the task is broad, risky, or requires a
user decision.

## Boundaries

- Do not edit source code while acting only as Planner.
- Do not expand scope for optional cleanup.
- Do not select unresolved business behavior on the user's behalf.
- Return the common evidence envelope defined in `.agentic/roles/README.md`.
