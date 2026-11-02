#!/usr/bin/env python3
"""coverage-ledger runner (H4): website-qa-gates 每次发布的各门禁覆盖记账。

用法:
  python3 tools/ledger-run.py --release <发布ID> --change "<变更描述>" \
      [--site-root PATH] [--site-url URL] [--no-browser] [--lang zh|en]

环境变量（命令行参数优先）:
  QA_GATES_SITE_ROOT       默认站点根目录（缺省：仓库 demo 页，仅供演示）
  QA_GATES_SITE_URL        G8 要请求的线上地址（缺省：配置 site_url；都没有则 G8 记 waived）
  QA_GATES_CONFIG          门禁配置 JSON（缺省：仓库根 qa-gates.config.json）
  QA_GATES_SECURITY_GATE   外部敏感扫描脚本（以 `bash <脚本> <站点根目录>` 调用）
  QA_GATES_SIZE_GATE       外部体积预算脚本（以 `bash <脚本> <站点根目录>` 调用）
  QA_GATES_LEDGER          台账路径（缺省：仓库根 coverage-ledger.json）
  QA_GATES_EVIDENCE_DIR    浏览器证据（截图、axe JSON）目录（缺省：台账旁 qa-evidence/<发布ID>/）
  QA_GATES_REQUIRE_BROWSER =1 时浏览器不可用判 fail（CI 用），否则浏览器门禁记 waived
  QA_GATES_LANG            输出语言 zh（缺省）或 en

行为:
- 机器门禁真实执行，记录 pass/fail + 证据。静态：G1/G4/G5/G7/G8/G15/A1/A2/A5/T1/T2/G12-1/G12-4；
  真浏览器（tools/browser/gates.cjs，Playwright + axe-core）：G2/G3/G9/A4/M4/T5/G16，另为 M1 生成截图。
- 失败即关闭：门禁执行抛异常 -> 判 fail（附异常），不再记 waived 放行。
- 全部检查不经 shell：外部脚本按 argv 列表调用，文本扫描用纯 Python。
- 站点根目录不存在 -> 直接 exit 2，不记账。
- 需人工的门禁按诚实原则记 waived（未验证，不许用推测代替）。
- 本轮真实 FAIL（V4 自身除外）全部记入 run["interceptions"]；处置用 tools/ledger-dispose.py
  追加到台账 dispositions（两人关闭、进哈希链）。
- V4：本轮有 FAIL -> 每条 FAIL 必须带实际输出证据并有拦截项，否则 V4 自判 fail；本轮零 FAIL ->
  回查最近一条含拦截的 run，其拦截项当前状态（最近一条处置）未全部 closed 则 V4 自判 fail。
- 结果追加进台账：加锁＋原子写入＋哈希链封印（tools/ledger-verify.py 校验）。
"""
import argparse, base64, functools, hashlib, html as htmlmod, http.client, json, math, os, re, shutil, subprocess, sys
import tempfile, threading, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ledger_io import SKILL_DIR, interception_status, ledger_path, locked_ledger, seal  # noqa: E402
from qa_config import load_config  # noqa: E402
from site_refs import css_urls, html_refs, is_external, resolve_local, strip_html_noise  # noqa: E402

FALLBACK_DIR = os.path.join(SKILL_DIR, "tools", "fallback")
BROWSER_DIR = os.path.join(SKILL_DIR, "tools", "browser")
DEFAULT_ROOT = os.environ.get("QA_GATES_SITE_ROOT") or os.path.join(SKILL_DIR, "demo", "www")
GATE_TIMEOUT = 120

# 门禁名（zh, en）。台账里 name 记中文（向后兼容），name_en 记英文。
NAMES = {
    "G1": ("data-room 敏感扫描", "sensitive-content scan"),
    "G2": ("触控目标", "touch targets"),
    "G3": ("390px 零横向截断", "no horizontal overflow at 390px"),
    "G4": ("体积预算", "size budget"),
    "G5": ("中英镜像（机械项）", "zh/en mirror (mechanical)"),
    "G6": ("题材说明书机械项", "subject-sheet consistency"),
    "G7": ("CSP hash round-trip", "CSP hash round-trip"),
    "G8": ("生产可达性", "production reachability"),
    "G9": ("真机渲染复验", "real-browser render check"),
    "G12-1": ("动效白名单属性", "motion property whitelist"),
    "G12-2": ("blur 限面积", "blur area limit"),
    "G12-3": ("LCP 增量", "LCP increase"),
    "G12-4": ("禁粒子背景", "no particle backgrounds"),
    "G13": ("模糊词翻译", "vague-word translation"),
    "G15": ("站内资源完整性", "local resource integrity"),
    "G16": ("axe WCAG 自动扫描", "axe WCAG scan"),
    "A1": ("字阶命中", "type scale"),
    "A2": ("8pt 间距", "8pt spacing"),
    "A3": ("按钮五态", "button five states"),
    "A4": ("键盘可达与焦点环", "keyboard reach and focus ring"),
    "A5": ("count-up 归零", "no count-up"),
    "T1": ("eyebrow 计数", "eyebrow count"),
    "T2": ("em-dash 零", "no em-dash"),
    "T3": ("CTA 意图去重", "CTA intent dedupe"),
    "T4": ("logo 墙授权", "logo-wall licensing"),
    "T5": ("CTA 单行", "single-line CTA"),
    "M1": ("关动效静态帧", "static frame with motion off"),
    "M2": ("降速帧率", "throttled frame rate"),
    "M3": ("转场编排审计", "transition choreography audit"),
    "M4": ("减少动态效果", "reduced motion"),
    "V1": ("色盲安全", "colour-blind safety"),
    "V2": ("图表文字对比度", "chart text contrast"),
    "V3": ("图表文字替代", "chart text alternative"),
    "V4": ("拦截/放行记录", "interception record"),
}

