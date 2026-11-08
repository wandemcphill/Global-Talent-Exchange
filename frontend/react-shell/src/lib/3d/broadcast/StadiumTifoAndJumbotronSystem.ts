/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast
 * Dynamic 3D Stadium Jumbotron & Supporter Tifo Choreography System (Phase 4).
 *
 * Implements:
 * 1. Dual high-visibility stadium jumbotron LED video screens (North & South stands)
 *    rendering dynamic HTML5 canvas textures with live scores, clock, and event banners.
 * 2. Home-end supporter Ultras Tifo choreography banner, dynamically unfurling on
 *    walkouts and goal celebrations with club colors and crest slogans.
 *
 * Graceful fallback in non-browser/headless environments; zero per-frame garbage.
 */

import * as THREE from "three";

export interface StadiumTifoOptions {
  homeTeamName?: string;
  awayTeamName?: string;
  homeShortName?: string;
  awayShortName?: string;
  homeColorHex?: string;
  awayColorHex?: string;
  competitionName?: string;
}

export type TifoState = "hidden" | "unfurling" | "displayed" | "furling";

export interface StadiumTifoAndJumbotronSummary {
  tifoState: TifoState;
  tifoProgress: number;
  jumbotronAlertText: string | null;
  jumbotronAlertActive: boolean;
  scoreText: string;
  clockText: string;
}

export class StadiumTifoAndJumbotronSystem {
  public readonly rootGroup: THREE.Group;

  // Jumbotron Elements
  private jumbotronMeshNorth: THREE.Mesh | null = null;
  private jumbotronMeshSouth: THREE.Mesh | null = null;
  private canvasElement: HTMLCanvasElement | null = null;
  private canvasContext: CanvasRenderingContext2D | null = null;
  private canvasTexture: THREE.CanvasTexture | null = null;
  private screenMaterial: THREE.MeshBasicMaterial | null = null;

  // Tifo Elements
  private tifoGroup: THREE.Group;
  private tifoBannerMesh: THREE.Mesh;
  private tifoMaterial: THREE.MeshBasicMaterial;
  private tifoState: TifoState = "hidden";
  private tifoProgress: number = 0; // 0.0 to 1.0
  private tifoTimerSec: number = 0;
  private tifoMaxDurationSec: number = 10;
  private tifoText: string = "FORZA GTEX";

  // Match State Cache
  private homeShortName: string = "HOM";
  private awayShortName: string = "AWY";
  private homeColor: string = "#10b981";
  private awayColor: string = "#06b6d4";
  private competitionName: string = "GTEX PREMIER LEAGUE";
  private currentHomeScore: number = 0;
  private currentAwayScore: number = 0;
  private currentClockText: string = "00'";
  private alertText: string | null = null;
  private alertColorHex: string = "#facc15";
  private alertTimerSec: number = 0;
  private needsCanvasRedraw: boolean = true;
  private redrawCooldownMs: number = 0;

