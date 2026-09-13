# Academy Promotion Invariant

An accepted academy contract must be promotable only after the prospect is youth-signed.

Promotion must leave:
- one canonical senior `Player` identity
- one active `PlayerContract` for the owning club
- `current_club_profile_id` aligned to that club
- appropriate squad-tier membership
- an idempotent promotion history row

Promotion must not silently create duplicate `Player` rows or leave an accepted youth contract disconnected from the senior lifecycle.