# 需人工或外部材料的门禁：(zh 原因, en 原因)
WAIVED = {
    "G6": ("需本次变更的数字联动上下文，dry-run 无变更单", "needs the change's linked-number context"),
    "M2": ("需真机 CPU 节流帧率测试", "needs a throttled real-device frame-rate test"),
    "M3": ("需转场清单审计文档", "needs a transition audit document"),
    "A3": ("需按钮五态样式目检", "needs a visual check of five button states"),
    "T3": ("需全页 CTA 意图人工去重", "needs a manual CTA intent review"),
    "T4": ("需 logo 墙 alt+授权记录人工核对", "needs logo-wall licence records"),
    "V1": ("需色盲模拟检查", "needs a colour-blindness simulation review"),
    "V2": ("需图表文字对比度取色（全页文字对比度见 G16）", "needs chart text sampling (page text contrast is in G16)"),
    "V3": ("需图表文字替代摘要人工确认", "needs a manual check of chart text alternatives"),
    "G12-2": ("blur 面积需渲染测量", "blur area needs a rendered measurement"),
    "G12-3": ("LCP 增量需真机 Lighthouse", "LCP increase needs real-device Lighthouse"),
    "G13": ("需变更单附模糊词翻译表", "needs the vague-word translation table"),
}
BROWSER_GATES = ("G2", "G3", "G9", "A4", "M4", "T5", "G16", "M1")
DESIGN_GATES = ("A1", "A2", "A5", "T1", "G12-1", "G12-4")

MSG = {
    "zh": {"no_root": "ERROR: 站点根目录不存在或不是目录：{root}（未记账）",
           "summary": "release={rel} pass={p} fail={f} waived={w} machine={m} -> {ledger}",
           "intercept": "  interceptions: {n} 项待处置（tools/ledger-dispose.py）",
           "evidence": "  evidence: {d}", "config": "  config: {c}"},
    "en": {"no_root": "ERROR: site root does not exist or is not a directory: {root} (nothing recorded)",
           "summary": "release={rel} pass={p} fail={f} waived={w} machine={m} -> {ledger}",
           "intercept": "  interceptions: {n} to dispose (tools/ledger-dispose.py)",
           "evidence": "  evidence: {d}", "config": "  config: {c}"},
}


def run_script(argv, timeout=GATE_TIMEOUT, env=None):
    """按 argv 列表执行（不经 shell）；返回 (rc, stdout, stderr)，超时 rc=None。"""
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return None, "", f"超时（>{timeout}s）"
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def site_files(root, exts, exclude=()):
    """递归列出站点根目录下指定扩展名的文件（跳过 .git 与 exclude 里的相对路径/文件名）。"""
    out = []
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != ".git")
        for fn in sorted(files):
            if not fn.lower().endswith(exts):
                continue
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, root).replace(os.sep, "/")
            if rel in exclude or fn in exclude:
                continue
            out.append(p)
    return out


def read_text(path):
    """读文本；读不了（坏符号链接、权限）直接抛错，由 run_gates 判 fail。"""
    with open(path, encoding="utf-8", errors="ignore") as f:
        return f.read()


def count_matches(root, pattern, exts=(".html",), exclude=()):
    rx = re.compile(pattern)
    return sum(len(rx.findall(read_text(p))) for p in site_files(root, exts, exclude))


def _cfg(ctx):
    return ctx.get("cfg") or load_config()[0]


def _excluded(ctx):
    return tuple(i["path"] for i in _cfg(ctx)["design_rules"]["exclude"])


