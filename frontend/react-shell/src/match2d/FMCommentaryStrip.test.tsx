import React, { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { FMCommentaryStrip, resolveCommentaryPhase } from "./FMCommentaryStrip";

describe("FMCommentaryStrip", () => {
  let host: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    host = document.createElement("div");
    document.body.appendChild(host);
    root = createRoot(host);
  });

  afterEach(() => {
    act(() => root.unmount());
    host.remove();
  });

  test("resolves match phases cleanly across neutral, chance, goal, cards, VAR, and subs", () => {
    expect(resolveCommentaryPhase({ kind: "pass" })).toBe("neutral");
    expect(resolveCommentaryPhase({ kind: "shot", shotXg: 0.42 })).toBe("chance");
    expect(resolveCommentaryPhase({ kind: "goal" })).toBe("goal");
    expect(resolveCommentaryPhase({ kind: "yellow_card" })).toBe("card_yellow");
    expect(resolveCommentaryPhase({ kind: "red_card" })).toBe("card_red");
    expect(resolveCommentaryPhase({ kind: "var" })).toBe("var");
    expect(resolveCommentaryPhase({ kind: "substitution" })).toBe("sub");
  });

  test("renders neutral buildup, big chance xG pill, goal club-color banner, and card/VAR/sub badges", () => {
    act(() => {
      root.render(
        <FMCommentaryStrip
          phase="neutral"
          badge="OPEN PLAY"
          headline="Bellingham switches it wide to Saka..."
          minuteLabel="34'"
          scoreline="0 - 0"
        />,
      );
    });
    const strip = host.querySelector("[data-testid='pitch-broadcast-banner']");
    expect(strip?.getAttribute("data-commentary-phase")).toBe("neutral");
    expect(strip?.textContent).toContain("Bellingham switches it wide to Saka...");
    expect(host.querySelector("[data-testid='live-shot-xg-pill']")).toBeNull();

    // Big chance with live shot xG pill
    act(() => {
      root.render(
        <FMCommentaryStrip
          phase="chance"
          badge="BIG CHANCE"
          headline="Saka cuts inside and fires towards the far post!"
          shotXg={0.42}
          minuteLabel="36'"
          scoreline="0 - 0"
        />,
      );
    });
    expect(host.querySelector("[data-testid='live-shot-xg-pill']")?.textContent).toBe("0.42 xG");

    // Goal flash banner with scorer, assist, minute, and score tick-up
    act(() => {
      root.render(
        <FMCommentaryStrip
          phase="goal"
          badge="GOAL"
          headline="Clinical finish into the bottom corner!"
          scorerName="Bukayo Saka"
          assistName="Jude Bellingham"
          clubColor="#dc2626"
          minuteLabel="37'"
          scoreline="1 - 0"
        />,
      );
    });
    expect(strip?.getAttribute("data-commentary-phase")).toBe("goal");
    expect(strip?.textContent).toContain("Bukayo Saka");
    expect(host.querySelector("[data-testid='goal-assist-pill']")?.textContent).toContain("Jude Bellingham");
    expect(host.querySelector("[data-testid='commentary-score-tick']")?.textContent).toBe("1 - 0");

    // Card / VAR / Sub slide-in badge
    act(() => {
      root.render(
        <FMCommentaryStrip
          phase="var"
          badge="VAR CHECK"
          headline="Checking possible offside in the build-up"
          minuteLabel="38'"
          scoreline="1 - 0"
        />,
      );
    });
    expect(strip?.getAttribute("data-commentary-phase")).toBe("var");
    expect(strip?.textContent).toContain("VAR CHECK");

    act(() => {
      root.render(
        <FMCommentaryStrip
          variant="classic"
          phase="neutral"
          badge="PLAY-BY-PLAY"
          headline="Hutchinson searches out Rebic to his left"
        />,
      );
    });
    expect(strip?.getAttribute("data-commentary-variant")).toBe("classic");
    expect(strip?.textContent).toBe("Hutchinson searches out Rebic to his left");
  });
});
