"""cip selftest — end-to-end tests against a throwaway fixture repo.
Run: cip selftest"""
import json, os, shutil, tempfile, unittest

FIX_TOKEN = '''class TokenManager:
    def validate(self, token):
        return bool(token)

    def refresh(self, token):
        return "refreshed"

def refresh_token(tm, token):
    return tm.refresh(token)
'''
FIX_TEST = '''from src.token import TokenManager

def test_refresh():
    tm = TokenManager()
    assert tm.refresh("x") == "refreshed"
'''
FIX_VITEST = {"testResults": [{"name": "tests/test_token.py", "assertionResults": [
    {"ancestorTitles": [], "title": "refresh works", "status": "failed", "duration": 12}]}]}

class CIPCore(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="cip-selftest-")
        os.makedirs(os.path.join(self.root, ".cip", "data"))
        os.makedirs(os.path.join(self.root, "src"))
        os.makedirs(os.path.join(self.root, "tests"))
        open(os.path.join(self.root, "src", "token.py"), "w").write(FIX_TOKEN)
        open(os.path.join(self.root, "tests", "test_token.py"), "w").write(FIX_TEST)
        from . import indexer
        self.stats = indexer.sync(self.root, full=True)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_sync_counts(self):
        self.assertGreaterEqual(self.stats["files"], 2)
        self.assertGreaterEqual(self.stats["symbols"], 5)

    def test_symbol_lookup(self):
        from . import retrieve
        hits = retrieve.find_symbol(self.root, "TokenManager")
        self.assertTrue(hits)
        self.assertEqual(hits[0]["kind"], "class")

    def test_search(self):
        from . import retrieve
        self.assertTrue(retrieve.search(self.root, "refresh token"))

    def test_context_pack(self):
        from . import retrieve
        pack = retrieve.context(self.root, symbol="TokenManager")
        self.assertTrue(pack["sections"])

    def test_imports_and_tested_by(self):
        from .store import connect
        con = connect(self.root)
        self.assertGreaterEqual(con.execute(
            "SELECT COUNT(*) c FROM edges WHERE kind='imports'").fetchone()["c"], 1)
        self.assertGreaterEqual(con.execute(
            "SELECT COUNT(*) c FROM edges WHERE kind='tested_by'").fetchone()["c"], 1)

    def test_summary_and_map(self):
        from . import summarize
        s = summarize.summary(self.root, "src/token.py")
        self.assertIn("TokenManager", s["summary"])
        m = summarize.map_(self.root)
        self.assertGreaterEqual(m["totals"]["files"], 2)

    def test_ingest_and_broken(self):
        from . import runtime_adapters
        fx = os.path.join(self.root, ".cip", "data", "vitest.json")
        json.dump(FIX_VITEST, open(fx, "w"))
        r = runtime_adapters.ingest(self.root, "vitest", fx)
        self.assertGreaterEqual(r["ingested"], 1)
        b = runtime_adapters.broken(self.root)
        self.assertTrue(b["signals"])

    def test_router(self):
        from . import router
        self.assertEqual(router.route("why is this workaround here")["intent"], "history")
        self.assertEqual(router.route("overview of the system")["intent"], "architecture")

    def test_export(self):
        from . import export
        out = os.path.join(self.root, ".cip", "data", "dump.json")
        r = export.export(self.root, "json", out)
        self.assertGreater(r["bytes"], 100)

def run_selftest():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CIPCore)
    res = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if res.wasSuccessful() else 1
