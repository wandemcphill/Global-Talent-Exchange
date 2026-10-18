/**
 * Single public-path prefix for the React shell.
 *
 * CRA inlines PUBLIC_URL at build time. The Render publish script sets it to
 * `/console`. Local `npm start` leaves it empty, so the dev server stays at `/`.
 * Router basename, static images, and full-page navigations all read this
 * value so path handling is not repeated in each screen.
 */
const rawPublicUrl = (process.env.PUBLIC_URL || "").trim();

/** No trailing slash. Empty in local development. `/console` on Render. */
export const PUBLIC_URL = rawPublicUrl.replace(/\/+$/, "");

/** React Router basename. `/` when the shell is served from the site root. */
export const ROUTER_BASENAME = PUBLIC_URL || "/";

/** Prefix a root-absolute route or `public/` asset with the public URL. */
export function publicUrl(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${PUBLIC_URL}${normalized}`;
}
