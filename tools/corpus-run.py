#!/usr/bin/env python3
"""门禁缺陷语料库：每个已知缺陷一条用例，报告每个机器门禁的拦截率（issue #23）。

语料在 tests/corpus/*.json，每个文件是一个用例列表。每条用例在 demo/www 的副本上注入缺陷：

  {"id": "G15-srcset", "origin": "real: 2026-10-28 SOTA 评分卡 R5" | "synthetic",
   "patch": {"index.html": {"append": "..."}, "hero.jpg": {"bytes": 2000000},
             "old.html": {"symlink": "/nonexistent"}, "en.html": {"delete": true},
             "vercel.json": {"write": "..."}},
   "both": "<同时追加到 index.html 与 en.html，避免触发 G5>",
   "site_url": "unreachable" | "local",          # 可选，G8 用
   "prior_runs": [...], "dispositions": [...],   # 可选，V4 用
   "expect": {"G15": "fail"}}

"{FAKE_GH}" 在运行时替换成拼接出来的假 token，仓库里不出现 token 字面量。

判定：expect 为 fail 的门禁实际也 fail 才算"拦下"；expect 为 pass 的门禁实际 pass 才算"没误报"。
用法:
  python3 tools/corpus-run.py                 # 跑全部用例，打印每个门禁的拦截率
  python3 tools/corpus-run.py --require-all   # 另外要求每个机器门禁至少有一条 fail 用例（CI 用）
  python3 tools/corpus-run.py --no-browser    # 跳过需要浏览器的用例（会在报告里列出）
有 $GITHUB_STEP_SUMMARY 时把报告表格追加进去。退出码：0=全部符合预期，1=有漏检/误报/覆盖不足。
"""
import argparse, functools, glob, importlib.util, json, os, shutil, sys, tempfile, threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO = os.path.join(REPO, "demo", "www")
CORPUS = os.path.join(REPO, "tests", "corpus")
FAKE_GH = "gh" + "p_" + "C0rpusT0kenA1b2C3d4E5f6G7h8"


def load_runner():
    spec = importlib.util.spec_from_file_location("ledger_run", os.path.join(REPO, "tools", "ledger-run.py"))
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def load_cases(path=CORPUS):
    cases = []
    for f in sorted(glob.glob(os.path.join(path, "*.json"))):
        with open(f, encoding="utf-8") as fh:
            for c in json.load(fh):
                c["_file"] = os.path.basename(f)
                cases.append(c)
    ids = [c["id"] for c in cases]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        raise ValueError(f"语料用例 id 重复：{dup}")
    return cases


def _text(s):
    return s.replace("{FAKE_GH}", FAKE_GH)


def apply_patch(root, case):
    patch = dict(case.get("patch") or {})
    if case.get("both"):
        for page in ("index.html", "en.html"):
            op = patch.setdefault(page, {})
            op["append"] = op.get("append", "") + case["both"]
    for name, op in patch.items():
        p = os.path.join(root, name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        if op.get("delete"):
            os.remove(p)
        elif "symlink" in op:
            os.symlink(op["symlink"], p)
        elif "bytes" in op:
            with open(p, "wb") as f:
                f.write(b"\1" * int(op["bytes"]))
        elif "write" in op:
            with open(p, "w", encoding="utf-8") as f:
                f.write(_text(op["write"]))
        if "append" in op:
            with open(p, "a", encoding="utf-8") as f:
                f.write(_text(op["append"]))


def run_case(lr, case, browser_ok, use_browser):
    """返回 {gate_id: verdict}；需要浏览器但不可用时对应门禁记 'skipped'。"""
    tmp = tempfile.mkdtemp(prefix="qa-corpus-")
    root = os.path.join(tmp, "www")
    srv = None
    try:
        shutil.copytree(DEMO, root)
        apply_patch(root, case)
        url = None
        if case.get("site_url") == "unreachable":
            url = "http://127.0.0.1:9"
        elif case.get("site_url") == "local":
            srv = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=root))
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            url = f"http://127.0.0.1:{srv.server_port}"
        cfg = lr.load_config()[0]
        gates = lr.run_gates(root, url, case.get("prior_runs", []), cfg, case.get("dispositions", []), browser=False)
        got = {g["gate_id"]: g["verdict"] for g in gates}
        if any(g in lr.BROWSER_GATES for g in case["expect"]):
            if browser_ok and use_browser:
                res, why = lr.run_browser_gates(root, cfg, os.path.join(tmp, "evidence"))
                got.update({g: v for g, (v, _) in (res or {}).items()})
            else:
                got.update({g: "skipped" for g in lr.BROWSER_GATES})
        return got
    finally:
        if srv:
            srv.shutdown()
            srv.server_close()
        shutil.rmtree(tmp, ignore_errors=True)


