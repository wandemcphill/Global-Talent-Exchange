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
});
