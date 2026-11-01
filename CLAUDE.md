# website-qa-gates

A published skill package: the website QA gate system — per-gate
pass/fail checks with evidence, an 11-dimension weighted score, and the
release gate used before any website change ships. Public, bilingual
editions.

## How work happens here

- Direction arrives in-repo: GitHub Issues labeled `jarvis-task`, PR
  review comments, and `CLAUDE.md` / `LOOP.md`. Read both at session start.
- External Claude works on `claude/*` branches and opens PRs; it never
  merges its own PRs. Jarvis reviews and merges.
- Review verdicts exist only as PR comments.

## Working rules

- Bilingual parity is a publish gate: SKILL.md / SKILL.zh.md and
  README.md / README.zh.md ship together, sections aligned.
- Gate definitions change only with evidence from a real run; a gate
  that has never fired on a real defect is a hypothesis, labeled as such.
