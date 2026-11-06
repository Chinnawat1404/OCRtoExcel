# Closed-Loop Agentic Workflow

Use this lifecycle for every request. Scale detail to task risk and size while keeping
all material gates and evidence requirements.

At session startup apply `.agentic/core/startup.md` before source edits, including
when the user directly requests a fix. Startup reports do not replace the lifecycle
or create an extra approval gate.

## 1. Classify the request

- `READ_ONLY`: explain, inspect, diagnose, review, or report status.
- `CHANGE`: modify existing behavior or documentation.
- `CREATE`: scaffold a new project or major component.
- `BUG_FIX`: reproduce and correct unintended behavior.
- `REFACTOR`: change structure while preserving behavior.
- `MIGRATION`: change a public interface, platform, dependency family, schema, or
  persistent format.
- `EXTERNAL_ACTION`: deploy, publish, message, purchase, or mutate an external system.

`READ_ONLY` tasks may proceed without initialization and must not alter repository or
state files. Every mutating type uses the full workflow. Migrations and external
actions always require explicit scope and applicable approval.

## 2. Recover or start task state

Follow `.agentic/core/state.md`.

- Reconcile any active local state with the actual repository before resuming.
- For a new mutating task, create `.agentic/local/current-task.md` from the template,
  assign a task ID, and set status to `DISCOVERING`.
- Capture the initial version-control status and existing changes. Never overwrite or
  claim unrelated user changes.

## 3. Discover safely

Follow `.agentic/core/discovery.md`, `.agentic/core/trust.md`, and
`.agentic/core/command-safety.md`. Read documentation and configuration before relevant
source files. Record only verified durable facts in `.agentic-project/project-context.md` and
do not overwrite user-confirmed values with inference.

All phases follow default project confinement and database isolation, with exceptions
only through explicit scoped grants in `.agentic/core/permissions.md`. Load relevant
`.agentic-project/` instructions and check capability gaps under
`.agentic/core/capabilities.md`. Do not rewrite the core during ordinary project work.
For an empty project, treat technology and operational choices as requirements.

For `BUG_FIX`, capture expected behavior, actual behavior, and reproducible evidence
before changing code when reproduction is safe and permitted. For `REFACTOR`, identify
the behavior that must remain unchanged. For `MIGRATION`, identify compatibility and
rollback requirements.

## 4. Pass the Requirement Gate

Apply `.agentic/core/requirements.md`.

- Resolve explicit information from the current request.
- Resolve technical facts through safe repository inspection.
- Ask only for missing information that can materially change the outcome.
- Group related questions and offer recommendations when helpful.
- Do not invent business rules or treat silence as acceptance.

Set `REQUIREMENTS_NEEDED` while blocked on a user decision. Set `READY_TO_PLAN` only
when the gate returns `READY`.

## 5. Plan and preflight

Follow `.agentic/roles/planner.md` and then preflight planned commands with
`.agentic/core/command-safety.md`.

- Set status to `PLANNING`.
- Map every acceptance criterion to an implementation step and verification method.
- Label each verification method `CRITICAL` or `NON_CRITICAL`.
- Identify file ownership, approval points, risks, rollback needs, and unavailable
  checks before editing. Resolve tool gaps using `.agentic/core/capabilities.md`.
- Before external mutations or recovery, load `.agentic/core/external-actions.md` and plan
  authorization, a reviewable payload and reconciliation of uncertain outcomes.
- Present the plan when broad, risky, irreversible, or dependent on a user decision.

Set `READY_FOR_IMPLEMENTATION` only when the plan is actionable and applicable
approvals are available.

## 6. Implement

Follow `.agentic/roles/implementer.md` and set `IMPLEMENTING`.

- Implement one coherent step at a time.
- Inspect the diff after each meaningful step and keep it within accepted scope.
- If a material requirement gap appears, increment the requirement version, set
  `REQUIREMENTS_NEEDED`, and return to the Active Task Gate.
- If the user changes requirements, follow steering rules in `.agentic/core/state.md`.

After implementation, proceed to verification. Do not self-declare completion.

## 7. Verify

Follow `.agentic/roles/tester.md` and set `VERIFYING`.

- `PASS`: every critical check ran and passed; proceed to review.
- `PASS_WITH_LIMITATIONS`: implementation evidence passed, but only non-critical checks
  were skipped; proceed to review with recorded limitations.
- `FAIL`: record reproducible evidence, increment the verification attempt, and return
  to `IMPLEMENTING`.
- `BLOCKED`: a critical acceptance criterion cannot be verified within permissions or
  available capabilities; stop and request the missing decision or capability.

A database-dependent or outside-project check without a matching valid grant is
skipped. If it is critical and no permitted equivalent exists, verification is
`BLOCKED`, never `PASS`. Continue independent permitted work while approval is pending.

## 8. Review

Follow `.agentic/roles/reviewer.md` and set `REVIEWING`. Review the actual diff,
requirements version, scope, and verification evidence.

- `PASS`: requirements are met and all critical verification passed; set `DONE`.
- `PASS_WITH_WARNINGS`: requirements are met, critical verification passed, and only
  non-blocking risks or non-critical verification limitations remain; set `DONE`.
- `FAIL`: record actionable findings, increment the review attempt, and return to
  `IMPLEMENTING`.
- `BLOCKED`: correctness or acceptance cannot be established within current
  permissions; stop for user direction.

After any verification or review failure, the full repair path is:

```text
IMPLEMENTING -> VERIFYING -> REVIEWING
```

Never skip re-verification after a repair. Apply the three-cycle retry budget from
`.agentic/core/state.md` for repeated failures with the same root cause.

## 9. Handoff and feedback

Report the outcome, important changed files, checks actually run, skipped checks,
review verdict, and unresolved warnings. Do not require the user to read internal
state files.

- If the user accepts the result, leave the task `DONE`.
- If the user reports a defect or unmet accepted criterion, reopen the same task at
  `REQUIREMENTS_NEEDED` or `IMPLEMENTING` as appropriate.
- If the user requests a new outcome, create a new task after resolving how it relates
  to any active task.

## State transitions

```text
IDLE -> DISCOVERING -> REQUIREMENTS_NEEDED -> READY_TO_PLAN
     -> PLANNING -> READY_FOR_IMPLEMENTATION -> IMPLEMENTING
     -> VERIFYING -> REVIEWING -> DONE

VERIFYING --FAIL--> IMPLEMENTING
REVIEWING --FAIL--> IMPLEMENTING
ANY ACTIVE STATE --missing decision/capability--> BLOCKED
ANY ACTIVE STATE --user cancels--> CANCELLED
BLOCKED --resolved--> last valid gate or phase
DONE --accepted defect--> REQUIREMENTS_NEEDED or IMPLEMENTING
```
