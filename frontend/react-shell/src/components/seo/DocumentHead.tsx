import { useEffect } from "react";

export const GTEX_SITE_ORIGIN = "https://playgtex.app";

type DocumentHeadProps = {
  title: string;
  description: string;
  path?: string;
  noindex?: boolean;
};

function upsertMeta(attr: "name" | "property", key: string, content: string) {
  let el = document.head.querySelector(`meta[${attr}="${key}"]`) as HTMLMetaElement | null;
  if (!el) {
    el = document.createElement("meta");
    el.setAttribute(attr, key);
    document.head.appendChild(el);
  }
  el.content = content;
}

function upsertLink(rel: string, href: string) {
  let el = document.head.querySelector(`link[rel="${rel}"]`) as HTMLLinkElement | null;
  if (!el) {
    el = document.createElement("link");
    el.rel = rel;
    document.head.appendChild(el);
  }
  el.href = href;
}

/** Sets the document title, description, and canonical URL for public pages. */
export function DocumentHead({ title, description, path = "/", noindex = false }: DocumentHeadProps) {
  useEffect(() => {
    const canonicalPath = path.startsWith("/") ? path : `/${path}`;
    const canonical = `${GTEX_SITE_ORIGIN}${canonicalPath}`;
    document.title = title;
    document.documentElement.lang = "en-NG";
    upsertMeta("name", "description", description);
    upsertMeta("name", "robots", noindex ? "noindex, nofollow" : "index, follow, max-image-preview:large");
    upsertMeta("name", "geo.region", "NG-LA");
    upsertMeta("name", "geo.placename", "Lagos");
    upsertMeta("name", "geo.position", "6.5244;3.3792");
    upsertMeta("name", "ICBM", "6.5244, 3.3792");
    upsertMeta("property", "og:title", title);
    upsertMeta("property", "og:description", description);
    upsertMeta("property", "og:url", canonical);
    upsertMeta("property", "og:type", "website");
    upsertMeta("property", "og:locale", "en_NG");
    upsertMeta("property", "og:site_name", "GTEX");
    upsertMeta("property", "og:image", `${GTEX_SITE_ORIGIN}/img/hero.jpg`);
    upsertMeta("name", "twitter:card", "summary_large_image");
    upsertMeta("name", "twitter:title", title);
    upsertMeta("name", "twitter:description", description);
    upsertMeta("name", "twitter:image", `${GTEX_SITE_ORIGIN}/img/hero.jpg`);
    upsertLink("canonical", canonical);
  }, [title, description, path, noindex]);

  return null;
}
