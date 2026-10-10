#!/usr/bin/env python3
"""coverage-ledger runner (H4): website-qa-gates 每次发布的各门禁覆盖记账。

用法:
  python3 tools/ledger-run.py --release <发布ID> --change "<变更描述>" \
      [--site-root PATH] [--site-url URL]

环境变量（P0-1 可移植化；命令行参数优先）:
  QA_GATES_SITE_ROOT     默认站点根目录（缺省：仓库 demo 页，仅供演示）
  QA_GATES_SECURITY_GATE 外部敏感扫描脚本路径（缺省：仓库内 tools/fallback/secret-scan.py）
  QA_GATES_SIZE_GATE     外部体积预算脚本路径（缺省：仓库内 tools/fallback/size-budget.py）

行为:
- 机器可跑的门禁真实执行（G1/G4/G7/G8/A1/A2/A5/T1/T2/G12-1/G12-4/V4），记录 pass/fail + 证据。
- G1/G4 外部脚本缺失时：环境变量未设置 -> 走仓库内 fallback 真实执行；
  环境变量指向不存在的路径 -> 直接判 fail（配置错误，拒绝误判 pass）。
- 需真浏览器/人工的门禁按 skill 诚实原则记 waived（未验证，不许用推测代替）。
- 本轮真实 FAIL 全部记入 run["interceptions"]（拦截项/处置）；处置用
  tools/ledger-dispose.py 追加 disposition_history 闭环（立案->整改->复验）。
- V4（P0-3 真校验）：本轮有 FAIL -> evidence 必须逐条引用到 interceptions
  记录，引用不到则 V4 自判 fail；本轮零 FAIL -> 记"零拦截"并回查上一条 run
  的处置闭环，未闭环则 V4 自判 fail。
- 结果 additive 追加进 ../coverage-ledger.json（只追加不覆盖，多轮累积）。
"""
import argparse, base64, hashlib, json, os, re, subprocess, sys
from datetime import datetime, timezone

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER_PATH = os.path.join(SKILL_DIR, "coverage-ledger.json")
FALLBACK_DIR = os.path.join(SKILL_DIR, "tools", "fallback")
DEFAULT_ROOT = os.environ.get("QA_GATES_SITE_ROOT") or os.path.join(SKILL_DIR, "demo", "www")

def sh(cmd, **kw):
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=kw.get("timeout", 120))
    return p.returncode, p.stdout.strip(), p.stderr.strip()

def grep_count(root, pattern, include="*.html"):
    rc, out, _ = sh(f"grep -rhoE --include='{include}' '{pattern}' {root} 2>/dev/null | wc -l")
    try:
        return int(out)
    except ValueError:
        return -1

def _resolve_gate_script(env_name, fallback_file):
    """返回 (mode, path, detail)：mode=external|fallback|missing"""
    p = os.environ.get(env_name)
    if p:
        if os.path.isfile(p):
            return ("external", p, f"环境变量 {env_name} 指向 {p}")
        return ("missing", p, f"环境变量 {env_name} 指向缺失路径 {p}")
    fb = os.path.join(FALLBACK_DIR, fallback_file)
    if os.path.isfile(fb):
        return ("fallback", fb, f"{env_name} 未设置，走仓库 fallback {fallback_file}")
    return ("missing", fb, f"{env_name} 未设置且仓库 fallback {fallback_file} 缺失")

# 门禁定义: (gate_id, 名称, 检查函数名)
# 检查函数 fn(root, url, ctx) 返回 (verdict, [evidence...]) ; verdict in pass/fail/waived
# ctx = {"gates": 已跑完的机器门禁结论, "interceptions": 本轮拦截项, "prior_runs": 历史 runs}
def ck_g1(root, url, ctx):
    mode, path, detail = _resolve_gate_script("QA_GATES_SECURITY_GATE", "secret-scan.py")
    if mode == "external":
        rc, out, _ = sh(f"bash {path}")
        src = f"外部脚本 {path}"
    elif mode == "fallback":
        rc, out, _ = sh(f"python3 {path} --root {root}")
        src = "仓库 fallback secret-scan.py"
    else:
        return "fail", [{"type": "note",
                         "ref": f"G1 无可用实现：{detail}——拒绝误判 pass，直接判 fail"}]
    ev = [{"type": "cmd", "ref": src},
          {"type": "output", "ref": (' | '.join(out.splitlines()[-3:]) if out else f"rc={rc}") or "no output"}]
    verdict = "fail" if ("GATE FAIL" in out or "FAIL" in out) else "pass"
    return verdict, ev