def _exclude_note(ctx):
    ex = _cfg(ctx)["design_rules"]["exclude"]
    if not ex:
        return []
    return [{"type": "note", "ref": "配置排除：" + "；".join(f"{i['path']}（{i['reason']}）" for i in ex)}]


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


# 门禁定义: 检查函数 fn(root, url, ctx) 返回 (verdict, [evidence...]) ; verdict in pass/fail/waived
# ctx = {"cfg": 配置, "gates": 已跑完的机器门禁, "interceptions": 本轮拦截项, "prior_runs": 历史 runs,
#        "dispositions": 历史处置}
def ck_g1(root, url, ctx):
    mode, path, detail = _resolve_gate_script("QA_GATES_SECURITY_GATE", "secret-scan.py")
    if mode == "external":
        rc, out, err = run_script(["bash", path, root])
        src = f"外部脚本 {path} <站点根目录>"
    elif mode == "fallback":
        argv = [sys.executable, path, "--root", root]
        for p in _cfg(ctx)["secret_scan"]["extra_patterns"]:
            argv += ["--pattern", f"{p['name']}={p['regex']}"]
        rc, out, err = run_script(argv)
        src = "仓库 fallback secret-scan.py"
    else:
        return "fail", [{"type": "note", "ref": f"G1 无可用实现：{detail}——拒绝误判 pass，直接判 fail"}]
    return _script_verdict(src, rc, out, err, 3)


def ck_g4(root, url, ctx):
    mode, path, detail = _resolve_gate_script("QA_GATES_SIZE_GATE", "size-budget.py")
    if mode == "external":
        rc, out, err = run_script(["bash", path, root])
        src = f"外部脚本 {path} <站点根目录>"
    elif mode == "fallback":
        b = _cfg(ctx)["size_budget"]
        rc, out, err = run_script([sys.executable, path, root,
                                   "--file-fail", str(b["file_fail_bytes"]), "--file-warn", str(b["file_warn_bytes"]),
                                   "--page-fail", str(b["page_fail_bytes"]), "--required", *b["required_pages"]])
        src = "仓库 fallback size-budget.py"
    else:
        return "fail", [{"type": "note", "ref": f"G4 无可用实现：{detail}——拒绝误判 pass，直接判 fail"}]
    return _script_verdict(src, rc, out, err, 4)


# ---- G5 中英镜像（机械项）----
_FULLWIDTH = "，。：；！？（）【】《》“”‘’、"
_LANG_RX = re.compile(r"""<html\b[^>]*\blang\s*=\s*["']?([\w-]+)""", re.I)
_ALT_RX = re.compile(r"""<(?:link|a)\b[^>]*\bhreflang\s*=\s*["']?en\b[^>]*>""", re.I)
_HREF_RX = re.compile(r"""\bhref\s*=\s*["']([^"']+)["']""", re.I)


def visible_text(html):
    html = re.sub(r"<!--.*?-->", " ", html, flags=re.S)
    html = re.sub(r"<(script|style|noscript|template)\b.*?</\1>", " ", html, flags=re.S | re.I)
    return htmlmod.unescape(re.sub(r"<[^>]+>", " ", html))


def _page_lang(html):
    m = _LANG_RX.search(html)
    return (m.group(1).lower() if m else "")


def _en_counterpart(root, zh_path, html):
    for tag in _ALT_RX.findall(html):
        m = _HREF_RX.search(tag)
        if m and not is_external(m.group(1)):
            p, _ = resolve_local(root, zh_path, m.group(1))
            if p and os.path.isfile(p):
                return p
    d, fn = os.path.split(zh_path)
    for cand in ([os.path.join(d, "en.html")] if fn == "index.html" else []) + [
            os.path.join(d, "en", fn), os.path.join(d, fn.replace(".zh.", ".en."))]:
        if cand != zh_path and os.path.isfile(cand):
            return cand
    return None


def _shape(html):
    text = visible_text(html)
    body = strip_html_noise(html)
    return {"numbers": sorted(re.findall(r"\d+(?:[.,]\d+)*", text)),
            "headings": [len(re.findall(fr"<h{i}\b", body, re.I)) for i in range(1, 7)],
            "links": len(re.findall(r"<a\b[^>]*\bhref", body, re.I)),
            "images": len(re.findall(r"<img\b", body, re.I)),
            "text": text}


