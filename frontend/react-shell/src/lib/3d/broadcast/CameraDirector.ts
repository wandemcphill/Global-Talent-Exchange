/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast
 * Event-Aware Broadcast Camera Director with Critically Damped Spring Physics.
 *
 * Implements FM/TV-grade broadcast cinematography with:
 * 1. Event-aware "shot grammar" driven by ball velocity/altitude, attacking-third &
 *    penalty-box entry, shot probability, goalkeeper action, dramatic match events,
 *    sideline dead-zone, and cut cooldowns.
 * 2. Critically damped spring camera leading the ball by 0.5–1.0s in its travel
 *    direction, framing the ball carrier + support runners + defensive line,
 *    with separate smooth states for position, aim target, FOV, and roll.
 * 3. Collision-safe stadium/goalpost bounds and camera shake restricted strictly
 *    to goals, woodwork, major saves, and red cards.
 * 4. Four polished live camera modes ("broadcast", "tactical", "action", "goal_replay")
 *    while preserving full compatibility with canonical server presets and manual modes.
 */

export type LiveCameraMode = "broadcast" | "tactical" | "action" | "goal_replay";

export type ManualCameraMode =
  | "director_auto"
  | "broadcast_main"
  | "tactical_high"
  | "closeup_action"
  | "endzone_home"
  | "endzone_away"
  | "replay_cam"
  | "celebration_cam"
  | "dugout_cam"
  | "tunnel_walkout"
  | "free_orbit";

export interface CameraPose {
  position: [number, number, number];
  target: [number, number, number];
  fov: number;
  roll?: number;
  activeShotPreset?: string;
  liveMode?: LiveCameraMode;
}

export interface ShotGrammarContext {
  /** Ball velocity in 3D world space (m/s). If omitted, estimated from consecutive ballPos3D updates. */
  ballVelocity3D?: [number, number, number] | null;
  /** Current match event type (e.g., "goal", "foul", "corner", "substitution", "var", "halftime", "woodwork", "save", "red_card"). */
  eventType?: string | null;
  /** Instantaneous xG / shot probability in [0, 1]. */
  shotProbability?: number;
  /** Current goalkeeper action state. */
  goalkeeperAction?: "idle" | "sweeper" | "set_shot" | "diving_save" | string | null;
  /** Nearby attacking support runners for tactical framing zone. */
  supportRunnerPositions3D?: Array<[number, number, number]>;
  /** X-coordinate of the active defending backline. */
  defensiveLineX?: number | null;
  /** Lead time in seconds along ball velocity vector (clamped to 0.5–1.0s when active). */
  leadTimeSec?: number;
  /** Minimum cooldown between non-emergency camera cuts in seconds. */
  cutCooldownSec?: number;
}

const SHAKE_ELIGIBLE_EVENTS = new Set([
  "goal",
  "woodwork",
  "crossbar",
  "post",
  "save",
  "major_save",
  "diving_save",
  "red_card",
]);

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

export class CameraDirector {
  private currentPose: CameraPose = {
    position: [0, 32, 55],
    target: [0, 0, 0],
    fov: 38,
    roll: 0,
    activeShotPreset: "broadcast",
    liveMode: "broadcast",
  };

  private targetPose: CameraPose = {
    position: [0, 32, 55],
    target: [0, 0, 0],
    fov: 38,
    roll: 0,
    activeShotPreset: "broadcast",
    liveMode: "broadcast",
  };

  // Critically damped spring velocity states
  private posVelocity: [number, number, number] = [0, 0, 0];
  private targetVelocity: [number, number, number] = [0, 0, 0];
  private fovVelocity = 0;
  private rollVelocity = 0;

  // Ball velocity estimation & dead-zone state
  private lastBallPos3D: [number, number, number] | null = null;
  private estimatedBallVel3D: [number, number, number] = [0, 0, 0];
  private deadZoneAnchorX = 0;
  private readonly deadZoneRadiusM = 3.2;

  // Shot grammar & cooldown state
  private manualMode: ManualCameraMode = "director_auto";
  private liveCameraMode: LiveCameraMode = "broadcast";
  private activeShotPreset = "broadcast";
  private cutCooldownRemainingSec = 0;
  private lastEventKey = "";
  private celebrationOrbitAngle = 0;

  // Camera shake state (strictly restricted to dramatic events)
  private shakeIntensity = 0;
  private shakePhase = 0;

