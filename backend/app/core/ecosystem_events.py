from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
from typing import Any, Callable, Sequence
from uuid import uuid4

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.event_backbone import (
    build_outbox_event,
    defer_event_publish_until_commit,
)
from app.core.events import DomainEvent, InMemoryEventPublisher
from app.core.serialization import make_json_safe
from app.models.event_backbone import EventConsumerState, EventDeadLetter, EventOutbox

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EcosystemDomain(str, Enum):
    """Canonical GTEX Ecosystem Domains."""
    CLUB_MANAGEMENT = "club_management"
    OWNER_DECISION = "owner_decision"
    OWNER_GOVERNANCE = "owner_governance"
    STAFF_INTERACTION = "staff_interaction"
    ACADEMY_LIFE = "academy_life"
    RECRUITMENT_TRANSFER = "recruitment_transfer"
    COMPETITION = "competition"
    MATCH_BROADCAST = "match_broadcast"
    SOCIAL_COMMUNICATION = "social_communication"
    ADVERTISING_CAMPAIGN = "advertising_campaign"
    MUSIC_PROMOTION = "music_promotion"
    GIFTING_CELEBRATION = "gifting_celebration"
    MARKETPLACE_COMMERCIAL = "marketplace_commercial"


class EcosystemEventPriority(str, Enum):
    """Priority tiers for GTEX Ecosystem events."""
    CRITICAL = "critical"  # Immediate processing (boardroom ultimatums, takeover notices)
    HIGH = "high"          # Prompt handling (transfer bids, signing reveals)
    NORMAL = "normal"      # Standard lifecycle operations
    LOW = "low"            # Passive metrics, ambient simulations, background logs


class EcosystemResolutionStatus(str, Enum):
    """Lifecycle / resolution status for interactive ecosystem events."""
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"


class UnauthorizedSettlementBypassError(ValueError):
    """Raised when an ecosystem event attempts to bypass authoritative financial or match settlement."""
    pass


@dataclass(frozen=True, slots=True)
class EcosystemActor:
    """Identity and authorization context of the initiating actor."""
    actor_id: str
    actor_type: str = "user"  # "user" | "agent" | "system" | "staff" | "player" | "sponsor"
    roles: tuple[str, ...] = field(default_factory=tuple)
    display_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "roles": list(self.roles),
            "display_name": self.display_name,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> EcosystemActor | None:
        if not data:
            return None
        return cls(
            actor_id=str(data.get("actor_id") or ""),
            actor_type=str(data.get("actor_type") or "user"),
            roles=tuple(str(r) for r in (data.get("roles") or [])),
            display_name=data.get("display_name"),
        )


