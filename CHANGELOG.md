# 更新日志 / Changelog

本文件记录本仓库的所有重要变更，格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号以 `SKILL.md` frontmatter 的 `version` 为准。条目整理自 `git log`；仓库目前没有 git tag。

All notable changes to this repository are documented here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
The version number follows the `version` field in `SKILL.md`. Entries are derived from `git log`; the repo has no git tags yet.

> 说明 / Note：`SKILL.md` 的「版本变更记录」另列了 v1.1.0 – v1.3.0（2026-10-06 至 2026-10-07）的门禁内容变化；
> 这些版本在 git 历史中没有单独提交，详情以 `SKILL.md` 为准。
> `SKILL.md` also lists v1.1.0 – v1.3.0 gate changes; those versions have no separate commits in git history.

## [Unreleased]

### 新增 / Added
- `docs/PRODUCT.md` 产品一页纸 / product one-pager.
- `CHANGELOG.md`（本文件 / this file）.
- 根目录 `dna.css`：从 HUIIIM/.github `design/dist/dna.css` 原样引入的 vertciti DNA v4.0.0 样式表 /
  vendored vertciti DNA v4.0.0 stylesheet (unmodified copy).
- README 增加状态行与双语「安全 / Security」「许可证 / License」小节 / README status line and bilingual Security and License sections.
- 基线工程配置：CODEOWNERS、`.editorconfig`、gitleaks 与 OpenSSF Scorecard 工作流、Dependabot（github-actions）/
  engineering baseline: CODEOWNERS, `.editorconfig`, gitleaks and OpenSSF Scorecard workflows, Dependabot.

### 变更 / Changed
- `demo/www/index.html`、`en.html` 引用 `../../dna.css`；演示链接改为黑底 `dna-btn`，`body` 加 16px 边距 /
  demo pages link the DNA stylesheet; the demo link is a black `dna-btn`; 16px body gutter.
  `dna.css` 放在 `demo/www` 之外，避免门禁 runner 把它当作被测站点 CSS 扫描 /
  kept outside `demo/www` so the gate runner does not scan it as site CSS.
- `qa-gates.yml`：最小权限 `contents: read`、`timeout-minutes`，actions 升级到 `@v7` /
  least-privilege permissions, job timeout, actions bumped to `@v7`.

### 修复 / Fixed
- `gitleaks.yml` 增加 `pull-requests: read`（仅 `contents: read` 时 gitleaks-action 在 PR 上返回 403）/
  add `pull-requests: read` so gitleaks-action does not 403 on pull requests.

## [1.4.0] - 2026-10-10

### 新增 / Added
- 自家 CI dogfood：`.github/workflows/qa-gates.yml` 在 push/PR 上跑 `demo/run.sh` 与 `demo/eval.sh`，门禁 FAIL 即红 /
  CI dogfood workflow that runs the demo gates and eval on every push and PR.
- `tools/ledger-dispose.py`：拦截项处置记录（立案 → 整改 → 复验）/ disposition log for intercepted gates.
- `tools/fallback/secret-scan.py`、`tools/fallback/size-budget.py`：纯 stdlib 最小实现 / stdlib-only fallbacks.
- `demo/eval.sh`、`demo/www/en.html`、`references/a011-fail-format.md`、`coverage-ledger.json`。

### 变更 / Changed
- V4 校验改为断言本轮拦截项含真实 FAIL 及其处置 / V4 now asserts real FAILs and their dispositions.
- 评分公式：N/A 维度从分母剔除权重，不再按满分计入（scorecard v1.0 → v1.1）/ N/A dimensions are excluded from the denominator.
- 外部路径收敛为 `QA_GATES_*` 环境变量；外部脚本缺失时判 fail / external paths moved to `QA_GATES_*` env vars; missing scripts fail.

### 修复 / Fixed
- `ck_t2` em-dash 扫描在 `/bin/sh=dash` 下假阴性，改为纯 Python 扫描 / em-dash scan false negative under dash.

### 验证 / Verified
- 2026-10-10 红测：故意在 `demo/www/index.html` 注入 em-dash，CI 变红（8a4edbc）；随后修复恢复常绿（428252e）/
  red test injected an em-dash to confirm CI fails, then reverted.

## [1.0.0] - 2026-10-06

### 新增 / Added
- 首次公开发布：`SKILL.md`（G1–G9 门禁、动效门禁、11 维度评分、自动立案）、`references/`、`evals/smoke-01..06`、
  `tools/ledger-run.py`、`demo/run.sh` / initial public release.

### 文档 / Docs
- 2026-10-07：README 重构（快速开始、Demo、场景表、FAQ、License 表）/ README restructure.
- 2026-10-14：README 作者段改为 N=1 定位 / Author section updated.

[Unreleased]: https://github.com/HUIIIM/website-qa-gates/compare/main...HEAD
