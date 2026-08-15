"""Tests for gapfill.py functions."""
import os, tempfile, unittest
from . import gapfill

class GapFillTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="cip-gapfilltest-")
        os.makedirs(os.path.join(self.root, ".cip", "data"))
        from . import indexer
        indexer.sync(self.root, full=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.root, ignore_errors=True)

    def test_con_function(self):
        """Test _con helper function for database connection."""
        con = gapfill._con(self.root)
        self.assertIsNotNone(con)
        # Test that connection can execute queries
        result = con.execute("SELECT 1").fetchone()
        self.assertEqual(result[0], 1)

    def test_pattern_count(self):
        """Test _pattern_count function."""
        con = gapfill._con(self.root)
        # Count occurrences of a pattern
        count = gapfill._pattern_count(con, "import")
        self.assertGreaterEqual(count, 0)

    def test_pattern_paths(self):
        """Test _pattern_paths function."""
        con = gapfill._con(self.root)
        # Get paths containing a pattern
        paths = gapfill._pattern_paths(con, "import", limit=10)
        self.assertIsInstance(paths, list)

def run_gapfill_selftest():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(GapFillTest)
    res = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if res.wasSuccessful() else 1
