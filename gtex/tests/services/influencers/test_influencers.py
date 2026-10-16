from __future__ import annotations

from services.influencers import build_persona_publish_jobs, generate_persona_content, resolve_voice_profile, select_persona


def test_select_persona_and_voice_profile_follow_story_context() -> None:
    clip = {"event_type": "winner", "viral_score": 91}

    persona = select_persona(clip, story_tags=("rivalry",))
    profile = resolve_voice_profile(persona)

    assert persona.name == "Coach Rage"
    assert profile.preset == "hype"


def test_persona_content_and_publish_jobs_bridge_into_publisher_pipeline() -> None:
    clip = {
        "clip_id": "clip_900",
        "match_id": "match_900",
        "title": "Late winner",
        "event_type": "winner",
        "team_name": "Lagos Titans",
        "opponent_name": "Abuja Storm",
        "player_name": "Ayo Bello",
        "viral_score": 92,
        "duration": 19,
        "minute": 88,
        "video_path": "generated/match_900/raw.mp4",
        "polished_video_path": "generated/match_900/polished.mp4",
        "metadata": {"story_tags": ["underdog"]},
    }

    content = generate_persona_content("Street Analyst", clip, story_tags=("underdog",))
    jobs = build_persona_publish_jobs(clip, story_tags=("underdog",))

    assert content["voice_style"] == "african_radio"
    assert content["caption"].startswith("Street Analyst:")
    assert len(jobs) == 6
    assert all(job.caption.startswith("Street Analyst:") for job in jobs)
    assert all(job.metadata["persona"]["name"] == "Street Analyst" for job in jobs)
