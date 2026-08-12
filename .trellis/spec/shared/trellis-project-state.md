# Trellis 项目状态

## 应跟踪的项目内容

下列文件属于项目协作和可复现工作流，存在时应作为普通项目文件审查和跟踪：

- `.trellis/spec/**`、`.trellis/config.yaml`、`.trellis/workflow.md`
- `.trellis/.version`、`.trellis/.template-hashes.json`
- `.trellis/scripts/**`、项目生成的 agent/skill/hook 入口
- `.trellis/tasks/**`、`.trellis/workspace/**` 中有协作价值的任务、归档和交接记录

`.trellis/.version` 和 `.trellis/.template-hashes.json` 是工具维护的派生状态；不得手工修改它们或其它生成块来消除更新提示。

## 应忽略的本机状态

下列内容不跨设备同步，也不得 force-add：

- `.trellis/.developer`、`.trellis/.current-task`
- `.trellis/.runtime/**`、`.trellis/.backup-*`
- cache、worktree、临时文件、Python cache 和平台会话 scratch
- 用户级 trust、provider、MCP、登录、通知、审批和密钥状态

项目如果有额外本机状态，应在项目 `.gitignore` 中精确列出，不用宽泛规则忽略整个 `.trellis/`。

## 受管入口与生成投影

- 一个入口文件可以同时包含官方模板块、Profile 生成块和项目正文。修改前先依据托管标记确认各部分的所有者，不把整份文件视为全手工或全生成。
- 标准 Profile 中，`TRELLIS:START` 块来自官方模板，`TRELLIS-PROFILE` 块来自共享索引和声明的项目索引；托管块外的项目正文由项目维护并应保留。
- 修改 `TRELLIS-PROFILE` 展示的规则时，先更新拥有规则的 spec；路由变化时再更新对应索引，然后通过 Profile 重新生成投影。不得把手工修改生成块或哈希当作修复。
- 至少审查一次 dry run 和生成 diff，运行相关链接检查，再在落盘后通过第二次 dry run 确认零文件变化。

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
