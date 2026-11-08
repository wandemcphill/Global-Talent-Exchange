/**
 * GTEX Living Football Ecosystem — WebGL 3D Match Broadcast
 * Spectator-Safe Data Contract, Canonical Match Identity Resolution,
 * and Streaming Synchronization.
 *
 * Implements:
 * 1. Spectator data sanitization (strips confidential coach notes and internal tactics).
 * 2. Canonical match key resolution across OwnerMatch and CompetitionMatch.
 * 3. Read-only spectator stream management with duplicate suppression and resync.
 */

export interface SpectatorSafeTeamView {
  team_id: string;
  team_name: string;
  short_name: string;
  formation: string;
  primary_color: string;
  secondary_color: string;
  accent_color: string;
  goalkeeper_color: string;
  coach_name?: string;
  crest_url?: string;
  pattern_type?: string;
  shorts_color?: string;
  socks_color?: string;
  sponsor_name?: string;
  third_primary_color?: string;
  third_secondary_color?: string;
}

export interface SpectatorSafePlayerTelemetry {
  player_id: string;
  team_id: string;
  side: "home" | "away";
  shirt_number?: number;
  label: string;
  role: string;
  line?: string;
  state?: string;
  active?: boolean;
  highlighted?: boolean;
  position: { x: number; y: number };
  anchor_position?: { x: number; y: number };
  animation_state?: string;
  speed_ratio?: number;
  blend_factor?: number;
  stamina_pct?: number;
  has_possession?: boolean;
  facing?: { x: number; y: number };
  velocity?: { x: number; y: number };
}

export interface SpectatorSafeBallTelemetry {
  position: { x: number; y: number };
  height: number;
  state: string;
  owner_player_id?: string | null;
  velocity?: { x: number; y: number; z: number } | null;
  spin?: { x: number; y: number; z: number } | null;
}

export interface SpectatorSafeFrameView {
  frame_id: string;
  time_seconds: number;
  clock_minute: number;
  phase: string;
  stage?: string;
  home_score: number;
  away_score: number;
  home_attacks_right: boolean;
  possession_side: "home" | "away";
  camera_preset: string;
  active_event_id?: string | null;
  event_banner?: string | null;
  celebration_team_id?: string | null;
  possession_phase?: string;
  transition_state?: string;
  danger_zone?: string | null;
  pressure_index?: number;
  compactness_home?: number;
  compactness_away?: number;
  frame_tags?: string[];
  flag_animation?: boolean;
  players: SpectatorSafePlayerTelemetry[];
  ball: SpectatorSafeBallTelemetry;
}

export interface SpectatorAdPlacementView {
  ad_id: string;
  ad_type: string;
  placement: string;
  brand: string;
  message: string;
  event_id?: string | null;
  active_from_second?: number | null;
  active_until_second?: number | null;
  cta_label?: string | null;
  pricing_cpm_usd?: number | null;
  targeting_tags?: string[];
  inventory_owner?: string | null;
}

export interface SpectatorMonetizationView {
  ads_enabled: boolean;
  premium_ad_free: boolean;
  placements: SpectatorAdPlacementView[];
  metadata?: Record<string, unknown>;
}

export interface SpectatorSafeEventView {
  event_id: string;
  sequence: number;
  event_type: string;
  minute: number;
  added_time: number;
  clock_label: string;
  time_seconds?: number;
  home_score: number;
  away_score: number;
  banner_text: string;
  commentary: string;
  team_id?: string | null;
  team_name?: string | null;
  primary_player_id?: string | null;
  primary_player_name?: string | null;
  secondary_player_id?: string | null;
  secondary_player_name?: string | null;
  highlighted_player_ids?: string[];
  playback_profile?: string;
  miss_variant?: string | null;
  flags?: string[];
  duration_ms?: number;
}

export interface SpectatorSafeMatchView {
  match_id: string;
  canonical_match_id: string;
  source: string;
  home_team: SpectatorSafeTeamView;
  away_team: SpectatorSafeTeamView;
  match_label: string;
  venue_name?: string;
  competition_name?: string;
  duration_seconds?: number;
  frames: SpectatorSafeFrameView[];
  events: SpectatorSafeEventView[];
  is_owner_or_manager: boolean;
  is_demonstration_fixture?: boolean;
  monetization?: SpectatorMonetizationView | null;
  /** Confidential coaching notes: ONLY populated if is_owner_or_manager is true */
  coach_notes?: string[];
}

