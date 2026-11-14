import React, { act } from "react";
import { createRoot } from "react-dom/client";

import { buildTimelineModel, MatchTimelineScrubber, phaseLabel } from "./MatchTimelineScrubber";

describe("match timeline scrubber", () => {
  const frames = [
    { timeSeconds: 0, phase: "first_half" },
    { timeSeconds: 100, phase: "first_half" },
    { timeSeconds: 200, phase: "halftime" },
    { timeSeconds: 230, phase: "second_half" },
    { timeSeconds: 400, phase: "second_half" },
  ];

  test("phase segments come only from recorded frames and are labelled distinctly", () => {
    const model = buildTimelineModel(frames, [], 400);
    expect(model.segments.map((s) => s.label)).toEqual(["1st Half", "Half-Time", "2nd Half"]);
    expect(model.segments[0].endSeconds).toBe(200);
    expect(model.segments[2].endSeconds).toBe(400);
    expect(phaseLabel("first_half")).not.toBe(phaseLabel("halftime"));
  });

  test("no phases are invented when frames carry none", () => {
    expect(buildTimelineModel([{ timeSeconds: 0 }, { timeSeconds: 50 }], [], 50).segments).toEqual([]);
  });

  test("pins keep only supported event types, dedupe, and drop out-of-range events", () => {
    const model = buildTimelineModel(
      frames,
      [
        { event_id: "g1", type: "goal", time_seconds: 120, team: "home", player_name: "Nine" },
        { event_id: "g1", type: "goal", time_seconds: 120 },
        { event_id: "p1", type: "pass", time_seconds: 30 },
        { event_id: "y1", event_type: "yellow_card", minute: 3, side: "away" },
        { event_id: "late", type: "goal", time_seconds: 9999 },
      ],
      400,
    );
    expect(model.pins.map((p) => p.id)).toEqual(["g1", "y1"]);
    expect(model.pins[0].side).toBe("home");
  });

  test("clicking a pin or moving the range seeks; renders nothing without a duration", () => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    const onSeek = jest.fn();
    const model = buildTimelineModel(frames, [{ event_id: "g1", type: "goal", time_seconds: 120 }], 400);
    const host = document.createElement("div");
    document.body.appendChild(host);
    const root = createRoot(host);
    act(() => {
      root.render(<MatchTimelineScrubber model={model} currentSeconds={210} onSeek={onSeek} />);
    });
    expect(host.querySelector("[data-testid='match-timeline-phase']")?.textContent).toBe("Half-Time");

    act(() => {
      (host.querySelector("[data-testid='match-timeline-pin']") as HTMLButtonElement).click();
    });
    expect(onSeek).toHaveBeenLastCalledWith(114);

    const range = host.querySelector("[data-testid='match-timeline-range']") as HTMLInputElement;
    act(() => {
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;
      setter.call(range, "300");
      range.dispatchEvent(new Event("input", { bubbles: true }));
    });
    expect(onSeek).toHaveBeenLastCalledWith(300);

    act(() => {
      root.render(
        <MatchTimelineScrubber model={buildTimelineModel([], [], 0)} currentSeconds={0} onSeek={onSeek} />,
      );
    });
    expect(host.querySelector("[data-testid='match-timeline-scrubber']")).toBeNull();
    act(() => root.unmount());
    host.remove();
  });

  test("hovering a pin shows the rich event preview card and prev/next key buttons navigate between pins", () => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    const onSeek = jest.fn();
    const model = buildTimelineModel(
      frames,
      [
        { event_id: "g1", type: "goal", time_seconds: 60, team: "home", player_name: "Osimhen" },
        { event_id: "s1", type: "save", time_seconds: 240, team: "away", player_name: "Maignan" },
      ],
      400,
    );
    const host = document.createElement("div");
    document.body.appendChild(host);
    const root = createRoot(host);
    act(() => {
      root.render(<MatchTimelineScrubber model={model} currentSeconds={120} onSeek={onSeek} />);
    });

    const prevBtn = host.querySelector("[data-testid='timeline-prev-event']") as HTMLButtonElement;
    const nextBtn = host.querySelector("[data-testid='timeline-next-event']") as HTMLButtonElement;
    expect(prevBtn).not.toBeNull();
    expect(nextBtn).not.toBeNull();

    act(() => {
      prevBtn.click();
    });
    expect(onSeek).toHaveBeenLastCalledWith(54);

    act(() => {
      nextBtn.click();
    });
    expect(onSeek).toHaveBeenLastCalledWith(234);

    const firstPin = host.querySelector("[data-testid='match-timeline-pin']") as HTMLButtonElement;
    act(() => {
      firstPin.focus();
    });
    const preview = host.querySelector("[data-testid='timeline-pin-preview']");
    expect(preview).not.toBeNull();
    expect(preview?.textContent).toContain("Osimhen");

    act(() => root.unmount());
    host.remove();
  });
});