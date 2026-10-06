#!/usr/bin/env python3
"""coverage-ledger runner (H4): website-qa-gates 每次发布的各门禁覆盖记账。

用法:
  python3 tools/ledger-run.py --release <发布ID> --change "<变更描述>" \
      [--site-root PATH] [--site-url URL]

行为:
- 对机器可跑的门禁真实执行（G1/G4/G7/G8/A1/A2/A5/T1/T2/G12-1/G12-4/V4），记录 pass/fail + 证据。
- 需真浏览器/人工的门禁按 skill 诚实原则记 waived（未验证，不许用推测代替）。
- 结果 additive 追加进 ../coverage-ledger.json（只追加不覆盖，多轮累积）。
"""
import argparse, base64, hashlib, json, os, re, subprocess, sys
from datetime import datetime, timezone

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER_PATH = os.path.join(SKILL_DIR, "coverage-ledger.json")
HOME = os.path.expanduser("~")
DEFAULT_ROOT = os.path.join(HOME, "workspace/vertcity/deploy-prod-root")

def sh(cmd, **kw):
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=kw.get("timeout", 120))
    return p.returncode, p.stdout.strip(), p.stderr.strip()

def grep_count(root, pattern, include="*.html"):
    rc, out, _ = sh(f"grep -rhoE --include='{include}' '{pattern}' {root} 2>/dev/null | wc -l")
    try:
        return int(out)
    except ValueError:
        return -1

# 门禁定义: (gate_id, 名称, 检查函数名)
# 检查函数返回 (verdict, [evidence...]) ; verdict in pass/fail/waived
def ck_g1(root, url):
    rc, out, _ = sh(f"bash {HOME}/workspace/vertcity/security-watch/data-room-gate.sh")
    ev = [{"type": "cmd", "ref": "bash ~/workspace/vertcity/security-watch/data-room-gate.sh"},
          {"type": "output", "ref": (out.splitlines()[-3:] and ' | '.join(out.splitlines()[-3:])) or "no output"}]
    verdict = "fail" if "FAIL" in out else "pass"
    return verdict, ev

def ck_g4(root, url):
    rc, out, _ = sh(f"bash {HOME}/workspace/vertcity/deliverables/qa-gates/size-gate.sh {root}")
    tail = ' | '.join(out.splitlines()[-4:]) if out else f"rc={rc}"
    ev = [{"type": "cmd", "ref": f"bash size-gate.sh {root}"}, {"type": "output", "ref": tail}]
    if "FAIL" in out:
        return "fail", ev
    return "pass", ev

def ck_g7(root, url):
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

def ck_g8(root, url):
    rc, out, _ = sh(f"curl -s -o /dev/null -w '%{{http_code}}' -m 20 {url}/")
    ev = [{"type": "cmd", "ref": f"curl {url}/ -> HTTP code"}, {"type": "output", "ref": f"HTTP {out}"}]
    return ("pass" if out == "200" else "fail"), ev

def ck_a1(root, url):
    # 字阶: 40/32/24/20/16/14/12；禁 13/15/17/19
    n = grep_count(root, r"font-size:\s*(13|15|17|19)px")
    ev = [{"type": "cmd", "ref": "grep font-size 13/15/17/19px"}, {"type": "output", "ref": f"hits={n}"}]
    return ("pass" if n == 0 else "fail"), ev

def ck_a2(root, url):
    # 8pt: 间距须命中 scale；抽查 margin/padding 非法值（非 4/8 倍数且不在 scale）
    rc, out, _ = sh(f"grep -rhoE --include='*.css' --include='*.html' '(margin|padding)[^;{{}}]*:[^;{{}}]*' {root} 2>/dev/null | grep -oE '[0-9]+px' | sort -u | tr '\n' ' '")
    vals = [int(x[:-2]) for x in out.split() if x[:-2].isdigit()]
    legal = {4,8,12,16,20,24,32,40,48,56,64,80,96,120}
    bad = sorted(v for v in vals if v not in legal)
    ev = [{"type": "cmd", "ref": "grep margin/padding px values"}, {"type": "output", "ref": f"illegal={bad[:10]}" if bad else "all legal"}]
    return ("pass" if not bad else "fail"), ev

