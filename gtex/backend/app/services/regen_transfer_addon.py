from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP


DECIMAL_QUANTUM = Decimal("0.0001")
DIRECT_FANCOIN_PER_GTEX = Decimal("100")
AUTO_CONVERSION_PREMIUM_BPS = 1200
BIG_MOVE_THRESHOLD_GTEX = Decimal("40")
RECORD_MOVE_THRESHOLD_GTEX = Decimal("90")


def _clamp_float(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def _quantize(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value)).quantize(DECIMAL_QUANTUM, rounding=ROUND_HALF_UP)


def _format_gtex(value: Decimal) -> str:
    return f"{value:,.4f} GTex Coin"


def _format_fancoin(value: Decimal) -> str:
    return f"{value:,.4f} Fan Coin"


def _format_eur(value: int) -> str:
    return f"EUR {value:,}"


@dataclass(frozen=True, slots=True)
class BigClubApproachInputs:
    approaching_prestige: float
    approaching_trophies: float
    current_prestige: float
    current_trophies: float
    tenure_months: int
    ambition: int
    loyalty: int
    hometown_resistance: float
    rising_club_resistance: float
    already_considering_move: bool = False


@dataclass(frozen=True, slots=True)
class BigClubApproachResult:
    effect_score: float
    resisted: bool
    resulting_state: str
    ambition_pressure_delta: float
    transfer_desire_delta: float
    salary_expectation_delta_pct: float
    prestige_dissatisfaction_delta: float
    title_frustration_delta: float
    resistance_score: float


@dataclass(frozen=True, slots=True)
class TransferPressureInputs:
    current_state: str
    ambition_pressure: float
    transfer_desire: float
    prestige_dissatisfaction: float
    title_frustration: float
    salary_expectation_fancoin_per_year: Decimal
    current_salary_fancoin_per_year: Decimal
    ambition: int
    loyalty: int
    trophy_hunger: int
    greed: int
    current_club_prestige: float
    current_club_trophies: float
    days_remaining: int | None
    unresolved_bonus: float = 0.0
    relief_score: float = 0.0


@dataclass(frozen=True, slots=True)
class TransferPressureComputation:
    ambition_pressure: float
    transfer_desire: float
    prestige_dissatisfaction: float
    title_frustration: float
    salary_expectation_fancoin_per_year: Decimal
    current_state: str
    active_transfer_request: bool
    refuses_new_contract: bool
    end_of_contract_pressure: bool
    pressure_score: float


@dataclass(frozen=True, slots=True)
class PressureResolution:
    transfer_desire_delta: float
    prestige_dissatisfaction_delta: float
    title_frustration_delta: float
    relief_score_delta: float
    unresolved_bonus_delta: float


@dataclass(frozen=True, slots=True)
class TeamDynamicsInputs:
    pressure_score: float
    leadership: int
    importance_score: float
    unresolved_days: int
    active_transfer_request: bool


@dataclass(frozen=True, slots=True)
class TeamDynamicsEffect:
    active: bool
    morale_penalty: float
    chemistry_penalty: float
    tactical_cohesion_penalty: float
    performance_penalty: float
    influences_younger_players: bool


@dataclass(frozen=True, slots=True)
class ContractOfferScoreInputs:
    salary_score: float
    contract_length_score: float
    prestige_score: float
    trophy_score: float
    playing_time_score: float
    hometown_score: float
    manager_fit_score: float
    ambition_alignment_score: float
    greed: int
    ambition: int
    loyalty: int
    professionalism: int
    trophy_hunger: int


@dataclass(frozen=True, slots=True)
class ContractOfferScore:
    total_score: float
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ConversionQuote:
    required_fancoin: Decimal
    current_fancoin_balance: Decimal
    shortfall_fancoin: Decimal
    current_gtex_balance: Decimal
    direct_gtex_equivalent: Decimal
    gtex_required_for_conversion: Decimal
    conversion_premium_bps: int
    can_cover_shortfall: bool
    premium_note: str