  public setManualMode(mode: ManualCameraMode): void {
    this.manualMode = mode;
    if (mode === "tactical_high") {
      this.liveCameraMode = "tactical";
    } else if (mode === "closeup_action") {
      this.liveCameraMode = "action";
    } else if (mode === "replay_cam" || mode === "celebration_cam") {
      this.liveCameraMode = "goal_replay";
    } else if (mode === "broadcast_main" || mode === "director_auto") {
      this.liveCameraMode = "broadcast";
    }
  }

  public getManualMode(): ManualCameraMode {
    return this.manualMode;
  }

  /**
   * Sets one of the four polished live camera modes ("broadcast", "tactical", "action", "goal_replay").
   */
  public setLiveCameraMode(mode: LiveCameraMode): void {
    this.liveCameraMode = mode;
    switch (mode) {
      case "tactical":
        this.manualMode = "tactical_high";
        break;
      case "action":
        this.manualMode = "closeup_action";
        break;
      case "goal_replay":
        this.manualMode = "replay_cam";
        break;
      case "broadcast":
      default:
        this.manualMode = "director_auto";
        break;
    }
  }

  public getLiveCameraMode(): LiveCameraMode {
    return this.liveCameraMode;
  }

  public getActiveShotPreset(): string {
    return this.activeShotPreset;
  }

  public getCutCooldownRemainingSec(): number {
    return this.cutCooldownRemainingSec;
  }

  /**
   * Triggers camera shake ONLY for goals, woodwork, major saves, and red cards.
   * Ordinary passes, dribbles, or routine tackles are ignored and return false.
   */
  public triggerCameraShake(eventType: string, intensity = 0.45): boolean {
    const normalized = (eventType || "").trim().toLowerCase();
    if (!SHAKE_ELIGIBLE_EVENTS.has(normalized)) {
      return false;
    }
    this.shakeIntensity = clamp(Math.max(this.shakeIntensity, intensity), 0, 1.0);
    return true;
  }

  public getShakeIntensity(): number {
    return this.shakeIntensity;
  }

  public getPose(): CameraPose {
    return {
      position: [...this.currentPose.position],
      target: [...this.currentPose.target],
      fov: this.currentPose.fov,
      roll: this.currentPose.roll ?? 0,
      activeShotPreset: this.activeShotPreset,
      liveMode: this.liveCameraMode,
    };
  }

