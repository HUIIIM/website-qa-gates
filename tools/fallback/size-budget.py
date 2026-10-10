#!/usr/bin/env python3
"""Fallback 最小体积预算门禁（纯 stdlib）。

当 QA_GATES_SIZE_GATE 未设置时，ck_g4 用本脚本代替外部 size-gate.sh。
规则（与外部脚本一致）：
  单文件 > 1.2MB        -> FAIL（停发）
  单文件 > 1.0MB        -> WARN（可发布，留痕）
  缺失 index.html/en.html -> FAIL
输出 "GATE PASS:" / "GATE FAIL:" / "GATE WARN:" 行供 ck_g4 解析。

用法: python3 size-budget.py <站点根目录>
退出码: 0=PASS(含 WARN), 1=FAIL
"""
import os, sys

WARN_BYTES = 1048576   # 1.0MB
FAIL_BYTES = 1258291   # 1.2MB
WATCH_FILES = ("index.html", "en.html")

def main():
    if len(sys.argv) < 2:
        print("GATE FAIL: 用法: size-budget.py <站点根目录>")
        return 1
    root = sys.argv[1]
    fails, warns = [], []
    for fn in WATCH_FILES:
        p = os.path.join(root, fn)
        if not os.path.isfile(p):
            fails.append(f"缺失文件: {fn}")
            continue
        n = os.path.getsize(p)
        if n > FAIL_BYTES:
            fails.append(f"{fn}={n}B > 1.2MB 红线")
        elif n > WARN_BYTES:
            warns.append(f"{fn}={n}B > 1.0MB 黄线")
    for w in warns:
        print(f"GATE WARN: {w}")
    if fails:
        print("GATE FAIL: 体积预算:")
        for f in fails:
            print(f"  {f}")
        return 1
    extra = f"（另有 {len(warns)} 条 WARN）" if warns else ""
    print(f"GATE PASS: 体积预算通过{extra}（fallback 最小规则：单文件 1.2MB 红线）")
    return 0

if __name__ == "__main__":
    sys.exit(main())
