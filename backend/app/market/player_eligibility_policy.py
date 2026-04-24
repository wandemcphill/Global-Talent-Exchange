from __future__ import annotations

from typing import Any

from app.models.regen_ecosystem import NationalRegenSeed


def _read_value(entity: Any, key: str) -> Any:
    if entity is None:
        return None
    if isinstance(entity, dict):
        return entity.get(key)
    return getattr(entity, key, None)


def _metadata_payload(entity: Any) -> dict[str, Any]:
    if entity is None:
        return {}
    if isinstance(entity, dict):
        metadata = entity.get("metadata")
        if isinstance(metadata, dict):
            return metadata
        metadata_json = entity.get("metadata_json")
        return metadata_json if isinstance(metadata_json, dict) else {}
    metadata = getattr(entity, "metadata", None)
    if isinstance(metadata, dict):
        return metadata
    metadata_json = getattr(entity, "metadata_json", None)
    return metadata_json if isinstance(metadata_json, dict) else {}


def _read_bool(entity: Any, *keys: str) -> bool | None:
    metadata = _metadata_payload(entity)
    for key in keys:
        value = _read_value(entity, key)
        if isinstance(value, bool):
            return value
        if key in metadata and isinstance(metadata[key], bool):
            return metadata[key]
    return None


def _read_text(entity: Any, *keys: str) -> str | None:
    metadata = _metadata_payload(entity)
    for key in keys:
        value = _read_value(entity, key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        meta_value = metadata.get(key)
        if isinstance(meta_value, str) and meta_value.strip():
            return meta_value.strip()
    return None


def is_preseeded_national_regen(entity: Any) -> bool:
    if entity is None:
        return False
    if isinstance(entity, NationalRegenSeed):
        return True
    explicit = _read_bool(entity, "is_preseeded_national_regen")
    if explicit is not None:
        return explicit
    source_type = (_read_text(entity, "source_type") or "").lower()
    if source_type == "national_seed":
        return True
    source_bucket = (_read_text(entity, "source_bucket") or "").lower()
    national_pool_only = _read_bool(entity, "national_pool_only")
    if source_bucket == "preseeded" and national_pool_only is True:
        return True
    seed_type = (_read_text(entity, "seed_type") or "").lower()
    return seed_type == "preseeded_national_pool"


def is_share_market_eligible(entity: Any) -> bool:
    if is_preseeded_national_regen(entity):
        return False
    explicit = _read_bool(entity, "share_market_eligible", "market_eligible")
    if explicit is not None:
        return explicit
    tradable = _read_bool(entity, "is_tradable", "tradable")
    if tradable is not None:
        return tradable
    return True


def is_transfer_market_eligible(entity: Any) -> bool:
    if is_preseeded_national_regen(entity):
        return False
    explicit = _read_bool(entity, "transfer_market_eligible", "transferable", "tradable")
    if explicit is not None:
        return explicit
    tradable = _read_bool(entity, "is_tradable")
    if tradable is not None:
        return tradable
    return True


def is_card_mint_eligible(entity: Any) -> bool:
    if is_preseeded_national_regen(entity):
        return False
    explicit = _read_bool(entity, "card_mint_eligible")
    if explicit is not None:
        return explicit
    return True


def is_buy_cta_allowed(entity: Any, actor: Any = None) -> bool:
    del actor
    if is_preseeded_national_regen(entity):
        return False
    explicit = _read_bool(entity, "buy_cta_allowed", "buyable")
    if explicit is not None:
        return explicit
    return is_share_market_eligible(entity) or is_transfer_market_eligible(entity)


def market_access_payload(entity: Any, actor: Any = None) -> dict[str, bool]:
    transfer_market_eligible = is_transfer_market_eligible(entity)
    share_market_eligible = is_share_market_eligible(entity)
    card_mint_eligible = is_card_mint_eligible(entity)
    buy_cta_allowed = is_buy_cta_allowed(entity, actor=actor)
    preseeded_national_regen = is_preseeded_national_regen(entity)
    national_pool_only = _read_bool(entity, "national_pool_only")
    return {
        "market_eligible": share_market_eligible or transfer_market_eligible,
        "share_market_eligible": share_market_eligible,
        "tradable": transfer_market_eligible,
        "buyable": buy_cta_allowed,
        "transferable": transfer_market_eligible,
        "card_mint_eligible": card_mint_eligible,
        "buy_cta_allowed": buy_cta_allowed,
        "is_preseeded_national_regen": preseeded_national_regen,
        "national_pool_only": bool(national_pool_only) or preseeded_national_regen,
    }


__all__ = [
    "is_buy_cta_allowed",
    "is_card_mint_eligible",
    "is_preseeded_national_regen",
    "is_share_market_eligible",
    "is_transfer_market_eligible",
    "market_access_payload",
]
