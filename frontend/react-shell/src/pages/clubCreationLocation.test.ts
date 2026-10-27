import { validateClubLocation } from "./clubCreationLocation";

describe("validateClubLocation", () => {
  test("normalizes a valid country code and trims the city", () => {
    expect(validateClubLocation(" ng ", " Lagos ")).toEqual({
      valid: true,
      countryCode: "NG",
      cityName: "Lagos",
    });
  });

  test("rejects a missing or malformed country code", () => {
    expect(validateClubLocation("", "Lagos")).toEqual({
      valid: false,
      error: "Enter a valid two-letter country code (for example NG).",
    });
    expect(validateClubLocation("NGA", "Lagos").valid).toBe(false);
    expect(validateClubLocation("N1", "Lagos").valid).toBe(false);
  });

  test("rejects a missing or too-short city", () => {
    expect(validateClubLocation("NG", "").valid).toBe(false);
    expect(validateClubLocation("NG", "L").valid).toBe(false);
  });
});
