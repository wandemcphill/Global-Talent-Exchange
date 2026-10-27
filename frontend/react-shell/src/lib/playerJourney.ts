/**
 * Regen discovery -> scouting -> offer -> contract -> squad registration journey.
 *
 * Everything here is a pure projection of records the backend has already
 * returned. Nothing in this module (or the UI built on it) may mark a step
 * complete on its own: a step is "done" only when an API record proves it.
 * The canonical player id is carried through every link unchanged.
 */

export type JourneyStepState = "done" | "current" | "pending" | "blocked" | "unavailable" | "error";
export type Tone = "emerald" | "cyan" | "gold" | "red" | "slate";

export interface Source<T> {
  status: "idle" | "loading" | "error" | "ok";
  data?: T;
  /** Human-readable failure; the HTTP status lets the UI tell 403/404 from 5xx. */
  error?: string;
  httpStatus?: number;
}

export interface JourneyAction {
  label: string;
  to?: string;
}

export interface JourneyStep {
  id: "report" | "watchlist" | "listing" | "offer" | "contract" | "registration";
  title: string;
  state: JourneyStepState;
  detail: string;
  action?: JourneyAction;
}

export const SQUAD_SEASON_LABEL = "launch";

const enc = encodeURIComponent;

export const journeyLinks = {
  dossier: (playerId: string) => `/app/regen-world?player=${enc(playerId)}`,
  transferHub: (lane: "listings" | "offers" | "negotiations" | "shortlist" | "bids", playerId: string) =>
    `/app/transfer-hub?lane=${lane}&player=${enc(playerId)}`,
  squad: (playerId: string) => `/app/squad?player=${enc(playerId)}`,
};

const LANES = ["listings", "offers", "negotiations", "bids", "shortlist"] as const;
export type JourneyLane = (typeof LANES)[number];

export function readJourneyParams(search: string): { player: string | null; lane: JourneyLane | null } {
  const params = new URLSearchParams(search);
  const player = (params.get("player") || "").trim();
  const lane = (params.get("lane") || "").trim() as JourneyLane;
  return { player: player || null, lane: LANES.includes(lane) ? lane : null };
}

/** Canonical id of a regen/prospect row from any of the regen-universe list shapes. */
export function canonicalPlayerId(row: any): string | null {
  if (!row) return null;
  const id =
    row.player_id ??
    row.player?.player_id ??
    row.player?.id ??
    row.id;
  return typeof id === "string" && id.trim() ? id.trim() : null;
}

export interface StatusView {
  label: string;
  tone: Tone;
  explanation: string;
}

/** Offer statuses are those of TransferHubOfferView. Unknown values are shown verbatim, never guessed. */
export function describeOffer(status: unknown): StatusView {
  const s = String(status ?? "").toLowerCase();
  switch (s) {
    case "draft":
      return { label: "Draft", tone: "slate", explanation: "Saved but not yet sent to the selling club." };
    case "open":
      return { label: "Offered", tone: "gold", explanation: "Sent. Waiting for the selling club to respond." };
    case "countered":
      return { label: "Countered", tone: "cyan", explanation: "The other club answered with different terms." };
    case "accepted":
      return {
        label: "Offer accepted",
        tone: "emerald",
        explanation: "The club agreed the fee. The player's contract terms are a separate step.",
      };
    case "rejected":
      return { label: "Rejected", tone: "red", explanation: "The selling club turned this offer down." };
    case "cancelled":
      return { label: "Cancelled", tone: "slate", explanation: "This offer was withdrawn." };
    case "expired":
      return { label: "Expired", tone: "red", explanation: "No answer arrived before the offer expired." };
    default:
      return { label: s ? s.replace(/_/g, " ") : "Unknown", tone: "slate", explanation: "Status reported by the transfer service." };
  }
}

/** Negotiation statuses are those of TransferNegotiationView (player / agent / coach decision loop). */
export function describeNegotiation(status: unknown, opts: { decisionDueAt?: string | null } = {}): StatusView {
  const s = String(status ?? "").toLowerCase();
  switch (s) {
    case "awaiting_contract_offer":
      return {
        label: "Awaiting contract terms",
        tone: "gold",
        explanation: "The transfer fee is settled. The buying club must now submit wage and contract length.",
      };
    case "player_delayed": {
      const due = opts.decisionDueAt ? ` Decision due ${formatWhen(opts.decisionDueAt)}.` : "";
      return {
        label: "Awaiting player decision",
        tone: "cyan",
        explanation: `The player is considering the terms.${due}`,
      };
    }
    case "counter_offer":
      return {
        label: "Agent counter-offer",
        tone: "cyan",
        explanation: "The player's agent wants different terms. Review the demands and resubmit.",
      };
    case "coach_blocked":
      return {
        label: "Blocked by coach",
        tone: "red",
        explanation: "The selling club's coach has vetoed this move. The reason is shown below when supplied.",
      };
    case "rejected":
      return { label: "Player rejected", tone: "red", explanation: "The player turned the contract down." };
    case "collapsed":
      return { label: "Talks collapsed", tone: "red", explanation: "Negotiations ended without a deal." };
    case "completed":
      return { label: "Completed", tone: "emerald", explanation: "The backend recorded the contract and transfer." };
    default:
      return { label: s ? s.replace(/_/g, " ") : "Unknown", tone: "slate", explanation: "Status reported by the transfer service." };
  }
}