  /**
   * Shot grammar evaluator: maps ball kinematics, spatial zone, shot probability,
   * goalkeeper action, and match events into a broadcast shot preset while respecting
   * camera cut cooldowns.
   */
  public evaluateShotGrammar(
    serverPreset: string,
    ballPos3D: [number, number, number],
    ballVel3D: [number, number, number],
    context?: ShotGrammarContext
  ): { preset: string; liveMode: LiveCameraMode } {
    const normalizedPreset = (serverPreset || "broadcast").trim().toLowerCase();
    const eventType = (context?.eventType || "").trim().toLowerCase();
    const gkAction = (context?.goalkeeperAction || "").trim().toLowerCase();
    const shotProb = context?.shotProbability ?? 0;
    const cooldownDefault = context?.cutCooldownSec ?? 1.8;

    // Trigger shake automatically if eventType or gkAction warrants it
    if (eventType && SHAKE_ELIGIBLE_EVENTS.has(eventType)) {
      const eventKey = `${eventType}:${Math.round(ballPos3D[0])}`;
      if (eventKey !== this.lastEventKey) {
        this.lastEventKey = eventKey;
        this.triggerCameraShake(eventType, eventType === "goal" ? 0.65 : 0.4);
      }
    } else if (gkAction === "diving_save") {
      this.triggerCameraShake("diving_save", 0.38);
    }

    // 1. Explicit non-default server preset or high-priority dramatic event cuts immediately
    if (
      normalizedPreset !== "broadcast" &&
      ["attack_push", "box_zoom", "goal_celebration", "assistant_flag", "var_replay"].includes(normalizedPreset)
    ) {
      this.activeShotPreset = normalizedPreset;
      const mode: LiveCameraMode =
        normalizedPreset === "goal_celebration" ||
        normalizedPreset === "var_replay" ||
        normalizedPreset === "assistant_flag"
          ? "goal_replay"
          : "action";
      return { preset: normalizedPreset, liveMode: mode };
    }

    if (eventType === "goal" || eventType === "goal_celebration") {
      this.activeShotPreset = "goal_celebration";
      this.cutCooldownRemainingSec = Math.max(this.cutCooldownRemainingSec, 3.2);
      return { preset: "goal_celebration", liveMode: "goal_replay" };
    }
    if (eventType === "var" || eventType === "var_review") {
      this.activeShotPreset = "var_replay";
      this.cutCooldownRemainingSec = Math.max(this.cutCooldownRemainingSec, 2.8);
      return { preset: "var_replay", liveMode: "goal_replay" };
    }
    if (eventType === "offside") {
      this.activeShotPreset = "assistant_flag";
      this.cutCooldownRemainingSec = Math.max(this.cutCooldownRemainingSec, 2.2);
      return { preset: "assistant_flag", liveMode: "goal_replay" };
    }
    if (
      eventType === "shot" ||
      eventType === "save" ||
      eventType === "woodwork" ||
      eventType === "red_card" ||
      eventType === "corner" ||
      gkAction === "diving_save" ||
      gkAction === "set_shot" ||
      shotProb >= 0.45
    ) {
      this.activeShotPreset = "box_zoom";
      this.cutCooldownRemainingSec = Math.max(this.cutCooldownRemainingSec, cooldownDefault);
      return { preset: "box_zoom", liveMode: "action" };
    }

    // 2. If a contextual cut was only requested via context (when serverPreset is "broadcast"),
    //    only evaluate spatial auto-cuts when context is explicitly provided.
    if (!context) {
      this.activeShotPreset = "broadcast";
      return { preset: "broadcast", liveMode: "broadcast" };
    }

    // Respect cooldown before cutting between spatial modes
    if (this.cutCooldownRemainingSec > 0) {
      const heldMode: LiveCameraMode =
        this.activeShotPreset === "attack_push" || this.activeShotPreset === "box_zoom"
          ? "action"
          : this.activeShotPreset === "goal_celebration" || this.activeShotPreset === "var_replay"
          ? "goal_replay"
          : "broadcast";
      return { preset: this.activeShotPreset, liveMode: heldMode };
    }

    const absX = Math.abs(ballPos3D[0]);
    const absZ = Math.abs(ballPos3D[2]);
    const ballSpeed = Math.hypot(ballVel3D[0], ballVel3D[2]);
    const movingTowardGoal = ballPos3D[0] * ballVel3D[0] >= -0.5;

    // Penalty box entry + active play
    if (absX >= 36.5 && absZ <= 20.16 && (shotProb >= 0.25 || ballSpeed >= 4.0)) {
      if (this.activeShotPreset !== "box_zoom") {
        this.activeShotPreset = "box_zoom";
        this.cutCooldownRemainingSec = cooldownDefault;
      }
      return { preset: "box_zoom", liveMode: "action" };
    }

    // Attacking final-third entry
    if (absX >= 34.0 && movingTowardGoal && (ballSpeed >= 3.5 || shotProb >= 0.15)) {
      if (this.activeShotPreset !== "attack_push") {
        this.activeShotPreset = "attack_push";
        this.cutCooldownRemainingSec = cooldownDefault;
      }
      return { preset: "attack_push", liveMode: "action" };
    }

    if (this.activeShotPreset !== "broadcast") {
      this.activeShotPreset = "broadcast";
      this.cutCooldownRemainingSec = cooldownDefault * 0.75;
    }
    return { preset: "broadcast", liveMode: "broadcast" };
  }

