"""Tests for embed.py functions."""
import os, tempfile, unittest
from . import embed

class EmbedTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="cip-embedtest-")
        os.makedirs(os.path.join(self.root, ".cip", "data"))
        # Create a test file
        test_file = os.path.join(self.root, "test.py")
        with open(test_file, "w") as f:
            f.write("def hello():\n    return 'world'")
        from . import indexer
        indexer.sync(self.root, full=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.root, ignore_errors=True)

    def test_get_embedder(self):
        """Test get_embedder function returns valid embedder."""
        embedder = embed.get_embedder(self.root)
        self.assertIsNotNone(embedder)
        # Test that embedder can encode text
        vectors = embedder.encode(["test text"])
        self.assertEqual(len(vectors), 1)
        self.assertGreater(len(vectors[0]), 0)

    def test_hashing_embedder(self):
        """Test HashingEmbedder as fallback."""
        hashing = embed.HashingEmbedder(dim=384)
        vectors = hashing.encode(["test text"])
        self.assertEqual(len(vectors), 1)
        self.assertEqual(len(vectors[0]), 384)

def run_embed_selftest():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(EmbedTest)
    res = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if res.wasSuccessful() else 1
