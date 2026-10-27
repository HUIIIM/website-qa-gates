#!/usr/bin/env python3
"""ledger 处置闭环工具：对某条 run 的拦截项追加处置记录（立案->整改->复验）。

用法:
  python3 tools/ledger-dispose.py --run-id <run_id> --gate-id <G12-1|A2|...> \
      --action "立案/整改/复验" --result closed|open --note "<处置说明>"

语义:
  --action  立案 = 自动立案记录；整改 = 改了什么；复验 = 复验结论
  --result  closed = 该拦截项处置闭环；open = 仍待处置
  disposition_history 只追加不改写（ledger additive 纪律）；
  status = 最近一条 result。

V4 回查规则：上一条含拦截的 run 里 status != closed 的拦截项存在 -> V4 自判 fail。
"""
import argparse, os, sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ledger_io import ledger_path, locked_ledger  # noqa: E402

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--gate-id", required=True)
    ap.add_argument("--action", required=True, help="立案/整改/复验")
    ap.add_argument("--result", required=True, choices=["closed", "open"])
    ap.add_argument("--note", default="")
    a = ap.parse_args()

    with locked_ledger(ledger_path(), create=False) as (ledger, save):
        for run in ledger.get("runs", []):
            if run.get("run_id") != a.run_id:
                continue
            for it in run.get("interceptions", []):
                if it.get("gate_id") != a.gate_id:
                    continue
                it.setdefault("disposition_history", []).append(
                    {"at": datetime.now(timezone.utc).isoformat(),
                     "action": a.action, "result": a.result, "note": a.note})
                it["status"] = a.result
                save(ledger)
                print(f"OK: run={a.run_id} gate={a.gate_id} action={a.action} result={a.result}")
                return 0
    print(f"NOT FOUND: run={a.run_id} gate={a.gate_id} 的拦截项", file=sys.stderr)
    return 1

if __name__ == "__main__":
    sys.exit(main())
