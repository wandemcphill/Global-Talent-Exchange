from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.admin_engine.service import AdminEngineService
from app.models.hosted_competition import (
    CompetitionTemplate,
    HostedCompetitionSettlement,
    HostedCompetitionSettlementStatus,
    HostedCompetitionStanding,
    HostedCompetitionStatus,
    UserHostedCompetition,
    UserHostedCompetitionParticipant,
)
from app.models.user import User
from app.models.wallet import LedgerAccount, LedgerAccountKind, LedgerEntryReason, LedgerSourceTag, LedgerUnit
from app.story_feed_engine.service import StoryFeedService
from app.wallets.service import InsufficientBalanceError, LedgerPosting, WalletService

DEFAULT_TEMPLATES: tuple[dict[str, object], ...] = (
    {
        'template_key': 'user-hosted-cup-8',
        'title': 'User Hosted Cup',
        'description': 'An 8-team knockout cup for creator leagues and community rivalries.',
        'competition_type': 'user_hosted_cup',
        'team_type': 'club',
        'age_grade': 'senior',
        'cup_or_league': 'cup',
        'participants': 8,
        'viewing_mode': 'broadcast',
        'gift_rules': {'enabled': True},
        'seeding_method': 'random',
        'is_user_hostable': True,
        'entry_fee_fancoin': Decimal('250.0000'),
        'reward_pool_fancoin': Decimal('1600.0000'),
        'platform_fee_bps': 1000,
        'metadata_json': {'family': 'creator'},
        'active': True,
    },
    {
        'template_key': 'user-hosted-league-10',
        'title': 'User Hosted League',
        'description': 'A 10-team league format for creator communities and fan-organized ladders.',
        'competition_type': 'user_hosted_league',
        'team_type': 'club',
        'age_grade': 'senior',
        'cup_or_league': 'league',
        'participants': 10,
        'viewing_mode': 'broadcast',
        'gift_rules': {'enabled': True},
        'seeding_method': 'snake',
        'is_user_hostable': True,
        'entry_fee_fancoin': Decimal('300.0000'),
        'reward_pool_fancoin': Decimal('2400.0000'),
        'platform_fee_bps': 1000,
        'metadata_json': {'family': 'creator'},
        'active': True,
    },
    {
        'template_key': 'queue-cup',
        'title': 'Queue Cup',
        'description': 'Quick-fill queue cup with smaller entry and fast lock window.',
        'competition_type': 'queue_cup',
        'team_type': 'club',
        'age_grade': 'senior',
        'cup_or_league': 'cup',
        'participants': 4,
        'viewing_mode': 'quick',
        'gift_rules': {'enabled': True},
        'seeding_method': 'random',
        'is_user_hostable': True,
        'entry_fee_fancoin': Decimal('100.0000'),
        'reward_pool_fancoin': Decimal('320.0000'),
        'platform_fee_bps': 2000,
        'metadata_json': {'family': 'queue'},
        'active': True,
    },
)

AMOUNT_QUANTUM = Decimal('0.0001')


class HostedCompetitionError(ValueError):
    pass


