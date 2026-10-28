import {
  canonicalPlayerId,
  describeOffer,
  describeNegotiation,
  isNegotiationActionable,
  registrationMembership,
  buildJourney,
  readJourneyParams,
  journeyLinks,
  Source,
} from "./playerJourney";

describe("playerJourney unit suite", () => {
  describe("canonicalPlayerId extraction", () => {
    test("extracts canonical ID from top-level or nested player objects", () => {
      expect(canonicalPlayerId({ id: "p-123" })).toBe("p-123");
      expect(canonicalPlayerId({ player_id: "p-456" })).toBe("p-456");
      expect(canonicalPlayerId({ player: { id: "p-789" } })).toBe("p-789");
      expect(canonicalPlayerId({ player: { player_id: "p-abc" } })).toBe("p-abc");
      expect(canonicalPlayerId(null)).toBeNull();
      expect(canonicalPlayerId({})).toBeNull();
      expect(canonicalPlayerId({ id: "   " })).toBeNull();
    });
  });

  describe("URL journey query parser", () => {
    test("extracts player and lane from search params", () => {
      expect(readJourneyParams("?player=reg-001&lane=negotiations")).toEqual({
        player: "reg-001",
        lane: "negotiations",
      });
      expect(readJourneyParams("?player=reg-002")).toEqual({
        player: "reg-002",
        lane: null,
      });
      expect(readJourneyParams("?lane=invalid_lane")).toEqual({
        player: null,
        lane: null,
      });
    });

    test("generates canonical journey links without altering the player id", () => {
      expect(journeyLinks.dossier("p:test/123")).toBe("/app/regen-world?player=p%3Atest%2F123");
      expect(journeyLinks.transferHub("negotiations", "p:test/123")).toBe(
        "/app/transfer-hub?lane=negotiations&player=p%3Atest%2F123",
      );
      expect(journeyLinks.squad("p:test/123")).toBe("/app/squad?player=p%3Atest%2F123");
    });
  });

  describe("intermediate offer state representation", () => {
    test("faithfully represents draft, open, countered, accepted, rejected, cancelled, and expired states", () => {
      expect(describeOffer("draft").label).toBe("Draft");
      expect(describeOffer("open").label).toBe("Offered");
      expect(describeOffer("open").tone).toBe("gold");

      expect(describeOffer("countered").label).toBe("Countered");
      expect(describeOffer("countered").tone).toBe("cyan");

      expect(describeOffer("accepted").label).toBe("Offer accepted");
      expect(describeOffer("accepted").tone).toBe("emerald");
      expect(describeOffer("accepted").explanation).toContain("contract terms are a separate step");

      expect(describeOffer("rejected").label).toBe("Rejected");
      expect(describeOffer("rejected").tone).toBe("red");

      expect(describeOffer("expired").label).toBe("Expired");
      expect(describeOffer("expired").tone).toBe("red");
    });
  });

  describe("negotiation decision loop representation", () => {
    test("honestly represents awaiting_contract_offer, player_delayed, counter_offer, coach_blocked, completed", () => {
      expect(describeNegotiation("awaiting_contract_offer").label).toBe("Awaiting contract terms");
      expect(describeNegotiation("awaiting_contract_offer").tone).toBe("gold");

      const delayed = describeNegotiation("player_delayed", { decisionDueAt: "2026-11-01T12:00:00Z" });
      expect(delayed.label).toBe("Awaiting player decision");
      expect(delayed.explanation).toContain("Decision due");

      expect(describeNegotiation("counter_offer").label).toBe("Agent counter-offer");
      expect(describeNegotiation("counter_offer").tone).toBe("cyan");

      expect(describeNegotiation("coach_blocked").label).toBe("Blocked by coach");
      expect(describeNegotiation("coach_blocked").tone).toBe("red");

      expect(describeNegotiation("completed").label).toBe("Completed");
      expect(describeNegotiation("completed").tone).toBe("emerald");
    });

    test("isNegotiationActionable flags only active decision states", () => {
      expect(isNegotiationActionable("awaiting_contract_offer")).toBe(true);
      expect(isNegotiationActionable("player_delayed")).toBe(true);
      expect(isNegotiationActionable("counter_offer")).toBe(true);
      expect(isNegotiationActionable("coach_blocked")).toBe(false);
      expect(isNegotiationActionable("completed")).toBe(false);
      expect(isNegotiationActionable("rejected")).toBe(false);
    });
  });

  describe("squad registration membership verification", () => {
    test("does not mark registered until verified by backend registration object", () => {
      expect(registrationMembership(null, "p-1")).toBe("no_registration");
      expect(registrationMembership({ status: "draft", players: [] }, "p-1")).toBe("not_included");
      expect(
        registrationMembership(
          { status: "draft", players: [{ player_id: "p-1", name: "Star" }] },
          "p-1",
        ),
      ).toBe("draft");
      expect(
        registrationMembership(
          { status: "submitted", players: [{ player_id: "p-1", name: "Star" }] },
          "p-1",
        ),
      ).toBe("registered");
      expect(
        registrationMembership(
          { status: "locked", players: [{ player_id: "p-1", name: "Star" }] },
          "p-1",
        ),
      ).toBe("registered");
    });
  });

  describe("buildJourney integration step progression", () => {
    const okSource = <T>(data: T): Source<T> => ({ status: "ok", data });

    test("builds full journey without inventing a transfer or premature registration", () => {
      const playerId = "regen-999";
      const clubId = "my-club";

      const journey = buildJourney({
        playerId,
        clubId,
        report: okSource({ summary_text: "Elite prospect with wonderkid ceiling." }),
        watchlist: okSource([{ player_id: playerId, source: "scouting_dossier" }]),
        listings: okSource([{ id: "list-1", player_id: playerId, base_price: 50000, status: "open" }]),
        offers: okSource([]),
        negotiations: okSource([]),
        registration: okSource({ status: "submitted", players: [] }),
      });

      expect(journey).toHaveLength(6);

      // 1. Report is done
      expect(journey[0].id).toBe("report");
      expect(journey[0].state).toBe("done");

      // 2. Watchlist is done
      expect(journey[1].id).toBe("watchlist");
      expect(journey[1].state).toBe("done");

      // 3. Open listing is done
      expect(journey[2].id).toBe("listing");
      expect(journey[2].state).toBe("done");

      // 4. Offer is current (ready to make offer)
      expect(journey[3].id).toBe("offer");
      expect(journey[3].state).toBe("current");

      // 5. Contract is pending
      expect(journey[4].id).toBe("contract");
      expect(journey[4].state).toBe("pending");

      // 6. Registration is pending because player is not in registration.players!
      expect(journey[5].id).toBe("registration");
      expect(journey[5].state).toBe("pending");
    });

    test("marks registration done ONLY when backend confirms player in registration.players with submitted/locked status", () => {
      const playerId = "regen-999";
      const clubId = "my-club";

      const journey = buildJourney({
        playerId,
        clubId,
        report: okSource(null),
        watchlist: okSource([]),
        listings: okSource([]),
        offers: okSource([]),
        negotiations: okSource([
          {
            id: "neg-1",
            player_id: playerId,
            bidder_club_id: clubId,
            selling_club_id: "other-club",
            status: "completed",
          },
        ]),
        registration: okSource({
          status: "locked",
          players: [{ player_id: playerId, name: "Regen Star" }],
        }),
      });

      const regStep = journey.find((s) => s.id === "registration");
      expect(regStep?.state).toBe("done");
      expect(regStep?.detail).toContain("Registered (locked)");
    });

    test("handles permissions and error states actionably", () => {
      const playerId = "regen-999";
      const clubId = "my-club";

      const journey = buildJourney({
        playerId,
        clubId,
        report: { status: "error", httpStatus: 403, error: "Forbidden" },
        watchlist: okSource([]),
        listings: okSource([]),
        offers: okSource([]),
        negotiations: okSource([]),
        registration: okSource(null),
      });

      const reportStep = journey.find((s) => s.id === "report");
      expect(reportStep?.state).toBe("error");
      expect(reportStep?.detail).toContain("do not have permission");
    });
  });
});
