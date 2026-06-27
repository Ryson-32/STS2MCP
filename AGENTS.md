# STS2 MCP — AI Gameplay Guide

## Trellis Git Tracking

- Track `.trellis/tasks/**`, `.trellis/workspace/**`, `.trellis/spec/**`,
  `.trellis/config.yaml`, `.trellis/.version`, and
  `.trellis/.template-hashes.json` in Git when they change.
- Keep developer-local Trellis state out of Git: `.trellis/.developer`,
  `.trellis/.current-task`, `.trellis/.runtime/`, `.trellis/.backup-*/`,
  `.trellis/**/__pycache__/`, and `.trellis/**/*.pyc`.
- Do not force-edit `.trellis/.version` or `.trellis/.template-hashes.json`
  just to silence a `trellis update` warning. Run `trellis update --dry-run`
  and fix the real tracked/ignored boundary instead.
- Do not create PRs, tag releases, or deploy unless the user explicitly asks
  for that remote action. Pushes follow the cross-device rules below.

## Cross-Device Collaboration

- This repository may be edited from both macOS and Windows checkouts. Treat
  GitHub / the configured Git remote as the source of truth between machines.
- Do not use OneDrive, iCloud, or other cloud-synced folders as the
  synchronization layer for the Git worktree; local paths are only storage
  locations.
- Before editing, check `git status --short --branch`. When an upstream exists
  and the worktree is clean, fast-forward from the remote before making changes.
- If a checkout is dirty, ahead/behind, or has unfamiliar changes, preserve
  them. Do not overwrite, reset, or fold in work left by the other machine,
  another AI, or the user.
- Keep machine-specific paths, tool versions, OS account names, secrets, tokens,
  passwords, and local MCP/client config out of shared project docs. Use ignored
  local config or local notes when those details are needed.
- When changing Trellis, Codex, Claude, Cursor, or other project-level AI
  workflow files, keep shared rules path-agnostic and cross-device safe; put
  per-machine setup details in local-only files.
- When frontend work touches behavior that may differ between macOS and
  Windows, leave a clear boundary, configuration entry point, or code comment
  for the other side. Do not implement unverified adaptations for the other OS.
- Standing repo rule: after every verified change set, automatically split the
  work into logical commits by module or concern, then push the completed
  branch to the configured writable remote.
- This is a public repository. Before every push, inspect the exact staged and
  outgoing changes for private data: secrets, tokens, passwords, private keys,
  local-only account details, machine-specific paths, and sensitive host or
  network details. Do not push if the privacy check fails or the push would
  include unfamiliar changes.

## MCP Tool Calling Tips

## Gameplay Learning

- Actively use the `sts2-gameplay-learning` skill when playing STS2 through MCP,
  reviewing a run, or answering strategy questions from prior runs.
- For meaningful gameplay decisions and run closeout, record compact run facts
  and lessons in the shared local gameplay-learning store instead of leaving
  them only in chat.

## Gameplay Automation Boundary

- Default to manual gameplay decisions using MCP/API state inspection. Do not
  run local auto-play scripts unless the user explicitly asks to use a script
  for that run.
- Keep experimental auto-play scripts in local-only paths, not the public repo,
  unless the user explicitly asks to publish them.

### State Polling
- After `combat_end_turn`, the state may show `is_play_phase: false` or `turn: enemy`. Call `get_game_state` again to advance to the next player turn.
- Sometimes you need to call `get_game_state` twice — once to see enemy turn results, once to see your new hand.
- Use `format: "json"` during combat for structured data; `format: "markdown"` for map/event overview.

### Card Index Shifting
- **CRITICAL**: Playing a card removes it from hand and shifts all indices. Play cards from RIGHT to LEFT (highest index first) to keep lower indices stable, or re-check state between plays.
- When targeting, always provide `target` for single-target cards. Entity IDs are UPPER_SNAKE_CASE with a `_0` suffix (e.g. `KIN_PRIEST_0`).

### Event & Reward Flow
- Events: `event_choose_option`. After choosing, there's often a "Proceed" option at index 0.
- Rest sites: `rest_choose_option`, then `proceed_to_map`.
- Rewards: claim from right-to-left (highest index first) to avoid index shifting. Card rewards open a sub-screen; use `rewards_pick_card` or `rewards_skip_card`.

### Potions
- `use_potion(slot=N)` — slot is the potion slot index, not a card index.
- `discard_potion(slot=N)` — discard a potion to free up the slot when full.
- Potions don't cost energy or count as card plays. Use buff potions BEFORE playing cards.

---

## General Strategy

### Core Principles
1. **HP is a resource, not a score.** Take calculated damage to deal more. Don't waste energy on block when enemies aren't attacking.
2. **Deck quality > deck size.** Skip card rewards if nothing synergizes. A lean deck draws key cards more often.
3. **Front-load damage.** Killing enemies faster means less total damage taken.
4. **Read intents carefully.** Sleep/Buff = go all-out offense. Attack = balance block and damage. Debuff = usually no damage, offense turn.

### Combat Sequencing (General)
1. Play 0-cost utility/setup cards first.
2. Play skills before attacks when possible — many mechanics reward this order (e.g. Slow debuff on enemies stacks per card played).
3. Play biggest attacks last to benefit from accumulated buffs/debuffs.
4. Check enemy HP — if you can kill this turn, skip blocking entirely.

### Map Pathing
- **Elites** give relics — fight them when healthy (>70% HP).
- **Rest before Boss** — heal if below 80% HP. Boss fights are long and punishing.
- **Unknown nodes** are safer than Elites. Good at medium HP.
- **Shops** — visit with 100+ gold.
- **Deck quality matters more than quantity** — don't add cards just because they're offered.

### Boss Fights
- **Kill the leader, not the minions.** Enemies with "Minion" power flee when their leader dies.
- Use potions aggressively in boss fights — they don't carry between acts.
- Boss fights are wars of attrition. The longer they go, the more enemies scale with Strength buffs.

### Potion Usage
- Don't hoard potions. Dying with full potions is the worst outcome.
- Use permanent-value potions (Fruit Juice = +5 Max HP) early in any combat.
- Use buff potions (Flex Potion) on turns with multiple attacks.

### Common Mistakes
- Blocking when enemies are sleeping/buffing — waste of energy.
- Not checking card indices after playing — indices shift left.
- Taking too long to kill bosses — enemies scale every turn.
- Adding mediocre cards that dilute the deck before boss fights.
