# GTEX Living Star Regens

Regens are unique living footballers. Real players are permanent share assets.

## Asset law

| | Real players | Regens |
|---|---|---|
| Supply | Many share listings | **1 OF 1** |
| Ownership | Permanent | Career can end |
| Salary | None on GTEX | FanCoin wage |
| Contract clock | None | Yes — can demand exit |

## Closed loop (shipped)

1. **Archetype** — derived from `PlayerPersonality` (Mercenary, One-Club Romantic, Big-Game Ghost, Clutch Animal, Dressing-Room Bomb, Media Hurricane).
2. **Mood** — Settled / Watching / Restless / Explosive from `PlayerAgencyState`.
3. **Inner monologue** — daily seeded first-person line on the dossier.
4. **Exit ladder** — settled → quiet discontent → formal request → training exile → termination petition → force-sale window.
5. **Promise memory** — surfaces `promise_memory_json` / unmet expectations.
6. **Match BehaviorBrief** — `GET /api/players/{id}/behavior-brief` → Unity `GtexRegenBehaviorBrief` / `GtexVisualIntentDirector`.
7. **Heir spark** — retirement academy bridge stamps `inherited_personality_fragment` on successors (`GTE_REGEN_LEGACY_INTAKE_ENABLED=1` to mint).

## API

- `GET /api/players/{player_id}/living-star`
- `GET /api/players/{player_id}/behavior-brief`
- `POST /api/players/{player_id}/agency/exit-petition` (auth)

## Frontend

- Dossier **Living star** panel (voice, mood, exit, promises, match temperament)
- Ownership **Escalate exit pressure**
- Regen World contract board populated from living-star exit pressure
- Player cards: salary/contract only on regen variants; **1 OF 1** for all non-seed regens
