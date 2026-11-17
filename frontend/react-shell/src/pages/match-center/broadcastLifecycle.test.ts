import {
  canonicalBroadcastPhase,
  isActiveCanonicalBroadcast,
  shouldPollMatchState,
} from "./broadcastLifecycle";

describe("canonical match broadcast lifecycle", () => {
  test("a scheduled minute-zero payload stays pre-match and keeps polling", () => {
    const live = { status: "SCHEDULED", phase: "pre_match", minute: 0 };
    expect(canonicalBroadcastPhase(live)).toBe("pre_match");
    expect(isActiveCanonicalBroadcast("scheduled")).toBe(true);
    expect(shouldPollMatchState(live)).toBe(true);
  });

  test("kickoff, minute 15 and minute 30 stay live", () => {
    expect(canonicalBroadcastPhase({ status: "LIVE", phase: "first_half" })).toBe("first_half");
    expect(shouldPollMatchState({ status: "LIVE", phase: "first_half" })).toBe(true);
    expect(shouldPollMatchState({ status: "LIVE", phase: "second_half" })).toBe(true);
  });

  test("halftime is not full time and does not stop polling", () => {
    const live = { status: "HALFTIME", phase: "halftime" };
    expect(canonicalBroadcastPhase(live)).toBe("halftime");
    expect(shouldPollMatchState(live)).toBe(true);
  });

  test("a final precomputed frame phase does not finish a scheduled match", () => {
    expect(canonicalBroadcastPhase({ status: "SCHEDULED", phase: "full_time" })).toBe("pre_match");
    expect(shouldPollMatchState({ status: "SCHEDULED", phase: "completed" })).toBe(true);
  });

  test("full time is the only completed stop", () => {
    expect(canonicalBroadcastPhase({ status: "FT", phase: "full_time" })).toBe("full_time");
    expect(shouldPollMatchState({ status: "FT", phase: "full_time" })).toBe(false);
    expect(shouldPollMatchState(null)).toBe(true);
  });
});
