"""站内引用解析（G4 页面体积与 G15 资源完整性共用）。

覆盖：src / href / srcset / poster 属性（带引号或不带引号），<style> 块、style="" 与站内 .css 文件里的 url()。
外链（http/https、//、mailto: 等）不在此范围。
"""
import os, re, urllib.parse

SKIP_SCHEMES = ("http:", "https:", "mailto:", "tel:", "data:", "blob:", "//", "about:")
_ATTR_RX = re.compile(r"""(?<![\w-])(src|href|srcset|poster)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))""", re.I)
_URL_RX = re.compile(r"""url\(\s*(?:"([^"]*)"|'([^']*)'|([^)\s]*))\s*\)""", re.I)
_STYLE_BLOCK_RX = re.compile(r"<style\b[^>]*>(.*?)</style>", re.I | re.S)
_STYLE_ATTR_RX = re.compile(r"""\bstyle\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.I)


def strip_html_noise(html):
    """去掉注释与内联脚本正文（保留 <script src> 开标签），避免把 JS 字符串当成引用。"""
    html = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    return re.sub(r"(<script\b[^>]*>).*?</script>", r"\1", html, flags=re.S | re.I)


def _srcset_urls(value):
    out = []
    for cand in value.split(","):
        parts = cand.strip().split()
        if parts:
            out.append(parts[0])
    return out


def css_urls(css):
    return [next((g for g in m.groups() if g is not None), "") for m in _URL_RX.finditer(css)]


def html_refs(html):
    """返回 [(kind, raw)]：kind 为属性名（src/href/srcset/poster）或 'url()'。"""
    html = strip_html_noise(html)
    refs: list[tuple[str, str]] = []
    for m in _ATTR_RX.finditer(html):
        attr = m.group(1).lower()
        raw = next(g for g in m.groups()[1:] if g is not None)
        if attr == "srcset":
            refs.extend(("srcset", u) for u in _srcset_urls(raw))
        else:
            refs.append((attr, raw))
    for block in _STYLE_BLOCK_RX.findall(html):
        refs.extend(("url()", u) for u in css_urls(block))
    for m in _STYLE_ATTR_RX.finditer(html):
        refs.extend(("url()", u) for u in css_urls(m.group(1) or m.group(2) or ""))
    return refs


def is_external(ref):
    return ref.strip().lower().startswith(SKIP_SCHEMES)


def resolve_local(root, from_file, ref):
    """把站内引用解析成磁盘路径。返回 (path, escapes_root)；纯 #锚点/?query 返回 (None, False)。"""
    path = urllib.parse.unquote(urllib.parse.urlsplit(ref.strip()).path)
    if not path:
        return None, False
    root = os.path.abspath(root)
    base = root if path.startswith("/") else os.path.dirname(os.path.abspath(from_file))
    target = os.path.normpath(os.path.join(base, path.lstrip("/")))
    escapes = not (target == root or target.startswith(root + os.sep))
    if os.path.isdir(target):
        target = os.path.join(target, "index.html")
    return target, escapes
