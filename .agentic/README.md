# Agentic Instruction Pack

This directory is the canonical, tool-neutral source of the project's Agentic
workflow. Root-level and vendor-specific instruction files should point here instead
of duplicating the workflow.

## Folders

- `core/`: shared workflow and safety policies
- `guides/`: user-facing getting-started instructions and copyable prompts
- `roles/`: phase responsibilities
- `templates/`: blank record formats, copied when needed
- `evals/`: behavioral evaluation scenarios
- `tasks/`: optional redacted task history
- `local/`: ignored execution state and local evidence
- `../.agentic-project/`: project-specific instructions, knowledge and context

## Files

- `core/startup.md`: session loading and visible readiness checkpoint
- `guides/getting-started.md`: Thai startup, task and resume prompts
- `core/workflow.md`: task lifecycle and state transitions
- `core/discovery.md`: language-agnostic repository inspection
- `core/trust.md`: trusted instruction sources and prompt-injection handling
- `core/command-safety.md`: command preflight and execution classification
- `../.agentic-project/project-context.md`: durable, verified project facts
- `core/requirements.md`: initialization and per-task Requirement Gates
- `core/permissions.md`: default data isolation and explicit scoped user grants
- `core/capabilities.md`: tool discovery, free-first selection and informed approval
- `core/external-actions.md`: safe submission and reconciliation of uncertain outcomes
- `core/state.md`: local state, recovery, steering, and history policy
- `roles/`: responsibilities for each workflow phase
- `local/current-task.md`: optional gitignored active-task checkpoint
- `templates/`: reusable records for requirements and tasks
- `evals/scenarios.md`: behavior scenarios for validating the pack

## Maintenance

- Store stable, verified project facts in `../.agentic-project/project-context.md`.
- Store the active task only in the gitignored `local/current-task.md`.
- Do not store secrets, access tokens, or credentials anywhere in `.agentic/`.
- Keep instructions concise and remove conflicts when project rules change.
- Keep editable project guidance in `.agentic-project/`, subordinate to the core.
- Core policy changes require an explicitly authorized instruction-maintenance task;
  context, knowledge, fixtures and local state never grant permissions.
