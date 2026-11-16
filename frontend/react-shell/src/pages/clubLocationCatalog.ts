/**
 * Selectable country, region/state and city values for club registration.
 * The catalogue is intentionally curated around major football markets and
 * metropolitan centres; all values map to the API's ISO-2 country code and
 * display-name location fields. Users select each value instead of typing it.
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
  { code: "NG", name: "Nigeria", cities: [
    c("Abakaliki", "Ebonyi"), c("Abeokuta", "Ogun"), c("Ado-Ekiti", "Ekiti"), c("Akure", "Ondo"),
    c("Asaba", "Delta"), c("Awka", "Anambra"), c("Bauchi", "Bauchi"), c("Bayelsa", "Bayelsa"),
    c("Benin City", "Edo"), c("Birnin Kebbi", "Kebbi"), c("Calabar", "Cross River"), c("Damaturu", "Yobe"),
    c("Dutse", "Jigawa"), c("Enugu", "Enugu"), c("Gombe", "Gombe"), c("Gusau", "Zamfara"),
    c("Ibadan", "Oyo"), c("Ikorodu", "Lagos"), c("Ikeja", "Lagos"), c("Ilorin", "Kwara"),
    c("Jalingo", "Taraba"), c("Jos", "Plateau"), c("Kaduna", "Kaduna"), c("Kano", "Kano"),
    c("Katsina", "Katsina"), c("Lafia", "Nasarawa"), c("Lagos", "Lagos"), c("Lokoja", "Kogi"),
    c("Makurdi", "Benue"), c("Maiduguri", "Borno"), c("Minna", "Niger"), c("Ogbomoso", "Oyo"),
    c("Onitsha", "Anambra"), c("Osogbo", "Osun"), c("Owerri", "Imo"), c("Port Harcourt", "Rivers"),
    c("Sokoto", "Sokoto"), c("Umuahia", "Abia"), c("Uyo", "Akwa Ibom"), c("Warri", "Delta"),
    c("Yenagoa", "Bayelsa"), c("Yola", "Adamawa"), c("Abuja", "FCT"), c("Gwagwalada", "FCT"),
  ] },
  { code: "NL", name: "Netherlands", cities: [c("Amsterdam", "North Holland"), c("Rotterdam", "South Holland")] },
  { code: "PT", name: "Portugal", cities: [c("Lisbon", "Lisbon"), c("Porto", "Porto")] },
  { code: "SA", name: "Saudi Arabia", cities: [c("Riyadh", "Riyadh"), c("Jeddah", "Makkah")] },
  { code: "SN", name: "Senegal", cities: [c("Dakar", "Dakar"), c("Thiès", "Thiès")] },
  { code: "US", name: "United States", cities: [c("New York", "New York"), c("Los Angeles", "California"), c("Chicago", "Illinois"), c("Houston", "Texas")] },
  { code: "ZA", name: "South Africa", cities: [c("Johannesburg", "Gauteng"), c("Cape Town", "Western Cape"), c("Durban", "KwaZulu-Natal")] },

  { code: "AO", name: "Angola", cities: [c("Luanda", "Luanda"), c("Huambo", "Huambo"), c("Benguela", "Benguela"), c("Lobito", "Benguela")] },
  { code: "DZ", name: "Algeria", cities: [c("Algiers", "Algiers"), c("Oran", "Oran"), c("Constantine", "Constantine"), c("Annaba", "Annaba")] },
  { code: "AT", name: "Austria", cities: [c("Vienna", "Vienna"), c("Graz", "Styria"), c("Linz", "Upper Austria"), c("Salzburg", "Salzburg")] },
  { code: "BE", name: "Belgium", cities: [c("Brussels", "Brussels"), c("Antwerp", "Flanders"), c("Bruges", "Flanders"), c("Ghent", "Flanders")] },
  { code: "BJ", name: "Benin", cities: [c("Cotonou", "Littoral"), c("Porto-Novo", "Ouémé"), c("Parakou", "Borgou")] },
  { code: "BF", name: "Burkina Faso", cities: [c("Ouagadougou", "Centre"), c("Bobo-Dioulasso", "Hauts-Bassins")] },
  { code: "BG", name: "Bulgaria", cities: [c("Sofia", "Sofia City"), c("Plovdiv", "Plovdiv"), c("Varna", "Varna")] },
  { code: "BI", name: "Burundi", cities: [c("Gitega", "Gitega"), c("Bujumbura", "Bujumbura Mairie")] },
  { code: "BW", name: "Botswana", cities: [c("Gaborone", "South-East"), c("Francistown", "North-East")] },
  { code: "CD", name: "Democratic Republic of the Congo", cities: [c("Kinshasa", "Kinshasa"), c("Lubumbashi", "Haut-Katanga"), c("Mbuji-Mayi", "Kasaï-Oriental"), c("Goma", "North Kivu")] },
  { code: "CG", name: "Republic of the Congo", cities: [c("Brazzaville", "Brazzaville"), c("Pointe-Noire", "Pointe-Noire")] },
  { code: "CL", name: "Chile", cities: [c("Santiago", "Santiago Metropolitan"), c("Valparaíso", "Valparaíso"), c("Concepción", "Biobío")] },
  { code: "CN", name: "China", cities: [c("Beijing", "Beijing"), c("Shanghai", "Shanghai"), c("Guangzhou", "Guangdong"), c("Shenzhen", "Guangdong")] },
  { code: "CO", name: "Colombia", cities: [c("Bogotá", "Bogotá D.C."), c("Medellín", "Antioquia"), c("Cali", "Valle del Cauca"), c("Barranquilla", "Atlántico")] },
  { code: "CR", name: "Costa Rica", cities: [c("San José", "San José"), c("Alajuela", "Alajuela")] },
  { code: "HR", name: "Croatia", cities: [c("Zagreb", "City of Zagreb"), c("Split", "Split-Dalmatia"), c("Rijeka", "Primorje-Gorski Kotar")] },
  { code: "CZ", name: "Czechia", cities: [c("Prague", "Prague"), c("Brno", "South Moravian"), c("Ostrava", "Moravian-Silesian")] },
  { code: "DK", name: "Denmark", cities: [c("Copenhagen", "Capital Region"), c("Aarhus", "Central Denmark"), c("Odense", "Southern Denmark")] },
  { code: "DO", name: "Dominican Republic", cities: [c("Santo Domingo", "National District"), c("Santiago de los Caballeros", "Santiago")] },
  { code: "EC", name: "Ecuador", cities: [c("Quito", "Pichincha"), c("Guayaquil", "Guayas"), c("Cuenca", "Azuay")] },
  { code: "ET", name: "Ethiopia", cities: [c("Addis Ababa", "Addis Ababa"), c("Dire Dawa", "Dire Dawa")] },
  { code: "FI", name: "Finland", cities: [c("Helsinki", "Uusimaa"), c("Tampere", "Pirkanmaa"), c("Turku", "Southwest Finland")] },
  { code: "GA", name: "Gabon", cities: [c("Libreville", "Estuaire"), c("Port-Gentil", "Ogooué-Maritime")] },
  { code: "GM", name: "The Gambia", cities: [c("Banjul", "Banjul"), c("Serekunda", "Kanifing")] },
  { code: "GN", name: "Guinea", cities: [c("Conakry", "Conakry"), c("Nzérékoré", "Nzérékoré")] },
  { code: "GR", name: "Greece", cities: [c("Athens", "Attica"), c("Thessaloniki", "Central Macedonia"), c("Patras", "Western Greece")] },
  { code: "HU", name: "Hungary", cities: [c("Budapest", "Budapest"), c("Debrecen", "Hajdú-Bihar")] },
  { code: "ID", name: "Indonesia", cities: [c("Jakarta", "Jakarta"), c("Surabaya", "East Java"), c("Bandung", "West Java"), c("Medan", "North Sumatra")] },
  { code: "IE", name: "Ireland", cities: [c("Dublin", "Leinster"), c("Cork", "Munster"), c("Galway", "Connacht"), c("Limerick", "Munster")] },
  { code: "IR", name: "Iran", cities: [c("Tehran", "Tehran"), c("Isfahan", "Isfahan"), c("Tabriz", "East Azerbaijan"), c("Shiraz", "Fars")] },
  { code: "IQ", name: "Iraq", cities: [c("Baghdad", "Baghdad"), c("Basra", "Basra")] },
  { code: "IL", name: "Israel", cities: [c("Jerusalem", "Jerusalem"), c("Tel Aviv", "Tel Aviv"), c("Haifa", "Haifa")] },
  { code: "JM", name: "Jamaica", cities: [c("Kingston", "Surrey"), c("Montego Bay", "Cornwall")] },
  { code: "JO", name: "Jordan", cities: [c("Amman", "Amman"), c("Zarqa", "Zarqa")] },
  { code: "KW", name: "Kuwait", cities: [c("Kuwait City", "Al Asimah"), c("Al Ahmadi", "Ahmadi")] },
  { code: "LB", name: "Lebanon", cities: [c("Beirut", "Beirut"), c("Tripoli", "North")] },
  { code: "LY", name: "Libya", cities: [c("Tripoli", "Tripoli"), c("Benghazi", "Benghazi")] },
  { code: "ML", name: "Mali", cities: [c("Bamako", "Bamako"), c("Sikasso", "Sikasso")] },
  { code: "MZ", name: "Mozambique", cities: [c("Maputo", "Maputo City"), c("Beira", "Sofala")] },
  { code: "NA", name: "Namibia", cities: [c("Windhoek", "Khomas"), c("Walvis Bay", "Erongo")] },
  { code: "NE", name: "Niger", cities: [c("Niamey", "Niamey"), c("Zinder", "Zinder")] },
  { code: "NO", name: "Norway", cities: [c("Oslo", "Oslo"), c("Bergen", "Vestland"), c("Trondheim", "Trøndelag")] },
  { code: "NZ", name: "New Zealand", cities: [c("Auckland", "Auckland"), c("Wellington", "Wellington"), c("Christchurch", "Canterbury")] },
  { code: "OM", name: "Oman", cities: [c("Muscat", "Muscat"), c("Salalah", "Dhofar")] },
  { code: "PE", name: "Peru", cities: [c("Lima", "Lima"), c("Arequipa", "Arequipa"), c("Cusco", "Cusco")] },
  { code: "PH", name: "Philippines", cities: [c("Manila", "Metro Manila"), c("Cebu City", "Central Visayas"), c("Davao City", "Davao Region")] },
  { code: "PK", name: "Pakistan", cities: [c("Karachi", "Sindh"), c("Lahore", "Punjab"), c("Islamabad", "Islamabad Capital Territory"), c("Peshawar", "Khyber Pakhtunkhwa")] },
  { code: "PL", name: "Poland", cities: [c("Warsaw", "Masovian"), c("Kraków", "Lesser Poland"), c("Gdańsk", "Pomeranian"), c("Poznań", "Greater Poland")] },
  { code: "QA", name: "Qatar", cities: [c("Doha", "Doha"), c("Al Rayyan", "Al Rayyan")] },
  { code: "RO", name: "Romania", cities: [c("Bucharest", "Bucharest"), c("Cluj-Napoca", "Cluj"), c("Timișoara", "Timiș")] },
  { code: "RS", name: "Serbia", cities: [c("Belgrade", "Belgrade"), c("Novi Sad", "Vojvodina"), c("Niš", "Nišava")] },
  { code: "RU", name: "Russia", cities: [c("Moscow", "Moscow"), c("Saint Petersburg", "Saint Petersburg"), c("Kazan", "Tatarstan")] },
  { code: "RW", name: "Rwanda", cities: [c("Kigali", "Kigali"), c("Huye", "Southern Province")] },
  { code: "SG", name: "Singapore", cities: [c("Singapore", "Central Region")] },
  { code: "SI", name: "Slovenia", cities: [c("Ljubljana", "Central Slovenia"), c("Maribor", "Drava")] },
  { code: "SK", name: "Slovakia", cities: [c("Bratislava", "Bratislava"), c("Košice", "Košice")] },
  { code: "KR", name: "South Korea", cities: [c("Seoul", "Seoul"), c("Busan", "Busan"), c("Daegu", "Daegu")] },
  { code: "SD", name: "Sudan", cities: [c("Khartoum", "Khartoum"), c("Omdurman", "Khartoum")] },
  { code: "SS", name: "South Sudan", cities: [c("Juba", "Central Equatoria"), c("Wau", "Western Bahr el Ghazal")] },
  { code: "SE", name: "Sweden", cities: [c("Stockholm", "Stockholm"), c("Gothenburg", "Västra Götaland"), c("Malmö", "Skåne")] },
  { code: "CH", name: "Switzerland", cities: [c("Zurich", "Zurich"), c("Geneva", "Geneva"), c("Basel", "Basel-Stadt")] },
  { code: "TH", name: "Thailand", cities: [c("Bangkok", "Bangkok"), c("Chiang Mai", "Chiang Mai"), c("Phuket", "Phuket")] },
  { code: "TG", name: "Togo", cities: [c("Lomé", "Maritime"), c("Sokodé", "Centrale")] },
  { code: "TN", name: "Tunisia", cities: [c("Tunis", "Tunis"), c("Sfax", "Sfax"), c("Sousse", "Sousse")] },
  { code: "TZ", name: "Tanzania", cities: [c("Dar es Salaam", "Dar es Salaam"), c("Dodoma", "Dodoma"), c("Zanzibar City", "Zanzibar Urban/West")] },
  { code: "TR", name: "Türkiye", cities: [c("Istanbul", "Istanbul"), c("Ankara", "Ankara"), c("Izmir", "Izmir"), c("Bursa", "Bursa")] },
  { code: "UA", name: "Ukraine", cities: [c("Kyiv", "Kyiv City"), c("Lviv", "Lviv Oblast"), c("Odesa", "Odesa Oblast")] },
  { code: "AE", name: "United Arab Emirates", cities: [c("Dubai", "Dubai"), c("Abu Dhabi", "Abu Dhabi"), c("Sharjah", "Sharjah")] },
  { code: "UY", name: "Uruguay", cities: [c("Montevideo", "Montevideo"), c("Salto", "Salto")] },
  { code: "UZ", name: "Uzbekistan", cities: [c("Tashkent", "Tashkent"), c("Samarkand", "Samarkand")] },
  { code: "UG", name: "Uganda", cities: [c("Kampala", "Central Region"), c("Entebbe", "Central Region"), c("Gulu", "Northern Region")] },
  { code: "VE", name: "Venezuela", cities: [c("Caracas", "Capital District"), c("Maracaibo", "Zulia")] },
  { code: "VN", name: "Vietnam", cities: [c("Hanoi", "Hanoi"), c("Ho Chi Minh City", "Ho Chi Minh City"), c("Da Nang", "Da Nang")] },
  { code: "ZM", name: "Zambia", cities: [c("Lusaka", "Lusaka"), c("Ndola", "Copperbelt")] },
  { code: "ZW", name: "Zimbabwe", cities: [c("Harare", "Harare"), c("Bulawayo", "Bulawayo")] },

];


export type CatalogRegion = { code: string; name: string };
export type CatalogLocationCity = { city: string; region: string; regionCode: string };

const CSC_DATA_BASE =
  "https://cdn.jsdelivr.net/npm/@countrystatecity/countries-browser@3.0.1/dist/data";
const locationDataCache = new Map<string, Promise<any>>();

async function loadLocationJson<T>(path: string): Promise<T> {
  const cached = locationDataCache.get(path);
  if (cached) return cached as Promise<T>;

  const request = fetch(`${CSC_DATA_BASE}/${path}`, {
    headers: { Accept: "application/json" },
  })
    .then(async (response) => {
      if (!response.ok) throw new Error(`Location data request failed: ${response.status}`);
      return response.json();
    })
    .catch((error) => {
      locationDataCache.delete(path);
      throw error;
    });

  locationDataCache.set(path, request);
  return request as Promise<T>;
}

/** Complete country list, fetched once and cached by the CDN-backed dataset. */
export async function loadAllCountries(): Promise<CatalogCountry[]> {
  const countries = await loadLocationJson<Array<{ name: string; iso2: string }>>("countries.json");
  return countries
    .filter((country) => country.iso2 && country.name)
    .map((country) => ({ code: country.iso2.toUpperCase(), name: country.name, cities: [] }))
    .sort((a, b) => a.name.localeCompare(b.name));
}

