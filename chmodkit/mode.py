"""权限：八进制、rwx 字符串与符号表达式。只用标准库。

语法（兼容 POSIX chmod 符号模式的小子集）：

    表达式    := 子句 ("," 子句)*
    子句      := [who]+ 操作符 权限字母*
    who       := "u" | "g" | "o" | "a"（可组合，缺省等价于 a）
    操作符    := "=" | "+" | "-"
    权限字母  := "r" | "w" | "x" | "X"

解析采用单次线性扫描：每个字符处理一次，内存占用为 O(1)，
不使用任何回溯式正则。
"""

# 特殊位：setuid=4、setgid=2、sticky=1
SUID, SGID, STICKY = 0o4000, 0o2000, 0o1000

# who 字母 -> rwx 三位的位移
GROUP_SHIFT = {"u": 6, "g": 3, "o": 0}

# 权限字母 -> 在一组内的位值
PERM_BIT = {"r": 4, "w": 2, "x": 1}

# 错误类型（测试与参考实现按类型比对，而不是按文案）
ERR_EMPTY_EXPR = "empty_expr"
ERR_EMPTY_CLAUSE = "empty_clause"
ERR_BAD_OCTAL_DIGIT = "bad_octal_digit"
ERR_OCTAL_TOO_LONG = "octal_too_long"
ERR_UNKNOWN_WHO = "unknown_who"
ERR_UNKNOWN_OP = "unknown_op"
ERR_UNKNOWN_LETTER = "unknown_letter"


class ModeError(Exception):
    """权限表达式有问题。position 为 0 基字符位置（-1 表示不定位到字符）。"""

    def __init__(self, message, kind="mode_error", position=-1):
        super().__init__(message)
        self.message = message
        self.kind = kind
        self.position = position


def parse_octal(text):
    """解析八进制权限，最多 4 位，逐位校验 0-7。"""
    if not isinstance(text, str) or text == "":
        raise ModeError("空八进制字符串", ERR_EMPTY_EXPR, -1)
    if text[0] == "-":
        raise ModeError("八进制权限不能为负数：第 1 位 %r 不是八进制数字" % text[0],
                        ERR_BAD_OCTAL_DIGIT, 0)
    if len(text) > 4:
        raise ModeError("八进制权限最多 4 位：第 %d 位超长" % 5,
                        ERR_OCTAL_TOO_LONG, 4)
    value = 0
    for index, char in enumerate(text):
        if char < "0" or char > "7":
            raise ModeError("第 %d 位不是八进制数字：%r" % (index + 1, char),
                            ERR_BAD_OCTAL_DIGIT, index)
        value = value * 8 + (ord(char) - ord("0"))
    return value


def _select_shifts(who_part, base):
    """把 who 部分（一个或多个 u/g/o/a）转成组位移集合。base 是子句起始位置。"""
    shifts = []
    for offset, char in enumerate(who_part):
        if char == "a":
            shifts.extend(GROUP_SHIFT.values())
        elif char in GROUP_SHIFT:
            shifts.append(GROUP_SHIFT[char])
        else:
            raise ModeError("第 %d 位是未知的 who：%r（应为 u/g/o/a）"
                            % (base + offset + 1, char),
                            ERR_UNKNOWN_WHO, base + offset)
    return shifts or list(GROUP_SHIFT.values())


def _apply_clause(current, clause, base):
    """处理单个子句（不含逗号）。base 是子句在整个表达式中的起始位置。"""
    if clause == "":
        raise ModeError("第 %d 位是空子句" % (base + 1),
                        ERR_EMPTY_CLAUSE, base)

    # who 部分：开头连续的 u/g/o/a
    end = 0
    while end < len(clause) and clause[end] in "ugoa":
        end += 1
    if end == 0 and len(clause) > 0 and clause[0] not in "=+-":
        raise ModeError("第 %d 位是未知的 who：%r（应为 u/g/o/a）"
                        % (base + 1, clause[0]),
                        ERR_UNKNOWN_WHO, base)
    shifts = _select_shifts(clause[:end], base)

    if end >= len(clause):
        raise ModeError("第 %d 位缺少操作符（应为 =、+、-）" % (base + end + 1),
                        ERR_UNKNOWN_OP, base + end)
    operator = clause[end]
    if operator not in "=+-":
        raise ModeError("第 %d 位是未知操作符：%r（应为 =、+、-）"
                        % (base + end + 1, operator),
                        ERR_UNKNOWN_OP, base + end)
    letters = clause[end + 1:]

    any_execute = bool(current & 0o111)
    add_mask = 0
    for offset, letter in enumerate(letters):
        position = base + end + 1 + offset
        if letter == "X":
            if any_execute:
                for shift in shifts:
                    add_mask |= 1 << shift
            continue
        if letter not in PERM_BIT:
            raise ModeError("第 %d 位是未知权限字母：%r（应为 r/w/x/X）"
                            % (position + 1, letter),
                            ERR_UNKNOWN_LETTER, position)
        bit = PERM_BIT[letter]
        for shift in shifts:
            add_mask |= bit << shift

    if operator == "+":
        return current | add_mask
    if operator == "-":
        return current & ~add_mask
    # "=" 是赋值：先清掉目标组的 rwx 三位，再置位
    group_clear = 0
    for shift in shifts:
        group_clear |= 0o7 << shift
    return (current & ~group_clear) | add_mask


def apply_symbolic(current, spec):
    """把符号表达式作用到当前权限上，按逗号拆成子句顺序执行。"""
    if not isinstance(spec, str) or spec == "":
        raise ModeError("空表达式", ERR_EMPTY_EXPR, -1)

    mode = current
    base = 0
    start = 0
    while True:
        comma = spec.find(",", start)
        if comma == -1:
            return _apply_clause(mode, spec[start:], base)
        mode = _apply_clause(mode, spec[start:comma], base)
        base += comma - start + 1
        start = comma + 1


def format_mode(mode):
    """把权限整数写成 9 个字符的 rwx 形式，含 setuid/setgid/sticky。"""
    chars = []
    groups = (
        (6, mode & SUID, "s"),
        (3, mode & SGID, "s"),
        (0, mode & STICKY, "t"),
    )
    for shift, special_bit, special_char in groups:
        chunk = (mode >> shift) & 0x7
        chars.append("r" if chunk & 4 else "-")
        chars.append("w" if chunk & 2 else "-")
        if special_bit:
            chars.append(special_char if chunk & 1 else special_char.upper())
        else:
            chars.append("x" if chunk & 1 else "-")
    return "".join(chars)
