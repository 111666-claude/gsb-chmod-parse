import unittest

from chmodkit.mode import (
    ERR_BAD_OCTAL_DIGIT,
    ERR_EMPTY_CLAUSE,
    ERR_EMPTY_EXPR,
    ERR_OCTAL_TOO_LONG,
    ERR_UNKNOWN_LETTER,
    ERR_UNKNOWN_OP,
    ERR_UNKNOWN_WHO,
    ModeError,
    apply_symbolic,
    format_mode,
    parse_octal,
)


class ExpectModeError:
    def __init__(self, testcase, kind, position=-1):
        self.testcase = testcase
        self.kind = kind
        self.position = position

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.testcase.assertIsNotNone(exc_type, "应当抛出 ModeError")
        self.testcase.assertTrue(issubclass(exc_type, ModeError))
        self.testcase.assertEqual(exc.kind, self.kind)
        if self.position >= 0:
            self.testcase.assertEqual(exc.position, self.position)
        return True


class FormatTest(unittest.TestCase):
    def test_755(self):
        self.assertEqual(format_mode(0o755), "rwxr-xr-x")

    def test_644(self):
        self.assertEqual(format_mode(0o644), "rw-r--r--")

    def test_zero(self):
        self.assertEqual(format_mode(0), "---------")

    def test_suid_with_x(self):
        self.assertEqual(format_mode(0o4755), "rwsr-xr-x")

    def test_sgid_with_x(self):
        self.assertEqual(format_mode(0o2755), "rwxr-sr-x")

    def test_sticky_with_x(self):
        self.assertEqual(format_mode(0o1755), "rwxr-xr-t")

    def test_suid_without_x_uppercase(self):
        self.assertEqual(format_mode(0o4644), "rwSr--r--")

    def test_sgid_without_x_uppercase(self):
        self.assertEqual(format_mode(0o2644), "rw-r-Sr--")

    def test_sticky_without_x_uppercase(self):
        self.assertEqual(format_mode(0o1644), "rw-r--r-T")

    def test_all_special_bits(self):
        self.assertEqual(format_mode(0o7000), "--S--S--T")
        self.assertEqual(format_mode(0o7777), "rwsrwsrwt")


class OctalTest(unittest.TestCase):
    def test_parses(self):
        self.assertEqual(parse_octal("755"), 0o755)

    def test_leading_zero(self):
        self.assertEqual(parse_octal("0755"), 0o755)

    def test_four_digits_special(self):
        self.assertEqual(parse_octal("4755"), 0o4755)

    def test_bad_digit_position(self):
        with ExpectModeError(self, ERR_BAD_OCTAL_DIGIT, 0):
            parse_octal("888")
        with ExpectModeError(self, ERR_BAD_OCTAL_DIGIT, 1):
            parse_octal("78")
        with ExpectModeError(self, ERR_BAD_OCTAL_DIGIT, 2):
            parse_octal("778")

    def test_negative(self):
        with ExpectModeError(self, ERR_BAD_OCTAL_DIGIT, 0):
            parse_octal("-1")

    def test_empty(self):
        with ExpectModeError(self, ERR_EMPTY_EXPR):
            parse_octal("")

    def test_too_long(self):
        with ExpectModeError(self, ERR_OCTAL_TOO_LONG, 4):
            parse_octal("10755")


class SymbolicAssignmentTest(unittest.TestCase):
    def test_equals_clears_group_first(self):
        # README 口径：777 + u=r => 477
        self.assertEqual(apply_symbolic(0o777, "u=r"), 0o477)
        self.assertEqual(format_mode(apply_symbolic(0o777, "u=r")), "r--rwxrwx")

    def test_equals_empty_perms_clears(self):
        self.assertEqual(apply_symbolic(0o777, "u="), 0o077)
        self.assertEqual(apply_symbolic(0o755, "g="), 0o705)

    def test_equals_sets_only_listed(self):
        self.assertEqual(apply_symbolic(0o777, "o=rx"), 0o775)

    def test_plus_minus_unchanged_semantics(self):
        self.assertEqual(apply_symbolic(0, "u+r"), 0o400)
        self.assertEqual(apply_symbolic(0o777, "u+x"), 0o777)
        self.assertEqual(apply_symbolic(0o777, "g-w"), 0o757)


