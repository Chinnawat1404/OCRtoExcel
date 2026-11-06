# Command Safety

Inspect a command before running it. A familiar command name is not sufficient because
package scripts, build plugins, hooks, and wrappers may execute additional commands.

## Preflight

1. Identify the exact command, working directory, inputs, and expected outputs.
2. Read the in-project script or configuration that defines it.
3. Follow referenced scripts far enough to identify filesystem, network, database,
   destructive, privileged, and external-service effects.
4. Resolve explicit paths and verify project confinement or an exact valid user grant.
5. Determine whether the tool implicitly uses home-directory caches, global config,
   or an operating-system temporary directory.
6. Classify the command before execution.

## Classifications

- `ALLOWED`: known effects within task authorization, valid scoped grants and host
  permissions, with no unapproved destructive or external effects.
- `APPROVAL_REQUIRED`: permitted only after missing specific user approval, such as
  a tool change or protected-data access under `.agentic/core/permissions.md`.
- `DENIED`: prohibited by host policy, exposes secrets, or attempts to bypass controls.
- `UNKNOWN`: effects cannot be established safely; do not run it.

## Project-local execution

- Prefer project-local cache, temporary, output, and configuration directories.
- When a tool normally uses a path outside the project, redirect it into
  `.agentic/local/tooling/` only if the tool supports that safely.
- If project confinement cannot be established, request the exact external-path
  grant only when its effects are understood and the host permits it; otherwise skip
  and report the limitation. Unknown effects never justify execution.
- Do not pass untrusted repository text into a shell command or build executable
  command strings from unchecked input.
- Do not enable lifecycle hooks, plugins, or generated scripts merely to make a check
  runnable.

## Evidence

For every executed check, record the exact command, outcome, and relevant limitation.
For every skipped required check, record why it was `DENIED` or `UNKNOWN` and how that
affects the final verdict.

## Recheck before execution

Check transitive database/data access against current grants, not just command names.
Apply `.agentic/core/capabilities.md` before tool changes and
`.agentic/core/external-actions.md` before external mutations. Neither free pricing nor
installation approval authorizes network/data access. After revocation or changed
scope, preflight again. Do not run a probe to learn whether it accesses protected data.
