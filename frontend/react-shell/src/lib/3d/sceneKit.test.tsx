import { paintIdentityBoard } from "./sceneKit";
import { ClubTakeoverScene } from "./scenes/PresentationStage";
import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { QUALITY_PROFILES } from "./GtexSceneRegistry";

describe("presentation identity", () => {
  test("paints the live club name onto the jumbotron canvas", () => {
    const canvas = paintIdentityBoard({
      clubName: "Harbour Athletic",
      headline: "THE CLUB IS YOURS",
      primary: "#0f766e",
    });
    expect(canvas.getAttribute("data-club-name")).toBe("Harbour Athletic");
    expect(canvas.width).toBe(1024);
  });

  test("club takeover scene carries the club name without starting WebGL in jsdom", async () => {
    (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
    const container = document.createElement("div");
    document.body.appendChild(container);
    const root: Root = createRoot(container);
    await act(async () => {
      root.render(
        <ClubTakeoverScene
          sceneId="club_takeover"
          qualityTier="high"
          activeQuality={QUALITY_PROFILES.high}
          clubName="Harbour Athletic"
        />
      );
    });
    const stage = container.querySelector('[data-testid="club-takeover-scene"]');
    expect(stage?.getAttribute("data-club-name")).toBe("Harbour Athletic");
    expect(stage?.getAttribute("data-scene-kind")).toBe("takeover");
    await act(async () => {
      root.unmount();
    });
    container.remove();
  });
});
