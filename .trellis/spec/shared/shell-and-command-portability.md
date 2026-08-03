# Shell 与命令可移植性

## 明确运行边界

- 根据当前真实 shell 编写命令：Mac/Linux 通常使用 zsh/bash，Windows 本机通常使用 PowerShell。
- 跨 shell 时显式标出边界，例如 `pwsh -File`、`cmd /c`、`wsl.exe` 或远端 stdin；不把多种语法混成一条命令。
- 路径、用户名、安装目录和工具前缀通过仓库根、配置或发现命令解析，不写死机器专属值。
- 不确定工具或语法时先运行短时、只读的发现命令，再执行有副作用的命令。

## PowerShell

- 含空格、中文或特殊字符的路径必须引用；字面量优先单引号，需要插值时使用双引号。
- 路径操作优先 `Join-Path`、`Resolve-Path`、`Test-Path`，文件参数优先 `-LiteralPath`。
- 外部程序参数较多时先构造参数数组，再使用调用运算符 `&`。
- 复杂引号、重定向、`< > & | $ $(...)` 或多行脚本优先使用临时脚本或 stdin，不塞进 `.cmd` 包装的一行命令。
- 不把 `export`、`VAR=value command`、`grep/sed/awk` 或 `cmd && next` 当作 PowerShell 默认语法。

## zsh/bash 与远端命令

- 引用可能含空格或通配符的路径；不要让反引号、`$()` 或未审计变量意外执行。
- 复杂远端命令通过 stdin 或专用脚本传输，避免本地和远端两层 shell 重复解释。
- 自动化连接使用非交互模式、短连接超时和有限重试；诊断卡住位置后再判断服务状态。

## Python 与跨平台入口

项目应提供一个经过验证的 Python 入口名或包装器。Trellis 受管理文本可以统一为项目 profile 规定的命令，但不得因此替换业务源码、shebang 或用户级解释器配置。Mac/Windows 均只声明实际运行过的入口。
