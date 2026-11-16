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

/** In-memory POST /clubs and GET /clubs/{id} adapter. */
function installFakeServer(posted: any[], store: Record<string, any>) {
  api.defaults.adapter = async (config: any) => {
    const ok = (status: number, data: any) => ({ status, statusText: "", headers: {}, config, data });
    if (config.method === "post" && config.url === "/clubs") {
      const body = JSON.parse(config.data);
      posted.push(body);
      const id = `club-${posted.length}`;
      store[id] = { club_id: id, ...body };
      return ok(201, { club_id: id });
    }
    const match = /^\\/clubs\\/(.+)$/.exec(config.url);
    if (config.method === "get" && match && store[match[1]]) return ok(200, store[match[1]]);
    throw new Error(`unexpected ${config.method} ${config.url}`);
  };
}

function setSelectValue(select: HTMLSelectElement, value: string) {
  const setter = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value")!.set!;
  setter.call(select, value);
  select.dispatchEvent(new Event("change", { bubbles: true }));
}

function Form({ prefix, onDone }: { prefix: string; onDone: (id: string, err?: string) => void }) {
  const location = useClubLocation();
  const submit = async () => {
    if (!location.validation.valid) return;
    try {
      const { data } = await api.post("/clubs", {
        club_name: "Test FC",
        ...clubLocationPayload(location.validation),
      });
      onDone(data.club_id);
    } catch (error) {
      onDone("", clubCreateErrorMessage(error, () => "fallback"));
    }
  };
  return (
    <div>
      <ClubLocationFields state={location} testIdPrefix={prefix} />
      <button data-testid="go" disabled={!location.validation.valid} onClick={submit} />
    </div>
  );
}

function Saved({ id, onLoad }: { id: string; onLoad: (club: any) => void }) {
  React.useEffect(() => {
    api.get(`/clubs/${id}`).then((response: any) => onLoad(response.data));
  }, [id, onLoad]);
  return null;
}

describe("club location dropdowns", () => {
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

  const q = (id: string) => host.querySelector(`[data-testid="${id}"]`) as HTMLSelectElement;
  const flush = () => act(async () => { await new Promise((resolve) => setTimeout(resolve, 0)); });

  test("starts with real dropdowns, a broad country list and no premature errors", () => {
    act(() => root.render(<Form prefix="t" onDone={() => {}} />));

    expect(q("t-country-input").tagName).toBe("SELECT");
    expect(q("t-country-input").options.length).toBeGreaterThanOrEqual(90);
    expect(q("t-country-input").value).toBe("");
    expect(q("t-city-input").disabled).toBe(true);
    expect(q("t-region-input").disabled).toBe(true);
    expect(q("go").disabled).toBe(true);
    expect(host.textContent).toContain("Country");
    expect(host.textContent).toContain("Home city");
    expect(host.textContent).toContain("Region / state");
    expect(host.querySelectorAll('[role="alert"]')).toHaveLength(0);
  });

  test("country, region and city dropdowns cascade and persist the selected Nigerian location", async () => {
    const posted: any[] = [];
    const store: Record<string, any> = {};
    installFakeServer(posted, store);
    let clubId = "";

    act(() => root.render(<Form prefix="t" onDone={(id) => { clubId = id; }} />));
    act(() => setSelectValue(q("t-country-input"), "Nigeria (NG)"));

    expect(q("t-city-input").disabled).toBe(false);
    expect(q("t-region-input").options.length).toBeGreaterThan(30);

    act(() => setSelectValue(q("t-region-input"), "Rivers"));
    expect(q("t-city-input").value).toBe("");
    expect(Array.from(q("t-city-input").options).map((option) => option.value)).toContain("Port Harcourt");
    expect(Array.from(q("t-city-input").options).map((option) => option.value)).not.toContain("Lagos");

    act(() => setSelectValue(q("t-city-input"), "Port Harcourt"));
    expect(q("t-region-input").value).toBe("Rivers");
    expect(q("go").disabled).toBe(false);
    await act(async () => { q("go").click(); });
    await flush();

    expect(posted).toHaveLength(1);
    expect(posted[0]).toMatchObject({
      country_code: "NG",
      region_name: "Rivers",
      city_name: "Port Harcourt",
    });

    act(() => root.unmount());
    root = createRoot(host);
    let loaded: any = null;
    await act(async () => {
      root.render(<Saved id={clubId} onLoad={(club) => { loaded = club; }} />);
    });
    await flush();
    expect(loaded).toMatchObject({
      country_code: "NG",
      region_name: "Rivers",
      city_name: "Port Harcourt",
    });
  });

  test("offers Ikorodu and other cities under the selected Lagos state", () => {
    act(() => root.render(<Form prefix="t" onDone={() => {}} />));
    act(() => setSelectValue(q("t-country-input"), "Nigeria (NG)"));
    act(() => setSelectValue(q("t-region-input"), "Lagos"));

    const cityOptions = Array.from(q("t-city-input").options).map((option) => option.value);
    expect(cityOptions).toContain("Ikorodu");
    expect(cityOptions).toContain("Ikeja");
    expect(cityOptions).toContain("Lagos");
    expect(cityOptions).not.toContain("Port Harcourt");
  });

  test("selecting a city automatically selects its region/state", () => {
    act(() => root.render(<Form prefix="t" onDone={() => {}} />));
    act(() => setSelectValue(q("t-country-input"), "Ghana (GH)"));
    act(() => setSelectValue(q("t-city-input"), "Kumasi"));

    expect(q("t-region-input").value).toBe("Ashanti");
    expect(q("go").disabled).toBe(false);
  });

  test("changing country clears the previous city and region", () => {
    act(() => root.render(<Form prefix="t" onDone={() => {}} />));
    act(() => setSelectValue(q("t-country-input"), "Nigeria (NG)"));
    act(() => setSelectValue(q("t-city-input"), "Lagos"));
    expect(q("t-region-input").value).toBe("Lagos");

    act(() => setSelectValue(q("t-country-input"), "Ghana (GH)"));
    expect(q("t-city-input").value).toBe("");
    expect(q("t-region-input").value).toBe("");
    expect(q("go").disabled).toBe(true);
  });

  test("surfaces server validation errors clearly", () => {
    const error = {
      response: {
        data: { detail: [{ loc: ["body", "city_name"], msg: "Field required" }] },
      },
    };
    expect(clubCreateErrorMessage(error, () => "fallback")).toBe("city name: Field required");
    expect(clubCreateErrorMessage({ response: { data: {} } }, () => "fallback")).toBe("fallback");
  });
});
