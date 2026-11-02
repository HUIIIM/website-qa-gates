#!/usr/bin/env python3
"""校验台账哈希链，并打印链头（head）供外部锚定。

用法: python3 tools/ledger-verify.py [--ledger PATH] [--require-sealed]
  --require-sealed  有未封印的旧记录也判失败（新台账应全部封印）
退出码: 0=链完整, 1=链被改写/截断, 2=用法或文件错误

外部锚定：把输出里的 head 值抄到台账之外只追加的地方（例如发布 PR 的描述、一个 git tag 的注释），
之后任何人都能用本工具确认台账在那一刻之前的内容没被改过。
"""
import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ledger_io import ledger_path, verify_chain  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", default=None)
    ap.add_argument("--require-sealed", action="store_true")
    a = ap.parse_args()
    path = a.ledger or ledger_path()
    if not os.path.isfile(path):
        print(f"ERROR: 台账不存在 {path}", file=sys.stderr)
        return 2
    with open(path, encoding="utf-8") as f:
        ledger = json.load(f)
    problems, sealed, unsealed = verify_chain(ledger)
    if ledger.get("additive") is not True:
        problems.insert(0, "additive 标志不是 true")
    if a.require_sealed and unsealed:
        problems.append(f"{unsealed} 条记录未封印（无 seq/sha256）")
    print(f"ledger={path} sealed={sealed} unsealed={unsealed} head={ledger.get('head') or '-'}")
    for p in problems:
        print(f"  CHAIN FAIL: {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