@dataclass(frozen=True, slots=True)
class EcosystemSubject:
    """Primary entity affected by this ecosystem event."""
    subject_id: str
    subject_type: str  # "player" | "facility" | "campaign" | "song" | "match" | "order"
    title: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject_id": self.subject_id,
            "subject_type": self.subject_type,
            "title": self.title,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> EcosystemSubject | None:
        if not data:
            return None
        return cls(
            subject_id=str(data.get("subject_id") or ""),
            subject_type=str(data.get("subject_type") or ""),
            title=data.get("title"),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(frozen=True, slots=True)
class EcosystemClubContext:
    """Club authority context for multi-tenant isolation and routing."""
    club_id: str
    club_name: str | None = None
    division_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "club_id": self.club_id,
            "club_name": self.club_name,
            "division_id": self.division_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> EcosystemClubContext | None:
        if not data:
            return None
        return cls(
            club_id=str(data.get("club_id") or ""),
            club_name=data.get("club_name"),
            division_id=data.get("division_id"),
        )


@dataclass(frozen=True, slots=True)
class EcosystemEvidence:
    """Origin telemetry and verification data."""
    source: str  # "ui_action" | "simulation_tick" | "cron" | "webhook" | "ai_agent"
    ip_address: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "ip_address": self.ip_address,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> EcosystemEvidence | None:
        if not data:
            return None
        return cls(
            source=str(data.get("source") or "unknown"),
            ip_address=data.get("ip_address"),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(frozen=True)
class EcosystemEvent:
    """
    Authoritative Versioned Typed GTEX Ecosystem Event Contract.
    Conforms to DomainEvent and EventOutbox standards.
    """
    domain: EcosystemDomain | str
    name: str
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=utcnow)
    version: int = 1
    producer: str = "gtex.ecosystem"
    actor: EcosystemActor | None = None
    subject: EcosystemSubject | None = None
    club_context: EcosystemClubContext | None = None
    evidence: EcosystemEvidence | None = None
    idempotency_key: str | None = None
    correlation_id: str | None = None
    priority: EcosystemEventPriority = EcosystemEventPriority.NORMAL
    resolution_state: EcosystemResolutionStatus | None = None
    headers: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Invariant check: Protect financial ledgers & match simulation from bypass
        if "bypass_financial_ledger" in self.payload or "force_wallet_credit" in self.payload:
            raise UnauthorizedSettlementBypassError(
                "Direct ledger balance bypass is strictly forbidden in ecosystem events."
            )
        if "bypass_match_engine" in self.payload:
            raise UnauthorizedSettlementBypassError(
                "Authoritative 2D match simulation cannot be bypassed via ecosystem events."
            )

    @property
    def event_type(self) -> str:
        d = self.domain.value if isinstance(self.domain, EcosystemDomain) else str(self.domain)
        return f"{d}.{self.name}"

    def envelope(self) -> dict[str, Any]:
        d_val = self.domain.value if isinstance(self.domain, EcosystemDomain) else str(self.domain)
        prio_val = self.priority.value if isinstance(self.priority, EcosystemEventPriority) else str(self.priority)
        res_val = (
            self.resolution_state.value
            if isinstance(self.resolution_state, EcosystemResolutionStatus)
            else (str(self.resolution_state) if self.resolution_state is not None else None)
        )

        headers = dict(self.headers)
        if self.idempotency_key:
            headers["idempotency_key"] = self.idempotency_key
        headers["correlation_id"] = self.correlation_id or self.event_id
        headers["priority"] = prio_val
        headers["ecosystem_version"] = self.version
        headers["ecosystem_domain"] = d_val

        payload = dict(self.payload)
        payload["__ecosystem__"] = {
            "domain": d_val,
            "name": self.name,
            "actor": self.actor.to_dict() if self.actor else None,
            "subject": self.subject.to_dict() if self.subject else None,
            "club_context": self.club_context.to_dict() if self.club_context else None,
            "evidence": self.evidence.to_dict() if self.evidence else None,
            "resolution_state": res_val,
            "version": self.version,
        }

        agg_id = (
            (self.club_context.club_id if self.club_context else None)
            or (self.subject.subject_id if self.subject else None)
            or self.event_id
        )

        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "aggregate_id": agg_id,
            "aggregate_type": d_val,
            "version": self.version,
            "timestamp": self.occurred_at,
            "producer": self.producer,
            "partition_key": agg_id,
            "payload": make_json_safe(payload),
            "headers": make_json_safe(headers),
        }

    def to_domain_event(self) -> DomainEvent:
        env = self.envelope()
        return DomainEvent(
            name=env["event_type"],
            payload=env["payload"],
            event_id=env["event_id"],
            occurred_at=self.occurred_at,
            aggregate_id=env["aggregate_id"],
            aggregate_type=env["aggregate_type"],
            version=self.version,
            producer=self.producer,
            partition_key=env["partition_key"],
            headers=env["headers"],
        )

    @classmethod
    def from_outbox(cls, row: EventOutbox) -> EcosystemEvent:
        payload = dict(row.payload_json or {})
        eco_meta = payload.pop("__ecosystem__", {})
        headers = dict(row.headers_json or {})

        domain_str = eco_meta.get("domain") or headers.get("ecosystem_domain") or row.aggregate_type or "system"
        name_str = eco_meta.get("name") or (
            row.event_type.split(".", 1)[-1] if "." in row.event_type else row.event_type
        )

        actor = EcosystemActor.from_dict(eco_meta.get("actor"))
        subject = EcosystemSubject.from_dict(eco_meta.get("subject"))
        club_context = EcosystemClubContext.from_dict(eco_meta.get("club_context"))
        evidence = EcosystemEvidence.from_dict(eco_meta.get("evidence"))

        prio_str = headers.get("priority", "normal")
        try:
            priority = EcosystemEventPriority(prio_str)
        except ValueError:
            priority = EcosystemEventPriority.NORMAL

        res_str = eco_meta.get("resolution_state")
        resolution_state = None
        if res_str:
            try:
                resolution_state = EcosystemResolutionStatus(res_str)
            except ValueError:
                resolution_state = None

        return cls(
            domain=domain_str,
            name=name_str,
            payload=payload,
            event_id=row.event_id,
            occurred_at=row.occurred_at,
            version=row.version,
            producer=row.producer,
            actor=actor,
            subject=subject,
            club_context=club_context,
            evidence=evidence,
            idempotency_key=headers.get("idempotency_key"),
            correlation_id=headers.get("correlation_id"),
            priority=priority,
            resolution_state=resolution_state,
            headers=headers,
        )


