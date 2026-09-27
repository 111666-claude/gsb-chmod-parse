# chmod-parse

权限字符串解析与规范化（八进制、rwx、符号表达式），只用 Python 标准库。

```
python3 -m chmodkit.cli --apply 777 "u=r"
python3 -m chmodkit.cli --apply 777 "u+x,g-w"
python3 -m chmodkit.cli --format 4755
python3 -m unittest discover -s tests -v
```

## 口径（README 为准）

- `=` 是**赋值**：先把这一组（u/g/o）的 rwx 三位清零，再置上等号右边的位。
  `--apply 777 "u=r"` 按口径是 `477`（`r--rwxrwx`），现在给 `777`。
- 符号表达式可以**用逗号写多个子句**，按顺序依次作用；`--apply 777 "u+x,g-w"` 按口径是 `757`
  （g 的 w 被去掉），现在只处理了第一个子句、给 `777`。
- 八进制要**逐位校验**：每一位必须是 0–7，`888` 要报「第 1 位不是八进制数字」并给出位置，
  长度最多 4 位（含 setuid/setgid/sticky）；现在直接把 `888` 丢给 `int()` 抛原始异常。
- `format` 要显示特殊位：`4755` 是 `rwsr-xr-x`、`2755` 是 `rwxr-sr-x`、`1755` 是 `rwxr-xr-t`，
  没有 x 时用大写 `S`/`T`；现在这三者都显示成普通 rwx。
- 不变量：`parse_octal(format_mode(mode))` 在去掉特殊位后一致；`apply_symbolic(mode, "")` 报错；
  同一表达式重复作用结果相同；`who=umask` 之外的写法都要报错。
- 规模：10 万次表达式应用要线性完成，内存 O(1)。

## 现在的行为

- `=` 先清掉这一组的 rwx 三位再置位：`u=r` 对 `777` 给 `477`；`+`/`-` 保持加/减语义。
- 逗号分隔的子句按顺序全部作用：`u+x,g-w` 对 `777` 给 `757`；空子句报错并给出位置。
- `parse_octal` 逐位校验 0–7、最多 4 位：`888` 报「第 1 位不是八进制数字」，空串、负数、超长都报错并给位置。
- `format_mode` 显示特殊位：`4755` → `rwsr-xr-x`、`2755` → `rwxr-sr-x`、`1755` → `rwxr-xr-t`，没有 x 时用大写 `S`/`T`。
- 未知 who、未知操作符、未知权限字母都报 `ModeError` 并指出位置；`tests/posix_reference.py`
  是按 POSIX chmod 语义写的参考实现，`tests/test_against_reference.py` 用样例和 1 万组随机用例对照结果与错误类型。

## 计划新增的能力

```
--octal 权限     解析并打印规范形式
--apply 当前 表达式
```

## 输出

```
755 rwxr-xr-x
```

## 目录

```
chmodkit/mode.py   八进制、rwx、符号表达式
chmodkit/cli.py    命令行入口
tests/             unittest 用例
```
