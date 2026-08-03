# Gameplay Operation And Learning Contract

## Manual-first boundary

- Default to manual MCP/state-driven decisions. Do not run or publish an autoplay script unless
  the user explicitly opts in for that run or publication.
- For gameplay, reviews and strategy questions, use the `sts2-gameplay-learning` skill and record
  compact reusable run facts in its local learning store. Do not commit private run history here.

## Safe state/action loop

- Use JSON state during combat and Markdown for map/event overviews.
- After ending a turn, poll state again until the player phase is visible; one response may only
  represent the enemy transition.
- Card and reward arrays re-index after a selection. Re-read state between operations or consume
  planned indices from highest to lowest.
- Single-target cards require the current entity id. Do not reuse an id or index from stale state.
- Potions use potion-slot indices and do not consume energy; confirm the current slot before use or
  discard.
- Events, rest sites and reward sub-screens often require a follow-up proceed/confirm action. Read
  the returned state instead of assuming the screen closed.

## Strategy is advisory

HP, deck size, pathing, potion use and combat sequencing guidance are heuristics, not API
contracts. Re-evaluate them against the current run, enemy intents, relics and card text. Preserve
observed facts separately from recommendations so later learning does not turn one run's tactic
into a false universal rule.
