# Shell 与命令可移植性

## 明确运行边界

- 根据当前真实 shell 编写命令：Mac/Linux 通常使用 zsh/bash，Windows 本机通常使用 PowerShell。
- 跨 shell 时显式标出边界，例如 `pwsh -File`、`cmd /c`、`wsl.exe` 或远端 stdin；不把多种语法混成一条命令。
- 路径、用户名、安装目录和工具前缀通过仓库根、配置或发现命令解析，不写死机器专属值。
- 不确定工具或语法时先运行短时、只读的发现命令，再执行有副作用的命令。

## PowerShell 7

- Windows 本机终端、脚本、自动化和远程包装器默认使用 PowerShell 7 的 `pwsh` 入口；环境未知时先用发现命令确认 `pwsh` 和实际版本。
- 遇到兼容问题时优先修正脚本、参数、模块或调用方式，使其在当前 PowerShell 7 上工作，不以改用 `powershell.exe` 掩盖问题。
- 新增或重写的 Windows 入口不得默认使用 `powershell.exe` 或 `cmd.exe`。只有外部依赖明确要求 Windows PowerShell 5.1 或 CMD 时才能保留例外；项目必须写明阻塞原因、适用范围、当前桥接入口、验证方式和移除条件，形成可跟踪的 PS7 替换计划，不能把例外扩散为默认值。

- 含空格、中文或特殊字符的路径必须引用；字面量优先单引号，需要插值时使用双引号。
- 路径操作优先 `Join-Path`、`Resolve-Path`、`Test-Path`，文件参数优先 `-LiteralPath`。
- 外部程序参数较多时先构造参数数组，再使用调用运算符 `&`。
- 本机执行涉及复杂引号、重定向、`< > & | $ $(...)` 或多行脚本时，优先使用临时 `.ps1` 或受控 stdin；远程执行遵循下一节的显式 `pwsh` 合同，不塞进 `.cmd` 包装的一行命令。
- 不把 `export`、`VAR=value command`、`grep/sed/awk` 或 `cmd && next` 当作 PowerShell 默认语法。

## 远程命令与跨 shell

- 引用可能含空格或通配符的路径；不要让反引号、`$()` 或未审计变量意外执行。
- 复杂远程 PowerShell 显式调用 `pwsh -NoLogo -NoProfile -NonInteractive`，使用 UTF-16LE Base64 的 `-EncodedCommand`，或传输 `.ps1` 后用 `pwsh -File` 执行；不经过未知默认 shell 使用 `-Command -`、`-File -` 或复杂内联命令。
- `cmd.exe` 或 `powershell.exe` 只可用于发现环境或引导进入 `pwsh` 的最小桥接，不承载复合业务逻辑。简单状态探针分别执行，不使用 `&`、括号、管道或重定向拼成复杂链。
- 预期产生输出的远程命令必须同时满足退出状态成功，并且预期字段、可解析结果或明确哨兵实际出现；退出码为零但 stdout 为空时按失败处理，不能报告完成。
- 自动化连接使用非交互模式、短连接超时和有限重试；诊断卡住位置后再判断服务状态。

## Mac、Windows 与 WSL 的跨 Shell SSH

- 当任务仍需通过 Windows OpenSSH 管理 Windows 时，保留既有 Windows 管理入口，并保持 OpenSSH `DefaultShell` 为 PowerShell 7；不得为兼容要求 POSIX shell 的客户端而全局改成 Bash。连接前用独立的最小只读命令确认实际远端 shell 和 `pwsh` 可用性；发现遗留入口时显式调用 `pwsh` 并按上一节记录替换计划，不得把遗留默认值当成正常完成态。
- 当客户端明确要求 `sh`、Linux 登录环境或 Linux 原生工具时，使用独立、最小权限的 Linux/WSL SSH 入口；端到端验证后，可以用 `ProxyCommand` 复用既有 Windows SSH 入口，但它只充当透明字节流桥接，不能改变任一端的 shell 合同。
- Linux/WSL 入口使用普通非特权用户和公钥认证；不得为连接方便开放 root 登录、密码认证或新增免密 sudo。
- 动态 WSL 地址、额外 LAN 监听端口、`portproxy`、防火墙放行和地址刷新任务都不是默认方案；只有项目证据证明必要且能管理其生命周期时才可采用，TCP 端口可连不等于 SSH 端到端成功或产品已经启动。
- 验收按实际路径分层验证外层 Windows SSH（若使用）、内层 Linux SSH、实际 shell 身份、原生工具解析路径以及最终客户端或 App 日志；每层都要核对退出状态和预期输出，不能用前一层成功推断后一层成功。
- 具体别名、用户、发行版、端口、版本、密钥路径和故障证据归具体项目规范或该仓库的 ignored 本地记录管理；平台实测与完成声明遵循[跨平台验证](cross-platform-validation.md)和[证据与验证](evidence-and-verification.md)，凭据与机器事实遵循[敏感信息](sensitive-data.md)。

## Python 与跨平台入口

项目应提供一个经过验证的 Python 入口名或包装器。Trellis 受管理文本可以统一为项目 profile 规定的命令，但不得因此替换业务源码、shebang 或用户级解释器配置。Mac/Windows 均只声明实际运行过的入口。
