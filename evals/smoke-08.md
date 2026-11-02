# smoke-08：SOTA 评分卡复现项回归（2026-11-02）

背景：2026-10-28 的 SOTA 评分卡（issue #12）在 `66115ea` 上复现了下列问题。本轮逐项修复，每项都有
`tests/test_gates.py` 用例，并由 `docs/TRACEABILITY.md` 追溯到门禁。"修复前"一列是评分卡在 `66115ea` 上的实测结果。

| 场景 | 修复前（66115ea） | 修复后 |
|---|---|---|
| 站点里一个坏符号链接，另有 4 处真实缺陷 | `pass=4 fail=0 waived=29`，exit 0 | 受影响门禁全部 fail，exit 2 |
| `srcset` 指向不存在的图、无引号 `href=missing.html`、CSS `url(missing.png)` | G15 pass（`refs=0`） | G15 fail，三处全部列出 |
| JSON-LD `<script type="application/ld+json">` | G7 误报 fail | 不计入 hash，G7 pass |
| 外部 G1 脚本 | 拿不到站点根目录（`args=[]`） | 以 `bash <脚本> <站点根目录>` 调用 |
| 页面引用 2 MB 图片 | G4 pass（只称两个 HTML） | G4 fail（单文件＋单页合计） |
| 页面写 `2027-02-14` | G1 fail（写死的内部规则） | 通用默认不命中；vertciti 自用配置仍命中 |
| `dna.css` 放进站点根目录 | demo 把它放在扫描范围外 | 放回 demo 根目录，配置排除并写进证据；不排除时 A1/A2/G12-1 fail |
| 关闭拦截项 | 单人单条命令、无身份 | 需 `--by` 与不同的 `--reviewer`，只在复验时 |
| 改写旧 run 的结论 | 无法发现 | `ledger-verify.py` 报链断，runner 拒绝追加 |
| "11 维度评分" | 无代码 | `tools/score.py`，适用均分 80 → 80.0 B → P1 立案 |
| 390px 横滚、20×20 按钮、无焦点环、CTA 折行、低对比度、reduce 下 2s 过渡、控制台报错、CSP 拦截 | 全部 waived | G3/G2/A4/T5/G16/M4/G9 fail |

demo 基线（`bash demo/eval.sh`，2026-11-02，本地 Playwright 1.63.0＋axe-core 4.14.0）：
`pass=20 fail=0 waived=14 machine=20/34`，台账封印并通过 `ledger-verify.py`，eval 输出 PASS。
G7 在 demo 上为 waived：demo 没有部署配置，因此没有 CSP 可比对。
