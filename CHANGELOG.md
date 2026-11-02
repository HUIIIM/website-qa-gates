# 更新日志 / Changelog

本文件记录本仓库的所有重要变更，格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号以 `SKILL.md` frontmatter 的 `version` 为准。条目整理自 `git log`；仓库目前没有 git tag（合并后由维护者打 tag）。

All notable changes to this repository are documented here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
The version number follows the `version` field in `SKILL.md`. Entries are derived from `git log`; the repo has no git tags yet.

> 说明 / Note：`SKILL.md` 的「版本变更记录」另列了 v1.1.0 – v1.3.0（2026-10-06 至 2026-10-07）的门禁内容变化；
> 这些版本在 git 历史中没有单独提交，详情以 `SKILL.md` 为准。
> `SKILL.md` also lists v1.1.0 – v1.3.0 gate changes; those versions have no separate commits in git history.

## [Unreleased]

## [1.5.0] - 2026-11-02

依据 2026-10-28 SOTA 评分卡（issue #12）逐项修复；下面"本轮"标注的是这一轮，其余条目是 1.4.0 以后已合并、此前未发版的改动。
Fixes from the 2026-10-28 SOTA scorecard (issue #12); items marked "本轮 / this round" are new, the rest were merged after 1.4.0 and never released.

### 新增 / Added（本轮 / this round）
- 真浏览器门禁 `tools/browser/gates.cjs`（Playwright 1.63.0 Chromium＋axe-core 4.14.0，`package-lock.json` 锁版本与完整性哈希）：
  G2 触控目标、G3 390px 零横向截断、G9 生产 CSP 下渲染、A4 键盘可达与焦点环、M4 减少动态效果、T5 CTA 单行，
  新增 G16 axe WCAG 2.2 AA（浅色＋深色）；M1 自动截取关动效截图（结论仍待人工）/
  real-browser gates for G2, G3, G9, A4, M4, T5 and the new G16 (axe WCAG 2.2 AA, light and dark); M1 screenshots.
- G5 中英镜像机械项（数字、标题层级、链接、图片一致，英文版无全角标点）/ G5 mechanical zh/en mirror check.
- `tools/score.py`：11 维度加权评分、等级、立案记录（权重与阈值读自 `scorecard-v1.yaml`）/ scoring, grade and filing in code.
- `tools/ledger-verify.py` 与台账哈希链（runs / dispositions / scores）/ ledger hash chain and verifier.
- `qa-gates.config.json`＋`QA_GATES_CONFIG`：阈值、站点地址、站点专属敏感规则、设计规则排除项 / gate configuration file.
- `tools/trace-matrix.py` 与 `docs/TRACEABILITY.md`：每个机器门禁都有 pass 与 fail 用例 / gate-to-test traceability.
- `--lang en`、`QA_GATES_LANG`：英文输出；台账门禁带 `name_en` / English output.
- `SECURITY.md`、`THIRD_PARTY_NOTICES.md`、`evals/injection-01.md`、`evals/smoke-08.md`、`mypy.ini`。
- 双语对齐（`CLAUDE.md` 发布门禁）：`SKILL.md` 改为英文版，原中文版移到 `SKILL.zh.md`；新增 `README.zh.md`。两对文件章节一一对应 /
  bilingual parity: English `SKILL.md`, Chinese `SKILL.zh.md`, new `README.zh.md`, sections aligned.
- 检查表新增「门禁验证状态」：未在真实缺陷上触发过的门禁标为假设 / gate evidence status, unproven gates labelled hypotheses.
- CI：mypy（哈希锁定）、追溯矩阵检查、浏览器门禁（`QA_GATES_REQUIRE_BROWSER=1`）、证据存档、dna-drift /
  CI adds mypy, traceability, browser gates, an evidence artifact and the dna-drift job.

### 变更 / Changed（本轮 / this round）
- **处置需要两个人**：`ledger-dispose.py` 必填 `--by`；关闭只能在复验时，且需不同于执行人的 `--reviewer`。
  处置追加进台账 `dispositions`，不再改写原 run / closing an interception needs a second person; dispositions no longer rewrite runs.
- G4：任一文件超单文件红线、或单页（HTML＋站内资源）合计超 1.5MB 即 FAIL，不再只称 `index.html`/`en.html` / per-file and per-page budgets.
- G1/G4 外部脚本以 `bash <脚本> <站点根目录>` 调用 / external gate scripts now receive the site root.
- G1 fallback 去掉写死的 `2027-02` 规则，改由配置 `secret_scan.extra_patterns` 传入（vertciti 自用配置保留）/
  the site-specific date rule moved to configuration.
- G8 缺省不再请求 vertciti.com：取 `--site-url`、`QA_GATES_SITE_URL` 或配置 `site_url`，都没有则记 waived / no hard-coded URL.
- `dna.css` 与 `fonts/` 移到 `demo/www/`，demo 页正常引用；它违反本仓库 A1/A2/G12-1 的地方由配置排除并写进证据，不再靠放在扫描范围外 /
  the DNA stylesheet now lives in the demo site and is excluded by configuration, with the exclusion stated in evidence.
- A2 合法间距加入 `0`；A1/A5/G12-4 也扫 `.css`/`.js`；T1 逐页判定；T2 只看可见文字 / gate scope fixes.
- `demo/run.sh` 用临时目录并在退出时删除，不再在 `/tmp` 留台账副本；`eval.sh` 同时校验哈希链 / demo cleans up after itself.
- 门禁检查表、评分卡里指向不存在脚本或本机路径的引用改为仓库内真实实现 / dangling references removed.
- `references/coverage-ledger.schema.json` 改为描述真实台账结构，并由测试核对 / ledger schema matches the real ledger.

### 修复 / Fixed（本轮 / this round）
- 门禁执行抛异常（如站点里有坏符号链接）判 fail，不再记 waived 而放行发布 / a crashing gate now fails instead of being waived.
- G15 漏检 `srcset`、无引号属性、CSS `url()`（含站内 `.css` 文件）与越出站点根目录的引用 / G15 false passes.
- G7 不再把 JSON-LD 等数据块当作内联脚本；改为解析 CSP 的 `script-src`，支持 `_headers` / G7 false failures.
- A2 正则不再跨 HTML 标签读到后面的 `width` 值 / A2 no longer reads across tags.

### 新增 / Added
- `docs/PRODUCT.md` 产品一页纸 / product one-pager.
- `CHANGELOG.md`（本文件 / this file）.
- 根目录 `dna.css`：从 HUIIIM/.github `design/dist/dna.css` 原样引入的 vertciti DNA v4.0.0 样式表 /
  vendored vertciti DNA v4.0.0 stylesheet (unmodified copy).
- README 增加状态行与双语「安全 / Security」「许可证 / License」小节 / README status line and bilingual Security and License sections.
- 基线工程配置：CODEOWNERS、`.editorconfig`、gitleaks 与 OpenSSF Scorecard 工作流、Dependabot（github-actions）/
  engineering baseline: CODEOWNERS, `.editorconfig`, gitleaks and OpenSSF Scorecard workflows, Dependabot.

### 变更 / Changed
- 新增机器门禁 G15「站内资源完整性」（坏引用、`href="#"`、`javascript:`、不存在的锚点）；demo 基线变为 pass=12 fail=0 waived=21 /
  new machine gate G15 (local resource integrity); demo baseline is now 12 pass, 0 fail, 21 waived.
- CI：全部 Actions 按 commit SHA 固定（附版本注释）；`qa-gates.yml` 增加 ruff（`requirements-dev.txt` 版本＋哈希锁定）与
  `tests/` 单元测试两个阻断步骤，push 只在 `main` 上触发（PR 不再跑两遍）/
  CI: actions pinned by SHA; ruff (hash-pinned) and unit tests are blocking steps; push runs only on `main`.
- 新增 `QA_GATES_LEDGER` 环境变量（台账路径）/ new `QA_GATES_LEDGER` environment variable.
- `demo/www/index.html`、`en.html` 引用 `../../dna.css`；演示链接改为黑底 `dna-btn`，`body` 加 16px 边距 /
  demo pages link the DNA stylesheet; the demo link is a black `dna-btn`; 16px body gutter.
  `dna.css` 放在 `demo/www` 之外，避免门禁 runner 把它当作被测站点 CSS 扫描 /
  kept outside `demo/www` so the gate runner does not scan it as site CSS.
  （本轮已撤销：这样做等于让 demo 绕开自家门禁，见上方"变更"/ reverted this round: it hid the stylesheet from the gates.）
- `qa-gates.yml`：最小权限 `contents: read`、`timeout-minutes`，actions 升级到 `@v7` /
  least-privilege permissions, job timeout, actions bumped to `@v7`.

### 修复 / Fixed
- 门禁 runner 假 PASS（2026-10-25 独立评估 P1-1 至 P1-5，P2-1 至 P2-9）/ gate-runner false passes found by the 2026-10-25 independent assessment:
  - G1/G4 外部或 fallback 脚本非零退出、超时一律判 fail，不再只看输出里有没有 `FAIL` /
    G1/G4 fail on a non-zero exit or timeout, not only on `FAIL` in the output.
  - `tools/ledger-run.py` 不再经 shell：外部脚本按 argv 调用，grep 类检查改为纯 Python；路径含空格不再假 PASS，
    `--site-url` / `--site-root` 无法注入命令，`--site-url` 只接受 http/https /
    no shell anywhere in the runner: paths with spaces no longer pass falsely and arguments cannot inject commands.
  - G12-1 逐属性判定（`transition: transform, width` 判 fail；省略属性名＝all；检查 `@keyframes`；去掉只看前 40 条的截断）/
    G12-1 checks each transitioned property and `@keyframes` declarations, with no 40-line cap.
  - fallback 敏感扫描扫全部非二进制文件（含 `.env`、`.mjs`、`.map`、`.svg`），新增 `github_pat_`、`sk-ant-`、`AIza`、JWT、凭据赋值规则；
    英文密级只认大写标识（`secret sauce` 不再误报）；接上 `.publish-allowlist`（`--allowlist`）/
    the fallback secret scan covers every text file, more token shapes, no lowercase "secret" false positive, and honours `.publish-allowlist`.
  - 站点根目录不存在时 exit 2 且不记账 / a missing site root exits 2 without writing the ledger.
  - V4：FAIL 门禁须带实际输出证据；V4 自身的 fail 不再立案，不再连锁 / V4 requires output evidence and no longer cascades.
  - 台账加锁＋原子替换写入；站点路径记为仓库相对路径或 `~/…` / ledger writes are locked and atomic; paths no longer record the local user name.
- demo：`x.png` 坏图与 `href="#"` 死链改为 `demo.svg` 与中英互链；`demo/run.sh` 起本地服务测 G8（不再测 vertciti.com、不依赖外网），
  运行记录写临时文件（`QA_GATES_LEDGER`）；超时 25 s → 60 s /
  demo: fixed the broken image and dead link, G8 now targets a local server, and the demo writes its run to a temporary ledger file.
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
