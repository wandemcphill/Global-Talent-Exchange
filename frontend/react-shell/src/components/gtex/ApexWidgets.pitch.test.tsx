import { placeFirstTeamOnPitch } from "./ApexWidgets";

describe("first-team pitch", () => {
  test("places real players by position and leaves a short sheet short", () => {
    const slots = placeFirstTeamOnPitch([
      { id: "gk", name: "Ada Keeper", position: "GK", rating: 80 },
      { id: "cb", name: "Ben Centre", position: "CB", rating: 77 },
    ]);

    const keeper = slots.find((slot) => slot.role === "GK");
    const centre = slots.find((slot) => slot.player?.id === "cb");
    const emptyForward = slots.find((slot) => slot.role === "ST");

    expect(keeper?.player?.name).toBe("Ada Keeper");
    expect(keeper?.shirt).toBe(1);
    expect(keeper?.ovr).toBe(80);
    expect(centre?.shirt).toBe(5);
    expect(emptyForward?.player).toBeUndefined();
    expect(emptyForward?.label).toBe("");
    expect(slots.filter((slot) => slot.player).map((slot) => slot.label)).toEqual([
      "Centre",
      "Keeper",
    ]);
  });

  test("draws a filed back five instead of falling back to 4-3-3", () => {
    const players = [
      { id: "gk", name: "Ada Keeper", position: "GK", rating: 80 },
      ...Array.from({ length: 10 }, (_, index) => ({
        id: `out-${index}`,
        name: `Out ${index}`,
        position: index < 5 ? "CM" : "ST",
        rating: 70,
      })),
    ];

    const slots = placeFirstTeamOnPitch(players, "5-4-1");

    expect(slots.filter((slot) => slot.bucket === "DEF" && slot.player)).toHaveLength(5);
    expect(slots.filter((slot) => slot.bucket === "MID" && slot.player)).toHaveLength(4);
    expect(slots.filter((slot) => slot.bucket === "FWD" && slot.player)).toHaveLength(1);
    expect(slots.find((slot) => slot.player?.id === "out-0")?.bucket).toBe("DEF");
    expect(slots.find((slot) => slot.player?.id === "out-9")?.bucket).toBe("FWD");
  });
});
