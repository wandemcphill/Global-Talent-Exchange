# Quick Commands and Workflow

## First thing to tell Codex
"Read every file in this ZIP first.
Use `15_CODEX_MASTER_PROMPT.md` as the governing instruction.
Do not invent new business rules.
Start with Stage 1 only."

## After every stage ask
1. What files changed?
2. What tests pass?
3. What still needs work?
4. What should I review now?

## Safe workflow
- finish one stage
- run tests
- review files
- only then move on

## Parallel work
Use separate Codex threads for:
- backend core
- market engine
- Flutter UI

Do not let multiple threads edit the same core financial files at once.
