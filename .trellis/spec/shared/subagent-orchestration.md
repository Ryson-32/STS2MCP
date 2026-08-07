# 子代理与外部 AI Worker 编排

## 角色、上下文与执行器分层

- `research`、`implement`、`check` 是稳定职责，不等于固定模型、provider 或进程类型。主会话先按任务风险和项目规则确定角色，再选择最低足够能力的执行器。
- Trellis 平台子代理优先通过原生 `SubagentStart` 获得任务上下文；Hook 不可用时，角色必须自行读取活动任务和同一份路由，不得从记忆猜测规范集合。
- Codex/Trellis 启动的独立 Claude Code CLI/SDK worker 是外部进程，不是 Claude 主会话内部 subagent。不得依赖 Agent Teams、环境中的隐式子代理模型变量或界面工作流提示来推断其模型、effort、并发或上下文。
- 浏览器、桌面应用或其它项目私有自动化不是 Trellis 子代理。它们的槽位、附件、业务门禁和状态账本留在拥有它们的项目规则中。

## 任务路由合同

普通小任务、自包含任务和只需要任务文档即可完成的工作不创建
`routing.json`。复杂、多代理、高风险，或确实需要把共同规范与角色补充精确交接的
任务，才在任务目录保存最小 `routing.json`：

```json
{
  "schema_version": 2,
  "state": "resolved",
  "common_specs": [
    { "path": ".trellis/spec/example/rule.md", "reason": "本任务需要的规则" }
  ],
  "role_supplements": {
    "check": [
      { "path": ".trellis/spec/example/verification.md", "reason": "check 专用验收规则" }
    ]
  },
  "source_digest": "sha256:<digest>"
}
```

- 文件缺失是正常状态，不报错、不阻止派发；角色继续读取任务文档，并按当前
  workflow 使用已存在且经校验的 `implement.jsonl` / `check.jsonl` 或角色自己的
  开工规范。文件一旦存在，就是本任务显式规范交接的唯一机器可读事实源。
- `common_specs` 是所有角色一致读取的共同 baseline；`role_supplements` 只允许
  `research`、`implement`、`check` 三个键。某角色的有效集合是
  `common_specs + role_supplements[当前角色]`，保持声明顺序；重复项失败关闭。角色
  之间不要求 supplement 相同，也不得把别的角色 supplement 注入当前角色。
- 所有集合只接受仓库相对 Markdown 文件和单行理由。同一集合不得重复；共同
  baseline 与任一角色 supplement 也不得重复同一路径。不同角色的 supplement
  可以引用同一路径，因为它们不会同时进入一个角色的有效集合。
- `source_digest` 使用长度分帧覆盖共同/角色作用域、规范路径、理由和按 LF
  规范化后的所有 Markdown 原始字节，避免内容与下一条记录发生边界碰撞、角色归属
  变化漏检，也避免 Windows/Mac checkout 换行差异制造假漂移。摘要覆盖所有角色，
  不只覆盖当前派发角色；理由与 Markdown 不接受 NUL 字节。
- schema v2 的 `resolved` 必须至少有一条共同规范。`blocked`、未知字段/角色、路径
  越界、文件缺失、有效集合重复或 digest 漂移都阻止当前 worker；不得静默回退到
  JSONL 制造一个较小集合。现有 schema v1 `required_specs` 文档在完整校验通过时
  继续按“所有角色共同集合”读取，新任务和新示例使用 v2。
- Hook 只注入经过摘要校验的 compact 路径/理由有效集合，agent 再打开正文；Hook
  不可用时，角色直接读取同一 `routing.json` 并应用相同合并规则。最终报告列出
  实际读取路径、当前角色以及路由是否验证通过。
- 不得同时维护 routing 与一套相互冲突的 JSONL 规范事实源。routing 缺失时，旧
  JSONL 兼容路径仍可用；routing 存在且有效时优先 routing，存在但无效时失败关闭。

## 能力事实与选择

- 模型、provider、effort、CLI flag 和实机版本由拥有这些事实的能力仓库导出非敏感、版本化记录；消费仓库与 Fleet 不读取或复制用户级登录、token、CC Switch 或 provider 配置。
- 能力清单只暴露 provider 实际报告的模型和支持档位。每个 model/effort profile 分开记录 `requested`、`unknown`、`verified` 或 `unsupported`；CLI 接受参数最多证明 `cli-accepted/unknown`，第三方网关需由原始 provider 日志把状态提升为 `verified`。一个 provider 只有一个模型时只记录该模型，不把熟悉的模型名伪装成 alias。
- 先应用项目启停、领域禁用、安全主目标和设备可用性，再在剩余候选中选择最低足够能力。安全主目标只能选择能力记录明确标记可承担该目标的模型。
- 重试次数必须有界。重选模型、降低 effort、切换 provider 或从并行降为串行时，保留原请求、实际结果和原因；不能把降级后的身份写成最初请求已经满足。

