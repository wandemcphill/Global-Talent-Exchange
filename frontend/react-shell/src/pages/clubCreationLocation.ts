import { canonicalCity } from "./clubLocationCatalog";

export type ClubLocationValidation =
  | { valid: true; countryCode: string; regionName: string; cityName: string }
  | { valid: false; error: string };

export function validateClubLocation(
  countryCode: string,
  cityName: string,
  regionName: string,
): ClubLocationValidation {
  const code = countryCode.trim().toUpperCase();
  const region = regionName.trim().replace(/\s+/g, " ");
  const city = cityName.trim().replace(/\s+/g, " ");

  if (!/^[A-Z]{2}$/.test(code)) {
    return {
      valid: false,
      error: "Select the club's country.",
    };
  }
  if (city.length < 2) {
    return { valid: false, error: "Enter the club home city." };
  }
  if (region.length < 2) {
    return { valid: false, error: "Enter the club's region or state." };
  }
  if (city.length > 120 || region.length > 120) {
    return { valid: false, error: "City and region must be 120 characters or fewer." };
  }

  return { valid: true, countryCode: code, regionName: region, cityName: canonicalCity(code, city) };
}
