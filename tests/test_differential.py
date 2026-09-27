import random
import unittest

from chmodkit.mode import ModeError, apply_symbolic, format_mode, parse_octal

try:
    from .chmod_reference import RefError, ref_apply_symbolic, ref_format_mode, ref_parse_octal
except ImportError:
    from chmod_reference import RefError, ref_apply_symbolic, ref_format_mode, ref_parse_octal

WHO_POOL = ["", "u", "g", "o", "a", "ug", "uo", "go", "ua", "q", "x", "ugz"]
OP_POOL = ["+", "-", "=", "?", "", "*"]
LETTER_POOL = ["r", "w", "x", "X", "rw", "rx", "wx", "rwx", "", "z", "rq", "xwX"]


def make_spec(rng):
    clause_count = rng.randint(1, 4)
    clauses = []
    for _ in range(clause_count):
        roll = rng.random()
        if roll < 0.75:
            clause = rng.choice(WHO_POOL) + rng.choice(OP_POOL) + rng.choice(LETTER_POOL)
        elif roll < 0.85:
            clause = ""  # 空子句
        else:
            clause = rng.choice(["u", "g+x,", "=rw,", ",,", "u++r"])
        clauses.append(clause)
    return ",".join(clauses)


def make_octal(rng):
    roll = rng.random()
    if roll < 0.7:
        digits = "01234567"
        return "".join(rng.choice(digits) for _ in range(rng.randint(1, 4)))
    if roll < 0.8:
        digits = "0123456789abz- "
        return "".join(rng.choice(digits) for _ in range(rng.randint(1, 5)))
    if roll < 0.9:
        return ""
    return "1" * rng.randint(5, 7)


class DifferentialTest(unittest.TestCase):
    def test_documented_samples(self):
        for current, spec, expected in (
            (0o777, "u=r", 0o477),
            (0o777, "u+x,g-w", 0o757),
        ):
            self.assertEqual(apply_symbolic(current, spec), expected)
            self.assertEqual(ref_apply_symbolic(current, spec), expected)
        for mode, text in (
            (0o4755, "rwsr-xr-x"),
            (0o2755, "rwxr-sr-x"),
            (0o1755, "rwxr-xr-t"),
        ):
            self.assertEqual(format_mode(mode), text)
            self.assertEqual(ref_format_mode(mode), text)

    def test_random_apply_10000(self):
        rng = random.Random(20260928)
        mismatches = 0
        for _ in range(10000):
            current = rng.randrange(0o10000)
            spec = make_spec(rng)
            try:
                actual = apply_symbolic(current, spec)
                actual_err = None
            except ModeError as error:
                actual = None
                actual_err = (error.kind, error.position)
            try:
                expected = ref_apply_symbolic(current, spec)
                expected_err = None
            except RefError as error:
                expected = None
                expected_err = (error.kind, error.position)
            if actual != expected or actual_err != expected_err:
                mismatches += 1
                if mismatches <= 5:
                    raise AssertionError(
                        "mismatch current=%o spec=%r actual=%s/%s ref=%s/%s"
                        % (current, spec, oct(actual) if actual is not None else None,
                           actual_err, oct(expected) if expected is not None else None,
                           expected_err)
                    )
        self.assertEqual(mismatches, 0)

    def test_random_octal_10000(self):
        rng = random.Random(4755)
        for _ in range(10000):
            text = make_octal(rng)
            try:
                actual = parse_octal(text)
                actual_err = None
            except ModeError as error:
                actual = None
                actual_err = (error.kind, error.position)
            try:
                expected = ref_parse_octal(text)
                expected_err = None
            except RefError as error:
                expected = None
                expected_err = (error.kind, error.position)
            self.assertEqual((actual, actual_err), (expected, expected_err), repr(text))

    def test_format_agrees_on_all_12bit_modes(self):
        for mode in range(0o10000):
            self.assertEqual(format_mode(mode), ref_format_mode(mode), oct(mode))
