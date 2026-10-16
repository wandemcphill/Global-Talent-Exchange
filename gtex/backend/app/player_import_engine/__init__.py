from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
import random

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.enums.player_pathway_stage import PlayerPathwayStage
from app.common.enums.youth_prospect_rating_band import YouthProspectRatingBand
from app.ingestion.models import Player
from app.models.club_profile import ClubProfile
from app.models.player_import import PlayerImportItem, PlayerImportItemStatus, PlayerImportJob, PlayerImportJobStatus
from app.models.user import User
from app.models.youth_pipeline_snapshot import YouthPipelineSnapshot
from app.models.youth_prospect import YouthProspect
from app.models.youth_prospect_report import YouthProspectReport

FIRST_NAMES = ('Tunde', 'Seyi', 'Ayo', 'Kelechi', 'Ibrahim', 'David', 'Michael', 'Chinedu', 'Omar', 'Santi', 'Leo', 'Kwame')
LAST_NAMES = ('Oni', 'Adeyemi', 'Balogun', 'Okafor', 'Musa', 'Mensah', 'Silva', 'Diallo', 'Ibrahim', 'Torres', 'Costa', 'Ramos')
POSITIONS = ('GK', 'CB', 'LB', 'RB', 'DM', 'CM', 'AM', 'LW', 'RW', 'ST')
TRAITS = ('pace', 'vision', 'press resistance', 'finishing', 'aggression', 'leadership', 'flair')


class PlayerImportError(ValueError):
    pass


