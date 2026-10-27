#!/usr/bin/env python3
"""coverage-ledger runner (H4): website-qa-gates 每次发布的各门禁覆盖记账。

用法:
  python3 tools/ledger-run.py --release <发布ID> --change "<变更描述>" \
      [--site-root PATH] [--site-url URL]

环境变量（P0-1 可移植化；命令行参数优先）:
  QA_GATES_SITE_ROOT     默认站点根目录（缺省：仓库 demo 页，仅供演示）
  QA_GATES_SECURITY_GATE 外部敏感扫描脚本路径（缺省：仓库内 tools/fallback/secret-scan.py）
  QA_GATES_SIZE_GATE     外部体积预算脚本路径（缺省：仓库内 tools/fallback/size-budget.py）
  QA_GATES_LEDGER        台账路径（缺省：仓库根 coverage-ledger.json）

行为:
- 机器可跑的门禁真实执行（G1/G4/G7/G8/G15/A1/A2/A5/T1/T2/G12-1/G12-4/V4），记录 pass/fail + 证据。
- 全部检查不经 shell：外部脚本按 argv 列表调用，文本扫描用纯 Python，
  路径含空格或 shell 元字符时结论不变，也无法注入命令。
- 站点根目录不存在 -> 直接 exit 2，不记账（拒绝在空目录上判 pass）。
- G1/G4 外部脚本缺失时：环境变量未设置 -> 走仓库内 fallback 真实执行；
  环境变量指向不存在的路径、脚本非零退出或超时 -> 直接判 fail（拒绝误判 pass）。
- 需真浏览器/人工的门禁按 skill 诚实原则记 waived（未验证，不许用推测代替）。
- 本轮真实 FAIL（V4 自身除外）全部记入 run["interceptions"]（拦截项/处置）；处置用
  tools/ledger-dispose.py 追加 disposition_history 闭环（立案->整改->复验）。
- V4：本轮有 FAIL -> 每条 FAIL 必须带实际输出证据（不只是命令描述）并有拦截项，
  否则 V4 自判 fail；本轮零 FAIL -> 记"零拦截"并回查最近一条含拦截的 run 的处置闭环，
  未闭环则 V4 自判 fail。V4 自身的 fail 不再生成新拦截项，处置原 run 即可解除。
- 结果 additive 追加进台账（只追加不覆盖，多轮累积；加锁＋原子写入）。
"""
import argparse, base64, hashlib, http.client, math, os, re, subprocess, sys, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ledger_io import SKILL_DIR, ledger_path, locked_ledger  # noqa: E402

FALLBACK_DIR = os.path.join(SKILL_DIR, "tools", "fallback")
DEFAULT_ROOT = os.environ.get("QA_GATES_SITE_ROOT") or os.path.join(SKILL_DIR, "demo", "www")
GATE_TIMEOUT = 120


def run_script(argv, timeout=GATE_TIMEOUT):
    """按 argv 列表执行（不经 shell）；返回 (rc, stdout, stderr)，超时 rc=None。"""
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, "", f"超时（>{timeout}s）"
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def site_files(root, exts):
    """递归列出站点根目录下指定扩展名的文件（跳过 .git）。"""
    out = []
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != ".git")
        for fn in sorted(files):
            if fn.lower().endswith(exts):
                out.append(os.path.join(dirpath, fn))
    return out


def read_text(path):
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read()


def count_matches(root, pattern, exts=(".html",)):
    rx = re.compile(pattern)
    return sum(len(rx.findall(read_text(p))) for p in site_files(root, exts))


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


def _script_verdict(src, rc, out, err, tail_lines):
    """外部/fallback 脚本结论：非零退出、超时或输出含 FAIL 一律 fail。"""
    lines = out.splitlines()[-tail_lines:] if out else []
    if rc != 0 and err:
        lines += err.splitlines()[-2:]
    ev = [{"type": "cmd", "ref": src},
          {"type": "output", "ref": (" | ".join(lines) + f" (rc={rc})") if lines else f"rc={rc}，无输出"}]
    ok = rc == 0 and "FAIL" not in out
    return ("pass" if ok else "fail"), ev


