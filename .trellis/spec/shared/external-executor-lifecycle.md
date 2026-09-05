# 外部 AI 执行器生命周期

## 场景：外部执行器的选择、完成与回收

### 1. Scope / Trigger

当主会话准备使用原生子代理以外的 Channel worker、可见交互式 runtime、浏览器/桌面执行器或其它外部 AI 控制面时应用本节。目标是防止静默换路、把可见或安静误当完成，以及在权限和副作用未知时启动第二个同目标执行器。

### 2. Signatures

- 能力探测至少区分：`executorId`、当前 `capable`、实际 `assurances`、`permissionBoundary`，以及探测是否已经产生运行实例或外部副作用。
- 一次运行至少能按精确身份投影：`goalId`、`runtimeId/workerId`、`lifecycle`、可选 typed `completion`、归属明确的输出，以及当前工作树/外部副作用。
- 终态事件和最终答案是两个字段：例如 Channel `done/error/killed` 证明 lifecycle，最终 `message` 或 typed result 承载结果；二者不得互相冒充。

### 3. Contracts

- 用户显式指定执行器时只使用该执行器；失败不自动换到另一条路。自动选择只在启动前用非变异探测比较当前能力、真实权限/隔离保证和任务交互形态。
- 一旦执行器启动被尝试，同一目标最多保留一个可能仍能工作的执行面。只有精确证据证明原执行器从未创建，或已终止且不再能产生工作，并且其输出、审批、工作树和其它副作用已经归属并处理，才可以披露后重新选择。
- “只读”提示词、worker 名称或 review 角色不是技术保证。完成报告必须写明实际 Provider 权限、sandbox/worktree、可写路径和审批 owner；没有强制边界时把只读视为行为要求而非隔离事实。
- 通知、启动回执、进程存在、窗口/pane 可见、worker 注册、安静超时和 payload 为空的 lifecycle 事件都不授予权限，也不单独证明结果完成。审批由当前任务的授权 owner 决定；通知只负责唤醒或定位该决定。
- 完成需要把同一精确运行身份的 lifecycle/typed result 与实际产物、Git diff 或外部状态回读相互印证。Channel 等事件系统先核对终态归属，再读取该 worker 的最终结果；不得把 supervisor 的 `done` 文本当成答案。
- 主会话保留最终验收、commit、push、发布、部署和任务收尾 ownership。外部结果是建议或候选改动，必须经过受影响范围检查。
- 回收只能定位该执行器拥有的精确 session、worker、worktree、helper 或临时目录。dirty、已 commit、未归属或仍可能继续工作的资源必须保留并报告；收到结果不等于已经审阅可见窗口，也不自动授权关闭或丢弃。

### 4. Validation & Error Matrix

- 显式执行器不可用或失败 → 报告该路由失败，除非用户随后明确改选，否则不 fallback。
- 自动候选的非变异探测失败且尚未启动 → 可在说明能力差异后选择其它合格候选。
- 启动结果 unknown、partial、live、awaiting approval 或仍可编辑 → 留在原恢复路径，不启动同目标替代者。
- lifecycle 终止但找不到归属结果，或结果存在但 lifecycle/身份不匹配 → 标为未完成或证据不完整，继续精确核对。
- 工作树 dirty、已有 commit 或副作用 ownership 不清 → 禁止自动清理；保留现场并交回主会话。

### 5. Good / Base / Bad Cases

- Good：显式 Channel review 等到该 worker 的系统终态，再读取同一 worker 的最终 message，复核目标文件仍无 diff 后交付。
- Base：启动前探测显示一个候选不具备任务要求的隔离能力，且没有创建实例；主会话记录理由后选择另一合格候选。
- Bad：看到 pane、`done`、启动 PID 或 wait timeout 就声称完成/失败，随后静默启动第二个同目标执行器，或清理含未审阅改动的 worktree。

### 6. Tests Required

- 路由场景覆盖显式选择、启动前候选淘汰、显式失败不 fallback、启动后 unknown/live/partial 禁止重复、终态且副作用已处理后的受控重选。
- adapter/事件测试分别断言 lifecycle 归属、最终结果归属和空 payload 行为；`done` 不应被解析成最终答案，`killed` 应按目标 worker 而非事件作者归属。
- 权限测试区分提示词只读与技术只读，覆盖 Provider-native 权限、sandbox/worktree 和可写范围的真实投影。
- 清理测试证明只移除精确 owned 且 clean 的资源，并保留 dirty、committed、unowned 及仍 live 的 sibling。

### 7. Wrong vs Correct

```text
# Wrong: wait 超时或看到 done 就换路并清理。
start(executor_b)
remove(worktree_a)

# Correct: 读取 exact lifecycle/result/effects，再决定恢复、交付或披露后重选。
state = observe(executor_a, runtime_id)
effects = inspect_owned_effects(state)
if state.terminal && !state.can_work && effects.resolved:
    decide_next_route_explicitly()
```

## Trellis Channel 外部 worker 参考

- 一次性任务优先 print mode，prompt 经 stdin 或受保护文件传入，不拼接 shell 命令；连续上下文才使用 persistent mode 与明确 session identity。
- adapter 应处理进程启动、结构化输出、只告警监督、显式 cancel、退出码/stderr 分类和输出大小边界。真实调用可能产生费用或外部动作时，仍需当前任务授权。
- `--output-format json` / `stream-json` 可能抑制重映射提示，所以 argv、stdout 标签或“命令成功”只证明请求事实；实际身份优先看 provider 原始结果或适用的结构化 `modelUsage`。
- fake executable 与合成输入适合测试 adapter 行为；不要为了普通任务运行真实付费调用来证明编排流程本身。
