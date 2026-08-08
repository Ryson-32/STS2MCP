# 子代理与外部 AI Worker 编排

## 角色、上下文与执行器分层

- `research`、`implement`、`check` 是稳定职责，不等于固定模型、provider 或进程类型。主会话先判断任务形态和职责，再从本文件的规范性偏好表取得通常的第一候选；不得因此在三个角色定义中静态锁死同一个模型或 effort。
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
- 调度时先按下方偏好表根据任务形态选择。项目关闭、领域或安全规则禁用、设备或 provider 当前不可用时，可以改选其它候选，但必须按任务重新判断并说明原因；安全主目标只能选择能力记录明确标记可承担该目标的模型。
- `requested/observed` 用于如实记录调用结果，不是选用某档模型前必须提交证明的门槛。重试次数必须有界；重选模型、降低 effort、切换 provider 或从并行降为串行时，保留原请求、实际结果和原因，不能把降级后的身份写成最初请求已经满足。

## 跨项目模型偏好

下表是跨项目的规范性默认路由。profile 标识表示“模型 + 请求 effort”的选择意图，
不是 provider 当前一定可用或已经被实际观测到的声明。项目约束和当前可用性可以
影响实际选择；与默认偏好不同时说明原因即可，不为普通调度增加额外证明流程。

| 模型档位 | 偏好任务 |
|---|---|
| `gpt-5.6-sol-medium` | 目标明确、约束完整、非探索性杂活、批量定位和整理 |
| `gpt-5.6-sol-high` | 有一定复杂度，但范围仍比较明确；普通探索、跨文件分析 |
| `gpt-5.6-sol-xhigh` | 默认通用档；归类困难、需求存在歧义或涉及多个系统时 |
| `gpt-5.6-sol-max` | 高复杂度技术任务、关键逻辑和科学推理；Fable 被领域规则禁止时的强力替代 |
| `claude-opus-5-xhigh` | 能力定位在 Sol Medium 与 Sol High 之间且更接近 Sol High；约束明确的编码任务优先，前端实现、重构和普通文案也适合，并支持高并发拆分 |
| `claude-fable-5-xhigh` | 重要 UI/文案优化、复杂问题探索、独立复核和高价值验证 |
| `claude-fable-5-max` | 仅在 Fable xhigh 已实际返回但证据表明不够深入时升级 |

- `gpt-5.6-sol-xhigh` 是无法可靠归入其它类别时的默认通用档；不能为了节省调用而把
  有歧义或跨系统任务静默降到 `medium` / `high`。
- 同一主任务内，GPT 系列子代理同时最多并行 10 个，Claude 系列子代理同时最多并行
  20 个。实际平台可用额度更低时采用较低值；并发上限不是目标数量，只在任务彼此独立
  且并行确有收益时使用。
- `research` 直接按表中的任务形态选择：普通探索和跨文件分析属于 Sol high，归类
  困难、有歧义或跨系统时使用默认 Sol xhigh；复杂探索或高价值验证可选择 Fable xhigh。
- `implement` 对约束完整的编码任务优先选择 `claude-opus-5-xhigh`，前端实现、重构
  和普通文案也适用；其高并发优势适合拆分为多个互不依赖单元的工作。其它实现仍按表
  中的机械性、复杂度、歧义和关键逻辑类别选路，不把 Opus 固定为所有实现任务的默认值。
- `check` 应优先选择与实现者不同的模型家族保持独立性；符合条件的高价值验证可
  选择 `claude-fable-5-xhigh`。领域或项目禁止 Fable 时，关键检查使用
  `gpt-5.6-sol-max` 作为强力替代；安全主目标不得由 Fable 承担。
- Fable 通常先用 `claude-fable-5-xhigh`；只有它已经实际返回、且从结果本身可见深度
  明显不足时，才考虑 `claude-fable-5-max`。这是轻量调度偏好，不要求额外证据文件、
  task ID、ledger 证明或 worker 失败关闭。
- 项目可以禁用某个模型或收紧候选，但必须写明适用范围和理由。任何家族发生拒绝、
  降级、重映射或不可观测时，仍按 requested/observed 合同如实记录；该身份记录与
  上述轻量选模偏好各自独立。

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
