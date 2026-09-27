"""和 tests/posix_reference.py 的 POSIX 参考实现对照。"""

import random
import unittest

from chmodkit import mode
from chmodkit.mode import ModeError

import posix_reference
from posix_reference import ReferenceError


SAMPLES = [
    (0o777, "u=r"),
    (0o777, "u+x,g-w"),
    (0o777, "u=rwx,g=rx,o="),
    (0o000, "a+rwx"),
    (0o644, "g+w,o-r"),
    (0o4755, "u=r"),
    (0o7777, "a="),
    (0o100, "a+X"),
    (0o444, "a+X"),
    (0o777, "ug=rw,o+x"),
    (0o777, "u+r-x,g=w"),
    (0o777, ""),
    (0o777, "u+r,,g-w"),
    (0o777, "u+r,"),
    (0o777, ",u+r"),
    (0o777, "q+x"),
    (0o777, "u~r"),
    (0o777, "u+z"),
    (0o777, "u+"),
    (0o777, "u"),
]


def random_spec(rng):
    clauses = []
    for _ in range(rng.randrange(1, 4)):
        parts = []
        if rng.random() < 0.8:
            parts.append("".join(rng.choice("ugoaaq") for _ in range(rng.randrange(1, 3))))
        for _ in range(rng.randrange(1, 3)):
            parts.append(rng.choice("=+-~"))
            parts.append("".join(rng.choice("rwxXsz") for _ in range(rng.randrange(0, 4))))
        clauses.append("".join(parts))
    return ",".join(clauses)


class AgainstReferenceTest(unittest.TestCase):
    def check_both(self, current, spec):
        try:
            expected = posix_reference.apply_symbolic(current, spec)
        except ReferenceError:
            with self.assertRaises(ModeError, msg="%o %r" % (current, spec)):
                mode.apply_symbolic(current, spec)
            return
        try:
            actual = mode.apply_symbolic(current, spec)
        except ModeError:
            self.fail("参考实现接受但主实现报错：%o %r" % (current, spec))
        self.assertEqual(actual, expected, "%o %r" % (current, spec))

    def test_samples(self):
        for current, spec in SAMPLES:
            self.check_both(current, spec)

    def test_random_cases(self):
        rng = random.Random(20260928)
        for _ in range(10000):
            current = rng.randrange(0o10000)
            self.check_both(current, random_spec(rng))

    def test_format_matches_reference(self):
        for value in list(range(0o1000)) + [0o4755, 0o2755, 0o1755, 0o7777, 0o7641]:
            self.assertEqual(mode.format_mode(value), posix_reference.format_mode(value))

    def test_parse_octal_matches_reference(self):
        rng = random.Random(7)
        texts = ["", "0", "755", "0755", "4755", "7777", "8", "888", "-1", "10755", "75a", " 1"]
        texts += ["".join(rng.choice("0123456789a-") for _ in range(rng.randrange(0, 6))) for _ in range(2000)]
        for text in texts:
            try:
                expected = posix_reference.parse_octal(text)
            except ReferenceError:
                with self.assertRaises(ModeError, msg=repr(text)):
                    mode.parse_octal(text)
                continue
            self.assertEqual(mode.parse_octal(text), expected, repr(text))


if __name__ == "__main__":
    unittest.main()