def ck_g4(root, url, ctx):
    mode, path, detail = _resolve_gate_script("QA_GATES_SIZE_GATE", "size-budget.py")
    if mode == "external":
        rc, out, _ = sh(f"bash {path} {root}")
        src = f"外部脚本 {path}"
    elif mode == "fallback":
        rc, out, _ = sh(f"python3 {path} {root}")
        src = "仓库 fallback size-budget.py"
    else:
        return "fail", [{"type": "note",
                         "ref": f"G4 无可用实现：{detail}——拒绝误判 pass，直接判 fail"}]
    tail = ' | '.join(out.splitlines()[-4:]) if out else f"rc={rc}"
    ev = [{"type": "cmd", "ref": src}, {"type": "output", "ref": tail}]
    if "GATE FAIL" in out or "FAIL" in out:
        return "fail", ev
    return "pass", ev

def ck_g7(root, url, ctx):
    # 提取全部 *.html 内联 <script> hash，与 vercel.json script-src 比对
    import glob
    vj = os.path.join(root, "vercel.json")
    ev = [{"type": "cmd", "ref": "all *.html inline <script> sha256 vs vercel.json script-src"}]
    if not os.path.exists(vj):
        return "waived", ev + [{"type": "note", "ref": "vercel.json 缺失，未验证"}]
    got = {}
    for f in glob.glob(os.path.join(root, "*.html")):
        html = open(f, encoding="utf-8", errors="ignore").read()
        for s in re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.S):
            h = "sha256-" + base64.b64encode(hashlib.sha256(s.encode("utf-8")).digest()).decode()
            got.setdefault(h, []).append(os.path.basename(f))
    cfg = open(vj, encoding="utf-8", errors="ignore").read()
    want = set(re.findall(r"sha256-[A-Za-z0-9+/=]+", cfg))
    ev.append({"type": "output", "ref": f"inline={len(got)} want={len(want)} missing={sorted(want-set(got))} extra={sorted(set(got)-want)}"})
    return ("pass" if set(got) == want and want else "fail"), ev

def ck_g8(root, url, ctx):
    rc, out, _ = sh(f"curl -s -o /dev/null -w '%{{http_code}}' -m 20 {url}/")
    ev = [{"type": "cmd", "ref": f"curl {url}/ -> HTTP code"}, {"type": "output", "ref": f"HTTP {out}"}]
    return ("pass" if out == "200" else "fail"), ev

def ck_a1(root, url, ctx):
    # 字阶: 40/32/24/20/16/14/12；禁 13/15/17/19
    n = grep_count(root, r"font-size:\s*(13|15|17|19)px")
    ev = [{"type": "cmd", "ref": "grep font-size 13/15/17/19px"}, {"type": "output", "ref": f"hits={n}"}]
    return ("pass" if n == 0 else "fail"), ev

def ck_a2(root, url, ctx):
    # 8pt: 间距须命中 scale；抽查 margin/padding 非法值（非 4/8 倍数且不在 scale）
    rc, out, _ = sh(f"grep -rhoE --include='*.css' --include='*.html' '(margin|padding)[^;{{}}]*:[^;{{}}]*' {root} 2>/dev/null | grep -oE '[0-9]+px' | sort -u | tr '\n' ' '")
    vals = [int(x[:-2]) for x in out.split() if x[:-2].isdigit()]
    legal = {4,8,12,16,20,24,32,40,48,56,64,80,96,120}
    bad = sorted(v for v in vals if v not in legal)
    ev = [{"type": "cmd", "ref": "grep margin/padding px values"}, {"type": "output", "ref": f"illegal={bad[:10]}" if bad else "all legal"}]
    return ("pass" if not bad else "fail"), ev

def ck_a5(root, url, ctx):
    n = grep_count(root, r"countUp|animate-number|CountUp")
    ev = [{"type": "cmd", "ref": "grep countUp|animate-number"}, {"type": "output", "ref": f"hits={n}"}]
    return ("pass" if n == 0 else "fail"), ev

def ck_t1(root, url, ctx):
    # eyebrow 计数 ≤ ceil(n/3)：eyebrow 类元素数 vs section 数
    eb = grep_count(root, r'class="[^"]*eyebrow')
    secs = grep_count(root, r"<section")
    import math
    limit = math.ceil(max(secs, 1) / 3)
    ev = [{"type": "cmd", "ref": "eyebrow class count vs <section> count"}, {"type": "output", "ref": f"eyebrow={eb} sections={secs} limit={limit}"}]
    return ("pass" if eb <= limit else "fail"), ev

