# Trellis 项目状态

## 应跟踪的项目内容

下列文件属于项目协作和可复现工作流，存在时应作为普通项目文件审查和跟踪：

- `.trellis/spec/**`、`.trellis/config.yaml`、`.trellis/workflow.md`
- `.trellis/.version`、`.trellis/.template-hashes.json`
- `.trellis/scripts/**`、项目生成的 agent/skill/hook 入口
- `.trellis/tasks/**`、`.trellis/workspace/**` 中有协作价值的任务、归档和交接记录

不要手工修改 `.trellis/.version` 或 `.trellis/.template-hashes.json` 来消除更新提示。

## 应忽略的本机状态

下列内容不跨设备同步，也不得 force-add：

- `.trellis/.developer`、`.trellis/.current-task`
- `.trellis/.runtime/**`、`.trellis/.backup-*`
- cache、worktree、临时文件、Python cache 和平台会话 scratch
- 用户级 trust、provider、MCP、登录、通知、审批和密钥状态

项目如果有额外本机状态，应在项目 `.gitignore` 中精确列出，不用宽泛规则忽略整个 `.trellis/`。

## 更新原则

- 默认采纳 Trellis 最新官方模板、迁移和默认行为。
- 只有与明确的项目定制、兼容合同或真实语义冲突时，才保留本地版本并人工合并。
- `update.skip` 只保护确实存在冲突且仍需本地维护的文件；每个条目都应能解释差异，差异消失后及时移除。
- 不用笼统的“谨慎”长期冻结官方修复，也不为追求全量更新覆盖用户或项目规则。

更新前后至少检查：

```bash
trellis update --dry-run
git diff --check
git check-ignore -v .trellis/.developer .trellis/.current-task .trellis/.runtime
```

再确认 `.trellis/tasks/**`、`.trellis/workspace/**` 和项目配置没有被意外忽略。

## Registry 边界

- 共享 Registry 只管理 `.trellis/spec/shared/**`，不接管项目 backend、frontend、研究、部署或业务命名空间。
- 首次接入和每次更新先看 dry run；存在同名本地文件时先比较所有权和语义。
- 任务 JSONL 清单按任务需要使用，不属于长期共享规范。
- Trellis 阶段、任务创建、批准和平台调度逻辑继续由当前版本的工作流与平台配置管理，不在共享 spec 中复制。