/**
 * Strongly typed backend MatchViewStateDTO contract accepted at the viewer boundary
 * before sanitization into SpectatorSafeMatchView.
 */
export interface MatchViewStateDTO {
  match_id: string;
  canonical_match_id?: string;
  source?: string;
  venue_name?: string;
  competition_name?: string;
  duration_seconds?: number;
  is_demonstration_fixture?: boolean;
  monetization?: Partial<SpectatorMonetizationView> | null;
  home_team?: Partial<SpectatorSafeTeamView>;
  away_team?: Partial<SpectatorSafeTeamView>;
  frames?: Partial<SpectatorSafeFrameView>[];
  events?: Partial<SpectatorSafeEventView>[];
  presentation_package?: {
    match_label?: string;
    context?: {
      venue_name?: string;
      competition_name?: string;
    };
    home?: {
      coach_name?: string;
      crest?: { image_url?: string };
    };
    away?: {
      coach_name?: string;
      crest?: { image_url?: string };
    };
    coach_notes?: string[];
  } | null;
  metadata_json?: {
    canonical_match_id?: string;
  } | null;
  match?: {
    canonical_match_id?: string;
  } | null;
}

/**
 * Typed contract input for 3D Match Broadcast components (no untyped Record<string, unknown>).
 */
export type MatchViewerContractInput = SpectatorSafeMatchView | MatchViewStateDTO;

/**
 * Runtime validation boundary verifying an incoming payload conforms to MatchViewerContractInput.
 */
export function isValidMatchViewerInput(input: unknown): input is MatchViewerContractInput {
  if (!input || typeof input !== "object") return false;
  const candidate = input as { match_id?: unknown; frames?: unknown; events?: unknown };
  if (typeof candidate.match_id !== "string" && typeof candidate.match_id !== "undefined") {
    return false;
  }
  if (candidate.frames !== undefined && !Array.isArray(candidate.frames)) {
    return false;
  }
  if (candidate.events !== undefined && !Array.isArray(candidate.events)) {
    return false;
  }
  return true;
}

/**
 * Resolves the canonical CompetitionMatch ID from an arbitrary match identifier.
 * Reconciles OwnerMatch IDs (Issue #352) with platform CompetitionMatch records.
 */
export function resolveCanonicalMatchKey(rawId: string, matchPayload?: any): string {
  if (!rawId) return "";
  const trimmed = String(rawId).trim();

  // If match payload specifies an explicit canonical_match_id from Issue #352 mapping
  if (matchPayload?.canonical_match_id) {
    return String(matchPayload.canonical_match_id).trim();
  }
  if (matchPayload?.metadata_json?.canonical_match_id) {
    return String(matchPayload.metadata_json.canonical_match_id).trim();
  }
  if (matchPayload?.match?.canonical_match_id) {
    return String(matchPayload.match.canonical_match_id).trim();
  }

  return trimmed;
}

/**
 * Sanitizes a raw MatchViewStateView payload for public spectator broadcast safety.
 *
 * Rules:
 * - Confidential `coach_notes` are redacted unless `isOwnerOrManager` is true.
 * - Internal tactical flags and opponent exploit telemetry are stripped.
 * - Public match events, scorelines, and spatial player/ball coordinates are preserved.
 */
