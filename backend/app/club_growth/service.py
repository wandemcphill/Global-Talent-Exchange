from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from hashlib import sha256
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session

from app.ingestion.models import ImageModerationStatus, Player, PlayerImageMetadata
from app.models.base import utcnow
from app.models.club_growth import (
    AcademyGenerationRun,
    AcademyProfile,
    AcademyPromotionHistory,
    AcademyProspect,
    AcademyRegenContractOffer,
    ClubGrowthAuditEvent,
    ClubStaffAssignment,
    ClubStaffContract,
    ClubStaffProfile,
)
from app.models.club_profile import ClubProfile
from app.models.user import User
from app.notifications.service import NotificationEventMatrixService
from app.services.regen_portrait_service import (
    FACE_RECIPE_VERSION,
    NEWGEN_FACE_BANK_COLLECTION,
    NEWGEN_FACE_BANK_PROVIDER,
    RegenPortraitService,
)
from app.sponsorship_engine.service import SponsorshipEngineService

from .schemas import (
    AcademyContractOfferRequest,
    AcademyContractOfferView,
    AcademyContractResponseRequest,
    AcademyGenerateProspectsRequest,
    AcademyGenerationRunView,
    AcademyProfileView,
    AcademyProspectView,
    ClubGrowthDashboardView,
    SponsorshipClubSummaryView,
    StaffContractView,
    StaffOfferRequest,
    StaffProfileView,
)


class ClubGrowthError(ValueError):
    pass


DEFAULT_STAFF_MARKET: tuple[dict[str, object], ...] = (
    {
        "market_key": "launch-agent-negotiator",
        "display_name": "Launch Negotiation Agent",
        "staff_type": "agent",
        "rarity": "standard",
        "skills_json": ["negotiation", "contract_handling", "market_insight"],
        "salary_minor": 24000,
        "commission_bps": 350,
        "rating": 62,
    },
    {
        "market_key": "academy-scout-regional",
        "display_name": "Regional Academy Scout",
        "staff_type": "scout",
        "rarity": "standard",
        "skills_json": ["scouting", "academy_growth", "regen_development"],
        "salary_minor": 18000,
        "commission_bps": 100,
        "rating": 58,
    },
    {
        "market_key": "youth-coach-foundation",
        "display_name": "Foundation Youth Coach",
        "staff_type": "coach",
        "rarity": "standard",
        "skills_json": ["regen_development", "fitness", "morale"],
        "salary_minor": 20000,
        "commission_bps": 0,
        "rating": 60,
    },
    {
        "market_key": "manager-match-prep",
        "display_name": "Match Prep Manager",
        "staff_type": "manager",
        "rarity": "pro",
        "skills_json": ["tactics", "morale", "market_insight"],
        "salary_minor": 36000,
        "commission_bps": 200,
        "rating": 70,
        "metadata_json": {"source": "club_growth_bridge", "manager_market_compatible": True},
    },
)

POSITIONS = ("GK", "RB", "CB", "LB", "DM", "CM", "AM", "RW", "LW", "ST")
PERSONALITIES = (
    {"temperament": "focused", "training_style": "methodical", "risk": "low"},
    {"temperament": "ambitious", "training_style": "explosive", "risk": "medium"},
    {"temperament": "creative", "training_style": "improviser", "risk": "medium"},
    {"temperament": "resilient", "training_style": "physical", "risk": "low"},
)


def _staff_profile_id(market_key: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"gtex:club-growth-staff:{market_key}"))


