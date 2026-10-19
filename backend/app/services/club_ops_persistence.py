from __future__ import annotations

import base64
from dataclasses import fields, is_dataclass, MISSING
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
import importlib
import logging
from typing import Any
from uuid import UUID, NAMESPACE_URL, uuid5

from sqlalchemy import select

logger = logging.getLogger(__name__)

_INTERNAL_STORE_FIELDS = {
    "lock",
    "session_factory",
    "_thread_lock",
    "_local",
}


def _class_path(value: object) -> str:
    cls = value if isinstance(value, type) else type(value)
    return f"{cls.__module__}:{cls.__qualname__}"


def _resolve_class(path: str) -> type:
    module_name, qualified_name = path.split(":", 1)
    if not module_name.startswith("app."):
        raise ValueError(f"Unsupported ClubOps persisted type: {module_name}")
    resolved: Any = importlib.import_module(module_name)
    for name in qualified_name.split("."):
        resolved = getattr(resolved, name)
    if not isinstance(resolved, type):
        raise TypeError(f"Persisted symbol is not a class: {path}")
    return resolved


def _encode(value: Any) -> Any:
    if isinstance(value, Enum):
        return {"$clubops_type": "enum", "class": _class_path(value), "value": value.value}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return {"$clubops_type": "datetime", "value": value.isoformat()}
    if isinstance(value, date):
        return {"$clubops_type": "date", "value": value.isoformat()}
    if isinstance(value, Decimal):
        return {"$clubops_type": "decimal", "value": str(value)}
    if isinstance(value, UUID):
        return {"$clubops_type": "uuid", "value": str(value)}
    if isinstance(value, bytes):
        return {"$clubops_type": "bytes", "value": base64.b64encode(value).decode("ascii")}
    if is_dataclass(value) and not isinstance(value, type):
        return {
            "$clubops_type": "dataclass",
            "class": _class_path(value),
            "fields": {
                item.name: _encode(getattr(value, item.name))
                for item in fields(value)
                if item.init and item.name not in _INTERNAL_STORE_FIELDS
            },
        }

    try:
        from pydantic import BaseModel
    except ImportError:  # pragma: no cover - pydantic is a backend dependency
        BaseModel = ()  # type: ignore[assignment,misc]
    if BaseModel and isinstance(value, BaseModel):
        model_fields = getattr(type(value), "model_fields", None) or getattr(type(value), "__fields__", {})
        return {
            "$clubops_type": "pydantic",
            "class": _class_path(value),
            "fields": {name: _encode(getattr(value, name)) for name in model_fields},
        }

    if isinstance(value, dict):
        # Pair-encoding preserves Enum/tuple keys; plain JSON object keys would
        # silently turn them into strings and corrupt the in-memory service API.
        return {
            "$clubops_type": "dict",
            "items": [[_encode(key), _encode(item)] for key, item in value.items()],
        }
    if isinstance(value, tuple):
        return {"$clubops_type": "tuple", "items": [_encode(item) for item in value]}
    if isinstance(value, (set, frozenset)):
        return {
            "$clubops_type": "frozenset" if isinstance(value, frozenset) else "set",
            "items": [_encode(item) for item in value],
        }
    if isinstance(value, list):
        return [_encode(item) for item in value]

    if hasattr(value, "__dict__") and type(value).__module__.startswith("app."):
        return {
            "$clubops_type": "object",
            "class": _class_path(value),
            "fields": {key: _encode(item) for key, item in vars(value).items() if not key.startswith("_")},
        }
    raise TypeError(f"Unsupported ClubOps persisted value: {_class_path(value)}")


