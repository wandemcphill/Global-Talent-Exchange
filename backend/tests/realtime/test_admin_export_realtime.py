from __future__ import annotations

from app.core.events import DomainEvent
from app.realtime.service import RealtimeHub, admin_topic


def test_admin_export_ready_dispatches_to_scoped_admin_topic_without_artifact_content() -> None:
    hub = RealtimeHub()
    event = DomainEvent(
        name="admin.export.ready",
        aggregate_id="EXPORT-READY",
        aggregate_type="admin_export",
        payload={
            "export_id": "EXPORT-READY",
            "admin_user_id": "admin-1",
            "status": "ready",
            "export_type": "payment_queue",
            "format": "csv",
            "requested_at": "2026-06-03T00:00:00+00:00",
            "completed_at": "2026-06-03T00:00:01+00:00",
            "download_url": "/api/v2/admin/finance/exports/EXPORT-READY/download",
            "audit_reference": "audit-ready",
            "requested_audit_reference": "audit-requested",
            "artifact": {
                "filename": "export-ready.csv",
                "content_type": "text/csv",
                "row_count": 2,
                "content": "sensitive,csv\n",
            },
        },
    )

    dispatches = hub._map_domain_event(event)

    assert len(dispatches) == 1
    assert dispatches[0].type == "admin_export_ready"
    assert dispatches[0].topics == (admin_topic("admin-1"),)
    assert dispatches[0].data["event_name"] == "admin.export.ready"
    assert dispatches[0].data["export_id"] == "EXPORT-READY"
    assert dispatches[0].data["download_url"].endswith("/EXPORT-READY/download")
    assert dispatches[0].data["backend_authored"] is True
    assert dispatches[0].data["artifact"]["row_count"] == 2
    assert "content" not in dispatches[0].data["artifact"]


def test_admin_export_events_require_export_and_admin_scope() -> None:
    hub = RealtimeHub()

    assert (
        hub._map_domain_event(
            DomainEvent(
                name="admin.export.ready",
                payload={"admin_user_id": "admin-1"},
            )
        )
        == []
    )
    assert (
        hub._map_domain_event(
            DomainEvent(
                name="admin.export.ready",
                aggregate_id="EXPORT-READY",
                payload={"export_id": "EXPORT-READY"},
            )
        )
        == []
    )


def test_admin_realtime_topics_are_user_scoped() -> None:
    hub = RealtimeHub()

    assert hub._resolve_topics(("admin", "admin:admin-1", "admin:other-admin"), user_id="admin-1") == (
        admin_topic("admin-1"),
    )
