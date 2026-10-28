/**
 * Selectable club home locations.
 *
 * Values follow the existing `POST /clubs` contract: `country_code` is an
 * upper-case ISO 3166-1 alpha-2 code, `region_name` / `city_name` are trimmed
 * display names. Users may still type a city or region that is not listed, so
 * the catalog is a convenience for search/autofill, not an allow-list.
 */
export type CatalogCity = { city: string; region: string };
export type CatalogCountry = { code: string; name: string; cities: CatalogCity[] };

const c = (city: string, region: string): CatalogCity => ({ city, region });

export const CLUB_LOCATION_CATALOG: CatalogCountry[] = [
  { code: "AR", name: "Argentina", cities: [c("Buenos Aires", "Buenos Aires"), c("Córdoba", "Córdoba"), c("Rosario", "Santa Fe")] },
  { code: "AU", name: "Australia", cities: [c("Sydney", "New South Wales"), c("Melbourne", "Victoria"), c("Brisbane", "Queensland")] },
  { code: "BR", name: "Brazil", cities: [c("São Paulo", "São Paulo"), c("Rio de Janeiro", "Rio de Janeiro"), c("Salvador", "Bahia")] },
  { code: "CA", name: "Canada", cities: [c("Toronto", "Ontario"), c("Vancouver", "British Columbia"), c("Montreal", "Quebec")] },
  { code: "CM", name: "Cameroon", cities: [c("Douala", "Littoral"), c("Yaoundé", "Centre")] },
  { code: "CI", name: "Côte d'Ivoire", cities: [c("Abidjan", "Lagunes"), c("Bouaké", "Vallée du Bandama")] },
  { code: "DE", name: "Germany", cities: [c("Berlin", "Berlin"), c("Munich", "Bavaria"), c("Hamburg", "Hamburg")] },
  { code: "EG", name: "Egypt", cities: [c("Cairo", "Cairo"), c("Alexandria", "Alexandria")] },
  { code: "ES", name: "Spain", cities: [c("Madrid", "Community of Madrid"), c("Barcelona", "Catalonia"), c("Seville", "Andalusia")] },
  { code: "FR", name: "France", cities: [c("Paris", "Île-de-France"), c("Marseille", "Provence-Alpes-Côte d'Azur"), c("Lyon", "Auvergne-Rhône-Alpes")] },
  { code: "GB", name: "United Kingdom", cities: [c("London", "England"), c("Manchester", "England"), c("Glasgow", "Scotland"), c("Cardiff", "Wales")] },
  { code: "GH", name: "Ghana", cities: [c("Accra", "Greater Accra"), c("Kumasi", "Ashanti")] },
  { code: "IN", name: "India", cities: [c("Mumbai", "Maharashtra"), c("Delhi", "Delhi"), c("Kolkata", "West Bengal")] },
  { code: "IT", name: "Italy", cities: [c("Rome", "Lazio"), c("Milan", "Lombardy"), c("Naples", "Campania")] },
  { code: "JP", name: "Japan", cities: [c("Tokyo", "Tokyo"), c("Osaka", "Osaka"), c("Yokohama", "Kanagawa")] },
  { code: "KE", name: "Kenya", cities: [c("Nairobi", "Nairobi"), c("Mombasa", "Mombasa")] },
  { code: "MA", name: "Morocco", cities: [c("Casablanca", "Casablanca-Settat"), c("Rabat", "Rabat-Salé-Kénitra")] },
  { code: "MX", name: "Mexico", cities: [c("Mexico City", "Mexico City"), c("Guadalajara", "Jalisco"), c("Monterrey", "Nuevo León")] },
  { code: "NG", name: "Nigeria", cities: [c("Lagos", "Lagos"), c("Abuja", "FCT"), c("Port Harcourt", "Rivers"), c("Kano", "Kano")] },
  { code: "NL", name: "Netherlands", cities: [c("Amsterdam", "North Holland"), c("Rotterdam", "South Holland")] },
  { code: "PT", name: "Portugal", cities: [c("Lisbon", "Lisbon"), c("Porto", "Porto")] },
  { code: "SA", name: "Saudi Arabia", cities: [c("Riyadh", "Riyadh"), c("Jeddah", "Makkah")] },
  { code: "SN", name: "Senegal", cities: [c("Dakar", "Dakar"), c("Thiès", "Thiès")] },
  { code: "US", name: "United States", cities: [c("New York", "New York"), c("Los Angeles", "California"), c("Chicago", "Illinois"), c("Houston", "Texas")] },
  { code: "ZA", name: "South Africa", cities: [c("Johannesburg", "Gauteng"), c("Cape Town", "Western Cape"), c("Durban", "KwaZulu-Natal")] },
];

const fold = (s: string) =>
  s
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toLowerCase();

export function countryLabel(country: CatalogCountry): string {
  return `${country.name} (${country.code})`;
}

export function findCountry(code: string): CatalogCountry | undefined {
  const upper = code.trim().toUpperCase();
  return CLUB_LOCATION_CATALOG.find((x) => x.code === upper);
}

/**
 * Resolve free text typed into the searchable country box (a label such as
 * "Ghana (GH)", a name such as "ghana", or a bare alpha-2 code) to a code.
 * Returns "" when nothing matches so the form stays invalid.
 */
export function resolveCountryCode(input: string): string {
  const text = fold(input);
  if (!text) return "";
  const hit = CLUB_LOCATION_CATALOG.find(
    (x) => fold(countryLabel(x)) === text || fold(x.name) === text || x.code.toLowerCase() === text,
  );
  return hit ? hit.code : "";
}

export function citiesFor(code: string): CatalogCity[] {
  return findCountry(code)?.cities ?? [];
}

/** Region for a known city, or "" when the city is not in the catalog. */
export function regionForCity(code: string, city: string): string {
  const wanted = fold(city);
  return citiesFor(code).find((x) => fold(x.city) === wanted)?.region ?? "";
}

/** Canonical casing for a catalog city typed in any case; otherwise trimmed input. */
export function canonicalCity(code: string, city: string): string {
  const wanted = fold(city);
  return citiesFor(code).find((x) => fold(x.city) === wanted)?.city ?? city.trim();
}

/** Readable message for FastAPI 422 validation arrays and other server errors. */
export function clubCreateErrorMessage(e: any, fallback: (e: any) => string): string {
  const detail = e?.response?.data?.detail;
  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((d: any) => {
        const field = Array.isArray(d?.loc) ? String(d.loc[d.loc.length - 1]).replace(/_/g, " ") : "";
        const msg = typeof d?.msg === "string" ? d.msg : "is invalid";
        return field ? `${field}: ${msg}` : msg;
      })
      .join("; ");
  }
  return fallback(e);
}
