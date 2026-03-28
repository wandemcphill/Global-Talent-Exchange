from __future__ import annotations

from dataclasses import dataclass

from app.viral.captions import CaptionResult
from app.viral.scorer import ViralScoreContext

_GOAL_EVENTS = {"goal", "penalty_goal", "penalty_scored"}
_SAVE_EVENTS = {"double_save", "goalkeeper_save", "save"}
_TACTICAL_EVENTS = _GOAL_EVENTS | _SAVE_EVENTS | {"red_card", "tactical_swing", "missed_big_chance", "woodwork"}


@dataclass(frozen=True, slots=True)
class ContentPersona:
    code: str
    name: str
    tone: str


@dataclass(frozen=True, slots=True)
class AccountProfile:
    handle: str
    niche: str
    target_audience: str
    persona_code: str
    focus_event_types: tuple[str, ...]
    primary_hashtags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CaptionTestPlan:
    variant_key: str
    audience: str
    hook: str
    caption: str
    hashtags: tuple[str, ...]
    source: str
    hypothesis: str | None = None


@dataclass(frozen=True, slots=True)
class DistributionAccountPlan:
    handle: str
    niche: str
    target_audience: str
    fit_score: int
    persona: ContentPersona
    cross_promo_handles: tuple[str, ...]
    caption_tests: tuple[CaptionTestPlan, ...]


PERSONAS: dict[str, ContentPersona] = {
    "hype_king": ContentPersona(
        code="hype_king",
        name="HypeKing",
        tone="loud, emotional, meme-heavy",
    ),
    "tactician": ContentPersona(
        code="tactician",
        name="Tactician",
        tone="analytical, calm",
    ),
}

ACCOUNT_PROFILES: tuple[AccountProfile, ...] = (
    AccountProfile(
        handle="@GTEXGoals",
        niche="High-conviction goals and finishing moments",
        target_audience="broad football clip viewers",
        persona_code="hype_king",
        focus_event_types=("goal", "penalty_goal", "penalty_scored"),
        primary_hashtags=("#GTEX", "#Goals", "#FootballClips"),
    ),
    AccountProfile(
        handle="@LastMinuteDrama",
        niche="Late chaos, equalizers, and match-swing moments",
        target_audience="fans who share pressure moments fast",
        persona_code="hype_king",
        focus_event_types=("goal", "penalty_goal", "penalty_scored", "double_save", "goalkeeper_save", "save", "red_card"),
        primary_hashtags=("#GTEX", "#LateDrama", "#ClutchMoment"),
    ),
    AccountProfile(
        handle="@StreetFootballEnergy",
        niche="Flair, confidence, and raw player energy",
        target_audience="younger short-form viewers and flair fans",
        persona_code="hype_king",
        focus_event_types=("goal", "penalty_goal", "penalty_scored", "double_save", "save", "woodwork"),
        primary_hashtags=("#GTEX", "#StreetEnergy", "#FootballCulture"),
    ),
    AccountProfile(
        handle="@TacticalBreakdown",
        niche="Tactical analysis, structure, and sequence review",
        target_audience="detail-oriented and analysis-first fans",
        persona_code="tactician",
        focus_event_types=tuple(sorted(_TACTICAL_EVENTS)),
        primary_hashtags=("#GTEX", "#TacticalBreakdown", "#FootballAnalysis"),
    ),
)


def catalog_accounts() -> tuple[AccountProfile, ...]:
    return ACCOUNT_PROFILES


