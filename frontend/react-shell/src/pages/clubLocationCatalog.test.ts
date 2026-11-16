declare const describe: any;
declare const test: any;
declare const expect: any;
declare const beforeEach: any;
declare const afterEach: any;

import {
  countryCodeFromLabel,
  loadAllCountries,
  loadCountryRegions,
  loadRegionCities,
} from "./clubLocationCatalog";

describe("global club location catalogue", () => {
  let originalFetch: typeof fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  test("resolves ISO-2 codes for countries outside the bundled fallback list", () => {
    expect(countryCodeFromLabel("Aland Islands (AX)")).toBe("AX");
    expect(countryCodeFromLabel("South Korea (KR)")).toBe("KR");
    expect(countryCodeFromLabel("Not a country")).toBe("");
  });

  test("loads the complete country list from the pinned public dataset", async () => {
    globalThis.fetch = (async (input: RequestInfo | URL) => {
      expect(String(input)).toContain("/data/countries.json");
      return {
        ok: true,
        json: async () => [
          { name: "Zeta", iso2: "ZZ" },
          { name: "Alpha", iso2: "AA" },
        ],
      } as Response;
    }) as typeof fetch;

    const countries = await loadAllCountries();
    expect(countries.map((country) => country.code)).toEqual(["AA", "ZZ"]);
  });

  test("loads state options and only the selected state's city list", async () => {
    const requested: string[] = [];
    globalThis.fetch = (async (input: RequestInfo | URL) => {
      const url = String(input);
      requested.push(url);
      if (url.endsWith("/states/XZ.json")) {
        return {
          ok: true,
          json: async () => [{ name: "North Province", iso2: "NP" }],
        } as Response;
      }
      if (url.endsWith("/cities/XZ-NP.json")) {
        return {
          ok: true,
          json: async () => [
            { name: "North City", state_code: "NP" },
            { name: "River Town", state_code: "NP" },
          ],
        } as Response;
      }
      throw new Error(`Unexpected location-data URL: ${url}`);
    }) as typeof fetch;

    const regions = await loadCountryRegions("XZ");
    expect(regions).toEqual([{ code: "NP", name: "North Province" }]);

    const cities = await loadRegionCities("XZ", "NP", "North Province");
    expect(cities.map((city) => city.city)).toEqual(["North City", "River Town"]);
    expect(cities.every((city) => city.region === "North Province" && city.regionCode === "NP")).toBe(true);
    expect(requested).toHaveLength(2);
  });
});
