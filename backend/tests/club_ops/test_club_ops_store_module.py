from __future__ import annotations

from app.services.club_ops_store import (
    ClubOpsPersistenceLock,
    ClubOpsStore,
    get_club_ops_store,
)


def test_club_ops_store_module_exports() -> None:
    store = get_club_ops_store()
    assert isinstance(store, ClubOpsStore)
    assert store.session_factory is not None
    assert isinstance(store.lock, ClubOpsPersistenceLock)


def test_club_ops_store_thread_safe_access() -> None:
    store = ClubOpsStore()
    assert isinstance(store.lock, ClubOpsPersistenceLock)
    with store.lock:
        store.accounts_by_club["test-club"] = {}
        assert "test-club" in store.accounts_by_club
