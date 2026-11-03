# website-qa-gates

一个网站变更发布前 QA 的 vertciti skill：给出逐门禁 pass / fail 结论与证据、11 维度加权评分与等级，
并在发布低于 A 级时生成立案记录，面向要给官网或产品站上线改动的团队。

English: [README.md](README.md)

| | |
|---|---|
| 状态 | active · 早期、单人维护 — v1.5.0（版本以 [SKILL.md](SKILL.md) 为准）；每个 PR 与 main push 上 CI 跑 ruff、mypy、追溯矩阵检查、单元测试（含真浏览器门禁）与 demo 门禁；2026-11-02 本地运行：20 pass、0 fail，34 个门禁中 14 个 `waived`（需人工核对或外部材料） |
| 类型 | vertciti skill（agent skill，定义见 [SKILL.md](SKILL.md) / [SKILL.zh.md](SKILL.zh.md)），配 Python 门禁 runner（[`tools/ledger-run.py`](tools/ledger-run.py)）与真浏览器门禁（[`tools/browser/gates.cjs`](tools/browser/gates.cjs)，Playwright＋axe-core） |
| 安装 / 使用 | 在 agent 里加载 `SKILL.md`；本地用 `bash demo/run.sh` 跑门禁 |
| 许可证 | 本仓库自有代码与文档为 MIT（[LICENSE](LICENSE)），Copyright (c) 2026 Jiahui Miao · `demo/www/dna.css` 为 VERTCITY LLC 专有，字体为 SIL OFL — 见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) |
| 语言 | README 中英双版 · SKILL 中英双版 · 检查表与 demo 页为简体中文 · runner 输出可选（`--lang zh\|en`） |
| 联系 | 安全：[SECURITY.md](SECURITY.md) · 产品：[vertciti.com](https://vertciti.com) |

## 概览 / Overview

发布前的人工 QA 往往以"有人看了一眼说没问题"收场。website-qa-gates 用门禁清单替代它：每个门禁有通过判据、
必须引用证据，任一 FAIL 阻断发布。机器验证不了的门禁记 `waived` 并写明原因；waived 会被报告，但永远不算通过。
门禁执行出错算 FAIL，不算 waived。

每次运行追加进本地 `coverage-ledger.json`（运行产物，不入仓；路径可用 `QA_GATES_LEDGER` 改）。
运行记录、处置记录与评分记录共用一条哈希链，事后改写结论会被 `tools/ledger-verify.py` 发现。

产品一页纸：[docs/PRODUCT.md](docs/PRODUCT.md) · 更新日志：[CHANGELOG.md](CHANGELOG.md) ·
门禁与测试对照：[docs/TRACEABILITY.md](docs/TRACEABILITY.md)

## 能力 / Capabilities

| 输出 | 内容 | 由谁产出 |
|---|---|---|
| 门禁结论 | 34 个门禁：13 个静态机器门禁、7 个真浏览器门禁（触控目标、390px 横滚、生产 CSP 下渲染、键盘与焦点环、减少动态效果、CTA 单行、浅色＋深色 axe WCAG 2.2 AA）、V4，以及 13 个需人工的门禁 | `tools/ledger-run.py` |
| 证据 | 每个门禁的命令与输出；每页 1440 与 390px 截图和 axe JSON | `tools/browser/gates.cjs` |
| 11 维度评分 | 加权 100 分模型，读自 `references/scorecard-v1.yaml`；N/A 维度从分母剔除。等级：S ≥95 · A++ ≥90 · A ≥85 · B ≥70 · C <70 | `tools/score.py` |
| 立案记录 | 任一门禁 FAIL（P0）、总分 <70（P0）、任一维度 <70（P1）或总分 <85（P1）时生成，带责任人与默认 24 小时期限 | `tools/score.py` |
| 处置 | 立案、整改、复验；关闭需要第二个人 | `tools/ledger-dispose.py` |

```
输入：变更单（改了什么、影响哪些视口、有哪些材料）
  -> tools/ledger-run.py：静态门禁＋真浏览器门禁 -> 证据 -> PASS / FAIL / waived
  -> 按 references/gate-checklist.md 执行人工门禁
  -> tools/score.py：11 维度评分 -> 等级 -> 立案记录
  -> tools/ledger-dispose.py：立案 -> 整改 -> 复验（两人关闭）
  -> tools/ledger-verify.py：哈希链完整；把链头抄到台账之外
```

缺失的材料（spec、截图、源码路径）会缩小检查范围并如实写明，不会变成静默通过。

## 快速开始 / Quick start

```bash
git clone https://github.com/HUIIIM/website-qa-gates && cd website-qa-gates
npm ci --prefix tools/browser && npx --prefix tools/browser playwright install chromium   # 真浏览器门禁
bash demo/run.sh    # 本地托管 demo/www/ 并跑全部门禁；exit 0 = 无 FAIL，2 = 至少一个 FAIL
bash demo/eval.sh   # 记账、封印且零 FAIL 时输出 PASS
python3 -m unittest discover -s tests -v   # 回归测试（没装 Playwright 时浏览器用例跳过）
```

没装 Playwright 时浏览器门禁记 `waived`；设 `QA_GATES_REQUIRE_BROWSER=1` 则判 FAIL（CI 就这样做）。
`demo/run.sh` 写到一个临时目录，退出时删除；要保留台账和截图，设 `QA_GATES_LEDGER` 与 `QA_GATES_EVIDENCE_DIR`。
注入缺陷看门禁变红的方法见 [`demo/README.md`](demo/README.md)。

用在你自己的站点上：复制 [`qa-gates.config.json`](qa-gates.config.json)（vertciti 自用设置），改阈值和站点专属规则，
再用 `QA_GATES_CONFIG` 指向你的副本。

## 仓库结构 / Repository layout

```
SKILL.md / SKILL.zh.md   skill 本体（英文 / 中文）：门禁、评分模型、立案规则
qa-gates.config.json     vertciti 门禁配置（阈值、站点地址、额外敏感规则、排除文件）
tools/ledger-run.py      门禁 runner（不经 shell；失败即关闭；台账加锁、原子写入、封印）
tools/browser/           真浏览器门禁（Playwright＋axe-core，package-lock.json 锁精确版本）
tools/score.py           11 维度评分、等级与立案记录
tools/ledger-dispose.py  处置记录（两人关闭）
tools/ledger-verify.py   哈希链校验；打印链头供外部锚定
tools/trace-matrix.py    门禁与测试对照（docs/TRACEABILITY.md），CI 校验
tests/                   每个机器门禁的 pass 与 fail 用例，以及台账、评分
demo/www/                测试页、vendored DNA 样式表与字体
references/              gate-checklist.md、scorecard-v1.yaml、台账 schema 与配套清单
evals/                   dry-run 记录 smoke-01 至 smoke-08、injection-01
```

## 现状与边界 / Status and limitations

- 34 个门禁中 14 个仍需人工或外部材料：G6、G13、M2、M3、A3、T3、T4、V1–V3、G12-2、G12-3，
  以及 M1（runner 截图，由人判断）。
- 机器结论只覆盖 [`references/gate-checklist.md`](references/gate-checklist.md) 写明的判据。例如 G16 跑的 axe-core
  只能发现一部分 WCAG 问题；G5 比对数字与结构，不比对语义。
- 多数门禁只在测试注入的缺陷上触发过，按规则标为"假设"，见检查表「门禁验证状态」。
- 性能按字节（G4）衡量，不是真机 LCP、CLS、INP。
- vendored `dna.css` 违反本仓库自己的 A1、A2、G12-1。它由 `qa-gates.config.json` 排除，每次运行的证据都会写明；
  应在上游 HUIIIM/.github 修。
- 运行台账是本地文件，链头不会自动锚定到机器之外，要手工完成（例如写进发布 PR 描述）。
- agent 层面的提示注入评测（`evals/injection-01.md`）尚未执行。

## 安全 / Security

见 [SECURITY.md](SECURITY.md)。门禁把缺陷判成 PASS 算漏洞。CI 跑 gitleaks 密钥扫描与 OpenSSF Scorecard。

## 参与 / Contributing

欢迎 issue 与 pull request。改门禁需要在 `evals/` 附一次实跑记录，并在 `tests/` 加带门禁标注的用例（`[G15:fail]`），
至少一条 pass、一条 fail。推送前：

```bash
ruff check tools tests && python3 -m mypy && python3 tools/trace-matrix.py --check && python3 -m unittest discover -s tests
```

## 许可证 / Licence

MIT — 见 [LICENSE](LICENSE)。Copyright (c) 2026 Jiahui Miao。MIT 不覆盖 `demo/www/dna.css`
（VERTCITY LLC 专有，从 [HUIIIM/.github](https://github.com/HUIIIM/.github) `design/dist/dna.css` 原样引入）
与 `demo/www/fonts/` 里的 Nunito Sans 字体（SIL Open Font License，[OFL.txt](demo/www/fonts/OFL.txt)）。
详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

由 vertciti 构建 — https://vertciti.com
