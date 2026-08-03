# Shell 与命令可移植性

## 明确运行边界

- 根据当前真实 shell 编写命令：Mac/Linux 通常使用 zsh/bash，Windows 本机通常使用 PowerShell。
- 跨 shell 时显式标出边界，例如 `pwsh -File`、`cmd /c`、`wsl.exe` 或远端 stdin；不把多种语法混成一条命令。
- 路径、用户名、安装目录和工具前缀通过仓库根、配置或发现命令解析，不写死机器专属值。
- 不确定工具或语法时先运行短时、只读的发现命令，再执行有副作用的命令。

## PowerShell 7

- Windows 本机终端、脚本、自动化、远程包装器和 OpenSSH `DefaultShell` 默认使用 PowerShell 7 的 `pwsh` 入口；环境未知时先用发现命令确认 `pwsh` 和实际版本。
- 遇到兼容问题时优先修正脚本、参数、模块或调用方式，使其在当前 PowerShell 7 上工作，不以改用 `powershell.exe` 掩盖问题。
- 新增或重写的 Windows 入口不得默认使用 `powershell.exe` 或 `cmd.exe`。只有外部依赖明确要求 Windows PowerShell 5.1 或 CMD 时才能保留例外；项目必须写明阻塞原因、适用范围、当前桥接入口、验证方式和移除条件，形成可跟踪的 PS7 替换计划，不能把例外扩散为默认值。

- 含空格、中文或特殊字符的路径必须引用；字面量优先单引号，需要插值时使用双引号。
- 路径操作优先 `Join-Path`、`Resolve-Path`、`Test-Path`，文件参数优先 `-LiteralPath`。
- 外部程序参数较多时先构造参数数组，再使用调用运算符 `&`。
- 本机执行涉及复杂引号、重定向、`< > & | $ $(...)` 或多行脚本时，优先使用临时 `.ps1` 或受控 stdin；远程执行遵循下一节的显式 `pwsh` 合同，不塞进 `.cmd` 包装的一行命令。
- 不把 `export`、`VAR=value command`、`grep/sed/awk` 或 `cmd && next` 当作 PowerShell 默认语法。

## 远程命令与跨 shell

- 引用可能含空格或通配符的路径；不要让反引号、`$()` 或未审计变量意外执行。
- Windows OpenSSH 的目标 `DefaultShell` 是 PowerShell 7。连接前先用独立的最小只读命令确认实际远程 shell 和 `pwsh` 可用性；发现仍是 `cmd.exe`、Windows PowerShell 5.1 或其它遗留入口时，显式调用 `pwsh` 完成当前工作，并按上一节记录替换计划，不能把遗留默认值当成正常完成态。
- 复杂远程 PowerShell 显式调用 `pwsh -NoLogo -NoProfile -NonInteractive`，使用 UTF-16LE Base64 的 `-EncodedCommand`，或传输 `.ps1` 后用 `pwsh -File` 执行；不经过未知默认 shell 使用 `-Command -`、`-File -` 或复杂内联命令。
- `cmd.exe` 或 `powershell.exe` 只可用于发现环境或引导进入 `pwsh` 的最小桥接，不承载复合业务逻辑。简单状态探针分别执行，不使用 `&`、括号、管道或重定向拼成复杂链。
- 预期产生输出的远程命令必须同时满足退出状态成功，并且预期字段、可解析结果或明确哨兵实际出现；退出码为零但 stdout 为空时按失败处理，不能报告完成。
- 自动化连接使用非交互模式、短连接超时和有限重试；诊断卡住位置后再判断服务状态。

## Python 与跨平台入口

项目应提供一个经过验证的 Python 入口名或包装器。Trellis 受管理文本可以统一为项目 profile 规定的命令，但不得因此替换业务源码、shebang 或用户级解释器配置。Mac/Windows 均只声明实际运行过的入口。
