# Parallel Building With Codex

Yes, you can build this in parallel.

OpenAI's official Codex materials say the Codex app supports multiple agents in parallel with isolated worktrees, and Codex cloud can also run tasks in parallel in the background.

## Best 4-way split
### Thread A
Backend foundation:
- auth
- users
- wallets
- teams
- models

### Thread B
Data + value engine:
- Sportmonks
- fallback API
- value engine
- events

### Thread C
Market engine:
- listings
- offers
- swaps
- auctions
- trade settlement

### Thread D
Flutter UI:
- screens
- navigation
- layout

## Important
Do not let multiple threads edit the same money / ownership / migration files at the same time.

## Best merge order
1. Thread A
2. Thread B
3. Thread C
4. Thread D

## Best starter advice
Run 3 threads first:
- backend core
- market engine
- Flutter UI

Then start data/value engine once schema is stable.
