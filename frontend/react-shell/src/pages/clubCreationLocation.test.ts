import { validateClubLocation } from "./clubCreationLocation";
import { regionForCity, resolveCountryCode } from "./clubLocationCatalog";

describe("validateClubLocation", () => {
  it("normalizes country, region and city for the club request", () => {
    expect(validateClubLocation(" ng ", " lagos ", " Lagos ")).toEqual({
      valid: true,
      countryCode: "NG",
      regionName: "Lagos",
      cityName: "Lagos",
    });
  });

  it("normalizes a different country/city combination", () => {
    expect(validateClubLocation("gh", "kumasi", "Ashanti")).toEqual({
      valid: true,
      countryCode: "GH",
      regionName: "Ashanti",
      cityName: "Kumasi",
    });
  });

  it("requires a country", () => {
    expect(validateClubLocation("", "Lagos", "Lagos")).toEqual({
      valid: false,
      error: "Select the club's country.",
    });
  });

  it("rejects malformed country codes", () => {
    expect(validateClubLocation("NGA", "Lagos", "Lagos").valid).toBe(false);
    expect(validateClubLocation("N1", "Lagos", "Lagos").valid).toBe(false);
  });

  it("rejects a missing or too-short city or region", () => {
    expect(validateClubLocation("NG", "", "Lagos").valid).toBe(false);
    expect(validateClubLocation("NG", "L", "Lagos").valid).toBe(false);
    expect(validateClubLocation("NG", "Lagos", "").valid).toBe(false);
  });
});

describe("club location catalog", () => {
  it("resolves labels, names and codes to alpha-2 codes", () => {
    expect(resolveCountryCode("Ghana (GH)")).toBe("GH");
    expect(resolveCountryCode("cote d'ivoire")).toBe("CI");
    expect(resolveCountryCode("br")).toBe("BR");
    expect(resolveCountryCode("Atlantis")).toBe("");
  });

  it("maps known cities to their region", () => {
    expect(regionForCity("US", "houston")).toBe("Texas");
    expect(regionForCity("US", "Nowhere")).toBe("");
  });
});
