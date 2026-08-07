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

先按任务对象同时检查本表、项目索引和相关 package 或 guides 入口；一项请求可以命中多处。索引只负责定位：计划或执行前必须打开所有直接相关链接的正文，不能把看见文件名当成已经加载规范。

| 规范 | 什么时候读取 |
|---|---|
| [规则归属与优先级](rule-ownership-and-precedence.md) | 新增、迁移、合并或修改长期规则时 |
| [双端 Git 协作](cross-device-git.md) | Mac/Windows 开工、交接、提交或同步时 |
| [上游跟踪与分叉治理](upstream-fork-governance.md) | 仓库跟踪外部上游并长期保留本地或私有偏离时 |
| [子代理与外部 AI Worker 编排](subagent-orchestration.md) | 规划复杂任务、选择或启动子代理/外部 AI worker、分发规范上下文或记录 requested/observed 身份时 |
| [Trellis 项目状态](trellis-project-state.md) | 更新 Trellis、处理跟踪/忽略或 Registry 时 |
| [长期知识沉淀](durable-knowledge.md) | 工作中出现或用户提出可复用经验、长期指令、设计原则、验收边界或稳定偏好时 |
| [证据与验证](evidence-and-verification.md) | 调查、检索、下载、入库或整理文献、获取或生成数据与产物、测试、完成声明和最终交接时 |
| [跨平台验证](cross-platform-validation.md) | 路径、工具、数据或行为可能因系统不同而变化时 |
| [敏感信息](sensitive-data.md) | 处理日志、配置、远端系统、账号或准备 push 时 |
| [工程原则与最小改动](engineering-principles.md) | 设计实现、重构或评估是否需要新增抽象时 |
| [安全高效工作流](safe-workflow-and-efficiency.md) | 从调查到交付组织步骤、并行和 ownership 时 |
| [权限与变更安全](authority-and-change-safety.md) | 删除、清理、迁移、push、部署或其它外部变更前 |
| [Shell 与命令可移植性](shell-and-command-portability.md) | 编写 Mac、Windows、远端或跨 shell 命令时 |
| [新项目标准初始化](new-project-bootstrap.md) | 新仓库初始化 Trellis 或同步标准 profile 时 |

## 共享规则与项目边界

- Trellis 阶段、任务是否创建、JSONL 上下文清单和批准逻辑：由当前 `.trellis/workflow.md` 管理。
- Codex、Claude、Cursor 等单个平台的模型、推理强度、hook 和权限：由对应项目级平台配置管理。
- 子代理的通用角色、routing、外部 worker 进程和 requested/observed 记录合同由上表“子代理与外部 AI Worker 编排”管理；真实模型/provider 能力仍由能力仓库和当前项目声明。
- 私有/公开仓库的默认 commit/push 授权边界由上表“权限与变更安全”管理；具体 remote、branch、main-only、PR-only、部署、发布和 tag 策略留在当前项目。
- 论文数据、图件、Word、业务 API、数据库、UI、生产，以及具体上游地址、分支策略、差异清单和发布部署合同：留在拥有它们的项目规范中。
- Trellis 自带的 code-reuse、cross-layer 等生成模板：继续跟随 Trellis 官方更新。
