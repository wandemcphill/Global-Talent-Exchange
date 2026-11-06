import {
  sanitizeForSpectator,
  resolveCanonicalMatchKey,
  StreamFrameDeduplicator,
  SpectatorSafeFrameView,
} from "./spectatorContract";

describe("spectatorContract", () => {
  const mockRawMatchState = {
    match_id: "match-legacy-352",
    source: "live_match_hub",
    canonical_match_id: "canonical-competition-match-777",
    home_team: {
      team_id: "club-1",
      team_name: "Apex Lagos FC",
      short_name: "APX",
      formation: "4-3-3",
      primary_color: "#00E676",
      secondary_color: "#F5B83D",
    },
    away_team: {
      team_id: "club-2",
      team_name: "Nairobi Stars",
      short_name: "NST",
      formation: "4-4-2",
      primary_color: "#3B82F6",
      secondary_color: "#1E40AF",
    },
    presentation_package: {
      match_label: "Apex Lagos FC vs Nairobi Stars",
      coach_notes: [
        "Opponent fullback vulnerable to high press",
        "Target right half-space during transitions",
      ],
      context: {
        competition_name: "GTEX Super Cup",
        venue_name: "Lagos National Arena",
      },
    },
    frames: [
      {
        frame_id: "f-1",
        time_seconds: 1.0,
        clock_minute: 0,
        phase: "open_play",
        home_score: 0,
        away_score: 0,
        players: [{ player_id: "p1", position: { x: 50, y: 50 } }],
        ball: { position: { x: 50, y: 50 }, height: 0, state: "rolling" },
      },
    ],
    events: [],
  };

  test("strips confidential coach notes for general spectators", () => {
    const sanitized = sanitizeForSpectator(mockRawMatchState, false);
    expect(sanitized.coach_notes).toBeUndefined();
    expect(sanitized.home_team.team_name).toBe("Apex Lagos FC");
    expect(sanitized.away_team.team_name).toBe("Nairobi Stars");
    expect(sanitized.is_owner_or_manager).toBe(false);
  });

  test("preserves confidential coach notes for verified owner or manager", () => {
    const sanitized = sanitizeForSpectator(mockRawMatchState, true);
    expect(sanitized.coach_notes).toBeDefined();
    expect(sanitized.coach_notes).toHaveLength(2);
    expect(sanitized.coach_notes?.[0]).toContain("Opponent fullback vulnerable");
    expect(sanitized.is_owner_or_manager).toBe(true);
  });

  test("resolves canonical match key from Issue #352 metadata mapping", () => {
    expect(resolveCanonicalMatchKey("raw-match-123", { canonical_match_id: "canon-456" })).toBe("canon-456");
    expect(resolveCanonicalMatchKey("raw-match-123", { metadata_json: { canonical_match_id: "canon-789" } })).toBe("canon-789");
    expect(resolveCanonicalMatchKey("direct-id-999")).toBe("direct-id-999");
  });

  test("deduplicates frames and rejects out-of-order time jitter", () => {
    const dedup = new StreamFrameDeduplicator();

    const frame1: SpectatorSafeFrameView = {
      frame_id: "frame-1",
      time_seconds: 10.0,
      clock_minute: 1,
      phase: "open_play",
      home_score: 0,
      away_score: 0,
      home_attacks_right: true,
      possession_side: "home",
      camera_preset: "broadcast",
      players: [],
      ball: { position: { x: 50, y: 50 }, height: 0, state: "rolling" },
    };

    const frame2: SpectatorSafeFrameView = {
      ...frame1,
      frame_id: "frame-2",
      time_seconds: 11.0,
    };

    const frameDuplicate: SpectatorSafeFrameView = {
      ...frame1,
      frame_id: "frame-1",
    };

    const frameJitter: SpectatorSafeFrameView = {
      ...frame1,
      frame_id: "frame-3",
      time_seconds: 10.2, // Backwards relative to frame2's 11.0
    };

    expect(dedup.process(frame1)).not.toBeNull();
    expect(dedup.process(frameDuplicate)).toBeNull(); // Duplicate suppressed
    expect(dedup.process(frame2)).not.toBeNull();
    expect(dedup.process(frameJitter)).toBeNull(); // Out of order jitter suppressed
  });
});