/** All first-level regions/states for one ISO-2 country code. */
export async function loadCountryRegions(countryCode: string): Promise<CatalogRegion[]> {
  const states = await loadLocationJson<Array<{ name: string; iso2: string }>>(
    `states/${countryCode.toUpperCase()}.json`,
  );
  return states
    .filter((state) => state.name && state.iso2)
    .map((state) => ({ code: state.iso2, name: state.name }))
    .sort((a, b) => a.name.localeCompare(b.name));
}

/** Cities for the selected country and first-level state/region. */
export async function loadRegionCities(
  countryCode: string,
  regionCode: string,
  regionName: string,
): Promise<CatalogLocationCity[]> {
  const cities = await loadLocationJson<Array<{ name: string; state_code: string | null }>>(
    `cities/${countryCode.toUpperCase()}-${regionCode.toUpperCase()}.json`,
  );
  return cities
    .filter((city) => city.name)
    .map((city) => ({
      city: city.name,
      region: regionName,
      regionCode,
    }))
    .sort((a, b) => a.city.localeCompare(b.city));
}

/** Resolve the current dropdown label, including countries outside the fallback catalogue. */
export function countryCodeFromLabel(input: string): string {
  const known = resolveCountryCode(input);
  if (known) return known;
  const match = /\\(([a-z]{2})\\)$/i.exec(input.trim());
  return match?.[1]?.toUpperCase() || "";
}

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

/** Unique region/state options for a selected country. */
export function regionsFor(code: string): string[] {
  return Array.from(new Set(citiesFor(code).map((item) => item.region))).sort((a, b) => a.localeCompare(b));
}

/** City options can be narrowed to a selected region/state. */
export function citiesForRegion(code: string, region: string): CatalogCity[] {
  const cities = citiesFor(code);
  return region ? cities.filter((item) => item.region === region) : cities;
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