## 跨项目模型偏好

- 这是一份经过能力门禁后的候选偏好，不是固定 provider 矩阵。实际 capability
  export、项目禁用、安全主目标和设备可用性始终优先。
- 日常研究、实现和检查优先考虑 Sol `medium` / `high`；困难科学推理、跨层问题、
  安全或高影响判断优先考虑能力已验证的 Sol `xhigh` / `max`。
- 能力已验证且当前配额充足的 Opus 应在候选池中获得实质而非象征性的权重：
  适合边界清晰的实现、前端与文字工作，也适合作为独立 research/check。独立检查
  优先选择与实现不同的模型家族；反向组合也成立，不能把 Opus 固定成偶发兜底。
- Fable 只有在目标 model/effort profile 已验证且项目允许时才进入候选；它不得
  承担安全主目标。任何家族发生降级、重映射或不可观测时，仍按 requested/observed
  合同记录，而不是用偏好表替代事实。

## 独立 Claude worker 进程合同

- 默认使用一次性 print mode：参数数组包含 `-p --output-format json --no-session-persistence`，prompt 通过 stdin 或受保护文件传入，不拼接 shell 命令。需要连续上下文时，必须显式选择 persistent mode 和 session identity。
- adapter 必须实现进程启动、JSON 解析、timeout、cancel、退出码/stderr 分类和输出大小边界。真实调用可能产生费用或外部动作时，必须由当前授权单独覆盖；测试优先使用 fake executable 和合成输入。
- `--settings` 只指向本次进程的显式设置；进程级 env 只注入当前 worker。声明 `per-process` 隔离时必须存在真实 provider 设置或 provider 环境证据，普通 `LANG`、测试变量等任意 env 不足以绕过 active-global 互斥。不得读取、重写或切换用户级 Claude、Codex、CC Switch、provider 或认证配置。
- 并行 worker 不能反复切换同一个全局 active provider。能够用 per-process settings/env 证明进程隔离时才可跨 provider 并行；否则 `provider-serial` 表示所有依赖同一个 active-global 配置面板的 worker 共用一把互斥锁，不只是同一 provider ID 内串行。不同 provider 只要都依赖 CC Switch 等同一个全局 active 状态，也必须彼此串行。
- 每台设备先探测实际 executable、CLI 版本和 `--model` / `--effort` / `--agents` 支持。远端非登录 shell 的 `PATH` 可能不同，必须使用已验证的发现入口，不能因为本地 shell 可用就推断远端可用。
- 检测到 `CLAUDE_CODE_EFFORT_LEVEL` 等会覆盖命令行 effort 的环境值时失败关闭或明确警告；不得为通过检查而修改用户环境。

## Requested 与 observed 身份

每次独立 worker 运行至少记录：

| 字段 | 合同 |
|---|---|
| role / worker kind | Trellis 职责与实际外部执行器类型 |
| provider/model/effort requested | 调度器本次明确请求，不从全局配置倒推 |
| model state / observed / source | `observed`、`downgraded` 或 `unknown`；JSON result 的 `modelUsage` 或 provider 原始日志才是实际模型证据 |
| effort state / observed / source | `observed`、`downgraded` 或 `unknown`；没有等价可验证字段时保持 `unknown` |
| fallback reason | 模型或 effort 降级、重选、串行化的原因 |
| CLI / process | CLI 版本、executable probe、settings scope、persistence mode、timeout 和 cancel 结果 |

`--output-format json` / `stream-json` 可能抑制 stderr 中的模型重映射提示，所以不能只信 argv、stdout 标签或“命令成功”。effort 不受支持时可能降到不高于请求的最高档；没有 provider/gateway 原始证据时不得把请求值写成 observed。

## 失败关闭

以下任一情况停止当前 worker 或仓库，但不污染其它独立对象：

- 路由无效、规范缺失或不同角色得到不同规范集合。
- 能力导出版本/来源不明、provider 模型被虚构映射，或安全目标没有合格候选。
- requested 与 observed 混写、effort 覆盖未处理、降级没有原因或模型证据来源不可解释。
- executable/flag/version 探测失败、JSON 无法解析、timeout/cancel 无法执行或 persistent session 身份不明确。
- per-process provider 隔离无法证明且调度器仍让任意两个依赖同一个 active-global 状态的 worker 并行，包括 provider ID 不同的 worker。
