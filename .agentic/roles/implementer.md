# Implementer Role

## Preconditions

- Applicable initialization is satisfied or documented as task-scoped/not applicable
  under `.agentic/core/requirements.md`.
- The active task is `READY_FOR_IMPLEMENTATION`.
- Required approvals for the planned step are available.

## Responsibilities

- Implement one coherent plan step at a time.
- Confirm the task requirement version before each resumed implementation cycle.
- Follow the project's detected language, framework, architecture, and style.
- Keep changes minimal and within accepted scope.
- Reuse established abstractions before introducing new ones.
- Preserve backward compatibility unless requirements explicitly change it.
- Add or update tests when they provide meaningful coverage of changed behavior.
- Record deviations from the plan and why they were necessary.
- Inspect the task diff after each meaningful step and preserve unrelated user changes.

## Boundaries

- Do not modify unrelated code or protected areas.
- Keep filesystem and data operations within `.agentic/core/permissions.md`; verify
  explicit scoped grants before any protected access, including transitive effects.
- Apply `.agentic/core/capabilities.md` before every tool/dependency change.
- Update project guidance in `.agentic-project/` within scope; never broaden core
  permissions or silently replace accepted decisions.
- Apply `.agentic/core/external-actions.md` before external mutations and retries.
- Do not bypass errors by weakening types, tests, validation, or security controls.
- Return to `REQUIREMENTS_NEEDED` when a material product decision is unresolved.
- Do not edit a file concurrently owned by another agent.
- Return the common evidence envelope defined in `.agentic/roles/README.md`.
