#!/usr/bin/env python3
"""11 维度加权评分＋等级＋自动立案（SKILL.md 第二、三步的可执行版本）。

权重、等级线、立案阈值全部从 references/scorecard-v1.yaml 读取（唯一来源），不在这里另抄一份。

用法:
  python3 tools/score.py --scores scores.json [--run-id <发布ID>] [--owner <责任人>] \
      [--deadline-hours 24] [--record] [--json]

scores.json:
  {"dimensions": {"real_browser_evidence": 82, "visual_craft": "N/A", ...},   # 11 个维度一个不少，0–100 或 "N/A"
   "na_reasons": {"visual_craft": "本次只改文案"},                            # 每个 N/A 必须写理由
   "evidence":   {"real_browser_evidence": "qa-evidence/r1/desktop-1440-index.html.png"},  # 每个打了分的维度必须有证据
   "failed_checks": ["seo_full.og_tags_complete"]}                          # 可选：失败的检查项

--run-id  从台账读取该次运行：任一门禁 FAIL -> P0 立案（gate_fail）。
--owner   命中立案时必填（立案记录要有责任人）。
--record  把评分与立案记录追加进台账 scores（进哈希链）。
退出码: 0=未触发立案, 3=触发立案, 2=输入错误。
"""
import argparse, json, os, re, sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ledger_io import SKILL_DIR, ledger_path, locked_ledger, seal  # noqa: E402

SCORECARD = os.path.join(SKILL_DIR, "references", "scorecard-v1.yaml")


def _find(rx, text, flags=re.M):
    m = re.search(rx, text, flags)
    if not m:
        raise ValueError(f"scorecard 结构不符：找不到 {rx}")
    return m.group(1)


def load_scorecard(path=SCORECARD):
    """从 scorecard YAML 里取维度（id/中文名/权重）、等级线与立案规则。只解析本文件用到的固定结构。"""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    version = _find(r"^\s{2}version:\s*(\S+)", text)
    dims = []
    for block in re.split(r"\n  - id: ", text.split("\ndimensions:", 1)[1])[1:]:
        dim_id = block.split("\n", 1)[0].strip()
        weight = int(_find(r"^\s{4}weight:\s*(\d+)", block))
        name = _find(r"^\s{4}name_zh:\s*(.+)$", block).strip()
        dims.append({"id": dim_id, "name_zh": name, "weight": weight})
    grades = [(g, int(v)) for g, v in re.findall(r"^\s{4}(\w+):\s*\{\s*min:\s*(\d+)", text, re.M)]
    rule = lambda k: int(_find(rf"^\s+{k}:\s*(\d+)", text))  # noqa: E731
    prio = dict(re.findall(r"^\s{4}(gate_fail|total_below_70|dimension_below_70|total_below_85|check_fail_only):\s*(P\d)", text, re.M))
    return {"version": version, "dimensions": dims, "grades": sorted(grades, key=lambda g: -g[1]),
            "total_below": rule("total_below"), "dimension_below": rule("dimension_below"), "priority": prio}


def grade_of(total, grades):
    for name, lo in grades:
        if total >= lo:
            return name.replace("A_plus_plus", "A++")
    return grades[-1][0]


def compute(card, scores):
    """返回 (result, errors)。"""
    dims_in = scores.get("dimensions") or {}
    na_reasons = scores.get("na_reasons") or {}
    evidence = scores.get("evidence") or {}
    errors, rows = [], []
    known = {d["id"] for d in card["dimensions"]}
    for k in dims_in:
        if k not in known:
            errors.append(f"未知维度 {k}")
    for d in card["dimensions"]:
        v = dims_in.get(d["id"])
        if v is None:
            errors.append(f"缺少维度 {d['id']}（{d['name_zh']}）：每个维度都要打分或写 N/A")
            continue
        if v == "N/A":
            if not str(na_reasons.get(d["id"], "")).strip():
                errors.append(f"{d['id']} 记 N/A 但没写理由")
            rows.append(dict(d, score=None, na_reason=na_reasons.get(d["id"])))
            continue
        if not isinstance(v, (int, float)) or not 0 <= v <= 100:
            errors.append(f"{d['id']} 分数必须是 0–100 或 \"N/A\"：{v!r}")
            continue
        if not str(evidence.get(d["id"], "")).strip():
            errors.append(f"{d['id']} 打了分但没给证据（无证据的分数无效）")
        rows.append(dict(d, score=float(v), evidence=evidence.get(d["id"])))
    if errors:
        return None, errors
    applicable = [r for r in rows if r["score"] is not None]
    if not applicable:
        return None, ["全部维度都是 N/A，没有可计分的内容"]
    w = sum(r["weight"] for r in applicable)
    total = round(sum(r["score"] * r["weight"] for r in applicable) / w, 1)
    return {"scorecard_version": card["version"], "total": total, "grade": grade_of(total, card["grades"]),
            "applicable_weight": w, "dimensions": rows,
            "failed_checks": list(scores.get("failed_checks") or [])}, []


