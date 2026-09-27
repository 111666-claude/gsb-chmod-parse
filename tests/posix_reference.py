"""POSIX chmod 语义的参考实现，用于和 chmodkit.mode 对照。只用标准库。"""

SHIFTS = {"u": 6, "g": 3, "o": 0}


class ReferenceError(Exception):
    """参考实现里的表达式错误。"""


def parse_octal(text):
    if not text or len(text) > 4:
        raise ReferenceError("bad octal: %r" % text)
    value = 0
    for char in text:
        if char < "0" or char > "7":
            raise ReferenceError("bad octal digit: %r" % char)
        value = value * 8 + (ord(char) - ord("0"))
    return value


def format_mode(mode):
    out = []
    for shift, special in ((6, 0o4000), (3, 0o2000), (0, 0o1000)):
        chunk = (mode >> shift) & 7
        out.append("r" if chunk & 4 else "-")
        out.append("w" if chunk & 2 else "-")
        if special and mode & special:
            if special == 0o1000:
                out.append("t" if chunk & 1 else "T")
            else:
                out.append("s" if chunk & 1 else "S")
        else:
            out.append("x" if chunk & 1 else "-")
    return "".join(out)


def apply_symbolic(current, spec):
    if spec == "":
        raise ReferenceError("empty spec")
    mode = current
    pos = 0
    while pos < len(spec):
        end = spec.find(",", pos)
        if end == -1:
            end = len(spec)
        mode = _clause(mode, spec[pos:end])
        pos = end + 1
    if spec.endswith(","):
        raise ReferenceError("empty trailing clause")
    return mode


def _clause(mode, clause):
    if clause == "":
        raise ReferenceError("empty clause")
    index = 0
    who = set()
    while index < len(clause) and clause[index] in "ugoa":
        who.add(clause[index])
        index += 1
    if index == len(clause):
        raise ReferenceError("missing operator")
    if clause[index] not in "=+-":
        raise ReferenceError("bad who/operator: %r" % clause[index])
    if not who or "a" in who:
        who = {"u", "g", "o"}
    while index < len(clause):
        operator = clause[index]
        index += 1
        perms = 0
        got = False
        while index < len(clause) and clause[index] not in "=+-":
            char = clause[index]
            if char == "r":
                perms |= 4
            elif char == "w":
                perms |= 2
            elif char == "x":
                perms |= 1
            elif char == "X":
                if mode & 0o111:
                    perms |= 1
            else:
                raise ReferenceError("bad perm: %r" % char)
            got = True
            index += 1
        if not got and operator != "=":
            raise ReferenceError("missing perms")
        for group in who:
            shift = SHIFTS[group]
            bits = perms << shift
            if operator == "=":
                mode = (mode & ~(7 << shift)) | bits
            elif operator == "+":
                mode |= bits
            else:
                mode &= ~bits
    return mode