@dataclass(frozen=True, slots=True)
class TransferHeadline:
    category: str
    announcement_tier: str
    headline: str
    detail_text: str
    estimated_transfer_fee_eur: int
    estimated_salary_package_eur: int
    estimated_total_value_eur: int
    salary_package_fancoin: Decimal


def classify_transfer_pressure_state(pressure_score: float) -> str:
    if pressure_score >= 84:
        return "unsettled"
    if pressure_score >= 70:
        return "transfer_requested"
    if pressure_score >= 55:
        return "considering_transfer"
    if pressure_score >= 38:
        return "attracted_by_bigger_club"
    if pressure_score >= 20:
        return "monitoring_situation"
    return "content"


def evaluate_big_club_approach(inputs: BigClubApproachInputs) -> BigClubApproachResult:
    prestige_gap = max(0.0, inputs.approaching_prestige - inputs.current_prestige)
    trophy_gap = max(0.0, inputs.approaching_trophies - inputs.current_trophies)
    ambition_gap = max(0.0, inputs.ambition - inputs.current_prestige)
    tenure_boost = min(inputs.tenure_months / 36.0, 1.0) * 14.0
    intent_boost = 10.0 if inputs.already_considering_move else 0.0
    raw_effect = (
        8.0
        + (prestige_gap * 0.38)
        + (trophy_gap * 0.28)
        + (ambition_gap * 0.22)
        + tenure_boost
        + intent_boost
        + (inputs.ambition * 0.10)
        - (inputs.loyalty * 0.05)
    )
    resistance = (
        (inputs.loyalty * 0.42)
        + (inputs.hometown_resistance * 0.32)
        + (inputs.rising_club_resistance * 0.26)
    )
    effect_score = _clamp_float(raw_effect - (resistance * 0.50))
    resisted = effect_score < 22.0
    if resisted:
        effect_score = _clamp_float(effect_score * 0.65)
    salary_delta = min(45.0, 4.0 + (prestige_gap * 0.25) + (trophy_gap * 0.18) + max(inputs.ambition - inputs.loyalty, 0) * 0.08)
    resulting_state = classify_transfer_pressure_state(effect_score if not resisted else max(effect_score - 8.0, 0.0))
    return BigClubApproachResult(
        effect_score=round(effect_score, 2),
        resisted=resisted,
        resulting_state=resulting_state,
        ambition_pressure_delta=round(effect_score * 0.46, 2),
        transfer_desire_delta=round(effect_score * (0.68 if not resisted else 0.34), 2),
        salary_expectation_delta_pct=round(salary_delta if not resisted else salary_delta * 0.45, 2),
        prestige_dissatisfaction_delta=round(max(0.0, (prestige_gap * 0.55) - (inputs.hometown_resistance * 0.12)), 2),
        title_frustration_delta=round(max(0.0, trophy_gap * 0.50), 2),
        resistance_score=round(resistance, 2),
    )


