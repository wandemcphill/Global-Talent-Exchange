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
    expect(pose2.position[1]).toBeCloseTo(16, 0); // Closer gantry so a player reads at broadcast size
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

  test("evaluates shot grammar with penalty-box entry, attack push, and cut cooldowns", () => {
    // Final-third attack push when ball enters attacking third with forward velocity
    const poseAttack = director.update(0.5, "broadcast", [36, 0, 4], null, {
      ballVelocity3D: [8, 0, 0],
      shotProbability: 0.2,
      cutCooldownSec: 2.0,
    });
    expect(poseAttack.activeShotPreset).toBe("attack_push");
    expect(poseAttack.liveMode).toBe("action");
    expect(director.getCutCooldownRemainingSec()).toBeGreaterThan(0);

    // While cooldown is active, ordinary midfield coordinates do not cause a whip-cut back to broadcast
    const poseHeld = director.update(0.2, "broadcast", [10, 0, 0], null, {
      ballVelocity3D: [-2, 0, 0],
      shotProbability: 0.05,
    });
    expect(poseHeld.activeShotPreset).toBe("attack_push");

    // High-priority dramatic events (e.g. goal or high xG shot) cut immediately regardless of cooldown
    const poseGoal = director.update(0.5, "broadcast", [48, 1.2, 0], [46, 0, 2], {
      eventType: "goal",
    });
    expect(poseGoal.activeShotPreset).toBe("goal_celebration");
    expect(poseGoal.liveMode).toBe("goal_replay");
  });

  test("leads ball in direction of travel (0.5-1.0s) and frames support runners + defensive line", () => {
    const dirStatic = new CameraDirector();
    const dirLeading = new CameraDirector();

    const staticPose = dirStatic.update(0.8, "broadcast", [10, 0, 0], null, {
      ballVelocity3D: [0, 0, 0],
      leadTimeSec: 0.8,
    });
    const leadingPose = dirLeading.update(0.8, "broadcast", [10, 0, 0], null, {
      ballVelocity3D: [14, 0, 0],
      supportRunnerPositions3D: [
        [22, 0, -6],
        [24, 0, 8],
      ],
      defensiveLineX: 30,
      leadTimeSec: 0.8,
    });

    expect(leadingPose.target[0]).toBeGreaterThan(staticPose.target[0]);
    expect(leadingPose.position[0]).toBeGreaterThan(staticPose.position[0]);
  });

  test("supports the four polished live camera modes and restricts shake to dramatic events", () => {
    director.setLiveCameraMode("tactical");
    expect(director.getLiveCameraMode()).toBe("tactical");
    expect(director.getManualMode()).toBe("tactical_high");

    director.setLiveCameraMode("action");
    expect(director.getManualMode()).toBe("closeup_action");

    director.setLiveCameraMode("goal_replay");
    expect(director.getManualMode()).toBe("replay_cam");

    director.setLiveCameraMode("broadcast");
    expect(director.getManualMode()).toBe("director_auto");

    // Ordinary passes/dribbles/tackles never trigger camera shake
    expect(director.triggerCameraShake("pass", 0.5)).toBe(false);
    expect(director.triggerCameraShake("dribble", 0.5)).toBe(false);
    expect(director.triggerCameraShake("tackle", 0.5)).toBe(false);
    expect(director.getShakeIntensity()).toBe(0);

    // Goals, woodwork, major saves, and red cards trigger camera shake
    expect(director.triggerCameraShake("woodwork", 0.5)).toBe(true);
    expect(director.getShakeIntensity()).toBeGreaterThan(0);
  });
});
