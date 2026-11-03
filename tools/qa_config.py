"""门禁配置：阈值与站点相关项都从这里读，不再写死在门禁函数里。

查找顺序：环境变量 QA_GATES_CONFIG 指向的 JSON 文件；否则仓库根 qa-gates.config.json（vertciti 自用配置）；
都没有就用 DEFAULTS。文件里给出的键覆盖默认值（按层合并），没给的键保持默认。
"""
import copy, json, os
from typing import Any

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_CONFIG = os.path.join(SKILL_DIR, "qa-gates.config.json")

DEFAULTS: dict[str, Any] = {
    # G8：缺省不测任何线上地址；--site-url / QA_GATES_SITE_URL / 配置三选一
    "site_url": None,
    # A1：禁用字号（px）
    "typography": {"banned_font_sizes_px": [13, 15, 17, 19]},
    # A2：margin/padding 合法 px 值
    "spacing": {"scale_px": [0, 4, 8, 12, 16, 20, 24, 32, 40, 48, 56, 64, 80, 96, 120]},
    # G4：单文件红线/黄线、单页（HTML＋站内引用资源）总量红线、必须存在的页面
    "size_budget": {"file_fail_bytes": 1258291, "file_warn_bytes": 1048576,
                    "page_fail_bytes": 1572864, "required_pages": ["index.html"]},
    # G1 fallback：额外敏感规则（name + 正则），追加在内置规则之后
    "secret_scan": {"extra_patterns": []},
    # G7：读取 CSP 的部署配置文件（相对站点根目录）
    "csp_sources": ["vercel.json", "_headers"],
    # 设计规则门禁（A1/A2/A5/T1/G12-1/G12-4）跳过的文件（相对站点根目录的路径或文件名）；
    # 每项必须写 reason，且会逐条写进证据，不静默
    "design_rules": {"exclude": []},
    # 浏览器门禁
    "browser": {"min_target_px": 44, "reduced_motion_max_ms": 110,
                "viewports": {"mobile": [390, 844], "desktop": [1440, 900]},
                "timeout_s": 300,
                "axe_tags": ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]},
}


def _merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def config_path():
    p = os.environ.get("QA_GATES_CONFIG")
    if p:
        return p
    return REPO_CONFIG if os.path.isfile(REPO_CONFIG) else None


def load_config(path=None):
    """返回 (config, source)。source 是实际读的文件路径，或 'defaults'。指定的文件不存在时报错。"""
    path = path or config_path()
    if not path:
        return copy.deepcopy(DEFAULTS), "defaults"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    data.pop("$comment", None)
    cfg = _merge(DEFAULTS, data)
    for item in cfg["design_rules"]["exclude"]:
        if not isinstance(item, dict) or not item.get("path") or not item.get("reason"):
            raise ValueError(f"design_rules.exclude 每项必须有 path 与 reason：{item!r}")
    return cfg, path
