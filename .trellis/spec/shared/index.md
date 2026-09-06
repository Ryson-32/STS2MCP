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

先根据当前任务对象，从本表、项目索引和相关 package 或 guides 入口选择直接命中的 owner；一项请求可以命中多处。索引只负责定位，选中文件仍须完整读取；正文中的链接不自动触发传递式全量加载，只有当前任务也命中其场景时才继续读取。

| 规范 | 什么时候读取 |
|---|---|
| [规则归属与优先级](rule-ownership-and-precedence.md) | 新增、迁移、合并或修改长期规则时 |
| [通用语言表达](language-general.md) | 起草、修改或审查面向读者的中英文说明、文档和沟通时 |
| [科研语言表达](language-research.md) | 项目声明适用科研语言规则，且起草、翻译或审查科研文类时 |
| [FCI 概念与双语术语](language-fci.md) | 项目声明采用 FCI 语言规则，且处理燃料—冷却剂相互作用术语时 |
| [作者学术语气](language-author-academic.md) | 项目明确采用此作者语气，且进行学术起草、润色或语气校准时 |
| [双端 Git 协作](cross-device-git.md) | Mac/Windows 开工、交接、提交或同步时 |
| [上游跟踪与分叉治理](upstream-fork-governance.md) | 仓库跟踪外部上游并长期保留本地或私有偏离时 |
| [子代理与外部 AI Worker 编排](subagent-orchestration.md) | 选择或启动子代理/外部 AI worker、划分并行目标与基线、判断模型/provider/effort 或处理中断恢复时 |
| [外部 AI 执行器生命周期](external-executor-lifecycle.md) | 使用原生子代理以外的 Channel worker、可见交互式 runtime、浏览器/桌面执行器或其它外部 AI 控制面时 |
| [Trellis 项目状态](trellis-project-state.md) | 更新 Trellis、处理跟踪/忽略或 Registry 时 |
| [长期知识沉淀](durable-knowledge.md) | 工作中出现或用户提出可复用经验、长期指令、设计原则、验收边界或稳定偏好时 |
| [证据与验证](evidence-and-verification.md) | 核验事实、获取或生成数据与产物、测试、完成声明和最终交接时 |
| [文献主库归档与分类](literature-library-ingestion.md) | 检索、获取、发现或整理文献，或写入、分类用户级文献主库时 |
| [跨平台验证](cross-platform-validation.md) | 路径、工具、数据或行为可能因系统不同而变化时 |
| [敏感信息](sensitive-data.md) | 处理日志、配置、远端系统、账号或准备 push 时 |
| [工程原则与最小改动](engineering-principles.md) | 任务会修改、创建、删除或生成任何文件时 |
| [安全高效工作流](safe-workflow-and-efficiency.md) | 任务开始、恢复或范围切换，以及规划、执行、验证或交付时 |
| [权限与变更安全](authority-and-change-safety.md) | 删除、清理、迁移、push、部署或其它外部变更前 |
| [Shell 与命令可移植性](shell-and-command-portability.md) | 编写 Mac、Windows、远端或跨 shell 命令时 |
| [VPS 与远端操作](vps-operations.md) | 涉及任何 VPS、SSH 或其它远端操作时，包括只读排查、探测、配置、部署和恢复 |
| [新项目标准初始化](new-project-bootstrap.md) | 新仓库初始化 Trellis 或同步标准 profile 时 |

## 共享规则与项目边界

- Trellis 阶段、任务是否创建、JSONL 上下文清单和批准逻辑：由当前 `.trellis/workflow.md` 管理。
- Codex、Claude、Cursor 等单个平台的模型、推理强度、hook 和权限：由对应项目级平台配置管理。
- 子代理的通用角色、上下文交接、模型/provider/effort 决策参考、worktree 隔离、并发和中断恢复由上表“子代理与外部 AI Worker 编排”管理；真实能力由当前平台/能力 owner 提供，项目只补充本项目特有边界。
- 原生子代理以外的外部执行器选择、精确运行身份、完成证据、受控重选和资源回收由上表“外部 AI 执行器生命周期”管理。
- 私有/公开仓库的默认 commit/push 授权边界由上表“权限与变更安全”管理；具体 remote、branch、main-only、PR-only、部署、发布和 tag 策略留在当前项目。
- 论文数据、图件、Word、业务 API、数据库、UI、生产，以及具体上游地址、分支策略、差异清单和发布部署合同：留在拥有它们的项目规范中。
- Trellis 自带的 code-reuse、cross-layer 等生成模板：继续跟随 Trellis 官方更新。
