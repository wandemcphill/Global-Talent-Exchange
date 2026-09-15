# GTEX Full User Journey Acceptance Pass

## Purpose

This acceptance journey provisions six authenticated test users and follows one cross-domain lifecycle through the canonical GTEX APIs.

## Test actors

| Actor | Purpose | Initial test balances |
|---|---|---|
| Journey Owner | Primary club owner, competition player, regen creator, Jackpot winner, gift sender | 5,000 Fan Coin + 10,000 GTEX Coin |
| Journey Trader | Coin Trader and real-player seller | 500 Fan Coin + 100,000 GTEX Coin |
| Journey Peer | Joins the owner-hosted competition | 5,000 Fan Coin + 5,000 GTEX Coin |
| Journey Recipient | Gift recipient and owner of the recipient club context | 2,500 Fan Coin + 2,500 GTEX Coin |
| Journey Buyer | Coin Trader buyer and later player buyer | 5,000 Fan Coin + 100,000 GTEX Coin |
| Journey Club Buyer | Regen buyer and club seller | 5,000 Fan Coin + 200,000 GTEX Coin |

The implementation uses the existing `auth_user_factory`, whose fixture calls the real `/auth/signup/user` endpoint and therefore exercises registration, user-id issuance, and the normal signup-created club profile.

## Journey sequence

The acceptance runner also certifies the canonical API contract used by this journey.
