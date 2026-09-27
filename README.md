# chmod-parse

权限字符串解析与规范化（八进制、rwx、符号表达式），只用 Python 标准库。

```
python3 -m chmodkit.cli --apply 777 "u=r"
python3 -m chmodkit.cli --apply 777 "u+x,g-w"
python3 -m chmodkit.cli --format 4755
python3 -m unittest discover -s tests -v
```

## 口径（已按本文档实现）

- `=` 是**赋值**：先把目标组（u/g/o）的 rwx 三位清零，再置上等号右边的位。
  `--apply 777 "u=r"` 给出 `477`（`r--rwxrwx`）；`+`/`-` 保持加/减语义。
- 符号表达式用**逗号写多个子句**，按顺序依次作用；`--apply 777 "u+x,g-w"`
  给出 `757`。空子句报错并给出位置。
- 八进制**逐位校验**：每一位必须是 0–7，否则报「第 N 位不是八进制数字」
  （N 从 1 起）；空串、负数、超过 4 位同样报错并给出位置。
- `format` 显示特殊位：`4755` 是 `rwsr-xr-x`、`2755` 是 `rwxr-sr-x`、
  `1755` 是 `rwxr-xr-t`；没有 x 时用大写 `S`/`T`（如 `4644` → `rwSr--r--`）。
- who 为 `u`/`g`/`o`/`a`，可组合、可缺省（缺省等价 `a`）；权限字母为
  `r`/`w`/`x`/`X`（`X`：当前已有任一执行位时才加 x）。未知 who、未知操作符、
  未知权限字母都报错并指出位置。
- 不变量：同一表达式重复作用结果相同；`format_mode` 的 rwx 串解析回来与
  `mode & 0o777` 一致（特殊位体现为 s/S、t/T，不改变 r/w/x 三位）。
- 规模：单遍线性扫描、无正则回溯，10 万个子句的表达式线性完成、内存 O(1)。
- 差分测试：`tests/chmod_reference.py` 是按 POSIX chmod 语义逐子句处理的
  独立参考实现，`tests/test_differential.py` 用 1 万组随机「当前权限 + 表达式」
  与 1 万组随机八进制串比对结果值与错误类型/位置，并穷举 0–0o7777 的格式化。

## 支持的命令

```
--octal 权限       解析并打印规范形式
--format 权限      把八进制权限格式化成 rwx
--apply 当前 表达式 把符号表达式作用到当前权限上
```

## 输出

```
755 rwxr-xr-x
```

## 目录

```
chmodkit/mode.py   八进制、rwx、符号表达式
chmodkit/cli.py    命令行入口
tests/             unittest 用例（含参考实现、差分与性能测试）
```
