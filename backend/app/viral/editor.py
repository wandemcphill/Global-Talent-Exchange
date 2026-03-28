from __future__ import annotations

from dataclasses import dataclass


VERTICAL_FILTER = "crop=in_h*9/16:in_h:(in_w-in_h*9/16)/2:0,scale=1080:1920"
SQUARE_FILTER = "scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080"
WIDESCREEN_FILTER = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080"


@dataclass(slots=True)
class ViralEditPlan:
    format_key: str
    style_preset: str
    aspect_ratio: str
    crop_filter: str
    overlay_text: str
    transcode_command: list[str]
    overlay_command: list[str]
    audio_mix_profile: str
    loop_window_seconds: int
    watermark_text: str
    share_targets: list[str]
    narrative_device: str
    effect_stack: list[str]
    publish_strategy: str
    commentary_prompt: str | None = None


@dataclass(slots=True)
class ViralContentFormatPlan:
    format_key: str
    title: str
    description: str
    editor: ViralEditPlan


def _filter_for_aspect_ratio(aspect_ratio: str) -> str:
    return {
        "1:1": SQUARE_FILTER,
        "16:9": WIDESCREEN_FILTER,
    }.get(aspect_ratio, VERTICAL_FILTER)


def build_transcode_command(input_file: str, output_file: str, *, aspect_ratio: str) -> list[str]:
    return [
        "ffmpeg",
        "-i",
        input_file,
        "-vf",
        _filter_for_aspect_ratio(aspect_ratio),
        "-y",
        output_file,
    ]


def build_overlay_command(input_file: str, output_file: str, *, text: str) -> list[str]:
    safe_text = text.replace(":", r"\:").replace("'", r"\'")
    return [
        "ffmpeg",
        "-i",
        input_file,
        "-vf",
        (
            "drawtext="
            f"text='{safe_text}':"
            "x=(w-text_w)/2:"
            "y=100:"
            "fontsize=54:"
            "fontcolor=white:"
            "box=1:"
            "boxcolor=black@0.45:"
            "boxborderw=18"
        ),
        "-y",
        output_file,
    ]


def build_edit_plan(
    *,
    storage_key: str | None,
    overlay_text: str,
    duration_seconds: int | None,
    format_key: str = "instant_clip",
    aspect_ratio: str = "9:16",
    audio_mix_profile: str | None = None,
    share_targets: list[str] | None = None,
    watermark_text: str = "GTEX",
    style_preset: str | None = None,
    narrative_device: str = "raw_moment",
    effect_stack: list[str] | None = None,
    publish_strategy: str = "post_now",
    commentary_prompt: str | None = None,
) -> ViralEditPlan:
    source = storage_key or "match_clip.mp4"
    suffix = format_key.replace("-", "_")
    transcode_target = source.replace(".mp4", f"_{suffix}.mp4") if source.endswith(".mp4") else f"{source}_{suffix}.mp4"
    overlay_target = transcode_target.replace(".mp4", "_overlay.mp4")
    return ViralEditPlan(
        format_key=format_key,
        style_preset=style_preset or format_key,
        aspect_ratio=aspect_ratio,
        crop_filter=_filter_for_aspect_ratio(aspect_ratio),
        overlay_text=overlay_text,
        transcode_command=build_transcode_command(source, transcode_target, aspect_ratio=aspect_ratio),
        overlay_command=build_overlay_command(transcode_target, overlay_target, text=overlay_text),
        audio_mix_profile=audio_mix_profile or ("crowd_spike_goal_bass" if duration_seconds and duration_seconds <= 18 else "broadcast_clean"),
        loop_window_seconds=max(2, min(duration_seconds or 8, 10)),
        watermark_text=watermark_text,
        share_targets=list(share_targets or ["whatsapp", "tiktok", "stories"]),
        narrative_device=narrative_device,
        effect_stack=list(effect_stack or []),
        publish_strategy=publish_strategy,
        commentary_prompt=commentary_prompt,
    )


