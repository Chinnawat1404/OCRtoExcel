# External Actions and Uncertain Results

Before external mutation, verify user authorization for the exact target, operation,
payload, data access and cost under `.agentic/core/permissions.md`. Prepare a reviewable
result before requesting missing approval. A preview/dry run is allowed only when
its effects are known and authorized.

Before submission record a redacted operation description, target, approval reference
and reconciliation method. Use an idempotency key when supported and preserve it for
the same operation. Record a non-secret operation/request ID and status:
`PREPARED`, `SUBMITTED`, `CONFIRMED`, `FAILED`, or `OUTCOME_UNKNOWN`.

On timeout, disconnect, interrupted submission or cancellation, do not assume failure
and do not blindly resubmit. Set `OUTCOME_UNKNOWN`; check status using the operation
ID or a narrowly scoped lookup only when authorized. Confirmed success must not be
repeated. Retry only if non-execution is established or a verified idempotency
guarantee makes the retry safe, and authorization still applies. Otherwise block
dependent work and ask for reconciliation.

The three-cycle code repair budget never authorizes repeating external actions.
Revocation stops new operations, including unauthorized lookups. Report unresolved
in-flight effects; do not assume cancellation rolled them back. Compensation needs
its own authorization and verified target and may not fully reverse the effect.

Keep receipts and approval references in local state without secrets or raw sensitive
payloads. Reconcile on resume before retry. Report unknown outcomes explicitly; never
claim completion or failure without evidence.
