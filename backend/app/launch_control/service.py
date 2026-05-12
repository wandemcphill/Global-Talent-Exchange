from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.models.admin_rules import AdminBetaAccessGrant, AdminFeatureFlag, AdminFeatureFlagAuditLog
from app.models.base import utcnow
from app.models.notification_center import NotificationPreference
from app.models.notification_record import NotificationRecord
from app.models.user import User, UserRole
from app.notifications.service import NotificationEventMatrixService, NotificationServiceError

from .schemas import (
    AdminCommandRouteView,
    BetaAccessGrantRequest,
    BetaAccessGrantView,
    ClientFeatureFlagView,
    FeatureFlagAuditEventView,
    LaunchControlDashboardView,
    LaunchControlFeatureFlagView,
    LaunchControlFlagUpdateRequest,
    LaunchState,
    ModuleHealthView,
)

LAUNCH_STATES = {item.value for item in LaunchState}

COMMAND_ROUTE_CATALOG: tuple[dict[str, str], ...] = (
    {
        "module_key": "launch_control",
        "title": "Launch Control",
        "description": "Batch 34 rollout states, kill switches, beta access, and module health.",
        "route": "/admin/launch-control",
        "feature_key": "launch_control",
    },
    {
        "module_key": "operations_readiness",
        "title": "Operations Readiness",
        "description": "Production diagnostics, ledger health, risk queues, launch gates, and worker status.",
        "route": "/admin/ops",
        "feature_key": "operations_readiness",
    },
    {
        "module_key": "global_search",
        "title": "Global Search",
        "description": "Role-aware search across players, clubs, orders, disputes, news, and Batch 24-34 loops.",
        "route": "/app/home",
        "feature_key": "global_search",
    },
    {
        "module_key": "club_lifecycle",
        "title": "Club Lifecycle",
        "description": "Club readiness, lifecycle state, eligibility checks, operating dashboards, and squad launch.",
        "route": "/app/club",
        "feature_key": "club_lifecycle",
    },
    {
        "module_key": "squad_registration",
        "title": "Squad Registration",
        "description": "Position balance, registered squad locks, competition eligibility, and admin overrides.",
        "route": "/app/club",
        "feature_key": "club_lifecycle",
    },
    {
        "module_key": "academy_regens",
        "title": "Academy Regens",
        "description": "Academy generation, training plans, portrait assignment, contracts, and senior promotion.",
        "route": "/world/regens",
        "feature_key": "academy_regens",
    },
    {
        "module_key": "transfer_hub",
        "title": "Transfer Hub",
        "description": "Loans, swaps, private bids, release clauses, and deadline controls.",
        "route": "/app/market",
        "feature_key": "transfer_hub",
    },
    {
        "module_key": "coin_traders",
        "title": "Coin Traders",
        "description": "Liquidity partners, escrow windows, fiat/coin order review, and disputes.",
        "route": "/app/coin-traders",
        "feature_key": "coin_traders",
    },
    {
        "module_key": "staff_marketplace",
        "title": "Staff Marketplace",
        "description": "Managers, agents, scouts, coaches, contract terms, commissions, and assignments.",
        "route": "/app/club",
        "feature_key": "staff_marketplace",
    },
    {
        "module_key": "sponsorships",
        "title": "Sponsorships",
        "description": "Sponsor packages, brand assets, contract activation, performance analytics, and payouts.",
        "route": "/app/club",
        "feature_key": "sponsorships",
    },
    {
        "module_key": "fan_coin",
        "title": "Fan Economy",
        "description": "Fan Coin, predictions, fan wars, gifts, streaks, and reward settlement.",
        "route": "/app/community",
        "feature_key": "fan_coin",
    },
    {
        "module_key": "fan_predictions",
        "title": "Fan Predictions",
        "description": "Prediction markets, token spend, settlement, Fan Coin rewards, and abuse controls.",
        "route": "/app/community",
        "feature_key": "predictions",
    },
    {
        "module_key": "fan_wars",
        "title": "Fan Wars",
        "description": "Fanbase profiles, points, leaderboards, rewards, streaks, and moderation signals.",
        "route": "/app/community",
        "feature_key": "fan_wars",
    },
    {
        "module_key": "newgen_portraits",
        "title": "NewGen Portraits",
        "description": "Portrait assignment, fallback generation, moderation, and diagnostics.",
        "route": "/world/regens",
        "feature_key": "newgen_portraits",
    },
    {
        "module_key": "ticketing",
        "title": "Ticketing",
        "description": "Ticket inventory, resale, attendance rewards, and stadium revenue.",
        "route": "/app/play",
        "feature_key": "ticketing",
    },
    {
        "module_key": "broadcast",
        "title": "Broadcast",
        "description": "Clips, highlights, rights, premium packages, and creator revenue.",
        "route": "/broadcast/live",
        "feature_key": "broadcast",
    },
    {
        "module_key": "viral_clips",
        "title": "Viral Clips",
        "description": "Clip moderation, viral ranking, sponsored clips, blocked appeals, and news publishing.",
        "route": "/news",
        "feature_key": "viral_clips",
    },
    {
        "module_key": "player_card_marketplace",
        "title": "Player Cards",
        "description": "Collectible cards, packs, offers, listings, burn, and fuse.",
        "route": "/player-cards",
        "feature_key": "player_card_marketplace",
    },
    {
        "module_key": "club_sale_market",
        "title": "Club Sale Market",
        "description": "Valuation, due diligence, escrow, approval, and ownership transfer.",
        "route": "/clubs/sale-market",
        "feature_key": "club_sale_market",
    },
    {
        "module_key": "federations",
        "title": "Federations",
        "description": "Federation roles, rules, rankings, sanctions, and national eligibility.",
        "route": "/app/play",
        "feature_key": "federations",
    },
)


