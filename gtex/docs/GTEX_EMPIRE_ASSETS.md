# GTEX Empire Assets

Controlling ownership, paid coaches, and sister-club groups.

## Caps

- One user may own at most **3** clubs (`MAX_OWNED_CLUBS`).
- Ownership groups are capped at the same **3** clubs.
- Token/DAO shareholdings are a separate domain and do not count toward the cap.

## Coaches

- Catalog managers recruit for Fan Coin (`recruit_price_fancoin`).
- Catalog also exposes `annual_wage_fancoin` and `manager_impact` (1–99).
- Match team factory reads `manager_impact` into dugout authority.

## Club switcher

- `GET /api/clubs/owned` — empire roster
- `POST /api/clubs/owned/{club_id}/activate` — primary membership
- Flutter: `GtexEmpireClubWorkspace` on the Club lane

## Regen approach loop

- Submit: `POST /api/players/{id}/regen/contract-offers/submit`
- Inbox: `GET /api/regen/contract-offers/inbox` (real `RegenContractOffer` rows)
- Resolve: `POST /api/transfers/windows/{window}/players/{id}/resolve-regen-bid` (buying club owner or admin)

## Transfer desk

- Canonical route: `/football/transfer-center` (and `/app/transfer-hub` alias)
- Competitions mark same-group fixtures with `ownership_integrity.review_required`
