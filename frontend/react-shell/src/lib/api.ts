import axios from "axios";

function backendOrigin(): string {
  const configured = (process.env.REACT_APP_BACKEND_URL || "").trim().replace(/\/+$/, "");
  if (!configured) {
    throw new Error(
      "REACT_APP_BACKEND_URL is required. Set it to the canonical GTEX API origin, without a /api suffix.",
    );
  }
  if (configured.endsWith("/api")) {
    throw new Error("REACT_APP_BACKEND_URL must be the API origin without a /api suffix. The shell appends /api itself.");
  }
  return configured;
}

const BACKEND_ORIGIN = backendOrigin();
export const API = `${BACKEND_ORIGIN}/api`;
export const api = axios.create({ baseURL: API });

const ACCESS = "gtex_access";
const REFRESH = "gtex_refresh";

export const tokens = {
  get: () => localStorage.getItem(ACCESS),
  set: (access: string, refresh?: string) => {
    localStorage.setItem(ACCESS, access);
    if (refresh) localStorage.setItem(REFRESH, refresh);
  },
  clear: () => {
    localStorage.removeItem(ACCESS);
    localStorage.removeItem(REFRESH);
  },
  refresh: () => localStorage.getItem(REFRESH),
};

api.interceptors.request.use((config) => {
  const t = tokens.get();
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});

let refreshing: Promise<string | null> | null = null;

const unwrap = (body: any) => (body && body.success === true && "data" in body ? body.data : body);

async function doRefresh(): Promise<string | null> {
  const rt = tokens.refresh();
  if (!rt) return null;
  try {
    const { data: raw } = await axios.post(`${API}/v2/auth/refresh`, { refresh_token: rt });
    const data = unwrap(raw);
    tokens.set(data.access_token, data.refresh_token);
    return data.access_token;
  } catch {
    tokens.clear();
    return null;
  }
}

api.interceptors.response.use(
  (r) => {
    r.data = unwrap(r.data);
    return r;
  },
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry && tokens.refresh()) {
      original._retry = true;
      refreshing = refreshing || doRefresh();
      const t = await refreshing;
      refreshing = null;
      if (t) {
        original.headers.Authorization = `Bearer ${t}`;
        return api(original);
      }
    }
    return Promise.reject(error);
  },
);

const READABLE: Record<string, string> = {
  insufficient_funds: "Not enough funds in this account.",
  same_owner_bracket_blocked: "Clubs under common ownership can't enter the same prize-sensitive bracket.",
  club_ownership_cap_reached: "You already own the maximum of 3 clubs.",
  paystack_secret_key_not_configured: "Paystack isn't connected yet. Add the Paystack secret key to enable Naira deposits.",
  withdrawal_not_eligible: "This withdrawal does not pass the payout eligibility checks.",
  related_party_transfer_blocked: "Related-party transfer blocked by integrity rules.",
  sign_starting_squad_first: "Sign a starting squad (11 players incl. a goalkeeper) first.",
};

export function errMsg(e: any): string {
  const d = e?.response?.data;
  const detail = d?.detail ?? d?.details ?? d;
  const code = detail?.code || d?.code;
  if (code && READABLE[code]) return READABLE[code];
  if (typeof detail?.detail === "string") return detail.detail;
  if (typeof d?.message === "string" && d.message !== "Request failed.") return d.message;
  if (code) return String(code).replace(/_/g, " ");
  return e?.message || "Something went wrong";
}