export function sanitizeForSpectator(
  rawState: MatchViewerContractInput | unknown,
  isOwnerOrManager: boolean = false
): SpectatorSafeMatchView {
  const validSource: any = isValidMatchViewerInput(rawState) ? rawState : {};
  const matchId = String(validSource?.match_id || "").trim();
  const canonicalId = resolveCanonicalMatchKey(matchId, validSource);

  const rawHome = validSource?.home_team || {};
  const rawAway = validSource?.away_team || {};
  const rawPres = validSource?.presentation_package || {};

  const homeTeam: SpectatorSafeTeamView = {
    team_id: String(rawHome.team_id || "home"),
    team_name: String(rawHome.team_name || "Home Team"),
    short_name: String(rawHome.short_name || rawHome.team_name?.slice(0, 3) || "HOM").toUpperCase(),
    formation: String(rawHome.formation || "4-3-3"),
    primary_color: rawHome.primary_color || "#00E676",
    secondary_color: rawHome.secondary_color || "#F5B83D",
    accent_color: rawHome.accent_color || "#FFFFFF",
    goalkeeper_color: rawHome.goalkeeper_color || "#FFB800",
    coach_name: rawPres.home?.coach_name,
    crest_url: rawPres.home?.crest?.image_url,
    pattern_type: rawHome.pattern_type || rawHome.jersey?.pattern || "solid",
    shorts_color: rawHome.shorts_color || rawHome.jersey?.shorts_color,
    socks_color: rawHome.socks_color || rawHome.jersey?.socks_color,
    sponsor_name: rawHome.sponsor_name || rawHome.jersey?.sponsor_name,
    third_primary_color: rawHome.third_primary_color,
    third_secondary_color: rawHome.third_secondary_color,
  };

  const awayTeam: SpectatorSafeTeamView = {
    team_id: String(rawAway.team_id || "away"),
    team_name: String(rawAway.team_name || "Away Team"),
    short_name: String(rawAway.short_name || rawAway.team_name?.slice(0, 3) || "AWY").toUpperCase(),
    formation: String(rawAway.formation || "4-4-2"),
    primary_color: rawAway.primary_color || "#3B82F6",
    secondary_color: rawAway.secondary_color || "#1E40AF",
    accent_color: rawAway.accent_color || "#FFFFFF",
    goalkeeper_color: rawAway.goalkeeper_color || "#EC4899",
    coach_name: rawPres.away?.coach_name,
    crest_url: rawPres.away?.crest?.image_url,
    pattern_type: rawAway.pattern_type || rawAway.jersey?.pattern || "solid",
    shorts_color: rawAway.shorts_color || rawAway.jersey?.shorts_color,
    socks_color: rawAway.socks_color || rawAway.jersey?.socks_color,
    sponsor_name: rawAway.sponsor_name || rawAway.jersey?.sponsor_name,
    third_primary_color: rawAway.third_primary_color,
    third_secondary_color: rawAway.third_secondary_color,
  };

  // Sanitize frames
  const rawFrames: any[] = Array.isArray(validSource?.frames) ? validSource.frames : [];
  const frames: SpectatorSafeFrameView[] = rawFrames.map((f, idx) => ({
    frame_id: String(f.frame_id || `frame_${idx}`),
    time_seconds: Math.max(0, Number(f.time_seconds) || 0),
    clock_minute: Math.max(0, Number(f.clock_minute) || 0),
    phase: String(f.phase || "open_play"),
    stage: f.stage ? String(f.stage) : "event",
    home_score: Math.max(0, Number(f.home_score) || 0),
    away_score: Math.max(0, Number(f.away_score) || 0),
    home_attacks_right: f.home_attacks_right !== false,
    possession_side: f.possession_side === "away" ? "away" : "home",
    camera_preset: String(f.camera_preset || "broadcast"),
    active_event_id: f.active_event_id ? String(f.active_event_id) : null,
    event_banner: f.event_banner ? String(f.event_banner) : null,
    celebration_team_id: f.celebration_team_id ? String(f.celebration_team_id) : null,
    possession_phase: f.possession_phase ? String(f.possession_phase) : "build_up",
    transition_state: f.transition_state ? String(f.transition_state) : "stable",
    danger_zone: f.danger_zone ? String(f.danger_zone) : null,
    pressure_index: typeof f.pressure_index === "number" ? Math.max(0, Math.min(1, f.pressure_index)) : 0,
    compactness_home: typeof f.compactness_home === "number" ? Math.max(0, Math.min(1, f.compactness_home)) : 0.5,
    compactness_away: typeof f.compactness_away === "number" ? Math.max(0, Math.min(1, f.compactness_away)) : 0.5,
    frame_tags: Array.isArray(f.frame_tags) ? f.frame_tags.map((t: any) => String(t)) : [],
    flag_animation: Boolean(f.flag_animation),
    players: Array.isArray(f.players)
      ? f.players.map((p: any) => ({
          player_id: String(p.player_id),
          team_id: String(p.team_id),
          side: p.side === "away" ? ("away" as const) : ("home" as const),
          shirt_number: p.shirt_number ? Number(p.shirt_number) : undefined,
          label: String(p.label || "Player"),
          role: String(p.role || "MID"),
          line: p.line ? String(p.line) : undefined,
          state: p.state ? String(p.state) : "idle",
          active: p.active !== false,
          highlighted: Boolean(p.highlighted),
          position: {
            x: Math.max(0, Math.min(100, Number(p.position?.x) || 50)),
            y: Math.max(0, Math.min(100, Number(p.position?.y) || 50)),
          },
          anchor_position: p.anchor_position
            ? {
                x: Math.max(0, Math.min(100, Number(p.anchor_position.x) || 50)),
                y: Math.max(0, Math.min(100, Number(p.anchor_position.y) || 50)),
              }
            : undefined,
          animation_state: p.animation_state ? String(p.animation_state) : "idle",
          speed_ratio: Math.max(0, Math.min(1, Number(p.speed_ratio) || 0)),
          blend_factor: typeof p.blend_factor === "number" ? Math.max(0, Math.min(1, p.blend_factor)) : undefined,
          stamina_pct: typeof p.stamina_pct === "number" ? Math.max(0, Math.min(100, p.stamina_pct)) : undefined,
          has_possession: Boolean(p.has_possession),
          facing: p.facing ? { x: Number(p.facing.x) || 0, y: Number(p.facing.y) || 0 } : undefined,
          velocity: p.velocity ? { x: Number(p.velocity.x) || 0, y: Number(p.velocity.y) || 0 } : undefined,
        }))
      : [],
    ball: {
      position: {
        x: Math.max(0, Math.min(100, Number(f.ball?.position?.x) || 50)),
        y: Math.max(0, Math.min(100, Number(f.ball?.position?.y) || 50)),
      },
      height: Math.max(0, Number(f.ball?.height) || 0),
      state: String(f.ball?.state || "rolling"),
      owner_player_id: f.ball?.owner_player_id ? String(f.ball.owner_player_id) : null,
      velocity: f.ball?.velocity
        ? {
            x: Number(f.ball.velocity.x) || 0,
            y: Number(f.ball.velocity.y) || 0,
            z: Number(f.ball.velocity.z) || 0,
          }
        : null,
      spin: f.ball?.spin
        ? {
            x: Number(f.ball.spin.x) || 0,
            y: Number(f.ball.spin.y) || 0,
            z: Number(f.ball.spin.z) || 0,
          }
        : null,
    },
  }));

  // Sanitize events
  const rawEvents: any[] = Array.isArray(validSource?.events) ? validSource.events : [];
  const events: SpectatorSafeEventView[] = rawEvents.map((e, idx) => ({
    event_id: String(e.event_id || `event_${idx}`),
    sequence: Math.max(0, Number(e.sequence) || idx),
    event_type: String(e.event_type || "neutral"),
    minute: Math.max(0, Number(e.minute) || 0),
    added_time: Math.max(0, Number(e.added_time) || 0),
    clock_label: String(e.clock_label || `${e.minute || 0}'`),
    time_seconds: typeof e.time_seconds === "number" ? Math.max(0, e.time_seconds) : undefined,
    home_score: Math.max(0, Number(e.home_score) || 0),
    away_score: Math.max(0, Number(e.away_score) || 0),
    banner_text: String(e.banner_text || ""),
    commentary: String(e.commentary || ""),
    team_id: e.team_id ? String(e.team_id) : null,
    team_name: e.team_name ? String(e.team_name) : null,
    primary_player_id: e.primary_player_id ? String(e.primary_player_id) : null,
    primary_player_name: e.primary_player_name ? String(e.primary_player_name) : null,
    secondary_player_id: e.secondary_player_id ? String(e.secondary_player_id) : null,
    secondary_player_name: e.secondary_player_name ? String(e.secondary_player_name) : null,
    highlighted_player_ids: Array.isArray(e.highlighted_player_ids)
      ? e.highlighted_player_ids.map((id: any) => String(id))
      : [],
    playback_profile: e.playback_profile ? String(e.playback_profile) : "neutral",
    miss_variant: e.miss_variant ? String(e.miss_variant) : null,
    flags: Array.isArray(e.flags) ? e.flags.map((fl: any) => String(fl)) : [],
    duration_ms: typeof e.duration_ms === "number" ? e.duration_ms : 500,
  }));

  const sourceLabel = String(validSource?.source || "live_match_hub");
  const isDemoFixture =
    Boolean(validSource?.is_demonstration_fixture) ||
    sourceLabel === "authoritative_simulation_acceptance" ||
    sourceLabel === "local_showcase" ||
    matchId === "gtex_u2a_006_humanoid_showcase" ||
    matchId === "u2a-006-showcase";

  let monetization: SpectatorMonetizationView | null = null;
  if (validSource?.monetization && typeof validSource.monetization === "object") {
    const rawMon = validSource.monetization;
    const rawPlacements: any[] = Array.isArray(rawMon.placements) ? rawMon.placements : [];
    monetization = {
      ads_enabled: Boolean(rawMon.ads_enabled),
      premium_ad_free: Boolean(rawMon.premium_ad_free),
      placements: rawPlacements
        .filter((pl) => pl && typeof pl.brand === "string" && typeof pl.message === "string")
        .map((pl, idx) => ({
          ad_id: String(pl.ad_id || `ad_${idx}`),
          ad_type: String(pl.ad_type || "live_banner"),
          placement: String(pl.placement || "stadium_board"),
          brand: String(pl.brand),
          message: String(pl.message),
          event_id: pl.event_id ? String(pl.event_id) : null,
          active_from_second: typeof pl.active_from_second === "number" ? pl.active_from_second : null,
          active_until_second: typeof pl.active_until_second === "number" ? pl.active_until_second : null,
          cta_label: pl.cta_label ? String(pl.cta_label) : null,
          pricing_cpm_usd: typeof pl.pricing_cpm_usd === "number" ? pl.pricing_cpm_usd : null,
          targeting_tags: Array.isArray(pl.targeting_tags) ? pl.targeting_tags.map((t: any) => String(t)) : [],
          inventory_owner: pl.inventory_owner ? String(pl.inventory_owner) : null,
        })),
      metadata: rawMon.metadata && typeof rawMon.metadata === "object" ? { ...rawMon.metadata } : {},
    };
  }

  const safeView: SpectatorSafeMatchView = {
    match_id: matchId,
    canonical_match_id: canonicalId,
    source: sourceLabel,
    home_team: homeTeam,
    away_team: awayTeam,
    match_label: String(rawPres.match_label || `${homeTeam.team_name} vs ${awayTeam.team_name}`),
    venue_name:
      (rawPres.context?.venue_name ? String(rawPres.context.venue_name) : undefined) ||
      (validSource?.venue_name ? String(validSource.venue_name) : undefined),
    competition_name:
      (rawPres.context?.competition_name ? String(rawPres.context.competition_name) : undefined) ||
      (validSource?.competition_name ? String(validSource.competition_name) : undefined),
    duration_seconds: typeof validSource?.duration_seconds === "number" ? validSource.duration_seconds : undefined,
    frames,
    events,
    is_owner_or_manager: isOwnerOrManager,
    is_demonstration_fixture: isDemoFixture,
    monetization,
  };

  // Only include internal confidential coach notes if viewer is verified club owner/manager
  if (isOwnerOrManager && Array.isArray(rawPres.coach_notes) && rawPres.coach_notes.length > 0) {
    safeView.coach_notes = rawPres.coach_notes.map((n: any) => String(n));
  }

  return safeView;
}

