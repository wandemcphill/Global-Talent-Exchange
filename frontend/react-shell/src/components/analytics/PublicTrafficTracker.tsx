import axios from "axios";
import { useCallback, useEffect, useRef } from "react";
import { useLocation } from "react-router-dom";
import { API, api, tokens } from "@/lib/api";

const VISITOR_STORAGE_KEY = "gtex_public_visitor_v1";
const HEARTBEAT_INTERVAL_MS = 30_000;

function createVisitorId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  const bytes = new Uint8Array(16);
  if (typeof crypto !== "undefined" && typeof crypto.getRandomValues === "function") {
    crypto.getRandomValues(bytes);
  } else {
    for (let index = 0; index < bytes.length; index += 1) {
      bytes[index] = Math.floor(Math.random() * 256);
    }
  }
  // Keep the fallback UUID-shaped because the API validates the visitor ID.
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (value) => value.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

/**
 * Runs inside the canonical React Router so public, authenticated, and advertiser
 * routes all contribute page views. Only a random first-party visitor UUID and the
 * route pathname are sent; query strings, IP addresses, and browser fingerprints
 * are deliberately not collected by this tracker.
 */
export function PublicTrafficTracker() {
  const location = useLocation();
  const visitorIdRef = useRef<string | null>(null);

  const getVisitorId = useCallback((): string => {
    if (visitorIdRef.current) return visitorIdRef.current;

    let visitorId: string | null = null;
    try {
      visitorId = window.localStorage.getItem(VISITOR_STORAGE_KEY);
    } catch {
      // Storage may be disabled. Keep an in-memory ID for this page lifetime.
    }

    if (!visitorId) {
      visitorId = createVisitorId();
      try {
        window.localStorage.setItem(VISITOR_STORAGE_KEY, visitorId);
      } catch {
        // In-memory tracking still works for this page lifetime.
      }
    }

    visitorIdRef.current = visitorId;
    return visitorId;
  }, []);

  const sendHeartbeat = useCallback(
    (pageView: boolean) => {
      if (typeof document === "undefined" || document.visibilityState === "hidden") return;
      // Anonymous browsers only need to report navigations. Signed-in users also
      // send interval heartbeats so their session remains live while interacting.
      if (!pageView && !tokens.get()) return;
      const payload = {
        visitor_id: getVisitorId(),
        path: location.pathname || "/",
        page_view: pageView,
      };
      void api
        .post("/public/traffic/heartbeat", payload, { timeout: 4_000 })
        .catch((error: any) => {
          // An expired stored token must not cause an otherwise valid anonymous
          // page view to disappear from public visitor totals.
          if (pageView && error?.response?.status === 401) {
            void axios
              .post(`${API}/public/traffic/heartbeat`, payload, { timeout: 4_000 })
              .catch(() => undefined);
          }
          // Public telemetry must never block navigation or the application shell.
        });
    },
    [getVisitorId, location.pathname],
  );

  useEffect(() => {
    sendHeartbeat(true);
  }, [sendHeartbeat]);

  useEffect(() => {
    const timer = window.setInterval(() => sendHeartbeat(false), HEARTBEAT_INTERVAL_MS);
    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") sendHeartbeat(false);
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [sendHeartbeat]);

  return null;
}