@dataclass(slots=True)
class HostedCompetitionService:
    session: Session
    wallet_service: WalletService | None = None

    def __post_init__(self) -> None:
        if self.wallet_service is None:
            self.wallet_service = WalletService()

    def _normalize_amount(self, amount: Decimal | int | float | str) -> Decimal:
        return Decimal(str(amount)).quantize(AMOUNT_QUANTUM)

    def seed_defaults(self) -> None:
        existing = {item.template_key for item in self.session.scalars(select(CompetitionTemplate)).all()}
        for payload in DEFAULT_TEMPLATES:
            if payload['template_key'] in existing:
                continue
            self.session.add(CompetitionTemplate(**payload))
        self.session.flush()

    def list_templates(self) -> list[CompetitionTemplate]:
        stmt = select(CompetitionTemplate).where(CompetitionTemplate.active.is_(True)).order_by(CompetitionTemplate.title.asc())
        return list(self.session.scalars(stmt).all())

    def get_template_by_key(self, template_key: str) -> CompetitionTemplate | None:
        return self.session.scalar(select(CompetitionTemplate).where(CompetitionTemplate.template_key == template_key, CompetitionTemplate.active.is_(True)))

    def _active_platform_fee_bps(self) -> int:
        rule = next(iter(AdminEngineService(self.session).list_reward_rules(active_only=True)), None)
        return int(rule.competition_platform_fee_bps if rule is not None else 1000)

    def _competition_escrow_account(self, competition: UserHostedCompetition) -> LedgerAccount:
        code = f'competition:{competition.id}:credit:escrow'
        account = self.session.scalar(select(LedgerAccount).where(LedgerAccount.code == code))
        if account is None:
            account = LedgerAccount(
                code=code,
                label=f'{competition.title} Competition Escrow',
                unit=LedgerUnit.CREDIT,
                kind=LedgerAccountKind.ESCROW,
            )
            self.session.add(account)
            self.session.flush()
        return account

    def _available_escrow_balance(self, competition: UserHostedCompetition) -> Decimal:
        return self.wallet_service.get_balance(self.session, self._competition_escrow_account(competition))

    def _create_entry_participant(self, *, competition: UserHostedCompetition, user: User, role: str) -> UserHostedCompetitionParticipant:
        participant = UserHostedCompetitionParticipant(
            competition_id=competition.id,
            user_id=user.id,
            entry_fee_fancoin=competition.entry_fee_fancoin,
            metadata_json={'role': role},
        )
        self.session.add(participant)
        try:
            self.session.flush()
        except IntegrityError as exc:
            raise HostedCompetitionError('User has already joined this competition.') from exc
        return participant

    def _collect_entry_fee(self, *, competition: UserHostedCompetition, participant: UserHostedCompetitionParticipant, user: User) -> None:
        amount = self._normalize_amount(competition.entry_fee_fancoin)
        if amount <= Decimal('0.0000'):
            participant.metadata_json = {**participant.metadata_json, 'payment_status': 'free'}
            self.session.flush()
            return
        user_account = self.wallet_service.get_user_account(self.session, user, LedgerUnit.CREDIT)
        escrow_account = self._competition_escrow_account(competition)
        if self.wallet_service.get_balance(self.session, user_account) < amount:
            raise InsufficientBalanceError('Available FanCoin balance is lower than the hosted competition entry fee.')
        entries = self.wallet_service.append_transaction(
            self.session,
            postings=[
                LedgerPosting(account=user_account, amount=-amount, source_tag=LedgerSourceTag.USER_COMPETITION_ENTRY_SPEND),
                LedgerPosting(account=escrow_account, amount=amount, source_tag=LedgerSourceTag.USER_COMPETITION_ENTRY_SPEND),
            ],
            reason=LedgerEntryReason.COMPETITION_ENTRY,
            reference=f'hosted-entry:{competition.id}:{user.id}',
            description=f'Hosted competition entry for {competition.title}',
            external_reference=f'hosted-entry:{competition.id}:{user.id}',
            actor=user,
        )
        participant.metadata_json = {
            **participant.metadata_json,
            'payment_status': 'settled',
            'entry_transaction_id': entries[0].transaction_id if entries else None,
        }
        self.session.flush()

    def create_competition(self, *, host: User, payload) -> tuple[UserHostedCompetition, CompetitionTemplate, bool]:
        template = self.get_template_by_key(payload.template_key)
        if template is None or not template.is_user_hostable:
            raise HostedCompetitionError('Competition template was not found or is not hostable.')
        slug = (payload.slug or payload.title).strip().lower().replace(' ', '-')
        if not slug:
            raise HostedCompetitionError('Competition slug cannot be empty.')
        entry_fee = Decimal(str(payload.entry_fee_fancoin if payload.entry_fee_fancoin is not None else template.entry_fee_fancoin)).quantize(Decimal('0.0001'))
        if entry_fee < Decimal('0.0000'):
            raise HostedCompetitionError('Entry fee cannot be negative.')
        max_participants = int(payload.max_participants or template.participants)
        platform_fee_bps = self._active_platform_fee_bps()
        capacity_revenue = entry_fee * Decimal(max_participants)
        platform_fee_amount = (capacity_revenue * Decimal(platform_fee_bps) / Decimal(10_000)).quantize(Decimal('0.0001'))
        reward_pool = max(Decimal('0.0000'), (capacity_revenue - platform_fee_amount).quantize(Decimal('0.0001')))
        competition = UserHostedCompetition(
            template_id=template.id,
            host_user_id=host.id,
            title=payload.title,
            slug=slug,
            description=payload.description,
            visibility=payload.visibility,
            starts_at=payload.starts_at,
            lock_at=payload.lock_at,
            max_participants=max_participants,
            entry_fee_fancoin=entry_fee,
            reward_pool_fancoin=reward_pool,
            platform_fee_amount=platform_fee_amount,
            metadata_json=dict(payload.metadata_json),
            status=HostedCompetitionStatus.OPEN,
        )
        self.session.add(competition)
        self.session.flush()
        participant = self._create_entry_participant(competition=competition, user=host, role='host')
        try:
            self._collect_entry_fee(competition=competition, participant=participant, user=host)
        except InsufficientBalanceError as exc:
            raise HostedCompetitionError(str(exc)) from exc
        return competition, template, True

    def list_public_competitions(self) -> list[UserHostedCompetition]:
        stmt = select(UserHostedCompetition).where(UserHostedCompetition.visibility == 'public').order_by(UserHostedCompetition.created_at.desc())
        return list(self.session.scalars(stmt).all())

    def list_for_host(self, *, user: User) -> list[UserHostedCompetition]:
        stmt = select(UserHostedCompetition).where(UserHostedCompetition.host_user_id == user.id).order_by(UserHostedCompetition.created_at.desc())
        return list(self.session.scalars(stmt).all())

    def get_competition(self, competition_id: str) -> UserHostedCompetition | None:
        return self.session.get(UserHostedCompetition, competition_id)

    def participants_for_competition(self, competition_id: str) -> list[UserHostedCompetitionParticipant]:
        stmt = select(UserHostedCompetitionParticipant).where(UserHostedCompetitionParticipant.competition_id == competition_id).order_by(UserHostedCompetitionParticipant.joined_at.asc())
        return list(self.session.scalars(stmt).all())

    def standings_for_competition(self, competition_id: str) -> list[HostedCompetitionStanding]:
        stmt = select(HostedCompetitionStanding).where(HostedCompetitionStanding.competition_id == competition_id).order_by(HostedCompetitionStanding.final_rank.asc().nullslast(), HostedCompetitionStanding.created_at.asc())
        return list(self.session.scalars(stmt).all())

    def settlements_for_competition(self, competition_id: str) -> list[HostedCompetitionSettlement]:
        stmt = select(HostedCompetitionSettlement).where(HostedCompetitionSettlement.competition_id == competition_id).order_by(HostedCompetitionSettlement.created_at.asc())
        return list(self.session.scalars(stmt).all())

    def finance_snapshot(self, competition_id: str) -> dict[str, Decimal | int | str]:
        competition = self.get_competition(competition_id)
        if competition is None:
            raise HostedCompetitionError('Hosted competition was not found.')
        participants = self.participants_for_competition(competition_id)
        escrow_balance = self._available_escrow_balance(competition)
        settled_prizes = self._normalize_amount(self.session.scalar(select(func.coalesce(func.sum(HostedCompetitionSettlement.net_amount), 0)).where(HostedCompetitionSettlement.competition_id == competition_id, HostedCompetitionSettlement.settlement_type == 'prize')) or 0)
        platform_fee_settled = self._normalize_amount(self.session.scalar(select(func.coalesce(func.sum(HostedCompetitionSettlement.net_amount), 0)).where(HostedCompetitionSettlement.competition_id == competition_id, HostedCompetitionSettlement.settlement_type == 'platform_fee')) or 0)
        return {
            'currency': 'credits',
            'participant_count': len(participants),
            'entry_fee_fancoin': self._normalize_amount(competition.entry_fee_fancoin),
            'gross_collected': self._normalize_amount(competition.entry_fee_fancoin * Decimal(len(participants))),
            'projected_reward_pool': self._normalize_amount(competition.reward_pool_fancoin),
            'projected_platform_fee': self._normalize_amount(competition.platform_fee_amount),
            'escrow_balance': escrow_balance,
            'settled_prizes': settled_prizes,
            'settled_platform_fee': platform_fee_settled,
            'status': competition.status.value if hasattr(competition.status, 'value') else str(competition.status),
        }

    def join_competition(self, *, user: User, competition_id: str) -> tuple[UserHostedCompetition, UserHostedCompetitionParticipant]:
        competition = self.get_competition(competition_id)
        if competition is None:
            raise HostedCompetitionError('Hosted competition was not found.')
        if competition.status not in {HostedCompetitionStatus.OPEN, HostedCompetitionStatus.DRAFT}:
            raise HostedCompetitionError('Hosted competition is not open for joining.')
        current_participants = self.session.scalar(select(func.count(UserHostedCompetitionParticipant.id)).where(UserHostedCompetitionParticipant.competition_id == competition.id)) or 0
        if int(current_participants) >= int(competition.max_participants):
            raise HostedCompetitionError('Hosted competition is already full.')
        participant = self._create_entry_participant(competition=competition, user=user, role='participant')
        try:
            self._collect_entry_fee(competition=competition, participant=participant, user=user)
        except InsufficientBalanceError as exc:
            self.session.delete(participant)
            self.session.flush()
            raise HostedCompetitionError(str(exc)) from exc
        updated_count = int(current_participants) + 1
        if updated_count >= int(competition.max_participants):
            competition.status = HostedCompetitionStatus.LOCKED
            self.session.flush()
        return competition, participant

    def launch_competition(self, *, actor: User, competition_id: str) -> UserHostedCompetition:
        competition = self.get_competition(competition_id)
        if competition is None:
            raise HostedCompetitionError('Hosted competition was not found.')
        participants = self.participants_for_competition(competition_id)
        if len(participants) < 2:
            raise HostedCompetitionError('At least two participants are required before launch.')
        competition.status = HostedCompetitionStatus.LIVE
        existing = {row.user_id for row in self.standings_for_competition(competition_id)}
        for index, item in enumerate(participants, start=1):
            if item.user_id in existing:
                continue
            self.session.add(HostedCompetitionStanding(
                competition_id=competition.id,
                user_id=item.user_id,
                final_rank=index,
                metadata_json={'seed_order': index},
            ))
        StoryFeedService(self.session).publish(
            story_type='competition_launch',
            title=f'{competition.title} is live',
            body='Hosted competition moved into live mode and standings have been initialized.',
            audience='public',
            subject_type='hosted_competition',
            subject_id=competition.id,
            metadata_json={'competition_id': competition.id, 'slug': competition.slug},
            published_by_user_id=actor.id,
        )
        self.session.flush()
        return competition

    def finalize_competition(self, *, actor: User, competition_id: str, placements: Iterable[dict[str, object]], note: str | None = None) -> tuple[UserHostedCompetition, list[HostedCompetitionStanding], list[HostedCompetitionSettlement]]:
        competition = self.get_competition(competition_id)
        if competition is None:
            raise HostedCompetitionError('Hosted competition was not found.')
        if competition.status == HostedCompetitionStatus.COMPLETED:
            raise HostedCompetitionError('Hosted competition has already been completed.')
        participants = {item.user_id for item in self.participants_for_competition(competition_id)}
        if not participants:
            raise HostedCompetitionError('Hosted competition has no participants.')
        escrow_account = self._competition_escrow_account(competition)
        escrow_balance = self.wallet_service.get_balance(self.session, escrow_account)
        if escrow_balance <= Decimal('0.0000'):
            raise HostedCompetitionError('Hosted competition escrow balance is empty.')
        platform_fee = min(self._normalize_amount(competition.platform_fee_amount), escrow_balance)
        prize_pool = self._normalize_amount(escrow_balance - platform_fee)
        placements = list(placements)
        total_percent = sum(Decimal(str(item.get('payout_percent', 0))) for item in placements)
        if total_percent > Decimal('100.0000'):
            raise HostedCompetitionError('Total payout percent cannot exceed 100.')
        standings_by_user = {row.user_id: row for row in self.standings_for_competition(competition_id)}
        if not standings_by_user:
            for item in self.participants_for_competition(competition_id):
                row = HostedCompetitionStanding(competition_id=competition.id, user_id=item.user_id, metadata_json={})
                self.session.add(row)
                self.session.flush()
                standings_by_user[item.user_id] = row
        postings: list[LedgerPosting] = []
        settlements: list[HostedCompetitionSettlement] = []
        total_prize_paid = Decimal('0.0000')
        for item in placements:
            user_id = str(item['user_id'])
            if user_id not in participants:
                raise HostedCompetitionError('A placement referenced a user that is not part of this competition.')
            payout_percent = Decimal(str(item.get('payout_percent', 0)))
            rank = int(item.get('rank', 0) or 0)
            if payout_percent < Decimal('0.0000'):
                raise HostedCompetitionError('Payout percent cannot be negative.')
            payout_amount = self._normalize_amount(prize_pool * payout_percent / Decimal('100'))
            user = self.session.get(User, user_id)
            if user is None:
                raise HostedCompetitionError('A placement referenced a missing user.')
            recipient_account = self.wallet_service.get_user_account(self.session, user, LedgerUnit.CREDIT)
            postings.append(
                LedgerPosting(
                    account=recipient_account,
                    amount=payout_amount,
                    source_tag=LedgerSourceTag.USER_HOSTED_GIFT_INCOME_FANCOIN,
                )
            )
            total_prize_paid += payout_amount
            standing = standings_by_user[user_id]
            standing.final_rank = rank
            standing.payout_amount = payout_amount
            standing.metadata_json = {**(standing.metadata_json or {}), 'payout_percent': str(payout_percent)}
            settlements.append(HostedCompetitionSettlement(
                competition_id=competition.id,
                recipient_user_id=user.id,
                settlement_type='prize',
                status=HostedCompetitionSettlementStatus.PENDING,
                gross_amount=payout_amount,
                platform_fee_amount=Decimal('0.0000'),
                net_amount=payout_amount,
                note=note or '',
                settled_by_user_id=actor.id,
            ))
        platform_account = self.wallet_service.ensure_platform_account(self.session, LedgerUnit.CREDIT)
        if platform_fee > Decimal('0.0000'):
            postings.append(
                LedgerPosting(
                    account=platform_account,
                    amount=platform_fee,
                    source_tag=LedgerSourceTag.HOSTING_FEE_SPEND,
                )
            )
        total_outgoing = self._normalize_amount(total_prize_paid + platform_fee)
        if total_outgoing > escrow_balance:
            raise HostedCompetitionError('Settlement exceeds available escrow balance.')
        if total_prize_paid > Decimal('0.0000'):
            postings.append(
                LedgerPosting(
                    account=escrow_account,
                    amount=-total_prize_paid,
                    source_tag=LedgerSourceTag.USER_HOSTED_GIFT_INCOME_FANCOIN,
                )
            )
        if platform_fee > Decimal('0.0000'):
            postings.append(
                LedgerPosting(
                    account=escrow_account,
                    amount=-platform_fee,
                    source_tag=LedgerSourceTag.HOSTING_FEE_SPEND,
                )
            )
        entries = self.wallet_service.append_transaction(
            self.session,
            postings=postings,
            reason=LedgerEntryReason.COMPETITION_REWARD,
            reference=f'hosted-settlement:{competition.id}',
            description=f'Hosted competition settlement for {competition.title}',
            external_reference=f'hosted-settlement:{competition.id}',
            actor=actor,
        )
        transaction_id = entries[0].transaction_id if entries else None
        for settlement in settlements:
            settlement.status = HostedCompetitionSettlementStatus.SETTLED
            settlement.ledger_transaction_id = transaction_id
            self.session.add(settlement)
        fee_settlement = HostedCompetitionSettlement(
            competition_id=competition.id,
            recipient_user_id=None,
            settlement_type='platform_fee',
            status=HostedCompetitionSettlementStatus.SETTLED,
            gross_amount=platform_fee,
            platform_fee_amount=platform_fee,
            net_amount=platform_fee,
            ledger_transaction_id=transaction_id,
            note=note or '',
            settled_by_user_id=actor.id,
        )
        self.session.add(fee_settlement)
        settlements.append(fee_settlement)
        competition.status = HostedCompetitionStatus.COMPLETED
        StoryFeedService(self.session).publish(
            story_type='competition_result',
            title=f'{competition.title} completed',
            body='Hosted competition settlements have been posted and final standings are available.',
            audience='public',
            subject_type='hosted_competition',
            subject_id=competition.id,
            metadata_json={'competition_id': competition.id, 'slug': competition.slug, 'transaction_id': transaction_id},
            published_by_user_id=actor.id,
        )
        self.session.flush()
        return competition, list(standings_by_user.values()), settlements
