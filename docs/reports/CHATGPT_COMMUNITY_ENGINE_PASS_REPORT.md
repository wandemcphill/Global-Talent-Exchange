# ChatGPT Community Engine Pass Report

This pass added a new community engine to push GTEX further toward a living spectator platform rather than a silent spreadsheet with studs.

## Added
- competition watchlists
- live threads
- live thread messages with lightweight review visibility
- private message threads
- private message participants
- private messages
- community digest endpoint

## New router prefix
- `/community`

## New endpoints
- `GET /community/digest`
- `GET /community/watchlist`
- `POST /community/watchlist`
- `DELETE /community/watchlist/{competition_key}`
- `GET /community/live-threads`
- `POST /community/live-threads`
- `GET /community/live-threads/{thread_id}`
- `GET /community/live-threads/{thread_id}/messages`
- `POST /community/live-threads/{thread_id}/messages`
- `GET /community/private-messages/threads`
- `POST /community/private-messages/threads`
- `GET /community/private-messages/threads/{thread_id}`
- `GET /community/private-messages/threads/{thread_id}/messages`
- `POST /community/private-messages/threads/{thread_id}/messages`

## Notes
- Live thread messages containing risk phrases are marked `mod_review` instead of immediately public.
- This pass focused on backend persistence and API surfaces. Full Flutter wiring remains open.
