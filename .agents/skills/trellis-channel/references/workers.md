# Workers And Agent Cards

Use workers when a peer agent should execute independently and report back
through the channel event log. A worker is a registered child process (claude
or codex) attached to a channel; the supervisor forwards inbox messages to it
and translates its output back into channel events.

## Spawn

```bash
trellis channel create impl-task --by dispatcher --cwd /path/to/repo
trellis channel spawn impl-task --provider codex --as codex-impl --timeout disabled

echo "Implement the schema for table X per .trellis/.../prd.md" \
  | trellis channel send impl-task --as dispatcher --to codex-impl --stdin

trellis channel wait impl-task --as dispatcher --from codex-impl --kind done --timeout 30m
```

`spawn` forks a `channel __supervisor` worker that emits `spawned`, streams
`progress`, and emits `done` or `error` for each completed turn. Those events
do not terminate the long-lived worker process; `killed` or a synthesized
process-exit event closes its durable lifecycle. Workers stay
inbox-idle until a `send --to <worker>` (or a broadcast when
`--inbox-policy broadcastAndExplicit` is set) wakes them.

Key `spawn` flags:

- `--agent <name>` — load `.trellis/agents/<name>.md` (provider/model/as/system prompt defaults).
- `--provider <claude|codex>` — overrides the agent card; validated against the adapter registry.
- `--as <name>` — channel worker handle; defaults to the agent name.
- `--cwd <path>` — worker working directory (also the jail root for `--file`/`--jsonl`).
- `--model <id>` — provider model ID override.
- `--effort <low|medium|high|xhigh|max>` — reasoning level, independent from model ID.
- `--resume <id>` — resume an existing claude session / codex thread.
- `--ownership <key>` — optional logical work metadata; it does not lock or exclude peers.
- `--timeout <duration|disabled>` — warning-only supervision threshold; omitted or `disabled` means no fixed threshold and never auto-kills.
- `--warn-before <duration>` — `supervisor_warning` lead time (default `5m`; `0ms` warns at the threshold).
- `--file <path>` (repeatable, glob-supported) — inject file content into the system prompt.
- `--jsonl <path>` (repeatable) — Trellis jsonl manifest (`{file, reason}` per line).
- `--by <agent>` — author of the `spawned` event (defaults to `$TRELLIS_CHANNEL_AS` or `main`).
- `--inbox-policy <explicitOnly|broadcastAndExplicit>` — default `explicitOnly`.
- `--idle-timeout <duration>` — warning-only idle observation interval (default `5m`; `0` disables).
- `--max-live-workers <n>` — spawn-time live-worker budget (default `25`; `0` disables).

`spawn` succeeds only after the matching durable `spawned` event exists. That
event records `pid`, `provider`, `agent`, the injected `files`, resolved
`manifests`, and any explicit model/effort/ownership/resume metadata. Claude's
system prompt is transported through an owner-only sidecar file so long Windows
prompts do not enter argv.

Model and effort in the command or `spawned` event are **requested** values.
Report them as provider-observed/applied only when provider output independently
exposes that evidence; CLI argument validation and transport do not prove the
provider honored them.

## Agent Cards

`--agent <name>` resolves to `.trellis/agents/<name>.md`. The card name must
match `[A-Za-z0-9._-]+`. The default Trellis install ships two cards:

- `.trellis/agents/check.md` — code-quality reviewer.
- `.trellis/agents/implement.md` — coding worker for implementation runs.

```yaml
---
name: check
description: Code quality check expert.
provider: claude
---
```

Frontmatter fields populate `spawn` defaults (provider, model, `as`); the
markdown body becomes the worker's system-prompt role. Cards do **not**
auto-attach task files — context must be injected explicitly per spawn (see
below).

Always inspect project cards before spawning a named agent:

```bash
ls .trellis/agents
sed -n '1,100p' .trellis/agents/check.md
```

## Context Injection

Two flags inject content into the worker's system prompt under a
`# CONTEXT FILES` block, assembled by `context-loader`:

- `--file <path>` — repeatable, glob-supported (`*`, `**`). Each match is
  read and concatenated.
- `--jsonl <path>` — repeatable Trellis manifest where every line is
  `{"file":"<path>","reason":"<why>"}`. The reason is preserved as a header
  comment above each file's content.

Limits enforced by the loader:

- 1 MB hard cap per file (oversize → error).
- 200 KB per-file warning to stderr.
- 500 KB total assembled-context warning to stderr.
- Path-traversal jail: all resolved paths must stay under `--cwd`.

Example spawning a check agent against a task directory:

```bash
TASK=.trellis/tasks/05-13-example
trellis channel spawn cr-example --agent check --provider codex --as check-cx \
  --file "$TASK/prd.md" \
  --file "$TASK/design.md" \
  --file "$TASK/implement.md" \
  --jsonl "$TASK/check.jsonl" \
  --cwd "$PWD" --timeout disabled
```

