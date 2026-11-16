import React, { useEffect, useState } from "react";
import {
  CLUB_LOCATION_CATALOG,
  countryCodeFromLabel,
  countryLabel,
  fallbackCitiesForRegion,
  fallbackRegionsFor,
  loadAllCountries,
  loadCountryRegions,
  loadRegionCities,
  regionForCity,
  type CatalogCountry,
  type CatalogRegion,
  type CatalogLocationCity,
} from "@/pages/clubLocationCatalog";
import { validateClubLocation } from "@/pages/clubCreationLocation";

/** Country → region/state → city values are selected from dependent lists. */
export function useClubLocation() {
  const [countryText, setCountryText] = useState("");
  const [cityName, setCityName] = useState("");
  const [regionName, setRegionName] = useState("");
  const [regionCode, setRegionCode] = useState("");
  const countryCode = countryCodeFromLabel(countryText);
  const validation = validateClubLocation(countryCode, cityName, regionName);

  const changeCountry = (label: string) => {
    setCountryText(label);
    setCityName("");
    setRegionName("");
    setRegionCode("");
  };

  const changeCity = (city: string, matchedRegion?: string, matchedRegionCode?: string) => {
    setCityName(city);
    const resolvedRegion = matchedRegion || regionForCity(countryCode, city);
    if (resolvedRegion) setRegionName(resolvedRegion);
    if (matchedRegionCode) setRegionCode(matchedRegionCode);
  };

  const changeRegion = (region: string, code = "") => {
    setRegionName(region);
    setRegionCode(code);
    if (cityName && (!region || regionForCity(countryCode, cityName) !== region)) {
      setCityName("");
    }
  };

  return {
    countryText,
    cityName,
    regionName,
    regionCode,
    countryCode,
    validation,
    changeCountry,
    changeCity,
    changeRegion,
  };
}

export type ClubLocationState = ReturnType<typeof useClubLocation>;

