"""参考实现：按 POSIX chmod 符号模式语义逐子句处理。

刻意采用与 chmodkit.mode 不同的代码组织（整段缓冲 + 状态机），
用于差分测试：结果整数与错误类型/位置必须一致。仅覆盖本项目支持的
r/w/x/X 子集；错误用 RefError 表示，kind 与主实现的 ModeError 对齐。
"""

from chmodkit.mode import (
    ERR_BAD_OCTAL_DIGIT,
    ERR_EMPTY_CLAUSE,
    ERR_EMPTY_EXPR,
    ERR_OCTAL_TOO_LONG,
    ERR_UNKNOWN_LETTER,
    ERR_UNKNOWN_OP,
    ERR_UNKNOWN_WHO,
)


class RefError(Exception):
    def __init__(self, kind, position, message=""):
        super().__init__(message)
        self.kind = kind
        self.position = position


def ref_parse_octal(text):
    if not isinstance(text, str) or len(text) == 0:
        raise RefError(ERR_EMPTY_EXPR, -1)
    if text.startswith("-"):
        raise RefError(ERR_BAD_OCTAL_DIGIT, 0)
    if len(text) > 4:
        raise RefError(ERR_OCTAL_TOO_LONG, 4)
    total = 0
    for pos, char in enumerate(text):
        code = ord(char)
        if code < 48 or code > 55:  # '0'..'7'
            raise RefError(ERR_BAD_OCTAL_DIGIT, pos)
        total = (total << 3) | (code - 48)
    return total


_WHO_SHIFT = {"u": 0o700, "g": 0o070, "o": 0o007, "a": 0o777}
_LETTER_MASK = {"r": 0o444, "w": 0o222, "x": 0o111}


def _resolve_who(segment, base):
    """返回（组掩码, 错误）。重复/组合的 who 按位并集。"""
    mask = 0
    for offset, char in enumerate(segment):
        if char not in _WHO_SHIFT:
            raise RefError(ERR_UNKNOWN_WHO, base + offset)
        mask |= _WHO_SHIFT[char]
    return mask or 0o777


def ref_apply_symbolic(current, spec):
    if not isinstance(spec, str) or spec == "":
        raise RefError(ERR_EMPTY_EXPR, -1)

    mode = current
    cursor = 0
    total = len(spec)
    while cursor <= total:
        clause_end = cursor
        while clause_end < total and spec[clause_end] != ",":
            clause_end += 1
        clause = spec[cursor:clause_end]
        if clause == "":
            raise RefError(ERR_EMPTY_CLAUSE, cursor)

        i = 0
        while i < len(clause) and clause[i] in "ugoa":
            i += 1
        if i == 0 and clause[0] not in "=+-":
            raise RefError(ERR_UNKNOWN_WHO, cursor)
        who_mask = _resolve_who(clause[:i], cursor)

        if i == len(clause) or clause[i] not in "=+-":
            raise RefError(ERR_UNKNOWN_OP, cursor + i)
        action = clause[i]
        i += 1

        pending = 0
        while i < len(clause):
            char = clause[i]
            if char == "X":
                if mode & 0o111:
                    pending |= 0o111
            elif char in _LETTER_MASK:
                pending |= _LETTER_MASK[char]
            else:
                raise RefError(ERR_UNKNOWN_LETTER, cursor + i)
            i += 1
        change = pending & who_mask
        if action == "+":
            mode |= change
        elif action == "-":
            mode &= ~change & 0o7777
        else:  # "="：目标组的 rwx 三位先清零
            mode &= (~who_mask & 0o7777)
            mode |= change
        if clause_end == total:
            return mode
        cursor = clause_end + 1


def ref_format_mode(mode):
    """参考格式化：按 POSIX ls -l 的特殊位规则。"""
    out = []
    for index, (shift, special) in enumerate(
        ((6, 0o4000), (3, 0o2000), (0, 0o1000))
    ):
        triple = (mode >> shift) & 0o7
        out.append("r" if triple & 4 else "-")
        out.append("w" if triple & 2 else "-")
        if mode & special:
            out.append(("s", "s", "t")[index] if triple & 1 else ("S", "S", "T")[index])
        else:
            out.append("x" if triple & 1 else "-")
    return "".join(out)
