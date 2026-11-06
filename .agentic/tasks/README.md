# Optional Task History

This directory is reserved for redacted final task records when the user explicitly
enables task history in `.agentic-project/project-context.md`.

- Do not store active task state here.
- Do not archive secrets, credentials, raw logs, or private user data.
- Use one stable file per task: `<task-id>.md`.
- Use `.agentic/templates/task-template.md` as the record shape.
- When history is disabled, leave this directory unchanged.