def build_distribution_accounts(
    *,
    title: str,
    event_type: str,
    minute: int,
    team_name: str | None,
    player_name: str | None,
    scoreline_label: str | None,
    default_caption: CaptionResult,
    context: ViralScoreContext,
) -> tuple[DistributionAccountPlan, ...]:
    normalized_event = event_type.strip().lower()
    scored_accounts = [
        (
            account,
            PERSONAS[account.persona_code],
            _fit_score(account=account, event_type=normalized_event, minute=minute, context=context, player_name=player_name),
        )
        for account in ACCOUNT_PROFILES
    ]
    scored_accounts.sort(key=lambda item: item[2], reverse=True)
    selected = [item for item in scored_accounts if item[2] >= 55]
    if not selected and scored_accounts:
        selected = [scored_accounts[0]]

    selected_handles = [item[0].handle for item in selected]
    plans: list[DistributionAccountPlan] = []
    for account, persona, fit_score in selected:
        cross_promo_handles = tuple(handle for handle in selected_handles if handle != account.handle)[:2]
        caption_tests = _build_caption_tests(
            account=account,
            persona=persona,
            title=title,
            event_type=normalized_event,
            minute=minute,
            team_name=team_name,
            player_name=player_name,
            scoreline_label=scoreline_label,
            default_caption=default_caption,
            context=context,
        )
        plans.append(
            DistributionAccountPlan(
                handle=account.handle,
                niche=account.niche,
                target_audience=account.target_audience,
                fit_score=fit_score,
                persona=persona,
                cross_promo_handles=cross_promo_handles,
                caption_tests=caption_tests,
            )
        )
    return tuple(plans)


def _fit_score(
    *,
    account: AccountProfile,
    event_type: str,
    minute: int,
    context: ViralScoreContext,
    player_name: str | None,
) -> int:
    score = 18
    if event_type in account.focus_event_types:
        score += 24
    if account.handle == "@GTEXGoals":
        if event_type in _GOAL_EVENTS:
            score += 28
        if minute >= 75:
            score += 8
        if context.go_ahead or context.equalizer or context.comeback:
            score += 10
    elif account.handle == "@LastMinuteDrama":
        if minute >= 85:
            score += 32
        elif minute >= 75:
            score += 20
        if context.go_ahead or context.equalizer or context.comeback:
            score += 16
        if context.is_final:
            score += 8
    elif account.handle == "@StreetFootballEnergy":
        if event_type in _GOAL_EVENTS:
            score += 16
        if context.crowd_spike:
            score += 12
        if player_name:
            score += 8
        if context.total_goals >= 4:
            score += 6
    elif account.handle == "@TacticalBreakdown":
        score += 14
        if context.go_ahead or context.equalizer or context.comeback:
            score += 10
        if context.xg >= 0.30:
            score += 6
        if context.is_final:
            score += 4
    return max(0, min(score, 100))


def _build_caption_tests(
    *,
    account: AccountProfile,
    persona: ContentPersona,
    title: str,
    event_type: str,
    minute: int,
    team_name: str | None,
    player_name: str | None,
    scoreline_label: str | None,
    default_caption: CaptionResult,
    context: ViralScoreContext,
) -> tuple[CaptionTestPlan, CaptionTestPlan]:
    if account.handle == "@GTEXGoals":
        return _build_goal_account_tests(
            account=account,
            title=title,
            minute=minute,
            team_name=team_name,
            player_name=player_name,
            scoreline_label=scoreline_label,
            default_caption=default_caption,
            context=context,
        )
    if account.handle == "@LastMinuteDrama":
        return _build_drama_account_tests(
            account=account,
            minute=minute,
            team_name=team_name,
            player_name=player_name,
            scoreline_label=scoreline_label,
            default_caption=default_caption,
            context=context,
        )
    if account.handle == "@StreetFootballEnergy":
        return _build_street_account_tests(
            account=account,
            team_name=team_name,
            player_name=player_name,
            scoreline_label=scoreline_label,
            default_caption=default_caption,
            context=context,
        )
    return _build_tactical_account_tests(
        account=account,
        persona=persona,
        title=title,
        event_type=event_type,
        team_name=team_name,
        player_name=player_name,
        scoreline_label=scoreline_label,
        context=context,
    )