def filings(card, result, gate_fails, owner, deadline_hours, now=None):
    now = now or datetime.now(timezone.utc)
    pr = card["priority"]
    out = []

    def add(rule, prio, title, ev):
        out.append({"title": title, "trigger": rule, "priority": prio, "evidence": ev,
                    "remediation": "改到对应门禁/维度复验通过；验收标准见 references/gate-checklist.md",
                    "owner": owner, "deadline": (now + timedelta(hours=deadline_hours)).isoformat()})

    for g in gate_fails:
        add("gate_fail", pr.get("gate_fail", "P0"), f"发布门禁 {g['gate_id']} FAIL", g["ref"])
    total = result["total"]
    if total < 70:
        add("total_below_70", pr.get("total_below_70", "P0"), f"总分 {total} < 70（{result['grade']}）", f"total={total}")
    elif total < card["total_below"]:
        add("total_below_85", pr.get("total_below_85", "P1"), f"总分 {total} < {card['total_below']}（低于 A）", f"total={total}")
    for r in result["dimensions"]:
        if r["score"] is not None and r["score"] < card["dimension_below"]:
            add("dimension_below_70", pr.get("dimension_below_70", "P1"),
                f"维度 {r['name_zh']} {r['score']:g} < {card['dimension_below']}", f"{r['id']}={r['score']:g}")
    if not out and result["failed_checks"]:
        add("check_fail_only", pr.get("check_fail_only", "P2"), "仅检查项失败、总分达标",
            ", ".join(result["failed_checks"]))
    return out


def markdown(result, files):
    lines = ["## 11 维度打分", "| 维度 | 权重 | 得分 | 加权 |", "|---|---|---|---|"]
    w = result["applicable_weight"]
    for r in result["dimensions"]:
        if r["score"] is None:
            lines.append(f"| {r['name_zh']} | {r['weight']} | N/A（{r['na_reason']}） | 剔除 |")
        else:
            lines.append(f"| {r['name_zh']} | {r['weight']} | {r['score']:g} | {r['score'] * r['weight'] / w:.1f} |")
    lines.append(f"| 总分 | {w}（适用） | — | {result['total']} → 等级 {result['grade']} |")
    lines += ["", "## 立案"]
    if not files:
        lines.append("未触发自动立案")
    for f in files:
        lines += [f"[立案 {f['deadline'][:10]}] {f['title']}", f"- 触发：{f['trigger']}（{f['priority']}）",
                  f"- 证据：{f['evidence']}", f"- 整改：{f['remediation']}", f"- 责任：{f['owner']}",
                  f"- 期限：{f['deadline']}"]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores", required=True)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--owner", default="")
    ap.add_argument("--deadline-hours", type=int, default=24)
    ap.add_argument("--record", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    card = load_scorecard()
    with open(a.scores, encoding="utf-8") as f:
        scores = json.load(f)
    result, errors = compute(card, scores)
    if errors:
        for e in errors:
            print(f"INPUT ERROR: {e}", file=sys.stderr)
        return 2

    gate_fails = []
    if a.run_id:
        with open(ledger_path(), encoding="utf-8") as f:
            ledger = json.load(f)
        run = next((r for r in reversed(ledger.get("runs", [])) if r.get("run_id") == a.run_id), None)
        if run is None:
            print(f"INPUT ERROR: 台账里没有 run {a.run_id}", file=sys.stderr)
            return 2
        for g in run["gates"]:
            if g["verdict"] == "fail":
                outs = [e["ref"] for e in g["evidence"] if e.get("type") == "output"] or [e["ref"] for e in g["evidence"]]
                gate_fails.append({"gate_id": g["gate_id"], "ref": outs[-1][:200]})

    files = filings(card, result, gate_fails, a.owner.strip(), a.deadline_hours)
    if files and not a.owner.strip():
        print("INPUT ERROR: 触发了立案，必须用 --owner 指定责任人", file=sys.stderr)
        return 2
    record = dict(result, run_id=a.run_id, at=datetime.now(timezone.utc).isoformat(), filings=files)
    if a.record:
        with locked_ledger(ledger_path()) as (ledger, save):
            seal(ledger, "scores", record)
            save(ledger)
    print(json.dumps(record, ensure_ascii=False, indent=2) if a.json else markdown(result, files))
    return 3 if files else 0


if __name__ == "__main__":
    sys.exit(main())