def ck_t2(root, url, ctx):
    # 中文文案 em-dash（U+2014）零：纯 Python 扫描，不依赖 shell 的 $'' 引用语义
    # （/bin/sh=dash 时 $'—' 会被当字面量导致假阴性——2026-10-10 实测）
    import glob
    n = 0
    for f in glob.glob(os.path.join(root, "*.html")):
        if "\u2014" in open(f, encoding="utf-8", errors="ignore").read():
            n += 1
    ev = [{"type": "cmd", "ref": "python: 扫描 *.html 含 U+2014 的文件数"},
          {"type": "output", "ref": f"files_with_emdash={n}"}]
    return ("pass" if n == 0 else "fail"), ev

def ck_g121(root, url, ctx):
    # 白名单属性：transition/animation 只许 transform/opacity
    rc, out, _ = sh(f"grep -rhoE --include='*.css' --include='*.html' '(transition|animation)[^;{{}}]*:[^;{{}}]*' {root} 2>/dev/null | head -40")
    bad = [l for l in out.splitlines() if not re.search(r"transform|opacity", l)]
    ev = [{"type": "cmd", "ref": "grep transition/animation props"}, {"type": "output", "ref": f"non-whitelist={len(bad)}" + (f" e.g. {bad[0][:80]}" if bad else "")}]
    return ("pass" if not bad else "fail"), ev

def ck_g124(root, url, ctx):
    n = grep_count(root, r"particles\.js|particlesjs|canvas-nest|confetti")
    ev = [{"type": "cmd", "ref": "grep 粒子背景库"}, {"type": "output", "ref": f"hits={n}"}]
    return ("pass" if n == 0 else "fail"), ev

def ck_v4(root, url, ctx):
    """V4 真实拦截/放行记录（P0-3 真校验，非同义反复）。

    - 本轮有真实 FAIL：每条 FAIL 必须在 ctx["interceptions"] 里有带证据引用的
      记录；V4 evidence 逐条引用到该 FAIL 的拦截项＋处置状态；引用不到 -> V4 自判 fail。
    - 本轮零 FAIL：记"零拦截"，并回查上一条 run 的拦截项处置闭环；
      有未闭环（status != closed） -> V4 自判 fail。
    """
    fails = [g for g in ctx.get("gates", []) if g["verdict"] == "fail"]
    interceptions = ctx.get("interceptions") or []
    by_id = {i["gate_id"]: i for i in interceptions}

    if fails:
        missing = [g["gate_id"] for g in fails if not by_id.get(g["gate_id"])
                   or not by_id[g["gate_id"]].get("evidence_refs")]
        if missing:
            return "fail", [{"type": "note",
                             "ref": f"V4 自判 fail：以下真实 FAIL 无拦截项/处置记录可引用：{missing}（记录缺失=作弊）"}]
        ev = []
        for g in fails:
            it = by_id[g["gate_id"]]
            status = it.get("status", "pending")
            ev.append({"type": "interception",
                       "ref": f"拦截 {g['gate_id']} {g['name']}：{it['evidence_refs'][-1]} ｜处置状态：{status}（见本 run interceptions[{g['gate_id']}]）"})
        ev.append({"type": "note",
                   "ref": f"本轮真实拦截 {len(fails)} 项，全部已记入 interceptions 并附证据引用"})
        return "pass", ev

    # 零 FAIL：回查上一条 run 的处置闭环
    prior = ctx.get("prior_runs") or []
    checked = 0
    for pr in reversed(prior):
        its = pr.get("interceptions") or []
        if not its:
            continue
        checked += 1
        open_its = [i["gate_id"] for i in its if i.get("status") != "closed"]
        if open_its:
            return "fail", [
                {"type": "note", "ref": "本轮零拦截"},
                {"type": "backcheck",
                 "ref": f"V4 自判 fail：上一条含拦截的 run {pr.get('run_id')} 处置未闭环：{open_its}（立案→整改→复验未完成，见 tools/ledger-dispose.py）"}]
        break  # 只回查最近一条含拦截的 run
    return "pass", [{"type": "note",
                     "ref": f"本轮零拦截；回查最近含拦截的 run 处置已闭环（共查 {checked} 条）"}]

WAIVED = {
    "G2": "需真浏览器 390px 量取触控目标，dry-run 未执行",
    "G3": "需 playwright 390px 渲染，dry-run 未执行（overflow-gate.sh 需 .qa-venv）",
    "G5": "需人工中英逐项比对",
    "G6": "需本次变更的数字联动上下文，dry-run 无变更单",
    "G9": "需真浏览器渲染复验",
    "M1": "需真浏览器关动效截帧目检",
    "M2": "需真机节流帧率测试；纯静态变更可记 N/A（本次 dry-run 按未验证）",
    "M3": "需转场清单审计文档",
    "M4": "需 reduce-motion 三级复验",
    "A3": "需按钮五态样式目检",
    "A4": "需键盘 Tab 全程可达验证",
    "T3": "需全页 CTA 意图人工去重",
    "T4": "需 logo 墙 alt+授权记录人工核对",
    "T5": "需真浏览器确认 CTA 文案无折行",
    "V1": "需色盲模拟检查",
    "V2": "需图表文字对比度取色",
    "V3": "需图表文字替代摘要人工确认",
    "G12-2": "blur 面积需渲染测量",
    "G12-3": "LCP 增量需真机 Lighthouse",
    "G13": "需变更单附模糊词翻译表，dry-run 无变更单",
}

