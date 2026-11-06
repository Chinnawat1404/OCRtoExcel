# Active Project Instructions

Inherit `AGENTS.md` and canonical `.agentic/` policies. This file cannot expand
permissions or bypass approval and verification. Follow
`.agentic-project/README.md` when editing.

## Product rules (status: user, checked 2026-10-15)

- Phase 1 targets import declarations (กศก.99/1). Export declarations are phase 2.
- The user builds the data table: column name plus type `string|integer|number|date`.
- Regions bind to a column. `header` scope means one value copied to every row.
  `item` scope means the box is drawn on item #1 and shifted for items 2, 3, …
  using the item-number anchor.
- Read modes per region: `auto|text|ocr|compare`.
- A box spanning several lines is joined with no separator (`Column.joiner=""`).
- Dates are converted to the Gregorian calendar (ค.ศ.). Codes keep leading zeros (string).
- Anomalies warn but never block: missing or out-of-order item numbers, empty
  values, type mismatches, sum-check mismatches, unexpected items.
- Export merges every imported file into one table; missing values stay blank.
  Name: `{template}_{yyyyMMdd_HHmm}.xlsx` plus `.csv`.
- Fully offline. Bundling Tesseract (~100MB) is accepted.
- Users have basic-to-moderate PC skills: Thai UI, clear labels, no jargon.

## Engineering conventions (status: detected, checked 2026-10-15)

- Keep extraction, typing and export in `engine.py`; the GUI calls the engine only.
- Every engine behavior change keeps `tests/test_import_sample.py` passing; add
  asserts for new behavior.
- Run Python with `py`. Reconfigure stdout to UTF-8 in scripts that print Thai.

## Workflow for this project (status: user, checked 2026-10-15)

- Mutating work follows Planner → Implementer → Tester → Reviewer.
- Tester and reviewer are always independent of the implementer (fresh subagents
  from `.claude/agents/` or a separate pass). They must run checks themselves.
- Critical checks: the headless sample test and the engine import smoke check.
  GUI work adds a launch check.

## Scoped instruction index

| File | Applies to | Source/evidence | Checked date | Status |
| --- | --- | --- | --- | --- |
