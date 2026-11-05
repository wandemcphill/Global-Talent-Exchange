/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast
 * Dynamic Broadcast Camera Director.
 *
 * Implements FIFA/TV-grade broadcast cinematography by dynamically transitioning
 * between the 6 canonical server camera presets with smooth exponential damping:
 * 1. BROADCAST: High sideline tracking camera.
 * 2. ATTACK_PUSH: Low forward push into final third.
 * 3. BOX_ZOOM: Tight penalty area framing during shots and saves.
 * 4. GOAL_CELEBRATION: Orbital hero camera circling scorer.
 * 5. ASSISTANT_FLAG: Sideline offside / line-inspection angle.
 * 6. VAR_REPLAY: High reverse-angle freeze-frame review.
 *
 * Also supports viewer-selected manual override modes:
 * - "director_auto", "tactical_high", "endzone_home", "endzone_away", "free_orbit".
 */

export type ManualCameraMode =
  | "director_auto"
  | "tactical_high"
  | "endzone_home"
  | "endzone_away"
  | "dugout_cam"
  | "tunnel_walkout"
  | "free_orbit";

export interface CameraPose {
  position: [number, number, number];
  target: [number, number, number];
  fov: number;
}

export class CameraDirector {
  private currentPose: CameraPose = {
    position: [0, 32, 55],
    target: [0, 0, 0],
    fov: 38,
  };

  private targetPose: CameraPose = {
    position: [0, 32, 55],
    target: [0, 0, 0],
    fov: 38,
  };

  private manualMode: ManualCameraMode = "director_auto";
  private celebrationOrbitAngle: number = 0;

  public setManualMode(mode: ManualCameraMode): void {
    this.manualMode = mode;
  }

  public getManualMode(): ManualCameraMode {
    return this.manualMode;
  }

  public getPose(): CameraPose {
    return {
      position: [...this.currentPose.position],
      target: [...this.currentPose.target],
      fov: this.currentPose.fov,
    };
  }

  /**
   * Evaluates the desired camera target pose based on the server preset,
   * ball position, scorer position, and manual user override.
   */
  public update(
    deltaSec: number,
    preset: string,
    ballPos3D: [number, number, number],
    activeGoalScorerPos3D?: [number, number, number] | null
  ): CameraPose {
    const ballX = ballPos3D[0];
    const ballY = ballPos3D[1];
    const ballZ = ballPos3D[2];

    // 1. Check if user selected manual camera override
    if (this.manualMode === "tactical_high") {
      this.targetPose = {
        position: [0, 68, 30],
        target: [0, 0, 0],
        fov: 45,
      };
    } else if (this.manualMode === "endzone_home") {
      this.targetPose = {
        position: [-62, 16, 0],
        target: [0, 0, 0],
        fov: 35,
      };
    } else if (this.manualMode === "endzone_away") {
      this.targetPose = {
        position: [62, 16, 0],
        target: [0, 0, 0],
        fov: 35,
      };
    } else if (this.manualMode === "dugout_cam") {
      this.targetPose = {
        position: [-14, 2.8, 38],
        target: [-14, 1.2, 0],
        fov: 42,
      };
    } else if (this.manualMode === "tunnel_walkout") {
      this.targetPose = {
        position: [0, 2.2, 40],
        target: [0, 1.0, 0],
        fov: 40,
      };
    } else if (this.manualMode === "free_orbit") {
      // In free orbit mode, caller manages OrbitControls directly; preserve pose
      return this.currentPose;
    } else {
      // 2. Automated Broadcast Director presets
      const normalizedPreset = (preset || "broadcast").toLowerCase();

      switch (normalizedPreset) {
        case "attack_push": {
          // Track forward into the attacking channel
          const forwardLead = ballX > 0 ? 12 : -12;
          this.targetPose = {
            position: [ballX * 0.7 + forwardLead, 22, 42],
            target: [ballX + forwardLead * 0.5, ballY * 0.5, ballZ * 0.7],
            fov: 36,
          };
          break;
        }

        case "box_zoom": {
          // Penalty area zoom
          const boxSide = ballX >= 0 ? 1 : -1;
          this.targetPose = {
            position: [boxSide * 38, 14, 26],
            target: [boxSide * 46, Math.max(1, ballY), ballZ * 0.5],
            fov: 30,
          };
          break;
        }

        case "goal_celebration": {
          // Orbit around scorer or goal center
          const center = activeGoalScorerPos3D || [ballX >= 0 ? 46 : -46, 0, 0];
          this.celebrationOrbitAngle += deltaSec * 0.8;
          const radius = 10;
          this.targetPose = {
            position: [
              center[0] + Math.cos(this.celebrationOrbitAngle) * radius,
              4.5,
              center[2] + Math.sin(this.celebrationOrbitAngle) * radius,
            ],
            target: [center[0], 1.5, center[2]],
            fov: 35,
          };
          break;
        }

        case "assistant_flag": {
          // Sideline offside review perspective aligned with defensive line
          this.targetPose = {
            position: [ballX, 10, -36],
            target: [ballX, 0, 0],
            fov: 28,
          };
          break;
        }

        case "var_replay": {
          // High reverse-angle freeze-frame review
          this.targetPose = {
            position: [ballX >= 0 ? 35 : -35, 26, -42],
            target: [ballX, ballY, ballZ],
            fov: 32,
          };
          break;
        }

        case "broadcast":
        default: {
          // Standard elevated sideline camera smoothly panning along touchline
          const trackingX = Math.max(-30, Math.min(30, ballX * 0.6));
          this.targetPose = {
            position: [trackingX, 30, 56],
            target: [ballX * 0.4, ballY * 0.3, ballZ * 0.3],
            fov: 38,
          };
          break;
        }
      }
    }

    // 3. Smooth exponential damping towards target pose
    const damping = Math.min(1.0, Math.max(0.01, deltaSec * 3.5));

    this.currentPose.position[0] += (this.targetPose.position[0] - this.currentPose.position[0]) * damping;
    this.currentPose.position[1] += (this.targetPose.position[1] - this.currentPose.position[1]) * damping;
    this.currentPose.position[2] += (this.targetPose.position[2] - this.currentPose.position[2]) * damping;

    this.currentPose.target[0] += (this.targetPose.target[0] - this.currentPose.target[0]) * damping;
    this.currentPose.target[1] += (this.targetPose.target[1] - this.currentPose.target[1]) * damping;
    this.currentPose.target[2] += (this.targetPose.target[2] - this.currentPose.target[2]) * damping;

    this.currentPose.fov += (this.targetPose.fov - this.currentPose.fov) * damping;

    return this.getPose();
  }
}
