import { pitchSafeShirt } from "./MatchPitchLiveScene";

describe("pitchSafeShirt", () => {
  it("swaps a grass-green shirt for the secondary colour", () => {
    expect(pitchSafeShirt("#00E676", "#0F172A")).toEqual({ primary: "#0F172A", secondary: "#00E676" });
  });

  it("keeps non-green shirts as they are", () => {
    expect(pitchSafeShirt("#3B82F6", "#F8FAFC")).toEqual({ primary: "#3B82F6", secondary: "#F8FAFC" });
  });

  it("keeps green when the secondary is green too", () => {
    expect(pitchSafeShirt("#00E676", "#1B5E20").primary).toBe("#00E676");
  });
});