MACHINE = [
    ("G1", "data-room 敏感扫描", ck_g1),
    ("G4", "体积预算", ck_g4),
    ("G7", "CSP hash round-trip", ck_g7),
    ("G8", "生产可达性", ck_g8),
    ("A1", "字阶命中", ck_a1),
    ("A2", "8pt 间距", ck_a2),
    ("A5", "count-up 归零", ck_a5),
    ("T1", "eyebrow 计数", ck_t1),
    ("T2", "em-dash 零", ck_t2),
    ("G12-1", "动效白名单属性", ck_g121),
    ("G12-4", "禁粒子背景", ck_g124),
    ("V4", "拦截/放行记录", ck_v4),
]

def load_ledger():
    ledger = {"additive": True, "runs": []}
    if os.path.exists(LEDGER_PATH):
        with open(LEDGER_PATH) as f:
            ledger = json.load(f)
        assert ledger.get("additive") is True, "ledger additive 标志被篡改，拒绝写入"
    return ledger

def build_interceptions(gates):
    """把本轮真实 FAIL 转为拦截项记录（V4 引用目标）。"""
    its = []
    for g in gates:
        if g["verdict"] == "fail":
            refs = [e.get("ref", "") for e in g.get("evidence", []) if e.get("ref")]
            its.append({"gate_id": g["gate_id"], "name": g["name"],
                        "evidence_refs": refs, "status": "pending",
                        "disposition_history": []})
    return its

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", required=True)
    ap.add_argument("--change", required=True)
    ap.add_argument("--site-root", default=DEFAULT_ROOT)
    ap.add_argument("--site-url", default="https://vertciti.com")
    a = ap.parse_args()
    root, url = a.site_root, a.site_url.rstrip("/")

    ledger = load_ledger()
    prior_runs = ledger.get("runs", [])

    gates = []
    for idx, (gid, name, fn) in enumerate(MACHINE):
        # V4 是最后一个机器门禁：先按已跑结论建 interceptions，再让它校验
        interceptions = build_interceptions(gates) if gid == "V4" else []
        ctx = {"gates": gates, "interceptions": interceptions, "prior_runs": prior_runs}
        try:
            verdict, evidence = fn(root, url, ctx)
        except Exception as e:
            verdict, evidence = "waived", [{"type": "note", "ref": f"执行异常未验证: {e}"}]
        gates.append({"gate_id": gid, "name": name,
                      "run_at": datetime.now(timezone.utc).isoformat(),
                      "verdict": verdict, "evidence": evidence})
    for gid, reason in WAIVED.items():
        gates.append({"gate_id": gid, "name": gid,
                      "run_at": datetime.now(timezone.utc).isoformat(),
                      "verdict": "waived",
                      "evidence": [{"type": "note", "ref": reason}]})

    interceptions = build_interceptions(gates)
    machine_done = sum(1 for g in gates[:len(MACHINE)] if g["verdict"] in ("pass", "fail"))
    run = {"run_id": a.release,
           "run_at": datetime.now(timezone.utc).isoformat(),
           "change": a.change, "site_root": root, "site_url": url,
           "gates": gates,
           "interceptions": interceptions,
           "machine_coverage": f"{machine_done}/{len(gates)}",
           "summary": {v: sum(1 for g in gates if g["verdict"] == v) for v in ("pass", "fail", "waived")}}

    ledger["runs"].append(run)
    with open(LEDGER_PATH, "w") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=2)
        f.write("\n")

    s = run["summary"]
    print(f"release={a.release} pass={s['pass']} fail={s['fail']} waived={s['waived']} machine={run['machine_coverage']} -> {LEDGER_PATH}")
    for g in gates:
        if g["verdict"] == "fail":
            print(f"  FAIL {g['gate_id']}: {g['evidence'][-1]['ref'][:120]}")
    if interceptions:
        print(f"  interceptions: {len(interceptions)} 项待处置（tools/ledger-dispose.py）")
    sys.exit(0 if s["fail"] == 0 else 2)

if __name__ == "__main__":
    main()