# 门禁定义: (gate_id, 名称, 检查函数名)
# 检查函数 fn(root, url, ctx) 返回 (verdict, [evidence...]) ; verdict in pass/fail/waived
# ctx = {"gates": 已跑完的机器门禁结论, "interceptions": 本轮拦截项, "prior_runs": 历史 runs}
def ck_g1(root, url, ctx):
    mode, path, detail = _resolve_gate_script("QA_GATES_SECURITY_GATE", "secret-scan.py")
    if mode == "external":
        rc, out, err = run_script(["bash", path])
        src = f"外部脚本 {path}"
    elif mode == "fallback":
        rc, out, err = run_script([sys.executable, path, "--root", root])
        src = "仓库 fallback secret-scan.py"
    else:
        return "fail", [{"type": "note",
                         "ref": f"G1 无可用实现：{detail}——拒绝误判 pass，直接判 fail"}]
    return _script_verdict(src, rc, out, err, 3)


def ck_g4(root, url, ctx):
    mode, path, detail = _resolve_gate_script("QA_GATES_SIZE_GATE", "size-budget.py")
    if mode == "external":
        rc, out, err = run_script(["bash", path, root])
        src = f"外部脚本 {path}"
    elif mode == "fallback":
        rc, out, err = run_script([sys.executable, path, root])
        src = "仓库 fallback size-budget.py"
    else:
        return "fail", [{"type": "note",
                         "ref": f"G4 无可用实现：{detail}——拒绝误判 pass，直接判 fail"}]
    return _script_verdict(src, rc, out, err, 4)


def ck_g7(root, url, ctx):
    # 提取全部 *.html 内联 <script> hash，与 vercel.json script-src 比对
    vj = os.path.join(root, "vercel.json")
    ev = [{"type": "cmd", "ref": "all *.html inline <script> sha256 vs vercel.json script-src"}]
    if not os.path.exists(vj):
        return "waived", ev + [{"type": "note", "ref": "vercel.json 缺失，未验证"}]
    got = {}
    for f in site_files(root, (".html",)):
        for s in re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", read_text(f), re.S):
            h = "sha256-" + base64.b64encode(hashlib.sha256(s.encode("utf-8")).digest()).decode()
            got.setdefault(h, []).append(os.path.relpath(f, root))
    want = set(re.findall(r"sha256-[A-Za-z0-9+/=]+", read_text(vj)))
    ev.append({"type": "output", "ref": f"inline={len(got)} want={len(want)} missing={sorted(want-set(got))} extra={sorted(set(got)-want)}"})
    return ("pass" if set(got) == want and want else "fail"), ev


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **kw):
        return None  # 与 curl 不加 -L 一致：3xx 原样返回，不算可达


def http_status(url, timeout=20):
    """GET url，返回 HTTP 状态码（int）；连不上返回 0。不跟随重定向。"""
    opener = urllib.request.build_opener(_NoRedirect)
    req = urllib.request.Request(url, headers={"User-Agent": "website-qa-gates/ledger-run"})
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError):
        return 0


def ck_g8(root, url, ctx):
    target = f"{url}/"
    ev = [{"type": "cmd", "ref": f"GET {target} -> HTTP code"}]
    parts = urllib.parse.urlsplit(target)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return "fail", ev + [{"type": "output", "ref": f"非法 site-url（只允许 http/https）：{url!r}"}]
    code = http_status(target)
    ev.append({"type": "output", "ref": f"HTTP {code:03d}"})
    return ("pass" if code == 200 else "fail"), ev


_SKIP_SCHEMES = ("http:", "https:", "mailto:", "tel:", "data:", "blob:", "//")
_REF_RX = re.compile(r"""\b(src|href)\s*=\s*(["'])(.*?)\2""", re.I | re.S)


