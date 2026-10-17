from datetime import datetime, timedelta, timezone

from app.owner_console import alerts
from app.owner_console.models import OwnerInboxItem


def _item(kind: str, created: datetime, actions=None, is_decision=True) -> OwnerInboxItem:
    return OwnerInboxItem(user_id="u1", club_id="c1", kind=kind, sender="s", title="t", what="w", why="y",
                          actions_json=actions or [], payload_json={}, is_decision=is_decision, created_at=created)


def test_response_windows_by_kind():
    assert alerts.response_hours("transfer_bid") == 48
    assert alerts.response_hours("regen_breakthrough") == 72
    assert alerts.response_hours("sponsor_opportunity") == 72
    assert alerts.response_hours("competition_invite") == 24
    assert alerts.response_hours("manager_meeting") == 96


def test_respond_by_uses_created_at_after_rollout():
    created = alerts.CLOCK_START + timedelta(days=2)
    assert alerts.respond_by(_item("transfer_bid", created)) == created + timedelta(hours=48)


def test_legacy_decisions_get_fresh_clock_from_rollout():
    old = alerts.CLOCK_START - timedelta(days=30)
    assert alerts.respond_by(_item("competition_invite", old)) == alerts.CLOCK_START + timedelta(hours=24)


def test_non_decisions_have_no_deadline():
    assert alerts.respond_by(_item("decision_expired", alerts.CLOCK_START, is_decision=False)) is None


def test_expiry_action_picks_safe_default():
    actions = [{"key": "accept", "label": "Accept bid"}, {"key": "reject", "label": "Reject"}]
    assert alerts.expiry_action(_item("transfer_bid", alerts.CLOCK_START, actions))["key"] == "reject"
    contract = [{"key": "new_contract", "label": "Offer"}, {"key": "acknowledge", "label": "Acknowledge"}]
    assert alerts.expiry_action(_item("regen_breakthrough", alerts.CLOCK_START, contract))["key"] == "acknowledge"
    unknown = [{"key": "go", "label": "Go"}, {"key": "skip", "label": "Skip"}]
    assert alerts.expiry_action(_item("brand_new_kind", alerts.CLOCK_START, unknown))["key"] == "skip"


def test_warning_marks_item_once():
    created = datetime.now(timezone.utc)
    item = _item("transfer_bid", created, [{"key": "reject", "label": "Reject"}])

    class FakeSession:
        added: list = []

        def add(self, obj):
            self.added.append(obj)

    session = FakeSession()
    alerts.warn_decision(session, item, created + timedelta(hours=48))
    assert item.payload_json["expiry_warned"] is True
    note = session.added[0]
    assert note.kind == "decision_expiring" and note.is_decision is False and "Reject" in note.what
