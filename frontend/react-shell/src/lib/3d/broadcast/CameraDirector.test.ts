import { CameraDirector } from "./CameraDirector";

describe("CameraDirector", () => {
  let director: CameraDirector;

  beforeEach(() => {
    director = new CameraDirector();
  });

  test("initializes with a valid broadcast pose", () => {
    const pose = director.getPose();
    expect(pose.position).toHaveLength(3);
    expect(pose.target).toHaveLength(3);
    expect(pose.fov).toBeGreaterThan(20);
  });

  test("smoothly responds to BROADCAST preset tracking ball", () => {
    // Initial update starts moving towards broadcast height
    const pose1 = director.update(0.016, "broadcast", [0, 0, 0]);
    expect(pose1.position[1]).toBeGreaterThanOrEqual(28);
    expect(pose1.position[1]).toBeLessThanOrEqual(34);

    // After 2 seconds of tracking, camera settles near broadcast height
    const pose2 = director.update(2.0, "broadcast", [35, 0, 10]);
    expect(pose2.position[1]).toBeCloseTo(30, 0); // Elevation around 30m
    // Sideline camera should have moved positive along X following ball at X: 35
    expect(pose2.position[0]).toBeGreaterThan(pose1.position[0]);
  });

  test("implements all 6 canonical presets without errors", () => {
    const presets = [
      "broadcast",
      "attack_push",
      "box_zoom",
      "goal_celebration",
      "assistant_flag",
      "var_replay",
    ];

    for (const preset of presets) {
      const pose = director.update(0.1, preset, [20, 1, -5], [45, 0, 0]);
      expect(pose.position[1]).toBeGreaterThan(0); // Camera is above pitch
      expect(pose.fov).toBeGreaterThanOrEqual(25);
    }
  });

  test("honors manual camera mode override", () => {
    director.setManualMode("tactical_high");
    expect(director.getManualMode()).toBe("tactical_high");

    const pose = director.update(1.0, "broadcast", [10, 0, 0]);
    // High tactical overhead position
    expect(pose.position[1]).toBeGreaterThan(50);

    // Dugout touchline view
    director.setManualMode("dugout_cam");
    const poseDugout = director.update(1.0, "broadcast", [0, 0, 0]);
    expect(poseDugout.position[1]).toBeLessThan(10);

    // Tunnel walkout view
    director.setManualMode("tunnel_walkout");
    const poseTunnel = director.update(1.0, "broadcast", [0, 0, 0]);
    expect(poseTunnel.position[2]).toBeGreaterThan(35);
  });
});