TransformFunc = Callable[[dict[str, Any], dict[str, Any]], tuple[dict[str, Any], dict[str, Any]]]


class EcosystemEventVersionAdapter:
    """
    Registers and executes schema evolution adapters across event versions.
    Enables backward and forward compatibility as events evolve.
    """
    _transformers: dict[tuple[str, int, int], TransformFunc] = {}

    @classmethod
    def register(cls, event_type: str, from_version: int, to_version: int, transform: TransformFunc) -> None:
        cls._transformers[(event_type, from_version, to_version)] = transform

    @classmethod
    def clear(cls) -> None:
        cls._transformers.clear()

    @classmethod
    def adapt(cls, event: EcosystemEvent, target_version: int) -> EcosystemEvent:
        if event.version == target_version:
            return event
        current_version = event.version
        payload = dict(event.payload)
        headers = dict(event.headers)
        event_type = event.event_type

        while current_version < target_version:
            next_version = current_version + 1
            key = (event_type, current_version, next_version)
            if key in cls._transformers:
                payload, headers = cls._transformers[key](payload, headers)
            current_version = next_version

        return EcosystemEvent(
            domain=event.domain,
            name=event.name,
            payload=payload,
            event_id=event.event_id,
            occurred_at=event.occurred_at,
            version=target_version,
            producer=event.producer,
            actor=event.actor,
            subject=event.subject,
            club_context=event.club_context,
            evidence=event.evidence,
            idempotency_key=event.idempotency_key,
            correlation_id=event.correlation_id,
            priority=event.priority,
            resolution_state=event.resolution_state,
            headers=headers,
        )


EcosystemConsumerHandler = Callable[[EcosystemEvent, Session], None]


@dataclass(slots=True)
class EcosystemConsumerRegistration:
    """Configuration and filters for registered ecosystem event consumers."""
    name: str
    domains: set[str]
    event_types: set[str]
    handler: EcosystemConsumerHandler
    max_retries: int = 3
    required_roles: set[str] = field(default_factory=set)
    target_version: int = 1

    def matches(self, event: EcosystemEvent) -> bool:
        domain_val = event.domain.value if isinstance(event.domain, EcosystemDomain) else str(event.domain)
        if "*" not in self.domains and domain_val not in self.domains:
            return False
        if "*" not in self.event_types and event.event_type not in self.event_types:
            return False
        return True

    def is_authorized(self, event: EcosystemEvent) -> bool:
        if not self.required_roles:
            return True
        if event.actor is None:
            return False
        actor_roles = set(event.actor.roles)
        return bool(actor_roles & self.required_roles)


