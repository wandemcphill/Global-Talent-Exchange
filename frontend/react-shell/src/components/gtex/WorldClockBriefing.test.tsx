declare const describe: any;
declare const test: any;
declare const expect: any;

import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

jest.mock("react-router-dom", () => ({
  Link: ({ to, children, ...props }: any) => <a href={to} {...props}>{children}</a>,
}));

jest.mock("@/lib/api", () => ({
  api: { get: () => Promise.resolve({ data: {} }) },
  errMsg: (e: any) => String(e),
}));

import { WorldClockView } from "./WorldClockCard";
import { OwnerBriefingView } from "./OwnerBriefingPanel";

const clock = {
  clockId: "global",
  worldTime: "2031-03-14T09:05:00+00:00",
  worldDate: "2031-03-14",
  isPaused: false,
  progressionRate: 6,
  virtualMonthsPerSeason: 12,
};
const html = (el: React.ReactElement) => renderToStaticMarkup(el);

describe("WorldClockView", () => {
  test("renders server date, time, running status, rate and season length", () => {
    const out = html(<WorldClockView state={{ status: "ready", clock }} />);
    expect(out).toContain("Fri, 14 March 2031");
    expect(out).toContain("09:05 UTC");
    expect(out).toContain("Running");
    expect(out).toContain("6x");
    expect(out).toContain("12 virtual months");
    expect(out).toContain('dateTime="2031-03-14"');
  });

  test("shows paused state", () => {
    expect(html(<WorldClockView state={{ status: "ready", clock: { ...clock, isPaused: true } }} />)).toContain("Paused");
  });

  test("never guesses the current season label", () => {
    const out = html(<WorldClockView state={{ status: "ready", clock }} />);
    expect(out).toContain("awaiting the approved season calendar");
    expect(out).not.toMatch(/Season\s+20\d\d|20\d\d\/\d\d/);
  });

  test("loading and error states are announced accessibly and show no time", () => {
    const loading = html(<WorldClockView state={{ status: "loading" }} />);
    expect(loading).toContain('role="status"');
    expect(loading).toContain('aria-busy="true"');
    const err = html(<WorldClockView state={{ status: "error", onRetry: () => {} }} />);
    expect(err).toContain('role="alert"');
    expect(err).toContain("Retry");
    expect(err).not.toContain("UTC");
  });

  test("stale refresh failure keeps last server snapshot with a notice", () => {
    const out = html(<WorldClockView state={{ status: "ready", clock, stale: true }} />);
    expect(out).toContain("world-clock-stale");
    expect(out).toContain("09:05 UTC");
  });
});

describe("OwnerBriefingView", () => {
  test("unavailable state invents no stories", () => {
    const out = html(<OwnerBriefingView state={{ status: "unavailable" }} />);
    expect(out).toContain("not available yet");
    expect(out).not.toContain("owner-briefing-card");
  });

  test("loading, error and empty states", () => {
    expect(html(<OwnerBriefingView state={{ status: "loading" }} />)).toContain("owner-briefing-loading");
    const err = html(<OwnerBriefingView state={{ status: "error" }} onRetry={() => {}} />);
    expect(err).toContain('role="alert"');
    expect(err).toContain("Retry");
    expect(html(<OwnerBriefingView state={{ status: "empty", worldDate: "2031-03-14" }} />)).toContain("Nothing to report");
  });

  test("ready cards link to decision, club history and match result", () => {
    const briefing = {
      briefingId: "b1",
      clubId: "c1",
      worldDate: "2031-03-14",
      rejectedEventCount: 1,
      explanation: "Prose only.",
      events: [
        { eventId: "e1", headline: "Offer received", occurredAt: "2031-03-14T08:00:00Z", target: { type: "decision" as const, inboxItemId: "i1" } },
        { eventId: "e2", headline: "Academy milestone", occurredAt: "2031-03-14T08:10:00Z", target: { type: "club_history" as const, clubId: "c1" } },
        { eventId: "e3", headline: "Won 2-1", occurredAt: "2031-03-13T20:00:00Z", target: { type: "match_result" as const, matchId: "m9" } },
        { eventId: "e4", headline: "No link", occurredAt: "2031-03-13T21:00:00Z", target: null },
      ],
    };
    const out = html(<OwnerBriefingView state={{ status: "ready", briefing, stale: true }} />);
    expect(out).toContain('href="/app/inbox"');
    expect(out).toContain('href="/app/clubs/c1/story"');
    expect(out).toContain('href="/app/match/m9"');
    expect((out.match(/owner-briefing-card/g) || []).length).toBe(4);
    expect(out).toContain("owner-briefing-stale");
    expect(out).toContain("owner-briefing-rejected");
    expect(out).toContain("explanatory only");
  });
});