def compute_transfer_pressure(inputs: TransferPressureInputs) -> TransferPressureComputation:
    prestige_gap = max(0.0, inputs.ambition - inputs.current_club_prestige)
    trophy_gap = max(0.0, inputs.trophy_hunger - inputs.current_club_trophies)
    current_salary = max(inputs.current_salary_fancoin_per_year, Decimal("0.0000"))
    expected_salary = max(inputs.salary_expectation_fancoin_per_year, current_salary)
    salary_shortfall_pct = 0.0
    if expected_salary > Decimal("0.0000"):
        salary_shortfall_pct = float(((expected_salary - current_salary) / expected_salary) * Decimal("100"))
    ambition_pressure = _clamp_float(
        max(inputs.ambition_pressure, 0.0)
        + (prestige_gap * 0.35)
        + (salary_shortfall_pct * 0.25)
        - inputs.relief_score
    )
    prestige_dissatisfaction = _clamp_float(
        max(inputs.prestige_dissatisfaction, 0.0)
        + (prestige_gap * 0.42)
        - (inputs.loyalty * 0.06)
        - (inputs.relief_score * 0.25)
    )
    title_frustration = _clamp_float(
        max(inputs.title_frustration, 0.0)
        + (trophy_gap * 0.38)
        - (inputs.relief_score * 0.35)
    )
    pressure_score = _clamp_float(
        (ambition_pressure * 0.34)
        + (prestige_dissatisfaction * 0.24)
        + (title_frustration * 0.20)
        + (salary_shortfall_pct * (0.16 + (inputs.greed / 1250.0)))
        + inputs.unresolved_bonus
        - (inputs.loyalty * 0.05)
    )
    transfer_desire = _clamp_float(max(inputs.transfer_desire, 0.0) + (pressure_score * 0.55) - (inputs.relief_score * 0.40))
    active_transfer_request = pressure_score >= 68.0 or (
        inputs.current_state in {"considering_transfer", "transfer_requested", "unsettled"}
        and pressure_score >= 52.0
    )
    refuses_new_contract = active_transfer_request and (
        salary_shortfall_pct >= 10.0 or prestige_gap >= 16.0 or trophy_gap >= 16.0
    )
    end_of_contract_pressure = refuses_new_contract and inputs.days_remaining is not None and inputs.days_remaining <= 180
    current_state = classify_transfer_pressure_state(max(pressure_score, transfer_desire))
    return TransferPressureComputation(
        ambition_pressure=round(ambition_pressure, 2),
        transfer_desire=round(transfer_desire, 2),
        prestige_dissatisfaction=round(prestige_dissatisfaction, 2),
        title_frustration=round(title_frustration, 2),
        salary_expectation_fancoin_per_year=_quantize(expected_salary),
        current_state=current_state,
        active_transfer_request=active_transfer_request,
        refuses_new_contract=refuses_new_contract,
        end_of_contract_pressure=end_of_contract_pressure,
        pressure_score=round(pressure_score, 2),
    )


def resolution_for_event(
    resolution_type: str,
    *,
    salary_raise_pct: float = 0.0,
    ambition_signal: float = 0.0,
    relationship_boost: float = 0.0,
    trophy_credit: float = 0.0,
) -> PressureResolution:
    normalized = resolution_type.strip().lower()
    if normalized == "trophy_win":
        return PressureResolution(-20.0, -10.0, -22.0, 18.0 + trophy_credit * 0.10, -8.0)
    if normalized == "title_challenge":
        return PressureResolution(-12.0, -6.0, -14.0, 10.0 + trophy_credit * 0.08, -5.0)
    if normalized == "salary_improved":
        relief = min(24.0, max(salary_raise_pct, 0.0) * 0.85)
        return PressureResolution(-relief, -3.0, -2.0, relief, -4.0)
    if normalized == "club_ambition":
        relief = min(18.0, max(ambition_signal, 0.0) * 0.30)
        return PressureResolution(-relief, -8.0, -6.0, relief, -3.0)
    if normalized == "relationship_improved":
        relief = min(14.0, max(relationship_boost, 0.0) * 0.35)
        return PressureResolution(-relief, -5.0, -2.0, relief, -3.0)
    if normalized == "sale_refused":
        return PressureResolution(12.0, 8.0, 3.0, -4.0, 12.0)
    if normalized == "issues_ignored":
        return PressureResolution(10.0, 6.0, 6.0, -3.0, 10.0)
    return PressureResolution(0.0, 0.0, 0.0, 0.0, 0.0)


def build_team_dynamics(inputs: TeamDynamicsInputs) -> TeamDynamicsEffect:
    if not inputs.active_transfer_request:
        return TeamDynamicsEffect(False, 0.0, 0.0, 0.0, 0.0, False)
    unrest_factor = _clamp_float(inputs.pressure_score + (inputs.unresolved_days * 0.8))
    morale = min(12.0, round((unrest_factor / 12.0) + (inputs.importance_score / 35.0), 2))
    chemistry = min(10.0, round((unrest_factor / 15.0) + (inputs.leadership / 28.0), 2))
    tactical = min(8.0, round((unrest_factor / 18.0) + (inputs.importance_score / 50.0), 2))
    performance = min(6.0, round((morale + chemistry + tactical) / 5.0, 2))
    return TeamDynamicsEffect(
        active=True,
        morale_penalty=morale,
        chemistry_penalty=chemistry,
        tactical_cohesion_penalty=tactical,
        performance_penalty=performance,
        influences_younger_players=inputs.leadership >= 68 or inputs.importance_score >= 78.0,
    )