export function isNegotiationActionable(status: unknown): boolean {
  return ["awaiting_contract_offer", "player_delayed", "counter_offer"].includes(String(status ?? "").toLowerCase());
}

export function formatWhen(iso: string): string {
  const t = Date.parse(iso);
  return Number.isFinite(t) ? new Date(t).toLocaleString() : iso;
}

/** Newest negotiation involving this player for the active club (API returns newest first). */
export function findNegotiation(list: any[] | undefined, playerId: string, clubId: string | null): any | null {
  if (!Array.isArray(list)) return null;
  const mine = list.filter(
    (n) => n?.player_id === playerId && (!clubId || n.bidder_club_id === clubId || n.selling_club_id === clubId),
  );
  return mine[0] ?? null;
}

/** Offers placed on any listing of this player (offers carry listing ids, not player ids). */
export function findPlayerOffers(offers: any[] | undefined, listings: any[] | undefined, playerId: string): any[] {
  if (!Array.isArray(offers) || !Array.isArray(listings)) return [];
  const ids = new Set(listings.filter((l) => l?.player_id === playerId).map((l) => l.id));
  return offers.filter((o) => ids.has(o?.listing_id));
}

export type RegistrationMembership = "registered" | "draft" | "not_included" | "no_registration";

export function registrationMembership(registration: any | null | undefined, playerId: string): RegistrationMembership {
  if (!registration) return "no_registration";
  const included = (registration.players || []).some((p: any) => p?.player_id === playerId);
  if (!included) return "not_included";
  const status = String(registration.status || "").toLowerCase();
  return status === "submitted" || status === "locked" ? "registered" : "draft";
}

function sourceProblem<T>(src: Source<T>, what: string): string | null {
  if (src.status !== "error") return null;
  if (src.httpStatus === 403) return `You do not have permission to view ${what} for this club.`;
  return `Could not load ${what}${src.error ? `: ${src.error}` : "."}`;
}

export interface JourneyInput {
  playerId: string;
  clubId: string | null;
  report: Source<any | null>;
  watchlist: Source<any[]>;
  listings: Source<any[]>;
  offers: Source<any[]>;
  negotiations: Source<any[]>;
  registration: Source<any | null>;
  /** Club the backend says currently holds the player, when known. */
  currentClubId?: string | null;
}

