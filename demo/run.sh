#!/bin/bash
# website-qa-gates demo: 用 skill 真实门禁 runner 跑 demo 测试页（静态＋真浏览器门禁）
# 退出码透传 runner：0=全部通过，2=有门禁 FAIL（CI 靠此变红）
# - 起本地 http.server 托管 demo/www，G8 测的是被测页本身，不依赖外网。
# - 没设 QA_GATES_LEDGER 时，台账与截图写进一个临时目录，退出时删除（不在 /tmp 留副本）；
#   本地已有 coverage-ledger.json 时先复制过去，V4 回查才有历史。
#   要保留：QA_GATES_LEDGER="$PWD/coverage-ledger.json" 和/或 QA_GATES_EVIDENCE_DIR=<目录>。
set -u
SKILL="$(cd "$(dirname "$0")/.." && pwd)"
REL="demo-$(date +%Y%m%d-%H%M%S)"

WORK=""
if [ -z "${QA_GATES_LEDGER:-}" ]; then
  WORK="$(mktemp -d "${TMPDIR:-/tmp}/qa-gates-demo.XXXXXX")"
  QA_GATES_LEDGER="$WORK/coverage-ledger.json"
  [ -f "$SKILL/coverage-ledger.json" ] && cp "$SKILL/coverage-ledger.json" "$QA_GATES_LEDGER"
fi
export QA_GATES_LEDGER

PORT="$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])')"
python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$SKILL/demo/www" >/dev/null 2>&1 &
SERVER=$!
cleanup() { kill "$SERVER" 2>/dev/null; [ -n "$WORK" ] && [ -z "${QA_GATES_KEEP:-}" ] && rm -rf "$WORK"; }
trap cleanup EXIT
for _ in $(seq 50); do
  python3 -c "import urllib.request,sys; urllib.request.urlopen(sys.argv[1], timeout=1)" "http://127.0.0.1:$PORT/" 2>/dev/null && break
  sleep 0.1
done

timeout 300 python3 "$SKILL/tools/ledger-run.py" --release "$REL" --change "demo: 测试页门禁跑通" \
  --site-root "$SKILL/demo/www" --site-url "http://127.0.0.1:$PORT"
RC=$?
python3 "$SKILL/tools/ledger-verify.py" --ledger "$QA_GATES_LEDGER" || RC=1
echo "RELEASE=$REL"
echo "LEDGER=$QA_GATES_LEDGER"
echo "EXIT_CODE=$RC"
# 供 eval.sh 在同一进程里读取：临时模式下打印记账结果后才删除
if [ -n "${QA_GATES_DEMO_DUMP:-}" ]; then cp "$QA_GATES_LEDGER" "$QA_GATES_DEMO_DUMP"; fi
exit $RC
