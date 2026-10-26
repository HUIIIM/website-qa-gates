# website-qa-gates — 产品一页纸 / Product one-pager

> 状态：active（早期，单人维护）· 版本：1.4.0（见 `SKILL.md`）· 更新：2026-10-22
> 所属：[vertciti](https://vertciti.com) — 一家公司，一个人生。
>
> Status: active (early, single maintainer) · Version 1.4.0 (per `SKILL.md`) · Updated 2026-10-22

## 一句话 / One line
网站维护者（目前是 Miao 本人及其 agent）在网站变更发布前用它跑一遍门禁，得到逐门禁的 PASS / FAIL / waived 结论与证据、11 维度加权评分与等级，以及低于 A 级时的立案记录。

A website maintainer runs it before releasing a site change and gets per-gate verdicts with evidence, an 11-dimension weighted score and grade, and a remediation record when the result is below A.

## 解决什么问题 / Problem
- 痛点：发布前的人工 QA 容易变成"看着没问题"，移动端页脚、悬空 CTA 之类问题会漏到线上（README「The real problem it solves」）。发生频率与代价：未确认（TBD）。
- 现在的替代做法：人工目检、零散脚本。不够好之处：没有统一的通过标准，也不要求留证据。
- Pain: manual pre-release QA drifts into eyeballing. Frequency and cost: TBD.

## 给谁 / Who it is for
- 首要用户：Miao 本人与执行该 skill 的 agent（`SKILL.md` 中门禁与证据路径以 vertciti 官网为对象）。
- 不是给谁：需要全自动浏览器回归测试的团队。依赖浏览器的门禁目前标为 `waived`，不会自动判过。
- Primary: Miao and the agent executing the skill. Not for: teams expecting fully automated browser regression; browser-dependent gates are currently `waived`.

## 怎么用（三步）/ How to use
1. 给出变更描述：改了什么、影响哪些视口（桌面 / 390px 移动）、有哪些材料（`SKILL.md`「输入」）。
2. 按 `SKILL.md` 执行：G1–G9＋G14＋M1–M5 逐门禁检查 → 11 维度打分 → 低于 A 级或有 FAIL 时立案。
3. 机器可跑的门禁用 `tools/ledger-run.py` 执行并追加记账到 `coverage-ledger.json`；处置用 `tools/ledger-dispose.py` 记录。本地体验：`bash demo/run.sh` 与 `bash demo/eval.sh`。

## 为什么是我们（差异化）/ Differentiation
| 维度 | 本仓库 | 常见替代 |
|---|---|---|
| 通过标准 | 每个门禁有明确判据，必须引用证据（`references/gate-checklist.md`） | 目检、口头确认 |
| 无法机器验证的项 | 标为 `waived` 并说明原因，不算通过 | 常被默认视为通过 |
| 评分 | N/A 维度从分母剔除，不按满分计入（`references/scorecard-v1.yaml` v1.1） | 未确认（TBD） |
| 记录 | `coverage-ledger.json` 只追加 | 无统一记录 |

## 证据 / Evidence
- 测试：仓库没有单元测试套件。CI 工作流 `.github/workflows/qa-gates.yml` 在每次 push/PR 上跑 `demo/run.sh` 与 `demo/eval.sh`。2026-10-22 本地运行结果：`pass=11 fail=0 waived=21 machine=11/32`，`eval.sh` 输出 PASS。
- 真实运行：`evals/smoke-01.md` – `smoke-06.md` 六份 dry-run 记录；`coverage-ledger.json` 中有 13 条 run 记录（含 `dryrun-2026-10-06-h4`、`v2-20261008-qa`）。
- 红测：commit 8a4edbc 故意注入 em-dash 缺陷使 CI 变红，428252e 修复。
- 不能证明的：32 个门禁中 21 个在 demo 中为 `waived`（需要真实浏览器、人工核对或外部材料）；部分 eval 与 ledger 记录引用的是仓库外绝对路径（如家目录下的工作区路径），在本仓库内无法复核。
- Evidence: no unit-test suite; CI runs the demo gates and eval. Local run on 2026-10-22: pass=11 fail=0 waived=21. 21 of 32 gates are waived in the demo; some records cite paths outside this repo.

## 边界与风险 / Boundaries and risks
- 不做：替代人工终审（G14 规定 AI 初筛＋人工终审）；在 demo 中自动驱动浏览器。
- 已知限制：依赖浏览器的门禁为 `waived`；部分门禁的外部脚本通过 `QA_GATES_*` 环境变量接入，缺失时回退到 `tools/fallback/` 或判 fail；README 徽章版本（1.2.1）与 `SKILL.md`（1.4.0）不一致。
- 安全与隐私：工具在本地读取被测站点文件，结果写入仓库内 `coverage-ledger.json`；`tools/ledger-run.py` 唯一的网络请求是对 `--site-url`（默认 https://vertciti.com）发一次 `curl` 取 HTTP 状态码，不上传被测文件。删除方式：删除对应 ledger 记录。漏洞报告途径见 README「安全 / Security」。

## 与其他 vertciti 产品的组合 / With other vertciti products
- 与 vertciti DNA 设计系统：本仓库引入了 `dna.css`；门禁中的 8px 间距（A2）、动效白名单（G12）等检查项与 DNA 规则方向一致。具体联动方式：未确认（TBD）。
- 其他组合：未确认（TBD）。

## 路线图 / Roadmap
| 阶段 | 内容 | 退出标准 |
|---|---|---|
| Now | 维持 CI dogfood 常绿；补齐产品文档与安全配置 | 未确认（TBD） |
| Next | 用 Playwright 自动化当前 `waived` 的浏览器门禁并留证（README Roadmap） | 未确认（TBD） |
| Later | 基于 ledger 的 A 级趋势看板；动效门禁库扩充（README Roadmap） | 未确认（TBD） |

## 衡量指标 / Metrics
- 北极星：未确认（TBD）。候选：每次发布前门禁的机器可验证比例（当前 demo 为 11/32）。
- 护栏：CI dogfood 保持零 FAIL；`waived` 不计为通过。
