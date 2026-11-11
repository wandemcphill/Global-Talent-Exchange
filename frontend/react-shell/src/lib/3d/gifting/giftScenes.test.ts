import { createGiftDirector, frameGiftShot } from "./giftScenes";
import { detectGiftQuality } from "./giftQuality";

describe("gifting 2.0 scenes", () => {
  const quality = detectGiftQuality(1440, 8);

  function stage(shot: string, giftCode: string) {
    return createGiftDirector({
      shot,
      giftCode,
      quality,
      canStream: false,
      resolveUrl: (path) => path,
      isCancelled: () => false,
      onReady: () => undefined,
    });
  }

  test("paris is a lattice tower and the eight shots do not share one camera", () => {
    const paris = stage("city", "paris_skyline");
    expect(paris.root.getObjectByName("eiffel-lattice")).toBeTruthy();
    paris.dispose();

    const parisStart = frameGiftShot("city", 0);
    const parisEnd = frameGiftShot("city", 1);
    expect(parisEnd.position[2]).toBeGreaterThan(parisStart.position[2]);

    const bicycle = frameGiftShot("bicycle", 0.4);
    const winner = frameGiftShot("last_minute", 0.4);
    expect(bicycle.position[0]).not.toBeCloseTo(winner.position[0], 0);
    expect(frameGiftShot("stadium", 0, [0, 0, 0], "golden_stadium").position[1]).toBeGreaterThan(
      frameGiftShot("stadium", 0, [0, 0, 0], "maracana_stadium").position[1]
    );
  });

  test("bicycle and last-minute winner are different stories", () => {
    const kick = stage("bicycle", "bicycle_kick");
    const winner = stage("last_minute", "last_minute_winner");
    expect(kick.root.getObjectByName("bicycle-pitch")).toBeTruthy();
    expect(kick.root.getObjectByName("winner-clock")).toBeFalsy();
    expect(winner.root.getObjectByName("winner-clock")).toBeTruthy();
    expect(winner.root.getObjectByName("match-goal")).toBeTruthy();
    kick.dispose();
    winner.dispose();
  });

  test("ballon d'or is a trophy stage with a ball, and the jet has a runway", () => {
    const trophy = stage("trophy", "ballon_dor");
    const jet = stage("jet", "private_jet");
    const yacht = stage("yacht", "superyacht");
    expect(trophy.root.getObjectByName("ballon-dor-ball")).toBeTruthy();
    expect(trophy.root.getObjectByName("ballon-dor-stage")).toBeTruthy();
    expect(jet.root.getObjectByName("runway")).toBeTruthy();
    expect(yacht.root.getObjectByName("ocean")).toBeTruthy();
    trophy.dispose();
    jet.dispose();
    yacht.dispose();
  });
});
