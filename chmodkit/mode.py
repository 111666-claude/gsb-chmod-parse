"""权限：八进制、rwx 字符串与符号表达式。只用标准库。"""

WHO = {"u": 6, "g": 3, "o": 0, "a": 8}


class ModeError(Exception):
    """权限表达式有问题。缺陷：不带位置。"""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


def format_mode(mode):
    """把权限整数写成 rwx 形式。缺陷：不显示 setuid/setgid/sticky。"""
    bits = ""
    for shift in (6, 3, 0):
        chunk = (mode >> shift) & 0x7
        bits += "r" if chunk & 4 else "-"
        bits += "w" if chunk & 2 else "-"
        bits += "x" if chunk & 1 else "-"
    return bits


def parse_octal(text):
    """解析八进制权限。缺陷：不校验每一位的范围，也不限长度。"""
    return int(text, 8)


def apply_symbolic(current, spec):
    """把符号表达式作用到当前权限上。

    缺陷：'=' 只加位不清位；多个逗号子句只处理第一个。
    """
    clause = spec.split(",")[0]
    if not clause:
        raise ModeError("空表达式")
    who = clause[0] if clause[0] in WHO else "a"
    rest = clause[1:] if clause[0] in WHO else clause
    if not rest or rest[0] not in "=+-":
        raise ModeError("缺少操作符：%r" % clause)
    operator = rest[0]
    letters = rest[1:]
    mask = 0
    for group, shift in (("u", 6), ("g", 3), ("o", 0)):
        if who in ("a", group):
            for letter in letters:
                if letter == "r":
                    mask |= 4 << shift
                elif letter == "w":
                    mask |= 2 << shift
                elif letter == "x":
                    mask |= 1 << shift
                elif letter == "X":
                    mask |= 1 << shift
                else:
                    raise ModeError("不认识的权限字符：%r" % letter)
    if operator == "+":
        return current | mask
    if operator == "-":
        return current & ~mask
    # 缺陷：'=' 只做加法，没有先清掉这一组的三位
    return current | mask
