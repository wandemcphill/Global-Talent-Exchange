# GTEX Local Release Certification

GitHub Actions may be temporarily unavailable because of repository quota exhaustion. This does not remove the need for a repeatable release gate.

## Command

From the repository root:

```bash
python tools/audit/gtex_release_certification.py
```

The runner executes the read-only production/release audits already maintained by the repository:

- reality/config integrity
- player-share release integrity
- player-share lifecycle integrity
- player-share trade-boundary integrity
- player-share API contract integrity

It also records the current Git branch, commit SHA, and working-tree cleanliness.

## Exit semantics

- `0`: every included local audit passed.
- `1`: at least one audit failed or timed out.

The command deliberately does **not** claim hosted CI, live database, payment-provider, or Unity certification. Those remain separate gates.

## When GitHub Actions is unavailable

Use this runner as the repeatable local/static gate, then record the missing hosted gates explicitly:

1. GitHub Actions suite
2. fresh production-like database migration replay
3. real KoraPay transaction and webhook settlement
4. staging/live player-market corpus verification
5. Unity licensed batch build

A green local certification therefore means **locally certified for the included checks**, not universally production certified.
