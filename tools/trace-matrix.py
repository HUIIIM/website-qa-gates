#!/usr/bin/env python3
"""门禁 ↔ 测试追溯矩阵（SOTA ARCH-1 / ARCH-3）。

从 tests/*.py 里每个 test_* 方法的 docstring 读取 [门禁ID:方向] 标注（方向为 pass / fail / waived），
与 tools/ledger-run.py 的机器门禁清单对照，生成 docs/TRACEABILITY.md。

规则：每个机器门禁至少有一条 pass 用例和一条 fail 用例（正反两类验收测试）。

用法:
  python3 tools/trace-matrix.py            # 打印矩阵
  python3 tools/trace-matrix.py --write    # 写 docs/TRACEABILITY.md
  python3 tools/trace-matrix.py --check    # CI：缺用例或提交的矩阵过期 -> exit 1
"""
import argparse, ast, glob, importlib.util, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "docs", "TRACEABILITY.md")
TAG = re.compile(r"\[([A-Za-z0-9-]+):([\w-]+)\]")


def machine_gates():
    spec = importlib.util.spec_from_file_location("ledger_run", os.path.join(REPO, "tools", "ledger-run.py"))
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return [g for g, _ in mod.MACHINE], mod.NAMES


def collect():
    tags: dict[str, dict[str, list[str]]] = {}
    for path in sorted(glob.glob(os.path.join(REPO, "tests", "test_*.py"))):
        tree = ast.parse(open(path, encoding="utf-8").read())
        for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
            for fn in [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]:
                for gid, direction in TAG.findall(ast.get_docstring(fn) or ""):
                    tags.setdefault(gid, {}).setdefault(direction, []).append(f"{cls.name}.{fn.name}")
    return tags


def _cell(t, key):
    return "<br>".join(f"`{x}`" for x in sorted(set(t.get(key, [])))) or "—"


def render(gates, names, tags):
    lines = ["# 门禁 ↔ 测试追溯矩阵 / Gate-to-test traceability", "",
             "由 `tools/trace-matrix.py --write` 从 `tests/` 的 `[门禁:方向]` 标注生成，CI 用 `--check` 校验，请勿手改。",
             "Generated from the `[gate:direction]` tags in `tests/`; CI checks it with `--check`. Do not edit by hand.", "",
             "| 门禁 | 名称 / Name | pass 用例 | fail 用例 | waived 用例 | 状态 |", "|---|---|---|---|---|---|"]
    missing = []
    for g in gates:
        t = tags.get(g, {})
        ok = bool(t.get("pass")) and bool(t.get("fail"))
        if not ok:
            missing.append(g)
        lines.append(f"| {g} | {names[g][0]} / {names[g][1]} | {_cell(t, 'pass')} | {_cell(t, 'fail')} | {_cell(t, 'waived')} | {'✓' if ok else '✗ 缺正反用例'} |")
    others = sorted(k for k in tags if k not in gates)
    if others:
        lines += ["", "## 其他受测行为 / Other tested behaviour", "", "| 标注 | 用例 |", "|---|---|"]
        for k in others:
            cases = sorted({c for v in tags[k].values() for c in v})
            lines.append(f"| {k}:{'/'.join(sorted(tags[k]))} | " + "<br>".join(f"`{c}`" for c in cases) + " |")
    return "\n".join(lines) + "\n", missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    gates, names = machine_gates()
    text, missing = render(gates, names, collect())
    if a.write:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, "w", encoding="utf-8") as f:
            f.write(text)
    elif not a.check:
        print(text)
    rc = 0
    if missing:
        print(f"TRACE FAIL: 以下机器门禁缺 pass 或 fail 用例：{missing}", file=sys.stderr)
        rc = 1
    if a.check:
        current = open(OUT, encoding="utf-8").read() if os.path.isfile(OUT) else ""
        if current != text:
            print("TRACE FAIL: docs/TRACEABILITY.md 已过期，运行 python3 tools/trace-matrix.py --write", file=sys.stderr)
            rc = 1
        elif not missing:
            print(f"TRACE OK: {len(gates)} 个机器门禁均有正反用例")
    return rc


if __name__ == "__main__":
    sys.exit(main())
