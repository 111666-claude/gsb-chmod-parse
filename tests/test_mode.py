import time
import unittest

from chmodkit.mode import ModeError, apply_symbolic, format_mode, parse_octal


class FormatTest(unittest.TestCase):
    def test_755(self):
        self.assertEqual(format_mode(0o755), "rwxr-xr-x")

    def test_644(self):
        self.assertEqual(format_mode(0o644), "rw-r--r--")

    def test_zero(self):
        self.assertEqual(format_mode(0), "---------")

    def test_setuid(self):
        self.assertEqual(format_mode(0o4755), "rwsr-xr-x")

    def test_setgid(self):
        self.assertEqual(format_mode(0o2755), "rwxr-sr-x")

    def test_sticky(self):
        self.assertEqual(format_mode(0o1755), "rwxr-xr-t")

    def test_setuid_without_execute(self):
        self.assertEqual(format_mode(0o4644), "rwSr--r--")

    def test_setgid_without_execute(self):
        self.assertEqual(format_mode(0o2644), "rw-r-Sr--")

    def test_sticky_without_execute(self):
        self.assertEqual(format_mode(0o1644), "rw-r--r-T")

    def test_all_special(self):
        self.assertEqual(format_mode(0o7777), "rwsrwsrwt")


class OctalTest(unittest.TestCase):
    def test_parses(self):
        self.assertEqual(parse_octal("755"), 0o755)

    def test_leading_zero(self):
        self.assertEqual(parse_octal("0755"), 0o755)

    def test_four_digits_with_special(self):
        self.assertEqual(parse_octal("4755"), 0o4755)

    def test_bad_digit_reports_position(self):
        with self.assertRaises(ModeError) as caught:
            parse_octal("888")
        self.assertEqual(caught.exception.position, 1)
        self.assertIn("第 1 位不是八进制数字", str(caught.exception))

    def test_bad_digit_later_position(self):
        with self.assertRaises(ModeError) as caught:
            parse_octal("75a")
        self.assertEqual(caught.exception.position, 3)

    def test_empty(self):
        with self.assertRaises(ModeError) as caught:
            parse_octal("")
        self.assertIsNotNone(caught.exception.position)

    def test_negative(self):
        with self.assertRaises(ModeError) as caught:
            parse_octal("-1")
        self.assertEqual(caught.exception.position, 1)

    def test_too_long(self):
        with self.assertRaises(ModeError) as caught:
            parse_octal("10755")
        self.assertIsNotNone(caught.exception.position)

    def test_roundtrip_after_masking_special_bits(self):
        for mode in (0, 0o1, 0o755, 0o4755, 0o2755, 0o1755, 0o7777):
            plain = mode & 0o777
            self.assertEqual(parse_octal("%o" % plain), plain)


class SymbolicTest(unittest.TestCase):
    def test_add_user_read(self):
        self.assertEqual(apply_symbolic(0, "u+r"), 0o400)

    def test_add_already_present(self):
        self.assertEqual(apply_symbolic(0o777, "u+x"), 0o777)

    def test_remove_group_write(self):
        self.assertEqual(apply_symbolic(0o777, "g-w"), 0o757)

    def test_all_who(self):
        self.assertEqual(apply_symbolic(0, "a+x"), 0o111)

    def test_assign_clears_group_first(self):
        self.assertEqual(apply_symbolic(0o777, "u=r"), 0o477)

    def test_assign_empty_clears_group(self):
        self.assertEqual(apply_symbolic(0o777, "go="), 0o700)

    def test_assign_keeps_other_groups(self):
        self.assertEqual(apply_symbolic(0o644, "g=rwx"), 0o674)

    def test_assign_keeps_special_bits(self):
        self.assertEqual(apply_symbolic(0o4777, "u=r"), 0o4477)

    def test_multiple_clauses_in_order(self):
        self.assertEqual(apply_symbolic(0o777, "u+x,g-w"), 0o757)

    def test_multiple_clauses_order_matters(self):
        self.assertEqual(apply_symbolic(0, "a+r,u-r"), 0o044)

    def test_multiple_who_letters(self):
        self.assertEqual(apply_symbolic(0, "ug+x"), 0o110)

    def test_multiple_ops_in_one_clause(self):
        self.assertEqual(apply_symbolic(0o777, "u+r-x"), 0o677)

    def test_no_who_defaults_to_all(self):
        self.assertEqual(apply_symbolic(0, "+x"), 0o111)

    def test_capital_x_with_execute_present(self):
        self.assertEqual(apply_symbolic(0o100, "a+X"), 0o111)

    def test_capital_x_without_execute(self):
        self.assertEqual(apply_symbolic(0o444, "a+X"), 0o444)

    def test_empty_spec(self):
        with self.assertRaises(ModeError):
            apply_symbolic(0o777, "")

    def test_empty_clause_reports_position(self):
        with self.assertRaises(ModeError) as caught:
            apply_symbolic(0o777, "u+r,,g-w")
        self.assertEqual(caught.exception.position, 5)

    def test_trailing_comma_is_empty_clause(self):
        with self.assertRaises(ModeError):
            apply_symbolic(0o777, "u+r,")

    def test_unknown_who_reports_position(self):
        with self.assertRaises(ModeError) as caught:
            apply_symbolic(0o777, "q+x")
        self.assertEqual(caught.exception.position, 1)

    def test_unknown_operator_reports_position(self):
        with self.assertRaises(ModeError) as caught:
            apply_symbolic(0o777, "ug~r")
        self.assertEqual(caught.exception.position, 3)

    def test_bad_letter(self):
        with self.assertRaises(ModeError) as caught:
            apply_symbolic(0o777, "u+z")
        self.assertEqual(caught.exception.position, 3)

    def test_bad_letter_in_later_clause(self):
        with self.assertRaises(ModeError) as caught:
            apply_symbolic(0o777, "u+r,g+z")
        self.assertEqual(caught.exception.position, 7)

    def test_missing_operator(self):
        with self.assertRaises(ModeError):
            apply_symbolic(0o777, "u")

    def test_missing_perms(self):
        with self.assertRaises(ModeError):
            apply_symbolic(0o777, "u+")

    def test_idempotent(self):
        for mode in (0, 0o777, 0o4755, 0o644):
            for spec in ("u=r", "u+x,g-w", "a=rw", "go+r-w"):
                once = apply_symbolic(mode, spec)
                self.assertEqual(apply_symbolic(once, spec), once)

    def test_scales_linearly(self):
        spec = "u+r,g-w,o=x," * 20 + "a+rwx,u=rx"
        mode = 0o777
        started = time.monotonic()
        for _ in range(100000):
            mode = apply_symbolic(mode, spec)
        elapsed = time.monotonic() - started
        self.assertEqual(mode, apply_symbolic(0o777, spec))
        self.assertLess(elapsed, 30)


if __name__ == "__main__":
    unittest.main()