def score_contract_offer(inputs: ContractOfferScoreInputs) -> ContractOfferScore:
    weighted_score = (
        inputs.salary_score * (0.18 + (inputs.greed / 1000.0))
        + inputs.contract_length_score * (0.10 + (inputs.professionalism / 1600.0))
        + inputs.prestige_score * (0.13 + (inputs.ambition / 1300.0))
        + inputs.trophy_score * (0.11 + (inputs.trophy_hunger / 1350.0))
        + inputs.playing_time_score * 0.12
        + inputs.hometown_score * (0.08 + (inputs.loyalty / 2100.0))
        + inputs.manager_fit_score * 0.11
        + inputs.ambition_alignment_score * 0.12
    )
    ranked = sorted(
        (
            ("salary", inputs.salary_score),
            ("contract_length", inputs.contract_length_score),
            ("prestige", inputs.prestige_score),
            ("trophies", inputs.trophy_score),
            ("playing_time", inputs.playing_time_score),
            ("hometown", inputs.hometown_score),
            ("manager_fit", inputs.manager_fit_score),
            ("ambition_alignment", inputs.ambition_alignment_score),
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    return ContractOfferScore(
        total_score=round(weighted_score, 2),
        reasons=tuple(label for label, value in ranked[:3] if value > 0),
    )


def quote_conversion(
    *,
    required_fancoin: Decimal,
    current_fancoin_balance: Decimal,
    current_gtex_balance: Decimal,
    direct_fancoin_per_gtex: Decimal = DIRECT_FANCOIN_PER_GTEX,
    premium_bps: int = AUTO_CONVERSION_PREMIUM_BPS,
) -> ConversionQuote:
    required = _quantize(required_fancoin)
    available_fancoin = _quantize(current_fancoin_balance)
    available_gtex = _quantize(current_gtex_balance)
    shortfall = _quantize(max(required - available_fancoin, Decimal("0.0000")))
    direct_equivalent = _quantize(shortfall / direct_fancoin_per_gtex) if shortfall > 0 else Decimal("0.0000")
    premium_multiplier = Decimal(10_000 + premium_bps) / Decimal(10_000)
    conversion_required = _quantize(direct_equivalent * premium_multiplier) if shortfall > 0 else Decimal("0.0000")
    return ConversionQuote(
        required_fancoin=required,
        current_fancoin_balance=available_fancoin,
        shortfall_fancoin=shortfall,
        current_gtex_balance=available_gtex,
        direct_gtex_equivalent=direct_equivalent,
        gtex_required_for_conversion=conversion_required,
        conversion_premium_bps=premium_bps,
        can_cover_shortfall=available_gtex >= conversion_required,
        premium_note="Direct Fan Coin purchase remains cheaper than GTex Coin auto-conversion.",
    )


def estimated_eur_from_gtex(value_gtex: Decimal, *, eur_per_gtex: int) -> int:
    return int((value_gtex * Decimal(eur_per_gtex)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def estimated_eur_from_fancoin(
    value_fancoin: Decimal,
    *,
    eur_per_gtex: int,
    direct_fancoin_per_gtex: Decimal = DIRECT_FANCOIN_PER_GTEX,
) -> int:
    gtex_equivalent = _quantize(value_fancoin / direct_fancoin_per_gtex)
    return estimated_eur_from_gtex(gtex_equivalent, eur_per_gtex=eur_per_gtex)


def classify_announcement_tier(
    *,
    transfer_fee_gtex_coin: Decimal,
    salary_package_fancoin: Decimal,
    record_flag: bool,
) -> str:
    salary_gtex_equivalent = _quantize(salary_package_fancoin / DIRECT_FANCOIN_PER_GTEX)
    total_gtex = _quantize(transfer_fee_gtex_coin + salary_gtex_equivalent)
    if record_flag or transfer_fee_gtex_coin >= RECORD_MOVE_THRESHOLD_GTEX or total_gtex >= RECORD_MOVE_THRESHOLD_GTEX:
        return "platform_headline"
    if transfer_fee_gtex_coin >= BIG_MOVE_THRESHOLD_GTEX or total_gtex >= BIG_MOVE_THRESHOLD_GTEX:
        return "trend_banner"
    return "feed_card"


def render_transfer_headline(
    *,
    player_name: str,
    selling_club_name: str | None,
    buying_club_name: str,
    transfer_fee_gtex_coin: Decimal,
    salary_fancoin_per_year: Decimal,
    contract_years: int,
    eur_per_gtex: int,
    free_agent: bool = False,
    wonderkid: bool = False,
    legend_tagged: bool = False,
    club_record_signing: bool = False,
    biggest_sale: bool = False,
) -> TransferHeadline:
    fee_gtex = _quantize(transfer_fee_gtex_coin)
    salary_package = _quantize(salary_fancoin_per_year * Decimal(contract_years))
    fee_eur = estimated_eur_from_gtex(fee_gtex, eur_per_gtex=eur_per_gtex)
    salary_eur = estimated_eur_from_fancoin(salary_package, eur_per_gtex=eur_per_gtex)
    total_eur = fee_eur + salary_eur
    if free_agent and fee_gtex >= BIG_MOVE_THRESHOLD_GTEX:
        category = "huge free-agent capture"
    elif club_record_signing or biggest_sale or fee_gtex >= RECORD_MOVE_THRESHOLD_GTEX:
        category = "record transfer"
    elif legend_tagged:
        category = "legend-tagged prospect move"
    elif wonderkid and fee_gtex >= BIG_MOVE_THRESHOLD_GTEX:
        category = "wonderkid mega move"
    elif fee_gtex >= BIG_MOVE_THRESHOLD_GTEX:
        category = "major transfer"
    else:
        category = "major transfer" if free_agent else "normal move"
    record_flag = club_record_signing or biggest_sale or category == "record transfer"
    tier = classify_announcement_tier(
        transfer_fee_gtex_coin=fee_gtex,
        salary_package_fancoin=salary_package,
        record_flag=record_flag,
    )
    move_phrase = (
        f"joined {buying_club_name} on a free capture"
        if free_agent or not selling_club_name
        else f"moved from {selling_club_name} to {buying_club_name}"
    )
    headline = (
        f"{player_name} {move_phrase} for {_format_eur(fee_eur)} ({_format_gtex(fee_gtex)}) "
        f"on a {contract_years}-year salary package worth {_format_eur(salary_eur)} ({_format_fancoin(salary_package)})."
    )
    detail = (
        f"Estimated Real-World Equivalent: {_format_eur(fee_eur)}. "
        f"Estimated Salary Equivalent: {_format_eur(salary_eur)}. "
        f"Actual transfer fee: {_format_gtex(fee_gtex)}. "
        f"Actual salary package: {_format_fancoin(salary_package)}."
    )
    return TransferHeadline(
        category=category,
        announcement_tier=tier,
        headline=headline,
        detail_text=detail,
        estimated_transfer_fee_eur=fee_eur,
        estimated_salary_package_eur=salary_eur,
        estimated_total_value_eur=total_eur,
        salary_package_fancoin=salary_package,
    )


def default_training_fee_gtex(*, current_gsi: int, potential_maximum: int) -> Decimal:
    base_value = Decimal(max(6, round((current_gsi * 0.08) + (potential_maximum * 0.10))))
    return _quantize(base_value)


def default_minimum_salary_fancoin(*, current_gsi: int, ambition: int, greed: int, current_salary: Decimal) -> Decimal:
    baseline = Decimal(max(150, round((current_gsi * 6.0) + (ambition * 3.2) + (greed * 2.4))))
    return _quantize(max(current_salary, baseline))


def unresolved_days_since(unresolved_since: date | None, *, reference_on: date) -> int:
    if unresolved_since is None:
        return 0
    return max(0, (reference_on - unresolved_since).days)
