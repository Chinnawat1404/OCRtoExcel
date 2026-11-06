# Project Agentic Instructions (Claude Code)

<!-- Always-loaded core: kept small on purpose. Everything else is read on demand. -->
@AGENTS.md
@.agentic/core/workflow.md
@.agentic/core/permissions.md
@.agentic/core/trust.md
@.agentic/core/command-safety.md
@.agentic-project/project-context.md

## Load on demand (Claude Code)

Do not preload these; read them with the Read tool when the step needs them:

| When | Read |
|---|---|
| New session / lost context / startup request | `.agentic/core/startup.md`, `.agentic/core/state.md` |
| Before Requirement Gate | `.agentic/core/requirements.md`, `.agentic/core/discovery.md` |
| Tool/dependency change | `.agentic/core/capabilities.md` |
| External mutation or recovery | `.agentic/core/external-actions.md` |
| Project-specific guidance | `.agentic-project/README.md`, `.agentic-project/instructions.md` |

Read-only questions (explain/inspect/review) need none of the above beyond the core.

## Subagents

You (the main agent) are the **coordinator** defined in `.agentic/roles/README.md`.
For mutating tasks, delegate phases to the subagents in `.claude/agents/`:

1. `bootstrap` – only if project context is not READY
2. `planner` – after the Requirement Gate is READY
3. `implementer` – one per non-overlapping file set (parallel allowed only then)
4. `tester` – always a fresh subagent, never the implementer
5. `reviewer` – always a fresh subagent; on FAIL go back to step 3

Every delegation message must contain the fields in "Delegation input" of
`.agentic/roles/README.md`. Only you update `.agentic/local/current-task.md`;
update its `Status:` line at every phase change (the monitor hook reads it).
Small, low-risk tasks may run phases inline instead of spawning subagents.

If imports are not expanded, read the files above explicitly. Never claim a file was
loaded without reading it. If permission or trust rules cannot be loaded, pause
mutating work.