The `spawned` event records both the literal `files` array and any `manifests`
expanded from `--jsonl`, so the audit trail captures whatever the worker was
actually shown.

## Names And Routing

`--as` has two meanings:

- `send` / `wait` / `interrupt`: speaker identity (author of the resulting event).
- `spawn`: the worker handle that other agents address with `--to`.

Use explicit names when multiple workers or providers participate in one
channel:

```bash
trellis channel spawn cr-feature --agent check --as check-claude
trellis channel spawn cr-feature --agent check --provider codex --as check-cx

trellis channel wait cr-feature --as main \
  --from check-claude,check-cx --kind done --all --timeout 15m
```

`--all` requires `--from` and blocks until every listed worker has produced a
matching event; timeout exits with code **124** and prints
`timeout: still waiting on ...` to stderr.

## Soft Interrupt — `interrupt`

`channel interrupt` is the cooperative redirect: it appends an `interrupt`
event (reason `"user"`) and, where the adapter supports it, issues a
provider-level turn interrupt with a replacement instruction. Use it when the
worker should drop its current turn and act on new input immediately, without
losing its session.

```bash
echo "Stop refactoring the parser — switch to fixing the failing test in src/foo.ts" \
  | trellis channel interrupt impl-task --as dispatcher --to codex-impl --stdin
```

Flags:

- `--as <agent>` **(required)** — caller identity.
- `--to <agent>` **(required)** — target worker.
- `--scope <project|global>` — channel scope.
- `--stdin` / `--text-file <path>` / `[text]` — replacement instruction body.

The command appends `interrupt_requested`; the supervisor answers with
`interrupted`. Filters can subscribe to those exact kinds. For a low-priority
hint that should wait for the next turn, send a plain message:

```bash
echo "Check this when you reach the next turn." \
  | trellis channel send impl-task --as dispatcher --to codex-impl \
      --stdin
```

## Hard Stop — `kill`

Use `kill` when the worker must stop **now** (e.g. runaway loop, bad
instructions already in flight, or `interrupt` is not honored by the
adapter). The supervisor escalates SIGTERM → 8 s grace → SIGKILL; the CLI
ensures that the stopped durable generation has exactly one terminal `killed`
event. On Windows the supervisor may exit before its JavaScript signal handler
runs, so the CLI supplies the missing event under the channel lock; on POSIX it
does not duplicate the supervisor's event.

```bash
trellis channel kill impl-task --as codex-impl
trellis channel kill impl-task --as codex-impl
```

`kill` flags:

- `--as <agent>` **(required)** — names the worker (positional `<name>` is the channel).
- `--scope <project|global>`.
- `--force` — SIGKILL immediately (also kills the inner worker pid).

Side effects: cleans `pid`, `worker-pid`, `config`, `system-prompt`, `spawnlock` sidecar
files; keeps `log`, `session-id`, `thread-id` for forensics and resume.
`runtime.durableWithoutSidecar` includes terminal history, so a non-zero value
alone is not a live-process leak; confirm `durable.running`, `durable.terminal`
and `runtime.sidecars` together.

Process control never treats PID existence as ownership. New launches carry a
random launch ID and structured supervisor/provider identity sidecars (PID,
role, channel, worker, canonical config, process birth, parent, and command
evidence). Provider command evidence is hashed. Windows reads command line,
creation date, and parent PID; POSIX/macOS reads the equivalent `ps` fields.
Before every TERM/KILL escalation Trellis rechecks the same generation. A
mismatched or unknown identity receives no signal; `kill` fails without
cleaning its evidence.

Resume is optional metadata and provider capability, not a mandatory recovery
step or guarantee. After a kill, inspect the durable result and decide whether
to spawn a fresh worker or explicitly resume a compatible saved session.

## No-signal Recovery — `reclaim`

Use `reclaim` only when one explicitly named worker has no local supervisor
identity, is confirmed dead, or has a mismatched reused PID. It takes the worker lock, rechecks
the durable spawn identity, exact sidecars, and PID. A durable worker gets one
synthesized reclaimed terminal event. Stable mismatched or legacy reservation
residue is reconciled with an unchanged non-terminal durable generation in the
same exact operation. A pure orphan or already-terminal identity with concrete
ephemeral sidecar evidence is cleaned without fabricating another worker event.
All paths remove only ephemeral runtime sidecars.

```bash
trellis channel reclaim impl-task --as codex-impl --dry-run
trellis channel reclaim impl-task --as codex-impl
```

`reclaim` never sends a signal, scans other workers, deletes the channel, or
requires an external audit file. A live, unknown, or changed worker fails closed. Use
`kill` for a live process; use `reclaim` only for missing/dead PID residue.

## Final Closeout

