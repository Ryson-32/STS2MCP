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
## 共享 Trellis 规则入口

共享规则由 Trellis 会话缓存固定到已验证版本，不复制到项目 Git。新主会话通常由 hook 完成一次检查；当前上下文没有注入共享索引、版本和实际路径时，运行：

`python .trellis/scripts/shared_spec_cache.py ensure --json`

从返回的 `index_path` 读取路由表，再按当前任务选择直接命中的 owner；不要传递式全量加载。每次完整读取一个选中的文件到 EOF。同一上下文已完整读取且版本未变时可以复用。

旧逻辑引用 `.trellis/spec/shared/<owner>.md` 继续有效。需要实际文件路径时运行 `python .trellis/scripts/shared_spec_cache.py resolve <logical-ref> --json`，使用返回的验证缓存路径；不要猜测缓存目录。

项目说明中的 Registry 网页链接只供人类浏览当前 `main`，不代表本任务版本。AI 执行仍以当前会话固定快照为准。

## 项目私有规则路由

| 什么时候读取 | 必须打开的项目规则正文 | 来源索引 |
|---|---|---|
| 读取 Gameplay Operation And Learning Contract 项目合同 | [Gameplay Operation And Learning Contract](.trellis/spec/gameplay/index.md) | [索引](.trellis/spec/gameplay/index.md) |
| 读取 Python MCP Bridge Contract 项目合同 | [Python MCP Bridge Contract](.trellis/spec/mcp/index.md) | [索引](.trellis/spec/mcp/index.md) |
| 读取 C# Mod And HTTP API Contract 项目合同 | [C# Mod And HTTP API Contract](.trellis/spec/mod/index.md) | [索引](.trellis/spec/mod/index.md) |

普通小任务无需 `routing.json`。文件存在时，它只是复杂交接的可选路径与理由提示；缺失不报错，也不承担摘要、模型资格或运行状态合同。任务阶段与验证深度见 [workflow](.trellis/workflow.md)；项目合同与例外由托管块外正文和项目规范拥有，冲突时按共享缓存返回的索引处理。
<!-- TRELLIS-PROFILE:END -->