export function buildJourney(input: JourneyInput): JourneyStep[] {
  const { playerId, clubId } = input;
  const needsClub: JourneyStep["state"] = "unavailable";
  const noClub = "Choose an active club to use this step.";
  const steps: JourneyStep[] = [];

  // 1. Scout report
  {
    const problem = sourceProblem(input.report, "the scout report");
    if (problem) steps.push({ id: "report", title: "Scout report", state: "error", detail: problem });
    else if (input.report.status === "loading") steps.push({ id: "report", title: "Scout report", state: "pending", detail: "Checking for a report…" });
    else if (input.report.data) {
      const r = input.report.data;
      steps.push({
        id: "report",
        title: "Scout report",
        state: "done",
        detail: typeof r.summary_text === "string" && r.summary_text ? r.summary_text : "A scout report exists for this player.",
      });
    } else {
      steps.push({
        id: "report",
        title: "Scout report",
        state: "pending",
        detail: "No scout report is recorded for your club yet. Reports come from scouting missions.",
      });
    }
  }

  // 2. Watchlist
  {
    const problem = clubId ? sourceProblem(input.watchlist, "the watchlist") : null;
    if (!clubId) steps.push({ id: "watchlist", title: "Shortlist", state: needsClub, detail: noClub });
    else if (problem) steps.push({ id: "watchlist", title: "Shortlist", state: "error", detail: problem });
    else if (input.watchlist.status === "loading") steps.push({ id: "watchlist", title: "Shortlist", state: "pending", detail: "Checking the shortlist…" });
    else {
      const entry = (input.watchlist.data || []).find((e) => e?.player_id === playerId);
      steps.push(
        entry
          ? {
              id: "watchlist",
              title: "Shortlist",
              state: "done",
              detail: `Saved by your club (source: ${entry.source || "scouting"}).`,
              action: { label: "Open shortlist", to: journeyLinks.transferHub("shortlist", playerId) },
            }
          : { id: "watchlist", title: "Shortlist", state: "pending", detail: "Not on your club's shortlist." },
      );
    }
  }

  // 3. Market listing
  const playerListings = (input.listings.data || []).filter((l) => l?.player_id === playerId);
  const openListing = playerListings.find((l) => l.status === "open");
  {
    const problem = sourceProblem(input.listings, "market listings");
    if (problem) steps.push({ id: "listing", title: "Transfer listing", state: "error", detail: problem });
    else if (input.listings.status === "loading") steps.push({ id: "listing", title: "Transfer listing", state: "pending", detail: "Checking the market…" });
    else if (openListing) {
      steps.push({
        id: "listing",
        title: "Transfer listing",
        state: "done",
        detail: `Open listing asking ${Number(openListing.base_price).toLocaleString()} GTX.`,
        action: { label: "View listing", to: journeyLinks.transferHub("listings", playerId) },
      });
    } else {
      steps.push({
        id: "listing",
        title: "Transfer listing",
        state: "blocked",
        detail:
          "No open listing. A formal offer needs an open listing, so there is nothing to bid on until the owner lists this player.",
      });
    }
  }

  // 4. Offer
  const offers = findPlayerOffers(input.offers.data, input.listings.data, playerId);
  const latestOffer = offers[0] ?? null;
  {
    const problem = clubId ? sourceProblem(input.offers, "offers") : null;
    if (!clubId) steps.push({ id: "offer", title: "Offer", state: needsClub, detail: noClub });
    else if (problem) steps.push({ id: "offer", title: "Offer", state: "error", detail: problem });
    else if (input.offers.status === "loading") steps.push({ id: "offer", title: "Offer", state: "pending", detail: "Checking offers…" });
    else if (latestOffer) {
      const v = describeOffer(latestOffer.status);
      const finished = ["accepted"].includes(String(latestOffer.status));
      steps.push({
        id: "offer",
        title: "Offer",
        state: finished ? "done" : ["rejected", "cancelled", "expired"].includes(String(latestOffer.status)) ? "blocked" : "current",
        detail: `${v.label}: ${v.explanation}`,
        action: { label: "Open offers", to: journeyLinks.transferHub("offers", playerId) },
      });
    } else {
      steps.push({
        id: "offer",
        title: "Offer",
        state: openListing ? "current" : "pending",
        detail: openListing ? "No offer from your club yet." : "Needs an open listing first.",
        action: openListing ? { label: "Make an offer", to: journeyLinks.transferHub("listings", playerId) } : undefined,
      });
    }
  }

  // 5. Contract (player / agent / coach decision)
  const negotiation = findNegotiation(input.negotiations.data, playerId, clubId);
  {
    const problem = clubId ? sourceProblem(input.negotiations, "negotiations") : null;
    if (!clubId) steps.push({ id: "contract", title: "Contract decision", state: needsClub, detail: noClub });
    else if (problem) steps.push({ id: "contract", title: "Contract decision", state: "error", detail: problem });
    else if (input.negotiations.status === "loading") steps.push({ id: "contract", title: "Contract decision", state: "pending", detail: "Checking negotiations…" });
    else if (negotiation) {
      const v = describeNegotiation(negotiation.status, { decisionDueAt: negotiation.decision_due_at });
      const s = String(negotiation.status);
      steps.push({
        id: "contract",
        title: "Contract decision",
        state: s === "completed" ? "done" : ["rejected", "collapsed", "coach_blocked"].includes(s) ? "blocked" : "current",
        detail: `${v.label}: ${v.explanation}`,
        action: { label: "Open negotiation", to: journeyLinks.transferHub("negotiations", playerId) },
      });
    } else {
      steps.push({
        id: "contract",
        title: "Contract decision",
        state: "pending",
        detail: "Starts after a transfer fee is agreed. No negotiation exists for this player yet.",
      });
    }
  }

  // 6. Squad registration — only a backend registration record proves this step.
  {
    const completed = negotiation && String(negotiation.status) === "completed";
    const problem = clubId ? sourceProblem(input.registration, "squad registration") : null;
    if (!clubId) steps.push({ id: "registration", title: "Squad registration", state: needsClub, detail: noClub });
    else if (problem) steps.push({ id: "registration", title: "Squad registration", state: "error", detail: problem });
    else if (input.registration.status === "loading") steps.push({ id: "registration", title: "Squad registration", state: "pending", detail: "Checking registration…" });
    else {
      const m = registrationMembership(input.registration.data, playerId);
      const link = { label: "Open squad registration", to: journeyLinks.squad(playerId) };
      if (m === "registered") {
        steps.push({
          id: "registration",
          title: "Squad registration",
          state: "done",
          detail: `Registered (${String(input.registration.data?.status)}).`,
          action: link,
        });
      } else if (m === "draft") {
        steps.push({
          id: "registration",
          title: "Squad registration",
          state: "current",
          detail: "Included in a draft registration. Submit it from the squad page to make it count.",
          action: link,
        });
      } else {
        steps.push({
          id: "registration",
          title: "Squad registration",
          state: completed ? "current" : "pending",
          detail: completed
            ? "The contract is complete but the registration does not list this player. Sync the squad registration."
            : "Available once the player has joined your club.",
          action: completed ? link : undefined,
        });
      }
    }
  }

  return steps;
}
