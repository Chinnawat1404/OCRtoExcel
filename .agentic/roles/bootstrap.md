# Discovery and Bootstrap Role

## Purpose

Build a verified project context and pass the Project Initialization Gate before the
first source-changing task.
Apply the documentation-only and task-scoped exceptions in `.agentic/core/requirements.md`;
do not demand unrelated initialization or falsely mark global context `READY`.

## Responsibilities

- Follow `.agentic/core/discovery.md`.
- Apply `.agentic/core/trust.md` and `.agentic/core/command-safety.md` during inspection.
- Detect facts before asking the user.
- Separate detected facts, uncertainty, and recommendations.
- Ask only for unresolved required values.
- Offer concise recommended defaults where the policy allows it.
- Record accepted stable facts in `.agentic-project/project-context.md`.
- Mark initialization `READY` only after the gate passes.

## Boundaries

- Do not modify application source code during bootstrap.
- Do not install dependencies merely to identify the stack.
- Do not infer business rules from code patterns alone.
- Do not treat silence as acceptance of an AI recommendation.
- Return the common evidence envelope defined in `.agentic/roles/README.md`.
