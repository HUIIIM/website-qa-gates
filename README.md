# website-qa-gates

A vertciti skill for pre-release QA of website changes: it returns per-gate pass / fail verdicts with
evidence, an 11-dimension weighted score with a grade, and a remediation record when a release falls below
grade A, for teams that ship changes to a marketing or product site.

| | |
|---|---|
| Status | active · early, single maintainer — v1.4.0 (version from [SKILL.md](SKILL.md)); CI runs the demo gates on every push and pull request; local run on 2026-10-22: 11 pass, 0 fail, 21 of 32 gates `waived` (they need a real browser, manual review or external materials); no unit-test suite |
| Type | vertciti skill (agent skill defined in [SKILL.md](SKILL.md)) with a Python gate runner ([`tools/ledger-run.py`](tools/ledger-run.py)) |
| Install / use | Load `SKILL.md` as a skill in your agent; run the gates locally with `bash demo/run.sh` |
| Licence | MIT ([LICENSE](LICENSE)), Copyright (c) 2026 Jiahui Miao · bundled Nunito Sans fonts under the SIL OFL ([fonts/OFL.txt](fonts/OFL.txt)) |
| Languages | README in English · skill text, checklists and demo pages in 简体中文 |
| Contact | Security: see [Security](#security) · Product: [vertciti.com](https://vertciti.com) |

## Overview

Manual QA before a website release tends to end with someone looking at the page and saying it is fine.
website-qa-gates replaces that with a gate list: each gate has a pass criterion and must cite evidence, and
any FAIL blocks the release. Gates that cannot be verified by machine are marked `waived` with the reason;
a waived gate is reported, never counted as a pass. Every run is appended to
[`coverage-ledger.json`](coverage-ledger.json).

Product one-pager: [docs/PRODUCT.md](docs/PRODUCT.md) · Changelog: [CHANGELOG.md](CHANGELOG.md)

## Capabilities

| Output | What it contains |
|---|---|
| Gate verdicts | Release gates G1–G9 and G14, plus five motion gates M1–M5, each PASS / FAIL / conditional with evidence |
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
bash demo/run.sh    # runs the real gate runner on demo/www/; exit 0 = no FAIL, 2 = at least one FAIL
bash demo/eval.sh   # PASS when the run was recorded in the ledger with zero FAIL
```

`demo/run.sh` appends a `demo-*` release to `coverage-ledger.json`. Gate counts change as gates are added;
see [`demo/README.md`](demo/README.md), including how to inject a defect and watch a gate fail.

## Repository layout

```
SKILL.md              the skill: gates, scoring model, filing rules
tools/ledger-run.py   gate runner used by the demo and CI
demo/                 test pages (demo/www/), run.sh, eval.sh
references/           gate-checklist.md, scorecard-v1.yaml and supporting checklists
evals/                dry-run records smoke-01 to smoke-06
coverage-ledger.json  append-only ledger of runs
dna.css, fonts/       vertciti DNA stylesheet and fonts used by the demo pages
```

## Status and limitations

- 21 of the 32 gates in the demo need a real browser, manual review or external material and are marked
  `waived` there (local run on 2026-10-22). Automating them with a real browser is planned, not done.
- There is no unit-test suite; the CI check is the demo gate run.
- Six dry-run records are in `evals/`; a run against the live deploy root (`dryrun-2026-10-06-h4`) is in the
  ledger.

## Security

There is no `SECURITY.md` in this repository yet. Report security issues through GitHub private
vulnerability reporting (Security tab → Report a vulnerability, if enabled); otherwise open an issue without
sensitive details and ask for a private channel. CI runs gitleaks secret scanning and OpenSSF Scorecard.

## Contributing

Issues and pull requests are welcome. Gate changes need a worked dry-run in `evals/` and a
`coverage-ledger.json` entry.

## Licence

MIT — see [LICENSE](LICENSE). Copyright (c) 2026 Jiahui Miao. `dna.css` is vendored unmodified from
[HUIIIM/.github](https://github.com/HUIIIM/.github) `design/dist/dna.css`. The Nunito Sans font files in
`fonts/` are distributed under the SIL Open Font License ([fonts/OFL.txt](fonts/OFL.txt)).

Built by vertciti — https://vertciti.com
