import unittest

from rag_lens.metrics import hit_rate_at_k, reciprocal_rank


class TestMetrics(unittest.TestCase):
    def test_hit_rate(self):
        self.assertEqual(hit_rate_at_k(["b", "a", "c"], "a", 3), 1.0)
        self.assertEqual(hit_rate_at_k(["b", "c", "d"], "a", 3), 0.0)
        self.assertEqual(hit_rate_at_k(["a", "b"], "a", 1), 1.0)

    def test_reciprocal_rank(self):
        self.assertEqual(reciprocal_rank(["a", "b"], "a", 5), 1.0)
        self.assertEqual(reciprocal_rank(["b", "a"], "a", 5), 0.5)
        self.assertAlmostEqual(reciprocal_rank(["b", "c", "a"], "a", 5), 1 / 3, places=6)
        self.assertEqual(reciprocal_rank(["b", "c"], "a", 5), 0.0)


if __name__ == "__main__":
    unittest.main()
