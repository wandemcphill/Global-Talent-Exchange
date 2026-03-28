from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ingestion.models import Country, Player
from app.models.club_profile import ClubProfile
from app.models.club_sale_market import ClubSaleTransfer
from app.models.club_sponsorship_contract import ClubSponsorshipContract
from app.models.club_sponsorship_payout import ClubSponsorshipPayout
from app.models.competition import UserCompetition
from app.models.competition_match import CompetitionMatch
from app.models.federation import (
    Federation,
    FederationCompetitionType,
    FederationLeague,
    FederationMembership,
    FederationMembershipStatus,
    FederationNarrativeSnapshot,
    FederationProposal,
    FederationProposalStatus,
    FederationRuleAudit,
    FederationRuleAuditStatus,
    FederationSanction,
    FederationSanctionType,
    FederationTreasuryEntry,
    FederationVote,
    FederationVoteType,
)
from app.models.media_engine import MatchRevenueSnapshot
from app.models.notification_record import NotificationRecord
from app.models.player_contract import PlayerContract
from app.models.real_world_hub import RealityMode
from app.models.transfer_market import TransferListing
from app.models.user import User, UserRole

AMOUNT_QUANTUM = Decimal("0.0001")


class FederationError(ValueError):
    pass


class FederationNotFoundError(FederationError):
    pass


class FederationValidationError(FederationError):
    pass


