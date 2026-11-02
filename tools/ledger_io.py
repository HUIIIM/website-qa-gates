"""coverage-ledger 读写：加锁＋原子替换＋哈希链（ledger-run / ledger-dispose / ledger-verify / score 共用）。

- 台账路径：环境变量 QA_GATES_LEDGER 优先，缺省为仓库根 coverage-ledger.json。
- 读-改-写全程持有 <ledger>.lock 上的排他锁，并发运行不丢更新。
- 写入先落同目录临时文件再 os.replace，进程中途被杀也不会留下截断的台账。
- 哈希链：runs / dispositions / scores 三类记录按追加顺序共用一条链。每条记录带
  seq（从 1 递增）、prev_sha256（上一条的 sha256，首条为 64 个 0）与 sha256
  （去掉 sha256 字段后的规范 JSON 的 SHA-256）。ledger["head"] 是最后一条的 sha256。
  任何事后改写都会让 tools/ledger-verify.py 报错；把 head 抄到台账之外即完成外部锚定。
- 旧台账里没有 seq 的记录照常读取，记为"未封印"，verify 会单独列出。
"""
import contextlib, fcntl, hashlib, json, os, tempfile

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENESIS = "0" * 64
CHAINED = ("runs", "dispositions", "scores")


def ledger_path():
    return os.environ.get("QA_GATES_LEDGER") or os.path.join(SKILL_DIR, "coverage-ledger.json")


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def record_hash(rec):
    body = {k: v for k, v in rec.items() if k != "sha256"}
    return hashlib.sha256(canonical(body).encode("utf-8")).hexdigest()


def seal(ledger, kind, rec):
    """给 rec 编号、挂上一条哈希并追加到 ledger[kind]。返回 rec。"""
    assert kind in CHAINED, kind
    sealed = [r for k in CHAINED for r in ledger.get(k, []) if "seq" in r]
    rec["seq"] = max((r["seq"] for r in sealed), default=0) + 1
    rec["prev_sha256"] = ledger.get("head") or GENESIS
    rec["sha256"] = record_hash(rec)
    ledger.setdefault(kind, []).append(rec)
    ledger["head"] = rec["sha256"]
    return rec


def verify_chain(ledger):
    """返回 (problems, sealed_count, unsealed_count)。problems 为空表示链完整。"""
    problems = []
    sealed = sorted(((r["seq"], k, r) for k in CHAINED for r in ledger.get(k, []) if "seq" in r),
                    key=lambda t: t[0])
    unsealed = sum(1 for k in CHAINED for r in ledger.get(k, []) if "seq" not in r)
    prev = GENESIS
    for i, (seq, kind, rec) in enumerate(sealed, 1):
        label = f"{kind}#seq={seq}({rec.get('run_id') or rec.get('gate_id') or ''})"
        if seq != i:
            problems.append(f"{label}: seq 不连续（期望 {i}）")
        if rec.get("prev_sha256") != prev:
            problems.append(f"{label}: prev_sha256 与上一条不符")
        if rec.get("sha256") != record_hash(rec):
            problems.append(f"{label}: 内容哈希不符（记录被改写）")
        prev = rec.get("sha256")
    if sealed and ledger.get("head") != prev:
        problems.append("head 与最后一条记录的 sha256 不符（尾部记录被删除或 head 被改）")
    return problems, len(sealed), unsealed


def interception_status(ledger_or_runs, run_id, gate_id, dispositions=None):
    """拦截项的当前状态：该 (run_id, gate_id) 最近一条处置的 result；没有处置则用记录内 status。"""
    if isinstance(ledger_or_runs, dict):
        runs = ledger_or_runs.get("runs", [])
        dispositions = ledger_or_runs.get("dispositions", []) if dispositions is None else dispositions
    else:
        runs = ledger_or_runs
    for d in reversed(dispositions or []):
        if d.get("run_id") == run_id and d.get("gate_id") == gate_id:
            return d.get("result")
    for r in runs:
        if r.get("run_id") == run_id:
            for i in r.get("interceptions", []):
                if i.get("gate_id") == gate_id:
                    return i.get("status", "pending")
    return None


@contextlib.contextmanager
def locked_ledger(path=None, create=True):
    """持锁打开台账，yield (ledger, save)；save(ledger) 原子写回。"""
    path = path or ledger_path()
    with open(path + ".lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                ledger = json.load(f)
            if ledger.get("additive") is not True:
                raise ValueError("ledger additive 标志被篡改，拒绝写入")
            problems, _, _ = verify_chain(ledger)
            if problems:
                raise ValueError("台账哈希链校验失败，拒绝追加：" + "；".join(problems[:3]))
        elif create:
            ledger = {"additive": True, "runs": []}
        else:
            raise FileNotFoundError(path)

        def save(data):
            fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(path)),
                                       prefix=".ledger-", suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    f.write("\n")
                    f.flush()
                    os.fsync(f.fileno())
                # mkstemp 建的是 0600；沿用原台账权限（新建则 0644）
                mode = os.stat(path).st_mode & 0o777 if os.path.exists(path) else 0o644
                os.chmod(tmp, mode)
                os.replace(tmp, path)
            except BaseException:
                with contextlib.suppress(FileNotFoundError):
                    os.unlink(tmp)
                raise

        yield ledger, save
