#!/usr/bin/env python3
"""ledger 处置闭环工具：对某条 run 的拦截项追加一条处置记录（立案->整改->复验）。

用法:
  python3 tools/ledger-dispose.py --run-id <run_id> --gate-id <G12-1|A2|...> \
      --action 立案|整改|复验 --result open|closed --by <执行人> \
      [--reviewer <复核人>] --note "<处置说明>"

语义:
  --action  立案 = 自动立案记录；整改 = 改了什么；复验 = 复验结论
  --result  closed = 该拦截项处置闭环；open = 仍待处置
  --by      执行人（人名或 agent 名），必填，写进记录
  --reviewer  关闭（--result closed）时必填，且不能与 --by 相同：
              关闭一个阻断发布的拦截项是两人动作，不是单人单键（SOTA INT-2 / SKILL G14 署名）。
              只能 --action 复验 时关闭。

处置写进台账顶层 dispositions（只追加、进哈希链），不改写原 run；
拦截项当前状态 = 该拦截项最近一条处置的 result。
V4 回查规则：最近一条含拦截的 run 里状态不是 closed 的拦截项存在 -> V4 自判 fail。
"""
import argparse, os, sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ledger_io import interception_status, ledger_path, locked_ledger, seal  # noqa: E402

ACTIONS = ("立案", "整改", "复验")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--gate-id", required=True)
    ap.add_argument("--action", required=True, choices=ACTIONS)
    ap.add_argument("--result", required=True, choices=["closed", "open"])
    ap.add_argument("--by", required=True, help="执行人")
    ap.add_argument("--reviewer", default="", help="复核人（关闭时必填，且不同于执行人）")
    ap.add_argument("--note", default="")
    a = ap.parse_args()

    by, reviewer = a.by.strip(), a.reviewer.strip()
    if not by:
        print("REFUSED: --by 不能为空", file=sys.stderr)
        return 2
    if a.result == "closed":
        if a.action != "复验":
            print("REFUSED: 只有 --action 复验 才能关闭拦截项", file=sys.stderr)
            return 2
        if not reviewer or reviewer.casefold() == by.casefold():
            print("REFUSED: 关闭拦截项需要 --reviewer，且复核人不能是执行人本人", file=sys.stderr)
            return 2

    with locked_ledger(ledger_path(), create=False) as (ledger, save):
        if interception_status(ledger, a.run_id, a.gate_id) is None:
            print(f"NOT FOUND: run={a.run_id} gate={a.gate_id} 的拦截项", file=sys.stderr)
            return 1
        rec = {"run_id": a.run_id, "gate_id": a.gate_id,
               "at": datetime.now(timezone.utc).isoformat(),
               "action": a.action, "result": a.result, "by": by, "note": a.note}
        if reviewer:
            rec["reviewer"] = reviewer
        seal(ledger, "dispositions", rec)
        save(ledger)
    print(f"OK: run={a.run_id} gate={a.gate_id} action={a.action} result={a.result} by={by}"
          + (f" reviewer={reviewer}" if reviewer else "") + f" seq={rec['seq']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
