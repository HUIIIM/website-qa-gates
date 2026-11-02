# Loop state — website-qa-gates

Updated: 2026-11-02 (v1.5.0 gate set, `claude/sota-roadmap`). Facts here are the standing state;
when one changes, the PR that changes it updates this file.

## Direction channel

- Tasks: GitHub Issues labeled `jarvis-task` in this repo.
- Reviews and verdicts: PR comments only.
- Merge owner: Jarvis. External Claude opens PRs from `claude/*` branches.

## Decisions in force

- The gate set is the pre-publish standard for the website line; changes
  here propagate to that line's release checklist.
- Gate set v1.5.0: 34 gates (G16 axe WCAG added; the
  G5 mechanics are now automated; G2/G3/G9/A4/M4/T5 run in a real browser).
  **Pending propagation**: the
  website line's release checklist has not been updated to v1.5.0 yet.
- Gates that have not fired on a real defect are labelled hypotheses in
  `references/gate-checklist.md` ("Gate evidence status").
- Gate thresholds and site-specific rules live in `qa-gates.config.json`.

## Acceptance rules

- CI green on the current head before merge.
- Before pushing: `ruff check tools tests`, `python3 -m mypy`,
  `python3 tools/trace-matrix.py --check`, `python3 -m unittest discover -s tests`.
