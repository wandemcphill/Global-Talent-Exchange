export type ClubLocationValidation =
  | { valid: true; countryCode: string; cityName: string }
  | { valid: false; error: string };

export function validateClubLocation(
  countryCode: string,
  cityName: string,
): ClubLocationValidation {
  const code = countryCode.trim().toUpperCase();
  const city = cityName.trim();

  if (!/^[A-Z]{2}$/.test(code)) {
    return {
      valid: false,
      error: "Enter a valid two-letter country code (for example NG).",
    };
  }
  if (city.length < 2) {
    return { valid: false, error: "Enter the club home city." };
  }

  return { valid: true, countryCode: code, cityName: city };
}
