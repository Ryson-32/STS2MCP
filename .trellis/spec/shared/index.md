# 共享规范入口

## 适用范围

本目录是多个 Trellis 项目共同使用的最低协作与质量底线。消费仓库可以增加更严格或更具体的规则；需要例外时，必须在项目规则中明确写出原因、范围和替代验证，不能静默忽略共享规则。

## 优先级

1. 平台、system、developer 和安全约束。
2. 用户当前明确指令。
3. 当前项目的 `AGENTS.md`、业务合同、任务要求和项目 spec。
4. 本目录的共享底线。
5. 通用模板、历史记录和示例。

发生冲突时采用更高优先级的当前规则，并同步修正或标注已失效的低优先级入口。

## 规范索引

| 规范 | 什么时候读取 |
|---|---|
| [规则归属与优先级](rule-ownership-and-precedence.md) | 新增、迁移、合并或修改长期规则时 |
| [双端 Git 协作](cross-device-git.md) | Mac/Windows 开工、交接、提交或同步时 |
| [Trellis 项目状态](trellis-project-state.md) | 更新 Trellis、处理跟踪/忽略或 Registry 时 |
| [长期知识沉淀](durable-knowledge.md) | 用户提出长期指令、设计原则或验收边界时 |
| [证据与验证](evidence-and-verification.md) | 调查、测试、完成声明和最终交接时 |
| [跨平台验证](cross-platform-validation.md) | 路径、工具、数据或行为可能因系统不同而变化时 |
| [敏感信息](sensitive-data.md) | 处理日志、配置、远端系统、账号或准备 push 时 |
| [工程原则与最小改动](engineering-principles.md) | 设计实现、重构或评估是否需要新增抽象时 |
| [安全高效工作流](safe-workflow-and-efficiency.md) | 从调查到交付组织步骤、并行和 ownership 时 |
| [权限与变更安全](authority-and-change-safety.md) | 删除、迁移、push、部署或其它外部变更前 |
| [Shell 与命令可移植性](shell-and-command-portability.md) | 编写 Mac、Windows、远端或跨 shell 命令时 |
| [新项目标准初始化](new-project-bootstrap.md) | 新仓库初始化 Trellis 或同步标准 profile 时 |

## 不归本目录管理

- Trellis 阶段、任务是否创建、JSONL 上下文清单和批准逻辑：由当前 `.trellis/workflow.md` 管理。
- Codex、Claude、Cursor 等单个平台的模型、推理强度、hook 和权限：由对应项目级平台配置管理。
- 分支、提交、push、部署、发布、tag 和 PR 的具体授权策略：由当前项目管理。
- 论文数据、图件、Word、业务 API、数据库、UI、生产和上游分叉合同：留在拥有它们的项目规范中。
- Trellis 自带的 code-reuse、cross-layer 等生成模板：继续跟随 Trellis 官方更新。
