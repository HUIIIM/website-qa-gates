![website-qa-gates](docs/assets/social-preview.png)

# website-qa-gates · 网站质量门禁

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.2.1-blue.svg)](SKILL.md)
[![QA Gates](https://github.com/HUIIIM/website-qa-gates/actions/workflows/qa-gates.yml/badge.svg)](https://github.com/HUIIIM/website-qa-gates/actions/workflows/qa-gates.yml)

**A website is the company's proof of caliber. This skill runs the pre-release gauntlet: per-gate pass/fail verdicts with evidence, an 11-dimension weighted score with a grade, and automatic issue filing when it falls below A-grade — so nothing ships on "looks fine to me."**

[官网](https://vertciti.com) · [快速开始](#快速开始) · [诚实约定](#诚实约定) · [测试实证](#测试实证)

[Quick start](#30-second-quick-start) · [What it delivers](#what-it-delivers) · [Demo](#demo) · [FAQ](#faq)

A [Vertciti Skill Pack](https://vertciti.com) for pre-release quality gates on website changes. One change description in, three things out.

Built for [Miao](https://vertciti.com) (Jiahui Miao) — N=1 founder IP infrastructure.

> website-qa-gates 是 vertciti 为创始人自用的技能工具。状态：🟢 已验证（PASS · 已验证）· 数据截至 2026-10-21（见[测试实证](#测试实证)）。

## 门禁结论词状态呈现

本仓门禁结论词按 vertciti 产品 DNA 的状态色口径呈现，只加呈现层映射，原结论词本身保留不删、结论含义一字不改：

| 门禁结论词（原词保留） | 状态呈现 | 状态色 |
|---|---|---|
| PASS | PASS · 已验证 | 绿 |
| WARN | WARN · 建设中 | 黄 |
| FAIL | FAIL · 风险 | 橙 |

说明：上表对应 `vc-product.css` 的 `.vc-st` 状态色定义（已验证=绿 / 建设中=黄 / 风险=橙）。本仓历史实跑结论（如某次运行的 PASS / WAIVED / FAIL 读数）属事实记录，只做呈现映射、数字不动；`waived` 不在上表三词之列，按原文保留。

## 快速开始

### 30-second quick start

```bash
cd demo
bash run.sh
# Runs the real gate runner against a test page (~30s)
```

See `demo/README.md` for details. Machine-runnable gates execute for real; browser-dependent gates are honestly marked `waived` (never faked).

## 它做什么

### The real problem it solves

Manual QA before a website release drifts into vibes: somebody eyeballs it, says fine, and the launch carries a broken footer on mobile or an orphaned CTA that leads nowhere. website-qa-gates replaces the eyeball with a gate list — each gate has a pass criterion and must cite evidence. Browser-dependent gates that can't be machine-verified are honestly marked `waived`, never faked into a pass.

### What it delivers

Three things per website change:

1. **Gate verdicts** — G1–G9 + G14 release gates + 4 motion-specific gates, each PASS · 已验证 / FAIL · 风险 / conditional with evidence. Any FAIL · 风险 blocks release.
2. **11-dimension score** — Weighted 100-point model (real-browser verification 18, visual craft 12, CTA closure 12, perf budget 12, …). Grades: S ≥95 / A++ ≥90 / A ≥85 / B ≥70 / C <70.
3. **Auto-filing** — Below A-grade (or any gate FAIL · 风险) automatically files a remediation record with owner and 24h deadline.

### When to use it

| Scenario | What it produces |
|---|---|
| Homepage hero changed | Gate verdicts + score before anything goes live |
| Mobile (390px) footer restyle | Contrast + touch-target gates, per-item inspection |
| New animation added | 4 motion-specific gates (no black first frames, no autoplay traps) |
| A release scored B | Auto-filed remediation with owner + 24h deadline |

### Input

One change brief, containing:

- **What changed**: e.g. "homepage hero adds a numbers-evidence bar: four numbers + source citations"
- **Viewports affected**: desktop / mobile (390px) / both
- **Materials**: change note, spec, screenshots/recordings, source paths (if missing, the check degrades and says so)

### Structure

```
Input: change brief
  ↓  G1–G9 release gates (each: run → evidence → PASS · 已验证/FAIL · 风险)
  ↓  G14 + 4 motion-specific gates
  ↓  11-dimension weighted score → grade
  ↓  Below A or any FAIL · 风险 → auto-filed remediation (owner + 24h deadline)
  ↓  Ledger append (coverage-ledger.json, additive)
```

### Repo layout

```
website-qa-gates/
  SKILL.md              # the skill itself: gates, scoring model, filing rules
  demo/                 # runnable test page + run.sh → coverage-ledger.json
  tools/ledger-run.py   # the real gate runner
  references/           # gate-checklist.md, scorecard-v1.yaml (machine-readable)
  evals/                # six real dry-run records (smoke-01..06)
  coverage-ledger.json  # additive ledger of real runs
```

### References

- `references/gate-checklist.md` — Per-gate execution methods and pass criteria.
- `references/scorecard-v1.yaml` — Machine-readable scoring model.
- `evals/` — Six real dry-run records (smoke-01 through smoke-06), each with evidence.
- `tools/ledger-run.py` — Gate runner used in the demos.

### Roadmap

- Real-browser gate automation for the currently `waived` gates (Playwright, evidence-captured).
- A-grade trend dashboard from the additive ledger.
- Motion-gate library expansion as the site's animation vocabulary grows.

## 诚实约定

- 每个数字标注来源与抓取时间；抓不到的标“需手动补”，绝不编数。

### Honesty contract

- Gates that cannot be executed machine-side are marked `waived` with the reason — a waived gate is not a pass.
- Missing materials degrade the check and are disclosed; they never silently become a pass.
- Every dry-run record is additive in `coverage-ledger.json` (real runs, e.g. `dryrun-2026-10-06-h4`); the ledger is the scoreboard.

## 测试实证

| 指标 | 数字 | 来源 · 数据截至 |
|---|---|---|
| 门禁自跑（demo） | pass=11 fail=0 waived=21 machine=11/32 | `bash demo/run.sh`（`tools/ledger-run.py`）本地实跑 · 2026-10-21 |
| eval 断言 | PASS · 已验证：门禁真实跑通且零 FAIL | `bash demo/eval.sh` 本地实跑 · 2026-10-21 |

### Demo

`bash run.sh` runs the real gate runner (`tools/ledger-run.py`) against a test page — machine gates execute, evidence is written, and the run is appended to `coverage-ledger.json`. Six real dry-run records ship in `evals/` (smoke-01 through smoke-06); a recent production run (`dryrun-2026-10-06-h4`, against the live deploy root) is in the ledger.

> Walkthrough video/screenshot of a gate run producing its verdicts: 待补（占位）——run records above are already real and evidence-backed.

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

## 关于 vertciti

vertciti 把全部资源用来运营一个人的人生：创始人苗家辉。官网 [vertciti.com](https://vertciti.com) · 仿冒预警：vertciti 从未发行任何代币。

### Author

**Jiahui Miao** — Founder, [vertciti](https://vertciti.com). Building N=1 personal AI infrastructure. Participates in 3GPP working on 6G core network standards.

## 许可证

| Module | License | Plain meaning |
|---|---|---|
| All files | MIT | Commercial use OK, modify OK, attribution required |

See [LICENSE](LICENSE).

MIT · 运营主体 VERTCITY LLC