def _build_goal_account_tests(
    *,
    account: AccountProfile,
    title: str,
    minute: int,
    team_name: str | None,
    player_name: str | None,
    scoreline_label: str | None,
    default_caption: CaptionResult,
    context: ViralScoreContext,
) -> tuple[CaptionTestPlan, CaptionTestPlan]:
    team = team_name or "this side"
    player = player_name or "the finisher"
    moment_label = _moment_label(minute=minute, scoreline_label=scoreline_label)
    hook_a = default_caption.hook
    if context.go_ahead or context.equalizer or context.comeback:
        hook_a = f"{moment_label} and the whole match tilts."
    hook_b = "Clip this one now. The finish sells itself."
    return (
        CaptionTestPlan(
            variant_key="A",
            audience="impulse-share viewers",
            hook=hook_a,
            caption=f"{player} puts {team} on the map in one touch. Clean finish, immediate replay value, wide-audience appeal.",
            hashtags=_hashtags(account=account, context=context, extra="#Finish"),
            source="persona-template",
            hypothesis="Emotion-first goal hooks should win more instant reshares.",
        ),
        CaptionTestPlan(
            variant_key="B",
            audience="goal compilation followers",
            hook=hook_b,
            caption=f"{title}. {moment_label} turns into a postable goal moment for {team} and it does not need extra framing.",
            hashtags=_hashtags(account=account, context=context, extra="#GoalClip"),
            source="persona-template",
            hypothesis="Direct utility framing should lift completion for compilation audiences.",
        ),
    )


def _build_drama_account_tests(
    *,
    account: AccountProfile,
    minute: int,
    team_name: str | None,
    player_name: str | None,
    scoreline_label: str | None,
    default_caption: CaptionResult,
    context: ViralScoreContext,
) -> tuple[CaptionTestPlan, CaptionTestPlan]:
    team = team_name or "the side"
    player = player_name or "someone"
    moment_label = _moment_label(minute=minute, scoreline_label=scoreline_label)
    dramatic_hook = f"{moment_label} and the match snaps."
    if minute < 75:
        dramatic_hook = default_caption.hook
    state_line = _swing_state(context=context)
    return (
        CaptionTestPlan(
            variant_key="A",
            audience="late-game chaos sharers",
            hook=dramatic_hook,
            caption=f"{player} waits for the pressure spike and flips the energy for {team}. {state_line}",
            hashtags=_hashtags(account=account, context=context, extra="#PressureMoment"),
            source="persona-template",
            hypothesis="Clock-pressure framing should outperform neutral match descriptions.",
        ),
        CaptionTestPlan(
            variant_key="B",
            audience="clutch-moment collectors",
            hook="This is what the red zone does to a match.",
            caption=f"No calm ending here. {moment_label} becomes a forwarding moment because {team} land the decisive action under stress.",
            hashtags=_hashtags(account=account, context=context, extra="#MatchSwing"),
            source="persona-template",
            hypothesis="Stress-language hooks should improve share intent on late clips.",
        ),
    )


def _build_street_account_tests(
    *,
    account: AccountProfile,
    team_name: str | None,
    player_name: str | None,
    scoreline_label: str | None,
    default_caption: CaptionResult,
    context: ViralScoreContext,
) -> tuple[CaptionTestPlan, CaptionTestPlan]:
    team = team_name or "the side"
    player = player_name or "the player"
    texture = "crowd up, confidence up, replay loop on" if context.crowd_spike else "zero fear, zero hesitation, pure confidence"
    scoreline = scoreline_label or "match level"
    return (
        CaptionTestPlan(
            variant_key="A",
            audience="flair-first short-form viewers",
            hook="Pure street energy in one action.",
            caption=f"{player} turns {scoreline} into a confidence clip for {team}. {texture}.",
            hashtags=_hashtags(account=account, context=context, extra="#Flair"),
            source="persona-template",
            hypothesis="Identity-driven language should resonate with younger replay viewers.",
        ),
        CaptionTestPlan(
            variant_key="B",
            audience="player-personality followers",
            hook="Playground confidence, stadium scale.",
            caption=f"{default_caption.caption} The reason it travels is the attitude inside the action, not only the outcome.",
            hashtags=_hashtags(account=account, context=context, extra="#PlayerEnergy"),
            source="persona-template",
            hypothesis="Personality framing should hold viewers who follow players more than teams.",
        ),
    )


