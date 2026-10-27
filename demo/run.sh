#!/bin/bash
# website-qa-gates demo: 用 skill 真实门禁 runner 跑 1 个测试页（30 秒内）
# 退出码透传 runner：0=全部通过，2=有门禁 FAIL（CI 靠此变红）
# - 起本地 http.server 托管 demo/www，G8 测的是被测页本身，不依赖外网。
# - 运行记录缺省写到临时文件（QA_GATES_LEDGER）；本地已有 coverage-ledger.json 时先复制过去，
#   V4 回查才有历史。要追加进本地记录：QA_GATES_LEDGER="$PWD/coverage-ledger.json" bash demo/run.sh
set -u
SKILL="$(cd "$(dirname "$0")/.." && pwd)"
REL="demo-$(date +%Y%m%d-%H%M%S)"

if [ -z "${QA_GATES_LEDGER:-}" ]; then
  QA_GATES_LEDGER="$(mktemp "${TMPDIR:-/tmp}/qa-gates-ledger.XXXXXX")"
  if [ -f "$SKILL/coverage-ledger.json" ]; then
    cp "$SKILL/coverage-ledger.json" "$QA_GATES_LEDGER"
  else
    rm -f "$QA_GATES_LEDGER"  # 空文件不是合法 JSON；runner 会新建
  fi
fi
export QA_GATES_LEDGER

PORT="$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])')"
python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$SKILL/demo/www" >/dev/null 2>&1 &
SERVER=$!
trap 'kill "$SERVER" 2>/dev/null' EXIT
for _ in $(seq 50); do
  python3 -c "import urllib.request,sys; urllib.request.urlopen(sys.argv[1], timeout=1)" "http://127.0.0.1:$PORT/" 2>/dev/null && break
  sleep 0.1
done

timeout 60 python3 "$SKILL/tools/ledger-run.py" --release "$REL" --change "demo: 单测试页门禁跑通" \
  --site-root "$SKILL/demo/www" --site-url "http://127.0.0.1:$PORT"
RC=$?
echo "RELEASE=$REL"
echo "LEDGER=$QA_GATES_LEDGER"
echo "EXIT_CODE=$RC"
exit $RC
