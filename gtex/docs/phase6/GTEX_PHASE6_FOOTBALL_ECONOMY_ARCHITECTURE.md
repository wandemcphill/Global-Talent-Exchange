# GTEX Phase 6 Football Economy Architecture

Status: Foundation contract

Starting main: `1530b36eb4cb0a1b9d65180ec16e31b659d8da09`

This document defines the product and engineering boundaries for the next GTEX evolution. It is deliberately foundational. It does not replace or rewrite the Phase 5 trading architecture and it does not authorize production database writes while the production database remains read-only.

## 1. Non-negotiable preservation rules

Phase 6 must preserve the existing platform unless a later PR explicitly changes a contract:

- System A remains the canonical real-player share ownership and trading system.
- `PlayerShareHolding` remains the canonical real-player share ownership record.
- `PlayerShareMarket.share_price_coin` remains the tradable player-share price.
- PRICE != VALUE remains absolute. Football valuation may not silently become tradable price.
- Matchday must not write `share_price_coin`.
- Admin is a market governor, not a buyer of last resort. Admin buyback remains retired.
- Fan Coin and GTEX Coin remain the only two GTEX currencies.
- No coin conversion mechanism is introduced.
- Fan Coin funds regen/staff salaries and facility investment.
- GTEX Coin funds player and regen transfers.
- Unknown data remains unknown. It must not be rendered as zero, a default price, or fabricated social proof.
- The canonical player card, canonical player detail, navigation shell and router remain single-source surfaces. Phase 6 must not create parallel implementations.
- Backend owns business logic and economic rules. Flutter consumes published contracts/models.

## 2. Real-player universe

Real players are a GTEX historical universe, not a continuously mirrored copy of real-world football.

Lifecycle:

`SportMonks ingest -> publish -> automatic market issuance -> released supply -> discoverable roster -> trading -> optional governed additional supply`

The initial SportMonks import establishes the real-player corpus. Normal operation must not automatically reshuffle squads because of promotions, relegations, transfers, or later real-world squad changes. Existing GTEX player identities and user-owned assets are stable historical objects.

New real players, clubs, competitions, and corrections can be introduced later through explicit admin operations.

## 3. Real-player share supply

A real player has one canonical player identity and one active player-share market.

Initial supply is limited. Example UX may communicate `owned / released`, but the semantic label must make clear that the denominator is currently released supply, not necessarily lifetime supply.

When released supply is exhausted:

- the player remains searchable;
- the player remains a valid historical GTEX asset;
- existing holders may trade through the normal market path;
- new primary supply is unavailable until the governor deliberately releases more.

Additional supply increases the existing market's released supply. It must not create a duplicate player record or a second active market.

Automatic issuance is a first-class operational process. It must be idempotent, explicit, and decoupled from the ingestion job so issuance can be run independently when ingestion is healthy and when the database is write-capable.

The strict issuer path remains the authority for issuance provenance. Ordinary reads and ordinary trades must never become hidden market-issuance mechanisms.

## 4. Player states

The product should be able to distinguish these states without guessing:

- `searchable_only`: player exists in the GTEX universe but has no usable market.
- `market_pending`: player is eligible and awaiting issuance.
- `market_active`: player has released supply and can accept primary purchases.
- `trade_only`: released supply is exhausted but the player remains tradable among existing holders.
- `market_blocked`: an integrity, eligibility, compliance, or manual block prevents market activity.

These states are product semantics. Exact API enum names may follow the existing codebase naming convention in the implementation PR.

## 5. Regen identity

Regens/newgens are GTEX-native football identities. They are not fractionalized real-player shares.

A regen is unique and individually scarce. A regen can therefore carry a much stronger scarcity premium than a real player of the same GSI.

The economic model must separate:

- GSI / quality band
- gameplay capability
- potential
- development state
- uniqueness/scarcity
- current market value
- career history
- club legacy

GSI must not be used as a direct gameplay multiplier. A developed regen can become more influential in matches and more valuable economically than a real player with the same GSI, but this must come from the separate capability/development model rather than a hidden multiplication factor.

## 6. Regen career clock

A regen career is governed by GTEX seasons, not by a fixed real-time retirement timer.

The system must eventually support:

- virtual date of birth;
- virtual age;
- GTEX season count;
- active career seasons;
- career stage;
- development history;
- retirement pressure;
- retirement decision;
- retirement season;
- legacy state.

The exact GTEX-season-to-virtual-age conversion is intentionally **TBD** and must be decided before a production migration. We must not silently hard-code a ratio such as 10 seasons per virtual year until the rule is approved.

