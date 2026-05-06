# Pre-Deletion Validation

## Status

**STOP** - destructive cleanup is not yet safe.

Frontend references and route mismatches still remain, especially around the shared Flutter repository and legacy `/api/v1` usage.

- Blocking mismatches: **768**
- Pending legacy route migrations: **176**
- Required next move: migrate remaining consumers onto the canonical routes in `FINAL_API_SCHEMA.json`, then re-scan.
