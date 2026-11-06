# Requirement Gates

Requirements exist at two levels: stable project initialization and the active task.
The user remains the authority for product behavior and business rules.

## Resolution states

- `missing`: no reliable value is available.
- `detected`: verified from repository evidence.
- `user`: stated or explicitly accepted by the user.
- `ai_recommended_user_accepted`: proposed by the AI and accepted by the user.

An AI recommendation alone remains `missing` until accepted when it concerns business
behavior, scope, protected areas, or an irreversible choice.

## Project Initialization Gate

Before the first source-changing task, resolve applicable stable fields below.
Documentation-only maintenance uses the Active Task Gate without requiring application
initialization. For a small, reversible source change, resolve the facts material to
that change; unrelated initialization fields may remain `missing`. Do not mark global
initialization `READY` until all applicable project fields resolve.

| Field | Required | Resolution rule |
| --- | --- | --- |
| Project name | Yes | Detect or ask |
| Project purpose | Yes | Detect from authoritative docs or ask |
| Technology | Yes | Detect for existing projects; ask for new projects |
| Project instructions and constraints | Yes | Inherit explicit instructions; ask only for material gaps; `none` is valid |
| Definition of Done | Yes | Use explicit outcome and checks; ask when a recommendation adds material scope |
| Protected areas | Yes | Inherit explicit policy; ask when ambiguity affects the planned change; do not infer wider access |
| Build/test commands | When applicable | Detect or ask if needed for verification |
| Compatibility targets | When applicable | Detect or ask when versions/platforms matter |
| Non-functional constraints | When applicable | Ask only when security, privacy, accessibility, performance, localization, or compliance can change the result |

When fields are missing:

1. Inspect first so the user is not asked for detectable facts.
2. Present detected values separately from recommendations.
3. Ask for all closely related missing fields in one concise request when possible.
4. Save accepted values in `.agentic-project/project-context.md`.
5. Set initialization to `READY` only when every applicable required field resolves.

Read-only tasks do not require initialization and must not silently initialize the
project.

## Active Task Gate

Before implementing each task, resolve:

| Field | Required | Notes |
| --- | --- | --- |
| Goal or requested outcome | Yes | Often supplied by the current request |
| Task type | Yes | Classify using `.agentic/core/workflow.md` |
| In-scope area | Yes | May be inferred when unambiguous |
| Out-of-scope area | When material | Prevent accidental expansion |
| Acceptance criteria | Yes | Recommend concise criteria if absent |
| Constraints and protected areas | Yes | Inherit stable project context and task overrides |
| Verification approach | Yes | Use detected commands when available |
| Verification criticality | Yes | Mark each check `CRITICAL` or `NON_CRITICAL` |
| Expected and actual behavior | For bug fixes | Reproduce safely when permitted |
| Compatibility and rollback | For migrations | Require before irreversible change |
| External or irreversible actions | If applicable | Require explicit authorization |

The gate returns:

- `READY`: implementation may begin.
- `REQUIREMENTS_NEEDED`: ask a focused question before affected work.
- `BLOCKED`: a required decision or capability is unavailable.

Do not use the gate to delay read-only inspection or routine reversible work whose
requirements are already clear from the request and project context.

## Requirement changes

Assign each active task a requirement version starting at `1`. When the user changes
the goal, scope, acceptance criteria, constraints, or protected areas:

1. increment the version
2. mark affected plan steps and verification evidence stale
3. preserve unaffected work
4. rerun the Active Task Gate
5. continue only after the revised gate is `READY`

## Proportionate questions and technical decisions

- Inspect detectable facts before asking. Separate evidence, technical assumptions
  and user-confirmed decisions.
- Decide reversible implementation details within clear scope using established
  project conventions. Record material assumptions; do not ask for every detail.
- Ask before unresolved business behavior, expanded scope, protected access, cost
  or irreversible choices. Group related questions and offer a recommendation.
- Prior explicit answers remain valid in unchanged scope. Silence is never approval.
- Continue independent work while waiting; pause only work dependent on the answer.
- Tool changes always use the informed per-change approval in
  `.agentic/core/capabilities.md`, even when a technical choice would otherwise be routine.
- Record whether initialization is `READY`, task-scoped, or not applicable and why.
  Task-scoped readiness does not authorize unrelated work or expand permissions.
