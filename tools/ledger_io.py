"""coverage-ledger 读写：加锁＋原子替换（ledger-run.py / ledger-dispose.py 共用）。

- 台账路径：环境变量 QA_GATES_LEDGER 优先，缺省为仓库根 coverage-ledger.json。
- 读-改-写全程持有 <ledger>.lock 上的排他锁，并发运行不丢更新。
- 写入先落同目录临时文件再 os.replace，进程中途被杀也不会留下截断的台账。
"""
import contextlib, fcntl, json, os, tempfile

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ledger_path():
    return os.environ.get("QA_GATES_LEDGER") or os.path.join(SKILL_DIR, "coverage-ledger.json")


@contextlib.contextmanager
def locked_ledger(path=None, create=True):
    """持锁打开台账，yield (ledger, save)；save(ledger) 原子写回。"""
    path = path or ledger_path()
    with open(path + ".lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                ledger = json.load(f)
            assert ledger.get("additive") is True, "ledger additive 标志被篡改，拒绝写入"
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
