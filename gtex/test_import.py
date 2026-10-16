#!/usr/bin/env python
import sys
try:
    from backend.app.leagues.service import LeagueSeasonLifecycleService
    print("SUCCESS: Import works")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
