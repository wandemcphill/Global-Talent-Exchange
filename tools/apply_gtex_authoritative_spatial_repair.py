from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "backend" / "app" / "services" / "match_timeline_service.py"


def replace_method(source: str, name: str, replacement: str) -> str:
    pattern = re.compile(rf"(?ms)^    def {re.escape(name)}\(.*?(?=^    def |\Z)")
    match = pattern.search(source)
    if not match:
        raise RuntimeError(f"Could not locate MatchTimelineService.{name}")
    return source[: match.start()] + replacement.rstrip() + "\n\n" + source[match.end() :]


def main() -> None:
    source = TARGET.read_text(encoding="utf-8")
    import_line = "from app.services.authoritative_spatial_simulation import build_ball_payload, build_player_payloads\n"
    if import_line not in source:
        marker = "from app.schemas.match_viewer import (\n"
        if marker not in source:
            raise RuntimeError("Could not locate match_viewer imports")
        source = source.replace(marker, import_line + marker, 1)

    player_replacement = '''    def _player_payloads(
        self,
        *,
        home_runtime: _TeamRuntime,
        away_runtime: _TeamRuntime,
        home_attacks_right: bool,
        active_event: _ViewerEventContext | None,
        stage: str,
        clock_minute: float,
        possession_side: MatchViewerSide,
        time_seconds: float | None = None,
    ) -> list[dict[str, Any]]:
        return build_player_payloads(
            home_runtime=home_runtime,
            away_runtime=away_runtime,
            home_attacks_right=home_attacks_right,
            active_event=active_event,
            stage=stage,
            clock_minute=clock_minute,
            possession_side=possession_side,
            time_seconds=float(time_seconds if time_seconds is not None else clock_minute * 60.0),
        )'''
    source = replace_method(source, "_player_payloads", player_replacement)

    ball_replacement = '''    def _ball_payload(
        self,
        *,
        player_payloads: list[dict[str, Any]],
        home_runtime: _TeamRuntime,
        away_runtime: _TeamRuntime,
        home_attacks_right: bool,
        active_event: _ViewerEventContext | None,
        stage: str,
        possession_side: MatchViewerSide,
        time_seconds: float | None = None,
    ) -> dict[str, Any]:
        return build_ball_payload(
            player_payloads=player_payloads,
            home_runtime=home_runtime,
            away_runtime=away_runtime,
            home_attacks_right=home_attacks_right,
            active_event=active_event,
            stage=stage,
            possession_side=possession_side,
            time_seconds=float(time_seconds if time_seconds is not None else 0.0),
        )'''
    source = replace_method(source, "_ball_payload", ball_replacement)

    # Pass the absolute frame time into the new continuous simulator. The existing
    # public method signatures remain backwards-compatible for other callers.
    frame_pattern = re.compile(r"(?ms)^        player_payloads = self\._player_payloads\(\n(.*?)^        ball_payload = self\._ball_payload\(\n(.*?)^        return MatchTimelineFrameView\(")
    match = frame_pattern.search(source)
    if not match:
        raise RuntimeError("Could not locate _frame player/ball calls")
    player_call = match.group(1)
    ball_call = match.group(2)
    if "time_seconds=time_seconds" not in player_call:
        player_call = player_call.replace("            possession_side=possession_side,\n", "            possession_side=possession_side,\n            time_seconds=time_seconds,\n", 1)
    if "time_seconds=time_seconds" not in ball_call:
        ball_call = ball_call.replace("            possession_side=possession_side,\n", "            possession_side=possession_side,\n            time_seconds=time_seconds,\n", 1)
    source = source[: match.start()] + "        player_payloads = self._player_payloads(\n" + player_call + "        ball_payload = self._ball_payload(\n" + ball_call + "        return MatchTimelineFrameView(\n" + source[match.end() :]

    TARGET.write_text(source, encoding="utf-8")
    print(f"patched {TARGET}")


if __name__ == "__main__":
    main()
