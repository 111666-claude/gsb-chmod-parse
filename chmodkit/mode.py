"""权限：八进制、rwx 字符串与符号表达式。只用标准库。"""

WHO_SHIFTS = {"u": 6, "g": 3, "o": 0}
ALL_GROUPS = ("u", "g", "o")
OPERATORS = "=+-"
PERM_BITS = {"r": 4, "w": 2, "x": 1}

MAX_OCTAL_DIGITS = 4


class ModeError(Exception):
    """权限表达式有问题。position 是 1 起始的字符位置，可以为 None。"""

    def __init__(self, message, position=None):
        self.message = message
        self.position = position
        if position is None:
            super().__init__(message)
        else:
            super().__init__("%s（位置 %d）" % (message, position))


def format_mode(mode):
    """把权限整数写成 rwx 形式，setuid/setgid/sticky 用 s/S/t/T 显示。"""
    bits = ""
    for shift, special, lower, upper in (
        (6, 0o4000, "s", "S"),
        (3, 0o2000, "s", "S"),
        (0, 0o1000, "t", "T"),
    ):
        chunk = (mode >> shift) & 0x7
        bits += "r" if chunk & 4 else "-"
        bits += "w" if chunk & 2 else "-"
        if mode & special:
            bits += lower if chunk & 1 else upper
        else:
            bits += "x" if chunk & 1 else "-"
    return bits


def parse_octal(text):
    """解析八进制权限：逐位校验 0-7，最多 4 位（含特殊位）。"""
    if not text:
        raise ModeError("空的八进制权限", position=1)
    if len(text) > MAX_OCTAL_DIGITS:
        raise ModeError(
            "八进制权限最多 %d 位，现在是 %d 位" % (MAX_OCTAL_DIGITS, len(text)),
            position=MAX_OCTAL_DIGITS + 1,
        )
    for index, char in enumerate(text, start=1):
        if char not in "01234567":
            raise ModeError("第 %d 位不是八进制数字：%r" % (index, char), position=index)
    return int(text, 8)


def apply_symbolic(current, spec):
    """把符号表达式作用到当前权限上。

    逗号分隔的子句按顺序依次作用；'=' 先清掉这一组的 rwx 三位再置位，
    '+'/'-' 保持加/减语义。不用正则，逐字符扫描，线性时间。
    """
    if not spec:
        raise ModeError("空表达式", position=1)
    mode = current
    start = 0
    for clause in spec.split(","):
        if not clause:
            raise ModeError("空子句", position=start + 1)
        mode = _apply_clause(mode, clause, start)
        start += len(clause) + 1
    return mode


def _apply_clause(mode, clause, base):
    index = 0
    groups = set()
    while index < len(clause) and clause[index] in "ugoa":
        groups.add(clause[index])
        index += 1
    if index >= len(clause):
        raise ModeError("缺少操作符：%r" % clause, position=base + index + 1)
    if clause[index] not in OPERATORS:
        if groups:
            raise ModeError("未知操作符：%r" % clause[index], position=base + index + 1)
        raise ModeError("未知 who：%r" % clause[index], position=base + index + 1)
    if not groups or "a" in groups:
        targets = ALL_GROUPS
    else:
        targets = [group for group in ALL_GROUPS if group in groups]
    while index < len(clause):
        operator = clause[index]
        index += 1
        perms = 0
        got_letter = False
        while index < len(clause) and clause[index] not in OPERATORS:
            letter = clause[index]
            if letter in PERM_BITS:
                perms |= PERM_BITS[letter]
            elif letter == "X":
                if mode & 0o111:
                    perms |= 1
            else:
                raise ModeError("未知权限字母：%r" % letter, position=base + index + 1)
            got_letter = True
            index += 1
        if not got_letter and operator != "=":
            raise ModeError("缺少权限字母：%r" % clause, position=base + index + 1)
        for group in targets:
            shift = WHO_SHIFTS[group]
            bits = perms << shift
            if operator == "+":
                mode |= bits
            elif operator == "-":
                mode &= ~bits
            else:
                mode = (mode & ~(0o7 << shift)) | bits
    return mode
