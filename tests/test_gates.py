"""门禁 runner 回归测试（纯 stdlib unittest）：python3 -m unittest discover -s tests -v

每个用例对应 2026-10-25 独立评估的一条复现：旧代码上红、新代码上绿。
测试用的假 token 在运行时拼出来，避免仓库里出现可被 gitleaks 命中的字面量。
"""
import functools, importlib.util, json, os, shutil, subprocess, sys, tempfile, threading, unittest
from http.server import HTTPServer, SimpleHTTPRequestHandler
from unittest import mock

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(REPO, "tools")
DEMO = os.path.join(REPO, "demo", "www")
RUNNER = os.path.join(TOOLS, "ledger-run.py")
SECRET_SCAN = os.path.join(TOOLS, "fallback", "secret-scan.py")


def load_runner():
    spec = importlib.util.spec_from_file_location("ledger_run", RUNNER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lr = load_runner()
FAKE_GH = "gh" + "p_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4"  # 假 token，运行时拼接


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class SiteCase(unittest.TestCase):
    """在临时目录里放一份 demo 站点，按需注入缺陷。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="qa gates ")  # 故意带空格
        # demo 页引用 ../../dna.css：保持同样的两级目录结构
        self.root = os.path.join(self.tmp, "site root", "www")
        shutil.copytree(DEMO, self.root)
        shutil.copy(os.path.join(REPO, "dna.css"), os.path.join(self.tmp, "dna.css"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, name, text, mode="a"):
        with open(os.path.join(self.root, name), mode, encoding="utf-8") as f:
            f.write(text)

    def gate(self, fn, url="http://127.0.0.1:9", ctx=None):
        return fn(self.root, url, ctx or {})[0]


class TestCleanDemo(SiteCase):
    def test_demo_passes_every_static_gate(self):
        for fn in (lr.ck_g1, lr.ck_g4, lr.ck_g15, lr.ck_a1, lr.ck_a2, lr.ck_a5,
                   lr.ck_t1, lr.ck_t2, lr.ck_g121, lr.ck_g124):
            with self.subTest(gate=fn.__name__):
                self.assertEqual(self.gate(fn), "pass")


class TestPathsWithSpaces(SiteCase):
    """P1-2：路径含空格时 grep 类门禁不得假 PASS。"""

    def test_a1_font_size(self):
        self.write("index.html", '<p style="font-size:13px">x</p>')
        self.assertEqual(self.gate(lr.ck_a1), "fail")

    def test_g1_secret_in_spaced_root(self):
        self.write("leak.txt", f"token {FAKE_GH}\n", "w")
        self.assertEqual(self.gate(lr.ck_g1), "fail")

    def test_a2_spacing(self):
        self.write("index.html", '<div style="margin:13px">x</div>')
        self.assertEqual(self.gate(lr.ck_a2), "fail")


class TestScriptExitCode(SiteCase):
    """P1-1：外部门禁脚本非零退出 / 超时一律 fail。"""

    def test_nonzero_exit_without_fail_text_is_fail(self):
        script = os.path.join(self.tmp, "bad gate.sh")
        with open(script, "w") as f:
            f.write("exit 3\n")
        with mock.patch.dict(os.environ, {"QA_GATES_SECURITY_GATE": script,
                                          "QA_GATES_SIZE_GATE": script}):
            self.assertEqual(self.gate(lr.ck_g1), "fail")
            self.assertEqual(self.gate(lr.ck_g4), "fail")

    def test_timeout_is_fail(self):
        with mock.patch.object(lr, "run_script", return_value=(None, "", "超时")):
            self.assertEqual(self.gate(lr.ck_g1), "fail")

    def test_missing_external_script_is_fail(self):
        with mock.patch.dict(os.environ, {"QA_GATES_SECURITY_GATE": "/nonexistent/gate.sh"}):
            self.assertEqual(self.gate(lr.ck_g1), "fail")


class TestNoShellInjection(SiteCase):
    """P1-3：site-url / site-root 不经 shell。"""

    def test_site_url_with_shell_metacharacters(self):
        marker = os.path.join(self.tmp, "PWNED")
        verdict = self.gate(lr.ck_g8, url=f"http://127.0.0.1:9; touch '{marker}'; echo")
        self.assertEqual(verdict, "fail")
        self.assertFalse(os.path.exists(marker))

    def test_non_http_scheme_rejected(self):
        self.assertEqual(self.gate(lr.ck_g8, url="file:///etc"), "fail")

    def test_site_root_with_shell_metacharacters(self):
        marker = os.path.join(self.tmp, "PWNED2")
        evil = os.path.join(self.tmp, f"x;touch {marker};y")
        shutil.copytree(DEMO, evil)
        for fn in (lr.ck_g1, lr.ck_g4, lr.ck_a1, lr.ck_a2, lr.ck_g121):
            fn(evil, "http://127.0.0.1:9", {})
        self.assertFalse(os.path.exists(marker))

    def test_g8_reachable_local_server(self):
        srv = HTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=self.root))
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            self.assertEqual(self.gate(lr.ck_g8, url=f"http://127.0.0.1:{srv.server_port}"), "pass")
        finally:
            srv.shutdown()
            srv.server_close()


class TestMotionWhitelist(SiteCase):
    """P1-4：动效白名单逐属性判定，且不截断。"""

    def test_mixed_transition_is_fail(self):
        self.write("index.html", "<style>.a{transition: transform .2s, width .2s}</style>")
        self.assertEqual(self.gate(lr.ck_g121), "fail")

    def test_transition_all_and_implicit_all(self):
        for decl in ("transition: all .2s", "transition: .2s ease", "transition-property: height"):
            with self.subTest(decl=decl):
                self.write("index.html", f"<style>.b{{{decl}}}</style>", "w")
                self.assertEqual(self.gate(lr.ck_g121), "fail")

    def test_whitelisted_transitions_pass(self):
        self.write("index.html", "<style>.c{transition: transform 150ms cubic-bezier(0.2,0,0.38,0.9), "
                                 "opacity 70ms linear}.d{-webkit-transition: opacity .1s}"
                                 ".e{transition: none}</style>", "w")
        self.assertEqual(self.gate(lr.ck_g121), "pass")

    def test_violation_after_40_declarations(self):
        ok = "".join(f".k{i}{{transition: opacity .1s}}" for i in range(60))
        self.write("index.html", f"<style>{ok}.z{{transition: width .2s}}</style>", "w")
        self.assertEqual(self.gate(lr.ck_g121), "fail")

    def test_keyframes_non_whitelisted_property(self):
        self.write("index.html", "<style>@keyframes grow{from{width:0}to{width:10px}}</style>")
        self.assertEqual(self.gate(lr.ck_g121), "fail")

    def test_keyframes_transform_opacity_pass(self):
        self.write("index.html", "<style>@keyframes fade{0%{opacity:0;transform:scale(.9)}"
                                 "100%{opacity:1;transform:none}}</style>", "w")
        self.assertEqual(self.gate(lr.ck_g121), "pass")


class TestSecretScan(SiteCase):
    """P1-5：扫全部文本文件、更全的 token 规则、无大小写误报、allowlist 生效。"""

    def scan(self, *extra):
        p = subprocess.run([sys.executable, SECRET_SCAN, "--root", self.root, *extra],
                           capture_output=True, text=True)
        return p.returncode, p.stdout

    def test_tokens_in_unlisted_extensions(self):
        for name in (".env", "app.mjs", "main.js.map", "icon.svg"):
            with self.subTest(file=name):
                self.write(name, f"k={FAKE_GH}\n", "w")
                rc, out = self.scan()
                self.assertEqual(rc, 1, out)
                os.remove(os.path.join(self.root, name))

    def test_more_token_shapes(self):
        tokens = ["github" + "_pat_" + "A" * 30, "sk-" + "ant-" + "b" * 30, "AI" + "za" + "C" * 35]
        for tok in tokens:
            with self.subTest(prefix=tok[:6]):
                self.write("x.txt", f"{tok}\n", "w")
                self.assertEqual(self.scan()[0], 1)

    def test_lowercase_secret_word_is_not_a_hit(self):
        self.write("index.html", "<p>Our secret sauce</p>")
        self.assertEqual(self.scan()[0], 0)

    def test_classification_marking_is_a_hit(self):
        self.write("index.html", "<p>TOP SECRET</p>")
        self.assertEqual(self.scan()[0], 1)

    def test_allowlist_excludes_line_and_is_not_scanned_itself(self):
        self.write("index.html", "<p>本工具负责查绝密泄露（data-room 敏感扫描）</p>")
        self.assertEqual(self.scan()[0], 1)
        self.write(".publish-allowlist", "# 注释：绝密\n绝密泄露（data-room 敏感扫描\n", "w")
        self.assertEqual(self.scan()[0], 0)

    def test_binary_files_skipped(self):
        with open(os.path.join(self.root, "font.woff2"), "wb") as f:
            f.write(b"\0\0" + FAKE_GH.encode())
        self.assertEqual(self.scan()[0], 0)


class TestLocalResources(SiteCase):
    """P2-4：G15 站内资源完整性。"""

    def test_missing_image(self):
        self.write("index.html", '<img src="missing.png" alt="x">')
        self.assertEqual(self.gate(lr.ck_g15), "fail")

    def test_dead_links(self):
        for a in ('<a href="#">x</a>', '<a href="">x</a>', '<a href="javascript:void(0)">x</a>',
                  '<a href="#nowhere">x</a>'):
            with self.subTest(a=a):
                shutil.copy(os.path.join(DEMO, "index.html"), os.path.join(self.root, "index.html"))
                self.write("index.html", a)
                self.assertEqual(self.gate(lr.ck_g15), "fail")

    def test_script_and_comment_text_ignored(self):
        self.write("index.html", '<script>a.href = "#"; img.src = "nope.png";</script>'
                                 '<!-- <img src="old.png"> --><script src="demo.svg"></script>')
        self.assertEqual(self.gate(lr.ck_g15), "pass")

    def test_valid_refs(self):
        self.write("index.html", '<a href="#top" id="top">x</a><a href="en.html?x=1#y">e</a>'
                                 '<a href="https://example.com/">ext</a><a href="mailto:a@b.c">m</a>'
                                 '<a href="/demo.svg">abs</a>')
        self.assertEqual(self.gate(lr.ck_g15), "pass")


class TestV4(unittest.TestCase):
    """P2-2：V4 不同义反复、不连锁。"""

    def fail_gate(self, gid, evidence):
        return {"gate_id": gid, "name": gid, "verdict": "fail", "evidence": evidence}

    def test_fail_without_output_evidence(self):
        g = self.fail_gate("A1", [{"type": "cmd", "ref": "grep"}])
        ctx = {"gates": [g], "interceptions": lr.build_interceptions([g])}
        self.assertEqual(lr.ck_v4("", "", ctx)[0], "fail")

    def test_fail_with_output_evidence(self):
        g = self.fail_gate("A1", [{"type": "cmd", "ref": "grep"}, {"type": "output", "ref": "hits=1"}])
        ctx = {"gates": [g], "interceptions": lr.build_interceptions([g])}
        self.assertEqual(lr.ck_v4("", "", ctx)[0], "pass")

    def test_v4_fail_is_not_an_interception(self):
        gates = [self.fail_gate("V4", [{"type": "note", "ref": "open"}])]
        self.assertEqual(lr.build_interceptions(gates), [])

    def test_disposing_original_run_clears_v4(self):
        open_run = {"run_id": "r1", "interceptions": [{"gate_id": "A1", "status": "pending"}]}
        v4_only = {"run_id": "r2", "interceptions": []}
        self.assertEqual(lr.ck_v4("", "", {"prior_runs": [open_run, v4_only]})[0], "fail")
        open_run["interceptions"][0]["status"] = "closed"
        self.assertEqual(lr.ck_v4("", "", {"prior_runs": [open_run, v4_only]})[0], "pass")


class TestRunnerEndToEnd(SiteCase):
    """P2-1 / P2-5 / P2-6 / P2-7：缺失根目录、台账路径与原子写入。"""

    def run_cli(self, root, ledger, url="http://127.0.0.1:9"):
        env = dict(os.environ, QA_GATES_LEDGER=ledger)
        return subprocess.run([sys.executable, RUNNER, "--release", "t", "--change", "t",
                               "--site-root", root, "--site-url", url],
                              capture_output=True, text=True, env=env)

    def test_missing_root_exits_2_without_writing(self):
        ledger = os.path.join(self.tmp, "ledger.json")
        p = self.run_cli(os.path.join(self.tmp, "nope"), ledger)
        self.assertEqual(p.returncode, 2)
        self.assertFalse(os.path.exists(ledger))

    def test_ledger_env_and_relative_paths(self):
        ledger = os.path.join(self.tmp, "ledger.json")
        p = self.run_cli(self.root, ledger)
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)  # G8 连不上 -> fail
        with open(ledger, encoding="utf-8") as f:
            d = json.load(f)
        self.assertTrue(d["additive"])
        self.assertEqual(len(d["runs"]), 1)
        self.assertEqual(d["runs"][0]["interceptions"][0]["gate_id"], "G8")
        p = self.run_cli(DEMO, ledger)
        with open(ledger, encoding="utf-8") as f:
            d = json.load(f)
        self.assertEqual(len(d["runs"]), 2)
        self.assertEqual(d["runs"][1]["site_root"], os.path.join("demo", "www"))
        self.assertEqual([f for f in os.listdir(self.tmp) if f.endswith(".tmp")], [])

    def test_home_dir_is_masked(self):
        with mock.patch.dict(os.environ, {"HOME": self.tmp}):
            self.assertTrue(lr.display_path(self.root).startswith("~" + os.sep))

    def test_tampered_additive_flag_refuses_write(self):
        ledger = os.path.join(self.tmp, "ledger.json")
        with open(ledger, "w") as f:
            json.dump({"additive": False, "runs": []}, f)
        p = self.run_cli(self.root, ledger)
        self.assertNotEqual(p.returncode, 0)
        with open(ledger) as f:
            self.assertEqual(json.load(f), {"additive": False, "runs": []})


if __name__ == "__main__":
    unittest.main()
