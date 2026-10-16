from __future__ import annotations

from dataclasses import dataclass

from app.viral.ingestion_schemas import ClipEvent, ClipEventType

_FAST_SCROLL_RATIO_THRESHOLD = 0.03


@dataclass(frozen=True, slots=True)
class ClipAnomalyAssessment:
    flags: tuple[str, ...]
    anomaly_factor: float
    loop_count: int
    pattern_actor_count: int
    ip_cluster_count: int
    device_cluster_count: int

    @property
    def suspicious(self) -> bool:
        return bool(self.flags)


@dataclass(frozen=True, slots=True)
class ClipTrustAnomalyDetector:
    loop_threshold: int = 3
    pattern_cluster_threshold: int = 4
    ip_cluster_threshold: int = 12
    device_cluster_threshold: int = 8

    def assess(
        self,
        event: ClipEvent,
        *,
        loop_count: int,
        pattern_actor_count: int,
        ip_cluster_count: int,
        device_cluster_count: int,
    ) -> ClipAnomalyAssessment:
        flags: list[str] = []

        if event.event_type is ClipEventType.LOOP and loop_count > self.loop_threshold:
            flags.append("repeated_loop_session")

        if event.event_type is ClipEventType.SCROLL and self._is_ultra_fast_scroll(event):
            flags.append("ultra_fast_scroll")

        if pattern_actor_count >= self.pattern_cluster_threshold:
            flags.append("identical_watch_pattern_cluster")

        if ip_cluster_count >= self.ip_cluster_threshold or device_cluster_count >= self.device_cluster_threshold:
            flags.append("abnormal_device_ip_cluster_spike")

        anomaly_factor = 1.0
        if "repeated_loop_session" in flags:
            anomaly_factor -= 0.25
        if "ultra_fast_scroll" in flags:
            anomaly_factor -= 0.20
        if "identical_watch_pattern_cluster" in flags:
            anomaly_factor -= 0.25
        if "abnormal_device_ip_cluster_spike" in flags:
            anomaly_factor -= 0.30

        return ClipAnomalyAssessment(
            flags=tuple(flags),
            anomaly_factor=round(max(0.05, min(anomaly_factor, 1.0)), 4),
            loop_count=max(int(loop_count), 0),
            pattern_actor_count=max(int(pattern_actor_count), 0),
            ip_cluster_count=max(int(ip_cluster_count), 0),
            device_cluster_count=max(int(device_cluster_count), 0),
        )

    @staticmethod
    def _is_ultra_fast_scroll(event: ClipEvent) -> bool:
        if event.watch_time_ms is None or event.video_length_ms is None or event.video_length_ms <= 0:
            return True
        return (float(event.watch_time_ms) / float(event.video_length_ms)) <= _FAST_SCROLL_RATIO_THRESHOLD


__all__ = ["ClipAnomalyAssessment", "ClipTrustAnomalyDetector"]
