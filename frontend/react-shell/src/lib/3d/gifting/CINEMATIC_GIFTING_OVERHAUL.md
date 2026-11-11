# GTEX cinematic gifting overhaul — production art and engineering brief

**Status:** implementation brief / acceptance contract. This document does not certify the renderer or assets as complete.

## Objective

Deliver live-gift reveals with the authored, directed impact expected from a premium live-stream product. Each gift must read instantly, feel materially distinct, and survive repeated playback on mobile. The renderer must never disguise a missing asset with primitive geometry or a generic particle-only scene.

## Non-negotiable art direction

- The gift itself is the hero. Use an authored, correctly proportioned GLB/GLTF, licensed pre-rendered clip, or approved high-resolution artwork sequence.
- No cones, spheres, capsules, cylinders, toruses, rings, gems, primitive crowds, or primitive landmarks as gift heroes or substitutes.
- Do not use a mismatched showroom model to represent a city, crown, boot, glove, player card, tactics board, or award.
- Atmosphere (fog, dust, light shafts, reflections, sound and restrained particles) is supporting composition, never the only content for a catalogue gift.
- Every gift has its own staging, camera choreography, lighting plan, timing, impact beat, sound cue and exit. Rarity scales production intensity; it must not merely add more floating decoration.
- Keep the lower-third legible and subordinate to the hero. Respect reduced-motion settings and mobile safe areas.

## Scene language

Every sequence is authored against a shared timeline with named beats:
1. **Anticipation (0–15%)** — establish the world, light and camera intent; avoid dead air.
2. **Entrance (15–38%)** — hero enters or is revealed through a motivated camera move, occlusion, lighting cue or authored animation.
3. **Hero read (38–68%)** — give the audience a clean silhouette and a readable close/medium composition.
4. **Payoff (68–86%)** — unique impact/reveal action and synchronized audio/lighting response.
5. **Exit (86–100%)** — intentional camera settle and clean hand-off to the next live event.

These are timing bands, not a requirement to make every gift move identically. The creative direction must vary by gift family.

## Asset strategy and current gaps

The merged baseline contains authored GLBs for the private jets, yacht, stadium, watch, coach, SUV, hypercar, performance campus, penthouse, trophy plinth and football match assets. It does not currently provide approved matching hero assets for city-specific skylines, dedicated crown, golden boot, goalkeeper glove, player card, tactics board or a dedicated Ballon d'Or trophy.

For each gap, source or create an approved asset with recorded provenance/licence, optimize it for real-time use, and add a matching cinematic sequence. Until then, use a deliberate premium 2D/video treatment built from approved artwork—not a blank atmosphere scene and not a fake 3D primitive. City gifts must use city-specific approved imagery; never relabel a generic building as Paris, Lagos, Dubai, etc.

## Required gift families

| Family | Hero requirement | Signature direction |
|---|---|---|
| City / skyline | Correct city landmark or approved city artwork/video | aerial approach, skyline reveal, landmark hero read |
| Stadium | Authored venue asset or clearly generic GTEX arena | broadcast-style fly-in, bowl reveal, pitch-level payoff |
| Jet | Matching aircraft asset | runway/tarmac reveal, controlled tracking pass |
| Yacht | Matching yacht asset | waterline approach, deck reveal, cinematic wake |
| Coach / vehicle | Matching vehicle | low tracking pass, controlled hero orbit via camera only |
| Facility / campus | Matching campus asset | aerial masterplan reveal, descend to focal building |
| Trophy / Ballon d'Or | Dedicated award asset | isolated hero reveal, material close-up, award moment |
| Watch / crown | Watch for watch; dedicated crown for crown | precision macro reveal; never interchange them |
| Boot / glove | Dedicated boot / glove asset or approved artwork sequence | athlete/product commercial language |
| Player card | Approved player portrait/card artwork | card reveal with portrait fidelity and stats hierarchy |
| Tactics | Approved tactical board / authored graphic | tactical lines and formation reveal, no 3D primitive props |
| Match moments | Existing animated player, ball, goal and stadium assets | clear action, contact, crowd/audio payoff, replay-style exit |

## Runtime architecture requirements

- Build a data-driven scene manifest: gift key, hero asset, environment, camera rail, beat timings, animation, audio cues, rarity grade, fallback and mobile quality profile.
- Asset loading must be cancellable, cached, progress-aware and resilient to missing/failed network requests.
- Missing assets must switch to a declared approved fallback; never silently continue with an empty particle scene.
- Use shared timeline time as the single source of truth for camera, animation, audio, lighting, lower-third and completion.
- Avoid per-frame allocations and unbounded particle counts. Dispose cloned geometry/materials/textures and stop audio/video on cancellation/unmount.
- Keep gameplay, gift purchase, wallet/ledger, payment, send/broadcast and combo contracts unchanged.
- Support WebGL context loss, reduced motion, sound-off, low-tier devices, portrait mobile and narrow landscape.

## Acceptance gates

A gift is not complete because TypeScript compiles or a scene object exists. Each gift must pass:

1. **Asset gate:** correct hero asset/art, provenance and licence recorded; no placeholder or unrelated substitute.
2. **Visual gate:** captured browser recording demonstrates all five beats, legible hero silhouette, correct composition and no clipping/pop-in.
3. **Distinctiveness gate:** side-by-side comparison proves the gift has its own camera/action/lighting/sound language.
4. **Responsive gate:** desktop, tablet, narrow mobile portrait and mobile landscape captures.
5. **Performance gate:** representative low/mid/high device profiles; record load time, frame-time distribution, memory and context-loss behavior.
6. **Accessibility gate:** reduced motion, sound off, captions/labels and safe-area checks.
7. **Regression gate:** existing gift catalogue, purchase/send/broadcast, combo, wallet/ledger and completion callbacks unchanged.
8. **Human art review:** visual reviewer explicitly approves the rendered recordings. Automated tests cannot certify TikTok-level art quality.

## Required evidence in the pull request

- Asset manifest with source, licence, file size, texture budget, triangle budget and compression status.
- One recording per gift family at desktop and mobile sizes.
- Contact sheet of hero, entrance, payoff and exit frames.
- Automated tests for manifest completeness, fallback correctness, cancellation/disposal and event-contract parity.
- Performance report from at least one mid-range Android device and one desktop browser.
- Known gaps listed honestly; no claim of production readiness while a gate is outstanding.

## First implementation milestone

1. Audit every catalogue gift code against the current resolver and asset inventory.
2. Build the manifest and fail tests for unassigned gifts or particle-only fallbacks.
3. Deliver a polished vertical slice for one gift from each materially different family (vehicle, venue, award/product, player/match moment).
4. Run human visual review before scaling the treatment to the rest of the catalogue.
5. Complete the remaining catalogue in quality-controlled batches.