/**
 * Deduplicator for streamed spectator frames.
 * Suppresses duplicates and out-of-order frames, enforcing monotonic simulation time.
 */
export class StreamFrameDeduplicator {
  private seenFrameIds = new Set<string>();
  private lastTimeSeconds: number = -1;
  private maxHistorySize: number = 200;

  public process(frame: SpectatorSafeFrameView): SpectatorSafeFrameView | null {
    if (!frame || !frame.frame_id) return null;

    if (this.seenFrameIds.has(frame.frame_id)) {
      return null; // Duplicate frame suppressed
    }

    // Suppress backwards / out-of-order time jitter unless match was deliberately rewound/reset
    if (frame.time_seconds < this.lastTimeSeconds && (this.lastTimeSeconds - frame.time_seconds < 10)) {
      return null;
    }

    this.seenFrameIds.add(frame.frame_id);
    this.lastTimeSeconds = frame.time_seconds;

    // Keep memory bounded
    if (this.seenFrameIds.size > this.maxHistorySize) {
      const iter = this.seenFrameIds.values();
      for (let i = 0; i < 50; i++) {
        const next = iter.next();
        if (next.done) break;
        this.seenFrameIds.delete(next.value);
      }
    }

    return frame;
  }

  public reset(): void {
    this.seenFrameIds.clear();
    this.lastTimeSeconds = -1;
  }
}
