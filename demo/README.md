# website-qa-gates demo

最小可运行切片：用 skill 自带真实门禁 runner（`tools/ledger-run.py`）跑 1 个测试页。

## 运行
```bash
bash demo/run.sh   # 起本地 http.server 托管 demo/www 并真实跑门禁；退出码 0=全过，2=有 FAIL
bash demo/eval.sh  # 输出 PASS/FAIL：断言 release 已记账且零 FAIL
```

运行记录与截图缺省写到一个临时目录，退出时删除（本地已有 `coverage-ledger.json` 时先复制一份，供 V4 回查）。
要保留：`QA_GATES_LEDGER="$PWD/coverage-ledger.json" QA_GATES_EVIDENCE_DIR="$PWD/qa-evidence" bash demo/run.sh`（两者都不入仓）。
G8 测的是本地起的 demo 服务，不依赖外网。真浏览器门禁需要 `npm ci --prefix tools/browser`；没装时这些门禁记 waived。

## 测试页
`demo/www/`：index.html＋en.html＋demo.svg＋vendored `dna.css` 与字体，基线干净（预期 `fail=0`，CI 常绿）。两页互链做语言切换，G15 校验引用都存在。
`dna.css` 违反 A1/A2/G12-1 的地方由 `qa-gates.config.json` 排除，每次运行的证据里都会写出这条排除。

## 红测（验证"FAIL 即红"）
故意注缺陷看门禁是否真拦，例如在 index.html 某行中文文案里加一个 em-dash（—）：
```bash
bash demo/run.sh   # 预期 T2 FAIL，退出码 2
```
修掉后恢复常绿。CI dogfood 就靠这个：main 常绿，缺陷提交即红。

## 预期输出（基线）
`release=demo-* pass=20 fail=0 waived=14`（装了浏览器门禁依赖时；数字随门禁版本浮动，关键是真实跑通＋记账＋封印）。