def ck_g5(root, url, ctx):
    pairs, bad = 0, []
    for f in site_files(root, (".html", ".htm")):
        html = read_text(f)
        if not _page_lang(html).startswith("zh"):
            continue
        en = _en_counterpart(root, f, html)
        if not en:
            continue
        pairs += 1
        a, b = _shape(html), _shape(read_text(en))
        pair = f"{os.path.relpath(f, root)}↔{os.path.relpath(en, root)}"
        for key in ("numbers", "headings", "links", "images"):
            if a[key] != b[key]:
                bad.append(f"{pair}: {key} 不一致 zh={a[key]} en={b[key]}"[:160])
        fw = sorted({c for c in b["text"] if c in _FULLWIDTH})
        if fw:
            bad.append(f"{pair}: 英文版含全角标点 {''.join(fw)}")
    ev = [{"type": "cmd", "ref": "python: zh/en 成对页面的数字、标题层级、链接数、图片数一致，英文版无全角标点"}]
    if not pairs:
        return "waived", ev + [{"type": "note", "ref": "未找到中英成对页面（hreflang=en 或 index.html↔en.html 等命名），未验证"}]
    ev.append({"type": "output", "ref": f"pairs={pairs} bad={len(bad)}" + (f" e.g. {'; '.join(bad[:3])}" if bad else "")})
    ev.append({"type": "note", "ref": "机械项；译文语义是否一致仍需人工终审（G14）"})
    return ("pass" if not bad else "fail"), ev


# ---- G7 CSP hash round-trip ----
_JS_TYPES = {"", "text/javascript", "application/javascript", "application/ecmascript", "text/ecmascript",
             "module", "importmap", "speculationrules"}
_INLINE_SCRIPT_RX = re.compile(r"<script\b(?![^>]*\bsrc\s*=)([^>]*)>(.*?)</script>", re.I | re.S)
_TYPE_RX = re.compile(r"""\btype\s*=\s*["']?([^"'\s>]+)""", re.I)


def csp_policies(root, cfg):
    """从部署配置里取 CSP：返回 [(来源文件, 策略字符串)]。"""
    out = []
    for name in cfg["csp_sources"]:
        p = os.path.join(root, name)
        if not os.path.isfile(p):
            continue
        text = read_text(p)
        if name.endswith(".json"):
            data = json.loads(text)
            for block in data.get("headers", []):
                for kv in block.get("headers", []):
                    if str(kv.get("key", "")).lower() == "content-security-policy":
                        out.append((name, str(kv.get("value", ""))))
        else:  # Netlify / Cloudflare Pages _headers：缩进的 "Header: value" 行
            for line in text.splitlines():
                k, sep, v = line.strip().partition(":")
                if sep and k.strip().lower() == "content-security-policy":
                    out.append((name, v.strip()))
    return out


def script_src_tokens(policy):
    directives = {}
    for part in policy.split(";"):
        toks = part.split()
        if toks:
            directives[toks[0].lower()] = [t.strip("'\"") for t in toks[1:]]
    return directives.get("script-src-elem") or directives.get("script-src") or directives.get("default-src") or []


def inline_scripts(root):
    got: dict[str, list[str]] = {}
    for f in site_files(root, (".html", ".htm")):
        for attrs, body in _INLINE_SCRIPT_RX.findall(read_text(f)):
            m = _TYPE_RX.search(attrs)
            if (m.group(1).lower() if m else "") not in _JS_TYPES:
                continue  # JSON-LD 等数据块不受 script-src 管
            h = "sha256-" + base64.b64encode(hashlib.sha256(body.encode("utf-8")).digest()).decode()
            got.setdefault(h, []).append(os.path.relpath(f, root))
    return got


def ck_g7(root, url, ctx):
    cfg = _cfg(ctx)
    ev = [{"type": "cmd", "ref": f"inline JS <script> sha256 vs CSP script-src（{', '.join(cfg['csp_sources'])}）"}]
    policies = csp_policies(root, cfg)
    if not policies:
        return "waived", ev + [{"type": "note", "ref": f"站点根目录下没有含 CSP 的 {'/'.join(cfg['csp_sources'])}，未验证"}]
    got = inline_scripts(root)
    bad = []
    for src, policy in policies:
        toks = script_src_tokens(policy)
        want = {t for t in toks if t.startswith("sha256-")}
        if want:
            missing, extra = sorted(want - set(got)), sorted(set(got) - want)
            if extra:
                bad.append(f"{src}: 页面内联脚本未登记 hash {extra[:3]}")
            if missing:
                bad.append(f"{src}: CSP 登记的 hash 在页面里找不到 {missing[:3]}")
        elif got and "unsafe-inline" not in toks and not any(t.startswith("nonce-") for t in toks):
            bad.append(f"{src}: 有 {len(got)} 段内联脚本，但 script-src 没有 hash/nonce/unsafe-inline（浏览器会拦截）")
    ev.append({"type": "output", "ref": f"policies={len(policies)} inline={len(got)} bad={len(bad)}" + (f" e.g. {'; '.join(bad[:2])}" if bad else "")})
    return ("pass" if not bad else "fail"), ev


