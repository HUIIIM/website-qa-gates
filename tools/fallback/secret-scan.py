#!/usr/bin/env python3
"""Fallback 最小敏感扫描（纯 stdlib）。

当 QA_GATES_SECURITY_GATE 未设置时，ck_g1 用本脚本代替外部
data-room-gate.sh。规则是外部脚本的子集：绝密红线/私钥块/
高置信 token 前缀。输出 "GATE PASS:" / "GATE FAIL:" 行供 ck_g1 解析。

用法: python3 secret-scan.py --root <站点根目录>
退出码: 0=无命中(PASS), 1=有命中(FAIL), 2=用法错误
"""
import argparse, os, re, sys

PATTERNS = [
    ("2027-02", re.compile(r"2027-0?2")),
    ("绝密字样", re.compile(r"绝密|机密|SECRET|TOP ?SECRET", re.IGNORECASE)),
    ("私钥块", re.compile(r"-----BEGIN .*PRIVATE KEY-----")),
    ("高置信token", re.compile(
        r"ghp_[A-Za-z0-9]{8,}|gho_[A-Za-z0-9]{8,}|"
        r"sk_live_[A-Za-z0-9]{8,}|rk_live_[A-Za-z0-9]{8,}|"
        r"AKIA[0-9A-Z]{16}|xox[bap]-[A-Za-z0-9-]{8,}")),
]

TEXT_EXTS = (".html", ".htm", ".txt", ".json", ".md", ".js", ".css", ".xml")

def scan(root):
    hits = []
    for dirpath, _, files in os.walk(root):
        for fn in files:
            if not fn.lower().endswith(TEXT_EXTS):
                continue
            p = os.path.join(dirpath, fn)
            try:
                with open(p, encoding="utf-8", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        for name, rx in PATTERNS:
                            if rx.search(line):
                                hits.append((os.path.relpath(p, root), i, name))
                                break  # 一行只记一次
            except OSError:
                continue
    return hits

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    a = ap.parse_args()
    if not os.path.isdir(a.root):
        print(f"GATE FAIL: 目录不存在 {a.root}")
        return 2
    hits = scan(a.root)
    if hits:
        print("GATE FAIL: 敏感内容命中:")
        for rel, ln, name in hits[:10]:
            print(f"  {rel}:{ln} [{name}]")
        if len(hits) > 10:
            print(f"  ... 共 {len(hits)} 处命中")
        return 1
    print("GATE PASS: 敏感扫描零命中（fallback 最小规则集：绝密/私钥/token 前缀）")
    return 0

if __name__ == "__main__":
    sys.exit(main())
