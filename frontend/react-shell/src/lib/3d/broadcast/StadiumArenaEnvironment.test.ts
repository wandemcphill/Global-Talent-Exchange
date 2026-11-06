import * as THREE from "three";
import { StadiumArenaEnvironment } from "./StadiumArenaEnvironment";
import { FIFA_PITCH_DIMENSIONS } from "./matchCoordinates";

describe("StadiumArenaEnvironment", () => {
  let scene: THREE.Scene;

  beforeEach(() => {
    scene = new THREE.Scene();
  });

  afterEach(() => {
    scene.clear();
  });

  test("initializes stadium environment with all 5 core subsystems", () => {
    const arena = new StadiumArenaEnvironment(scene, {
      qualityTier: "high",
      stadiumName: "GTEX National Arena",
      attendancePct: 95,
      homeTeam: {
        team_id: "home-1",
        team_name: "Apex Lagos",
        short_name: "APX",
        formation: "4-3-3",
        primary_color: "#00E676",
        secondary_color: "#1B5E20",
        accent_color: "#FFFFFF",
        goalkeeper_color: "#FFD600",
      },
      awayTeam: {
        team_id: "away-1",
        team_name: "Nairobi Stars",
        short_name: "NST",
        formation: "4-4-2",
        primary_color: "#3B82F6",
        secondary_color: "#1E40AF",
        accent_color: "#FFFFFF",
        goalkeeper_color: "#EC4899",
      },
    });

    expect(arena.group).toBeDefined();
    expect(arena.pitchGroup.children.length).toBeGreaterThan(10);
    expect(arena.stadiumGroup.children.length).toBeGreaterThan(4);
    expect(arena.lightingGroup.children.length).toBeGreaterThan(4);
    expect(arena.adBoardsGroup.children.length).toBeGreaterThan(2);
    expect(arena.crowdGroup.children.length).toBeGreaterThan(2);

    // Verify scene contains the stadium root group
    expect(scene.children).toContain(arena.group);

    // Verify update tick runs cleanly
    expect(() => arena.update(0.016)).not.toThrow();

    // Verify clean disposal
    arena.dispose();
    expect(arena.group.children.length).toBe(0);
  });

  test("procedurally constructs realistic FIFA pitch markings", () => {
    const arena = new StadiumArenaEnvironment(scene, { qualityTier: "medium" });

    // Find the pitch plane mesh
    const pitchPlane = arena.pitchGroup.children.find(
      (c) => c instanceof THREE.Mesh && (c.geometry as THREE.PlaneGeometry).parameters?.width === FIFA_PITCH_DIMENSIONS.length
    );
    expect(pitchPlane).toBeDefined();

    // Check goals exist
    const goals = arena.pitchGroup.children.filter(
      (c) => c instanceof THREE.Group && c.children.length >= 4
    );
    expect(goals.length).toBe(2); // Left goal and Right goal

    arena.dispose();
  });

  test("constructs 4 grandstands (West, East, North Kop, South Away)", () => {
    const arena = new StadiumArenaEnvironment(scene, { qualityTier: "high" });

    // 4 grandstands + 2 dugouts + 1 tunnel + 1 official desk + 2 tech boxes
    expect(arena.stadiumGroup.children.length).toBeGreaterThanOrEqual(8);

    arena.dispose();
  });
});
