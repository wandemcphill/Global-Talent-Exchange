from __future__ import annotations

from sqlalchemy import select

from app.economy.service import DEFAULT_GIFTS
from app.models.economy_config import GiftCatalogItem


def _prepare_gift_catalog(client) -> None:
    startup_thread = getattr(client.app.state, "deferred_startup_thread", None)
    if startup_thread is not None and startup_thread.is_alive():
        startup_thread.join(timeout=5)
    with client.app.state.session_factory() as session:
        existing = {item.key for item in session.scalars(select(GiftCatalogItem)).all()}
        for payload in DEFAULT_GIFTS:
            if payload["key"] in existing:
                continue
            session.add(GiftCatalogItem(**payload))
        session.commit()


def _login(client, email: str, password: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_send_gift_and_summary_flow(client, demo_seed) -> None:
    _prepare_gift_catalog(client)
    sender = demo_seed.demo_users[0]
    recipient = demo_seed.demo_users[1]
    sender_headers = _login(client, sender.email, sender.password)

    response = client.post(
        "/api/gift-engine/send",
        headers=sender_headers,
        json={
            "recipient_user_id": recipient.user_id,
            "gift_key": "fire",
            "quantity": "2.0000",
            "note": "For the knockout drama",
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["gift_key"] == "fire"
    assert payload["gross_amount"] == "4.0000"
    assert payload["platform_rake_amount"] == "1.2000"
    assert payload["recipient_net_amount"] == "2.8000"

    sender_summary = client.get("/api/gift-engine/me/summary", headers=sender_headers)
    assert sender_summary.status_code == 200, sender_summary.text
    assert sender_summary.json()["sent_total"] == "4.0000"
    assert sender_summary.json()["rake_total"] == "1.2000"

    recipient_headers = _login(client, recipient.email, recipient.password)
    recipient_summary = client.get("/api/gift-engine/me/summary", headers=recipient_headers)
    assert recipient_summary.status_code == 200, recipient_summary.text
    assert recipient_summary.json()["received_total"] == "2.8000"


def test_send_gift_rejects_self_send(client, demo_seed) -> None:
    _prepare_gift_catalog(client)
    sender = demo_seed.demo_users[0]
    sender_headers = _login(client, sender.email, sender.password)
    response = client.post(
        "/api/gift-engine/send",
        headers=sender_headers,
        json={
            "recipient_user_id": sender.user_id,
            "gift_key": "fire",
            "quantity": "1.0000",
        },
    )
    assert response.status_code == 400
    assert "cannot send gifts to themselves" in response.text.lower()
