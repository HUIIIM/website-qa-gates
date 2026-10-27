#!/usr/bin/env python3
"""Fallback 最小敏感扫描（纯 stdlib）。

当 QA_GATES_SECURITY_GATE 未设置时，ck_g1 用本脚本代替外部
data-room-gate.sh。规则是外部脚本的子集：绝密红线/私钥块/
高置信 token 前缀/凭据赋值。输出 "GATE PASS:" / "GATE FAIL:" 行供 ck_g1 解析。

扫描范围：站点根目录下全部非二进制文件（含 .env 等点文件、.map、.mjs、.svg），
跳过 .git 目录与 > 5MB 的文件（后者计入输出，不静默）。

精确排除：--allowlist 文件（缺省为 <root>/.publish-allowlist，存在才用），
每行一个子串（# 开头为注释）；命中行包含其中任一子串即不计。allowlist 文件本身不扫。

用法: python3 secret-scan.py --root <站点根目录> [--allowlist FILE]
退出码: 0=无命中(PASS), 1=有命中(FAIL), 2=用法错误
"""
import argparse, os, re, sys

PATTERNS = [
    ("2027-02", re.compile(r"2027-0?2")),
    # 密级标识：中文直接匹配；英文只认大写标识（避免 "secret sauce" 这类误报）
    ("绝密字样", re.compile(r"绝密|机密|\bTOP ?SECRET\b|\bSECRET\b|\bCONFIDENTIAL\b")),
    ("私钥块", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("高置信token", re.compile(
        r"gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
        r"sk-ant-[A-Za-z0-9_-]{20,}|sk-(?:proj-)?[A-Za-z0-9_-]{32,}|"
        r"[sr]k_live_[A-Za-z0-9]{8,}|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}|"
        r"xox[bapr]-[A-Za-z0-9-]{8,}|"
        r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("凭据赋值", re.compile(
        r"(?i)\b(?:api[_-]?key|client[_-]?secret|secret[_-]?key|access[_-]?token|auth[_-]?token|password)"
        r"\b[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9_\-+/=]{16,}")),
]

MAX_BYTES = 5 * 1024 * 1024
ALLOWLIST_NAME = ".publish-allowlist"


def is_binary(path):
    with open(path, "rb") as f:
        return b"\0" in f.read(8192)


def load_allowlist(path):
    if not path or not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8", errors="ignore") as f:
        return [ln.rstrip("\n") for ln in f if ln.strip() and not ln.lstrip().startswith("#")]


def scan(root, allow=(), allow_path=None):
    hits, skipped = [], []
    skip_abs = os.path.abspath(allow_path) if allow_path else None
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != ".git")
        for fn in sorted(files):
            p = os.path.join(dirpath, fn)
            if skip_abs and os.path.abspath(p) == skip_abs:
                continue
            try:
                if os.path.getsize(p) > MAX_BYTES:
                    skipped.append(os.path.relpath(p, root))
                    continue
                if is_binary(p):
                    continue
                with open(p, encoding="utf-8", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        if any(a in line for a in allow):
                            continue
                        for name, rx in PATTERNS:
                            if rx.search(line):
                                hits.append((os.path.relpath(p, root), i, name))
                                break  # 一行只记一次
            except OSError:
                continue
    return hits, skipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--allowlist", default=None)
    a = ap.parse_args()
    if not os.path.isdir(a.root):
        print(f"GATE FAIL: 目录不存在 {a.root}")
        return 2
    allow_path = a.allowlist or os.path.join(a.root, ALLOWLIST_NAME)
    hits, skipped = scan(a.root, load_allowlist(allow_path), allow_path)
    for s in skipped[:5]:
        print(f"GATE WARN: 超过 5MB 未扫：{s}")
    if hits:
        print("GATE FAIL: 敏感内容命中:")
        for rel, ln, name in hits[:10]:
            print(f"  {rel}:{ln} [{name}]")
        if len(hits) > 10:
            print(f"  ... 共 {len(hits)} 处命中")
        return 1
    print("GATE PASS: 敏感扫描零命中（fallback 最小规则集：绝密/私钥/token 前缀/凭据赋值）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
