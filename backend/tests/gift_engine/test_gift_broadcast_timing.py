from app.core.events import DomainEvent
from app.realtime.service import RealtimeHub


def test_gift_broadcast_keeps_catalog_duration_and_combo() -> None:
    hub = RealtimeHub()
    dispatches = hub._map_domain_event(
        DomainEvent(
            name="gift_sent",
            payload={
                "match_id": "match-1",
                "gift_key": "whistle_blow",
                "gift_name": "Whistle Blow",
                "duration_ms": 1200,
                "combo_count": 4,
                "sound_key": "whistle_pop",
                "animation_key": "common_whistle",
                "rarity": "common",
            },
        )
    )
    gift = next(item for item in dispatches if item.type == "gift_broadcast")
    assert gift.data["duration_ms"] == 1200
    assert gift.data["combo_count"] == 4
    assert gift.data["sound_key"] == "whistle_pop"
    assert gift.data["gift_code"] == "whistle_blow"


def test_legacy_gift_without_duration_stays_on_the_short_clock() -> None:
    hub = RealtimeHub()
    dispatches = hub._map_domain_event(
        DomainEvent(
            name="match.gift",
            payload={
                "match_id": "match-1",
                "gift_code": "stadium_roar",
                "animation_key": "fan_chant",
                "sound_key": "crowd_roar",
            },
        )
    )
    gift = next(item for item in dispatches if item.type == "gift_broadcast")
    assert gift.data["duration_ms"] == 3000
    assert gift.data["combo_count"] == 1
    assert gift.data["animation_key"] == "fan_chant"
    assert gift.data["sound_key"] == "crowd_roar"