class MultiClauseTest(unittest.TestCase):
    def test_all_clauses_apply_in_order(self):
        # README 口径：777 + u+x,g-w => 757
        self.assertEqual(apply_symbolic(0o777, "u+x,g-w"), 0o757)

    def test_three_clauses(self):
        self.assertEqual(apply_symbolic(0, "u+r,g+w,o+x"), 0o421)

    def test_order_matters(self):
        self.assertEqual(apply_symbolic(0o777, "u-r,u+r"), 0o777)
        self.assertEqual(apply_symbolic(0o777, "u=rw,u-x"), 0o677)

    def test_empty_clause_reports_position(self):
        with ExpectModeError(self, ERR_EMPTY_CLAUSE, 3):
            apply_symbolic(0o777, "u+,")
        with ExpectModeError(self, ERR_EMPTY_CLAUSE, 0):
            apply_symbolic(0o777, ",u+x")
        with ExpectModeError(self, ERR_EMPTY_CLAUSE, 4):
            apply_symbolic(0o777, "u+x,,g-w")

    def test_empty_expression(self):
        with ExpectModeError(self, ERR_EMPTY_EXPR):
            apply_symbolic(0o777, "")


class XSpecialTest(unittest.TestCase):
    def test_uppercase_x_when_no_execute(self):
        self.assertEqual(apply_symbolic(0o644, "a+X"), 0o644)

    def test_uppercase_x_when_any_execute(self):
        self.assertEqual(apply_symbolic(0o645, "a+X"), 0o755)

    def test_equals_does_not_touch_special_bits(self):
        self.assertEqual(apply_symbolic(0o4755, "u=rwx"), 0o4755)


class UnknownTokenTest(unittest.TestCase):
    def test_unknown_who(self):
        with ExpectModeError(self, ERR_UNKNOWN_WHO, 0):
            apply_symbolic(0o777, "z+r")
        with ExpectModeError(self, ERR_UNKNOWN_WHO, 4):
            apply_symbolic(0o777, "u+x,q+r")

    def test_unknown_operator(self):
        with ExpectModeError(self, ERR_UNKNOWN_OP, 1):
            apply_symbolic(0o777, "u?r")
        with ExpectModeError(self, ERR_UNKNOWN_OP, 1):
            apply_symbolic(0o777, "u")
        with ExpectModeError(self, ERR_UNKNOWN_OP, 5):
            apply_symbolic(0o777, "u+x,gr")

    def test_unknown_letter(self):
        with ExpectModeError(self, ERR_UNKNOWN_LETTER, 2):
            apply_symbolic(0o777, "u+z")
        with ExpectModeError(self, ERR_UNKNOWN_LETTER, 6):
            apply_symbolic(0o777, "u+x,g+z")

    def test_combined_who_and_default(self):
        self.assertEqual(apply_symbolic(0, "ug+x"), 0o110)
        self.assertEqual(apply_symbolic(0, "+x"), 0o111)
        self.assertEqual(apply_symbolic(0o777, "=r"), 0o444)


class InvariantTest(unittest.TestCase):
    def test_repeated_application_idempotent(self):
        for spec in ("u=r", "u+x,g-w", "a=rwx", "o-w", "g+x", "u=rw,g=r,o=r"):
            once = apply_symbolic(0o751, spec)
            twice = apply_symbolic(once, spec)
            self.assertEqual(once, twice, spec)

    def test_format_parse_roundtrip_drops_special(self):
        # 格式化后再解析 rwx，应与去掉特殊位后的低 9 位一致
        for mode in (0o4755, 0o2755, 0o1755, 0o7000, 0o7777, 0o4644):
            text = format_mode(mode)
            parsed = sum(
                1 << (8 - index)
                for index, char in enumerate(text)
                if char in "rwxst"
            )
            self.assertEqual(parsed, mode & 0o777, oct(mode))

    def test_octal_format_roundtrip(self):
        for mode in (0o755, 0o644, 0o0, 0o777):
            self.assertEqual(parse_octal(format(mode, "o")), mode)
