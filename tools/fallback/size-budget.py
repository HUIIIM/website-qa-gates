#!/usr/bin/env python3
"""Fallback 体积预算门禁（纯 stdlib）。

当 QA_GATES_SIZE_GATE 未设置时，ck_g4 用本脚本代替外部 size-gate.sh。规则：
  任一文件 > --file-fail（缺省 1.2MB）          -> FAIL
  任一文件 > --file-warn（缺省 1.0MB）          -> WARN（可发布，留痕）
  任一 HTML 页面自身＋其站内引用资源（img/script/link/srcset/poster/CSS url()，
  含所引 CSS 里的 url()）去重后合计 > --page-fail（缺省 1.5MB） -> FAIL
  --required 列出的页面缺失                      -> FAIL
页面合计是"全部资源都被加载"的上界，比真实首屏偏大；它能拦住超大图，但不替代真机 LCP。
输出 "GATE PASS:" / "GATE FAIL:" / "GATE WARN:" 行供 ck_g4 解析。

用法: python3 size-budget.py <站点根目录> [--file-fail N] [--file-warn N] [--page-fail N] [--required a.html ...]
退出码: 0=PASS(含 WARN), 1=FAIL
"""
import argparse, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from site_refs import css_urls, html_refs, is_external, resolve_local  # noqa: E402


def page_assets(root, html_path):
    """HTML 页面直接引用的站内文件，加上这些 CSS 里 url() 引用的文件（一层）。"""
    with open(html_path, encoding="utf-8", errors="ignore") as f:
        html = f.read()
    seen = set()
    for kind, raw in html_refs(html):
        if kind == "href" and not raw.lower().endswith(".css") and ".css?" not in raw.lower():
            continue  # 普通链接是导航，不算本页加载的资源
        if is_external(raw) or raw.strip().startswith("#"):
            continue
        p, _ = resolve_local(root, html_path, raw)
        if p and os.path.isfile(p):
            seen.add(os.path.abspath(p))
    for css in [p for p in seen if p.endswith(".css")]:
        with open(css, encoding="utf-8", errors="ignore") as f:
            for raw in css_urls(f.read()):
                if is_external(raw) or raw.startswith("#"):
                    continue
                p, _ = resolve_local(root, css, raw)
                if p and os.path.isfile(p):
                    seen.add(os.path.abspath(p))
    seen.discard(os.path.abspath(html_path))
    return seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--file-fail", type=int, default=1258291)
    ap.add_argument("--file-warn", type=int, default=1048576)
    ap.add_argument("--page-fail", type=int, default=1572864)
    ap.add_argument("--required", nargs="*", default=["index.html"])
    a = ap.parse_args()
    root = a.root
    if not os.path.isdir(root):
        print(f"GATE FAIL: 目录不存在 {root}")
        return 1
    fails, warns, pages = [], [], 0
    for fn in a.required:
        if not os.path.isfile(os.path.join(root, fn)):
            fails.append(f"缺失页面: {fn}")
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != ".git")
        for fn in sorted(files):
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, root)
            n = os.path.getsize(p)
            if n > a.file_fail:
                fails.append(f"{rel}={n}B > 单文件红线 {a.file_fail}B")
            elif n > a.file_warn:
                warns.append(f"{rel}={n}B > 单文件黄线 {a.file_warn}B")
            if fn.lower().endswith((".html", ".htm")):
                pages += 1
                total = n + sum(os.path.getsize(x) for x in page_assets(root, p))
                if total > a.page_fail:
                    fails.append(f"{rel} 页面合计={total}B > 单页红线 {a.page_fail}B")
    for w in warns:
        print(f"GATE WARN: {w}")
    if fails:
        print("GATE FAIL: 体积预算:")
        for f in fails[:10]:
            print(f"  {f}")
        return 1
    extra = f"（另有 {len(warns)} 条 WARN）" if warns else ""
    print(f"GATE PASS: 体积预算通过{extra}（{pages} 个页面，单文件 ≤{a.file_fail}B，单页合计 ≤{a.page_fail}B）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
