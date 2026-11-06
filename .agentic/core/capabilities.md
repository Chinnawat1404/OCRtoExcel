# Capability Discovery and Tool Changes

Use tools actually available in the host. Do not assume terminal, editing, network,
installation, browser or subagent support. Do not install merely to inventory tools.

## When a capability is missing

1. Identify the affected acceptance criterion and missing capability.
2. Safely inspect available tools and relevant in-project configuration.
3. Prefer an existing suitable tool or an allowed alternative with equivalent evidence.
4. Investigate suitable free options first. Prefer free options that meet the
   requirement. Consider paid options only when no suitable free option is available;
   explain the relevant free alternatives and why they cannot meet the need.
   Do not claim an exhaustive search without evidence.
5. Before EVERY proposed addition, activation, removal or substantial upgrade of a
   tool, plugin, connector, dependency or service, disclose the details below and ask
   the user to approve that specific change. Free tools also require approval.
6. After approval use supported host setup mechanisms. If the host cannot do it,
   provide precise setup steps for the user and continue independent permitted work.
7. Verify availability/version safely. Authentication or protected-data checks need
   their own grants. Installed does not necessarily mean usable.
8. If declined or unavailable, use an allowed equivalent if one exists. Keep critical
   verification `BLOCKED` otherwise; do not silently lower acceptance criteria.

## Informed approval and pricing

Include purpose, publisher/source, version when applicable, intended change,
installation location, permissions, data sent/retained, removal/recovery method,
pricing source and date checked. Verify pricing from official sources when permitted.
If unavailable, label cost `UNKNOWN`; do not call it free or activate a potentially
billable service until resolved.

Use labels `FREE`, `FREE_TIER`, `TRIAL`, `PAID`, or `UNKNOWN`. Explain quotas,
expiry, card requirements, automatic billing, usage charges and relevant hosting
costs. A trial is not permanently free. Open-source licensing does not imply free
operation. Do not enable overage billing or start paid work without explicit cost
approval and an agreed limit. Stop before exceeding approved limits. Changed cost
or scope requires renewed approval.

Approval remains valid for the exact disclosed change; do not ask again for every
installation substep. Broad intent such as "add whatever is needed" does not waive
disclosure and approval for each new tool change. Ordinary use of an already
approved tool within its scope does not require repeated setup approval.
Buying/subscribing and protected-data access need explicit authorization.

Record only non-secret capability facts, source/date and limitations in
`.agentic-project/knowledge.md` during authorized mutating work. Keep redacted
approval references in local task state. Neither file grants permissions or proves
availability in a later session. Never bypass host restrictions using another tool.
