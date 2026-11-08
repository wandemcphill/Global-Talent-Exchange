import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { hasFullTimeEvent, useMatchFullTimeGovernance } from "./useMatchFullTimeGovernance";

const mockPost = jest.fn();
let mockToken: string | null = "token";

jest.mock("@/lib/api", () => ({
  api: { post: (...args: unknown[]) => mockPost(...args) },
  tokens: { get: () => mockToken },
}));

type Ev = { event_type: string };

function Harness({
  matchId,
  events,
  enabled = true,
  isFullTime,
  onGovernanceSettled,
}: {
  matchId?: string;
  events?: Ev[];
  enabled?: boolean;
  isFullTime?: boolean;
  onGovernanceSettled?: () => void;
}) {
  useMatchFullTimeGovernance(matchId, events, enabled, isFullTime, onGovernanceSettled);
  return null;
}

describe("useMatchFullTimeGovernance", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeAll(() => {
    (globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  });

  beforeEach(() => {
    jest.useFakeTimers();
    mockPost.mockReset();
    mockToken = "token";
    container = document.createElement("div");
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    jest.useRealTimers();
  });

  const render = async (props: Parameters<typeof Harness>[0]) => {
    await act(async () => {
      root.render(<Harness {...props} />);
    });
  };

  it("detects full-time events in either spelling", () => {
    expect(hasFullTimeEvent([{ event_type: "goal" }])).toBe(false);
    expect(hasFullTimeEvent([{ event_type: "FULL_TIME" }])).toBe(true);
    expect(hasFullTimeEvent([{ event_type: "fulltime" }])).toBe(true);
    expect(hasFullTimeEvent(undefined)).toBe(false);
  });

  it("does nothing before full time, when signed out, or when disabled", async () => {
    await render({ matchId: "m1", events: [{ event_type: "goal" }] });
    mockToken = null;
    await render({ matchId: "m1", events: [{ event_type: "full_time" }] });
    mockToken = "token";
    await render({ matchId: "m1", events: [{ event_type: "full_time" }], enabled: false });
    expect(mockPost).not.toHaveBeenCalled();
  });

  it("posts exactly once on full time even when events re-render", async () => {
    mockPost.mockResolvedValue({ data: { results: [] } });
    await render({ matchId: "m1", events: [{ event_type: "full_time" }] });
    await render({ matchId: "m1", events: [{ event_type: "full_time" }, { event_type: "goal" }] });
    expect(mockPost).toHaveBeenCalledTimes(1);
    expect(mockPost).toHaveBeenCalledWith("/owner/matches/m1/full-time-governance");
  });

  it("triggers on isFullTime flag and invokes onGovernanceSettled on success", async () => {
    mockPost.mockResolvedValue({ data: { results: [] } });
    const onSettled = jest.fn();
    await render({ matchId: "m-flag", events: [], isFullTime: true, onGovernanceSettled: onSettled });
    expect(mockPost).toHaveBeenCalledTimes(1);
    expect(mockPost).toHaveBeenCalledWith("/owner/matches/m-flag/full-time-governance");
    await act(async () => {
      jest.advanceTimersByTime(10);
    });
    expect(onSettled).toHaveBeenCalledTimes(1);
  });

  it("retries a bounded number of times while the canonical match is not yet complete (409)", async () => {
    mockPost.mockRejectedValue({ response: { status: 409 } });
    await render({ matchId: "m2", events: [{ event_type: "full_time" }] });
    expect(mockPost).toHaveBeenCalledTimes(1);
    await act(async () => {
      jest.advanceTimersByTime(4000);
    });
    expect(mockPost).toHaveBeenCalledTimes(2);
    await act(async () => {
      jest.advanceTimersByTime(4000);
    });
    expect(mockPost).toHaveBeenCalledTimes(3);
    await act(async () => {
      jest.advanceTimersByTime(20000);
    });
    expect(mockPost).toHaveBeenCalledTimes(3);
  });

  it("does not retry on terminal errors", async () => {
    mockPost.mockRejectedValue({ response: { status: 403 } });
    await render({ matchId: "m3", events: [{ event_type: "full_time" }] });
    await act(async () => {
      jest.advanceTimersByTime(20000);
    });
    expect(mockPost).toHaveBeenCalledTimes(1);
  });
});
