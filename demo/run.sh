#!/bin/bash
# website-qa-gates demo: 用 skill 真实门禁 runner 跑 1 个测试页（30 秒内）
set -u
SKILL="$(cd "$(dirname "$0")/.." && pwd)"
REL="demo-$(date +%Y%m%d-%H%M%S)"
timeout 25 python3 "$SKILL/tools/ledger-run.py" --release "$REL" --change "demo: 单测试页门禁跑通" --site-root "$SKILL/demo/www"
echo "RELEASE=$REL"
