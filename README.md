# website-qa-gates

A vertciti skill for pre-release QA of website changes: it returns per-gate pass / fail verdicts with
evidence, an 11-dimension weighted score with a grade, and a remediation record when a release falls below
grade A, for teams that ship changes to a marketing or product site.

| | |
|---|---|
| Status | active · early, single maintainer — v1.4.0 (version from [SKILL.md](SKILL.md)); CI runs ruff, the unit tests in `tests/` and the demo gates on every pull request and push to `main`; local run on 2026-10-26: 12 pass, 0 fail, 21 of 33 gates `waived` (they need a real browser, manual review or external materials) |
| Type | vertciti skill (agent skill defined in [SKILL.md](SKILL.md)) with a Python gate runner ([`tools/ledger-run.py`](tools/ledger-run.py)) |
| Install / use | Load `SKILL.md` as a skill in your agent; run the gates locally with `bash demo/run.sh` |
| Licence | MIT ([LICENSE](LICENSE)), Copyright (c) 2026 Jiahui Miao · bundled Nunito Sans fonts under the SIL OFL ([fonts/OFL.txt](fonts/OFL.txt)) |
| Languages | README in English · skill text, checklists and demo pages in 简体中文 |
| Contact | Security: see [Security](#security) · Product: [vertciti.com](https://vertciti.com) |

## Overview

Manual QA before a website release tends to end with someone looking at the page and saying it is fine.
website-qa-gates replaces that with a gate list: each gate has a pass criterion and must cite evidence, and
any FAIL blocks the release. Gates that cannot be verified by machine are marked `waived` with the reason;
a waived gate is reported, never counted as a pass. Every run is appended to a local
`coverage-ledger.json` (a runtime file, git-ignored; path configurable with `QA_GATES_LEDGER`).

Product one-pager: [docs/PRODUCT.md](docs/PRODUCT.md) · Changelog: [CHANGELOG.md](CHANGELOG.md)

## Capabilities

| Output | What it contains |
|---|---|
| Gate verdicts | Release gates G1–G9, G14 and G15 (local resource integrity), plus five motion gates M1–M5, each PASS / FAIL / conditional with evidence |
| 11-dimension score | Weighted 100-point model (real-browser verification 18, visual craft 12, CTA closure 12, performance budget 12, and seven more). Grades: S ≥95 · A++ ≥90 · A ≥85 · B ≥70 · C <70 |
| Remediation record | Filed when the grade is below A or any gate fails, with an owner and a default 24-hour deadline |

```
Input: change brief (what changed, viewports affected, materials)
  -> G1–G9 release gates (run -> evidence -> PASS / FAIL)
  -> G14 + motion gates M1–M5
  -> 11-dimension weighted score -> grade
  -> below A or any FAIL -> remediation record
  -> append to coverage-ledger.json
```

Missing materials (spec, screenshots, source paths) reduce the scope of the check and are disclosed; they
never become a silent pass.

## Quick start

```bash
git clone https://github.com/HUIIIM/website-qa-gates && cd website-qa-gates
bash demo/run.sh    # serves demo/www/ locally and runs the real gate runner; exit 0 = no FAIL, 2 = at least one FAIL
bash demo/eval.sh   # PASS when the run was recorded in the ledger with zero FAIL
python3 -m unittest discover -s tests -v   # regression tests for the gate runner (stdlib only)
```

`demo/run.sh` records its `demo-*` release in a temporary ledger file (printed as `LEDGER=`; it starts from
a copy of your local `coverage-ledger.json` if you have one); set `QA_GATES_LEDGER` to write elsewhere.
Gate counts change as gates are added; see [`demo/README.md`](demo/README.md), including how to inject a
defect and watch a gate fail.

## Repository layout

```
SKILL.md              the skill: gates, scoring model, filing rules
tools/ledger-run.py   gate runner used by the demo and CI (no shell; ledger writes are locked and atomic)
tests/                unit tests for the gate runner and fallback scanners
demo/                 test pages (demo/www/), run.sh, eval.sh
references/           gate-checklist.md, scorecard-v1.yaml and supporting checklists
evals/                dry-run records smoke-01 to smoke-07
dna.css, fonts/       vertciti DNA stylesheet and fonts used by the demo pages
```

## Status and limitations

- 21 of the 33 gates in the demo need a real browser, manual review or external material and are marked
  `waived` there (local run on 2026-10-26). Automating them with a real browser is planned, not done.
- Unit tests cover the machine gates' known false-pass cases (exit codes, paths with spaces, shell
  metacharacters, per-property motion whitelist, secret-scan coverage); the waived gates have no tests.
- Seven dry-run records are in `evals/`. The run ledger is a local runtime file and is not committed, so
  earlier runs (including the one against the live deploy root) cannot be re-checked from this repository.

## Security

There is no `SECURITY.md` in this repository yet. Report security issues through GitHub private
vulnerability reporting (Security tab → Report a vulnerability, if enabled); otherwise open an issue without
sensitive details and ask for a private channel. CI runs gitleaks secret scanning and OpenSSF Scorecard.

## Contributing

Issues and pull requests are welcome. Gate changes need a worked dry-run in `evals/` and regression tests
in `tests/` (`python3 -m unittest discover -s tests -v` and `ruff check tools tests` must pass).

## Licence

MIT — see [LICENSE](LICENSE). Copyright (c) 2026 Jiahui Miao. `dna.css` is vendored unmodified from
[HUIIIM/.github](https://github.com/HUIIIM/.github) `design/dist/dna.css`. The Nunito Sans font files in
`fonts/` are distributed under the SIL Open Font License ([fonts/OFL.txt](fonts/OFL.txt)).

Built by vertciti — https://vertciti.com
