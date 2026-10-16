# N56 — API v2 Route Collision Hardening Report

## Summary

This document captures the before/after behavior of `register_domain_modules()` in
`backend/app/core/module.py` after the N56 hardening pass.

---

## Previous Behavior

### Collision resolution table (before N56)

| Existing | Incoming | Result |
|---|---|---|
| canonical | alias (`/api/*`) | Drop incoming alias ✓ |
| alias | canonical (`/api/*`) | **Raise ValueError** ✗ |
| alias | alias | Drop incoming alias (first wins) ✓ |
| canonical | canonical (bare path) | Raise ValueError ✓ |

### Why CI previously failed

1. The self-mount fix (N55) explicitly registered `/api/v2/...` routes as *canonical* routes
   from modules with no `router_transform`.  
2. In some orderings, a transform module (alias source) ran first and registered those same
   `/api/v2/...` paths as *aliases* in `app.routes`.  
3. When the canonical module subsequently ran, the collision handler saw
   `existing_is_alias=True, new_is_canonical=True` and **raised**, aborting startup.
4. `_route_fingerprints` also silently ignored `APIWebSocketRoute`, so WebSocket path
   collisions were never detected and could produce duplicate routes.

---

## New Deterministic Behavior

### Collision resolution table (after N56)

| Existing | Incoming | Result |
|---|---|---|
| canonical | alias (`/api/*`) | Drop incoming alias — **canonical wins** ✓ |
| alias | canonical (`/api/*`) | **Evict alias from app, allow canonical** ✓ |
| alias | alias | Drop incoming alias — first alias wins ✓ |
| canonical | canonical (bare path) | Raise ValueError — double-registration bug ✓ |

### Key change: alias eviction

When `existing_is_alias and new_is_canonical`:

```python
to_replace.add(fp)
# After the loop:
_remove_routes_from_app(app, to_replace)  # evicts stale alias from live app.routes
del registered[fp]                         # removes from precedence map
# Canonical route then passes through _drop_colliding_routes unimpeded
```

Canonical routes **always** win over aliases regardless of which module registered first.

### WebSocket route coverage

`_route_fingerprints` now also fingerprints `APIWebSocketRoute`:

```python
elif isinstance(route, APIWebSocketRoute):
    fingerprints.add((route.path, ("WEBSOCKET",)))
```

WebSocket collisions are subject to the same precedence rules and will no longer pass silently.

---

## Examples

### Example 1 — Canonical route wins (happy path, order-independent)

```
Module A (transform) registers /api/v2/auth/login  → stored as alias
Module B (canonical) registers /api/v2/auth/login  → alias evicted, canonical installed
Result: /api/v2/auth/login is canonical ✓
```

### Example 2 — Alias route discarded (canonical already present)

```
Module B (canonical) registers /api/v2/federations  → stored as canonical
Module A (transform) registers /api/v2/federations  → alias dropped by _drop_colliding_routes
Result: /api/v2/federations is canonical ✓
```

### Example 3 — Bare collision raises

```
Module X registers /market/foo  (no transform) → stored as canonical
Module Y registers /market/foo  (no transform) → _is_alias_path returns False → fatal set
Result: ValueError raised ✓
```

---

## Why Canonical Precedence Is Safer

1. **Determinism** — outcome is the same regardless of DOMAIN_MODULES ordering; ordering
   bugs no longer cause production startup failures.
2. **Correctness** — hand-authored (canonical) routes carry the full middleware stack,
   dependency injection, and response model annotations. Alias routes are lightweight
   re-exports and should never override them.
3. **CI stability** — the CI environment may resolve import order differently from local
   dev. With canonical-always-wins the output is identical in both environments.
4. **WebSocket safety** — the prior `_route_fingerprints` only scanned `APIRoute`, so
   a WebSocket path could silently collide and produce two handlers on the same path.
   Now both HTTP and WebSocket paths are fully tracked.
