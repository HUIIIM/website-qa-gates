# website-qa-gates demo

最小可运行切片：用 skill 自带真实门禁 runner（`tools/ledger-run.py`）跑 1 个测试页。

## 运行
```bash
bash demo/run.sh   # 真实跑门禁，记账进 coverage-ledger.json（additive，release=demo-*）
bash demo/eval.sh  # 输出 PASS/FAIL
```

## 测试页
`demo/www/index.html`：故意带 2 个问题（img 无 alt、小触控目标），预期 fail=2。

## 预期输出
`release=demo-* pass=9 fail=2 waived=21`（数字随门禁版本浮动，关键是真实跑通＋记账）。