def evaluate(lr, cases, use_browser=True):
    browser_ok = lr.browser_available()[0]
    rows = []  # (case, gate, expect, got)
    for c in cases:
        got = run_case(lr, c, browser_ok, use_browser)
        for gid, want in c["expect"].items():
            rows.append((c, gid, want, got.get(gid, "missing")))
    return rows


def report(rows, machine):
    per: dict[str, dict] = {}
    for c, gid, want, got in rows:
        s = per.setdefault(gid, {"fail_cases": 0, "caught": 0, "pass_cases": 0, "clean": 0, "skipped": 0,
                                 "real": 0, "misses": []})
        if got == "skipped":
            s["skipped"] += 1
            continue
        if want == "fail":
            s["fail_cases"] += 1
            s["real"] += c.get("origin", "").startswith("real")
            if got == "fail":
                s["caught"] += 1
            else:
                s["misses"].append(f"{c['id']}（得到 {got}）")
        else:
            s["pass_cases"] += 1
            if got == want:
                s["clean"] += 1
            else:
                s["misses"].append(f"{c['id']}（期望 {want}，得到 {got}）")
    lines = ["## 门禁缺陷语料库 / Gate defect corpus", "",
             "| 门禁 | 拦截 caught/fail 用例 | 其中真实缺陷 | 无误报 clean/pass 用例 | 跳过 | 漏检或误报 |",
             "|---|---|---|---|---|---|"]
    for gid in machine:
        s = per.get(gid) or {}
        if not s:
            lines.append(f"| {gid} | 0/0 | 0 | 0/0 | 0 | **无用例** |")
            continue
        lines.append(f"| {gid} | {s['caught']}/{s['fail_cases']} | {s['real']} | {s['clean']}/{s['pass_cases']} | "
                     f"{s['skipped']} | {'; '.join(s['misses']) or '—'} |")
    total_fail = sum(s["fail_cases"] for s in per.values())
    total_caught = sum(s["caught"] for s in per.values())
    lines += ["", f"总拦截率 / overall catch rate: {total_caught}/{total_fail}"
              + (f" = {100 * total_caught / total_fail:.1f}%" if total_fail else "")]
    return "\n".join(lines) + "\n", per


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--require-all", action="store_true", help="每个机器门禁至少一条 fail 用例")
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    lr = load_runner()
    machine = [g for g, _ in lr.MACHINE]
    cases = load_cases()
    unknown = sorted({g for c in cases for g in c["expect"] if g not in machine})
    if unknown:
        print(f"CORPUS FAIL: 用例引用了非机器门禁 {unknown}", file=sys.stderr)
        return 1
    rows = evaluate(lr, cases, use_browser=not a.no_browser)
    text, per = report(rows, machine)
    print(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(text)
    rc = 0
    bad = [m for s in per.values() for m in s["misses"]]
    if bad:
        print(f"CORPUS FAIL: {len(bad)} 处漏检或误报：{bad}", file=sys.stderr)
        rc = 1
    if a.require_all:
        missing = [g for g in machine if not per.get(g, {}).get("fail_cases")]
        if missing:
            print(f"CORPUS FAIL: 以下机器门禁没有可执行的 fail 用例：{missing}", file=sys.stderr)
            rc = 1
    if rc == 0:
        print(f"CORPUS OK: {len(cases)} 条用例全部符合预期")
    return rc


if __name__ == "__main__":
    sys.exit(main())
