#!/bin/bash
# website-qa-gates eval: 一键 PASS/FAIL
# 断言三件事：(1) release 已记账；(2) 无门禁 FAIL；(3) 台账哈希链完整（run.sh 已校验，失败则退出码非 0）。
set -u
DEMO="$(cd "$(dirname "$0")" && pwd)"
DUMP="$(mktemp "${TMPDIR:-/tmp}/qa-gates-eval.XXXXXX")"
trap 'rm -f "$DUMP"' EXIT
OUT="$(QA_GATES_DEMO_DUMP="$DUMP" bash "$DEMO/run.sh" 2>&1)"
RC=$?
echo "$OUT" | tail -12
REL="$(echo "$OUT" | grep -o 'RELEASE=demo-[0-9-]*' | cut -d= -f2)"
[ -n "$REL" ] || { echo "FAIL: 未产出 release id"; exit 1; }
python3 - "$DUMP" "$REL" "$RC" <<'PY'
import json, sys
ledger_path, rel, rc = sys.argv[1], sys.argv[2], int(sys.argv[3])
d = json.load(open(ledger_path))
run = next((e for e in d.get("runs", []) if e.get("run_id") == rel), None)
if run is None:
    print("FAIL: 台账无该 release 记账"); sys.exit(1)
if run["summary"]["fail"]:
    print(f"FAIL: {run['summary']['fail']} 个门禁 FAIL（见上方 FAIL 行）"); sys.exit(1)
if rc != 0:
    print(f"FAIL: run.sh 退出码 {rc}（台账哈希链校验或 runner 失败）"); sys.exit(1)
if not run.get("sha256"):
    print("FAIL: 本次记录未封印"); sys.exit(1)
s = run["summary"]
print(f"PASS: 门禁真实跑通且零 FAIL，release={rel} 已记账并封印（pass={s['pass']} waived={s['waived']}）")
PY