@dataclass(slots=True)
class PlayerImportService:
    session: Session

    def _validate_row(self, row: dict[str, object]) -> list[str]:
        errors: list[str] = []
        if not str(row.get('full_name') or '').strip():
            errors.append('full_name is required')
        if not str(row.get('position') or '').strip():
            errors.append('position is required')
        nationality = str(row.get('nationality_code') or '').strip().upper()
        if len(nationality) < 2:
            errors.append('nationality_code must be at least 2 letters')
        age = row.get('age')
        if age is not None and not (13 <= int(age) <= 45):
            errors.append('age must be between 13 and 45')
        return errors

    def _validate_card_supply_row(self, row: dict[str, object]) -> list[str]:
        errors: list[str] = []
        player_id = str(row.get("player_id") or "").strip()
        player_name = str(row.get("player_name") or "").strip()
        if not player_id and not player_name:
            errors.append("player_id or player_name is required")
        tier_code = str(row.get("tier_code") or "").strip()
        if len(tier_code) < 2:
            errors.append("tier_code is required")
        edition_code = str(row.get("edition_code") or "base").strip()
        if len(edition_code) < 2:
            errors.append("edition_code must be at least 2 characters")
        quantity = row.get("quantity")
        if quantity is None or int(quantity) <= 0:
            errors.append("quantity must be greater than 0")
        return errors

    def list_jobs(self) -> list[PlayerImportJob]:
        return list(self.session.scalars(select(PlayerImportJob).order_by(PlayerImportJob.created_at.desc())).all())

    def get_job(self, job_id: str) -> tuple[PlayerImportJob, list[PlayerImportItem]]:
        job = self.session.get(PlayerImportJob, job_id)
        if job is None:
            raise PlayerImportError('Import job was not found.')
        items = list(self.session.scalars(select(PlayerImportItem).where(PlayerImportItem.job_id == job_id).order_by(PlayerImportItem.row_number.asc())).all())
        return job, items

    def create_job(self, *, actor: User, source_type: str, source_label: str, rows: list[dict[str, object]], commit: bool) -> tuple[PlayerImportJob, list[PlayerImportItem]]:
        job = PlayerImportJob(created_by_user_id=actor.id, source_type=source_type.strip().lower(), source_label=source_label.strip(), status=PlayerImportJobStatus.DRAFT)
        self.session.add(job)
        self.session.flush()
        items: list[PlayerImportItem] = []
        imported = 0
        valid = 0
        failed = 0
        for idx, raw in enumerate(rows, start=1):
            payload = dict(raw)
            errors = self._validate_row(payload)
            status = PlayerImportItemStatus.VALID if not errors else PlayerImportItemStatus.INVALID
            item = PlayerImportItem(
                job_id=job.id,
                row_number=idx,
                external_source_id=str(payload.get('external_source_id') or '') or None,
                player_name=str(payload.get('full_name') or '') or None,
                normalized_position=str(payload.get('position') or '').strip().upper() or None,
                nationality_code=str(payload.get('nationality_code') or '').strip().upper() or None,
                age=int(payload['age']) if payload.get('age') is not None else None,
                status=status,
                validation_errors_json=errors,
                payload_json=payload,
            )
            self.session.add(item)
            items.append(item)
            if errors:
                failed += 1
                continue
            valid += 1
            if commit:
                player = self._upsert_player_from_payload(payload)
                item.linked_player_id = player.id
                item.status = PlayerImportItemStatus.IMPORTED
                imported += 1
        job.total_items = len(rows)
        job.valid_items = valid
        job.imported_items = imported
        job.failed_items = failed
        job.status = PlayerImportJobStatus.PROCESSED if commit and failed == 0 else PlayerImportJobStatus.PARTIAL if commit else PlayerImportJobStatus.DRAFT
        if failed == len(rows):
            job.status = PlayerImportJobStatus.FAILED
        self.session.flush()
        return job, items

    def create_card_supply_job(self, *, actor: User, source_label: str, rows: list[dict[str, object]], commit: bool) -> tuple[PlayerImportJob, list[PlayerImportItem]]:
        job = PlayerImportJob(created_by_user_id=actor.id, source_type="card_supply", source_label=source_label.strip(), status=PlayerImportJobStatus.DRAFT)
        self.session.add(job)
        self.session.flush()
        items: list[PlayerImportItem] = []
        imported = 0
        valid = 0
        failed = 0
        for idx, raw in enumerate(rows, start=1):
            payload = dict(raw)
            errors = self._validate_card_supply_row(payload)
            status = PlayerImportItemStatus.VALID if not errors else PlayerImportItemStatus.INVALID
            item = PlayerImportItem(
                job_id=job.id,
                row_number=idx,
                external_source_id=str(payload.get("batch_key") or payload.get("source_reference") or "") or None,
                player_name=str(payload.get("player_name") or payload.get("player_id") or "") or None,
                normalized_position=None,
                nationality_code=None,
                age=None,
                status=status,
                validation_errors_json=errors,
                payload_json=payload,
            )
            self.session.add(item)
            items.append(item)
            if errors:
                failed += 1
                continue
            valid += 1
            if commit:
                try:
                    batch = self._apply_card_supply(actor=actor, payload=payload, source_label=source_label)
                    item.linked_player_id = batch.player_id
                    item.status = PlayerImportItemStatus.IMPORTED
                    imported += 1
                except PlayerImportError as exc:
                    item.status = PlayerImportItemStatus.INVALID
                    item.validation_errors_json = [*errors, str(exc)]
                    failed += 1
        job.total_items = len(rows)
        job.valid_items = valid
        job.imported_items = imported
        job.failed_items = failed
        job.status = PlayerImportJobStatus.PROCESSED if commit and failed == 0 else PlayerImportJobStatus.PARTIAL if commit else PlayerImportJobStatus.DRAFT
        if failed == len(rows):
            job.status = PlayerImportJobStatus.FAILED
        self.session.flush()
        return job, items

    def generate_youth_batch(self, *, actor: User, club_id: str | None, count: int, nationality_code: str, region_label: str) -> tuple[PlayerImportJob, list[PlayerImportItem], list[YouthProspect]]:
        club = self._resolve_club(actor=actor, club_id=club_id)
        rows: list[dict[str, object]] = []
        prospects: list[YouthProspect] = []
        job = PlayerImportJob(created_by_user_id=actor.id, source_type='youth_generation', source_label=f'Youth generation for {club.club_name}', status=PlayerImportJobStatus.PROCESSED)
        self.session.add(job)
        self.session.flush()
        items: list[PlayerImportItem] = []
        for idx in range(1, count + 1):
            payload = self._random_youth_payload(nationality_code=nationality_code, region_label=region_label, club_id=club.id)
            item = PlayerImportItem(
                job_id=job.id,
                row_number=idx,
                external_source_id=payload['external_source_id'],
                player_name=payload['full_name'],
                normalized_position=payload['position'],
                nationality_code=payload['nationality_code'],
                age=payload['age'],
                status=PlayerImportItemStatus.IMPORTED,
                validation_errors_json=[],
                payload_json=payload,
            )
            self.session.add(item)
            items.append(item)
            prospect = YouthProspect(
                club_id=club.id,
                display_name=payload['full_name'],
                age=payload['age'],
                nationality_code=payload['nationality_code'],
                region_label=region_label,
                primary_position=payload['position'],
                secondary_position=random.choice([p for p in POSITIONS if p != payload['position']]),
                rating_band=random.choice(list(YouthProspectRatingBand)),
                development_traits_json=random.sample(TRAITS, 3),
                pathway_stage=PlayerPathwayStage.DISCOVERED,
                scouting_source='generated_youth_pool',
                follow_priority=random.randint(4, 9),
            )
            self.session.add(prospect)
            self.session.flush()
            item.linked_player_id = None
            prospects.append(prospect)
            self.session.add(YouthProspectReport(
                prospect_id=prospect.id,
                confidence_bps=random.randint(6500, 9400),
                summary_text=f"{prospect.display_name} flashes upside in the {region_label} pocket.",
                strengths_json=prospect.development_traits_json[:2],
                development_flags_json=['monitor', 'academy ready'],
            ))
        snapshot = self.session.scalar(select(YouthPipelineSnapshot).where(YouthPipelineSnapshot.club_id == club.id))
        if snapshot is None:
            snapshot = YouthPipelineSnapshot(club_id=club.id, funnel_json={})
            self.session.add(snapshot)
        funnel = dict(snapshot.funnel_json or {})
        funnel['generated'] = int(funnel.get('generated', 0)) + count
        snapshot.funnel_json = funnel
        snapshot.academy_conversion_rate_bps = 2500
        snapshot.promotion_rate_bps = 800
        job.total_items = count
        job.valid_items = count
        job.imported_items = count
        job.failed_items = 0
        job.metadata_json = {'club_id': club.id, 'generated_at': datetime.now(UTC).isoformat()}
        self.session.flush()
        return job, items, prospects

    def list_prospects_for_user(self, *, actor: User) -> list[YouthProspect]:
        club = self._resolve_club(actor=actor, club_id=None)
        return self.list_prospects_for_club(club.id)

    def list_prospects_for_club(self, club_id: str) -> list[YouthProspect]:
        return list(self.session.scalars(select(YouthProspect).where(YouthProspect.club_id == club_id).order_by(YouthProspect.created_at.desc())).all())

    def _resolve_club(self, *, actor: User, club_id: str | None) -> ClubProfile:
        if club_id:
            club = self.session.get(ClubProfile, club_id)
        else:
            club = self.session.scalar(select(ClubProfile).where(ClubProfile.owner_user_id == actor.id).order_by(ClubProfile.created_at.asc()))
        if club is None:
            raise PlayerImportError('Club was not found for this player import action.')
        return club

    def _upsert_player_from_payload(self, payload: dict[str, object]) -> Player:
        provider = 'gtex_manual'
        external_id = str(payload.get('external_source_id') or payload.get('full_name')).strip().lower().replace(' ', '-')
        player = self.session.scalar(select(Player).where(Player.source_provider == provider, Player.provider_external_id == external_id))
        dob = None
        age = payload.get('age')
        if age is not None:
            today = date.today()
            dob = date(today.year - int(age), 1, 1)
        if player is None:
            player = Player(source_provider=provider, provider_external_id=external_id, full_name=str(payload['full_name']).strip())
            self.session.add(player)
        player.full_name = str(payload['full_name']).strip()
        names = player.full_name.split(' ', 1)
        player.first_name = names[0]
        player.last_name = names[1] if len(names) > 1 else None
        player.short_name = player.full_name
        player.position = str(payload['position']).strip().upper()
        player.normalized_position = str(payload['position']).strip().upper()
        player.date_of_birth = dob
        player.market_value_eur = float(payload.get('market_value_eur') or 0) or None
        player.is_tradable = True
        self.session.flush()
        return player

    def _apply_card_supply(self, *, actor: User, payload: dict[str, object], source_label: str) -> "PlayerCardSupplyBatch":
        from app.player_cards.service import PlayerCardMarketService

        player = self._resolve_player_from_supply_payload(payload)
        if player is None:
            raise PlayerImportError("Player was not found for this card supply row.")
        tier_code = str(payload.get("tier_code") or "").strip()
        quantity = int(payload.get("quantity") or 0)
        edition_code = str(payload.get("edition_code") or "base").strip()
        season_label = str(payload.get("season_label") or "").strip() or None
        owner_user_id = str(payload.get("owner_user_id") or "").strip() or None
        source_reference = str(payload.get("source_reference") or "").strip() or None
        batch_key = str(payload.get("batch_key") or "").strip()
        if not batch_key:
            fingerprint = f"{player.id}:{tier_code}:{edition_code}:{owner_user_id or 'unassigned'}:{quantity}"
            batch_key = fingerprint.lower()

        service = PlayerCardMarketService(session=self.session)
        return service.apply_supply_batch(
            actor=actor,
            player_id=player.id,
            tier_code=tier_code,
            quantity=quantity,
            edition_code=edition_code,
            season_label=season_label,
            batch_key=batch_key,
            owner_user_id=owner_user_id,
            source_type="player_card_import",
            source_reference=source_reference or source_label,
            metadata=payload.get("metadata_json") or {},
        )

    def _resolve_player_from_supply_payload(self, payload: dict[str, object]) -> Player | None:
        player_id = str(payload.get("player_id") or "").strip()
        if player_id:
            return self.session.get(Player, player_id)
        player_name = str(payload.get("player_name") or "").strip()
        if not player_name:
            return None
        return self.session.scalar(select(Player).where(Player.full_name.ilike(player_name)))

    def _random_youth_payload(self, *, nationality_code: str, region_label: str, club_id: str) -> dict[str, object]:
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        name = f'{first} {last}'
        age = random.randint(14, 19)
        position = random.choice(POSITIONS)
        return {
            'external_source_id': f'youth-{club_id[:6]}-{first.lower()}-{last.lower()}-{random.randint(100, 999)}',
            'full_name': name,
            'position': position,
            'nationality_code': nationality_code.upper(),
            'age': age,
            'region_label': region_label,
            'market_value_eur': random.randint(25000, 350000),
        }