/** Dependent dropdowns for the club's official home location. */
export function ClubLocationFields({
  state,
  testIdPrefix,
  disabled,
}: {
  state: ClubLocationState;
  testIdPrefix: string;
  disabled?: boolean;
}) {
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const touch = (key: string) => setTouched((current) => ({ ...current, [key]: true }));
  const [countries, setCountries] = useState<CatalogCountry[]>(
    [...CLUB_LOCATION_CATALOG].sort((a, b) => a.name.localeCompare(b.name)),
  );
  const [regions, setRegions] = useState<CatalogRegion[]>([]);
  const [cities, setCities] = useState<CatalogLocationCity[]>([]);
  const [countriesLoading, setCountriesLoading] = useState(false);
  const [regionsLoading, setRegionsLoading] = useState(false);
  const [citiesLoading, setCitiesLoading] = useState(false);
  const [usingBundledFallback, setUsingBundledFallback] = useState(false);

  // The CDN snapshot contains 250+ countries. Tests use the bundled catalogue to
  // stay deterministic; production loads only country, selected-state and selected-city data.
  useEffect(() => {
    if (process.env.NODE_ENV === "test") return;
    let active = true;
    setCountriesLoading(true);
    loadAllCountries()
      .then((loaded) => {
        if (active && loaded.length) setCountries(loaded);
      })
      .catch(() => {
        if (active) setUsingBundledFallback(true);
      })
      .finally(() => {
        if (active) setCountriesLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!state.countryCode) {
      setRegions([]);
      setRegionsLoading(false);
      return;
    }

    const bundled = fallbackRegionsFor(state.countryCode);
    if (process.env.NODE_ENV === "test") {
      setRegions(bundled);
      return;
    }

    let active = true;
    setRegions([]);
    setRegionsLoading(true);
    loadCountryRegions(state.countryCode)
      .then((loaded) => {
        if (active) setRegions(loaded.length ? loaded : bundled);
      })
      .catch(() => {
        if (active) {
          setRegions(bundled);
          setUsingBundledFallback(true);
        }
      })
      .finally(() => {
        if (active) setRegionsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [state.countryCode]);

  useEffect(() => {
    if (!state.countryCode || !state.regionName) {
      setCities([]);
      setCitiesLoading(false);
      return;
    }

    const bundled = fallbackCitiesForRegion(state.countryCode, state.regionName, state.regionCode);
    if (process.env.NODE_ENV === "test" || !state.regionCode) {
      setCities(bundled);
      return;
    }

    let active = true;
    setCities([]);
    setCitiesLoading(true);
    loadRegionCities(state.countryCode, state.regionCode, state.regionName)
      .then((loaded) => {
        if (active) setCities(loaded.length ? loaded : bundled);
      })
      .catch(() => {
        if (active) {
          setCities(bundled);
          setUsingBundledFallback(true);
        }
      })
      .finally(() => {
        if (active) setCitiesLoading(false);
      });
    return () => {
      active = false;
    };
  }, [state.countryCode, state.regionCode, state.regionName]);

  const countryId = `${testIdPrefix}-country-input`;
  const cityId = `${testIdPrefix}-city-input`;
  const regionId = `${testIdPrefix}-region-input`;
  const selectedCountryOption = countries.find((country) => country.code === state.countryCode);
  const countrySelectValue = selectedCountryOption ? countryLabel(selectedCountryOption) : state.countryText;
  const countryBad = touched.country && !state.countryCode;
  const cityBad = touched.city && !state.cityName;
  const regionBad = touched.region && !state.regionName;
  const fieldClass =
    "gx-input w-full appearance-none bg-slate-950 pr-9 text-sm text-white disabled:cursor-not-allowed disabled:opacity-50";
  const labelClass = "mb-1 block text-[10px] font-semibold uppercase tracking-wider text-slate-400";
  const error = (message: string, id: string) => (
    <p id={id} role="alert" className="mt-1 text-xs text-rose-300">
      {message}
    </p>
  );
  const selectWrap = "relative";

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3" data-testid={`${testIdPrefix}-location-fields`}>
      <div className="min-w-0">
        <label htmlFor={countryId} className={labelClass}>Country</label>
        <div className={selectWrap}>
          <select
            id={countryId}
            data-testid={countryId}
            aria-label="Country"
            aria-invalid={countryBad ? true : undefined}
            aria-describedby={countryBad ? `${testIdPrefix}-country-error` : undefined}
            className={fieldClass}
            disabled={disabled}
            value={countrySelectValue}
            onChange={(event) => state.changeCountry(event.target.value)}
            onBlur={() => touch("country")}
          >
            <option value="">{countriesLoading ? "Loading countries…" : "Select country"}</option>
            {countries.map((country) => (
              <option key={country.code} value={countryLabel(country)}>
                {country.name} ({country.code})
              </option>
            ))}
          </select>
          <span aria-hidden="true" className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-slate-400">⌄</span>
        </div>
        {countryBad && error("Select a country from the list.", `${testIdPrefix}-country-error`)}
      </div>

      <div className="min-w-0">
        <label htmlFor={regionId} className={labelClass}>Region / state</label>
        <div className={selectWrap}>
          <select
            id={regionId}
            data-testid={regionId}
            aria-label="Region or state"
            aria-invalid={regionBad ? true : undefined}
            aria-describedby={regionBad ? `${testIdPrefix}-region-error` : undefined}
            className={fieldClass}
            disabled={disabled || !state.countryCode || regionsLoading || regions.length === 0}
            value={state.regionName}
            onChange={(event) => {
              const selected = regions.find((region) => region.name === event.target.value);
              state.changeRegion(event.target.value, selected?.code || "");
            }}
            onBlur={() => touch("region")}
          >
            <option value="">{regionsLoading ? "Loading regions…" : "Select region / state"}</option>
            {regions.map((region) => <option key={region.name} value={region.name}>{region.name}</option>)}
          </select>
          <span aria-hidden="true" className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-slate-400">⌄</span>
        </div>
        {regionBad && error("Select the club's region or state.", `${testIdPrefix}-region-error`)}
      </div>

      <div className="min-w-0">
        <label htmlFor={cityId} className={labelClass}>Home city</label>
        <div className={selectWrap}>
          <select
            id={cityId}
            data-testid={cityId}
            aria-label="City"
            aria-invalid={cityBad ? true : undefined}
            aria-describedby={cityBad ? `${testIdPrefix}-city-error` : undefined}
            className={fieldClass}
            disabled={disabled || !state.countryCode || !state.regionName || citiesLoading || cities.length === 0}
            value={state.cityName}
            onChange={(event) => {
              const selected = cities.find((city) => city.city === event.target.value);
              state.changeCity(event.target.value, selected?.region, selected?.regionCode);
            }}
            onBlur={() => touch("city")}
          >
            <option value="">{citiesLoading ? "Loading cities…" : "Select city"}</option>
            {cities.map((city) => (
              <option key={`${city.region}:${city.city}`} value={city.city}>{city.city}</option>
            ))}
          </select>
          <span aria-hidden="true" className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-slate-400">⌄</span>
        </div>
        {cityBad && error("Select the club's home city.", `${testIdPrefix}-city-error`)}
      </div>
      <p className="col-span-full mt-1 text-[9px] text-slate-600">
        Location reference data:{" "}
        <a
          href="https://github.com/dr5hn/countries-states-cities-database"
          target="_blank"
          rel="noreferrer"
          className="underline decoration-slate-700 underline-offset-2 hover:text-slate-400"
        >
          Country State City Database
        </a>
        {" "}· ODbL 1.0
        {usingBundledFallback ? " · Using GTEX's bundled fallback list where available." : ""}
      </p>
    </div>
  );
}

/** Request fields for POST /clubs once all three dropdowns have valid selections. */
export function clubLocationPayload(v: Extract<ClubLocationState["validation"], { valid: true }>) {
  return { country_code: v.countryCode, region_name: v.regionName, city_name: v.cityName };
}
