from __future__ import annotations

from datetime import UTC, datetime, timedelta

from services.publisher.hashtags import build_caption, generate_hashtags
from services.publisher.queue import PublisherJob, PublisherQueue
from services.publisher.scheduler import PublisherSchedulePolicy, PublisherScheduler, build_publish_jobs, should_post


class RecordingAdapter:
    def __init__(self, platform: str) -> None:
        self.platform = platform
        self.calls: list[dict[str, object]] = []

    def publish(self, *, video_path: str, caption: str, hashtags, metadata):
        self.calls.append(
            {
                "video_path": video_path,
                "caption": caption,
                "hashtags": tuple(hashtags),
                "metadata": dict(metadata),
            }
        )
        return {
            "platform": self.platform,
            "status": "posted",
            "post_id": f"{self.platform}-post-{len(self.calls)}",
        }


def test_should_post_requires_high_score_and_short_duration() -> None:
    assert should_post({"viral_score": 71, "duration": 29, "video_path": "clips/raw.mp4"}) is True
    assert should_post({"viral_score": 70, "duration": 29, "video_path": "clips/raw.mp4"}) is False
    assert should_post({"viral_score": 71, "duration": 30, "video_path": "clips/raw.mp4"}) is False
    assert should_post({"viral_score": 90, "duration": 20}) is False


def test_generate_hashtags_and_caption_follow_social_shape() -> None:
    clip = {
        "event_type": "goal",
        "team_name": "Lagos City",
        "player_name": "Ayo Bello",
    }

    hashtags = generate_hashtags(clip)
    caption = build_caption(clip, hashtags=hashtags, style="immediate")

    assert "#goal" in hashtags
    assert "#gtex" in hashtags
    assert any(tag.lower() == "#lagoscity" for tag in hashtags)
    assert "THIS JUST HAPPENED" in caption


def test_build_publish_jobs_creates_immediate_and_polished_batches() -> None:
    now = datetime(2026, 3, 28, 8, 0, tzinfo=UTC)
    clip = {
        "clip_id": "hl_901",
        "match_id": "match_44",
        "title": "Winner at the death",
        "event_type": "goal",
        "team_name": "Lagos City",
        "player_name": "Ayo Bello",
        "viral_score": 96,
        "duration": 18,
        "minute": 89,
        "video_path": "clips/raw_901.mp4",
        "polished_video_path": "clips/polished_901.mp4",
        "event_timestamp": now.isoformat(),
    }

    jobs = build_publish_jobs(
        clip,
        policy=PublisherSchedulePolicy(polished_delay_seconds=600),
        now=now,
    )

    assert len(jobs) == 6
    immediate = [job for job in jobs if job.phase == "immediate"]
    polished = [job for job in jobs if job.phase == "polished"]
    assert len(immediate) == 3
    assert len(polished) == 3
    delay_seconds = int((immediate[0].scheduled_for - now).total_seconds())
    assert 30 <= delay_seconds <= 90
    assert all(job.video_path == "clips/polished_901.mp4" for job in polished)
    assert all("#gtex" in job.hashtags for job in jobs)


def test_queue_claims_jobs_and_persists_post_ids(tmp_path) -> None:
    queue = PublisherQueue(tmp_path / "publisher.db")
    scheduled_for = datetime(2026, 3, 28, 8, 0, tzinfo=UTC)
    job = PublisherJob(
        clip_id="clip_1",
        match_id="match_1",
        platform="tiktok",
        phase="immediate",
        scheduled_for=scheduled_for,
        video_path="clips/clip_1.mp4",
        caption="THIS JUST HAPPENED",
        hashtags=("#football", "#gtex"),
    )

    queue.enqueue(job)
    claimed = queue.claim_due_jobs(now=scheduled_for + timedelta(seconds=1))
    assert len(claimed) == 1
    assert claimed[0].status == "processing"
    assert claimed[0].attempt_count == 1

    posted = queue.mark_posted(job.job_id, post_id="tik_123", response={"status": "posted"})

    assert posted.status == "posted"
    assert posted.post_id == "tik_123"
    assert queue.get(job.job_id).post_id == "tik_123"


def test_scheduler_dispatches_due_jobs_to_all_platforms(tmp_path) -> None:
    queue = PublisherQueue(tmp_path / "publisher.db")
    adapters = {
        "tiktok": RecordingAdapter("tiktok"),
        "instagram": RecordingAdapter("instagram"),
        "youtube": RecordingAdapter("youtube"),
    }
    scheduler = PublisherScheduler(
        queue=queue,
        policy=PublisherSchedulePolicy(polished_delay_seconds=600),
        adapters=adapters,
    )
    now = datetime(2026, 3, 28, 8, 5, tzinfo=UTC)
    clip = {
        "clip_id": "hl_777",
        "match_id": "match_777",
        "title": "Crowd goes wild",
        "event_type": "goal",
        "team_name": "Abuja United",
        "player_name": "Musa Ade",
        "viral_score": 88,
        "duration": 21,
        "minute": 76,
        "video_path": "clips/raw_777.mp4",
        "event_timestamp": (now - timedelta(minutes=5)).isoformat(),
        "publish_polished": False,
    }

    scheduled = scheduler.schedule_clip(clip, now=now)
    assert len(scheduled) == 3

    outcomes = scheduler.publish_due_jobs(now=now, limit=10)

    assert len(outcomes) == 3
    assert all(item["status"] == "posted" for item in outcomes)
    assert len(queue.list_jobs(status="posted")) == 3
    assert len(adapters["tiktok"].calls) == 1
    assert len(adapters["instagram"].calls) == 1
    assert len(adapters["youtube"].calls) == 1
