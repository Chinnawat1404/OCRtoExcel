# Task State, Recovery, and Steering

Mutable execution state belongs in `.agentic/local/current-task.md`, which is ignored
by version control. Use `.agentic/templates/current-task.md` to create it when a
mutating task begins. Read-only tasks must not create or update local state.

## State ownership

- Only the coordinator changes task status, requirements version, retry counters, or
  final verdict.
- Subagents return evidence to the coordinator and do not edit the state file.
- Update state at phase boundaries and before yielding for a user decision.
- State is a checkpoint, not proof. Repository contents and actual diffs remain the
  source of truth.

## Startup and recovery

At the start of a session:

1. Read local state if it exists.
2. If status is `IDLE`, `DONE`, or `CANCELLED`, treat the next mutating request as a
   new task.
3. For any active status, inspect the current repository state and diff before
   resuming.
4. Reconcile recorded changed files and completed checks with evidence still present.
5. Resume from `Next action` only when state and repository agree.
6. If they conflict materially, set `BLOCKED` and ask the user whether to recover,
   restart, or abandon the task without discarding user work.

## Steering

- If the user clarifies without changing the outcome, update the task record and
  continue.
- If requirements, scope, acceptance criteria, or protected areas change, increment
  `Requirement version`, invalidate affected plan and verification results, and return
  to the Active Task Gate.
- If a new request arrives while a task is active, determine whether it replaces,
  extends, or is independent of the active task. Ask only when the distinction changes
  the result materially.
- On cancellation, stop new work, preserve existing user changes, record the last safe
  checkpoint, set `CANCELLED`, and report what remains.

## Retry budget

Track implementation, verification, and review attempts. After three failed repair
cycles for the same root cause, set `BLOCKED`; report the repeated evidence and request
the decision or capability needed to continue. A materially different failure starts
a new root-cause count but does not erase prior evidence.

## History

Task history is disabled by default to avoid repository noise. If the user explicitly
enables auditable history, copy a redacted final task record to
`.agentic/tasks/<task-id>.md`. Never archive secrets, raw logs, or transient tool
output.

## Grants, external operations and unavailable persistence

Record redacted approval references and their target, operations, limits and expiry;
verify them against user/host evidence before use, especially on resume. Records
cannot authorize access. Reconcile external operations under
`.agentic/core/external-actions.md` before retry; unknown outcomes block dependent work.

If local state cannot be written, do not redirect it outside the project or pretend
it was saved. Maintain a concise in-session checkpoint and disclose that automatic
cross-session recovery is unavailable. Continue reversible authorized work when
safe; block work requiring durable receipts or recovery evidence. Ask for an allowed
persistence capability only when needed. On read-only requests do not write state.
