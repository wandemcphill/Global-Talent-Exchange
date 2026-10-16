from __future__ import annotations

import importlib
import warnings

from app.auth.schemas import RegisterRequest
import app.auth.schemas as auth_schemas


def test_register_request_normalizes_optional_profile_fields() -> None:
    payload = RegisterRequest(
        email=" Fan@Example.com ",
        username=" FanUser ",
        password="SuperSecret1",
        full_name="  Fan User  ",
        phone_number=" 08000000000 ",
        region_code=" ng ",
    )

    assert payload.email == "fan@example.com"
    assert payload.username == "fanuser"
    assert payload.full_name == "Fan User"
    assert payload.phone_number == "08000000000"
    assert payload.region_code == "NG"


def test_auth_schemas_reload_without_validator_override_warnings() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        importlib.reload(auth_schemas)