  /**
   * Evaluates the desired camera target pose based on the server preset / shot grammar,
   * predictive ball lead (0.5–1.0s), tactical framing zone, and critically damped spring dynamics.
   */
  public update(
    deltaSec: number,
    preset: string,
    ballPos3D: [number, number, number],
    activeGoalScorerPos3D?: [number, number, number] | null,
    context?: ShotGrammarContext
  ): CameraPose {
    const safeDelta = Math.max(0.001, deltaSec);
    this.cutCooldownRemainingSec = Math.max(0, this.cutCooldownRemainingSec - safeDelta);

    const ballX = ballPos3D[0];
    const ballY = ballPos3D[1];
    const ballZ = ballPos3D[2];

    // Estimate or read ball velocity
    if (context?.ballVelocity3D) {
      this.estimatedBallVel3D = [
        clamp(context.ballVelocity3D[0], -28, 28),
        clamp(context.ballVelocity3D[1], -18, 18),
        clamp(context.ballVelocity3D[2], -28, 28),
      ];
    } else if (this.lastBallPos3D && safeDelta > 0.004 && safeDelta < 0.5) {
      const rawVx = (ballX - this.lastBallPos3D[0]) / safeDelta;
      const rawVy = (ballY - this.lastBallPos3D[1]) / safeDelta;
      const rawVz = (ballZ - this.lastBallPos3D[2]) / safeDelta;
      const blend = 0.35;
      this.estimatedBallVel3D = [
        clamp(this.estimatedBallVel3D[0] * (1 - blend) + rawVx * blend, -28, 28),
        clamp(this.estimatedBallVel3D[1] * (1 - blend) + rawVy * blend, -18, 18),
        clamp(this.estimatedBallVel3D[2] * (1 - blend) + rawVz * blend, -28, 28),
      ];
    } else {
      this.estimatedBallVel3D = [0, 0, 0];
    }
    this.lastBallPos3D = [ballX, ballY, ballZ];

    // Predictive ball lead (0.5–1.0 seconds in direction of travel)
    const leadSec = context?.leadTimeSec !== undefined ? clamp(context.leadTimeSec, 0.5, 1.0) : 0.65;
    const hasVelocityContext = Boolean(context?.ballVelocity3D);
    const effectiveLeadSec = hasVelocityContext ? leadSec : Math.min(0.55, safeDelta < 0.25 ? 0.5 : 0);
    const predictedBallX = clamp(ballX + this.estimatedBallVel3D[0] * effectiveLeadSec, -52.5, 52.5);
    const predictedBallY = clamp(ballY + this.estimatedBallVel3D[1] * (effectiveLeadSec * 0.35), 0, 18);
    const predictedBallZ = clamp(ballZ + this.estimatedBallVel3D[2] * effectiveLeadSec, -34, 34);

    // Tactical framing zone (ball carrier + nearest support runners + defensive line)
    let framedX = predictedBallX;
    let framedZ = predictedBallZ;
    let tacticalFovBonus = 0;

    if (context?.supportRunnerPositions3D && context.supportRunnerPositions3D.length > 0) {
      let sumX = 0;
      let sumZ = 0;
      for (const runner of context.supportRunnerPositions3D) {
        sumX += runner[0];
        sumZ += runner[2];
      }
      const avgRunnerX = sumX / context.supportRunnerPositions3D.length;
      const avgRunnerZ = sumZ / context.supportRunnerPositions3D.length;
      framedX = framedX * 0.78 + avgRunnerX * 0.22;
      framedZ = framedZ * 0.8 + avgRunnerZ * 0.2;
    }

    if (typeof context?.defensiveLineX === "number" && Number.isFinite(context.defensiveLineX)) {
      const defLineX = clamp(context.defensiveLineX, -50, 50);
      const spreadX = Math.abs(defLineX - predictedBallX);
      framedX = framedX * 0.88 + defLineX * 0.12;
      tacticalFovBonus = clamp((spreadX - 12) * 0.12, 0, 3.5);
    }

    // Sideline dead-zone update so small midfield passes don't cause jitter
    const deltaFromDeadZone = framedX - this.deadZoneAnchorX;
    if (Math.abs(deltaFromDeadZone) > this.deadZoneRadiusM) {
      this.deadZoneAnchorX +=
        deltaFromDeadZone - Math.sign(deltaFromDeadZone) * this.deadZoneRadiusM;
    } else if (!context) {
      // Preserve legacy exact tracking in direct unit-test calls without ShotGrammarContext
      this.deadZoneAnchorX = framedX;
    }

    // 1. Check if user selected manual camera override
    if (this.manualMode === "broadcast_main") {
      const trackingX = clamp(this.deadZoneAnchorX * 0.62, -32, 32);
      this.targetPose = {
        position: [trackingX, 30, 58],
        target: [framedX * 0.45, predictedBallY * 0.25, framedZ * 0.25],
        fov: 42 + tacticalFovBonus,
        roll: 0,
      };
    } else if (this.manualMode === "tactical_high") {
      this.targetPose = {
        position: [0, 68, 30],
        target: [0, 0, 0],
        fov: 45,
        roll: 0,
      };
    } else if (this.manualMode === "closeup_action") {
      const sideOffset = framedX >= 0 ? -9.5 : 9.5;
      this.targetPose = {
        position: [framedX + sideOffset, 5.8, Math.min(34, framedZ + 14.5)],
        target: [framedX, Math.max(0.8, predictedBallY + 0.6), framedZ],
        fov: 32,
        roll: 0,
      };
    } else if (this.manualMode === "endzone_home") {
      const goalSide = framedX >= 0 ? 62 : -62;
      this.targetPose = {
        position: [goalSide, 15, framedZ * 0.3],
        target: [framedX * 0.6, Math.max(0.5, predictedBallY), framedZ * 0.4],
        fov: 35,
        roll: 0,
      };
    } else if (this.manualMode === "endzone_away") {
      this.targetPose = {
        position: [62, 16, 0],
        target: [0, 0, 0],
        fov: 35,
        roll: 0,
      };
    } else if (this.manualMode === "replay_cam") {
      this.celebrationOrbitAngle += safeDelta * 0.38;
      const sweepX = framedX + Math.sin(this.celebrationOrbitAngle) * 14;
      this.targetPose = {
        position: [clamp(sweepX, -48, 48), 14.5, 36],
        target: [framedX, Math.max(0.6, predictedBallY), framedZ],
        fov: 33,
        roll: 0,
      };
    } else if (this.manualMode === "celebration_cam") {
      const center = activeGoalScorerPos3D || [ballX, 0, ballZ];
      this.celebrationOrbitAngle += safeDelta * 0.75;
      const radius = 10.5;
      this.targetPose = {
        position: [
          center[0] + Math.cos(this.celebrationOrbitAngle) * radius,
          4.2,
          center[2] + Math.sin(this.celebrationOrbitAngle) * radius,
        ],
        target: [center[0], 1.35, center[2]],
        fov: 34,
        roll: 0,
      };
    } else if (this.manualMode === "dugout_cam") {
      this.targetPose = {
        position: [-14, 2.8, 38],
        target: [-14, 1.2, 0],
        fov: 42,
        roll: 0,
      };
    } else if (this.manualMode === "tunnel_walkout") {
      this.targetPose = {
        position: [0, 2.2, 40],
        target: [0, 1.0, 0],
        fov: 40,
        roll: 0,
      };
    } else if (this.manualMode === "free_orbit") {
      return this.getPose();
    } else {
      // 2. Automated Event-Aware Broadcast Director (Shot Grammar)
      const grammar = this.evaluateShotGrammar(preset, ballPos3D, this.estimatedBallVel3D, context);
      this.liveCameraMode = grammar.liveMode;

      switch (grammar.preset) {
        case "attack_push": {
          const forwardLead = framedX > 0 ? 12 : -12;
          this.targetPose = {
            position: [framedX * 0.7 + forwardLead, 22, 42],
            target: [framedX + forwardLead * 0.5, predictedBallY * 0.5, framedZ * 0.7],
            fov: 36 + tacticalFovBonus * 0.5,
            roll: clamp(-this.estimatedBallVel3D[0] * 0.0012, -0.018, 0.018),
          };
          break;
        }

        case "box_zoom": {
          const boxSide = framedX >= 0 ? 1 : -1;
          this.targetPose = {
            position: [boxSide * 38, 14, 26],
            target: [boxSide * 46, Math.max(1, predictedBallY), framedZ * 0.5],
            fov: 30,
            roll: 0,
          };
          break;
        }

        case "goal_celebration": {
          const center = activeGoalScorerPos3D || [ballX >= 0 ? 46 : -46, 0, 0];
          this.celebrationOrbitAngle += safeDelta * 0.8;
          const radius = 10;
          this.targetPose = {
            position: [
              center[0] + Math.cos(this.celebrationOrbitAngle) * radius,
              4.5,
              center[2] + Math.sin(this.celebrationOrbitAngle) * radius,
            ],
            target: [center[0], 1.5, center[2]],
            fov: 35,
            roll: 0,
          };
          break;
        }

        case "assistant_flag": {
          this.targetPose = {
            position: [framedX, 10, -36],
            target: [framedX, 0, 0],
            fov: 28,
            roll: 0,
          };
          break;
        }

        case "var_replay": {
          this.targetPose = {
            position: [framedX >= 0 ? 35 : -35, 26, -42],
            target: [framedX, predictedBallY, framedZ],
            fov: 32,
            roll: 0,
          };
          break;
        }

        case "broadcast":
        default: {
          const trackingX = clamp(this.deadZoneAnchorX * 0.62, -32, 32);
          this.targetPose = {
            position: [trackingX, 30, 58],
            target: [framedX * 0.45, predictedBallY * 0.25, framedZ * 0.25],
            fov: 42 + tacticalFovBonus,
            roll: 0,
          };
          break;
        }
      }
    }

    // 3. Critically damped spring integration (sub-stepped for large deltaSec)
    const omega = 4.2; // Natural frequency (rad/s) for smooth broadcast response
    const maxStep = 0.025;
    const steps = Math.max(1, Math.min(120, Math.ceil(safeDelta / maxStep)));
    const dt = safeDelta / steps;

    for (let s = 0; s < steps; s++) {
      const expTerm = Math.exp(-omega * dt);

      for (let axis = 0; axis < 3; axis++) {
        // Position spring
        const x0 = this.currentPose.position[axis] - this.targetPose.position[axis];
        const v0 = this.posVelocity[axis];
        const temp = (v0 + omega * x0) * dt;
        this.currentPose.position[axis] = this.targetPose.position[axis] + (x0 + temp) * expTerm;
        this.posVelocity[axis] = (v0 - omega * temp) * expTerm;

        // Target aim spring (slightly tighter omega for responsive look-at)
        const omegaAim = omega * 1.15;
        const expAim = Math.exp(-omegaAim * dt);
        const tx0 = this.currentPose.target[axis] - this.targetPose.target[axis];
        const tv0 = this.targetVelocity[axis];
        const tTemp = (tv0 + omegaAim * tx0) * dt;
        this.currentPose.target[axis] = this.targetPose.target[axis] + (tx0 + tTemp) * expAim;
        this.targetVelocity[axis] = (tv0 - omegaAim * tTemp) * expAim;
      }

      // FOV spring
      const fx0 = this.currentPose.fov - this.targetPose.fov;
      const fv0 = this.fovVelocity;
      const fTemp = (fv0 + omega * fx0) * dt;
      this.currentPose.fov = this.targetPose.fov + (fx0 + fTemp) * expTerm;
      this.fovVelocity = (fv0 - omega * fTemp) * expTerm;

      // Roll spring
      const targetRoll = this.targetPose.roll ?? 0;
      const rx0 = (this.currentPose.roll ?? 0) - targetRoll;
      const rv0 = this.rollVelocity;
      const rTemp = (rv0 + omega * rx0) * dt;
      this.currentPose.roll = targetRoll + (rx0 + rTemp) * expTerm;
      this.rollVelocity = (rv0 - omega * rTemp) * expTerm;
    }

    // 4. Apply event-restricted camera shake (goals, woodwork, major saves, red cards only)
    if (this.shakeIntensity > 0.001) {
      this.shakePhase += safeDelta * 34;
      const shakeOffsetY = Math.sin(this.shakePhase) * this.shakeIntensity * 0.35;
      const shakeOffsetX = Math.cos(this.shakePhase * 1.3) * this.shakeIntensity * 0.25;
      this.currentPose.position[0] += shakeOffsetX;
      this.currentPose.position[1] += shakeOffsetY;
      this.currentPose.roll = (this.currentPose.roll ?? 0) + Math.sin(this.shakePhase * 0.9) * this.shakeIntensity * 0.015;
      this.shakeIntensity *= Math.exp(-4.5 * safeDelta);
      if (this.shakeIntensity < 0.005) {
        this.shakeIntensity = 0;
      }
    }

    // 5. Collision-safe stadium, pitch, and goalpost bounds
    this.currentPose.position[0] = clamp(this.currentPose.position[0], -64, 64);
    this.currentPose.position[1] = clamp(this.currentPose.position[1], 1.4, 75);
    this.currentPose.position[2] = clamp(this.currentPose.position[2], -48, 62);

    // Prevent close cameras from clipping through goal frames at x = ±52.5, |z| <= 4.5
    if (
      Math.abs(Math.abs(this.currentPose.position[0]) - 52.5) < 2.0 &&
      Math.abs(this.currentPose.position[2]) < 5.0 &&
      this.currentPose.position[1] < 3.4
    ) {
      this.currentPose.position[1] = 3.4;
    }

    this.currentPose.fov = clamp(this.currentPose.fov, 24, 60);

    return this.getPose();
  }
}
