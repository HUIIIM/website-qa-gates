#!/bin/bash
# website-qa-gates eval: 一键 PASS/FAIL，零外部依赖
set -u
DEMO="$(cd "$(dirname "$0")" && pwd)"
OUT="$(bash "$DEMO/run.sh" 2>&1)"
echo "$OUT" | tail -5
REL="$(echo "$OUT" | grep -o 'RELEASE=demo-[0-9-]*' | cut -d= -f2)"
[ -n "$REL" ] || { echo "FAIL: 未产出 release id"; exit 1; }
if python3 -c "
import json,sys
d=json.load(open('$DEMO/../coverage-ledger.json'))
runs = d.get('runs', []) if isinstance(d, dict) else []
sys.exit(0 if any(e.get('run_id')=='$REL' for e in runs) else 1)"; then
  echo "PASS: 门禁真实跑通，release=$REL 已记账"; exit 0
else
  echo "FAIL: coverage-ledger.json 无该 release 记账"; exit 1
fi
