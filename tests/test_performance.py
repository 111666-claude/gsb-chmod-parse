import time
import unittest

from chmodkit.mode import apply_symbolic


class PerformanceTest(unittest.TestCase):
    def test_100k_clauses_linear(self):
        # 10 万个子句的单一表达式：必须线性完成，不能有正则回溯式的爆炸
        spec = ",".join(("u+x" if index % 2 == 0 else "g-w") for index in range(100000))
        start = time.perf_counter()
        result = apply_symbolic(0o777, spec)
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, 5.0, "耗时 %.2fs，超过 5s" % elapsed)
        self.assertEqual(result, 0o757)
        # 同一表达式重复作用结果相同
        self.assertEqual(apply_symbolic(result, spec), result)

    def test_100k_applications(self):
        spec = "u=rwx,go=rx"
        start = time.perf_counter()
        for _ in range(100000):
            apply_symbolic(0o027, spec)
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, 10.0, "耗时 %.2fs" % elapsed)
