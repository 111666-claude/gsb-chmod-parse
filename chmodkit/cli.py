"""命令行入口：解析权限。"""

import argparse
import sys

from .mode import ModeError, apply_symbolic, format_mode, parse_octal


def build_parser():
    parser = argparse.ArgumentParser(prog="chmod-parse", description="权限解析")
    parser.add_argument("--octal", help="八进制权限，例如 755")
    parser.add_argument("--format", type=lambda text: int(text, 8), help="把八进制权限格式化成 rwx")
    parser.add_argument("--apply", nargs=2, metavar=("当前", "表达式"), help="把符号表达式作用到当前权限上")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.format is not None:
            print(format_mode(args.format))
            return 0
        if args.octal is not None:
            mode = parse_octal(args.octal)
            print("%o %s" % (mode, format_mode(mode)))
            return 0
        if args.apply:
            current = parse_octal(args.apply[0]) if args.apply[0][0] != "r" else 0
            result = apply_symbolic(current, args.apply[1])
            print("%o %s" % (result, format_mode(result)))
            return 0
    except (ModeError, ValueError) as error:
        print("错误：%s" % error, file=sys.stderr)
        return 1
    print("错误：需要 --octal / --format / --apply", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
