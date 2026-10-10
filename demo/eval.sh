#!/bin/bash
# website-qa-gates eval: 一键 PASS/FAIL，零外部依赖
# 断言两件事：(1) release 已记账进 coverage-ledger.json；(2) 无门禁 FAIL。
set -u
DEMO="$(cd "$(dirname "$0")" && pwd)"
OUT="$(bash "$DEMO/run.sh" 2>&1)"
echo "$OUT" | tail -8
REL="$(echo "$OUT" | grep -o 'RELEASE=demo-[0-9-]*' | cut -d= -f2)"
[ -n "$REL" ] || { echo "FAIL: 未产出 release id"; exit 1; }
python3 - "$DEMO/../coverage-ledger.json" "$REL" <<'EOF'
import json, sys
ledger_path, rel = sys.argv[1], sys.argv[2]
d = json.load(open(ledger_path))
runs = d.get("runs", []) if isinstance(d, dict) else []
run = next((e for e in runs if e.get("run_id") == rel), None)
if run is None:
    print(f"FAIL: coverage-ledger.json 无该 release 记账")
    sys.exit(1)
n_fail = run["summary"]["fail"]
if n_fail:
    print(f"FAIL: {n_fail} 个门禁 FAIL（见上方 FAIL 行）")
    sys.exit(1)
print(f"PASS: 门禁真实跑通且零 FAIL，release={rel} 已记账")
EOF
