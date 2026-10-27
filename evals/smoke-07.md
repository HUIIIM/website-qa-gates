# smoke-07：门禁 runner 假 PASS 回归（2026-10-26）

背景：2026-10-25 独立评估在 `a4e8cc8` 上复现了一批"有缺陷却判 PASS"的场景。本轮修复后，每个场景都写成
`tests/test_gates.py` 里的回归用例；在修复前的代码上 34 个用例 22 个失败、10 个报错，修复后 34/34 通过。

| 场景 | 修复前 | 修复后 |
|---|---|---|
| 外部 G1 脚本 `exit 3`、无输出 | G1 pass（证据 `rc=3`） | G1 fail |
| 站点路径含空格，页内 `font-size:13px`、假 token | A1、G1、G12-1 pass | 全部 fail |
| `--site-url "http://127.0.0.1:9; touch PWNED; echo"` | 命令被执行 | G8 fail，不执行 |
| `transition: transform .2s, width .2s` | G12-1 pass | G12-1 fail |
| 第 41 条以后的 `transition: width` | 不检查 | G12-1 fail |
| `.env` / `.mjs` / `.map` / `.svg` 里的 token | G1 pass | G1 fail |
| `<p>Our secret sauce</p>` | G1 fail（误报） | G1 pass |
| 站点根目录不存在 | 7 个 grep 门禁 pass | exit 2，不记账 |
| demo 页 `x.png` 不存在、`href="#"` | 无门禁覆盖 | G15 fail（demo 已修正） |

demo 基线（`bash demo/eval.sh`，2026-10-26）：`pass=12 fail=0 waived=21 machine=12/33`，G8 测本地 http.server，eval 输出 PASS。
