# GTEX cinematic gift video pack — installation and verification

The project-owner-supplied MP4 pack contains 20 gift-specific clips. The renderer maps them to `/assets/gifting/<filename>`; the files must therefore be installed under:

`frontend/react-shell/public/assets/gifting/`

## Install

Download the companion archive `gtex-gift-video-assets.zip`, then from the repository root run:

```bash
python3 tools/install_gtex_gift_video_assets.py /path/to/gtex-gift-video-assets.zip
```

To verify the archive without writing files:

```bash
python3 tools/install_gtex_gift_video_assets.py /path/to/gtex-gift-video-assets.zip --dry-run
```

The installer checks that all 20 files are present exactly once, validates each expected byte size and SHA-256, rejects unsafe archive paths, and only then writes the MP4s. Existing matching files are kept. Existing files with different content require the explicit `--force` flag.

## Media profile

All clips are 1280×720 H.264 MP4, 24 fps, approximately 8.04 seconds, muted, and prepared with fast-start metadata. Gift celebration audio and on-screen labels are handled separately by GTEX. Video failure or missing files falls back to the existing WebGL scene. Reduced-motion users stay on the non-video path.

## Clip-to-gift mapping

| Gift family | File |
| --- | --- |
| Atmosphere | `gtex-gift-atmosphere.mp4` |
| Bicycle kick | `gtex-gift-bicycle.mp4` |
| Golden boot | `gtex-gift-boot.mp4` |
| Performance campus | `gtex-gift-campus.mp4` |
| Player card | `gtex-gift-card.mp4` |
| City / skyline (generic city visual) | `gtex-gift-city.mp4` |
| Team coach | `gtex-gift-coach.mp4` |
| Crown (not Chronos watch) | `gtex-gift-crown.mp4` |
| Goalkeeper glove | `gtex-gift-glove.mp4` |
| Goal celebration | `gtex-gift-goal.mp4` |
| Golden goal | `gtex-gift-golden-goal.mp4` |
| Hat trick | `gtex-gift-hat-trick.mp4` |
| Hypercar | `gtex-gift-hypercar.mp4` |
| Private jet | `gtex-gift-jet.mp4` |
| Last-minute winner | `gtex-gift-last-minute.mp4` |
| Goalkeeper save | `gtex-gift-save.mp4` |
| Tactics | `gtex-gift-tactics.mp4` |
| Trophy | `gtex-gift-trophy.mp4` |
| Yacht | `gtex-gift-yacht.mp4` |
| Maracanã | `gtex-maracana-gift.mp4` |

Generic stadium and golden-stadium gifts remain on their matching WebGL scene rather than using a clip for a different venue. The Chronos watch remains on its matching authored 3D asset.

## Provenance and release note

The source clips were supplied by the project owner in this conversation on 11 November 2026. No generating-tool record or licence statement accompanied them. The hashes in the installer are integrity checks, not licence claims. Confirm distribution rights before releasing the videos outside the project.
