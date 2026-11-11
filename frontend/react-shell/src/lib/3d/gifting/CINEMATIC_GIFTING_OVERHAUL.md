# GTEX cinematic gifting overhaul

**Status:** draft implementation and acceptance contract. This document does not certify the renderer or assets as complete.

## Art direction

Every gift should read as a distinct broadcast moment, not a floating catalogue icon. The five beats are anticipation, entrance, hero read, payoff and clean exit. The visual target is a premium live-event film integrated into the match broadcast, with authored hero assets, precise timing and restrained lower-thirds.

## Supplied cinematic films

The current main branch already contains the 20 project-owner-supplied H.264 films under `frontend/react-shell/public/assets/gifting/films/`. The renderer uses `giftConceptFilms.ts` and the shared `ShowroomInspectionReel` component; no duplicate asset upload or manual copy step is required.

The film path is `/assets/gifting/films/<filename>`. The clips are muted and inline; GTEX celebration audio, captions, sender/recipient identity, rarity and combo display remain separate. The Maracanã film must not be used for Wembley, San Siro, Camp Nou or golden-stadium gifts. A matching showroom inspection reel takes priority for items such as jets, vehicles, yachts and the Chronos watch.

If an inspection film fails, the engine tries the matching gift concept film. If that also fails, the film layer is removed and the underlying WebGL scene remains visible. Reduced-motion users stay on the non-video path.

## Authored WebGL scenes

The existing GLB assets remain the WebGL hero/fallback for gifts without a matching inspection reel or concept film. Imported models use controlled entrance/settle choreography on their wrapper groups without altering source mesh topology.

Do not use cones, spheres, toruses, capsules or generic geometry as substitutes for a crown, boot, goalkeeper glove, player card, tactics board, landmark or award. Do not pass a generic penthouse or stadium asset off as a specific city or venue.

## Acceptance gates

1. Every clip resolves only for the correct gift family.
2. Video playback is muted, inline, responsive and gracefully falls back to WebGL.
3. The Chronos watch retains its matching authored watch reel/GLB, not the crown clip.
4. Desktop, tablet and mobile recordings are visually reviewed against the supplied references.
5. A mid-range Android device is profiled for decode performance, bandwidth, memory and resource release.
6. Reduced motion, sound-off, captions and safe-area behavior remain correct.
7. Gift purchase, wallet/ledger, payment, send/broadcast and combo contracts remain unchanged.
8. Provenance/distribution rights are documented before public release.

Automated tests and successful builds are not a substitute for human art review or device profiling.
