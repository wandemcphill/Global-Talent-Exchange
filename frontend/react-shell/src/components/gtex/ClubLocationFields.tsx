import React, { useMemo, useState } from "react";
import {
  CLUB_LOCATION_CATALOG,
  citiesForRegion,
  countryLabel,
  regionForCity,
  regionsFor,
  resolveCountryCode,
} from "@/pages/clubLocationCatalog";
import { validateClubLocation } from "@/pages/clubCreationLocation";

/** Country → region/state → city values are selected from dependent lists. */
export function useClubLocation() {
  const [countryText, setCountryText] = useState("");
  const [cityName, setCityName] = useState("");
  const [regionName, setRegionName] = useState("");
  const countryCode = resolveCountryCode(countryText);
  const validation = validateClubLocation(countryCode, cityName, regionName);

  const changeCountry = (label: string) => {
    setCountryText(label);
    setCityName("");
    setRegionName("");
  };

  const changeCity = (city: string) => {
    setCityName(city);
    const matchedRegion = regionForCity(countryCode, city);
    if (matchedRegion) setRegionName(matchedRegion);
  };

  const changeRegion = (region: string) => {
    setRegionName(region);
    if (cityName && regionForCity(countryCode, cityName) !== region) {
      setCityName("");
    }
  };

  return {
    countryText,
    cityName,
    regionName,
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
  const countries = useMemo(
    () => [...CLUB_LOCATION_CATALOG].sort((a, b) => a.name.localeCompare(b.name)),
    [],
  );
  const regions = useMemo(() => regionsFor(state.countryCode), [state.countryCode]);
  const cities = useMemo(
    () => citiesForRegion(state.countryCode, state.regionName).slice().sort((a, b) => a.city.localeCompare(b.city)),
    [state.countryCode, state.regionName],
  );

  const countryId = `${testIdPrefix}-country-input`;
  const cityId = `${testIdPrefix}-city-input`;
  const regionId = `${testIdPrefix}-region-input`;
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
            value={state.countryText}
            onChange={(event) => state.changeCountry(event.target.value)}
            onBlur={() => touch("country")}
          >
            <option value="">Select country</option>
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
        <label htmlFor={cityId} className={labelClass}>Home city</label>
        <div className={selectWrap}>
          <select
            id={cityId}
            data-testid={cityId}
            aria-label="City"
            aria-invalid={cityBad ? true : undefined}
            aria-describedby={cityBad ? `${testIdPrefix}-city-error` : undefined}
            className={fieldClass}
            disabled={disabled || !state.countryCode || cities.length === 0}
            value={state.cityName}
            onChange={(event) => state.changeCity(event.target.value)}
            onBlur={() => touch("city")}
          >
            <option value="">Select city</option>
            {cities.map((city) => (
              <option key={`${city.region}:${city.city}`} value={city.city}>{city.city}</option>
            ))}
          </select>
          <span aria-hidden="true" className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-slate-400">⌄</span>
        </div>
        {cityBad && error("Select the club's home city.", `${testIdPrefix}-city-error`)}
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
            disabled={disabled || !state.countryCode || regions.length === 0}
            value={state.regionName}
            onChange={(event) => state.changeRegion(event.target.value)}
            onBlur={() => touch("region")}
          >
            <option value="">Select region / state</option>
            {regions.map((region) => <option key={region} value={region}>{region}</option>)}
          </select>
          <span aria-hidden="true" className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-slate-400">⌄</span>
        </div>
        {regionBad && error("Select the club's region or state.", `${testIdPrefix}-region-error`)}
      </div>
    </div>
  );
}

/** Request fields for POST /clubs once all three dropdowns have valid selections. */
export function clubLocationPayload(v: Extract<ClubLocationState["validation"], { valid: true }>) {
  return { country_code: v.countryCode, region_name: v.regionName, city_name: v.cityName };
}
