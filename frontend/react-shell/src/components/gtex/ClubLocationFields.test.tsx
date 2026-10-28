declare const describe: any;
declare const test: any;
declare const expect: any;
declare const beforeEach: any;
declare const afterEach: any;

if (!process.env.REACT_APP_BACKEND_URL) {
  process.env.REACT_APP_BACKEND_URL = "https://gtex-api-opea.onrender.com";
}

import React, { act } from "react";
import { createRoot, Root } from "react-dom/client";
import { ClubLocationFields, clubLocationPayload, useClubLocation } from "./ClubLocationFields";
import { clubCreateErrorMessage } from "@/pages/clubLocationCatalog";

const { api } = require("@/lib/api");

(globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;

/** Minimal in-memory stand-in for POST /clubs and GET /clubs/{id} using the real request contract. */
function installFakeServer(posted: any[], store: Record<string, any>) {
  api.defaults.adapter = async (config: any) => {
    const ok = (status: number, data: any) => ({ status, statusText: "", headers: {}, config, data });
    if (config.method === "post" && config.url === "/clubs") {
      const body = JSON.parse(config.data);
      posted.push(body);
      if (body.country_code === "XX") {
        const err: any = new Error("Request failed");
        err.response = ok(422, {
          detail: [{ loc: ["body", "country_code"], msg: "String should have at most 8 characters" }],
        });
        throw err;
      }
      const id = `club-${posted.length}`;
      store[id] = { club_id: id, ...body };
      return ok(201, { club_id: id });
    }
    const m = /^\/clubs\/(.+)$/.exec(config.url);
    if (config.method === "get" && m && store[m[1]]) {
      const c = store[m[1]];
      return ok(200, { club_id: c.club_id, country_code: c.country_code, region_name: c.region_name, city_name: c.city_name });
    }
    throw new Error(`unexpected ${config.method} ${config.url}`);
  };
}

function setValue(el: HTMLInputElement, value: string) {
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;
  setter.call(el, value);
  el.dispatchEvent(new Event("input", { bubbles: true }));
}

function Form({ prefix, onDone }: { prefix: string; onDone: (id: string, err?: string) => void }) {
  const loc = useClubLocation();
  const submit = async () => {
    if (!loc.validation.valid) return;
    try {
      const { data } = await api.post("/clubs", { club_name: "Test FC", ...clubLocationPayload(loc.validation) });
      onDone(data.club_id);
    } catch (e) {
      onDone("", clubCreateErrorMessage(e, () => "fallback"));
    }
  };
  return (
    <div>
      <ClubLocationFields state={loc} testIdPrefix={prefix} />
      <button data-testid="go" disabled={!loc.validation.valid} onClick={submit} />
    </div>
  );
}

function Saved({ id, onLoad }: { id: string; onLoad: (club: any) => void }) {
  React.useEffect(() => {
    api.get(`/clubs/${id}`).then((r) => onLoad(r.data));
  }, [id, onLoad]);
  return null;
}

describe("club location form", () => {
  let host: HTMLDivElement;
  let root: Root;
  beforeEach(() => {
    host = document.createElement("div");
    document.body.appendChild(host);
    root = createRoot(host);
  });
  afterEach(() => {
    act(() => root.unmount());
    host.remove();
  });
  const q = (id: string) => host.querySelector(`[data-testid="${id}"]`) as HTMLInputElement;
  const flush = () => act(async () => { await new Promise((r) => setTimeout(r, 0)); });

  test("starts empty with no default country and blocks submission", () => {
    act(() => root.render(<Form prefix="t" onDone={() => {}} />));
    expect(q("t-country-input").value).toBe("");
    expect(q("t-city-input").disabled).toBe(true);
    expect(q("go").disabled).toBe(true);
  });

  test.each([
    ["Ghana (GH)", "Kumasi", "GH", "Ashanti"],
    ["Brazil", "são paulo", "BR", "São Paulo"],
    ["Nigeria (NG)", "Port Harcourt", "NG", "Rivers"],
  ])("persists %s / %s and survives a refresh", async (countryText, city, code, region) => {
    const posted: any[] = [];
    const store: Record<string, any> = {};
    installFakeServer(posted, store);
    let id = "";
    act(() => root.render(<Form prefix="t" onDone={(v) => { id = v; }} />));
    act(() => setValue(q("t-country-input"), countryText));
    act(() => setValue(q("t-city-input"), city));
    expect(q("t-region-input").value).toBe(region); // auto-filled, editable
    expect(q("go").disabled).toBe(false);
    await act(async () => { q("go").click(); });
    await flush();

    expect(posted).toHaveLength(1);
    expect(posted[0].country_code).toBe(code);
    expect(posted[0].region_name).toBe(region);
    expect(posted[0].city_name.toLowerCase()).toBe(city.toLowerCase());
    if (code !== "NG") expect(JSON.stringify(posted[0])).not.toMatch(/Lagos|"NG"/);

    // "Refresh": throw away the form, mount a fresh view that loads the stored club.
    act(() => root.unmount());
    root = createRoot(host);
    let loaded: any = null;
    await act(async () => { root.render(<Saved id={id} onLoad={(c) => { loaded = c; }} />); });
    await flush();
    expect(loaded).toMatchObject({ country_code: code, region_name: region });
    expect(loaded.city_name.toLowerCase()).toBe(city.toLowerCase());
  });

  test("changing country clears the previous city and region", () => {
    act(() => root.render(<Form prefix="t" onDone={() => {}} />));
    act(() => setValue(q("t-country-input"), "Ghana"));
    act(() => setValue(q("t-city-input"), "Accra"));
    act(() => setValue(q("t-country-input"), "Spain"));
    expect(q("t-city-input").value).toBe("");
    expect(q("t-region-input").value).toBe("");
    expect(q("go").disabled).toBe(true);
  });

  test("allows a city that is not in the catalog with a typed region", () => {
    act(() => root.render(<Form prefix="t" onDone={() => {}} />));
    act(() => setValue(q("t-country-input"), "Kenya"));
    act(() => setValue(q("t-city-input"), "Kisumu"));
    expect(q("go").disabled).toBe(true);
    act(() => setValue(q("t-region-input"), "Nyanza"));
    expect(q("go").disabled).toBe(false);
  });

  test("surfaces server validation errors clearly", () => {
    const e = { response: { data: { detail: [{ loc: ["body", "city_name"], msg: "Field required" }] } } };
    expect(clubCreateErrorMessage(e, () => "fallback")).toBe("city name: Field required");
    expect(clubCreateErrorMessage({ response: { data: {} } }, () => "fallback")).toBe("fallback");
  });
});