def build_content_format_plans(
    *,
    storage_key: str | None,
    title: str,
    event_type: str,
    overlay_text: str,
    duration_seconds: int | None,
    team_name: str | None = None,
    player_name: str | None = None,
) -> list[ViralContentFormatPlan]:
    subject = player_name or team_name or title
    uppercase_hook = overlay_text.upper()
    return [
        ViralContentFormatPlan(
            format_key="instant_clip",
            title="Instant Clip",
            description="Raw moment pushed out immediately to capture the first spike of attention.",
            editor=build_edit_plan(
                storage_key=storage_key,
                overlay_text=overlay_text,
                duration_seconds=duration_seconds,
                format_key="instant_clip",
                style_preset="raw_reactive",
                narrative_device="raw_moment",
                effect_stack=["quick_cut", "score_bug", "caption_burn"],
                publish_strategy="post_now",
                share_targets=["whatsapp", "tiktok", "stories"],
            ),
        ),
        ViralContentFormatPlan(
            format_key="cinematic_replay",
            title="Cinematic Replay",
            description="Polished replay cut with slower pacing, drama, and guided commentary.",
            editor=build_edit_plan(
                storage_key=storage_key,
                overlay_text=f"Replay: {title}",
                duration_seconds=duration_seconds,
                format_key="cinematic_replay",
                style_preset="cinematic_replay",
                narrative_device="slow_motion_recap",
                effect_stack=["slow_motion", "crowd_swell", "commentary_bed"],
                publish_strategy="follow_up",
                audio_mix_profile="cinematic_replay_swell",
                share_targets=["tiktok", "instagram_reels", "youtube_shorts"],
                commentary_prompt=f"Explain why {subject} changed the match in one dramatic line.",
            ),
        ),
        ViralContentFormatPlan(
            format_key="debate_clip",
            title="Debate Clip",
            description="Two AI pundit voices frame the moment as an argument to trigger comments.",
            editor=build_edit_plan(
                storage_key=storage_key,
                overlay_text=f"Debate: {title}",
                duration_seconds=duration_seconds,
                format_key="debate_clip",
                style_preset="pundit_faceoff",
                narrative_device="ai_pundit_argument",
                effect_stack=["split_screen", "reaction_sting", "comment_bait"],
                publish_strategy="comment_harvest",
                audio_mix_profile="ai_pundit_duel",
                share_targets=["tiktok", "x", "stories"],
                commentary_prompt=f"Generate opposing takes on whether {subject} was brilliance or defensive failure.",
            ),
        ),
        ViralContentFormatPlan(
            format_key="tactical_breakdown",
            title="Tactical Breakdown",
            description="Higher-signal analysis cut with arrows, sequencing, and positional framing.",
            editor=build_edit_plan(
                storage_key=storage_key,
                overlay_text=f"Tactical: {event_type.replace('_', ' ')}",
                duration_seconds=duration_seconds,
                format_key="tactical_breakdown",
                aspect_ratio="16:9",
                style_preset="analysis_board",
                narrative_device="coaching_tape",
                effect_stack=["freeze_frame", "arrow_overlay", "zone_labels"],
                publish_strategy="high_value_follow_up",
                audio_mix_profile="tactical_breakdown_clean",
                share_targets=["youtube", "instagram_reels"],
                commentary_prompt=f"Break down the tactical chain that produced {title}.",
            ),
        ),
        ViralContentFormatPlan(
            format_key="meme_version",
            title="Meme Version",
            description="Caption-heavy comedic cut optimized for replays, shares, and low-friction reactions.",
            editor=build_edit_plan(
                storage_key=storage_key,
                overlay_text=uppercase_hook,
                duration_seconds=duration_seconds,
                format_key="meme_version",
                style_preset="meme_blast",
                narrative_device="comedic_reaction",
                effect_stack=["hard_caption", "record_scratch", "zoom_punch"],
                publish_strategy="share_flood",
                audio_mix_profile="meme_sting_pack",
                share_targets=["whatsapp", "tiktok", "x"],
                watermark_text="GTEX Meme",
                commentary_prompt=f"Turn {title} into a short meme caption with one punchline.",
            ),
        ),
    ]