@dataclass(slots=True)
class LaunchControlService:
    session: Session

    def list_flags(self) -> list[AdminFeatureFlag]:
        statement = select(AdminFeatureFlag).order_by(AdminFeatureFlag.feature_key.asc())
        return list(self.session.scalars(statement).all())

    def dashboard(self) -> LaunchControlDashboardView:
        return LaunchControlDashboardView(
            flags=[self.map_flag(flag) for flag in self.list_flags()],
            beta_grants=[self.map_beta_grant(grant) for grant in self.list_beta_grants()],
            recent_audit_events=[self.map_audit_event(event) for event in self.list_audit_events()],
            command_routes=self.command_router(),
            module_health=self.module_health(),
        )

    def update_flag(
        self,
        *,
        actor: User,
        feature_key: str,
        payload: LaunchControlFlagUpdateRequest,
        action: str = "flag_updated",
    ) -> AdminFeatureFlag:
        flag = self._get_or_create_flag(feature_key)
        previous = self._flag_snapshot(flag)
        if payload.title is not None:
            flag.title = payload.title
        if payload.description is not None:
            flag.description = payload.description
        if payload.enabled is not None:
            flag.enabled = payload.enabled
        if payload.audience is not None:
            flag.audience = payload.audience
        if payload.launch_state is not None:
            flag.launch_state = payload.launch_state.value
        if payload.allowed_roles is not None:
            flag.allowed_roles_json = self._normalize_string_list(payload.allowed_roles)
        if payload.allowed_regions is not None:
            flag.allowed_regions_json = self._normalize_string_list(payload.allowed_regions, uppercase=True)
        if payload.beta_only is not None:
            flag.beta_only = payload.beta_only
        if payload.kill_switch_enabled is not None:
            flag.kill_switch_enabled = payload.kill_switch_enabled
        if payload.maintenance_message is not None:
            flag.maintenance_message = payload.maintenance_message.strip() or None
        if payload.metadata is not None:
            flag.metadata_json = dict(payload.metadata)
        flag.updated_by_user_id = actor.id
        self.session.flush()
        next_snapshot = self._flag_snapshot(flag)
        if previous != next_snapshot:
            self._add_audit(
                actor=actor,
                feature_key=feature_key,
                action=action,
                previous=previous,
                next_snapshot=next_snapshot,
                reason=payload.reason,
            )
            event_key = "kill_switch_enabled" if (
                not bool(previous.get("kill_switch_enabled"))
                and bool(next_snapshot.get("kill_switch_enabled"))
            ) else "feature_flag_changed"
            self._publish_admin_event(
                event_key=event_key,
                actor=actor,
                feature_key=feature_key,
                action=action,
                reason=payload.reason,
                previous=previous,
                next_snapshot=next_snapshot,
            )
        self.session.flush()
        return flag

    def set_enabled(self, *, actor: User, feature_key: str, enabled: bool, reason: str | None = None) -> AdminFeatureFlag:
        return self.update_flag(
            actor=actor,
            feature_key=feature_key,
            payload=LaunchControlFlagUpdateRequest(enabled=enabled, reason=reason),
            action="flag_enabled" if enabled else "flag_disabled",
        )

    def set_kill_switch(
        self,
        *,
        actor: User,
        feature_key: str,
        enabled: bool,
        reason: str | None = None,
    ) -> AdminFeatureFlag:
        return self.update_flag(
            actor=actor,
            feature_key=feature_key,
            payload=LaunchControlFlagUpdateRequest(kill_switch_enabled=enabled, reason=reason),
            action="kill_switch_enabled" if enabled else "kill_switch_disabled",
        )

    def list_beta_grants(self) -> list[AdminBetaAccessGrant]:
        statement = select(AdminBetaAccessGrant).order_by(
            AdminBetaAccessGrant.feature_key.asc(),
            AdminBetaAccessGrant.user_id.asc(),
        )
        return list(self.session.scalars(statement).all())

    def upsert_beta_grant(self, *, actor: User, payload: BetaAccessGrantRequest) -> AdminBetaAccessGrant:
        if self.session.get(User, payload.user_id) is None:
            raise ValueError("User not found for beta access grant.")
        grant = self.session.scalar(
            select(AdminBetaAccessGrant).where(
                AdminBetaAccessGrant.feature_key == payload.feature_key,
                AdminBetaAccessGrant.user_id == payload.user_id,
            )
        )
        previous = {} if grant is None else self._grant_snapshot(grant)
        if grant is None:
            grant = AdminBetaAccessGrant(feature_key=payload.feature_key, user_id=payload.user_id)
            self.session.add(grant)
        grant.active = payload.active
        grant.notes = payload.notes
        grant.expires_at = payload.expires_at
        grant.granted_by_user_id = actor.id
        self.session.flush()
        self._add_audit(
            actor=actor,
            feature_key=payload.feature_key,
            action="beta_access_grant_upserted",
            previous=previous,
            next_snapshot=self._grant_snapshot(grant),
            reason=payload.notes,
        )
        self._publish_admin_event(
            event_key="beta_access_granted" if grant.active else "beta_access_revoked",
            actor=actor,
            feature_key=payload.feature_key,
            action="beta_access_grant_upserted",
            reason=payload.notes,
            previous=previous,
            next_snapshot=self._grant_snapshot(grant),
            target_user_ids=(actor.id, payload.user_id),
        )
        self.session.flush()
        return grant

    def revoke_beta_grant(self, *, actor: User, feature_key: str, user_id: str) -> AdminBetaAccessGrant:
        grant = self.session.scalar(
            select(AdminBetaAccessGrant).where(
                AdminBetaAccessGrant.feature_key == feature_key,
                AdminBetaAccessGrant.user_id == user_id,
            )
        )
        if grant is None:
            raise ValueError("Beta access grant not found.")
        previous = self._grant_snapshot(grant)
        grant.active = False
        grant.granted_by_user_id = actor.id
        self.session.flush()
        self._add_audit(
            actor=actor,
            feature_key=feature_key,
            action="beta_access_grant_revoked",
            previous=previous,
            next_snapshot=self._grant_snapshot(grant),
        )
        self._publish_admin_event(
            event_key="beta_access_revoked",
            actor=actor,
            feature_key=feature_key,
            action="beta_access_grant_revoked",
            previous=previous,
            next_snapshot=self._grant_snapshot(grant),
            target_user_ids=(actor.id, user_id),
        )
        self.session.flush()
        return grant

    def list_audit_events(self, *, limit: int = 25) -> list[AdminFeatureFlagAuditLog]:
        statement = select(AdminFeatureFlagAuditLog).order_by(AdminFeatureFlagAuditLog.created_at.desc()).limit(limit)
        return list(self.session.scalars(statement).all())

    def client_flags(self, *, user: User | None) -> list[ClientFeatureFlagView]:
        grants = self._active_beta_grants_for_user(user)
        visible: list[ClientFeatureFlagView] = []
        for flag in self.list_flags():
            if not self._is_client_visible(flag, user=user, beta_grants=grants):
                continue
            enabled = self._is_effectively_enabled(flag)
            visible.append(
                ClientFeatureFlagView(
                    feature_key=flag.feature_key,
                    title=flag.title,
                    enabled=enabled,
                    launch_state=self._launch_state(flag),
                    route=self._route_for(flag),
                    maintenance_message=flag.maintenance_message if flag.launch_state == LaunchState.MAINTENANCE else None,
                )
            )
        return visible

    def command_router(self) -> list[AdminCommandRouteView]:
        flags = {flag.feature_key: flag for flag in self.list_flags()}
        routes: list[AdminCommandRouteView] = []
        for item in COMMAND_ROUTE_CATALOG:
            flag_key = item.get("feature_key")
            flag = flags.get(flag_key or "")
            routes.append(
                AdminCommandRouteView(
                    module_key=item["module_key"],
                    title=item["title"],
                    description=item["description"],
                    route=self._route_for(flag) if flag is not None else item["route"],
                    feature_key=flag_key,
                    launch_state=self._launch_state(flag) if flag is not None else None,
                    enabled=self._is_effectively_enabled(flag) if flag is not None else True,
                )
            )
        return routes

    def module_health(self) -> list[ModuleHealthView]:
        flags = {flag.feature_key: flag for flag in self.list_flags()}
        health: list[ModuleHealthView] = []
        for item in COMMAND_ROUTE_CATALOG:
            feature_key = item.get("feature_key")
            flag = flags.get(feature_key or "")
            if flag is None:
                health.append(
                    ModuleHealthView(
                        module_key=item["module_key"],
                        status="not_configured",
                        detail="No canonical AdminFeatureFlag row exists yet.",
                        feature_key=feature_key,
                    )
                )
                continue
            state = self._launch_state(flag)
            if flag.kill_switch_enabled:
                status = "kill_switch"
                detail = "Kill switch is active; client actions are blocked."
            elif state in {LaunchState.DISABLED, LaunchState.HIDDEN}:
                status = state.value
                detail = "Feature is intentionally unavailable outside admin launch control."
            elif state in {LaunchState.PAUSED, LaunchState.MAINTENANCE}:
                status = state.value
                detail = flag.maintenance_message or "Feature is temporarily not accepting traffic."
            elif not flag.enabled:
                status = "off"
                detail = "Feature flag is configured but disabled."
            elif state in {LaunchState.INTERNAL, LaunchState.BETA}:
                status = "gated"
                detail = f"Feature is enabled for {state.value} rollout access."
            else:
                status = "online"
                detail = "Feature is public and enabled."
            health.append(
                ModuleHealthView(
                    module_key=item["module_key"],
                    status=status,
                    detail=detail,
                    feature_key=feature_key,
                    launch_state=state,
                    kill_switch_enabled=flag.kill_switch_enabled,
                )
            )
        return health

    def map_flag(self, flag: AdminFeatureFlag) -> LaunchControlFeatureFlagView:
        return LaunchControlFeatureFlagView(
            id=flag.id,
            feature_key=flag.feature_key,
            title=flag.title,
            description=flag.description,
            enabled=flag.enabled,
            audience=flag.audience,
            launch_state=self._launch_state(flag),
            allowed_roles=list(flag.allowed_roles_json or []),
            allowed_regions=list(flag.allowed_regions_json or []),
            beta_only=flag.beta_only,
            kill_switch_enabled=flag.kill_switch_enabled,
            maintenance_message=flag.maintenance_message,
            metadata=dict(flag.metadata_json or {}),
            route=self._route_for(flag),
            updated_at=flag.updated_at,
        )

    def map_beta_grant(self, grant: AdminBetaAccessGrant) -> BetaAccessGrantView:
        return BetaAccessGrantView(
            id=grant.id,
            feature_key=grant.feature_key,
            user_id=grant.user_id,
            active=grant.active,
            notes=grant.notes,
            expires_at=grant.expires_at,
            granted_by_user_id=grant.granted_by_user_id,
            created_at=grant.created_at,
            updated_at=grant.updated_at,
        )

    def map_audit_event(self, event: AdminFeatureFlagAuditLog) -> FeatureFlagAuditEventView:
        return FeatureFlagAuditEventView(
            id=event.id,
            feature_key=event.feature_key,
            action=event.action,
            previous=dict(event.previous_json or {}),
            next=dict(event.next_json or {}),
            reason=event.reason,
            actor_user_id=event.actor_user_id,
            created_at=event.created_at,
        )

    def _get_or_create_flag(self, feature_key: str) -> AdminFeatureFlag:
        flag = self.session.scalar(select(AdminFeatureFlag).where(AdminFeatureFlag.feature_key == feature_key))
        if flag is not None:
            return flag
        title = feature_key.replace("_", " ").replace("-", " ").title()
        flag = AdminFeatureFlag(feature_key=feature_key, title=title, enabled=False, audience="internal")
        self.session.add(flag)
        self.session.flush()
        return flag

    def _is_client_visible(
        self,
        flag: AdminFeatureFlag,
        *,
        user: User | None,
        beta_grants: set[str],
    ) -> bool:
        state = self._launch_state(flag)
        if state in {LaunchState.HIDDEN, LaunchState.DISABLED}:
            return False
        if state == LaunchState.INTERNAL and not self._is_admin(user):
            return False
        if (state == LaunchState.BETA or flag.beta_only) and not self._has_beta_access(flag, user, beta_grants):
            return False
        allowed_roles = {item.lower() for item in (flag.allowed_roles_json or [])}
        if allowed_roles and not (self._is_admin(user) or self._role_value(user) in allowed_roles):
            return False
        allowed_regions = {item.upper() for item in (flag.allowed_regions_json or [])}
        if allowed_regions:
            region = self._region_value(user)
            if region is None or region not in allowed_regions:
                return False
        return True

    def _has_beta_access(self, flag: AdminFeatureFlag, user: User | None, beta_grants: set[str]) -> bool:
        if self._is_admin(user):
            return True
        if user is None:
            return False
        return flag.feature_key in beta_grants

    def _active_beta_grants_for_user(self, user: User | None) -> set[str]:
        if user is None:
            return set()
        now = utcnow()
        statement = select(AdminBetaAccessGrant).where(
            AdminBetaAccessGrant.user_id == user.id,
            AdminBetaAccessGrant.active.is_(True),
        )
        grants = self.session.scalars(statement).all()
        return {
            grant.feature_key
            for grant in grants
            if grant.expires_at is None or self._as_aware(grant.expires_at) > now
        }

    def _is_effectively_enabled(self, flag: AdminFeatureFlag | None) -> bool:
        if flag is None:
            return False
        state = self._launch_state(flag)
        return flag.enabled and not flag.kill_switch_enabled and state not in {
            LaunchState.DISABLED,
            LaunchState.HIDDEN,
            LaunchState.PAUSED,
            LaunchState.MAINTENANCE,
        }

    def _launch_state(self, flag: AdminFeatureFlag | None) -> LaunchState:
        raw = (getattr(flag, "launch_state", None) or LaunchState.PUBLIC.value).strip().lower()
        if raw not in LAUNCH_STATES:
            return LaunchState.PUBLIC
        return LaunchState(raw)

    def _route_for(self, flag: AdminFeatureFlag | None) -> str | None:
        if flag is None:
            return None
        metadata = flag.metadata_json or {}
        route = metadata.get("route")
        return route if isinstance(route, str) and route.strip() else None

    def _flag_snapshot(self, flag: AdminFeatureFlag) -> dict[str, Any]:
        return {
            "feature_key": flag.feature_key,
            "title": flag.title,
            "description": flag.description,
            "enabled": flag.enabled,
            "audience": flag.audience,
            "launch_state": flag.launch_state,
            "allowed_roles": list(flag.allowed_roles_json or []),
            "allowed_regions": list(flag.allowed_regions_json or []),
            "beta_only": flag.beta_only,
            "kill_switch_enabled": flag.kill_switch_enabled,
            "maintenance_message": flag.maintenance_message,
            "metadata": dict(flag.metadata_json or {}),
        }

    def _grant_snapshot(self, grant: AdminBetaAccessGrant) -> dict[str, Any]:
        return {
            "feature_key": grant.feature_key,
            "user_id": grant.user_id,
            "active": grant.active,
            "notes": grant.notes,
            "expires_at": grant.expires_at.isoformat() if grant.expires_at else None,
            "granted_by_user_id": grant.granted_by_user_id,
        }

    def _add_audit(
        self,
        *,
        actor: User,
        feature_key: str,
        action: str,
        previous: dict[str, Any],
        next_snapshot: dict[str, Any],
        reason: str | None = None,
    ) -> None:
        self.session.add(
            AdminFeatureFlagAuditLog(
                feature_key=feature_key,
                action=action,
                previous_json=previous,
                next_json=next_snapshot,
                reason=reason,
                actor_user_id=actor.id,
            )
        )

    def _publish_admin_event(
        self,
        *,
        event_key: str,
        actor: User,
        feature_key: str,
        action: str,
        previous: dict[str, Any],
        next_snapshot: dict[str, Any],
        reason: str | None = None,
        target_user_ids: tuple[str, ...] | None = None,
    ) -> None:
        if not self._notification_tables_available():
            return
        recipients = target_user_ids or tuple(self._admin_user_ids())
        if not recipients:
            recipients = (actor.id,)
        try:
            NotificationEventMatrixService(self.session).publish_event(
                event_key=event_key,
                target_user_ids=recipients,
                resource_id=feature_key,
                metadata_json={
                    "feature_key": feature_key,
                    "action": action,
                    "reason": reason,
                    "actor_user_id": actor.id,
                    "previous": previous,
                    "next": next_snapshot,
                },
            )
        except NotificationServiceError:
            return

    def _admin_user_ids(self) -> list[str]:
        statement = (
            select(User.id)
            .where(User.role.in_([UserRole.ADMIN, UserRole.SUPER_ADMIN]))
            .order_by(User.created_at.asc())
        )
        return [item for item in self.session.scalars(statement).all() if item]

    def _notification_tables_available(self) -> bool:
        inspector = inspect(self.session.get_bind())
        return bool(
            inspector.has_table(NotificationRecord.__tablename__)
            and inspector.has_table(NotificationPreference.__tablename__)
        )

    @staticmethod
    def _normalize_string_list(values: list[str], *, uppercase: bool = False) -> list[str]:
        normalized: list[str] = []
        for value in values:
            item = value.strip()
            if not item:
                continue
            item = item.upper() if uppercase else item.lower()
            if item not in normalized:
                normalized.append(item)
        return normalized

    @staticmethod
    def _role_value(user: User | None) -> str:
        if user is None:
            return "guest"
        role = user.role
        return getattr(role, "value", str(role)).lower()

    @classmethod
    def _is_admin(cls, user: User | None) -> bool:
        return cls._role_value(user) in {UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value}

    @staticmethod
    def _region_value(user: User | None) -> str | None:
        if user is None:
            return None
        for field_name in ("region_code", "country_code", "nationality"):
            raw = getattr(user, field_name, None)
            if isinstance(raw, str) and raw.strip():
                return raw.strip().upper()
        return None

    @staticmethod
    def _as_aware(value: datetime) -> datetime:
        if value.tzinfo is not None:
            return value
        return value.replace(tzinfo=utcnow().tzinfo)
