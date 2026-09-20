# GTEX visual language

## What GTEX should feel like

GTEX is a football universe where a user's identity, club, owned players,
competitive position, and next decision meet. The interface should feel like a
personal football command surface, not a generic finance dashboard or an
imitation of an existing football game.

## Principles

1. **Identity before inventory.** A manager or club is visible before their
   balance, cards, or settings.
2. **The next football decision is primary.** Matchday, competition entry,
   market review, and club readiness get an explicit path; secondary admin
   data does not compete with them.
3. **Ownership is tangible.** Owned players, club stakes, ranks, and rewards
   use distinct semantic cues instead of a single generic success green.
4. **Prestige is earned, not decorative.** Honors, rank, and reward surfaces
   use restrained warm metallic emphasis and only appear when data supports
   them.
5. **Truth is part of the visual system.** Loading, quiet, locked, and absent
   states say exactly what the product knows. Fixtures are labelled and never
   leak into live paths.

## Command Center exploration

| Direction | Composition | Strength | Rejected because |
| --- | --- | --- | --- |
| A — Matchday Pulse | One immediate fixture/decision leads; competition and readiness form the rail. | Fast comprehension and football energy. | Can under-represent long-term ownership between fixtures. |
| B — Club Atlas | Crest, legacy, academy, and prestige lead. | Strongest club-builder identity. | Urgent competition and market decisions become secondary. |
| C — Ownership Ledger | Positions, value movement, bids, and rank lead. | Excellent collector/trader clarity. | Risks making GTEX feel transactional rather than football-first. |

## Selected direction

The production Command Center uses **Matchday Pulse as the hierarchy**, with
the identity clarity of Club Atlas and the high-signal metrics of Ownership
Ledger. This means the masthead introduces the person or club, names the next
goal, offers two direct actions, then exposes real capital, market,
competition, and task signals. Existing live modules continue to provide the
deeper world, market, rewards, and ownership detail.

## Responsive behaviour

- **390px:** identity leads, primary actions wrap, and command metrics become
  one-column readable cards. Secondary content stays below the first decision.
- **768px:** metrics become a two-column rail; focus cards remain vertically
  scannable.
- **1440px:** identity sits beside the narrative and metrics use four columns;
  the rest of Home retains its existing multi-rail data composition.

The Design Lab's three directions are deliberately distinct compositions, not
colour variations. Its fixtures are isolated under `frontend/lib/design_lab/`.
