#!/usr/bin/env python
try:
    print("SUCCESS: Import works")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