  constructor(scene: THREE.Scene, options?: StadiumTifoOptions) {
    this.rootGroup = new THREE.Group();
    this.rootGroup.name = "StadiumTifoAndJumbotronSystem";

    if (options?.homeShortName) this.homeShortName = options.homeShortName;
    if (options?.awayShortName) this.awayShortName = options.awayShortName;
    if (options?.homeColorHex) this.homeColor = options.homeColorHex;
    if (options?.awayColorHex) this.awayColor = options.awayColorHex;
    if (options?.competitionName) this.competitionName = options.competitionName;

    // -------------------------------------------------------------------------
    // 1. Dynamic Jumbotron Canvas Texture (512x256)
    // -------------------------------------------------------------------------
    if (typeof document !== "undefined" && typeof document.createElement === "function") {
      try {
        this.canvasElement = document.createElement("canvas");
        this.canvasElement.width = 512;
        this.canvasElement.height = 256;
        this.canvasContext = this.canvasElement.getContext("2d");
        if (this.canvasContext) {
          this.canvasTexture = new THREE.CanvasTexture(this.canvasElement);
          this.canvasTexture.minFilter = THREE.LinearFilter;
          this.canvasTexture.magFilter = THREE.LinearFilter;
          this.screenMaterial = new THREE.MeshBasicMaterial({
            map: this.canvasTexture,
          });
        }
      } catch {
        // Fallback for environments where Canvas is disabled
      }
    }

    if (!this.screenMaterial) {
      this.screenMaterial = new THREE.MeshBasicMaterial({ color: 0x0f172a });
    }

    // Dual Jumbotrons (North & South touchline stands at z = -46.5m and z = +46.5m)
    const screenGeo = new THREE.PlaneGeometry(16, 8);
    const frameGeo = new THREE.BoxGeometry(16.6, 8.6, 0.6);
    const frameMat = new THREE.MeshBasicMaterial({ color: 0x1e293b });

    const createJumbotronUnit = (zPos: number, rotY: number) => {
      const unit = new THREE.Group();
      unit.position.set(0, 24, zPos);
      unit.rotation.y = rotY;

      const frame = new THREE.Mesh(frameGeo, frameMat);
      frame.position.z = -0.3;
      unit.add(frame);

      const screen = new THREE.Mesh(screenGeo, this.screenMaterial!);
      unit.add(screen);
      return unit;
    };

    const northUnit = createJumbotronUnit(-46.5, 0);
    this.jumbotronMeshNorth = northUnit.children[1] as THREE.Mesh;
    this.rootGroup.add(northUnit);

    const southUnit = createJumbotronUnit(46.5, Math.PI);
    this.jumbotronMeshSouth = southUnit.children[1] as THREE.Mesh;
    this.rootGroup.add(southUnit);

    // Initial canvas render
    this.renderJumbotronCanvas();

    // -------------------------------------------------------------------------
    // 2. Home-End Supporter Tifo Banner (x = -58.5m behind Home goal)
    // -------------------------------------------------------------------------
    this.tifoGroup = new THREE.Group();
    this.tifoGroup.position.set(-58.5, 12, 0);
    this.tifoGroup.rotation.y = Math.PI / 2; // Facing the pitch

    const tifoBannerGeo = new THREE.PlaneGeometry(24, 10);
    // Anchor top of the banner to y = 0
    tifoBannerGeo.translate(0, -5, 0);

    this.tifoMaterial = new THREE.MeshBasicMaterial({
      color: new THREE.Color(this.homeColor),
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.95,
    });

    this.tifoBannerMesh = new THREE.Mesh(tifoBannerGeo, this.tifoMaterial);
    this.tifoBannerMesh.scale.set(1, 0.001, 1); // Start furled up
    this.tifoGroup.add(this.tifoBannerMesh);
    this.rootGroup.add(this.tifoGroup);

    scene.add(this.rootGroup);
  }

  /**
   * Triggers the supporter tifo banner to unfurl.
   */
  public triggerTifo(bannerText: string = "FORZA GTEX", durationSec: number = 10): void {
    this.tifoText = bannerText;
    this.tifoMaxDurationSec = durationSec;
    this.tifoTimerSec = 0;
    this.tifoState = "unfurling";
  }

  /**
   * Triggers an animated alert flash on the stadium jumbotrons.
   */
  public triggerJumbotronFlash(
    alertText: string,
    alertColorHex: string = "#facc15",
    durationSec: number = 6
  ): void {
    this.alertText = alertText;
    this.alertColorHex = alertColorHex;
    this.alertTimerSec = durationSec;
    this.needsCanvasRedraw = true;
  }

  /**
   * Updates jumbotron canvas and advances tifo choreography animation.
   */
  public update(
    deltaSec: number,
    matchState: {
      homeScore: number;
      awayScore: number;
      clockMinute: number;
      eventBanner?: string | null;
      phase?: string;
    }
  ): void {
    // 1. Check if score or clock changed
    const clockStr = `${Math.floor(matchState.clockMinute)}'`;
    if (
      this.currentHomeScore !== matchState.homeScore ||
      this.currentAwayScore !== matchState.awayScore ||
      this.currentClockText !== clockStr
    ) {
      this.currentHomeScore = matchState.homeScore;
      this.currentAwayScore = matchState.awayScore;
      this.currentClockText = clockStr;
      this.needsCanvasRedraw = true;
    }

    // 2. Alert timer countdown
    if (this.alertTimerSec > 0) {
      this.alertTimerSec -= deltaSec;
      if (this.alertTimerSec <= 0) {
        this.alertText = null;
        this.needsCanvasRedraw = true;
      }
    }

    // Redraw canvas with rate limiter (at most once every 120ms)
    this.redrawCooldownMs -= deltaSec * 1000;
    if (this.needsCanvasRedraw && this.redrawCooldownMs <= 0) {
      this.renderJumbotronCanvas();
      this.needsCanvasRedraw = false;
      this.redrawCooldownMs = 120;
    }

    // 3. Update Tifo Choreography State Machine
    switch (this.tifoState) {
      case "unfurling": {
        this.tifoProgress = Math.min(1.0, this.tifoProgress + deltaSec * 1.2);
        this.tifoBannerMesh.scale.y = this.tifoProgress;
        if (this.tifoProgress >= 1.0) {
          this.tifoState = "displayed";
          this.tifoTimerSec = 0;
        }
        break;
      }
      case "displayed": {
        this.tifoTimerSec += deltaSec;
        if (this.tifoTimerSec >= this.tifoMaxDurationSec) {
          this.tifoState = "furling";
        }
        break;
      }
      case "furling": {
        this.tifoProgress = Math.max(0.001, this.tifoProgress - deltaSec * 0.8);
        this.tifoBannerMesh.scale.y = this.tifoProgress;
        if (this.tifoProgress <= 0.002) {
          this.tifoState = "hidden";
          this.tifoBannerMesh.scale.y = 0.001;
        }
        break;
      }
      case "hidden":
      default: {
        this.tifoBannerMesh.scale.y = 0.001;
        break;
      }
    }
  }