Retirement pressure must be multi-factor and probabilistic rather than a fixed lifespan. It should consider, as available data permits:

- virtual age;
- position longevity profile;
- injuries and recovery burden;
- playing time;
- performance trajectory;
- contract quality and renewal opportunity;
- market demand;
- salary burden;
- personality traits;
- achievements and reputation;
- club role and opportunities;
- the player's willingness to continue.

Position may influence longevity statistically, with goalkeepers and defenders generally having more runway than some attacking roles, while exceptional careers can break the normal pattern. No deterministic nationality stereotype or fixed position retirement rule is permitted.

## 7. Regen gameplay and development

Academy quality, recruitment, coaching, training, medical capability, club context, development minutes, personality and controlled randomness jointly influence regen growth.

A regen should be able to move through a career such as:

`generated -> academy prospect -> senior player -> developed star -> club legend -> retired legacy`

Development must be auditable. Important state changes should have structured history rather than only overwriting a current rating.

Real-player live form and automatic squad reshuffling are not required by this phase. The real-player side remains primarily admin-governed while the regen world becomes the deeper living ecosystem.

## 8. Retirement and legacy

Retirement must not strand the owner's identity or history.

A retired regen remains permanently available as a Legacy Regen Card containing, as data exists:

- career history;
- peak GSI and peak ability;
- peak value;
- clubs and transfers;
- trophies and awards;
- personality/history;
- development timeline;
- career earnings;
- retirement season;
- legacy classification.

The retired player stops participating in normal match and market flows, but the record remains collectible and historically meaningful.

Retirement can trigger an academy legacy intake for the player's club. This creates a new generation opportunity, not a clone. Exceptional retirees may create a higher probability or quality floor for the intake, and in rare circumstances may create two exceptional prospects. Exact probabilities and guardrails must be specified before implementation.

Legacy effects must avoid infinite guaranteed compounding. A temporary legacy window is preferred over a permanent guaranteed-success multiplier.

## 9. Living regen interactions

Regens should have structured football-life events rather than a generic conversational AI layer pretending to be a person.

Initial event vocabulary may include:

- bigger-role request;
- playing-time concern;
- position preference;
- renewal request;
- challenge request;
- injury/rehab state;
- coach-ready assessment;
- transfer interest;
- development surge;
- retirement watch.

Each event must have an identifiable domain owner and a deterministic/evaluable rule set. AI may help phrase an event, but AI must not become the authoritative economic state machine.

## 10. Clubs, staff and personnel

Use the existing club staff system as the foundation. The current data model already separates staff profiles, contracts, and club assignments. It must be extended rather than replaced.

The conceptual model is:

- **Staff Person**: one unique individual.
- **Specialisation**: what the person is qualified to do.
- **Club Appointment**: the job/role they hold at a club.

Manager is a club appointment for first-team leadership, not a mandatory separate economic person type.

A coach can become a manager. A club can:

- promote a youth/academy coach into first-team manager;
- hire a coach from another club as manager;
- hire other qualified staff;
- replace staff subject to contract and scarcity rules.

Each unique staff person has one share. Scarcity is therefore real and must be respected by the marketplace and appointment system.

Retired regens may enter staff careers, but role qualification must be explicit. A retired footballer may become a coach or manager through a defined pathway. Medical roles require medical qualification/training and must never be granted solely because a player retired.

## 11. Staff economics

Staff draw Fan Coin salaries according to their active contracts, except personal managers described below.

Existing `ClubStaffProfile`, `ClubStaffContract`, and `ClubStaffAssignment` should remain the canonical staff records. Current seeded staff already demonstrate salary-bearing personnel, so Phase 6 should extend the existing salary path rather than invent a parallel payroll system.

Exact salary bands, transfer prices, and progression rules are **TBD** where not already represented by an existing contract.

## 12. Personal manager

Each GTEX profile may create exactly one personal manager identity.

The personal manager is:

- permanent;
- non-transferable;
- tied to the user's GTEX profile;
- not a market staff share;
- not a salaried club employee;
- created only once.

Creation is a one-time Fan Coin platform/admin payment. The user selects a quality band:

- 60-70
- 71-80
- 81-90
- 91-95
- 96-99

The exact Fan Coin price table is **TBD** and must be approved before implementation. Higher bands must cost materially more, with the 96-99 band intentionally expensive.

The personal manager should have configurable football identity, including tactics, formations, mentality, playing style and youth philosophy, while the underlying quality band remains immutable unless a later upgrade mechanism is explicitly introduced.

