import contextlib
import io
import unittest

from chmodkit.cli import main


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


class CliTest(unittest.TestCase):
    def test_apply_assignment(self):
        code, out, err = run("--apply", "777", "u=r")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "477 r--rwxrwx")

    def test_apply_multi_clause(self):
        code, out, err = run("--apply", "777", "u+x,g-w")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "757 rwxr-xrwx")

    def test_format_special_bits(self):
        code, out, err = run("--format", "4755")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "rwsr-xr-x")

    def test_format_bad_octal_reports_position(self):
        code, out, err = run("--format", "888")
        self.assertEqual(code, 1)
        self.assertIn("第 1 位不是八进制数字", err)

    def test_octal_still_works(self):
        code, out, err = run("--octal", "755")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "755 rwxr-xr-x")

    def test_apply_empty_clause_reports_position(self):
        code, out, err = run("--apply", "777", "u+x,,g-w")
        self.assertEqual(code, 1)
        self.assertIn("第 5 位是空子句", err)