# ---- G8 生产可达性 ----
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **kw):
        return None  # 3xx 原样返回，不算可达


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
    if not url:
        return "waived", [{"type": "note", "ref": "未给 --site-url / QA_GATES_SITE_URL / 配置 site_url，未请求线上地址"}]
    target = f"{url}/"
    ev = [{"type": "cmd", "ref": f"GET {target} -> HTTP code"}]
    parts = urllib.parse.urlsplit(target)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return "fail", ev + [{"type": "output", "ref": f"非法 site-url（只允许 http/https）：{url!r}"}]
    code = http_status(target)
    ev.append({"type": "output", "ref": f"HTTP {code:03d}"})
    return ("pass" if code == 200 else "fail"), ev


# ---- G15 站内资源完整性 ----
def _check_ref(root, from_file, kind, raw, ids, bad):
    ref = raw.strip()
    low = ref.lower()
    rel = os.path.relpath(from_file, root)
    if is_external(ref):
        return
    if kind in ("href", "src") and (ref in ("", "#") or low.startswith("javascript:")):
        bad.append(f"{rel}: {kind}={raw!r} 死链")
        return
    if ref.startswith("#"):
        if kind == "url()":
            return  # SVG 片段 url(#grad)
        if urllib.parse.unquote(ref[1:]) not in ids:
            bad.append(f"{rel}: {kind}={raw!r} 锚点不存在")
        return
    if not ref or low.startswith("var("):
        return
    target, escapes = resolve_local(root, from_file, ref)
    if target is None:
        return
    if escapes:
        bad.append(f"{rel}: {kind}={raw!r} 越出站点根目录（部署后会 404）")
    elif not os.path.exists(target):
        bad.append(f"{rel}: {kind}={raw!r} 文件不存在")


def ck_g15(root, url, ctx):
    """本地资源完整性：src/href/srcset/poster（含无引号写法）与 CSS url() 指向的站内文件必须存在且不越出站点根目录；
    href="#"、空 href、javascript: 判死链；#锚点必须在同页有对应 id/name。外链不在此门禁范围（见 G8）。"""
    bad: list[str] = []
    n = 0
    for f in site_files(root, (".html", ".htm")):
        html = read_text(f)
        ids = set(re.findall(r"""\b(?:id|name)\s*=\s*["']?([^"'\s>]+)""", strip_html_noise(html), re.I))
        for kind, raw in html_refs(html):
            n += 1
            _check_ref(root, f, kind, raw, ids, bad)
    for f in site_files(root, (".css",)):
        for raw in css_urls(read_text(f)):
            n += 1
            _check_ref(root, f, "url()", raw, set(), bad)
    ev = [{"type": "cmd", "ref": "python: src/href/srcset/poster＋CSS url() 站内引用存在性＋死链＋锚点＋越界"},
          {"type": "output", "ref": f"refs={n} bad={len(bad)}" + (f" e.g. {'; '.join(bad[:3])}" if bad else "")}]
    return ("pass" if not bad else "fail"), ev


# ---- 设计规则门禁（排除项见配置 design_rules.exclude，逐条写进证据）----
def ck_a1(root, url, ctx):
    sizes = "|".join(str(x) for x in _cfg(ctx)["typography"]["banned_font_sizes_px"]) or "(?!)"
    n = count_matches(root, rf"font-size:\s*(?:{sizes})px\b", (".html", ".css"), _excluded(ctx))
    ev = [{"type": "cmd", "ref": f"python: font-size {sizes}px 计数（html＋css）"}, {"type": "output", "ref": f"hits={n}"}]
    return ("pass" if n == 0 else "fail"), ev + _exclude_note(ctx)


def ck_a2(root, url, ctx):
    decl = re.compile(r"(?:margin|padding)[^;{}\"'<>]*:[^;{}\"'<>]*")
    vals: set[int] = set()
    for p in site_files(root, (".css", ".html"), _excluded(ctx)):
        for d in decl.findall(read_text(p)):
            vals.update(int(x) for x in re.findall(r"(?<![\w.])([0-9]+)px", d))
    legal = set(_cfg(ctx)["spacing"]["scale_px"])
    bad = sorted(v for v in vals if v not in legal)
    ev = [{"type": "cmd", "ref": "python: margin/padding px 值 vs 配置 spacing.scale_px"},
          {"type": "output", "ref": f"illegal={bad[:10]}" if bad else "all legal"}]
    return ("pass" if not bad else "fail"), ev + _exclude_note(ctx)


def ck_a5(root, url, ctx):
    n = count_matches(root, r"countUp|animate-number|CountUp", (".html", ".js", ".mjs"), _excluded(ctx))
    ev = [{"type": "cmd", "ref": "python: countUp|animate-number 计数（html＋js）"}, {"type": "output", "ref": f"hits={n}"}]
    return ("pass" if n == 0 else "fail"), ev + _exclude_note(ctx)


