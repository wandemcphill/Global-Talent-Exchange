declare const describe: any;
declare const test: any;
declare const expect: any;

import {
  buildLineupPayload,
  lineupRoleLabels,
  lineupFormationRows,
  normalizeLineupPlan,
  normalizeLineupSquad,
} from "./lineupModel";

describe("React club lineup model", () => {
  test("normalizes the authoritative squad-player shape and supported aliases", () => {
    const players = normalizeLineupSquad({
      items: [
        { player_id: "p-1", player_name: "Keeper", position: "GK", rating: 78 },
        { id: "p-2", name: "Centre Back", normalized_position: "CB", overall: "81" },
        { name: "Missing identifier" },
      ],
    });

    expect(players).toHaveLength(2);
    expect(players[0].player_id).toBe("p-1");
    expect(players[0].player_name).toBe("Keeper");
    expect(players[1].player_id).toBe("p-2");
    expect(players[1].position).toBe("CB");
    expect(players[1].rating).toBe(81);
  });

  test("falls back to a supported formation and prepares eleven position labels", () => {
    const plan = normalizeLineupPlan({
      formation: "not-a-formation",
      starter_player_ids: ["p-1"],
      bench_player_ids: ["p-2"],
    });

    expect(plan.formation).toBe("4-3-3");
    expect(lineupRoleLabels("4-2-3-1")).toHaveLength(11);
    expect(lineupRoleLabels("4-2-3-1")[0]).toBe("Goalkeeper");
    expect(lineupRoleLabels("4-2-3-1")[10]).toBe("Forward 1");
    expect(lineupFormationRows("4-2-3-1").map((row) => row.length)).toEqual([1, 4, 2, 3, 1]);
  });

  test("builds a save payload without duplicate starters or bench overlap", () => {
    const payload = buildLineupPayload(
      "4-4-2",
      ["gk", "def-1", "def-1", "mid-1", "", "striker"],
      ["bench-1", "gk", "bench-1", "unknown"],
      ["gk", "def-1", "mid-1", "striker", "bench-1"],
    );

    expect(payload.formation).toBe("4-4-2");
    expect(payload.starter_player_ids).toEqual(["gk", "def-1", "mid-1", "striker"]);
    expect(payload.bench_player_ids).toEqual(["bench-1"]);
  });
});
