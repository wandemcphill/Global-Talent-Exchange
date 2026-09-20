# GTEX design system — Command Center extension

GTEX already has the canonical `GtexColors`, `GtexSpacing`, `GtexText`,
`GtexPanel`, `GtexActionButton`, and player-card primitives. Slice 3 extends
them; it does not replace equivalent working components.

## New semantic tokens

`GtexCommandTokens` adds:

| Token | Meaning |
| --- | --- |
| `pitch` / `live` | active football and matchday state |
| `competition` | competitions and table context |
| `ownership` | owned players, clubs, and collection state |
| `coin` | market value and economic opportunity |
| `prestige` | rank, legacy, honors |
| `reward` | claimable/earned reward state |
| `pending`, `settled`, `risk` | semantic status, never decorative accents |

The extension also defines one action height, compact action height, shared icon
sizes, and Command Center radii. Base spacing and typography continue to come
from `GtexSpacing` and `GtexText`.

## New reusable primitives

- `GtexCommandCenterMasthead`: identity, current objective, direct actions,
  and a responsive metric rail.
- `GtexCommandAction`: command-surface action sizing wrapped around the
  existing `GtexActionButton` behaviour.
- `GtexCommandFocusTile`: a touch-safe, semantic next-decision tile.

All are exported from `ui_gtex.dart`. Use them when a surface needs a clear
identity → decision → signal hierarchy; use existing `GtexPanel` and
`GtexActionButton` for ordinary local UI.

## State rules

- A live metric uses a backend-backed value only.
- `Loading`, `Locked`, and `Quiet` are explicit states, not invented zeros.
- Rewards and trophies are shown only where the underlying product has them.
- Design Lab fixture values must remain within `frontend/lib/design_lab/` and
must visibly carry the isolated-fixture label.
