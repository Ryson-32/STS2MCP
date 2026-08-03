# 新项目 Trellis 标准初始化

## 适用范围

本流程用于新的活动 Git 仓库和首次接入共享规范的现有仓库。只读参考仓库、代码快照和没有独立 Trellis 配置的继承目录不重复初始化。

## 标准流程

1. 确认目标是正确的 Git 仓库，工作区干净，当前分支没有落后或分叉。
2. 使用共享仓库固定并验证过的 Trellis 版本，同时初始化 Codex 与 Claude，开发者身份使用当前团队约定。
3. 接入私有 Registry，使共享 payload 只落入 `.trellis/spec/shared/**`；认证 token 只通过子进程环境传递。
4. 应用标准 workflow：按任务需要持久化、JSONL 按需、原授权范围内不要求形式化二次批准、Codex 使用官方默认 auto 调度。
5. 保留项目 `AGENTS.md` 中的身份、事实源、业务合同、分支部署和明确例外；详细规则路由到共享或项目 spec。
6. 创建最小 `CLAUDE.md` 路由，确保 Claude 和 Codex 读取相同的项目、workflow 与 spec 事实源。
7. 根据真实代码和文档填写项目 spec；纯占位文件只能在确认无引用后删除。

推荐入口：

```text
node tools/trellis-profile.mjs init --repo <path>
node tools/trellis-profile.mjs sync --repo <path> --dry-run
node tools/trellis-profile.mjs sync --repo <path>
```

## 跟踪与冲突

- 跟踪项目 Trellis 配置、模板、tasks/workspace 和平台入口；忽略 developer、runtime、backup、cache 和用户级状态。
- `update.skip` 只保护 profile 或项目仍需维护的真实语义冲突；每项必须能说明拥有者，冲突消失后删除。
- `.codex/agents/trellis-*.toml` 的 `model` 和 `model_reasoning_effort` 是项目可选定制，更新不得覆盖。
- 平台渲染差异由 profile 在 Trellis 管理文件内规范化，不能扩散到业务文件。

## 验收

- `.trellis/.version`、Registry source、共享目录、Codex/Claude hook 和入口符合 profile。
- `sync --dry-run` 对目标仓库零写入，第二次真实 sync 幂等。
- 配置可解析、hook 可编译、本机状态被忽略、项目 tasks/workspace 未被误忽略。
- 活跃任务引用仍存在，`git diff --check` 通过，未运行或失败的验证如实记录。