A persistent worker remains inbox-idle after every ordinary `done` or
`turn_finished`. Once no later turn is planned, inspect `channel list --json`,
use exact `kill` for a live generation, or preview and run exact `reclaim` after
abnormal supervisor loss. Inspect the same channel again and confirm
`durable.running` no longer includes that worker. This is lifecycle closeout,
not a timeout, sweep, or reason to terminate unfinished work.

## Worker Live Budget And Idle Warnings

The guard prevents unbounded resident-worker accumulation without terminating
existing work. It provides two policies per project bucket:

- **Idle observation** — warn in the worker log after continuous idle time
  exceeds the configured threshold (default `5m`; `0` disables). It never
  signals or kills the worker.
- **Live-worker budget** — refuse the new spawn if more than N workers are
  already alive in the same project bucket (default `25`; `0` disables).

Precedence (highest first):

1. CLI flags: `--idle-timeout`, `--max-live-workers` on `spawn`.
2. Environment variables: `TRELLIS_CHANNEL_WORKER_IDLE_TIMEOUT`,
   `TRELLIS_CHANNEL_MAX_LIVE_WORKERS`.
3. `.trellis/config.yaml` under `channel.worker_guard`.
4. Built-in defaults (`5m`, `25`).

Budget rejection lists the currently live workers and explicit kill/override
hints. No worker is swept to create capacity. `--timeout` is warning-only;
`channel kill` remains the explicit live-process termination path. `reclaim`
only closes already missing/dead runtime residue. Provider usage-limit errors
end one turn (`error` + `turn_finished`) and never auto-kill, auto-reclaim, or
auto-retry the worker.

To inspect current state, use `channel list`: `DURABLE` is event-log lifecycle,
`ACTIVITY` is current turn state, and `RUNTIME` is local supervisor capacity.
`workersAlive` in JSON remains the live local supervisor count, while
`runtime.alive/dead/unknown` counts only PID sidecars and the same object
separately reports matched, orphan-sidecar, and durable-without-sidecar counts. Inspect exact
per-channel `pid` / `worker-pid` sidecars under
`~/.trellis/channels/<bucket>/<channel>/`.

## Worker Inbox APIs

The inbox is the channel surface workers wake on. Routing is controlled by
two knobs:

- **Inbox policy** (`spawn --inbox-policy`):
  - `explicitOnly` (default) — worker only wakes on `send --to <worker>` or
    `interrupt --to <worker>`.
  - `broadcastAndExplicit` — also wakes on broadcasts (`send` with no `--to`).
- **Delivery mode** (`send --delivery-mode`):
  - `appendOnly` — append the event regardless of worker state.
  - `requireKnownWorker` — atomically reject if any named worker was never spawned.
  - `requireRunningWorker` — atomically reject unless every named worker is
    durably running and its exact local supervisor PID is alive.

Strict multi-target delivery is all-or-nothing. Rejection appends durable
`undeliverable` attempt events, appends no inbox-visible `message`, and exits
non-zero. `appendOnly` keeps backlog-compatible behavior.

Inbox-relevant subcommands:

- `send <channel> [text]` — append a `message` event.
  - `--as <agent>` **(required)** — author.
  - `--to <agents>` — CSV; one → string, many → array; broadcast if omitted.
  - `--stdin` / `--text-file <path>` / `[text]` — body source.
  - `--delivery-mode <appendOnly|requireKnownWorker|requireRunningWorker>`.
- `interrupt <channel> [text]` — soft-interrupt redirect (see above).
- `wait <channel>` — block until matching events arrive.
  - `--as <agent>` **(required)** — `self` for filter context.
  - `--from <agents>` — CSV authors.
  - `--kind <kind[,kind...]>` — CSV (OR semantics); supports
    `interrupt_requested`, `interrupted`, `done`, `progress`, etc.
  - `--to <target>` — defaults to own agent (broadcast + explicit-to-me).
  - `--include-progress` — also wake on progress events.
  - `--all` — require every `--from` agent to match (timeout → exit **124**).
  - `--timeout <duration>` — `30s` / `2m` / `1h` / `1000ms`.
- `messages <channel>` — view / filter / follow the event stream.
  - `--follow` to tail, `--kind` / `--from` / `--to` to filter, `--raw` for
    JSON-per-line, `--no-progress` to hide progress noise.

A typical dispatcher loop:

```bash
# 1. Wake the worker.
echo "Run the failing test and report." \
  | trellis channel send impl-task --as dispatcher --to codex-impl --stdin \
      --delivery-mode requireRunningWorker

# 2. Block until it finishes.
trellis channel wait impl-task --as dispatcher \
  --from codex-impl --kind done,error --timeout 30m

# 3. Read the final answer.
trellis channel messages impl-task --from codex-impl --last 1 --raw
```

All event-emitting subcommands (`send`, `interrupt`, `post`, `context add` /
`delete`, `title set` / `clear`, `thread rename`) print the appended event as
a single JSON line on stdout, making the inbox layer easy to script against.