@dataclass(slots=True)
class FederationService:
    session: Session

    def list_federations(self) -> list[Federation]:
        self.refresh_rankings()
        stmt = select(Federation).order_by(Federation.ranking_score.desc(), Federation.reputation_score.desc(), Federation.name.asc())
        return list(self.session.scalars(stmt).all())

    def get_federation(self, federation_id: str) -> Federation:
        federation = self.session.get(Federation, federation_id)
        if federation is None:
            raise FederationNotFoundError("Federation was not found.")
        self._sync_snapshot_fields(federation)
        return federation

    def list_leagues(self, federation_id: str) -> list[FederationLeague]:
        if self.session.get(Federation, federation_id) is None:
            raise FederationNotFoundError("Federation was not found.")
        stmt = select(FederationLeague).where(FederationLeague.federation_id == federation_id).order_by(FederationLeague.created_at.asc())
        return list(self.session.scalars(stmt).all())

    def list_memberships(self, federation_id: str) -> list[FederationMembership]:
        if self.session.get(Federation, federation_id) is None:
            raise FederationNotFoundError("Federation was not found.")
        stmt = select(FederationMembership).where(FederationMembership.federation_id == federation_id).order_by(FederationMembership.created_at.asc())
        return list(self.session.scalars(stmt).all())

    def list_regional_tournaments(self) -> list[dict[str, Any]]:
        federations = list(
            self.session.scalars(
                select(Federation)
                .where(Federation.is_public.is_(True))
                .order_by(Federation.ranking_score.desc(), Federation.name.asc())
            ).all()
        )
        grouped: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "region_code": "global",
                "region_label": "Global",
                "federation_ids": set(),
                "member_club_ids": set(),
                "leagues": [],
            }
        )
        for federation in federations:
            metadata = dict(federation.metadata_json or {})
            region_code = str(
                metadata.get("region_code")
                or metadata.get("region")
                or (federation.rules_json or {}).get("region_code")
                or "global"
            ).strip().lower()
            region_label = str(
                metadata.get("region_label")
                or metadata.get("region_name")
                or metadata.get("region")
                or region_code.replace("_", " ").title()
            ).strip()
            bucket = grouped[region_code]
            bucket["region_code"] = region_code
            bucket["region_label"] = region_label or region_code.replace("_", " ").title()
            bucket["federation_ids"].add(federation.id)

            active_memberships = list(
                self.session.scalars(
                    select(FederationMembership).where(
                        FederationMembership.federation_id == federation.id,
                        FederationMembership.status == FederationMembershipStatus.ACTIVE.value,
                    )
                ).all()
            )
            bucket["member_club_ids"].update(item.club_id for item in active_memberships)
            member_count = len({item.club_id for item in active_memberships})
            leagues = list(
                self.session.scalars(
                    select(FederationLeague)
                    .where(FederationLeague.federation_id == federation.id)
                    .order_by(FederationLeague.created_at.desc(), FederationLeague.name.asc())
                ).all()
            )
            for league in leagues:
                bucket["leagues"].append(
                    {
                        "federation_id": federation.id,
                        "federation_name": federation.name,
                        "league_id": league.id,
                        "linked_competition_id": league.linked_competition_id,
                        "name": league.name,
                        "competition_type": league.competition_type,
                        "season_label": league.season_label,
                        "status": league.status,
                        "member_count": member_count,
                    }
                )

        result: list[dict[str, Any]] = []
        for bucket in grouped.values():
            leagues = sorted(
                bucket["leagues"],
                key=lambda item: (
                    str(item.get("season_label") or ""),
                    str(item.get("name") or ""),
                ),
                reverse=True,
            )
            result.append(
                {
                    "region_code": bucket["region_code"],
                    "region_label": bucket["region_label"],
                    "federation_count": len(bucket["federation_ids"]),
                    "active_league_count": len(leagues),
                    "total_member_clubs": len(bucket["member_club_ids"]),
                    "leagues": leagues,
                }
            )
        result.sort(key=lambda item: (-item["active_league_count"], item["region_label"]))
        return result

    def build_dashboard(self, federation_id: str) -> dict[str, Any]:
        federation = self.get_federation(federation_id)
        leagues = self.list_leagues(federation_id)
        self.refresh_rankings()
        self.session.refresh(federation)
        return {
            "leagues": leagues,
            "rules": dict(federation.rules_json or {}),
            "members": list(federation.members_json or []),
            "reputation": {
                "score": federation.reputation_score,
                "ranking_score": federation.ranking_score,
                "audience_size": federation.audience_size,
                "treasury_balance": federation.treasury_balance,
            },
        }

    def build_governance_view(self, federation_id: str) -> dict[str, Any]:
        self.get_federation(federation_id)
        proposals = list(
            self.session.scalars(
                select(FederationProposal)
                .where(FederationProposal.federation_id == federation_id)
                .order_by(FederationProposal.created_at.desc())
            ).all()
        )
        votes = list(
            self.session.scalars(
                select(FederationVote)
                .where(FederationVote.federation_id == federation_id)
                .order_by(FederationVote.created_at.desc())
            ).all()
        )
        sanctions = list(
            self.session.scalars(
                select(FederationSanction)
                .where(FederationSanction.federation_id == federation_id)
                .order_by(FederationSanction.created_at.desc())
            ).all()
        )
        return {
            "proposals": proposals,
            "votes": votes,
            "sanctions": sanctions,
        }

    def create_federation(
        self,
        *,
        actor: User,
        name: str,
        structure_json: dict[str, Any],
        rules_json: dict[str, Any],
        is_public: bool,
        default_reality_mode: RealityMode,
        metadata_json: dict[str, Any],
    ) -> Federation:
        existing = self.session.scalar(select(Federation).where(func.lower(Federation.name) == name.casefold()))
        if existing is not None:
            raise FederationValidationError("Federation name is already in use.")
        federation = Federation(
            name=name.strip(),
            owner_user_id=actor.id,
            structure_json=dict(structure_json or {}),
            rules_json=self._with_defaults(dict(rules_json or {}), default_reality_mode=default_reality_mode),
            is_public=is_public,
            default_reality_mode=default_reality_mode.value,
            metadata_json=dict(metadata_json or {}),
            members_json=[
                {
                    "user_id": actor.id,
                    "role": "owner_admin",
                    "status": "active",
                }
            ],
        )
        self.session.add(federation)
        self.session.flush()
        self._publish_notification(
            user_ids={actor.id},
            template_key="FEDERATION_CREATED",
            message=f"Federation '{federation.name}' has been created.",
            resource_type="federation",
            resource_id=federation.id,
            metadata_json={"federation_id": federation.id},
        )
        return federation

    def create_league(
        self,
        *,
        actor: User,
        federation_id: str,
        name: str,
        competition_type: FederationCompetitionType,
        format: str,
        divisions_json: list[dict[str, Any]],
        promotion_relegation_rules_json: dict[str, Any],
        entry_requirements_json: dict[str, Any],
        governance_rules_override_json: dict[str, Any],
        season_label: str | None,
        metadata_json: dict[str, Any],
    ) -> FederationLeague:
        federation = self.get_federation(federation_id)
        self._require_owner_or_admin(federation=federation, actor=actor)
        league = FederationLeague(
            federation_id=federation.id,
            name=name.strip(),
            competition_type=competition_type.value,
            format=format.strip(),
            divisions_json=list(divisions_json or []),
            promotion_relegation_rules_json=dict(promotion_relegation_rules_json or {}),
            entry_requirements_json=dict(entry_requirements_json or {}),
            governance_rules_override_json=dict(governance_rules_override_json or {}),
            season_label=season_label,
            metadata_json=dict(metadata_json or {}),
        )
        self.session.add(league)
        self.session.flush()

        competition_shell = UserCompetition(
            host_user_id=actor.id,
            name=league.name,
            description=f"Federation competition for {federation.name}",
            competition_type=self._competition_shell_format(league),
            source_type="federation_league",
            source_id=league.id,
            format=self._competition_shell_format(league),
            visibility="public" if federation.is_public else "private",
            currency="USD",
            metadata_json={
                "federation_id": federation.id,
                "federation_league_id": league.id,
                "competition_type": league.competition_type,
                "format": league.format,
                "season_label": season_label,
            },
        )
        self.session.add(competition_shell)
        self.session.flush()
        league.linked_competition_id = competition_shell.id
        self._sync_snapshot_fields(federation)
        return league

    def create_membership(
        self,
        *,
        actor: User,
        federation_id: str,
        club_id: str,
        user_id: str | None,
        role: str,
        auto_activate: bool,
        entry_requirements_json: dict[str, Any],
        metadata_json: dict[str, Any],
    ) -> FederationMembership:
        federation = self.get_federation(federation_id)
        club = self._require_club(club_id)
        if actor.id not in {club.owner_user_id, federation.owner_user_id} and actor.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            raise FederationValidationError("Only the club owner or federation admins can manage federation entry.")
        membership = self.session.scalar(
            select(FederationMembership).where(
                FederationMembership.federation_id == federation.id,
                FederationMembership.club_id == club.id,
            )
        )
        violations = self._evaluate_entry_requirements(
            federation=federation,
            club=club,
            requested_requirements=entry_requirements_json,
        )
        status = FederationMembershipStatus.ACTIVE.value if auto_activate and not violations else FederationMembershipStatus.PENDING.value
        if membership is None:
            membership = FederationMembership(
                federation_id=federation.id,
                club_id=club.id,
            )
            self.session.add(membership)
        membership.user_id = user_id or club.owner_user_id
        membership.role = role
        membership.status = status
        membership.entry_requirements_json = dict(entry_requirements_json or {})
        membership.metadata_json = {
            **dict(metadata_json or {}),
            "entry_violations": violations,
        }
        self.session.flush()
        self._sync_snapshot_fields(federation)
        return membership

    def create_proposal(
        self,
        *,
        actor: User,
        federation_id: str,
        league_id: str | None,
        proposal_type: str,
        title: str,
        summary: str,
        payload_json: dict[str, Any],
        voting_ends_at: datetime | None,
        metadata_json: dict[str, Any],
    ) -> FederationProposal:
        federation = self.get_federation(federation_id)
        self._require_governance_participant(federation=federation, actor=actor)
        if league_id is not None:
            self._require_league(league_id, federation.id)
        proposal = FederationProposal(
            federation_id=federation.id,
            league_id=league_id,
            proposer_user_id=actor.id,
            proposal_type=proposal_type.strip(),
            title=title.strip(),
            summary=summary.strip(),
            payload_json=dict(payload_json or {}),
            status=FederationProposalStatus.OPEN.value,
            voting_starts_at=datetime.now(UTC),
            voting_ends_at=self._normalize_datetime(voting_ends_at) or (datetime.now(UTC) + timedelta(days=3)),
            metadata_json=dict(metadata_json or {}),
        )
        self.session.add(proposal)
        self.session.flush()
        targets = self._notification_target_user_ids(federation.id)
        self._publish_notification(
            user_ids=targets,
            template_key="RULE_CHANGE_PROPOSED",
            message=f"Rule proposal opened in {federation.name}: {proposal.title}",
            resource_type="federation_proposal",
            resource_id=proposal.id,
            metadata_json={"federation_id": federation.id, "proposal_id": proposal.id},
        )
        self._publish_notification(
            user_ids=targets,
            template_key="VOTE_OPEN",
            message=f"Voting is open for proposal '{proposal.title}'.",
            resource_type="federation_proposal",
            resource_id=proposal.id,
            metadata_json={"federation_id": federation.id, "proposal_id": proposal.id},
        )
        return proposal

    def cast_vote(
        self,
        *,
        actor: User,
        proposal_id: str,
        vote_type: FederationVoteType,
        comment: str | None,
    ) -> tuple[FederationProposal, FederationVote]:
        proposal = self.session.get(FederationProposal, proposal_id)
        if proposal is None:
            raise FederationNotFoundError("Federation proposal was not found.")
        federation = self.get_federation(proposal.federation_id)
        self._require_governance_participant(federation=federation, actor=actor)
        if proposal.status != FederationProposalStatus.OPEN.value:
            raise FederationValidationError("Voting is closed for this proposal.")
        voting_ends_at = self._normalize_datetime(proposal.voting_ends_at)
        if voting_ends_at is not None and voting_ends_at <= datetime.now(UTC):
            raise FederationValidationError("Voting window has ended for this proposal.")
        vote = FederationVote(
            proposal_id=proposal.id,
            federation_id=federation.id,
            user_id=actor.id,
            vote_type=vote_type.value,
            weight=self._vote_weight(federation=federation, actor=actor),
            comment=comment,
            metadata_json={"federation_id": federation.id},
        )
        self.session.add(vote)
        try:
            self.session.flush()
        except IntegrityError as exc:
            raise FederationValidationError("You have already voted on this proposal.") from exc
        self._recompute_vote_totals(proposal)
        return proposal, vote

    def apply_sanction(
        self,
        *,
        actor: User,
        federation_id: str,
        league_id: str | None,
        club_id: str | None,
        player_id: str | None,
        sanction_type: FederationSanctionType,
        reason: str,
        fine_amount: Decimal,
        points_deduction: int,
        suspension_matches: int,
        ends_at: datetime | None,
        metadata_json: dict[str, Any],
    ) -> FederationSanction:
        federation = self.get_federation(federation_id)
        self._require_owner_or_admin(federation=federation, actor=actor)
        if league_id is not None:
            self._require_league(league_id, federation.id)
        sanction = FederationSanction(
            federation_id=federation.id,
            league_id=league_id,
            club_id=club_id,
            player_id=player_id,
            applied_by_user_id=actor.id,
            sanction_type=sanction_type.value,
            reason=reason.strip(),
            fine_amount=self._normalize_amount(fine_amount),
            points_deduction=points_deduction,
            suspension_matches=suspension_matches,
            ends_at=ends_at,
            metadata_json=dict(metadata_json or {}),
        )
        self.session.add(sanction)
        self.session.flush()
        user_targets = self._sanction_targets(club_id=club_id)
        self._publish_notification(
            user_ids=user_targets,
            template_key="SANCTION_APPLIED",
            message=f"Sanction applied in {federation.name}: {sanction.reason[:120]}",
            resource_type="federation_sanction",
            resource_id=sanction.id,
            metadata_json={"federation_id": federation.id, "sanction_id": sanction.id},
        )
        return sanction

    def validate_action(
        self,
        *,
        federation_id: str,
        league_id: str | None,
        action_type: str,
        club_id: str | None,
        player_id: str | None,
        proposed_fee: Decimal | None,
        proposed_wage: Decimal | None,
        source_reference: str | None,
        metadata_json: dict[str, Any],
    ) -> dict[str, Any]:
        federation = self.get_federation(federation_id)
        league = self._require_league(league_id, federation.id) if league_id is not None else None
        rules = self._merged_rules(federation=federation, league=league)
        applied_rules: list[str] = []
        violations: list[dict[str, Any]] = []
        player = self.session.get(Player, player_id) if player_id else None

        mode = str(rules.get("competition_player_mode") or federation.default_reality_mode)
        if player is not None and mode in {RealityMode.PURE_REGEN.value, "regen_only"} and player.is_real_player:
            violations.append(
                {
                    "code": "real_player_blocked",
                    "message": "This federation is currently running a regen-only competition policy.",
                    "context": {"player_id": player.id},
                }
            )
        if player is not None and mode == RealityMode.REAL_ONLY.value and not player.is_real_player:
            violations.append(
                {
                    "code": "regen_player_blocked",
                    "message": "This federation is currently configured for real-player-only competitions.",
                    "context": {"player_id": player.id},
                }
            )
        if player is not None:
            applied_rules.append("competition_player_mode")

        if club_id is not None:
            max_active_contracts = self._nested_int(rules, "squad_limits", "max_active_contracts")
            if max_active_contracts is not None:
                active_contracts = self._active_contract_count(club_id)
                projected_count = active_contracts + (1 if player_id and action_type in {"transfer_bid", "competition_entry"} else 0)
                applied_rules.append("squad_limits.max_active_contracts")
                if projected_count > max_active_contracts:
                    violations.append(
                        {
                            "code": "squad_limit_exceeded",
                            "message": f"Projected active squad size {projected_count} exceeds the federation cap of {max_active_contracts}.",
                            "context": {"club_id": club_id, "projected_count": projected_count},
                        }
                    )

            salary_cap = self._nested_decimal(rules, "salary_cap", "max_total_wage")
            if salary_cap is not None:
                current_wage_total = self._active_wage_total(club_id)
                projected_wage_total = current_wage_total + self._normalize_amount(proposed_wage or Decimal("0"))
                applied_rules.append("salary_cap.max_total_wage")
                if projected_wage_total > salary_cap:
                    violations.append(
                        {
                            "code": "salary_cap_exceeded",
                            "message": f"Projected wage bill {projected_wage_total} exceeds the salary cap of {salary_cap}.",
                            "context": {"club_id": club_id, "projected_total": str(projected_wage_total)},
                        }
                    )

        transfer_fee_cap = self._nested_decimal(rules, "transfer_restrictions", "max_fee")
        if transfer_fee_cap is not None and proposed_fee is not None:
            applied_rules.append("transfer_restrictions.max_fee")
            normalized_fee = self._normalize_amount(proposed_fee)
            if normalized_fee > transfer_fee_cap:
                violations.append(
                    {
                        "code": "transfer_fee_exceeded",
                        "message": f"Transfer fee {normalized_fee} exceeds the federation cap of {transfer_fee_cap}.",
                        "context": {"proposed_fee": str(normalized_fee)},
                    }
                )

        if club_id is not None and player is not None:
            max_foreign_players = self._nested_int(rules, "nationality_rules", "max_foreign_players")
            home_country_codes = {
                item.strip().upper()
                for item in self._nested_list(rules, "nationality_rules", "home_country_codes")
                if isinstance(item, str) and item.strip()
            }
            if max_foreign_players is not None and home_country_codes:
                projected_foreign_count = self._projected_foreign_player_count(
                    club_id=club_id,
                    incoming_player=player,
                    home_country_codes=home_country_codes,
                )
                applied_rules.append("nationality_rules.max_foreign_players")
                if projected_foreign_count > max_foreign_players:
                    violations.append(
                        {
                            "code": "nationality_rule_violation",
                            "message": f"Projected foreign-player count {projected_foreign_count} exceeds the cap of {max_foreign_players}.",
                            "context": {"club_id": club_id, "projected_foreign_count": projected_foreign_count},
                        }
                    )

        if action_type == "broadcast_distribution":
            min_share_bps = self._nested_int(rules, "broadcast_rights", "min_federation_share_bps")
            actual_share_bps = int(metadata_json.get("federation_share_bps", 0))
            if min_share_bps is not None:
                applied_rules.append("broadcast_rights.min_federation_share_bps")
                if actual_share_bps < min_share_bps:
                    violations.append(
                        {
                            "code": "broadcast_share_too_low",
                            "message": f"Federation share {actual_share_bps}bps is below the required {min_share_bps}bps.",
                            "context": {"federation_share_bps": actual_share_bps},
                        }
                    )

        if action_type == "ownership_change":
            requires_vote = bool(self._nested_value(rules, "ownership", "require_governance_vote_for_sale"))
            if requires_vote:
                applied_rules.append("ownership.require_governance_vote_for_sale")
                approved_proposal_id = metadata_json.get("approved_proposal_id")
                if not isinstance(approved_proposal_id, str) or not approved_proposal_id.strip():
                    violations.append(
                        {
                            "code": "ownership_vote_required",
                            "message": "Ownership change requires a passed governance proposal before execution.",
                            "context": {"source_reference": source_reference},
                        }
                    )

        audit = FederationRuleAudit(
            federation_id=federation.id,
            league_id=league.id if league is not None else None,
            action_type=action_type.strip(),
            club_id=club_id,
            player_id=player_id,
            status=FederationRuleAuditStatus.VIOLATION.value if violations else FederationRuleAuditStatus.PASSED.value,
            violation_count=len(violations),
            violations_json=violations,
            checked_at=datetime.now(UTC),
            metadata_json={"source_reference": source_reference, **dict(metadata_json or {})},
        )
        self.session.add(audit)
        self.session.flush()
        return {
            "allowed": not violations,
            "applied_rules": applied_rules,
            "violations": violations,
            "audit_id": audit.id,
        }

    def distribute_revenue(
        self,
        *,
        federation_id: str,
        source_type: str,
        source_reference: str | None,
        gross_amount: Decimal | None,
        federation_share_bps: int | None,
        metadata_json: dict[str, Any],
    ) -> FederationTreasuryEntry:
        federation = self.get_federation(federation_id)
        resolved_reference = source_reference or self._default_revenue_reference(federation.id, source_type)
        existing = self.session.scalar(
            select(FederationTreasuryEntry).where(
                FederationTreasuryEntry.federation_id == federation.id,
                FederationTreasuryEntry.source_type == source_type,
                FederationTreasuryEntry.source_reference == resolved_reference,
            )
        )
        if existing is not None:
            return existing

        resolved_amount = gross_amount
        if resolved_amount is None:
            resolved_amount = self._derive_revenue_amount(
                federation_id=federation.id,
                source_type=source_type,
                source_reference=resolved_reference,
            )
        normalized_amount = self._normalize_amount(resolved_amount)
        if normalized_amount <= Decimal("0.0000"):
            raise FederationValidationError("Revenue amount must be greater than zero.")
        share_bps = federation_share_bps if federation_share_bps is not None else self._nested_int(federation.rules_json, "economy", "federation_share_bps", default=1500)
        federation_share = self._normalize_amount((normalized_amount * Decimal(share_bps)) / Decimal(10_000))
        member_club_ids = self._active_member_club_ids(federation.id)
        club_distribution_json: list[dict[str, Any]] = []
        remaining = normalized_amount - federation_share
        if member_club_ids:
            per_club_share = self._normalize_amount(remaining / Decimal(len(member_club_ids)))
            club_distribution_json = [
                {
                    "club_id": club_id,
                    "amount": str(per_club_share),
                }
                for club_id in member_club_ids
            ]
        entry = FederationTreasuryEntry(
            federation_id=federation.id,
            source_type=source_type,
            source_reference=resolved_reference,
            gross_amount=normalized_amount,
            federation_share=federation_share,
            club_distribution_json=club_distribution_json,
            metadata_json={"share_bps": share_bps, **dict(metadata_json or {})},
        )
        self.session.add(entry)
        federation.treasury_balance = self._normalize_amount(Decimal(federation.treasury_balance or 0) + federation_share)
        self.session.flush()
        return entry

    def generate_narratives(self, federation_id: str) -> list[FederationNarrativeSnapshot]:
        federation = self.get_federation(federation_id)
        active_members = len(self._active_member_club_ids(federation.id))
        league_ids, competition_ids = self._federation_competition_context(federation.id)
        match_count = self._competition_match_count(competition_ids)
        sanction_count = int(
            self.session.scalar(
                select(func.count(FederationSanction.id)).where(FederationSanction.federation_id == federation.id)
            )
            or 0
        )
        view_count = int(
            self.session.scalar(
                select(func.coalesce(func.sum(MatchRevenueSnapshot.total_views), 0)).where(
                    MatchRevenueSnapshot.competition_key.in_(competition_ids)
                )
            )
            or 0
        ) if competition_ids else 0
        open_proposals = int(
            self.session.scalar(
                select(func.count(FederationProposal.id)).where(
                    FederationProposal.federation_id == federation.id,
                    FederationProposal.status == FederationProposalStatus.OPEN.value,
                )
            )
            or 0
        )

        narratives = [
            self._upsert_narrative(
                federation_id=federation.id,
                narrative_type="title_race_drama",
                headline="Title race drama",
                body=f"{match_count} federation fixtures are already shaping the title picture across {len(league_ids)} competitions.",
                score=min(100.0, (match_count * 2.0) + (len(league_ids) * 12.0)),
                metadata_json={"match_count": match_count, "league_count": len(league_ids)},
            ),
            self._upsert_narrative(
                federation_id=federation.id,
                narrative_type="relegation_battle",
                headline="Relegation battle",
                body=f"{sanction_count} active governance sanctions and promotion rules are raising the pressure on federation members.",
                score=min(100.0, (sanction_count * 20.0) + (active_members * 4.0)),
                metadata_json={"sanction_count": sanction_count, "member_count": active_members},
            ),
            self._upsert_narrative(
                federation_id=federation.id,
                narrative_type="underdog_story",
                headline="Underdog story",
                body=f"With {active_members} clubs involved and {view_count} audience impressions, smaller clubs have real room to build momentum.",
                score=min(100.0, (active_members * 8.0) + (open_proposals * 3.0) + (view_count / 500.0)),
                metadata_json={"audience_size": view_count, "open_proposals": open_proposals},
            ),
        ]
        self.session.flush()
        return narratives

    def refresh_rankings(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        federations = list(self.session.scalars(select(Federation)).all())
        for federation in federations:
            active_member_count = len(self._active_member_club_ids(federation.id))
            league_ids, competition_ids = self._federation_competition_context(federation.id)
            proposal_count = int(
                self.session.scalar(select(func.count(FederationProposal.id)).where(FederationProposal.federation_id == federation.id))
                or 0
            )
            vote_count = int(
                self.session.scalar(select(func.count(FederationVote.id)).where(FederationVote.federation_id == federation.id))
                or 0
            )
            sanction_count = int(
                self.session.scalar(select(func.count(FederationSanction.id)).where(FederationSanction.federation_id == federation.id))
                or 0
            )
            narrative_count = int(
                self.session.scalar(
                    select(func.count(FederationNarrativeSnapshot.id)).where(FederationNarrativeSnapshot.federation_id == federation.id)
                )
                or 0
            )
            audience_size = self._federation_audience(competition_ids)
            competitiveness_score = min(
                100.0,
                (self._competition_match_count(competition_ids) * 1.5)
                + (len(league_ids) * 10.0)
                + (active_member_count * 4.0),
            )
            activity_score = min(
                100.0,
                (proposal_count * 4.0)
                + (vote_count * 1.5)
                + (sanction_count * 2.0)
                + (narrative_count * 3.0),
            )
            ranking_score = round(
                activity_score
                + competitiveness_score
                + min(audience_size / 1000.0, 50.0)
                + (float(federation.reputation_score or 0.0) * 0.20),
                2,
            )
            federation.audience_size = audience_size
            federation.ranking_score = ranking_score
            items.append(
                {
                    "federation_id": federation.id,
                    "name": federation.name,
                    "ranking_score": federation.ranking_score,
                    "reputation_score": federation.reputation_score,
                    "audience_size": federation.audience_size,
                    "activity_score": round(activity_score, 2),
                    "competitiveness_score": round(competitiveness_score, 2),
                }
            )
        self.session.flush()
        items.sort(key=lambda item: (-item["ranking_score"], item["name"]))
        return items

    def run_background_jobs_once(self) -> dict[str, int]:
        closed_proposals = self.tally_due_proposals()
        audits_run = self.run_rule_enforcement_checks()
        broadcast_distributions = self.sync_broadcast_revenue()
        narratives_refreshed = 0
        for federation in self.session.scalars(select(Federation)).all():
            narratives_refreshed += len(self.generate_narratives(federation.id))
        rankings = self.refresh_rankings()
        return {
            "closed_proposals": closed_proposals,
            "audits_run": audits_run,
            "broadcast_distributions": broadcast_distributions,
            "narratives_refreshed": narratives_refreshed,
            "rankings_refreshed": len(rankings),
        }

    def tally_due_proposals(self) -> int:
        now = datetime.now(UTC)
        proposals = list(
            self.session.scalars(
                select(FederationProposal).where(
                    FederationProposal.status == FederationProposalStatus.OPEN.value,
                    FederationProposal.voting_ends_at.is_not(None),
                    FederationProposal.voting_ends_at <= now,
                )
            ).all()
        )
        closed = 0
        for proposal in proposals:
            self._recompute_vote_totals(proposal)
            federation = self.get_federation(proposal.federation_id)
            quorum_votes = self._nested_int(federation.rules_json, "governance", "quorum_votes", default=1)
            yes_votes = int(proposal.yes_votes or 0)
            no_votes = int(proposal.no_votes or 0)
            total_counted = yes_votes + no_votes + int(proposal.abstain_votes or 0)
            proposal.status = (
                FederationProposalStatus.ACCEPTED.value
                if yes_votes > no_votes and total_counted >= quorum_votes
                else FederationProposalStatus.REJECTED.value
            )
            proposal.result_summary = (
                f"Voting closed with yes={proposal.yes_votes}, no={proposal.no_votes}, abstain={proposal.abstain_votes}, quorum={quorum_votes}."
            )
            if proposal.status == FederationProposalStatus.ACCEPTED.value:
                self._apply_proposal_outcome(proposal)
            closed += 1
        return closed

    def run_rule_enforcement_checks(self) -> int:
        audits_run = 0
        active_federations = list(self.session.scalars(select(Federation)).all())
        for federation in active_federations:
            club_ids = self._active_member_club_ids(federation.id)
            if not club_ids:
                continue
            listings = list(
                self.session.scalars(
                    select(TransferListing).where(
                        TransferListing.selling_club_id.in_(club_ids),
                        TransferListing.status == "open",
                    )
                ).all()
            )
            for listing in listings:
                self.validate_action(
                    federation_id=federation.id,
                    league_id=None,
                    action_type="transfer_listing",
                    club_id=listing.selling_club_id,
                    player_id=listing.player_id,
                    proposed_fee=Decimal(listing.base_price or 0),
                    proposed_wage=None,
                    source_reference=listing.id,
                    metadata_json={},
                )
                audits_run += 1

            recent_transfers = list(
                self.session.scalars(
                    select(ClubSaleTransfer).where(
                        ClubSaleTransfer.club_id.in_(club_ids),
                        ClubSaleTransfer.created_at >= datetime.now(UTC) - timedelta(days=1),
                    )
                ).all()
            )
            for transfer in recent_transfers:
                self.validate_action(
                    federation_id=federation.id,
                    league_id=None,
                    action_type="ownership_change",
                    club_id=transfer.club_id,
                    player_id=None,
                    proposed_fee=Decimal(transfer.executed_sale_price or 0),
                    proposed_wage=None,
                    source_reference=transfer.transfer_id,
                    metadata_json=dict(transfer.metadata_json or {}),
                )
                audits_run += 1
        return audits_run

    def sync_broadcast_revenue(self) -> int:
        created = 0
        for federation in self.session.scalars(select(Federation)).all():
            _, competition_ids = self._federation_competition_context(federation.id)
            for competition_id in competition_ids:
                amount = self._derive_broadcast_amount(federation.id, competition_id)
                if amount <= Decimal("0.0000"):
                    continue
                existing = self.session.scalar(
                    select(FederationTreasuryEntry).where(
                        FederationTreasuryEntry.federation_id == federation.id,
                        FederationTreasuryEntry.source_type == "broadcast_rights",
                        FederationTreasuryEntry.source_reference == competition_id,
                    )
                )
                if existing is not None:
                    continue
                self.distribute_revenue(
                    federation_id=federation.id,
                    source_type="broadcast_rights",
                    source_reference=competition_id,
                    gross_amount=amount,
                    federation_share_bps=None,
                    metadata_json={"source": "background_sync"},
                )
                created += 1
        return created

    def _require_club(self, club_id: str) -> ClubProfile:
        club = self.session.get(ClubProfile, club_id)
        if club is None:
            raise FederationValidationError("Club was not found.")
        return club

    def _require_league(self, league_id: str, federation_id: str) -> FederationLeague:
        league = self.session.get(FederationLeague, league_id)
        if league is None or league.federation_id != federation_id:
            raise FederationValidationError("Federation league was not found.")
        return league

    def _require_owner_or_admin(self, *, federation: Federation, actor: User) -> None:
        if actor.id == federation.owner_user_id:
            return
        if actor.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            return
        raise FederationValidationError("Only federation owners or platform admins can perform this action.")

    def _require_governance_participant(self, *, federation: Federation, actor: User) -> None:
        if actor.id == federation.owner_user_id or actor.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            return
        membership = self.session.scalar(
            select(FederationMembership).where(
                FederationMembership.federation_id == federation.id,
                FederationMembership.status == FederationMembershipStatus.ACTIVE.value,
                FederationMembership.user_id == actor.id,
            )
        )
        if membership is not None:
            return
        owned_active_membership = self.session.scalar(
            select(FederationMembership)
            .join(ClubProfile, ClubProfile.id == FederationMembership.club_id)
            .where(
                FederationMembership.federation_id == federation.id,
                FederationMembership.status == FederationMembershipStatus.ACTIVE.value,
                ClubProfile.owner_user_id == actor.id,
            )
        )
        if owned_active_membership is not None:
            return
        raise FederationValidationError("You are not eligible to participate in this federation's governance.")

    def _evaluate_entry_requirements(
        self,
        *,
        federation: Federation,
        club: ClubProfile,
        requested_requirements: dict[str, Any],
    ) -> list[dict[str, Any]]:
        requirements = self._deep_merge(
            dict((federation.rules_json or {}).get("entry_control") or {}),
            dict(requested_requirements or {}),
        )
        violations: list[dict[str, Any]] = []
        allowed_country_codes = {
            item.strip().upper()
            for item in requirements.get("country_codes", [])
            if isinstance(item, str) and item.strip()
        }
        if allowed_country_codes and (club.country_code or "").upper() not in allowed_country_codes:
            violations.append(
                {
                    "code": "country_code_blocked",
                    "message": f"Club country {club.country_code or 'unknown'} is outside the federation entry policy.",
                }
            )
        if bool(requirements.get("require_public_visibility")) and club.visibility != "public":
            violations.append(
                {
                    "code": "visibility_blocked",
                    "message": "Club must be publicly visible before joining the federation.",
                }
            )
        min_founding_year = requirements.get("min_founding_year")
        if isinstance(min_founding_year, int):
            founded_year = club.founded_at.year if club.founded_at is not None else None
            if founded_year is None or founded_year > min_founding_year:
                violations.append(
                    {
                        "code": "founding_year_blocked",
                        "message": f"Club must be founded on or before {min_founding_year} to qualify.",
                    }
                )
        return violations

    def _sync_snapshot_fields(self, federation: Federation) -> None:
        leagues = self.list_leagues(federation.id)
        memberships = self.list_memberships(federation.id)
        club_map = {
            club.id: club
            for club in self.session.scalars(
                select(ClubProfile).where(ClubProfile.id.in_([item.club_id for item in memberships]))
            ).all()
        } if memberships else {}
        federation.competitions_json = [
            {
                "league_id": league.id,
                "name": league.name,
                "competition_type": league.competition_type,
                "format": league.format,
                "linked_competition_id": league.linked_competition_id,
                "status": league.status,
            }
            for league in leagues
        ]
        federation.members_json = [
            {
                "club_id": membership.club_id,
                "club_name": club_map.get(membership.club_id).club_name if membership.club_id in club_map else None,
                "user_id": membership.user_id,
                "role": membership.role,
                "status": membership.status,
            }
            for membership in memberships
        ] + [
            {
                "user_id": federation.owner_user_id,
                "role": "owner_admin",
                "status": "active",
            }
        ]
        self.session.flush()

    def _vote_weight(self, *, federation: Federation, actor: User) -> int:
        if actor.id == federation.owner_user_id:
            return 2
        membership = self.session.scalar(
            select(FederationMembership).where(
                FederationMembership.federation_id == federation.id,
                FederationMembership.user_id == actor.id,
            )
        )
        if membership is not None and membership.role in {"admin", "commissioner"}:
            return 2
        return 1

    def _recompute_vote_totals(self, proposal: FederationProposal) -> None:
        votes = list(
            self.session.scalars(
                select(FederationVote).where(FederationVote.proposal_id == proposal.id)
            ).all()
        )
        proposal.yes_votes = sum(vote.weight for vote in votes if vote.vote_type == FederationVoteType.YES.value)
        proposal.no_votes = sum(vote.weight for vote in votes if vote.vote_type == FederationVoteType.NO.value)
        proposal.abstain_votes = sum(vote.weight for vote in votes if vote.vote_type == FederationVoteType.ABSTAIN.value)
        self.session.flush()

    def _apply_proposal_outcome(self, proposal: FederationProposal) -> None:
        federation = self.get_federation(proposal.federation_id)
        rules_patch = proposal.payload_json.get("rules_patch")
        if isinstance(rules_patch, dict):
            federation.rules_json = self._deep_merge(dict(federation.rules_json or {}), rules_patch)
        if proposal.league_id:
            league = self._require_league(proposal.league_id, federation.id)
            league_patch = proposal.payload_json.get("league_rules_patch")
            if isinstance(league_patch, dict):
                league.governance_rules_override_json = self._deep_merge(
                    dict(league.governance_rules_override_json or {}),
                    league_patch,
                )
        self._sync_snapshot_fields(federation)

    def _merged_rules(self, *, federation: Federation, league: FederationLeague | None) -> dict[str, Any]:
        base_rules = dict(federation.rules_json or {})
        if league is None:
            return base_rules
        return self._deep_merge(base_rules, dict(league.governance_rules_override_json or {}))

    def _active_member_club_ids(self, federation_id: str) -> list[str]:
        return list(
            self.session.scalars(
                select(FederationMembership.club_id).where(
                    FederationMembership.federation_id == federation_id,
                    FederationMembership.status == FederationMembershipStatus.ACTIVE.value,
                )
            ).all()
        )

    def _notification_target_user_ids(self, federation_id: str) -> set[str]:
        federation = self.get_federation(federation_id)
        user_ids = {federation.owner_user_id}
        active_memberships = self.list_memberships(federation_id)
        for membership in active_memberships:
            if membership.status != FederationMembershipStatus.ACTIVE.value:
                continue
            if membership.user_id:
                user_ids.add(membership.user_id)
            club = self.session.get(ClubProfile, membership.club_id)
            if club is not None:
                user_ids.add(club.owner_user_id)
        return user_ids

    def _sanction_targets(self, *, club_id: str | None) -> set[str]:
        if club_id is None:
            return set()
        club = self.session.get(ClubProfile, club_id)
        return {club.owner_user_id} if club is not None else set()

    def _publish_notification(
        self,
        *,
        user_ids: set[str],
        template_key: str,
        message: str,
        resource_type: str,
        resource_id: str,
        metadata_json: dict[str, Any],
    ) -> None:
        if not user_ids:
            self.session.add(
                NotificationRecord(
                    user_id=None,
                    topic="federation",
                    template_key=template_key,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    message=message[:255],
                    metadata_json=dict(metadata_json or {}),
                )
            )
            return
        for user_id in user_ids:
            self.session.add(
                NotificationRecord(
                    user_id=user_id,
                    topic="federation",
                    template_key=template_key,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    message=message[:255],
                    metadata_json=dict(metadata_json or {}),
                )
            )

    def _competition_shell_format(self, league: FederationLeague) -> str:
        if league.competition_type in {FederationCompetitionType.CUP.value, FederationCompetitionType.TOURNAMENT.value}:
            return "cup"
        if "knockout" in league.format.casefold():
            return "cup"
        return "league"

    @staticmethod
    def _normalize_datetime(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def _projected_foreign_player_count(
        self,
        *,
        club_id: str,
        incoming_player: Player,
        home_country_codes: set[str],
    ) -> int:
        player_ids = list(
            self.session.scalars(
                select(PlayerContract.player_id).where(
                    PlayerContract.club_id == club_id,
                    PlayerContract.status == "active",
                )
            ).all()
        )
        if incoming_player.id not in player_ids:
            player_ids.append(incoming_player.id)
        foreign_count = 0
        for player_id in player_ids:
            player = self.session.get(Player, player_id)
            if player is None:
                continue
            country_code = self._country_code_for_player(player)
            if country_code not in home_country_codes:
                foreign_count += 1
        return foreign_count

    def _country_code_for_player(self, player: Player) -> str | None:
        if player.country_id is None:
            return None
        country = self.session.get(Country, player.country_id)
        if country is None:
            return None
        return (country.alpha2_code or country.alpha3_code or country.fifa_code or "").upper() or None

    def _active_contract_count(self, club_id: str) -> int:
        return int(
            self.session.scalar(
                select(func.count(PlayerContract.id)).where(
                    PlayerContract.club_id == club_id,
                    PlayerContract.status == "active",
                )
            )
            or 0
        )

    def _active_wage_total(self, club_id: str) -> Decimal:
        total = self.session.scalar(
            select(func.coalesce(func.sum(PlayerContract.wage_amount), 0)).where(
                PlayerContract.club_id == club_id,
                PlayerContract.status == "active",
            )
        )
        return self._normalize_amount(total or Decimal("0"))

    def _default_revenue_reference(self, federation_id: str, source_type: str) -> str:
        league_ids, competition_ids = self._federation_competition_context(federation_id)
        if source_type == "broadcast_rights" and competition_ids:
            return competition_ids[0]
        if source_type == "entry_fees" and competition_ids:
            return competition_ids[0]
        if source_type == "sponsorships" and league_ids:
            return league_ids[0]
        raise FederationValidationError("A revenue source_reference is required for this federation revenue action.")

    def _derive_revenue_amount(self, *, federation_id: str, source_type: str, source_reference: str) -> Decimal:
        if source_type == "broadcast_rights":
            return self._derive_broadcast_amount(federation_id, source_reference)
        if source_type == "entry_fees":
            return self._derive_entry_fee_amount(source_reference)
        if source_type == "sponsorships":
            return self._derive_sponsorship_amount(federation_id, source_reference)
        raise FederationValidationError("Unsupported federation revenue source.")

    def _derive_broadcast_amount(self, federation_id: str, source_reference: str) -> Decimal:
        _league_ids, competition_ids = self._federation_competition_context(federation_id)
        reference = source_reference
        league = self.session.get(FederationLeague, source_reference)
        if league is not None and league.federation_id == federation_id and league.linked_competition_id:
            reference = league.linked_competition_id
        if reference not in competition_ids:
            raise FederationValidationError("Broadcast revenue reference is not attached to this federation.")
        amount = self.session.scalar(
            select(func.coalesce(func.sum(MatchRevenueSnapshot.total_revenue_coin), 0)).where(
                MatchRevenueSnapshot.competition_key == reference
            )
        )
        return self._normalize_amount(amount or Decimal("0"))

    def _derive_entry_fee_amount(self, competition_id: str) -> Decimal:
        competition = self.session.get(UserCompetition, competition_id)
        if competition is None:
            raise FederationValidationError("Competition shell for entry-fee revenue was not found.")
        return self._normalize_amount(Decimal(int(competition.gross_pool_minor or 0)) / Decimal("100"))

    def _derive_sponsorship_amount(self, federation_id: str, source_reference: str) -> Decimal:
        club_ids = self._active_member_club_ids(federation_id)
        if source_reference in club_ids:
            club_ids = [source_reference]
        stmt = (
            select(func.coalesce(func.sum(ClubSponsorshipPayout.amount_minor), 0))
            .select_from(ClubSponsorshipPayout)
            .join(ClubSponsorshipContract, ClubSponsorshipContract.id == ClubSponsorshipPayout.contract_id)
            .where(
                ClubSponsorshipContract.club_id.in_(club_ids),
                ClubSponsorshipPayout.status == "settled",
            )
        )
        total_minor = int(self.session.scalar(stmt) or 0)
        return self._normalize_amount(Decimal(total_minor) / Decimal("100"))

    def _federation_competition_context(self, federation_id: str) -> tuple[list[str], list[str]]:
        leagues = self.list_leagues(federation_id)
        league_ids = [league.id for league in leagues]
        competition_ids = [league.linked_competition_id for league in leagues if league.linked_competition_id]
        return league_ids, competition_ids

    def _competition_match_count(self, competition_ids: list[str]) -> int:
        if not competition_ids:
            return 0
        return int(
            self.session.scalar(
                select(func.count(CompetitionMatch.id)).where(CompetitionMatch.competition_id.in_(competition_ids))
            )
            or 0
        )

    def _federation_audience(self, competition_ids: list[str]) -> int:
        if not competition_ids:
            return 0
        return int(
            self.session.scalar(
                select(func.coalesce(func.sum(MatchRevenueSnapshot.total_views), 0)).where(
                    MatchRevenueSnapshot.competition_key.in_(competition_ids)
                )
            )
            or 0
        )

    def _upsert_narrative(
        self,
        *,
        federation_id: str,
        narrative_type: str,
        headline: str,
        body: str,
        score: float,
        metadata_json: dict[str, Any],
    ) -> FederationNarrativeSnapshot:
        item = self.session.scalar(
            select(FederationNarrativeSnapshot).where(
                FederationNarrativeSnapshot.federation_id == federation_id,
                FederationNarrativeSnapshot.narrative_type == narrative_type,
            )
        )
        if item is None:
            item = FederationNarrativeSnapshot(
                federation_id=federation_id,
                narrative_type=narrative_type,
            )
            self.session.add(item)
        item.headline = headline
        item.body = body
        item.score = round(score, 2)
        item.metadata_json = dict(metadata_json or {})
        return item

    def _with_defaults(self, rules_json: dict[str, Any], *, default_reality_mode: RealityMode) -> dict[str, Any]:
        default_rules = {
            "competition_player_mode": default_reality_mode.value,
            "entry_control": {
                "approval_required": True,
            },
            "economy": {
                "federation_share_bps": 1500,
            },
            "broadcast_rights": {
                "min_federation_share_bps": 1000,
            },
            "ownership": {
                "require_governance_vote_for_sale": True,
            },
        }
        return self._deep_merge(default_rules, rules_json)

    @staticmethod
    def _normalize_amount(value: Decimal | float | int | str | None) -> Decimal:
        return Decimal(str(value or 0)).quantize(AMOUNT_QUANTUM, rounding=ROUND_HALF_UP)

    @classmethod
    def _deep_merge(cls, base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
        merged = dict(base)
        for key, value in overlay.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = cls._deep_merge(dict(merged[key]), value)
            else:
                merged[key] = value
        return merged

    @staticmethod
    def _nested_value(payload: dict[str, Any], *keys: str) -> Any:
        current: Any = payload
        for key in keys:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
        return current

    @classmethod
    def _nested_int(cls, payload: dict[str, Any], *keys: str, default: int | None = None) -> int | None:
        value = cls._nested_value(payload, *keys)
        if value is None:
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @classmethod
    def _nested_decimal(cls, payload: dict[str, Any], *keys: str) -> Decimal | None:
        value = cls._nested_value(payload, *keys)
        if value is None:
            return None
        try:
            return cls._normalize_amount(value)
        except Exception:
            return None

    @classmethod
    def _nested_list(cls, payload: dict[str, Any], *keys: str) -> list[Any]:
        value = cls._nested_value(payload, *keys)
        return list(value) if isinstance(value, list) else []


__all__ = [
    "FederationError",
    "FederationNotFoundError",
    "FederationService",
    "FederationValidationError",
]