def ck_t1(root, url, ctx):
    # eyebrow 计数 ≤ ceil(n/3)，逐页判
    bad, total = [], 0
    for f in site_files(root, (".html",), _excluded(ctx)):
        html = read_text(f)
        eb = len(re.findall(r"""class\s*=\s*["'][^"']*\beyebrow""", html, re.I))
        secs = len(re.findall(r"<section\b", html, re.I))
        total += eb
        limit = math.ceil(max(secs, 1) / 3)
        if eb > limit:
            bad.append(f"{os.path.relpath(f, root)}: eyebrow={eb} sections={secs} limit={limit}")
    ev = [{"type": "cmd", "ref": "python: 每页 eyebrow 数 ≤ ceil(<section> 数/3)"},
          {"type": "output", "ref": f"eyebrow_total={total} bad={len(bad)}" + (f" e.g. {bad[0]}" if bad else "")}]
    return ("pass" if not bad else "fail"), ev


def ck_t2(root, url, ctx):
    # 中文文案 em-dash（U+2014）零：扫可见文字
    hits = [os.path.relpath(f, root) for f in site_files(root, (".html",)) if "—" in visible_text(read_text(f))]
    ev = [{"type": "cmd", "ref": "python: 扫描 *.html 可见文字中含 U+2014 的文件"},
          {"type": "output", "ref": f"files_with_emdash={len(hits)}" + (f" e.g. {hits[:3]}" if hits else "")}]
    return ("pass" if not hits else "fail"), ev


MOTION_OK = {"transform", "opacity"}
_TIMING = {"ease", "ease-in", "ease-out", "ease-in-out", "linear", "step-start", "step-end",
           "normal", "allow-discrete", "initial", "inherit", "unset", "revert", "revert-layer"}
_TIME_RX = re.compile(r"^[+-]?(?:\d+\.?\d*|\.\d+)m?s$", re.I)


def split_top_level(value, sep=","):
    """按顶层分隔符切分（括号内的逗号不切），供 cubic-bezier(...) 等使用。"""
    parts: list[str] = []
    cur: list[str] = []
    depth = 0
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
    # 白名单属性：transition 逐个属性、@keyframes 内逐条声明只许 transform/opacity
    bad = []
    for p in site_files(root, (".css", ".html"), _excluded(ctx)):
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
    return ("pass" if not bad else "fail"), ev + _exclude_note(ctx)


def ck_g124(root, url, ctx):
    n = count_matches(root, r"particles\.js|particlesjs|canvas-nest|confetti", (".html", ".js", ".mjs"), _excluded(ctx))
    ev = [{"type": "cmd", "ref": "python: 粒子背景库计数（html＋js）"}, {"type": "output", "ref": f"hits={n}"}]
    return ("pass" if n == 0 else "fail"), ev + _exclude_note(ctx)