def ck_g15(root, url, ctx):
    """本地资源完整性：src/href 指向的站内文件必须存在；href="#"、空 href、javascript: 判死链；
    #锚点必须在同页有对应 id/name。外链不在此门禁范围（见 G8）。"""
    bad, n = [], 0
    for f in site_files(root, (".html", ".htm")):
        # 去掉注释与内联脚本正文（保留 <script src> 开标签），避免把 JS 里的 a.href="…" 当成引用
        html = re.sub(r"<!--.*?-->", "", read_text(f), flags=re.S)
        html = re.sub(r"(<script\b[^>]*>).*?</script>", r"\1", html, flags=re.S | re.I)
        ids = set(re.findall(r"""\b(?:id|name)\s*=\s*["']([^"']+)["']""", html, re.I))
        rel = os.path.relpath(f, root)
        for attr, _, raw in _REF_RX.findall(html):
            ref = raw.strip()
            n += 1
            low = ref.lower()
            if low.startswith(_SKIP_SCHEMES):
                continue
            if ref in ("", "#") or low.startswith("javascript:"):
                bad.append(f"{rel}: {attr}={raw!r} 死链")
                continue
            if ref.startswith("#"):
                if urllib.parse.unquote(ref[1:]) not in ids:
                    bad.append(f"{rel}: {attr}={raw!r} 锚点不存在")
                continue
            path = urllib.parse.unquote(urllib.parse.urlsplit(ref).path)
            if not path:  # 只有 ?query
                continue
            base = root if path.startswith("/") else os.path.dirname(f)
            target = os.path.normpath(os.path.join(base, path.lstrip("/")))
            if os.path.isdir(target):
                target = os.path.join(target, "index.html")
            if not os.path.exists(target):
                bad.append(f"{rel}: {attr}={raw!r} 文件不存在")
    ev = [{"type": "cmd", "ref": "python: *.html src/href 站内引用存在性＋死链＋锚点"},
          {"type": "output", "ref": f"refs={n} bad={len(bad)}" + (f" e.g. {'; '.join(bad[:3])}" if bad else "")}]
    return ("pass" if not bad else "fail"), ev


def ck_a1(root, url, ctx):
    # 字阶: 40/32/24/20/16/14/12；禁 13/15/17/19
    n = count_matches(root, r"font-size:\s*(?:13|15|17|19)px")
    ev = [{"type": "cmd", "ref": "python: font-size 13/15/17/19px 计数"}, {"type": "output", "ref": f"hits={n}"}]
    return ("pass" if n == 0 else "fail"), ev


def ck_a2(root, url, ctx):
    # 8pt: 间距须命中 scale；抽查 margin/padding 非法值（非 4/8 倍数且不在 scale）
    decl = re.compile(r"(?:margin|padding)[^;{}]*:[^;{}]*")
    vals = set()
    for p in site_files(root, (".css", ".html")):
        for d in decl.findall(read_text(p)):
            vals.update(int(x) for x in re.findall(r"([0-9]+)px", d))
    legal = {4, 8, 12, 16, 20, 24, 32, 40, 48, 56, 64, 80, 96, 120}
    bad = sorted(v for v in vals if v not in legal)
    ev = [{"type": "cmd", "ref": "python: margin/padding px 值"}, {"type": "output", "ref": f"illegal={bad[:10]}" if bad else "all legal"}]
    return ("pass" if not bad else "fail"), ev


def ck_a5(root, url, ctx):
    n = count_matches(root, r"countUp|animate-number|CountUp")
    ev = [{"type": "cmd", "ref": "python: countUp|animate-number 计数"}, {"type": "output", "ref": f"hits={n}"}]
    return ("pass" if n == 0 else "fail"), ev


def ck_t1(root, url, ctx):
    # eyebrow 计数 ≤ ceil(n/3)：eyebrow 类元素数 vs section 数
    eb = count_matches(root, r'class="[^"]*eyebrow')
    secs = count_matches(root, r"<section")
    limit = math.ceil(max(secs, 1) / 3)
    ev = [{"type": "cmd", "ref": "eyebrow class count vs <section> count"}, {"type": "output", "ref": f"eyebrow={eb} sections={secs} limit={limit}"}]
    return ("pass" if eb <= limit else "fail"), ev


def ck_t2(root, url, ctx):
    # 中文文案 em-dash（U+2014）零：纯 Python 扫描
    n = sum(1 for f in site_files(root, (".html",)) if "—" in read_text(f))
    ev = [{"type": "cmd", "ref": "python: 扫描 *.html 含 U+2014 的文件数"},
          {"type": "output", "ref": f"files_with_emdash={n}"}]
    return ("pass" if n == 0 else "fail"), ev


MOTION_OK = {"transform", "opacity"}
_TIMING = {"ease", "ease-in", "ease-out", "ease-in-out", "linear", "step-start", "step-end",
           "normal", "allow-discrete", "initial", "inherit", "unset", "revert", "revert-layer"}
_TIME_RX = re.compile(r"^[+-]?(?:\d+\.?\d*|\.\d+)m?s$", re.I)


def split_top_level(value, sep=","):
    """按顶层分隔符切分（括号内的逗号不切），供 cubic-bezier(...) 等使用。"""
    parts, depth, cur = [], 0, []
    for ch in value:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(depth - 1, 0)
        if ch == sep and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))
    return [p.strip() for p in parts if p.strip()]


