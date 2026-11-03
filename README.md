# website-qa-gates

A vertciti skill for pre-release QA of website changes: it returns per-gate pass / fail verdicts with
evidence, an 11-dimension weighted score with a grade, and a remediation record when a release falls below
grade A, for teams that ship changes to a marketing or product site.

中文版：[README.zh.md](README.zh.md)

| | |
|---|---|
| Status | active · early, single maintainer — v1.5.0 (version from [SKILL.md](SKILL.md)); CI runs ruff, mypy, the traceability check, the unit tests (including real-browser gates) and the demo gates on every pull request and push to `main`; local run on 2026-11-02: 20 pass, 0 fail, 14 of 34 gates `waived` (they need manual review or external materials) |
| Type | vertciti skill (agent skill defined in [SKILL.md](SKILL.md) / [SKILL.zh.md](SKILL.zh.md)) with a Python gate runner ([`tools/ledger-run.py`](tools/ledger-run.py)) and real-browser gates ([`tools/browser/gates.cjs`](tools/browser/gates.cjs), Playwright + axe-core) |
| Install / use | Load `SKILL.md` as a skill in your agent; run the gates locally with `bash demo/run.sh` |
| Licence | MIT ([LICENSE](LICENSE)) for this repository's own code and docs, Copyright (c) 2026 Jiahui Miao · `demo/www/dna.css` is proprietary to VERTCITY LLC and the fonts are SIL OFL — see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) |
| Languages | README and SKILL in English and 简体中文 · checklists and demo pages in 简体中文 · runner output in either (`--lang zh\|en`) |
| Contact | Security: [SECURITY.md](SECURITY.md) · Product: [vertciti.com](https://vertciti.com) |

## Overview

Manual QA before a website release tends to end with someone looking at the page and saying it is fine.
website-qa-gates replaces that with a gate list: each gate has a pass criterion and must cite evidence, and
any FAIL blocks the release. Gates that cannot be verified by machine are marked `waived` with the reason;
a waived gate is reported, never counted as a pass. A gate that crashes is a FAIL, not a waiver.

Every run is appended to a local `coverage-ledger.json` (a runtime file, git-ignored; path configurable with
`QA_GATES_LEDGER`). Runs, dispositions and scores form one hash chain, so a rewritten verdict is detected by
`tools/ledger-verify.py`.

Product one-pager: [docs/PRODUCT.md](docs/PRODUCT.md) · Changelog: [CHANGELOG.md](CHANGELOG.md) ·
Gate-to-test map: [docs/TRACEABILITY.md](docs/TRACEABILITY.md)

## Capabilities

| Output | What it contains | Produced by |
|---|---|---|
| Gate verdicts | 34 gates. 13 static machine gates, 7 real-browser gates (touch targets, 390px overflow, render under production CSP, keyboard and focus ring, reduced motion, single-line CTAs, axe WCAG 2.2 AA in light and dark), V4, and 13 gates that need a person | `tools/ledger-run.py` |
| Evidence | Command and output per gate; screenshots at 1440 and 390 px and axe JSON per page | `tools/browser/gates.cjs` |
| 11-dimension score | Weighted 100-point model read from `references/scorecard-v1.yaml`; N/A dimensions leave the denominator. Grades: S ≥95 · A++ ≥90 · A ≥85 · B ≥70 · C <70 | `tools/score.py` |
| Remediation record | Filed for any gate FAIL (P0), total <70 (P0), any dimension <70 (P1) or total <85 (P1), with an owner and a default 24-hour deadline | `tools/score.py` |
| Disposition | Open, fix, re-check; closing needs a second person | `tools/ledger-dispose.py` |

```
Input: change brief (what changed, viewports affected, materials)
  -> tools/ledger-run.py: static gates + real-browser gates -> evidence -> PASS / FAIL / waived
  -> manual gates per references/gate-checklist.md
  -> tools/score.py: 11-dimension score -> grade -> remediation records
  -> tools/ledger-dispose.py: open -> fix -> re-check (two people to close)
  -> tools/ledger-verify.py: hash chain intact; copy the head somewhere outside the ledger
```

Missing materials (spec, screenshots, source paths) reduce the scope of the check and are disclosed; they
never become a silent pass.

## Quick start

```bash
git clone https://github.com/HUIIIM/website-qa-gates && cd website-qa-gates
npm ci --prefix tools/browser && npx --prefix tools/browser playwright install chromium   # real-browser gates
bash demo/run.sh    # serves demo/www/ locally and runs every gate; exit 0 = no FAIL, 2 = at least one FAIL
bash demo/eval.sh   # PASS when the run was recorded, sealed and had zero FAIL
python3 -m unittest discover -s tests -v   # regression tests (browser tests skip if Playwright is missing)
```

Without Playwright the browser gates are recorded as `waived`; set `QA_GATES_REQUIRE_BROWSER=1` to make that
a FAIL, as CI does. `demo/run.sh` writes to a temporary directory that it deletes on exit; set
`QA_GATES_LEDGER` and `QA_GATES_EVIDENCE_DIR` to keep the ledger and screenshots. See
[`demo/README.md`](demo/README.md), including how to inject a defect and watch a gate fail.

To use it on your own site, copy [`qa-gates.config.json`](qa-gates.config.json) (the vertciti settings),
change the thresholds and site-specific rules, and point `QA_GATES_CONFIG` at your copy.

## Repository layout

```
SKILL.md / SKILL.zh.md   the skill (English / Chinese): gates, scoring model, filing rules
qa-gates.config.json     vertciti gate settings (thresholds, site URL, extra secret rules, excluded files)
tools/ledger-run.py      gate runner (no shell; fails closed; ledger writes locked, atomic and sealed)
tools/browser/           real-browser gates (Playwright + axe-core, exact versions in package-lock.json)
tools/score.py           11-dimension score, grade and remediation records
tools/ledger-dispose.py  disposition records (two people to close)
tools/ledger-verify.py   hash-chain check; prints the head for external anchoring
tools/trace-matrix.py    gate-to-test matrix (docs/TRACEABILITY.md), checked in CI
tests/                   unit tests for every machine gate (pass and fail), ledger, scoring
demo/www/                test pages, the vendored DNA stylesheet and fonts
references/              gate-checklist.md, scorecard-v1.yaml, ledger schema and supporting checklists
evals/                   dry-run records smoke-01 to smoke-08, injection-01
```

## Status and limitations

- 14 of the 34 gates still need a person or external material: G6, G13, M2, M3, A3, T3, T4, V1–V3,
  G12-2, G12-3, plus M1, for which the runner takes the screenshots but a person judges them.
- Machine verdicts cover only the criteria written in [`references/gate-checklist.md`](references/gate-checklist.md).
  For example G16 runs axe-core, which finds only part of WCAG; G5 compares numbers and structure, not meaning.
- Most gates have fired only on defects injected by tests, so they are labelled hypotheses; see "Gate evidence
  status" in the checklist.
- Performance is measured as bytes (G4), not as LCP, CLS or INP on a real device.
- The vendored `dna.css` breaks this repository's own A1, A2 and G12-1 rules. It is excluded from those gates by
  `qa-gates.config.json`, and every run says so in its evidence. The fix belongs upstream in HUIIIM/.github.
- The run ledger is a local file. Nothing anchors its head outside the machine automatically; do that by hand
  (for example in the release PR description).
- The agent-level prompt-injection evaluation (`evals/injection-01.md`) has not been run yet.

## Security

See [SECURITY.md](SECURITY.md). A gate that passes a defect counts as a vulnerability. CI runs gitleaks secret
scanning and OpenSSF Scorecard.

## Contributing

Issues and pull requests are welcome. Gate changes need a worked dry-run in `evals/` and tests in `tests/` tagged
with the gate (`[G15:fail]`), including at least one pass case and one fail case. Before pushing:

```bash
ruff check tools tests && python3 -m mypy && python3 tools/trace-matrix.py --check && python3 -m unittest discover -s tests
```

## Licence

MIT — see [LICENSE](LICENSE). Copyright (c) 2026 Jiahui Miao. The MIT licence does not cover `demo/www/dna.css`
(proprietary to VERTCITY LLC, vendored unmodified from [HUIIIM/.github](https://github.com/HUIIIM/.github)
`design/dist/dna.css`) or the Nunito Sans fonts in `demo/www/fonts/` (SIL Open Font License,
[OFL.txt](demo/www/fonts/OFL.txt)). Details: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Built by vertciti — https://vertciti.com
