# website-qa-gates

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.2.1-blue.svg)](SKILL.md)

**A website is the company's proof of caliber. This skill runs the pre-release gauntlet: per-gate pass/fail verdicts with evidence, an 11-dimension weighted score with a grade, and automatic issue filing when it falls below A-grade — so nothing ships on "looks fine to me."**

[Quick start](#30-second-quick-start) · [What it delivers](#what-it-delivers) · [Demo](#demo) · [FAQ](#faq)

A [Vertciti Skill Pack](https://vertciti.com) for pre-release quality gates on website changes. One change description in, three things out.

Built for [Miao](https://vertciti.com) (Jiahui Miao) — N=1 founder IP infrastructure.

## The real problem it solves

Manual QA before a website release drifts into vibes: somebody eyeballs it, says fine, and the launch carries a broken footer on mobile or an orphaned CTA that leads nowhere. website-qa-gates replaces the eyeball with a gate list — each gate has a pass criterion and must cite evidence. Browser-dependent gates that can't be machine-verified are honestly marked `waived`, never faked into a pass.

## What it delivers

Three things per website change:

1. **Gate verdicts** — G1–G9 + G14 release gates + 4 motion-specific gates, each PASS / FAIL / conditional with evidence. Any FAIL blocks release.
2. **11-dimension score** — Weighted 100-point model (real-browser verification 18, visual craft 12, CTA closure 12, perf budget 12, …). Grades: S ≥95 / A++ ≥90 / A ≥85 / B ≥70 / C <70.
3. **Auto-filing** — Below A-grade (or any gate FAIL) automatically files a remediation record with owner and 24h deadline.

## 30-second quick start

```bash
cd demo
bash run.sh
# Runs the real gate runner against a test page (~30s)
```

See `demo/README.md` for details. Machine-runnable gates execute for real; browser-dependent gates are honestly marked `waived` (never faked).

## Demo

`bash run.sh` runs the real gate runner (`tools/ledger-run.py`) against a test page — machine gates execute, evidence is written, and the run is appended to `coverage-ledger.json`. Six real dry-run records ship in `evals/` (smoke-01 through smoke-06); a recent production run (`dryrun-2026-10-06-h4`, against the live deploy root) is in the ledger.

> Walkthrough video/screenshot of a gate run producing its verdicts: 待补（占位）——run records above are already real and evidence-backed.

## When to use it

| Scenario | What it produces |
|---|---|
| Homepage hero changed | Gate verdicts + score before anything goes live |
| Mobile (390px) footer restyle | Contrast + touch-target gates, per-item inspection |
| New animation added | 4 motion-specific gates (no black first frames, no autoplay traps) |
| A release scored B | Auto-filed remediation with owner + 24h deadline |

## Repo layout

```
website-qa-gates/
  SKILL.md              # the skill itself: gates, scoring model, filing rules
  demo/                 # runnable test page + run.sh → coverage-ledger.json
  tools/ledger-run.py   # the real gate runner
  references/           # gate-checklist.md, scorecard-v1.yaml (machine-readable)
  evals/                # six real dry-run records (smoke-01..06)
  coverage-ledger.json  # additive ledger of real runs
```

## Input

One change brief, containing:

- **What changed**: e.g. "homepage hero adds a numbers-evidence bar: four numbers + source citations"
- **Viewports affected**: desktop / mobile (390px) / both
- **Materials**: change note, spec, screenshots/recordings, source paths (if missing, the check degrades and says so)

## Structure

```
Input: change brief
  ↓  G1–G9 release gates (each: run → evidence → PASS/FAIL)
  ↓  G14 + 4 motion-specific gates
  ↓  11-dimension weighted score → grade
  ↓  Below A or any FAIL → auto-filed remediation (owner + 24h deadline)
  ↓  Ledger append (coverage-ledger.json, additive)
```

## Honesty contract

- Gates that cannot be executed machine-side are marked `waived` with the reason — a waived gate is not a pass.
- Missing materials degrade the check and are disclosed; they never silently become a pass.
- Every dry-run record is additive in `coverage-ledger.json` (real runs, e.g. `dryrun-2026-10-06-h4`); the ledger is the scoreboard.

## References

- `references/gate-checklist.md` — Per-gate execution methods and pass criteria.
- `references/scorecard-v1.yaml` — Machine-readable scoring model.
- `evals/` — Six real dry-run records (smoke-01 through smoke-06), each with evidence.
- `tools/ledger-run.py` — Gate runner used in the demos.

## Roadmap

- Real-browser gate automation for the currently `waived` gates (Playwright, evidence-captured).
- A-grade trend dashboard from the additive ledger.
- Motion-gate library expansion as the site's animation vocabulary grows.

## FAQ

**What happens if I don't have materials (screenshots, specs)?**
The check degrades and says so. Missing materials are disclosed as a scope reduction — they never silently become a pass.

**Does a `waived` gate mean the release is blocked?**
No — waived means "could not be machine-verified, honestly disclosed." It stays visible in the verdict so a human knows what still needs eyes.

**Why auto-file on below-A instead of just warning?**
Because warnings get scrolled past. A filed record with an owner and a 24h deadline is a closed loop; a warning is a hope.

**Can this run against a staging URL instead of a local page?**
The gate runner works against a site root or URL; browser-dependent gates need a real browser session. The demo uses a test page so it runs anywhere in ~30s.

## Contributing

Issues and PRs welcome. Gate changes need a worked dry-run in `evals/` plus a `coverage-ledger.json` entry — paper proposals without a run don't merge.

## License

| Module | License | Plain meaning |
|---|---|---|
| All files | MIT | Commercial use OK, modify OK, attribution required |

See [LICENSE](LICENSE).

## Author

**Jiahui Miao** — Founder, [vertciti](https://vertciti.com). Building procurement infrastructure for AI agents. Participates in 3GPP working on 6G core network standards.