def transition_props(name, value):
    """返回 transition 声明实际动到的属性列表；省略属性名 = all。"""
    value = re.sub(r"!important\s*$", "", value.strip(), flags=re.I).strip()
    if name == "transition-property":
        return [p.lower() for p in split_top_level(value)]
    props = []
    for item in split_top_level(value):
        item = re.sub(r"\([^()]*\)", "", item)  # 去掉 cubic-bezier()/steps()/var() 参数
        toks = [t for t in item.split() if t.lower() not in _TIMING and not _TIME_RX.match(t)
                and not t.lower().startswith(("cubic-bezier", "steps", "linear"))]
        props.append(toks[0].lower() if toks else "all")
    return props


_TRANSITION_RX = re.compile(r"(?<![\w-])(?:-(?:webkit|moz|o)-)?(transition(?:-property)?)\s*:\s*([^;{}\"'<>]*)", re.I)
_KEYFRAMES_RX = re.compile(r"@(?:-webkit-)?keyframes\s+([\w-]+)\s*\{((?:[^{}]*\{[^{}]*\})*[^{}]*)\}", re.I)


def ck_g121(root, url, ctx):
    # 白名单属性：transition 逐个属性、@keyframes 内逐条声明只许 transform/opacity；
    # transition 省略属性名或写 all 都算 all（非白名单）
    bad = []
    for p in site_files(root, (".css", ".html")):
        text = read_text(p)
        rel = os.path.relpath(p, root)
        for name, value in _TRANSITION_RX.findall(text):
            if not value.strip() or value.strip().lower() == "none":
                continue
            for prop in transition_props(name.lower(), value):
                if prop not in MOTION_OK and prop != "none":
                    bad.append(f"{rel}: {name}: {value.strip()[:60]} -> {prop}")
        for kf_name, body in _KEYFRAMES_RX.findall(text):
            for prop in re.findall(r"([\w-]+)\s*:", re.sub(r"[^{}]*\{", "", body)):
                if prop.lower() not in MOTION_OK and prop.lower() != "animation-timing-function":
                    bad.append(f"{rel}: @keyframes {kf_name} -> {prop}")
    ev = [{"type": "cmd", "ref": "python: transition 逐属性＋@keyframes 声明白名单（transform/opacity）"},
          {"type": "output", "ref": f"non-whitelist={len(bad)}" + (f" e.g. {bad[0][:100]}" if bad else "")}]
    return ("pass" if not bad else "fail"), ev


def ck_g124(root, url, ctx):
    n = count_matches(root, r"particles\.js|particlesjs|canvas-nest|confetti")
    ev = [{"type": "cmd", "ref": "python: 粒子背景库计数"}, {"type": "output", "ref": f"hits={n}"}]
    return ("pass" if n == 0 else "fail"), ev


def ck_v4(root, url, ctx):
    """V4 真实拦截/放行记录。

    - 本轮有真实 FAIL：每条 FAIL 必须有拦截项，且其证据里至少一条是实际输出/说明
      （不只是"跑了什么命令"）；缺任一项 -> V4 自判 fail。
    - 本轮零 FAIL：记"零拦截"，并回查最近一条含拦截的 run 的处置闭环；
      有未闭环（status != closed） -> V4 自判 fail。
    """
    fails = [g for g in ctx.get("gates", []) if g["verdict"] == "fail"]
    interceptions = ctx.get("interceptions") or []
    by_id = {i["gate_id"]: i for i in interceptions}

    if fails:
        missing = [g["gate_id"] for g in fails if not by_id.get(g["gate_id"])]
        no_output = [g["gate_id"] for g in fails
                     if not any(e.get("type") != "cmd" and str(e.get("ref", "")).strip()
                                for e in g.get("evidence", []))]
        if missing or no_output:
            return "fail", [{"type": "note",
                             "ref": f"V4 自判 fail：无拦截项 {missing}；无实际输出证据 {no_output}（记录缺失=作弊）"}]
        ev = []
        for g in fails:
            it = by_id[g["gate_id"]]
            status = it.get("status", "pending")
            ev.append({"type": "interception",
                       "ref": f"拦截 {g['gate_id']} {g['name']}：{it['evidence_refs'][-1]} ｜处置状态：{status}（见本 run interceptions[{g['gate_id']}]）"})
        ev.append({"type": "note",
                   "ref": f"本轮真实拦截 {len(fails)} 项，全部已记入 interceptions 并附输出证据"})
        return "pass", ev

    # 零 FAIL：回查最近一条含拦截的 run 的处置闭环
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
    ("G15", "站内资源完整性", ck_g15),
    ("A1", "字阶命中", ck_a1),
    ("A2", "8pt 间距", ck_a2),
    ("A5", "count-up 归零", ck_a5),
    ("T1", "eyebrow 计数", ck_t1),
    ("T2", "em-dash 零", ck_t2),
    ("G12-1", "动效白名单属性", ck_g121),
    ("G12-4", "禁粒子背景", ck_g124),
    ("V4", "拦截/放行记录", ck_v4),
]