  private renderJumbotronCanvas(): void {
    if (!this.canvasContext || !this.canvasElement) return;

    const ctx = this.canvasContext;
    const w = this.canvasElement.width;
    const h = this.canvasElement.height;

    // Dark stadium LED background
    ctx.fillStyle = "#090d16";
    ctx.fillRect(0, 0, w, h);

    // Top Competition Header Strip
    ctx.fillStyle = "#1e293b";
    ctx.fillRect(0, 0, w, 40);
    ctx.fillStyle = "#10b981";
    ctx.font = "bold 16px monospace";
    ctx.textAlign = "center";
    ctx.fillText(this.competitionName.toUpperCase(), w / 2, 26);

    if (this.alertText && this.alertTimerSec > 0) {
      // Big Flashing Event Alert Banner
      ctx.fillStyle = this.alertColorHex;
      ctx.fillRect(16, 56, w - 32, 140);
      ctx.fillStyle = "#020617";
      ctx.font = "900 38px sans-serif";
      ctx.fillText(this.alertText.toUpperCase(), w / 2, 142);
    } else {
      // Standard Scorebug Mode
      // Home Team Box
      ctx.fillStyle = this.homeColor;
      ctx.font = "900 32px monospace";
      ctx.textAlign = "right";
      ctx.fillText(this.homeShortName, w / 2 - 80, 130);

      // Score
      ctx.fillStyle = "#f8fafc";
      ctx.font = "900 52px monospace";
      ctx.textAlign = "center";
      ctx.fillText(`${this.currentHomeScore} - ${this.currentAwayScore}`, w / 2, 136);

      // Away Team Box
      ctx.fillStyle = this.awayColor;
      ctx.font = "900 32px monospace";
      ctx.textAlign = "left";
      ctx.fillText(this.awayShortName, w / 2 + 80, 130);
    }

    // Bottom Clock & Status Strip
    ctx.fillStyle = "#0f172a";
    ctx.fillRect(0, h - 48, w, 48);
    ctx.fillStyle = "#38bdf8";
    ctx.font = "bold 22px monospace";
    ctx.textAlign = "center";
    ctx.fillText(this.currentClockText, w / 2, h - 16);

    if (this.canvasTexture) {
      this.canvasTexture.needsUpdate = true;
    }
  }

  public getSummary(): StadiumTifoAndJumbotronSummary {
    return {
      tifoState: this.tifoState,
      tifoProgress: Number(this.tifoProgress.toFixed(2)),
      jumbotronAlertText: this.alertText,
      jumbotronAlertActive: this.alertTimerSec > 0,
      scoreText: `${this.currentHomeScore} - ${this.currentAwayScore}`,
      clockText: this.currentClockText,
    };
  }

  public dispose(): void {
    if (this.canvasTexture) {
      this.canvasTexture.dispose();
    }
    if (this.screenMaterial) {
      this.screenMaterial.dispose();
    }
    this.tifoBannerMesh.geometry.dispose();
    this.tifoMaterial.dispose();
    this.rootGroup.clear();
    if (this.rootGroup.parent) {
      this.rootGroup.parent.remove(this.rootGroup);
    }
  }
}