def ck_v4(root, url, ctx):
    """V4 真实拦截/放行记录。

    - 本轮有真实 FAIL：每条 FAIL 必须有拦截项，且其证据里至少一条是实际输出/说明；缺任一项 -> V4 自判 fail。
    - 本轮零 FAIL：回查最近一条含拦截的 run，其拦截项当前状态（最近一条处置）不全是 closed -> V4 自判 fail。
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
            ev.append({"type": "interception",
                       "ref": f"拦截 {g['gate_id']} {g['name']}：{it['evidence_refs'][-1][:160]} ｜处置状态：{it.get('status', 'pending')}"})
        ev.append({"type": "note", "ref": f"本轮真实拦截 {len(fails)} 项，全部已记入 interceptions 并附输出证据"})
        return "pass", ev

    prior = ctx.get("prior_runs") or []
    dispositions = ctx.get("dispositions") or []
    checked = 0
    for pr in reversed(prior):
        its = pr.get("interceptions") or []
        if not its:
            continue
        checked += 1
        open_its = [i["gate_id"] for i in its
                    if interception_status(prior, pr.get("run_id"), i["gate_id"], dispositions) != "closed"]
        if open_its:
            return "fail", [
                {"type": "note", "ref": "本轮零拦截"},
                {"type": "backcheck",
                 "ref": f"V4 自判 fail：上一条含拦截的 run {pr.get('run_id')} 处置未闭环：{open_its}（立案→整改→复验未完成，见 tools/ledger-dispose.py）"}]
        break  # 只回查最近一条含拦截的 run
    return "pass", [{"type": "note", "ref": f"本轮零拦截；回查最近含拦截的 run 处置已闭环（共查 {checked} 条）"}]


STATIC = [
    ("G1", ck_g1), ("G4", ck_g4), ("G5", ck_g5), ("G7", ck_g7), ("G8", ck_g8), ("G15", ck_g15),
    ("A1", ck_a1), ("A2", ck_a2), ("A5", ck_a5), ("T1", ck_t1), ("T2", ck_t2),
    ("G12-1", ck_g121), ("G12-4", ck_g124),
]
MACHINE = STATIC + [(g, None) for g in BROWSER_GATES if g != "M1"] + [("V4", ck_v4)]


# ---- 真浏览器门禁 ----
class _SiteHandler(SimpleHTTPRequestHandler):
    csp = None

    def end_headers(self):
        if self.csp:
            self.send_header("Content-Security-Policy", self.csp)
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *args):
        pass


def _node_env():
    env = dict(os.environ)
    paths = [os.path.join(BROWSER_DIR, "node_modules")]
    npm = shutil.which("npm")
    if npm:
        rc, out, _ = run_script([npm, "root", "-g"], timeout=20)
        if rc == 0 and out:
            paths.append(out)
    env["NODE_PATH"] = os.pathsep.join(paths + ([env["NODE_PATH"]] if env.get("NODE_PATH") else []))
    return env


def browser_available():
    """返回 (ok, 说明)。"""
    node = shutil.which("node")
    if not node:
        return False, "未找到 node"
    rc, out, err = run_script([node, "-e", "require('playwright');require('axe-core');console.log(require('playwright/package.json').version)"],
                              timeout=30, env=_node_env())
    if rc != 0:
        return False, "playwright / axe-core 未安装（npm ci --prefix tools/browser）"
    return True, f"playwright {out}"


def run_browser_gates(root, cfg, evidence_dir):
    """返回 {gate_id: (verdict, evidence)}；浏览器不可用时返回 (None, 原因)。"""
    ok, why = browser_available()
    if not ok:
        return None, why
    pages = [os.path.relpath(p, root).replace(os.sep, "/") for p in site_files(root, (".html", ".htm"))]
    policies = csp_policies(root, cfg)
    handler = type("H", (_SiteHandler,), {"csp": policies[0][1] if policies else None})
    srv = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(handler, directory=root))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump({"base_url": f"http://127.0.0.1:{srv.server_port}", "pages": pages,
                   "out_dir": evidence_dir or tempfile.mkdtemp(prefix="qa-evidence-"), "cfg": cfg}, f)
        spec = f.name
    try:
        rc, out, err = run_script([shutil.which("node"), os.path.join(BROWSER_DIR, "gates.cjs"), spec],
                                  timeout=cfg["browser"]["timeout_s"], env=_node_env())
    finally:
        srv.shutdown()
        srv.server_close()
        os.unlink(spec)
    if rc != 0:
        reason = err.splitlines()[-1][:160] if err else f"rc={rc}"
        return {g: ("fail", [{"type": "note", "ref": f"浏览器门禁执行失败（{reason}）——判 fail"}]) for g in BROWSER_GATES if g != "M1"}, None
    data = json.loads(out)
    csp_note = [{"type": "note", "ref": f"本地服务按 {policies[0][0]} 的 CSP 下发" if policies else "站点无 CSP 配置，本地服务未加 CSP"}]
    return {g: (r["verdict"], r["evidence"] + (csp_note if g == "G9" else [])) for g, r in data["gates"].items()}, None


def build_interceptions(gates):
    """把本轮真实 FAIL 转为拦截项记录（V4 引用目标）。V4 自身不立案。"""
    its = []
    for g in gates:
        if g["verdict"] == "fail" and g["gate_id"] != "V4":
            refs = [e.get("ref", "") for e in g.get("evidence", []) if e.get("ref")]
            its.append({"gate_id": g["gate_id"], "name": g["name"],
                        "evidence_refs": refs, "status": "pending"})
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


def _gate(gid, verdict, evidence):
    return {"gate_id": gid, "name": NAMES[gid][0], "name_en": NAMES[gid][1],
            "run_at": datetime.now(timezone.utc).isoformat(), "verdict": verdict, "evidence": evidence}


def run_gates(root, url, prior_runs, cfg=None, dispositions=None, browser=True, evidence_dir=None, lang="zh"):
    cfg = cfg or load_config()[0]
    gates: list[dict] = []
    ctx_base = {"cfg": cfg, "prior_runs": prior_runs, "dispositions": dispositions or []}
    for gid, fn in STATIC:
        try:
            verdict, evidence = fn(root, url, dict(ctx_base, gates=gates))
        except Exception as e:  # 失败即关闭：执行不了的门禁不是"未验证放行"，是 fail
            verdict, evidence = "fail", [{"type": "note", "ref": f"执行异常（判 fail，拒绝静默放行）: {type(e).__name__}: {e}"}]
        gates.append(_gate(gid, verdict, evidence))

    results, why = (run_browser_gates(root, cfg, evidence_dir) if browser else (None, "--no-browser"))
    required = os.environ.get("QA_GATES_REQUIRE_BROWSER") == "1"
    for gid in BROWSER_GATES:
        if results is not None:
            verdict, evidence = results.get(gid, ("fail", [{"type": "note", "ref": "浏览器门禁未返回结果——判 fail"}]))
        elif required and gid != "M1":
            verdict, evidence = "fail", [{"type": "note", "ref": f"QA_GATES_REQUIRE_BROWSER=1 但浏览器不可用：{why}"}]
        else:
            verdict, evidence = "waived", [{"type": "note", "ref": f"真浏览器门禁未执行：{why}"}]
        gates.append(_gate(gid, verdict, evidence))

    ctx = dict(ctx_base, gates=gates, interceptions=build_interceptions(gates))
    try:
        verdict, evidence = ck_v4(root, url, ctx)
    except Exception as e:
        verdict, evidence = "fail", [{"type": "note", "ref": f"执行异常（判 fail）: {type(e).__name__}: {e}"}]
    gates.append(_gate("V4", verdict, evidence))

    for gid, reasons in WAIVED.items():
        gates.append(_gate(gid, "waived", [{"type": "note", "ref": reasons[0] if lang == "zh" else reasons[1]}]))
    return gates


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", required=True)
    ap.add_argument("--change", required=True)
    ap.add_argument("--site-root", default=DEFAULT_ROOT)
    ap.add_argument("--site-url", default=None)
    ap.add_argument("--no-browser", action="store_true", help="不跑真浏览器门禁（它们记 waived）")
    ap.add_argument("--lang", choices=["zh", "en"], default=os.environ.get("QA_GATES_LANG", "zh"))
    a = ap.parse_args()
    m = MSG[a.lang]
    try:
        cfg, cfg_src = load_config()
    except (OSError, ValueError) as e:
        print(f"ERROR: 门禁配置读不了 / cannot load config: {e}（未记账）", file=sys.stderr)
        sys.exit(2)
    root = a.site_root
    url = (a.site_url or os.environ.get("QA_GATES_SITE_URL") or cfg.get("site_url") or "").rstrip("/") or None
    if not os.path.isdir(root):
        print(m["no_root"].format(root=root), file=sys.stderr)
        sys.exit(2)

    path = ledger_path()
    evidence_dir = os.environ.get("QA_GATES_EVIDENCE_DIR") or os.path.join(
        os.path.dirname(os.path.abspath(path)), "qa-evidence", re.sub(r"[^\w.-]+", "_", a.release))
    with locked_ledger(path) as (ledger, save):
        gates = run_gates(root, url, ledger.get("runs", []), cfg, ledger.get("dispositions", []),
                          browser=not a.no_browser, evidence_dir=evidence_dir, lang=a.lang)
        interceptions = build_interceptions(gates)
        machine_ids = {g for g, _ in MACHINE}
        machine_done = sum(1 for g in gates if g["gate_id"] in machine_ids and g["verdict"] in ("pass", "fail"))
        run = {"run_id": a.release,
               "run_at": datetime.now(timezone.utc).isoformat(),
               "change": a.change, "site_root": display_path(root), "site_url": url,
               "config": display_path(cfg_src) if cfg_src != "defaults" else "defaults",
               "evidence_dir": display_path(evidence_dir) if os.path.isdir(evidence_dir) else None,
               "gates": gates,
               "interceptions": interceptions,
               "machine_coverage": f"{machine_done}/{len(gates)}",
               "summary": {v: sum(1 for g in gates if g["verdict"] == v) for v in ("pass", "fail", "waived")}}
        seal(ledger, "runs", run)
        save(ledger)

    s = run["summary"]
    print(m["summary"].format(rel=a.release, p=s["pass"], f=s["fail"], w=s["waived"], m=run["machine_coverage"], ledger=path))
    print(m["config"].format(c=run["config"]))
    for g in gates:
        if g["verdict"] == "fail":
            label = g["name"] if a.lang == "zh" else g["name_en"]
            out = [e for e in g["evidence"] if e.get("type") == "output"] or g["evidence"]
            print(f"  FAIL {g['gate_id']} {label}: {out[-1]['ref'][:140]}")
    if interceptions:
        print(m["intercept"].format(n=len(interceptions)))
    if run["evidence_dir"]:
        print(m["evidence"].format(d=run["evidence_dir"]))
    sys.exit(0 if s["fail"] == 0 else 2)


if __name__ == "__main__":
    main()