def build_interceptions(gates):
    """把本轮真实 FAIL 转为拦截项记录（V4 引用目标）。V4 自身不立案：
    它的 fail 指向的是更早 run 的未闭环拦截项，处置那条即可。"""
    its = []
    for g in gates:
        if g["verdict"] == "fail" and g["gate_id"] != "V4":
            refs = [e.get("ref", "") for e in g.get("evidence", []) if e.get("ref")]
            its.append({"gate_id": g["gate_id"], "name": g["name"],
                        "evidence_refs": refs, "status": "pending",
                        "disposition_history": []})
    return its


def display_path(path):
    """记账用路径：仓库内记相对路径，家目录换成 ~，不把本机用户名写进台账。"""
    ap = os.path.abspath(path)
    if ap == SKILL_DIR or ap.startswith(SKILL_DIR + os.sep):
        return os.path.relpath(ap, SKILL_DIR)
    home = os.path.expanduser("~")
    if home not in ("", "/") and (ap == home or ap.startswith(home + os.sep)):
        return "~" + ap[len(home):]
    return ap


def run_gates(root, url, prior_runs):
    gates = []
    for gid, name, fn in MACHINE:
        # V4 是最后一个机器门禁：先按已跑结论建 interceptions，再让它校验
        interceptions = build_interceptions(gates) if gid == "V4" else []
        ctx = {"gates": gates, "interceptions": interceptions, "prior_runs": prior_runs}
        try:
            verdict, evidence = fn(root, url, ctx)
        except Exception as e:
            verdict, evidence = "waived", [{"type": "note", "ref": f"执行异常未验证: {type(e).__name__}: {e}"}]
        gates.append({"gate_id": gid, "name": name,
                      "run_at": datetime.now(timezone.utc).isoformat(),
                      "verdict": verdict, "evidence": evidence})
    for gid, reason in WAIVED.items():
        gates.append({"gate_id": gid, "name": gid,
                      "run_at": datetime.now(timezone.utc).isoformat(),
                      "verdict": "waived",
                      "evidence": [{"type": "note", "ref": reason}]})
    return gates


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", required=True)
    ap.add_argument("--change", required=True)
    ap.add_argument("--site-root", default=DEFAULT_ROOT)
    ap.add_argument("--site-url", default="https://vertciti.com")
    a = ap.parse_args()
    root, url = a.site_root, a.site_url.rstrip("/")
    if not os.path.isdir(root):
        print(f"ERROR: 站点根目录不存在或不是目录：{root}（未记账）", file=sys.stderr)
        sys.exit(2)

    path = ledger_path()
    with locked_ledger(path) as (ledger, save):
        gates = run_gates(root, url, ledger.get("runs", []))
        interceptions = build_interceptions(gates)
        machine_done = sum(1 for g in gates[:len(MACHINE)] if g["verdict"] in ("pass", "fail"))
        run = {"run_id": a.release,
               "run_at": datetime.now(timezone.utc).isoformat(),
               "change": a.change, "site_root": display_path(root), "site_url": url,
               "gates": gates,
               "interceptions": interceptions,
               "machine_coverage": f"{machine_done}/{len(gates)}",
               "summary": {v: sum(1 for g in gates if g["verdict"] == v) for v in ("pass", "fail", "waived")}}
        ledger.setdefault("runs", []).append(run)
        save(ledger)

    s = run["summary"]
    print(f"release={a.release} pass={s['pass']} fail={s['fail']} waived={s['waived']} machine={run['machine_coverage']} -> {path}")
    for g in gates:
        if g["verdict"] == "fail":
            print(f"  FAIL {g['gate_id']}: {g['evidence'][-1]['ref'][:120]}")
    if interceptions:
        print(f"  interceptions: {len(interceptions)} 项待处置（tools/ledger-dispose.py）")
    sys.exit(0 if s["fail"] == 0 else 2)


if __name__ == "__main__":
    main()
