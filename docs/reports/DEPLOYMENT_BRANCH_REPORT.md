# Phase D1 — Deployment Branch Report

Date: 2026-06-14

## Branch

```
git checkout main && git pull origin main --ff-only
git checkout -b deployment/supabase-cloudflare
```

| Item | Value |
|---|---|
| Base branch | `main` |
| Base HEAD | `c45d422d` (Revamp GTEX frontend live experience) |
| New branch | `deployment/supabase-cloudflare` |
| Strategy | Infrastructure-only surgical port (NO feature merge) |

## Why not merge feature/original-visual-runtime?

A full merge of `feature/original-visual-runtime` into `main` produces **200+ conflicts** across auth,
market, trader, wallets, treasury, payment gateways, and the entire frontend (the two branches diverged:
main +20 commits, feature +92). That is unsafe and out of scope. This branch instead **re-creates only the
infrastructure changes** on top of main, touching no business logic.

## Worktree State

Clean except for pre-existing untracked local artifacts (`.runtime/`, generated media, investor-pitch
HTML) that are unrelated to this task and not staged.
