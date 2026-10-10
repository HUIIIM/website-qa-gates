# website-qa-gates demo

最小可运行切片：用 skill 自带真实门禁 runner（`tools/ledger-run.py`）跑 1 个测试页。

## 运行
```bash
bash demo/run.sh   # 真实跑门禁，记账进 coverage-ledger.json（additive，release=demo-*）；退出码 0=全过，2=有 FAIL
bash demo/eval.sh  # 输出 PASS/FAIL：断言 release 已记账且零 FAIL
```

## 测试页
`demo/www/`：index.html＋en.html 基线干净（预期 `fail=0`，CI 常绿）。

## 红测（验证"FAIL 即红"）
故意注缺陷看门禁是否真拦，例如在 index.html 某行中文文案里加一个 em-dash（—）：
```bash
bash demo/run.sh   # 预期 T2 FAIL，退出码 2
```
修掉后恢复常绿。CI dogfood 就靠这个：main 常绿，缺陷提交即红。

## 预期输出（基线）
`release=demo-* pass=11 fail=0 waived=21`（数字随门禁版本浮动，关键是真实跑通＋记账）。
