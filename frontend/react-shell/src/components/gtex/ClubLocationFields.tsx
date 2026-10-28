import React, { useMemo, useState } from "react";
import {
  CLUB_LOCATION_CATALOG,
  citiesFor,
  countryLabel,
  regionForCity,
  resolveCountryCode,
} from "@/pages/clubLocationCatalog";
import { validateClubLocation } from "@/pages/clubCreationLocation";

/** State + validation for the club home-location fields. Starts empty: no default country. */
export function useClubLocation() {
  const [countryText, setCountryText] = useState("");
  const [cityName, setCityName] = useState("");
  const [regionName, setRegionName] = useState("");
  const [regionEdited, setRegionEdited] = useState(false);
  const countryCode = resolveCountryCode(countryText);
  const validation = validateClubLocation(countryCode, cityName, regionName);

  const changeCountry = (text: string) => {
    const next = resolveCountryCode(text);
    setCountryText(text);
    if (next !== countryCode) {
      // A different country invalidates the previous city/region choice.
      setCityName("");
      setRegionName("");
      setRegionEdited(false);
    }
  };
  const changeCity = (text: string) => {
    setCityName(text);
    const known = regionForCity(countryCode, text);
    if (known && !regionEdited) setRegionName(known);
  };
  const changeRegion = (text: string) => {
    setRegionName(text);
    setRegionEdited(true);
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

/** Searchable country / city / region inputs. `testIdPrefix` e.g. "new-club" or "first-club". */
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
  const touch = (k: string) => setTouched((t) => ({ ...t, [k]: true }));
  const cities = useMemo(() => citiesFor(state.countryCode), [state.countryCode]);
  const countryList = `${testIdPrefix}-country-options`;
  const cityList = `${testIdPrefix}-city-options`;
  const countryBad = touched.country && !state.countryCode;
  const cityBad = touched.city && state.cityName.trim().length < 2;
  const regionBad = touched.region && state.regionName.trim().length < 2;
  const err = (text: string, id: string) => (
    <p id={id} role="alert" className="mt-1 text-xs text-rose-300">
      {text}
    </p>
  );

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3" data-testid={`${testIdPrefix}-location-fields`}>
      <div className="min-w-0">
        <input
          data-testid={`${testIdPrefix}-country-input`}
          aria-label="Country"
          aria-invalid={countryBad ? true : undefined}
          aria-describedby={countryBad ? `${testIdPrefix}-country-error` : undefined}
          className="gx-input w-full"
          placeholder="Search country"
          autoComplete="off"
          list={countryList}
          disabled={disabled}
          value={state.countryText}
          onChange={(e) => state.changeCountry(e.target.value)}
          onBlur={() => touch("country")}
        />
        <datalist id={countryList}>
          {CLUB_LOCATION_CATALOG.map((x) => (
            <option key={x.code} value={countryLabel(x)} />
          ))}
        </datalist>
        {countryBad && err("Select a country from the list.", `${testIdPrefix}-country-error`)}
      </div>
      <div className="min-w-0">
        <input
          data-testid={`${testIdPrefix}-city-input`}
          aria-label="City"
          aria-invalid={cityBad ? true : undefined}
          aria-describedby={cityBad ? `${testIdPrefix}-city-error` : undefined}
          className="gx-input w-full"
          placeholder="City"
          autoComplete="off"
          list={cityList}
          disabled={disabled || !state.countryCode}
          value={state.cityName}
          onChange={(e) => state.changeCity(e.target.value)}
          onBlur={() => touch("city")}
        />
        <datalist id={cityList}>
          {cities.map((x) => (
            <option key={x.city} value={x.city} />
          ))}
        </datalist>
        {cityBad && err("Enter the home city.", `${testIdPrefix}-city-error`)}
      </div>
      <div className="min-w-0">
        <input
          data-testid={`${testIdPrefix}-region-input`}
          aria-label="Region or state"
          aria-invalid={regionBad ? true : undefined}
          aria-describedby={regionBad ? `${testIdPrefix}-region-error` : undefined}
          className="gx-input w-full"
          placeholder="Region / state"
          autoComplete="off"
          disabled={disabled || !state.countryCode}
          value={state.regionName}
          onChange={(e) => state.changeRegion(e.target.value)}
          onBlur={() => touch("region")}
        />
        {regionBad && err("Enter the region or state.", `${testIdPrefix}-region-error`)}
      </div>
    </div>
  );
}

/** Request fields for `POST /clubs` once validation has passed. */
export function clubLocationPayload(v: Extract<ClubLocationState["validation"], { valid: true }>) {
  return { country_code: v.countryCode, region_name: v.regionName, city_name: v.cityName };
}
