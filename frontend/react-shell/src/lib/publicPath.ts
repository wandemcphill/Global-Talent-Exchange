/**
 * Single public-path prefix for the React shell.
 *
 * CRA inlines PUBLIC_URL at build time. The Render publish script sets it to
 * `/console`. Local `npm start` leaves it empty, so the dev server stays at `/`.
 * If served under `/console`, runtime pathname detection automatically falls back
 * to `/console` so routing remains robust across local and production builds.
 */
function resolvePublicUrl(): string {
  const rawPublicUrl = (process.env.PUBLIC_URL || "").trim().replace(/\/+$/, "");
  if (rawPublicUrl) {
    return rawPublicUrl;
  }
  if (typeof window !== "undefined" && window.location.pathname.startsWith("/console")) {
    return "/console";
  }
  return "";
}

/** No trailing slash. Empty in local development at root. `/console` on Render. */
export const PUBLIC_URL = resolvePublicUrl();

/** React Router basename. `/` when the shell is served from the site root. */
export const ROUTER_BASENAME = PUBLIC_URL || "/";

/** Prefix a root-absolute route or `public/` asset with the public URL. */
export function publicUrl(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${PUBLIC_URL}${normalized}`;
}