## 13. Club academy and facilities

Reuse the existing academy and club-growth foundations. Do not build a second academy system.

Facilities are long-term Fan Coin investments and should improve the club through progressive levels rather than instant maximum upgrades.

Candidate tracks include:

- Academy;
- Training Centre;
- Medical Centre;
- Coaching Staff;
- Youth Recruitment;
- Facilities & Equipment;
- Club Reputation;
- Club Culture.

Existing `AcademyProfile`, `AcademyProspect`, training plans, promotion history and generation runs remain part of the canonical academy pipeline.

Facility upgrade cost curves and build durations are **TBD**. The final implementation must define escalating cost and season-based completion before production migration.

## 14. Coaches and development influence

Coaching quality is a first-class part of the regen economy.

Youth/academy coaches should influence, as supported by the published model:

- prospect quality;
- potential recognition;
- positional development;
- technical/physical/mental growth;
- development speed;
- personality development;
- late-bloomer identification.

The first-team manager should influence:

- promotion decisions;
- competitive minutes;
- tactical role;
- position used;
- morale;
- renewal and career continuity.

These effects must live in backend domain services and published contracts. Flutter must not reproduce the formulas.

## 15. Medical ecosystem

Medical personnel are part of the club staff economy and draw Fan Coin salary.

The medical system should influence injury prevention, recovery, rehabilitation and career longevity within defensible limits. It must not guarantee injury-free careers.

Medical personnel who are retired regens require an explicit qualification pathway before appointment.

## 16. Production safety rule

The production database is currently read-only. Therefore:

- Phase 6 code and tests may be developed now.
- Read-only audits may continue.
- No migration, issuance, seed, repair, or backfill may be executed in production until write access is restored and explicitly verified.
- Production readiness must be evidenced with real runs after writes return. No code change may be used to disguise a write failure.

## 17. Phase 6 implementation order

### 6A. Foundation contract and state model

Lock the contracts for:

- regen career state;
- season clock;
- staff person/specialisation/appointment;
- personal manager identity;
- player market lifecycle states;
- academy/facility progression boundaries.

Acceptance: models/schemas/tests define the vocabulary without changing existing trading economics.

### 6B. Automatic real-player market issuance

Decouple market issuance from successful ingestion. Build an idempotent issuance job using the strict issuer and existing provenance model.

Acceptance:

- no duplicate market per player;
- explicit issuance provenance;
- ordinary reads do not issue;
- eligible players progress toward `market_active`;
- blocked players are reported with a reason;
- production execution is deferred until the database is writable.

### 6C. Regen career engine

Introduce the GTEX-season career clock, dynamic retirement pressure, contract opportunity, injuries, development state and retirement transition. Preserve Legacy Regen Card history.

Acceptance: deterministic tests cover normal career progression, injury pressure, renewal pressure, exceptional extension, retirement and legacy preservation.

### 6D. Staff and manager ecosystem

Extend the current club-growth staff system to support specialisation and appointments, manager promotion/hiring, unique staff scarcity, staff salary and qualified regen-to-staff transitions.

Acceptance: one unique staff person cannot be simultaneously held by conflicting exclusive clubs; role assignments remain auditable; manager appointment is one canonical appointment, not a second person asset.

### 6E. Academy and facilities economy

Wire Academy, Training, Medical and Youth Recruitment progression to Fan Coin with season-based completion and escalating investment.

Acceptance: costs are posted through the existing ledger/wallet architecture, upgrades are idempotent, and the same club-growth records remain authoritative.

### 6F. Personal manager creation

Add the one-per-profile personal manager identity and the approved quality-band Fan Coin creation price table.

Acceptance: exactly one personal manager per profile; non-transferable; no salary; quality band selected at purchase; payment is settled through the existing Fan Coin economy.

## 18. Explicit non-goals for Phase 6

Do not:

- add coin conversion;
- replace Fan Coin or GTEX Coin;
- reintroduce System B player-share trading;
- reintroduce admin buyback;
- create a second player card or player detail;
- create a second academy system;
- add automatic real-world squad reshuffling;
- make matchday a direct writer of tradable player-share price;
- invent live data where the backend has no evidence;
- execute production database writes while the database is read-only.

## 19. Definition of done for the foundation

The foundation is complete when the Phase 6 contracts are merged in PR form, the existing Phase 5 economic invariants still pass, no router/shell architecture has been duplicated, and the implementation sequence above can proceed in isolated, auditable PRs.