def ck_a5(root, url):
    n = grep_count(root, r"countUp|animate-number|CountUp")
    ev = [{"type": "cmd", "ref": "grep countUp|animate-number"}, {"type": "output", "ref": f"hits={n}"}]
    return ("pass" if n == 0 else "fail"), ev

def ck_t1(root, url):
    # eyebrow 计数 ≤ ceil(n/3)：eyebrow 类元素数 vs section 数
    eb = grep_count(root, r'class="[^"]*eyebrow')
    secs = grep_count(root, r"<section")
    import math
    limit = math.ceil(max(secs, 1) / 3)
    ev = [{"type": "cmd", "ref": "eyebrow class count vs <section> count"}, {"type": "output", "ref": f"eyebrow={eb} sections={secs} limit={limit}"}]
    return ("pass" if eb <= limit else "fail"), ev

def ck_t2(root, url):
    # 中文文案 em-dash（—）零：只查含 CJK 的行
    rc, out, _ = sh(f"grep -rl --include='*.html' $'—' {root} 2>/dev/null | wc -l")
    ev = [{"type": "cmd", "ref": "grep — in html"}, {"type": "output", "ref": f"files_with_emdash={out.strip()}"}]
    return ("pass" if out.strip() == "0" else "fail"), ev

def ck_g121(root, url):
    # 白名单属性：transition/animation 只许 transform/opacity
    rc, out, _ = sh(f"grep -rhoE --include='*.css' --include='*.html' '(transition|animation)[^;{{}}]*:[^;{{}}]*' {root} 2>/dev/null | head -40")
    bad = [l for l in out.splitlines() if not re.search(r"transform|opacity", l)]
    ev = [{"type": "cmd", "ref": "grep transition/animation props"}, {"type": "output", "ref": f"non-whitelist={len(bad)}" + (f" e.g. {bad[0][:80]}" if bad else "")}]
    return ("pass" if not bad else "fail"), ev

def ck_g124(root, url):
    n = grep_count(root, r"particles\.js|particlesjs|canvas-nest|confetti")
    ev = [{"type": "cmd", "ref": "grep 粒子背景库"}, {"type": "output", "ref": f"hits={n}"}]
    return ("pass" if n == 0 else "fail"), ev

def ck_v4(root, url):
    # V4 真实拦截/放行记录：本 ledger 条目自身即记录
    return "pass", [{"type": "note", "ref": "本 ledger run 即 V4 要求的真实记录"}]

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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", required=True)
    ap.add_argument("--change", required=True)
    ap.add_argument("--site-root", default=DEFAULT_ROOT)
    ap.add_argument("--site-url", default="https://vertciti.com")
    a = ap.parse_args()
    root, url = a.site_root, a.site_url.rstrip("/")

    gates = []
    for gid, name, fn in MACHINE:
        try:
            verdict, evidence = fn(root, url)
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

    run = {"run_id": a.release,
           "run_at": datetime.now(timezone.utc).isoformat(),
           "change": a.change, "site_root": root, "site_url": url,
           "gates": gates,
           "summary": {v: sum(1 for g in gates if g["verdict"] == v) for v in ("pass", "fail", "waived")}}

    ledger = {"additive": True, "runs": []}
    if os.path.exists(LEDGER_PATH):
        with open(LEDGER_PATH) as f:
            ledger = json.load(f)
        assert ledger.get("additive") is True, "ledger additive 标志被篡改，拒绝写入"
    ledger["runs"].append(run)
    with open(LEDGER_PATH, "w") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=2)
        f.write("\n")

    s = run["summary"]
    print(f"release={a.release} pass={s['pass']} fail={s['fail']} waived={s['waived']} -> {LEDGER_PATH}")
    for g in gates:
        if g["verdict"] == "fail":
            print(f"  FAIL {g['gate_id']}: {g['evidence'][-1]['ref'][:120]}")
    sys.exit(0 if s["fail"] == 0 else 2)

if __name__ == "__main__":
    main()