class EcosystemEventBus:
    """
    Authoritative GTEX Ecosystem Event Backbone Engine.
    Extends existing EventOutbox, EventConsumerState, and EventDeadLetter with:
      - Canonical multi-domain contracts
      - Persistent outbox insertion with idempotency deduplication
      - Reliable at-least-once consumer dispatch
      - Role-based permission filtering
      - Version upgrade adaptation
      - Consumer retry budgets & dead-letter archival
      - Strict non-bypass protection for ledgers & matches
    """

    def __init__(self, *, in_memory_publisher: InMemoryEventPublisher | None = None) -> None:
        self._in_memory_publisher = in_memory_publisher or InMemoryEventPublisher()
        self._consumers: dict[str, EcosystemConsumerRegistration] = {}

    @property
    def in_memory_publisher(self) -> InMemoryEventPublisher:
        return self._in_memory_publisher

    def register_consumer(
        self,
        name: str,
        handler: EcosystemConsumerHandler,
        *,
        domains: Sequence[str | EcosystemDomain] = ("*",),
        event_types: Sequence[str] = ("*",),
        required_roles: Sequence[str] = (),
        max_retries: int = 3,
        target_version: int = 1,
    ) -> EcosystemConsumerRegistration:
        """Register a typed, permission-aware event consumer."""
        reg = EcosystemConsumerRegistration(
            name=name,
            domains={d.value if isinstance(d, EcosystemDomain) else str(d) for d in domains},
            event_types=set(event_types),
            handler=handler,
            max_retries=max(1, max_retries),
            required_roles=set(required_roles),
            target_version=target_version,
        )
        self._consumers[name] = reg
        return reg

    def unregister_consumer(self, name: str) -> bool:
        return self._consumers.pop(name, None) is not None

    def publish(self, session: Session, event: EcosystemEvent) -> EventOutbox:
        """
        Persist an ecosystem event to the canonical EventOutbox with idempotency deduplication.
        Defers in-memory delivery until successful database transaction commit.
        """
        # 1. Deduplication by event_id
        existing_by_id = session.scalar(select(EventOutbox).where(EventOutbox.event_id == event.event_id))
        if existing_by_id is not None:
            logger.info("ecosystem.event.idempotent_duplicate_by_id event_id=%s", event.event_id)
            return existing_by_id

        # 2. Deduplication by idempotency_key
        if event.idempotency_key:
            # Query recent outbox events with the same event_type to match idempotency_key in headers
            candidates = session.scalars(
                select(EventOutbox)
                .where(EventOutbox.event_type == event.event_type)
                .order_by(EventOutbox.occurred_at.desc())
                .limit(100)
            ).all()
            for row in candidates:
                if (row.headers_json or {}).get("idempotency_key") == event.idempotency_key:
                    logger.info(
                        "ecosystem.event.idempotent_duplicate_by_key key=%s event_id=%s",
                        event.idempotency_key,
                        row.event_id,
                    )
                    return row

        # 3. Create canonical EventOutbox row
        outbox_row = build_outbox_event(domain_event=event)
        session.add(outbox_row)
        session.flush()

        # 4. Defer in-memory pubsub until session commit
        defer_event_publish_until_commit(
            session,
            publisher=self._in_memory_publisher,
            event=event.to_domain_event(),
        )

        return outbox_row

    def dispatch_pending_events(self, session: Session, *, batch_size: int = 50) -> int:
        """
        Claim and dispatch pending EventOutbox rows to registered ecosystem consumers.
        Applies idempotency, role-based permission checks, retry budgets, and dead-lettering.
        """
        statement = (
            select(EventOutbox)
            .where(
                or_(
                    EventOutbox.status == "pending",
                    and_(
                        EventOutbox.status == "processing",
                        EventOutbox.claimed_at.is_not(None),
                    ),
                )
            )
            .order_by(EventOutbox.occurred_at.asc())
            .limit(batch_size)
        )
        rows = list(session.scalars(statement).all())
        if not rows:
            return 0

        dispatched_count = 0
        now = utcnow()

        for row in rows:
            claim_token = str(uuid4())
            row.status = "processing"
            row.claimed_at = now
            row.claim_token = claim_token
            session.flush()

            eco_event = EcosystemEvent.from_outbox(row)
            all_successful = True
            any_dead_lettered = False

            # Find matching consumers
            matching = [c for c in self._consumers.values() if c.matches(eco_event)]

            for consumer in matching:
                # 1. Consumer-level idempotency check
                state = session.scalar(
                    select(EventConsumerState).where(
                        EventConsumerState.consumer_name == consumer.name,
                        EventConsumerState.event_id == eco_event.event_id,
                    )
                )
                if state is not None and state.status == "processed":
                    continue  # Already processed by this consumer

                # 2. Permission-aware check
                if not consumer.is_authorized(eco_event):
                    logger.warning(
                        "ecosystem.consumer.permission_denied consumer=%s event_id=%s actor_roles=%s required=%s",
                        consumer.name,
                        eco_event.event_id,
                        eco_event.actor.roles if eco_event.actor else (),
                        consumer.required_roles,
                    )
                    if state is None:
                        state = EventConsumerState(
                            consumer_name=consumer.name,
                            event_id=eco_event.event_id,
                            event_type=eco_event.event_type,
                            aggregate_id=row.aggregate_id,
                            status="permission_denied",
                            attempt_count=1,
                            last_error="Actor lacks required roles",
                            processed_at=now,
                        )
                        session.add(state)
                    else:
                        state.status = "permission_denied"
                        state.last_error = "Actor lacks required roles"
                        state.processed_at = now
                    continue

                # 3. Version adaptation
                adapted = EcosystemEventVersionAdapter.adapt(eco_event, consumer.target_version)

                # 4. Invoke consumer handler
                if state is None:
                    state = EventConsumerState(
                        consumer_name=consumer.name,
                        event_id=eco_event.event_id,
                        event_type=eco_event.event_type,
                        aggregate_id=row.aggregate_id,
                        status="processing",
                        attempt_count=1,
                        last_attempt_at=now,
                    )
                    session.add(state)
                else:
                    state.attempt_count += 1
                    state.last_attempt_at = now
                    state.status = "processing"

                try:
                    # Run in savepoint so consumer failures do not poison the session
                    with session.begin_nested():
                        consumer.handler(adapted, session)
                    state.status = "processed"
                    state.processed_at = utcnow()
                    state.last_error = None
                except Exception as exc:
                    error_msg = f"{type(exc).__name__}: {exc}"
                    logger.exception(
                        "ecosystem.consumer.failed consumer=%s event_id=%s attempt=%s",
                        consumer.name,
                        eco_event.event_id,
                        state.attempt_count,
                    )
                    state.last_error = error_msg
                    if state.attempt_count >= consumer.max_retries:
                        state.status = "dead_letter"
                        state.dead_lettered_at = utcnow()
                        any_dead_lettered = True
                        all_successful = False

                        # Insert audit dead letter record
                        dead_letter = EventDeadLetter(
                            consumer_name=consumer.name,
                            event_id=eco_event.event_id,
                            event_type=eco_event.event_type,
                            aggregate_id=row.aggregate_id,
                            attempts=state.attempt_count,
                            payload_json=make_json_safe(adapted.envelope()["payload"]),
                            headers_json=make_json_safe(adapted.envelope()["headers"]),
                            last_error=error_msg,
                            dead_lettered_at=utcnow(),
                        )
                        session.add(dead_letter)
                    else:
                        state.status = "retry"
                        all_successful = False

            # Update row status
            if any_dead_lettered:
                row.status = "dead_letter"
                row.dead_lettered_at = utcnow()
            elif all_successful:
                row.status = "processed"
                row.processed_at = utcnow()
                row.claim_token = None
                row.claimed_at = None
                dispatched_count += 1
            else:
                row.status = "pending"  # Eligible for next retry cycle
                row.claim_token = None
                row.claimed_at = None

            session.flush()

        return dispatched_count


# Global singleton instance of the GTEX Ecosystem Event Bus
gtex_ecosystem_bus = EcosystemEventBus()