def _decode(value: Any) -> Any:
    if isinstance(value, list):
        return [_decode(item) for item in value]
    if not isinstance(value, dict):
        return value

    kind = value.get("$clubops_type")
    if kind is None:
        return {key: _decode(item) for key, item in value.items()}
    if kind == "datetime":
        return datetime.fromisoformat(value["value"])
    if kind == "date":
        return date.fromisoformat(value["value"])
    if kind == "decimal":
        return Decimal(value["value"])
    if kind == "uuid":
        return UUID(value["value"])
    if kind == "bytes":
        return base64.b64decode(value["value"])
    if kind == "enum":
        return _resolve_class(value["class"])(value["value"])
    if kind == "dict":
        return {_decode(pair[0]): _decode(pair[1]) for pair in value["items"]}
    if kind == "tuple":
        return tuple(_decode(item) for item in value["items"])
    if kind == "set":
        return set(_decode(item) for item in value["items"])
    if kind == "frozenset":
        return frozenset(_decode(item) for item in value["items"])
    if kind in {"dataclass", "pydantic"}:
        cls = _resolve_class(value["class"])
        fields_value = {key: _decode(item) for key, item in value["fields"].items()}
        return cls(**fields_value)
    if kind == "object":
        cls = _resolve_class(value["class"])
        instance = cls.__new__(cls)
        for key, item in value["fields"].items():
            setattr(instance, key, _decode(item))
        return instance
    raise ValueError(f"Unknown ClubOps persisted value tag: {kind}")


def _store_state(store: object) -> dict[str, Any]:
    return {
        item.name: getattr(store, item.name)
        for item in fields(store)
        if item.name not in _INTERNAL_STORE_FIELDS
    }


def _replace_store_state(store: object, payload: Any) -> None:
    if not isinstance(payload, dict):
        raise TypeError("ClubOps snapshot payload must decode to a dictionary")
    store_fields = {
        item.name: item
        for item in fields(store)
        if item.name not in _INTERNAL_STORE_FIELDS
    }
    for name, item in store_fields.items():
        if name in payload:
            setattr(store, name, payload[name])
        elif item.default_factory is not MISSING:
            setattr(store, name, item.default_factory())
        elif item.default is not MISSING:
            setattr(store, name, item.default)