@dataclass(slots=True)
class ClubGrowthService:
    session: Session

    def get_dashboard(self, *, club_id: str) -> ClubGrowthDashboardView:
        self._ensure_club(club_id)
        self.seed_staff_defaults()
        academy = self.ensure_academy_profile(club_id=club_id)
        staff_market = self.list_staff_market()
        contracts = self.list_staff_contracts(club_id=club_id)
        prospects = self.list_academy_prospects(club_id=club_id)
        runs = self.list_generation_runs(club_id=club_id)
        sponsorship = self._sponsorship_summary(club_id=club_id)
        return ClubGrowthDashboardView(
            club_id=club_id,
            staff_market=[self._staff_profile_view(item) for item in staff_market],
            staff_contracts=[self._staff_contract_view(item) for item in contracts],
            staff_effects=self._staff_effects(contracts),
            academy_profile=self._academy_profile_view(academy),
            academy_prospects=[self._academy_prospect_view(item) for item in prospects],
            academy_runs=[self._academy_generation_run_view(item) for item in runs],
            sponsorship=sponsorship,
            updated_at=utcnow(),
        )

    def seed_staff_defaults(self) -> None:
        existing = {
            item[0]
            for item in self.session.execute(select(ClubStaffProfile.market_key)).all()
        }
        for payload in DEFAULT_STAFF_MARKET:
            market_key = str(payload["market_key"])
            if market_key in existing:
                continue
            self.session.add(
                ClubStaffProfile(
                    id=_staff_profile_id(market_key),
                    market_key=market_key,
                    display_name=str(payload["display_name"]),
                    staff_type=str(payload["staff_type"]),
                    rarity=str(payload.get("rarity", "standard")),
                    skills_json=list(payload.get("skills_json", [])),
                    salary_minor=int(payload.get("salary_minor", 0)),
                    commission_bps=int(payload.get("commission_bps", 0)),
                    rating=int(payload.get("rating", 50)),
                    metadata_json=dict(payload.get("metadata_json", {})),
                )
            )
        self.session.flush()

    def list_staff_market(self) -> list[ClubStaffProfile]:
        self.seed_staff_defaults()
        statement = (
            select(ClubStaffProfile)
            .where(ClubStaffProfile.active.is_(True))
            .order_by(ClubStaffProfile.rating.desc(), ClubStaffProfile.display_name.asc())
        )
        return list(self.session.scalars(statement).all())

    def list_staff_contracts(self, *, club_id: str) -> list[ClubStaffContract]:
        statement = (
            select(ClubStaffContract)
            .where(ClubStaffContract.club_id == club_id)
            .order_by(ClubStaffContract.updated_at.desc())
        )
        return list(self.session.scalars(statement).all())

    def offer_staff_contract(
        self,
        *,
        actor: User,
        club_id: str,
        staff_id: str,
        payload: StaffOfferRequest,
    ) -> StaffContractView:
        staff = self.session.get(ClubStaffProfile, staff_id)
        if staff is None:
            self.seed_staff_defaults()
            staff = self.session.get(ClubStaffProfile, staff_id)
        if staff is None or not staff.active:
            raise ClubGrowthError("staff_profile_not_found")
        if payload.exclusive:
            active_exclusive = self.session.scalar(
                select(ClubStaffContract).where(
                    ClubStaffContract.staff_profile_id == staff_id,
                    ClubStaffContract.status == "active",
                    ClubStaffContract.exclusive.is_(True),
                )
            )
            if active_exclusive is not None:
                raise ClubGrowthError("staff_already_exclusive")
        contract = ClubStaffContract(
            club_id=club_id,
            staff_profile_id=staff_id,
            status="offered",
            salary_minor=payload.salary_minor if payload.salary_minor is not None else staff.salary_minor,
            commission_bps=payload.commission_bps if payload.commission_bps is not None else staff.commission_bps,
            duration_days=payload.duration_days,
            role_scope=payload.role_scope,
            exclusive=payload.exclusive,
            metadata_json={"source": "club_growth_batch_25"},
        )
        self.session.add(contract)
        self._audit(
            actor=actor,
            club_id=club_id,
            action="staff_contract_offered",
            next_json={"staff_profile_id": staff_id, "role_scope": payload.role_scope},
        )
        self.session.flush()
        return self._staff_contract_view(contract)

    def accept_staff_contract(self, *, actor: User, club_id: str, contract_id: str) -> StaffContractView:
        contract = self._get_contract(club_id=club_id, contract_id=contract_id)
        if contract.status != "offered":
            raise ClubGrowthError("staff_contract_not_offered")
        now = utcnow()
        previous = self._staff_contract_snapshot(contract)
        contract.status = "active"
        contract.started_at = now
        contract.accepted_at = now
        contract.ends_at = now + timedelta(days=contract.duration_days)
        self._assign_staff_role(club_id=club_id, contract=contract)
        self._audit(
            actor=actor,
            club_id=club_id,
            action="staff_contract_accepted",
            previous_json=previous,
            next_json={"contract_id": contract.id, "staff_profile_id": contract.staff_profile_id},
        )
        self.session.flush()
        if contract.ends_at is not None and contract.ends_at <= now + timedelta(days=7):
            club = self._ensure_club(club_id)
            self._publish_matrix_notification(
                event_key="staff_contract_expiring",
                target_user_ids=[club.owner_user_id],
                resource_id=contract.id,
                message="A staff contract is approaching expiry.",
                metadata={
                    "club_id": club_id,
                    "contract_id": contract.id,
                    "staff_profile_id": contract.staff_profile_id,
                    "ends_at": contract.ends_at.isoformat(),
                    "route": "/app/club",
                },
            )
        return self._staff_contract_view(contract)

    def terminate_staff_contract(self, *, actor: User, club_id: str, contract_id: str) -> StaffContractView:
        contract = self._get_contract(club_id=club_id, contract_id=contract_id)
        if contract.status not in {"active", "offered"}:
            raise ClubGrowthError("staff_contract_not_terminable")
        previous = self._staff_contract_snapshot(contract)
        contract.status = "terminated"
        contract.terminated_at = utcnow()
        for assignment in self.session.scalars(
            select(ClubStaffAssignment).where(ClubStaffAssignment.staff_contract_id == contract.id)
        ):
            assignment.active = False
        self._audit(
            actor=actor,
            club_id=club_id,
            action="staff_contract_terminated",
            previous_json=previous,
            next_json={"contract_id": contract.id},
        )
        self.session.flush()
        return self._staff_contract_view(contract)

    def ensure_academy_profile(self, *, club_id: str) -> AcademyProfile:
        profile = self.session.scalar(select(AcademyProfile).where(AcademyProfile.club_id == club_id))
        if profile is not None:
            return profile
        self._ensure_club(club_id)
        profile = AcademyProfile(
            club_id=club_id,
            level=1,
            investment_minor=0,
            metadata_json={"created_by": "club_growth_batch_26"},
        )
        self.session.add(profile)
        self.session.flush()
        return profile

    def upgrade_academy(self, *, actor: User, club_id: str) -> AcademyProfileView:
        profile = self.ensure_academy_profile(club_id=club_id)
        previous = {"level": profile.level, "investment_minor": profile.investment_minor}
        profile.level += 1
        profile.investment_minor += profile.level * 50000
        self._audit(
            actor=actor,
            club_id=club_id,
            action="academy_upgraded",
            previous_json=previous,
            next_json={"level": profile.level, "investment_minor": profile.investment_minor},
        )
        self.session.flush()
        return self._academy_profile_view(profile)

    def list_academy_prospects(self, *, club_id: str) -> list[AcademyProspect]:
        statement = (
            select(AcademyProspect)
            .where(AcademyProspect.club_id == club_id)
            .order_by(AcademyProspect.updated_at.desc(), AcademyProspect.display_name.asc())
        )
        return list(self.session.scalars(statement).all())

    def list_generation_runs(self, *, club_id: str) -> list[AcademyGenerationRun]:
        statement = (
            select(AcademyGenerationRun)
            .where(AcademyGenerationRun.club_id == club_id)
            .order_by(AcademyGenerationRun.created_at.desc())
            .limit(5)
        )
        return list(self.session.scalars(statement).all())

    def generate_prospects(
        self,
        *,
        actor: User,
        club_id: str,
        payload: AcademyGenerateProspectsRequest,
    ) -> list[AcademyProspectView]:
        club = self._ensure_club(club_id)
        academy = self.ensure_academy_profile(club_id=club_id)
        existing_count = int(
            self.session.scalar(select(func.count(AcademyProspect.id)).where(AcademyProspect.club_id == club_id))
            or 0
        )
        seed = payload.seed or f"{club_id}:{academy.level}:{existing_count}:{payload.count}"
        generated: list[AcademyProspect] = []
        for index in range(payload.count):
            digest = sha256(f"{seed}:{index}".encode("utf-8")).hexdigest()
            position = POSITIONS[int(digest[0:2], 16) % len(POSITIONS)]
            personality = PERSONALITIES[int(digest[2:4], 16) % len(PERSONALITIES)]
            ability = 32 + (int(digest[4:6], 16) % 20) + academy.level
            potential = min(99, ability + 18 + (int(digest[6:8], 16) % 24))
            portrait_asset_ref = self._select_academy_portrait_asset_ref(
                seed=f"{seed}:{index}",
                nationality=club.country_code,
            )
            prospect = AcademyProspect(
                club_id=club_id,
                academy_profile_id=academy.id,
                display_name=f"Academy Regen {existing_count + index + 1:03d}",
                nationality=club.country_code,
                position=position,
                age=15 + (int(digest[8:10], 16) % 4),
                personality_json=dict(personality),
                current_ability=ability,
                potential=potential,
                portrait_asset_ref=portrait_asset_ref,
                status="discovered",
                metadata_json={
                    "generation_seed": seed,
                    "portrait_policy": "newgen_bank_only",
                    "portrait_source_provider": NEWGEN_FACE_BANK_PROVIDER,
                    "portrait_source_collection": NEWGEN_FACE_BANK_COLLECTION,
                    "source": "academy_to_regen_batch_26",
                },
            )
            self.session.add(prospect)
            generated.append(prospect)
        run = AcademyGenerationRun(
            club_id=club_id,
            run_seed=seed,
            prospects_created=payload.count,
            status="completed",
            metadata_json={"academy_level": academy.level},
        )
        self.session.add(run)
        self._audit(
            actor=actor,
            club_id=club_id,
            action="academy_prospects_generated",
            next_json={"run_seed": seed, "prospects_created": payload.count},
        )
        self.session.flush()
        self._publish_matrix_notification(
            event_key="academy_regen_generated",
            target_user_ids=[club.owner_user_id],
            resource_id=run.id,
            message=f"{payload.count} academy prospect(s) are ready for review.",
            metadata={
                "club_id": club_id,
                "run_id": run.id,
                "prospect_ids": [item.id for item in generated],
                "route": "/app/club",
            },
        )
        return [self._academy_prospect_view(item) for item in generated]

    def offer_prospect_contract(
        self,
        *,
        actor: User,
        club_id: str,
        prospect_id: str,
        payload: AcademyContractOfferRequest,
    ) -> AcademyContractOfferView:
        prospect = self._get_prospect(club_id=club_id, prospect_id=prospect_id)
        if prospect.status not in {"discovered", "trial", "academy", "contract_rejected"}:
            raise ClubGrowthError("prospect_not_contract_eligible")
        offer = AcademyRegenContractOffer(
            club_id=club_id,
            prospect_id=prospect_id,
            status="offered",
            wage_minor=payload.wage_minor,
            duration_months=payload.duration_months,
            metadata_json={"source": "academy_to_regen_batch_26"},
        )
        previous = {"status": prospect.status}
        prospect.status = "contract_offered"
        self.session.add(offer)
        self._audit(
            actor=actor,
            club_id=club_id,
            action="academy_contract_offered",
            previous_json=previous,
            next_json={"prospect_id": prospect_id, "wage_minor": payload.wage_minor},
        )
        self.session.flush()
        return self._academy_contract_offer_view(offer)

    def respond_to_prospect_contract(
        self,
        *,
        actor: User,
        club_id: str,
        offer_id: str,
        payload: AcademyContractResponseRequest,
    ) -> AcademyContractOfferView:
        offer = self.session.get(AcademyRegenContractOffer, offer_id)
        if offer is None or offer.club_id != club_id:
            raise ClubGrowthError("academy_contract_offer_not_found")
        if offer.status != "offered":
            raise ClubGrowthError("academy_contract_offer_closed")
        prospect = self._get_prospect(club_id=club_id, prospect_id=offer.prospect_id)
        previous = {"offer_status": offer.status, "prospect_status": prospect.status}
        offer.status = "accepted" if payload.accepted else "rejected"
        offer.response_reason = payload.reason
        prospect.status = "youth_signed" if payload.accepted else "contract_rejected"
        self._audit(
            actor=actor,
            club_id=club_id,
            action="academy_contract_responded",
            previous_json=previous,
            next_json={"offer_id": offer.id, "accepted": payload.accepted},
        )
        self.session.flush()
        return self._academy_contract_offer_view(offer)

    def promote_prospect(self, *, actor: User, club_id: str, prospect_id: str) -> AcademyProspectView:
        prospect = self._get_prospect(club_id=club_id, prospect_id=prospect_id)
        existing_history = self._promotion_history(prospect_id=prospect.id)
        if prospect.status == "promoted_to_senior" and existing_history is not None and existing_history.senior_player_id:
            return self._academy_prospect_view(prospect)
        if prospect.status != "youth_signed":
            raise ClubGrowthError("prospect_not_promotable")
        if not prospect.portrait_asset_ref:
            prospect.portrait_asset_ref = self._select_academy_portrait_asset_ref(
                seed=prospect.id,
                nationality=prospect.nationality,
            )
        senior_player = self._ensure_senior_player_for_prospect(club_id=club_id, prospect=prospect)
        previous = {"status": prospect.status}
        prospect.status = "promoted_to_senior"
        history = existing_history
        if history is None:
            history = AcademyPromotionHistory(
                club_id=club_id,
                prospect_id=prospect.id,
                senior_player_id=senior_player.id,
                metadata_json={
                    "promotion_policy": "canonical_senior_player_created",
                    "portrait_policy": "newgen_bank_only",
                    "portrait_asset_ref": prospect.portrait_asset_ref,
                },
            )
            self.session.add(history)
        else:
            history.senior_player_id = senior_player.id
            history.metadata_json = {
                **dict(history.metadata_json or {}),
                "promotion_policy": "canonical_senior_player_created",
                "portrait_asset_ref": prospect.portrait_asset_ref,
            }
        self._audit(
            actor=actor,
            club_id=club_id,
            action="academy_prospect_promoted",
            previous_json=previous,
            next_json={
                "prospect_id": prospect.id,
                "status": prospect.status,
                "senior_player_id": senior_player.id,
                "portrait_asset_ref": prospect.portrait_asset_ref,
            },
        )
        self.session.flush()
        return self._academy_prospect_view(prospect)

    def _select_academy_portrait_asset_ref(self, *, seed: str, nationality: str | None) -> str:
        service = RegenPortraitService(self.session)
        groups = RegenPortraitService._portrait_ethnicity_groups(nationality)
        recipe = {
            "portraitEthnicityGroups": list(groups),
            "portraitEthnicity": groups[0] if groups else "Mixed",
        }
        asset = service._select_regen_face_bank_asset(seed=seed, recipe=recipe)
        if asset is None:
            raise ClubGrowthError("academy_portrait_asset_missing")
        return str(asset["storage_key"])

    def _promotion_history(self, *, prospect_id: str) -> AcademyPromotionHistory | None:
        return self.session.scalar(
            select(AcademyPromotionHistory)
            .where(AcademyPromotionHistory.prospect_id == prospect_id)
            .order_by(AcademyPromotionHistory.created_at.desc())
        )

    def _ensure_senior_player_for_prospect(self, *, club_id: str, prospect: AcademyProspect) -> Player:
        provider_external_id = f"academy:{prospect.id}"
        existing = self.session.scalar(
            select(Player).where(
                Player.source_provider == "gtex_academy_regen",
                Player.provider_external_id == provider_external_id,
            )
        )
        if existing is not None:
            self._ensure_player_portrait_metadata(player=existing, prospect=prospect)
            return existing

        current_year = utcnow().year
        player = Player(
            source_provider="gtex_academy_regen",
            provider_external_id=provider_external_id,
            current_club_profile_id=club_id,
            full_name=prospect.display_name,
            first_name=prospect.display_name.split(" ", 1)[0],
            last_name=prospect.display_name.split(" ", 1)[1] if " " in prospect.display_name else None,
            short_name=prospect.display_name,
            position=prospect.position,
            normalized_position=prospect.position,
            date_of_birth=date(max(1970, current_year - prospect.age), 7, 1),
            is_tradable=False,
            is_real_player=False,
            canonical_display_name=prospect.display_name,
            identity_confidence_score=0.96,
            profile_completeness_score=0.82,
            current_market_reference_value=float(max(prospect.current_ability, prospect.potential) * 1000),
            market_reference_currency="GTEX",
            normalization_profile_version="academy_regen_v1",
            dna_profile={
                "generationSource": "academy",
                "academyProspectId": prospect.id,
                "academyClubId": club_id,
                "currentAbility": prospect.current_ability,
                "potential": prospect.potential,
                "personality": dict(prospect.personality_json or {}),
                "portraitStatus": "ready_newgen_face_bank",
                "portraitRecipeVersion": FACE_RECIPE_VERSION,
                "portraitSourceProvider": NEWGEN_FACE_BANK_PROVIDER,
                "portraitSourceCollection": NEWGEN_FACE_BANK_COLLECTION,
                "portraitStorageKey": prospect.portrait_asset_ref,
            },
            last_synced_at=utcnow(),
        )
        self.session.add(player)
        self.session.flush()
        self._ensure_player_portrait_metadata(player=player, prospect=prospect)
        return player

    def _ensure_player_portrait_metadata(self, *, player: Player, prospect: AcademyProspect) -> None:
        if not prospect.portrait_asset_ref:
            raise ClubGrowthError("academy_portrait_asset_missing")
        service = RegenPortraitService(self.session)
        asset = service._face_bank_asset_by_storage_key(prospect.portrait_asset_ref)
        if asset is None:
            raise ClubGrowthError("academy_portrait_asset_missing")
        image = self.session.scalar(
            select(PlayerImageMetadata).where(
                PlayerImageMetadata.player_id == player.id,
                PlayerImageMetadata.image_role == "portrait",
            )
        )
        if image is None:
            image = PlayerImageMetadata(
                source_provider=NEWGEN_FACE_BANK_PROVIDER,
                provider_external_id=f"{NEWGEN_FACE_BANK_PROVIDER}:{prospect.portrait_asset_ref}",
                player_id=player.id,
                image_role="portrait",
            )
            self.session.add(image)
        image.source_provider = NEWGEN_FACE_BANK_PROVIDER
        image.provider_external_id = f"{NEWGEN_FACE_BANK_PROVIDER}:{prospect.portrait_asset_ref}"
        image.source_url = service._generated_media_url(prospect.portrait_asset_ref)
        image.storage_key = prospect.portrait_asset_ref
        image.width = RegenPortraitService._optional_int(asset.get("width")) or 512
        image.height = RegenPortraitService._optional_int(asset.get("height")) or 512
        image.mime_type = service._mime_type_for_storage_key(prospect.portrait_asset_ref)
        image.file_size_bytes = RegenPortraitService._optional_int(asset.get("bytes"))
        image.checksum_sha256 = str(asset.get("sha256") or "") or None
        image.moderation_status = ImageModerationStatus.APPROVED.value
        image.rights_cleared = True
        image.is_primary = True
        image.last_processed_at = utcnow()
        player.dna_profile = {
            **dict(player.dna_profile or {}),
            "portraitStatus": "ready_newgen_face_bank",
            "portraitRecipeVersion": FACE_RECIPE_VERSION,
            "portraitSourceProvider": NEWGEN_FACE_BANK_PROVIDER,
            "portraitSourceCollection": NEWGEN_FACE_BANK_COLLECTION,
            "portraitStorageKey": prospect.portrait_asset_ref,
            "portraitUrl": image.source_url,
        }
        self.session.flush()

    def _ensure_club(self, club_id: str) -> ClubProfile:
        club = self.session.get(ClubProfile, club_id)
        if club is None:
            raise LookupError("club_not_found")
        return club

    def _get_contract(self, *, club_id: str, contract_id: str) -> ClubStaffContract:
        contract = self.session.get(ClubStaffContract, contract_id)
        if contract is None or contract.club_id != club_id:
            raise ClubGrowthError("staff_contract_not_found")
        return contract

    def _get_prospect(self, *, club_id: str, prospect_id: str) -> AcademyProspect:
        prospect = self.session.get(AcademyProspect, prospect_id)
        if prospect is None or prospect.club_id != club_id:
            raise ClubGrowthError("academy_prospect_not_found")
        return prospect

    def _assign_staff_role(self, *, club_id: str, contract: ClubStaffContract) -> None:
        role_key = contract.staff_profile.staff_type if contract.staff_profile is not None else contract.role_scope
        assignment = self.session.scalar(
            select(ClubStaffAssignment).where(
                ClubStaffAssignment.club_id == club_id,
                ClubStaffAssignment.role_key == role_key,
            )
        )
        if assignment is None:
            self.session.add(
                ClubStaffAssignment(
                    club_id=club_id,
                    staff_contract_id=contract.id,
                    role_key=role_key,
                    active=True,
                )
            )
            return
        assignment.staff_contract_id = contract.id
        assignment.active = True

    def _staff_effects(self, contracts: list[ClubStaffContract]) -> dict[str, int]:
        active = [item for item in contracts if item.status == "active" and item.staff_profile is not None]
        scout_quality = sum(item.staff_profile.rating for item in active if item.staff_profile.staff_type in {"scout", "academy_director"})
        training_bonus = sum(item.staff_profile.rating for item in active if item.staff_profile.staff_type in {"coach", "manager"})
        negotiation_bonus = sum(item.staff_profile.rating for item in active if item.staff_profile.staff_type in {"agent", "negotiation_specialist"})
        return {
            "scout_quality": min(100, scout_quality),
            "training_bonus": min(100, training_bonus),
            "negotiation_bonus": min(100, negotiation_bonus),
        }

    def _sponsorship_summary(self, *, club_id: str) -> SponsorshipClubSummaryView:
        dashboard = SponsorshipEngineService(self.session).dashboard(club_id=club_id)
        return SponsorshipClubSummaryView(
            active_contracts=int(dashboard.get("active_contracts", 0)),
            pending_contracts=int(dashboard.get("pending_contracts", 0)),
            settled_payout_minor=int(dashboard.get("settled_total_minor", 0)),
            outstanding_payout_minor=int(dashboard.get("outstanding_total_minor", 0)),
            open_leads=int(dashboard.get("open_leads", 0)),
        )

    def _audit(
        self,
        *,
        actor: User,
        club_id: str,
        action: str,
        previous_json: dict[str, Any] | None = None,
        next_json: dict[str, Any] | None = None,
        reason: str | None = None,
    ) -> None:
        self.session.add(
            ClubGrowthAuditEvent(
                club_id=club_id,
                action=action,
                previous_json=previous_json or {},
                next_json=next_json or {},
                actor_user_id=actor.id,
                reason=reason,
            )
        )

    def _publish_matrix_notification(
        self,
        *,
        event_key: str,
        target_user_ids: list[str | None],
        resource_id: str,
        message: str,
        metadata: dict[str, Any],
    ) -> None:
        if not self._notification_tables_available():
            return
        normalized_targets = [user_id for user_id in target_user_ids if user_id]
        if not normalized_targets:
            return
        NotificationEventMatrixService(self.session).publish_event(
            event_key=event_key,
            target_user_ids=normalized_targets,
            resource_id=resource_id,
            message=message,
            metadata_json=metadata,
        )

    def _notification_tables_available(self) -> bool:
        inspector = inspect(self.session.connection())
        return all(
            inspector.has_table(table_name)
            for table_name in ("notification_records", "notification_preferences", "users")
        )

    def _staff_profile_view(self, profile: ClubStaffProfile) -> StaffProfileView:
        return StaffProfileView(
            id=profile.id,
            display_name=profile.display_name,
            staff_type=profile.staff_type,
            rarity=profile.rarity,
            skills=list(profile.skills_json or []),
            salary_minor=profile.salary_minor,
            commission_bps=profile.commission_bps,
            rating=profile.rating,
            active=profile.active,
            metadata=dict(profile.metadata_json or {}),
        )

    def _staff_contract_snapshot(self, contract: ClubStaffContract) -> dict[str, Any]:
        return {
            "status": contract.status,
            "salary_minor": contract.salary_minor,
            "commission_bps": contract.commission_bps,
            "duration_days": contract.duration_days,
            "exclusive": contract.exclusive,
        }

    def _staff_contract_view(self, contract: ClubStaffContract) -> StaffContractView:
        return StaffContractView(
            id=contract.id,
            club_id=contract.club_id,
            staff_profile=self._staff_profile_view(contract.staff_profile),
            status=contract.status,
            salary_minor=contract.salary_minor,
            commission_bps=contract.commission_bps,
            duration_days=contract.duration_days,
            role_scope=contract.role_scope,
            exclusive=contract.exclusive,
            started_at=contract.started_at,
            ends_at=contract.ends_at,
            accepted_at=contract.accepted_at,
            terminated_at=contract.terminated_at,
            updated_at=contract.updated_at,
        )

    def _academy_profile_view(self, profile: AcademyProfile) -> AcademyProfileView:
        return AcademyProfileView(
            id=profile.id,
            club_id=profile.club_id,
            level=profile.level,
            investment_minor=profile.investment_minor,
            generation_cooldown_until=profile.generation_cooldown_until,
            metadata=dict(profile.metadata_json or {}),
            updated_at=profile.updated_at,
        )

    def _academy_prospect_view(self, prospect: AcademyProspect) -> AcademyProspectView:
        history = self._promotion_history(prospect_id=prospect.id)
        return AcademyProspectView(
            id=prospect.id,
            club_id=prospect.club_id,
            display_name=prospect.display_name,
            nationality=prospect.nationality,
            position=prospect.position,
            age=prospect.age,
            personality=dict(prospect.personality_json or {}),
            current_ability=prospect.current_ability,
            potential=prospect.potential,
            portrait_asset_ref=prospect.portrait_asset_ref,
            senior_player_id=history.senior_player_id if history is not None else None,
            status=prospect.status,
            metadata=dict(prospect.metadata_json or {}),
            updated_at=prospect.updated_at,
        )

    def _academy_contract_offer_view(self, offer: AcademyRegenContractOffer) -> AcademyContractOfferView:
        return AcademyContractOfferView(
            id=offer.id,
            club_id=offer.club_id,
            prospect_id=offer.prospect_id,
            status=offer.status,
            wage_minor=offer.wage_minor,
            duration_months=offer.duration_months,
            response_reason=offer.response_reason,
            updated_at=offer.updated_at,
        )

    def _academy_generation_run_view(self, run: AcademyGenerationRun) -> AcademyGenerationRunView:
        return AcademyGenerationRunView(
            id=run.id,
            club_id=run.club_id,
            run_seed=run.run_seed,
            prospects_created=run.prospects_created,
            status=run.status,
            created_at=run.created_at,
        )
