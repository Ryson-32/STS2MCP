<!-- TRELLIS:START -->
# Trellis Instructions

These instructions are for AI assistants working in this project.

This project is managed by Trellis. The working knowledge you need lives under `.trellis/`:

- `.trellis/workflow.md` — development phases, when to create tasks, skill routing
- `.trellis/spec/` — package- and layer-scoped coding guidelines (read before writing code in a given layer)
- `.trellis/workspace/` — per-developer journals and session traces
- `.trellis/tasks/` — active and archived tasks (PRDs, research, jsonl context)

If a Trellis command is available on your platform (e.g. `/trellis:finish-work`, `/trellis:continue`), prefer it over manual steps. Not every platform exposes every command.

If you're using Codex or another agent-capable tool, additional project-scoped helpers may live in:
- `.agents/skills/` — reusable Trellis skills
- `.codex/agents/` — optional custom subagents

Managed by Trellis. Edits outside this block are preserved; edits inside may be overwritten by a future `trellis update`.

<!-- TRELLIS:END -->

# STS2 MCP

- C# mod/API contracts: `.trellis/spec/mod/index.md`.
- Python MCP bridge contracts: `.trellis/spec/mcp/index.md`.
- Gameplay operation and learning rules: `.trellis/spec/gameplay/index.md`.
- This is a public repository. Before the repository's standing automatic commit/push closeout,
  inspect staged and outgoing changes for secrets, local accounts, machine paths and private host
  details. A privacy failure blocks the push.
- API-surface changes must keep `docs/raw-full.md`, `docs/raw-simplified.md` and MCP docstrings
  aligned. Non-trivial public API changes follow `CONTRIBUTING.md` discussion-first policy.
- Do not create a release, tag, PR or deployment without explicit authorization.

<!-- TRELLIS-PROFILE:START -->
## 共享 Trellis 规则路由

1. 先选择当前任务直接命中的规则文件；正文链接只有在任务也命中其场景时才继续读取，不做传递式全量加载。
2. 每次只打开一个选中的规则文件。输出被截断时按行段继续到 EOF；未完整读取的文件不算已加载。
3. 同一工作上下文内已经完整读取、且内容与适用事实未变化的规则可以复用，无需重复读取。

一项任务可以命中多行。开始实质工作前，完整读取每个直接命中的正文；本表只负责场景路由，不复制规则正文。

| 什么时候读取 | 必须打开的规则正文 |
|---|---|
| 新增、迁移、合并或修改长期规则时 | [规则归属与优先级](.trellis/spec/shared/rule-ownership-and-precedence.md) |
| 起草、修改或审查面向读者的中英文说明、文档和沟通时 | [通用语言表达](.trellis/spec/shared/language-general.md) |
| 项目声明适用科研语言规则，且起草、翻译或审查科研文类时 | [科研语言表达](.trellis/spec/shared/language-research.md) |
| 项目声明采用 FCI 语言规则，且处理燃料—冷却剂相互作用术语时 | [FCI 概念与双语术语](.trellis/spec/shared/language-fci.md) |
| 项目明确采用此作者语气，且进行学术起草、润色或语气校准时 | [作者学术语气](.trellis/spec/shared/language-author-academic.md) |
| Mac/Windows 开工、交接、提交或同步时 | [双端 Git 协作](.trellis/spec/shared/cross-device-git.md) |
| 仓库跟踪外部上游并长期保留本地或私有偏离时 | [上游跟踪与分叉治理](.trellis/spec/shared/upstream-fork-governance.md) |
| 选择或启动子代理/外部 AI worker、划分并行目标与基线、判断模型/provider/effort 或处理中断恢复时 | [子代理与外部 AI Worker 编排](.trellis/spec/shared/subagent-orchestration.md) |
| 使用原生子代理以外的 Channel worker、可见交互式 runtime、浏览器/桌面执行器或其它外部 AI 控制面时 | [外部 AI 执行器生命周期](.trellis/spec/shared/external-executor-lifecycle.md) |
| 更新 Trellis、处理跟踪/忽略或 Registry 时 | [Trellis 项目状态](.trellis/spec/shared/trellis-project-state.md) |
| 工作中出现或用户提出可复用经验、长期指令、设计原则、验收边界或稳定偏好时 | [长期知识沉淀](.trellis/spec/shared/durable-knowledge.md) |
| 核验事实、获取或生成数据与产物、测试、完成声明和最终交接时 | [证据与验证](.trellis/spec/shared/evidence-and-verification.md) |
| 检索、获取、发现或整理文献，或写入、分类用户级文献主库时 | [文献主库归档与分类](.trellis/spec/shared/literature-library-ingestion.md) |
| 路径、工具、数据或行为可能因系统不同而变化时 | [跨平台验证](.trellis/spec/shared/cross-platform-validation.md) |
| 处理日志、配置、远端系统、账号或准备 push 时 | [敏感信息](.trellis/spec/shared/sensitive-data.md) |
| 任务会修改、创建、删除或生成任何文件时 | [工程原则与最小改动](.trellis/spec/shared/engineering-principles.md) |
| 任务开始、恢复或范围切换，以及规划、执行、验证或交付时 | [安全高效工作流](.trellis/spec/shared/safe-workflow-and-efficiency.md) |
| 删除、清理、迁移、push、部署或其它外部变更前 | [权限与变更安全](.trellis/spec/shared/authority-and-change-safety.md) |
| 编写 Mac、Windows、远端或跨 shell 命令时 | [Shell 与命令可移植性](.trellis/spec/shared/shell-and-command-portability.md) |
| 涉及任何 VPS、SSH 或其它远端操作时，包括只读排查、探测、配置、部署和恢复 | [VPS 与远端操作](.trellis/spec/shared/vps-operations.md) |
| 新仓库初始化 Trellis 或同步标准 profile 时 | [新项目标准初始化](.trellis/spec/shared/new-project-bootstrap.md) |

## 项目私有规则路由

| 什么时候读取 | 必须打开的项目规则正文 | 来源索引 |
|---|---|---|
| 读取 Gameplay Operation And Learning Contract 项目合同 | [Gameplay Operation And Learning Contract](.trellis/spec/gameplay/index.md) | [索引](.trellis/spec/gameplay/index.md) |
| 读取 Python MCP Bridge Contract 项目合同 | [Python MCP Bridge Contract](.trellis/spec/mcp/index.md) | [索引](.trellis/spec/mcp/index.md) |
| 读取 C# Mod And HTTP API Contract 项目合同 | [C# Mod And HTTP API Contract](.trellis/spec/mod/index.md) | [索引](.trellis/spec/mod/index.md) |

普通小任务无需 `routing.json`。文件存在时，它只是复杂交接的可选路径与理由提示；缺失不报错，也不承担摘要、模型资格或运行状态合同。任务阶段与验证深度见 [workflow](.trellis/workflow.md)；项目合同与例外由托管块外正文和项目规范拥有，冲突时按[共享索引](.trellis/spec/shared/index.md)的优先级处理。
<!-- TRELLIS-PROFILE:END -->
