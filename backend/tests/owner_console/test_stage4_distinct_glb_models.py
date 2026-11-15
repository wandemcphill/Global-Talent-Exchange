from pathlib import Path

from app.owner_console import daily_operations_hub as hub_service
from tests.owner_console.test_owner_comms_overhaul import _setup_session


def test_stage4_all_six_destinations_use_distinct_verified_glb_assets_on_disk() -> None:
    session, _, _ = _setup_session()
    repo_root = Path(__file__).resolve().parents[3]
    public_root = repo_root / "frontend" / "react-shell" / "public"

    try:
        payload = hub_service.get_club_operations_hub(session, user_id="owner-u1", club_id="club-o1")
        destinations = payload["destinations"]
        assert len(destinations) == 6

        glb_models = [d["glb_model"] for d in destinations]
        assert len(set(glb_models)) == 6

        for dest in destinations:
            for field in ("glb_model", "exterior_glb", "model_glb_url"):
                rel = dest[field].lstrip("/")
                asset_path = public_root / rel
                assert asset_path.is_file(), f"Missing GLB file: {asset_path}"
                header = asset_path.read_bytes()[:4]
                assert header == b"glTF", f"Invalid GLB binary header for {asset_path}: {header!r}"
    finally:
        session.close()
