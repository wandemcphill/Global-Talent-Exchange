from __future__ import annotations

from datetime import UTC, datetime

from services.publisher.queue import PublisherJob, PublisherQueue


def test_enqueue_returns_existing_record_for_duplicate_target(tmp_path) -> None:
    queue = PublisherQueue(tmp_path / "publisher.db")
    job = PublisherJob(
        clip_id="clip-1",
        match_id="match-1",
        platform="youtube",
        phase="immediate",
        scheduled_for=datetime.now(UTC),
        video_path="/tmp/clip-1.mp4",
        caption="GTEX highlight",
        hashtags=("gtex", "football"),
    )
    duplicate = PublisherJob(
        clip_id="clip-1",
        match_id="match-2",
        platform="youtube",
        phase="immediate",
        scheduled_for=datetime.now(UTC),
        video_path="/tmp/clip-1-alt.mp4",
        caption="Duplicate highlight",
        hashtags=("duplicate",),
    )

    first = queue.enqueue(job)
    second = queue.enqueue(duplicate)

    assert second.job.job_id == first.job.job_id
    assert second.job.match_id == "match-1"
    assert second.job.caption == "GTEX highlight"
    assert len(queue.list_jobs()) == 1
