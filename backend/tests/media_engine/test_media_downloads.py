from __future__ import annotations

from backend.app.services.storage_media_service import MediaStorageService
from backend.app.storage import LocalObjectStorage


def test_media_download_flow(client, demo_auth_headers, app):
    settings = app.state.settings
    storage_service = MediaStorageService(
        storage=LocalObjectStorage(settings.media_storage.storage_root),
        config=settings.media_storage,
    )
    asset = storage_service.store_temporary_highlight(
        match_key="friendly-002",
        content=b"demo-highlight",
        content_type="video/mp4",
        clip_label="first-half",
    )

    purchase = client.post(
        "/media-engine/purchases",
        headers=demo_auth_headers,
        json={"match_key": "friendly-002", "competition_key": "friendly-cup"},
    )
    assert purchase.status_code == 201, purchase.text

    response = client.post(
        "/media-engine/downloads",
        headers=demo_auth_headers,
        json={"storage_key": asset.storage_key, "match_key": "friendly-002", "download_kind": "highlight"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["storage_key"] == asset.storage_key
    assert body["download_url"].startswith("/media-engine/downloads/")

    download = client.get(body["download_url"])
    assert download.status_code == 200, download.text
    assert download.content == b"demo-highlight"
