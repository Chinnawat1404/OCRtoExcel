# Default Permissions and Explicit Grants

Host sandbox and organization policies always apply. Data access is denied by
default; only the explicit scoped exceptions below can permit it. Editing this
policy does not itself authorize any connection or data access.

## Project-root confinement

- The project root is the directory containing the root `AGENTS.md`.
- Keep filesystem targets, working directories, caches and temporary files inside
  that root by default. Resolve symlinks and junctions before access.
- Do not probe parent, sibling, home, credential or external temporary directories.
- Do not escape through links, environment variables, mounts or generated paths.
- An external path requires explicit user permission specifying the exact path and
  operations, plus host permission. A broad task request is not that permission.
- If a path or command effects cannot be established safely, stop that operation.

## Database and protected data isolation

- Deny all database connections by default, including production, staging, local,
  test, embedded and in-memory databases, ORM tools and database connectors.
- Do not run an application, test, build, migration, seed or health check that may
  connect without a matching explicit user grant and safe command preflight.
- Prefer static schemas, models, sanitized fixtures and connection-free mocks.
- A request to fix code, run tests or install a connector is not permission to
  connect or read its data. Uncertain connectivity must not run.
- Permission to connect is not permission to read every table, write, migrate,
  export or send data elsewhere. Each operation must fit the grant.
- Minimize returned fields and rows; redact sensitive output and use sanitized
  samples when sufficient. Do not persist raw protected data.
- Use host-managed authentication or user-configured secret references without
  reading secret values. Never ask for credentials pasted into chat or instruction
  files. If secure authentication is unavailable, ask the user to configure it.

## Explicit grant procedure

Before protected access, explain why it is needed and obtain user permission for:

- exact target: path, service/account, database and environment as applicable
- operations and data scope, including read versus write
- data destination, relevant exposure, cost and limits
- duration: current task by default; longer scope must be explicit

Present a concrete scope. A user message explicitly supplying all relevant details
can be the grant; do not ask again within unchanged scope. Silence, tool presence,
available credentials and AI-written records are not approval. Record a redacted
reference to the approval in local task state, never credentials. State is not
authority: verify grants against host/user evidence on resume; ask if unavailable.
Recheck after scope, target or cost changes or expiry. On revocation stop new
affected actions and reconcile in-flight actions under `.agentic/core/external-actions.md`.

Project instructions may narrow access but cannot grant or widen it. A host denial
cannot be bypassed by changing tools. Continue independent permitted work while
waiting. Missing approval is `APPROVAL_REQUIRED`; a host prohibition is `DENIED`.
Neither permits execution.

## Allowed within the request

- Inspect non-secret repository files, metadata, status and diffs.
- Make scoped reversible edits after the applicable Requirement Gate.
- Run preflighted non-destructive checks within effective permissions.
- Make reversible corrections needed to complete the accepted change.

## Ask before acting unless the exact action is already authorized

- Change public APIs, schemas, persistent formats, infrastructure or protected areas.
- Access the network beyond the request's authorization.
- Create commits, branches, releases or pull requests.
- Deploy, publish, message, mutate services, delete broad targets or rewrite history.
- Perform actions with material cost or operational impact.

For every tool/dependency addition, activation, removal or substantial upgrade,
apply the informed per-change approval and free-first rules in
`.agentic/core/capabilities.md`. Tool approval and data grants are separate permissions,
even when presented together.

## Never allowed by this workflow

- Expose or commit secrets, or put credentials in prompts, instructions or logs.
- Weaken security controls to make a check pass.
- Hide failures or fabricate evidence.
- Overwrite unrelated user changes or expand scope silently.