def _attr(value: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if isinstance(value, dict) and name in value:
            result = value[name]
            if result is not None:
                return result
        elif hasattr(value, name):
            result = getattr(value, name)
            if result is not None:
                return result
    return default


def _time(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _integer(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _plain(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(_plain(key)): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_plain(item) for item in value]
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: _plain(getattr(value, item.name)) for item in fields(value) if item.init}
    if hasattr(value, "model_dump"):
        return _plain(value.model_dump(mode="python"))
    if hasattr(value, "dict") and callable(value.dict):
        return _plain(value.dict())
    return str(value)


def _enum_value(model: type, column_name: str, value: Any) -> Any:
    if value is None:
        return None
    column_type = model.__table__.c[column_name].type
    enum_class = getattr(column_type, "enum_class", None)
    if enum_class is None:
        return value
    if isinstance(value, enum_class):
        return value
    raw = value.value if isinstance(value, Enum) else value
    try:
        return enum_class(raw)
    except (TypeError, ValueError):
        try:
            return enum_class[str(raw)]
        except (KeyError, TypeError):
            return None


def _database_id(model: type, value: Any) -> str:
    raw = str(value or "")
    if not raw:
        return str(uuid5(NAMESPACE_URL, f"gtex-club-ops:{model.__tablename__}:missing"))
    if len(raw) <= 36:
        return raw
    return str(uuid5(NAMESPACE_URL, f"gtex-club-ops:{model.__tablename__}:{raw}"))


def _upsert(session: Any, model: type, record_id: Any, values: dict[str, Any], *, where: tuple[Any, ...] = ()) -> Any:
    normalized_id = _database_id(model, record_id)
    row = session.get(model, normalized_id)
    if row is None and where:
        row = session.scalar(select(model).where(*where).limit(1))
    if row is None:
        row = model(id=normalized_id, **values)
        session.add(row)
    else:
        for key, value in values.items():
            setattr(row, key, value)
    return row


def _persist_finance_projection(session: Any, store: object) -> None:
    from app.models.club_finance_account import ClubFinanceAccount
    from app.models.club_finance_ledger_entry import ClubFinanceLedgerEntry

    account_ids: dict[tuple[str, str], str] = {}
    for club_id, accounts in store.accounts_by_club.items():
        for account_type, record in accounts.items():
            enum_value = _enum_value(ClubFinanceAccount, "account_type", account_type)
            if enum_value is None:
                continue
            values = {
                "club_id": club_id,
                "account_type": enum_value,
                "currency": str(_attr(record, "currency", default="USD"))[:12],
                "balance_minor": _integer(_attr(record, "balance_minor")),
                "allow_negative": bool(_attr(record, "allow_negative", default=False)),
                "is_active": bool(_attr(record, "is_active", default=True)),
            }
            original_id = _attr(record, "id", default=f"{club_id}-{enum_value.value}")
            row = _upsert(
                session,
                ClubFinanceAccount,
                original_id,
                values,
                where=(ClubFinanceAccount.club_id == club_id, ClubFinanceAccount.account_type == enum_value),
            )
            if hasattr(record, "id"):
                record.id = row.id
            account_ids[(club_id, enum_value.value)] = row.id
    session.flush()

    for club_id, entries in store.ledger_by_club.items():
        for entry in entries:
            entry_id = _database_id(ClubFinanceLedgerEntry, _attr(entry, "id"))
            if session.get(ClubFinanceLedgerEntry, entry_id) is not None:
                continue  # Ledger rows are intentionally append-only.
            account_type = _enum_value(ClubFinanceLedgerEntry, "account_type", _attr(entry, "account_type"))
            entry_type = _enum_value(ClubFinanceLedgerEntry, "entry_type", _attr(entry, "entry_type"))
            if account_type is None or entry_type is None:
                continue
            account_id = account_ids.get((club_id, account_type.value))
            if account_id is None:
                continue
            created_at = _time(_attr(entry, "created_at"))
            values = {
                "transaction_id": str(_attr(entry, "transaction_id", default=entry_id))[:64],
                "club_id": club_id,
                "account_id": account_id,
                "account_type": account_type,
                "entry_type": entry_type,
                "amount_minor": _integer(_attr(entry, "amount_minor")),
                "currency": str(_attr(entry, "currency", default="USD"))[:12],
                "description": (
                    str(_attr(entry, "description"))[:255] if _attr(entry, "description") is not None else None
                ),
                "reference_id": (
                    str(_attr(entry, "reference_id"))[:64] if _attr(entry, "reference_id") is not None else None
                ),
                "metadata_json": _plain(_attr(entry, "metadata", default={})),
            }
            if created_at is not None:
                values["created_at"] = created_at
            session.add(ClubFinanceLedgerEntry(id=entry_id, **values))
    session.flush()


def _persist_sponsorship_projection(session: Any, store: object) -> None:
    from app.models.club_sponsorship_asset import ClubSponsorshipAsset
    from app.models.club_sponsorship_contract import ClubSponsorshipContract

    contract_ids: dict[str, str] = {}
    for club_id, contracts in store.sponsorship_contracts_by_club.items():
        for key, contract in contracts.items():
            record_id = _attr(contract, "id", default=key)
            asset_type = _enum_value(ClubSponsorshipContract, "asset_type", _attr(contract, "asset_type"))
            status = _enum_value(ClubSponsorshipContract, "status", _attr(contract, "status"))
            start_at = _time(_attr(contract, "start_at", "starts_at", "started_at"))
            end_at = _time(_attr(contract, "end_at", "ends_at", "expires_at"))
            sponsor_name = _attr(contract, "sponsor_name", "brand_name", "name")
            if asset_type is None or status is None or start_at is None or end_at is None or not sponsor_name:
                continue
            values = {
                "club_id": club_id,
                "package_id": None,  # Avoid a dangling FK when legacy catalogs use non-ORM IDs.
                "asset_type": asset_type,
                "sponsor_name": str(sponsor_name)[:120],
                "status": status,
                "contract_amount_minor": _integer(_attr(contract, "contract_amount_minor", "amount_minor")),
                "currency": str(_attr(contract, "currency", default="USD"))[:12],
                "duration_months": _integer(_attr(contract, "duration_months"), 3),
                "payout_schedule": str(_attr(contract, "payout_schedule", default="monthly"))[:24],
                "start_at": start_at,
                "end_at": end_at,
                "moderation_required": bool(_attr(contract, "moderation_required", default=False)),
                "moderation_status": str(_attr(contract, "moderation_status", default="not_required"))[:32],
                "custom_copy": _attr(contract, "custom_copy"),
                "custom_logo_url": _attr(contract, "custom_logo_url"),
                "performance_bonus_minor": _integer(_attr(contract, "performance_bonus_minor")),
                "settled_amount_minor": _integer(_attr(contract, "settled_amount_minor")),
                "outstanding_amount_minor": _integer(_attr(contract, "outstanding_amount_minor")),
            }
            row = _upsert(session, ClubSponsorshipContract, record_id, values)
            contract_ids[str(record_id)] = row.id
    session.flush()

    for club_id, assets in store.sponsorship_assets_by_club.items():
        for key, asset in assets.items():
            record_id = _attr(asset, "id", default=key)
            asset_type = _enum_value(ClubSponsorshipAsset, "asset_type", _attr(asset, "asset_type"))
            slot_code = _attr(asset, "slot_code", "placement_code", "slot")
            if asset_type is None or not slot_code:
                continue
            source_contract_id = _attr(asset, "contract_id", "sponsorship_contract_id")
            values = {
                "club_id": club_id,
                "contract_id": contract_ids.get(str(source_contract_id)) if source_contract_id is not None else None,
                "asset_type": asset_type,
                "slot_code": str(slot_code)[:80],
                "is_visible": bool(_attr(asset, "is_visible", "visible", default=True)),
                "moderation_required": bool(_attr(asset, "moderation_required", default=False)),
                "moderation_status": str(_attr(asset, "moderation_status", default="not_required"))[:32],
                "rendered_text": _attr(asset, "rendered_text", "display_text"),
                "asset_url": _attr(asset, "asset_url", "logo_url", "image_url"),
            }
            _upsert(session, ClubSponsorshipAsset, record_id, values)
    session.flush()


def _persist_academy_projection(session: Any, store: object) -> None:
    from app.models.academy_graduation_event import AcademyGraduationEvent
    from app.models.academy_player import AcademyPlayer
    from app.models.academy_program import AcademyProgram
    from app.models.academy_training_cycle import AcademyTrainingCycle

    program_ids: dict[str, str] = {}
    for club_id, programs in store.academy_programs_by_club.items():
        for key, program in programs.items():
            record_id = _attr(program, "id", default=key)
            program_type = _enum_value(AcademyProgram, "program_type", _attr(program, "program_type", "type"))
            name = _attr(program, "name", "display_name", "title")
            if program_type is None or not name:
                continue
            values = {
                "club_id": club_id,
                "name": str(name)[:120],
                "program_type": program_type,
                "budget_minor": _integer(_attr(program, "budget_minor")),
                "cycle_length_weeks": _integer(_attr(program, "cycle_length_weeks"), 6),
                "focus_attributes_json": _plain(_attr(program, "focus_attributes_json", "focus_attributes", default=[])),
                "is_active": bool(_attr(program, "is_active", "active", default=True)),
            }
            row = _upsert(session, AcademyProgram, record_id, values)
            program_ids[str(record_id)] = row.id
    session.flush()

    player_ids: dict[str, str] = {}
    for club_id, players in store.academy_players_by_club.items():
        for key, player in players.items():
            record_id = _attr(player, "id", default=key)
            status = _enum_value(AcademyPlayer, "status", _attr(player, "status"))
            name = _attr(player, "display_name", "name")
            age = _attr(player, "age")
            position = _attr(player, "primary_position", "position", "primary_role")
            if status is None or not name or age is None or not position:
                continue
            original_program_id = _attr(player, "program_id", "academy_program_id")
            values = {
                "club_id": club_id,
                "program_id": program_ids.get(str(original_program_id)) if original_program_id is not None else None,
                "display_name": str(name)[:120],
                "age": _integer(age),
                "primary_position": str(position)[:40],
                "secondary_position": _attr(player, "secondary_position"),
                "status": status,
                "overall_rating": _integer(_attr(player, "overall_rating", "rating")),
                "readiness_score": _integer(_attr(player, "readiness_score")),
                "completed_cycles": _integer(_attr(player, "completed_cycles")),
                "development_attributes_json": _plain(_attr(player, "development_attributes_json", "development_attributes", default={})),
                "pathway_note": _attr(player, "pathway_note"),
            }
            row = _upsert(session, AcademyPlayer, record_id, values)
            player_ids[str(record_id)] = row.id
    session.flush()

    for club_id, cycles in store.academy_training_cycles_by_club.items():
        for key, cycle in cycles.items():
            record_id = _attr(cycle, "id", default=key)
            original_program_id = _attr(cycle, "program_id", "academy_program_id")
            program_id = program_ids.get(str(original_program_id))
            start_at = _time(_attr(cycle, "starts_at", "start_at"))
            end_at = _time(_attr(cycle, "ends_at", "end_at"))
            if program_id is None or start_at is None or end_at is None:
                continue
            values = {
                "club_id": club_id,
                "program_id": program_id,
                "cycle_index": _integer(_attr(cycle, "cycle_index", "cycle_number"), 1),
                "starts_at": start_at,
                "ends_at": end_at,
                "focus_attributes_json": _plain(_attr(cycle, "focus_attributes_json", "focus_attributes", default=[])),
                "player_count": _integer(_attr(cycle, "player_count")),
                "average_delta": _integer(_attr(cycle, "average_delta", "average_rating_delta")),
            }
            _upsert(session, AcademyTrainingCycle, record_id, values)
    session.flush()

    for club_id, graduations in store.academy_graduations_by_club.items():
        for index, event in enumerate(graduations):
            source_player_id = _attr(event, "academy_player_id", "player_id", "prospect_id")
            player_id = player_ids.get(str(source_player_id))
            from_status = _enum_value(AcademyGraduationEvent, "from_status", _attr(event, "from_status", "previous_status"))
            to_status = _enum_value(AcademyGraduationEvent, "to_status", _attr(event, "to_status", "status"))
            if player_id is None or from_status is None or to_status is None:
                continue
            record_id = _attr(event, "id", default=f"{club_id}:{source_player_id}:{index}")
            values = {
                "club_id": club_id,
                "academy_player_id": player_id,
                "from_status": from_status,
                "to_status": to_status,
                "reason": str(_attr(event, "reason", "note", default="Academy progression recorded"))[:255],
            }
            _upsert(session, AcademyGraduationEvent, record_id, values)
    session.flush()


def _persist_scouting_projection(session: Any, store: object) -> None:
    from app.models.scout_assignment import ScoutAssignment
    from app.models.scouting_region import ScoutingRegion
    from app.models.youth_pipeline_snapshot import YouthPipelineSnapshot
    from app.models.youth_prospect import YouthProspect
    from app.models.youth_prospect_report import YouthProspectReport

    region_ids: dict[str, str] = {}
    region_values = store.scouting_regions
    if isinstance(region_values, dict):
        region_iterable = region_values.items()
    else:
        region_iterable = enumerate(region_values or [])
    for key, region in region_iterable:
        record_id = _attr(region, "id", default=key)
        code = _attr(region, "code", "region_code", default=str(key))
        name = _attr(region, "name", "region_name", default=str(code))
        region_type = _enum_value(ScoutingRegion, "region_type", _attr(region, "region_type", "type"))
        if region_type is None or not code:
            continue
        values = {
            "code": str(code)[:64],
            "name": str(name)[:120],
            "region_type": region_type,
            "territory_codes_json": _plain(_attr(region, "territory_codes_json", "territory_codes", default=[])),
            "is_active": bool(_attr(region, "is_active", "active", default=True)),
        }
        row = _upsert(
            session,
            ScoutingRegion,
            record_id,
            values,
            where=(ScoutingRegion.code == str(code)),
        )
        region_ids[str(key)] = row.id
        region_ids[str(code)] = row.id
    session.flush()

    assignment_ids: dict[str, str] = {}
    for club_id, assignments in store.scouting_assignments_by_club.items():
        for key, assignment in assignments.items():
            record_id = _attr(assignment, "id", default=key)
            status = _enum_value(ScoutAssignment, "status", _attr(assignment, "status"))
            starts_at = _time(_attr(assignment, "starts_at", "start_at"))
            ends_at = _time(_attr(assignment, "ends_at", "end_at"))
            region_code = _attr(assignment, "region_code", "code")
            region_name = _attr(assignment, "region_name", "name")
            focus_area = _attr(assignment, "focus_area", "focus", "objective")
            if status is None or starts_at is None or ends_at is None or not region_code or not region_name or not focus_area:
                continue
            source_region_id = _attr(assignment, "region_id")
            region_id = region_ids.get(str(source_region_id)) if source_region_id is not None else region_ids.get(str(region_code))
            values = {
                "club_id": club_id,
                "region_id": region_id,
                "region_code": str(region_code)[:64],
                "region_name": str(region_name)[:120],
                "focus_area": str(focus_area)[:120],
                "budget_minor": _integer(_attr(assignment, "budget_minor")),
                "scout_count": _integer(_attr(assignment, "scout_count"), 1),
                "status": status,
                "report_confidence_floor_bps": _integer(_attr(assignment, "report_confidence_floor_bps")),
                "starts_at": starts_at,
                "ends_at": ends_at,
            }
            row = _upsert(session, ScoutAssignment, record_id, values)
            assignment_ids[str(record_id)] = row.id
    session.flush()

    prospect_ids: dict[str, str] = {}
    for club_id, prospects in store.prospects_by_club.items():
        for key, prospect in prospects.items():
            record_id = _attr(prospect, "id", default=key)
            rating_band = _enum_value(YouthProspect, "rating_band", _attr(prospect, "rating_band", "potential_band"))
            pathway_stage = _enum_value(YouthProspect, "pathway_stage", _attr(prospect, "pathway_stage", "stage"))
            name = _attr(prospect, "display_name", "name", "player_name")
            age = _attr(prospect, "age")
            nationality = _attr(prospect, "nationality_code", "nationality", "country_code")
            region = _attr(prospect, "region_label", "region_name", "region")
            position = _attr(prospect, "primary_position", "position")
            source = _attr(prospect, "scouting_source", "source", default="club_ops")
            if rating_band is None or pathway_stage is None or not name or age is None or not nationality or not position:
                continue
            source_assignment_id = _attr(prospect, "assignment_id", "scout_assignment_id")
            assignment_id = assignment_ids.get(str(source_assignment_id)) if source_assignment_id is not None else None
            values = {
                "club_id": club_id,
                "assignment_id": assignment_id,
                "display_name": str(name)[:120],
                "age": _integer(age),
                "nationality_code": str(nationality)[:12],
                "region_label": str(region or "Unspecified")[:120],
                "primary_position": str(position)[:40],
                "secondary_position": _attr(prospect, "secondary_position"),
                "rating_band": rating_band,
                "development_traits_json": _plain(_attr(prospect, "development_traits_json", "development_traits", default=[])),
                "pathway_stage": pathway_stage,
                "scouting_source": str(source)[:80],
                "follow_priority": _integer(_attr(prospect, "follow_priority"), 5),
                "academy_player_id": _attr(prospect, "academy_player_id"),
            }
            row = _upsert(session, YouthProspect, record_id, values)
            prospect_ids[str(record_id)] = row.id
    session.flush()

    for source_prospect_id, reports in store.prospect_reports_by_prospect.items():
        prospect_id = prospect_ids.get(str(source_prospect_id))
        if prospect_id is None:
            continue
        for index, report in enumerate(reports or []):
            record_id = _attr(report, "id", default=f"{source_prospect_id}:report:{index}")
            source_assignment_id = _attr(report, "assignment_id", "scout_assignment_id")
            assignment_id = assignment_ids.get(str(source_assignment_id)) if source_assignment_id is not None else None
            values = {
                "prospect_id": prospect_id,
                "assignment_id": assignment_id,
                "confidence_bps": _integer(_attr(report, "confidence_bps", "confidence_score")),
                "summary_text": str(_attr(report, "summary_text", "summary", "description", default="Youth scouting report recorded"))[:255],
                "strengths_json": _plain(_attr(report, "strengths_json", "strengths", default=[])),
                "development_flags_json": _plain(_attr(report, "development_flags_json", "development_flags", default=[])),
            }
            _upsert(session, YouthProspectReport, record_id, values)
    session.flush()

    for club_id, snapshot in store.youth_pipeline_by_club.items():
        if snapshot is None:
            continue
        existing = session.scalar(select(YouthPipelineSnapshot).where(YouthPipelineSnapshot.club_id == club_id).limit(1))
        if existing is None:
            record_id = _attr(snapshot, "id", default=f"{club_id}:youth-pipeline")
            values = {
                "club_id": club_id,
                "funnel_json": _plain(_attr(snapshot, "funnel_json", "funnel", "funnel_counts", default={})),
                "academy_conversion_rate_bps": _integer(_attr(snapshot, "academy_conversion_rate_bps", "academy_conversion_bps")),
                "promotion_rate_bps": _integer(_attr(snapshot, "promotion_rate_bps", "promotion_bps")),
            }
            _upsert(session, YouthPipelineSnapshot, record_id, values)
        else:
            existing.funnel_json = _plain(_attr(snapshot, "funnel_json", "funnel", "funnel_counts", default={}))
            existing.academy_conversion_rate_bps = _integer(_attr(snapshot, "academy_conversion_rate_bps", "academy_conversion_bps"))
            existing.promotion_rate_bps = _integer(_attr(snapshot, "promotion_rate_bps", "promotion_bps"))
    session.flush()


def _persist_relational_projections(session: Any, store: object) -> None:
    # Finance projections are integrity-critical: a snapshot must not commit if
    # the account/ledger rows cannot also be written in the same transaction.
    _persist_finance_projection(session, store)

    # These are normalized read models for the existing feature services. Each
    # optional projection uses a savepoint so a legacy shape mismatch cannot
    # discard the authoritative durable snapshot.
    for projector, name in (
        (_persist_sponsorship_projection, "sponsorship"),
        (_persist_academy_projection, "academy"),
        (_persist_scouting_projection, "scouting"),
    ):
        try:
            with session.begin_nested():
                projector(session, store)
        except Exception:
            logger.exception("club_ops.persistence_projection_failed projection=%s", name)


class ClubOpsPersistenceLock:
    """Keep the legacy object-based ClubOps API durable and cross-worker safe."""

    def __init__(self, store: object) -> None:
        self.store = store

    def __enter__(self) -> "ClubOpsPersistenceLock":
        self.store._thread_lock.acquire()
        depth = getattr(self.store._local, "depth", 0)
        if depth:
            self.store._local.depth = depth + 1
            return self
        self.store._local.depth = 1
        self.store._local.session = None
        try:
            if self.store.session_factory is None:
                return self
            from app.models.club_ops_state_snapshot import ClubOpsStateSnapshot

            session = self.store.session_factory()
            session.begin()
            self.store._local.session = session
            row = session.scalar(
                select(ClubOpsStateSnapshot)
                .where(ClubOpsStateSnapshot.state_key == "global")
                .with_for_update()
            )
            if row is None:
                row = ClubOpsStateSnapshot(state_key="global", payload={})
                session.add(row)
                session.flush()
            original_payload = row.payload or {}
            self.store._local.row = row
            self.store._local.original_payload = original_payload
            _replace_store_state(self.store, _decode(original_payload) if original_payload else {})
            return self
        except Exception:
            session = getattr(self.store._local, "session", None)
            if session is not None:
                session.rollback()
                session.close()
                self.store._local.session = None
                self.store._local.row = None
                self.store._local.original_payload = None
            self.store._local.depth = 0
            self.store._thread_lock.release()
            raise

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> bool:
        depth = getattr(self.store._local, "depth", 1) - 1
        self.store._local.depth = depth
        if depth:
            self.store._thread_lock.release()
            return False

        session = getattr(self.store._local, "session", None)
        if session is None:
            self.store._thread_lock.release()
            return False

        try:
            if exc_type is not None:
                session.rollback()
                original = getattr(self.store._local, "original_payload", {})
                _replace_store_state(self.store, _decode(original) if original else {})
                return False

            row = self.store._local.row
            updated_payload = _encode(_store_state(self.store))
            original_payload = getattr(self.store._local, "original_payload", {})
            if updated_payload != original_payload:
                row.payload = updated_payload
                row.updated_at = datetime.now(timezone.utc)
                _persist_relational_projections(session, self.store)
                session.commit()
            else:
                session.rollback()
            return False
        except Exception:
            session.rollback()
            original = getattr(self.store._local, "original_payload", {})
            _replace_store_state(self.store, _decode(original) if original else {})
            raise
        finally:
            session.close()
            self.store._local.session = None
            self.store._local.row = None
            self.store._local.original_payload = None
            self.store._thread_lock.release()

    def acquire(self, *args: Any, **kwargs: Any) -> bool:
        return self.store._thread_lock.acquire(*args, **kwargs)

    def release(self) -> None:
        self.store._thread_lock.release()
