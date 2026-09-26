import unittest

from chmodkit.mode import ModeError, apply_symbolic, format_mode, parse_octal


class FormatTest(unittest.TestCase):
    def test_755(self):
        self.assertEqual(format_mode(0o755), "rwxr-xr-x")

    def test_644(self):
        self.assertEqual(format_mode(0o644), "rw-r--r--")

    def test_zero(self):
        self.assertEqual(format_mode(0), "---------")


class OctalTest(unittest.TestCase):
    def test_parses(self):
        self.assertEqual(parse_octal("755"), 0o755)

    def test_leading_zero(self):
        self.assertEqual(parse_octal("0755"), 0o755)


class SymbolicTest(unittest.TestCase):
    def test_add_user_read(self):
        self.assertEqual(apply_symbolic(0, "u+r"), 0o400)

    def test_add_already_present(self):
        self.assertEqual(apply_symbolic(0o777, "u+x"), 0o777)

    def test_remove_group_write(self):
        self.assertEqual(apply_symbolic(0o777, "g-w"), 0o757)

    def test_all_who(self):
        self.assertEqual(apply_symbolic(0, "a+x"), 0o111)

    def test_bad_letter(self):
        with self.assertRaises(ModeError):
            apply_symbolic(0o777, "u+z")