def _build_tactical_account_tests(
    *,
    account: AccountProfile,
    persona: ContentPersona,
    title: str,
    event_type: str,
    team_name: str | None,
    player_name: str | None,
    scoreline_label: str | None,
    context: ViralScoreContext,
) -> tuple[CaptionTestPlan, CaptionTestPlan]:
    team = team_name or "the side"
    player = player_name or "the player"
    opening = _tactical_opening(event_type=event_type, context=context)
    structural_note = _structural_note(event_type=event_type, context=context, team_name=team, player_name=player)
    scoreline = scoreline_label or "the scoreline"
    return (
        CaptionTestPlan(
            variant_key="A",
            audience="analysis-first viewers",
            hook=opening,
            caption=f"{structural_note} That is why {title.lower()} belongs on a tactical rail, not only a hype page.",
            hashtags=_hashtags(account=account, context=context, extra="#Structure"),
            source="persona-template",
            hypothesis=f"{persona.name} should retain viewers who want explanation before emotion.",
        ),
        CaptionTestPlan(
            variant_key="B",
            audience="coaches and detail-oriented fans",
            hook="Pause the frame one second before the outcome.",
            caption=f"Once the spacing breaks, {scoreline} is vulnerable. {team} get the decisive edge because the sequence problem is not solved early enough.",
            hashtags=_hashtags(account=account, context=context, extra="#SequencePlay"),
            source="persona-template",
            hypothesis="Instructional framing should improve saves for tactical audiences.",
        ),
    )


def _hashtags(*, account: AccountProfile, context: ViralScoreContext, extra: str) -> tuple[str, ...]:
    tags = list(account.primary_hashtags)
    if context.go_ahead:
        tags.append("#GoAhead")
    elif context.equalizer:
        tags.append("#Equalizer")
    elif context.comeback:
        tags.append("#Comeback")
    if context.is_final:
        tags.append("#Final")
    tags.append(extra)
    return tuple(tags)


def _moment_label(*, minute: int, scoreline_label: str | None) -> str:
    if scoreline_label:
        return f"{minute}' at {scoreline_label}"
    return f"{minute}'"


def _swing_state(*, context: ViralScoreContext) -> str:
    if context.comeback:
        return "The comeback angle is obvious on first watch."
    if context.equalizer:
        return "It drags the match back into chaos instantly."
    if context.go_ahead:
        return "That touch changes who owns the game."
    return "The clip works because the pressure is visible before the action lands."


def _tactical_opening(*, event_type: str, context: ViralScoreContext) -> str:
    if event_type in _SAVE_EVENTS:
        return "The keeper wins the second phase."
    if event_type in _GOAL_EVENTS and context.equalizer:
        return "Poor rest defense leaves the equalizer open."
    if event_type in _GOAL_EVENTS and context.go_ahead:
        return "Poor defensive spacing opens the winning lane."
    if event_type in _GOAL_EVENTS:
        return "Poor defensive spacing opens the finish."
    return "The sequence explains the outcome."


def _structural_note(
    *,
    event_type: str,
    context: ViralScoreContext,
    team_name: str,
    player_name: str,
) -> str:
    if event_type in _SAVE_EVENTS:
        return (
            f"{player_name} keeps {team_name} alive because the recovery shape holds long enough "
            "for the second action to be won."
        )
    if context.equalizer:
        return (
            f"The finish matters, but the real trigger is that {team_name} attack a defense that "
            "fails to reset the weak side."
        )
    if context.go_ahead:
        return (
            f"{player_name} gets the finish, but the decisive edge comes from delayed pressure and "
            "a lane that never closes."
        )
    return (
        f"The headline is the end product, yet the value for analysts is the spacing problem that "
        f"lets {player_name} punish the sequence."
    )
