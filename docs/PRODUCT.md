# website-qa-gates — 产品一页纸 / Product one-pager

> 状态：active（早期，单人维护）· 版本：1.5.0（见 `SKILL.md`）· 更新：2026-11-02
> 所属：[vertciti](https://vertciti.com) — 一家公司，一个人生。
>
> Status: active (early, single maintainer) · Version 1.5.0 (per `SKILL.md`) · Updated 2026-11-02

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
3. 机器门禁（静态 13 项＋真浏览器 7 项）用 `tools/ledger-run.py` 执行并封印记账；评分与立案用 `tools/score.py`；处置用 `tools/ledger-dispose.py`（两人关闭）；`tools/ledger-verify.py` 校验台账。本地体验：`bash demo/run.sh` 与 `bash demo/eval.sh`。

## 为什么是我们（差异化）/ Differentiation
| 维度 | 本仓库 | 常见替代 |
|---|---|---|
| 通过标准 | 每个门禁有明确判据，必须引用证据（`references/gate-checklist.md`） | 目检、口头确认 |
| 无法机器验证的项 | 标为 `waived` 并说明原因，不算通过 | 常被默认视为通过 |
| 评分 | `tools/score.py` 按 `scorecard-v1.yaml` 计算，N/A 维度从分母剔除，打分必须附证据 | 未确认（TBD） |
| 失败处理 | 门禁执行出错判 FAIL；FAIL 必须处置闭环（两人关闭）才放行下一次发布（V4） | 阈值失败即止，不追踪处置（对标工具文档未见，未核实） |
| 记录 | 台账哈希链，`ledger-verify.py` 能发现事后改写 | 无统一记录 |

## 证据 / Evidence
- 测试：`tests/test_gates.py` 覆盖每个机器门禁的 pass 与 fail 场景（含真浏览器门禁），追溯矩阵见 `docs/TRACEABILITY.md`。CI 在每个 PR 与 main push 上跑 ruff、mypy、追溯矩阵检查、单元测试（`QA_GATES_REQUIRE_BROWSER=1`）、`demo/run.sh` 与 `demo/eval.sh`，并存档截图与 axe 结果。
- 2026-11-02 本地运行：`pass=20 fail=0 waived=14 machine=20/34`，台账封印并通过校验，`eval.sh` 输出 PASS；单元测试 73 项全过。
- 红测：在 demo 页注入 em-dash，T2 FAIL、退出码 2（`evals/smoke-08.md`）。旧的红测记录：commit 8a4edbc 注入、428252e 修复。
- 不能证明的：34 个门禁中 14 个仍需人工或外部材料；G16 的 axe 扫描只覆盖一部分 WCAG；性能只按字节计，没有真机 LCP；agent 层面的提示注入评测（`evals/injection-01.md`）尚未执行；早期 ledger 记录引用的仓库外路径无法复核。
- Evidence: every machine gate has pass and fail tests, including the browser gates; CI runs lint, types, traceability, tests and the demo. Local run on 2026-11-02: pass=20 fail=0 waived=14. 14 of 34 gates still need a person.

## 边界与风险 / Boundaries and risks
- 不做：替代人工终审（G14 规定 AI 初筛＋人工终审）。
- 已知限制：14 个门禁仍需人工；vendored `dna.css` 违反本仓库 A1/A2/G12-1，靠配置排除（证据里写明），要在上游修；台账链头的外部锚定需手工完成。
- 安全与隐私：工具在本地读取被测站点文件，结果写入本地 `coverage-ledger.json`（不入仓）与证据目录（截图会包含被测页面内容）。网络请求只有两类：G8 对 `--site-url`（或配置 `site_url`）发一次 GET；浏览器门禁访问 127.0.0.1 上的本地服务，页面里的外链资源会被浏览器照常加载。不上传被测文件。保留期限：本地文件由使用者自行删除；CI 证据存档保留 90 天。漏洞报告见 `SECURITY.md`。

## 与其他 vertciti 产品的组合 / With other vertciti products
- 与 vertciti DNA 设计系统：本仓库引入了 `dna.css`；门禁中的 8px 间距（A2）、动效白名单（G12）等检查项与 DNA 规则方向一致。具体联动方式：未确认（TBD）。
- 其他组合：未确认（TBD）。

## 路线图 / Roadmap
| 阶段 | 内容 | 退出标准 |
|---|---|---|
| Now | 1.5.0：浏览器门禁、评分、哈希链、两人关闭已落地；维持 CI 常绿 | CI 绿且 `trace-matrix --check` 通过 |
| Next | 真机 Lighthouse（G12-3、LCP/CLS/INP）；按 sitemap 发现全站页面；PR 状态检查与报告；执行 `injection-01` agent 评测 | 每项有 pass/fail 用例进追溯矩阵 |
| Later | 门禁漏检率语料库（每个门禁一个已知缺陷页，CI 报告拦截率）；台账链头自动外部锚定；in-toto 发布证明 | 漏检率在 CI 输出里可见 |

## 衡量指标 / Metrics
- 北极星（候选）：每次发布前门禁的机器可验证比例（demo 当前 20/34）；以及门禁漏检率（语料库建成后）。
- 护栏：CI dogfood 保持零 FAIL；`waived` 不计为通过。
