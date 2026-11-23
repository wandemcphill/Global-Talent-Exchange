import React, { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { MatchPitchLiveScene } from "@/lib/3d/broadcast/MatchPitchLiveScene";
import { MixamoKitFootballer } from "@/lib/3d/broadcast/MixamoKitFootballer";
import { loadFiveMinuteShowcaseFixture } from "@/lib/3d/broadcast/showcaseLoader";
import { PressRoomStage } from "@/components/gtex/PressRoomStage";
import { CinematicGiftingEngine } from "@/lib/3d/gifting/CinematicGiftingEngine";
import { PrestigeShowroomScene } from "@/lib/3d/scenes/PrestigeShowroomScene";
import { GtexSceneViewport } from "@/lib/3d/GtexSceneViewport";
import { CampusBuilder3D } from "@/components/gtex/CampusBuilder3D";
import { ClubOperationsCentre3D } from "@/components/gtex/ClubOperationsCentre3D";
import type { ClubOperationsHubPayload, OperationsHubDestination } from "@/lib/ownerBriefing";
import type { SpectatorSafeMatchView } from "@/lib/3d/broadcast/spectatorContract";
import { Pitch2DView } from "@/pages/match-center/Pitch2DView";
import { MatchTimelineScrubber, buildTimelineModel } from "@/pages/match-center/MatchTimelineScrubber";
import { KitPlayerPortrait } from "@/components/gtex/KitPlayerPortrait";
import {
  EditorialLineupPosterCard,
  TunnelStartingXICard,
  type MatchdayTeamSheet,
} from "@/components/gtex/MatchdayLineupBroadcast";
import type { PitchCameraMode } from "@/match2d/OrthographicPitch";

const HEADQUARTERS_PREVIEW: ClubOperationsHubPayload = headquartersPreview();

function headquartersPreview(): ClubOperationsHubPayload {
  const keys: OperationsHubDestination["destination_key"][] = [
    "executive_office",
    "managers_office",
    "general_managers_office",
    "academy_department",
    "medical_department",
    "finance_commercial_office",
  ];
  const destinations: OperationsHubDestination[] = keys.map((key, index) => ({
    destination_key: key,
    label: key.replace(/_/g, " "),
    short_label: key.replace(/_/g, " "),
    subtitle: "Club operations",
    lead_role_key: key,
    communication_channel_mode: "office_wide",
    staff_lead: {
      role_key: key,
      name: "Tunde Bakare",
      role_label: "First-Team Manager",
      mood: 80,
      loyalty: 75,
      is_vacant: false,
      is_appointed: true,
    },
    glb_model: "/models/campus/club_hq.glb",
    exterior_glb: "/models/campus/club_hq.glb",
    accent_color: "#34d399",
    position_3d: [(index - 2.5) * 14, 0, index % 2 === 0 ? -8 : 8],
    camera_position: [3.4, 2.8, 6.2],
    camera_target: [0, 1.25, -0.4],
    hotspots: [{ id: `${key}-desk`, label: "Desk", action: "inspect_briefing", offset: [0, 1.2, 1.4] }],
    report_section_key: "executive_briefing",
    report: {},
    open_decisions: [],
    open_decisions_count: 0,
    recent_messages: [],
  }));
  return {
    club: {
      club_id: "review-club",
      club_name: "GTEX FC",
      owner_name: "Owner",
      world_day: 1,
      prestige: 40,
      prestige_tier: "Foundation",
      fans: 1000,
      mentality: "balanced",
      cash_gtex: 6930,
      fan_coin: 1000,
      club_valuation_gtex: 200000,
    },
    daily_briefing: { world_day: 1, headline: "First day" },
    destinations,
    actionable_decisions: { department_decisions: [], inbox_decisions: [], total_open_count: 0 },
    operational_timeline: [],
    decision_history: [],
  };
}

function KitCloseUp() {
  const mountRef = useRef<HTMLDivElement | null>(null);
    const kitFrame = 3;

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;
    const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    mount.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#0b1220");
    const camera = new THREE.PerspectiveCamera(28, mount.clientWidth / Math.max(mount.clientHeight, 1), 0.05, 40);
    camera.position.set(0.2, 1.35, 6.2);
    camera.lookAt(0, 0.95, 0);
    scene.add(new THREE.HemisphereLight(0xfff4e5, 0x1e3a2f, 1.4));
    const key = new THREE.DirectionalLight(0xffffff, 2.2);
    key.position.set(1.4, 3.2, 2.4);
    scene.add(key);
    const ground = new THREE.Mesh(
      new THREE.CircleGeometry(1.4, 32),
      new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.8 })
    );
    ground.rotation.x = -Math.PI / 2;
    scene.add(ground);

    const player = new MixamoKitFootballer({
      playerId: "review-kit",
      side: "home",
      shirtNumber: 9,
      label: "Review",
      role: "ST",
      isGoalkeeper: false,
      primaryColor: "#C8102E",
      secondaryColor: "#F5F5F5",
      accentColor: "#D4A84A",
      goalkeeperColor: "#F4C430",
      shortsColor: "#F5F5F5",
      socksColor: "#C8102E",
    });
    scene.add(player.rootGroup);
    (window as unknown as { __reviewPlayer?: MixamoKitFootballer }).__reviewPlayer = player;

    let raf = 0;
    let last = performance.now();
    const loop = (now: number) => {
      raf = requestAnimationFrame(loop);
      const delta = Math.min(0.05, (now - last) / 1000);
      last = now;
      player.update({
        deltaSec: delta,
        targetState: "idle",
        position3D: [0, 0, 0],
        facingAngleRad: Math.PI / 2,
        speedRatio: 0,
        hasPossession: false,
        ballPosition3D: [0, 0, 1],
        cameraPosition3D: [camera.position.x, camera.position.y, camera.position.z],
      });
      const label = mount.parentElement?.querySelector("[data-testid='kit-debug']");
      try {
        renderer.render(scene, camera);
        const info = renderer.info.render;
        let sphere = "none";
        player.rootGroup.traverse((obj) => {
          const mesh = obj as THREE.SkinnedMesh;
          if (sphere !== "none" || !mesh.isSkinnedMesh) return;
          mesh.geometry.computeBoundingSphere();
          const s = mesh.geometry.boundingSphere;
          sphere = s ? `${s.center.x.toFixed(2)},${s.center.y.toFixed(2)},${s.center.z.toFixed(2)} r${s.radius.toFixed(2)}` : "empty";
        });
        if (label) label.textContent = `calls ${info.calls} tris ${info.triangles} sphere ${sphere}`;
      } catch (err) {
        if (label) label.textContent = err instanceof Error ? err.message : String(err);
      }
    };
    loop(last);

    return () => {
      cancelAnimationFrame(raf);
      renderer.dispose();
      if (mount.contains(renderer.domElement)) mount.removeChild(renderer.domElement);
    };
  }, [kitFrame]);

  return (
    <div>
      <div ref={mountRef} className="h-[520px] w-full" data-testid="kit-closeup" />
      <p data-testid="kit-debug" className="px-3 py-1 text-xs text-amber-200">waiting</p>
    </div>
  );
}

function LiveFpsPill() {
  const [fps, setFps] = useState<number | null>(null);
  useEffect(() => {
    let raf = 0;
    let frames = 0;
    let windowStart = performance.now();
    const tick = (now: number) => {
      frames += 1;
      const elapsed = now - windowStart;
      if (elapsed >= 500) {
        setFps(Math.round((frames * 1000) / elapsed));
        frames = 0;
        windowStart = now;
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);
  return (
    <span
      data-testid="visual-review-live-fps"
      className="ml-auto rounded border border-emerald-400/35 bg-emerald-500/15 px-2 py-0.5 font-mono text-[10px] font-black uppercase tracking-wider text-emerald-300"
    >
      {fps !== null ? `${fps} FPS` : "MEASURING..."}
    </span>
  );
}

function Match2DReviewStage({ match }: { match: SpectatorSafeMatchView | null }) {
  const [cameraMode, setCameraMode] = useState<PitchCameraMode>("2d");
  const [activePanel, setActivePanel] = useState<"pitch" | "lineups">("pitch");
  const [timeSeconds, setTimeSeconds] = useState(12);
  const [paused, setPaused] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<1 | 2 | 3 | 4>(2);

  useEffect(() => {
    if (paused) return undefined;
    const id = window.setInterval(() => {
      setTimeSeconds((prev) => {
        const next = prev + 0.25 * playbackSpeed;
        return next >= 298 ? 2 : next;
      });
    }, 250);
    return () => window.clearInterval(id);
  }, [paused, playbackSpeed]);

  const homeName = match?.home_team?.team_name || "EKITI FC";
  const awayName = match?.away_team?.team_name || "Lagos Titans AI";
  const homeColor = match?.home_team?.primary_color || "#123C73";
  const awayColor = match?.away_team?.primary_color || "#F5F7FA";
  const timelineModel = useMemo(
    () =>
      buildTimelineModel(
        (match?.frames || []).map((f: any) => ({
          timeSeconds: Number(f.time_seconds ?? f.timeSeconds ?? 0),
          phase: f.phase,
          possession_side: f.possession_side,
          pressure_index: f.pressure_index,
          ball: f.ball,
          home_attacks_right: f.home_attacks_right,
        })),
        (match?.events as any) || [],
        300,
      ),
    [match],
  );

  if (!match) {
    return <div className="grid h-screen place-items-center text-sm text-slate-400">Loading 2D match review...</div>;
  }

  const firstPlayers = (match.frames?.[0] as any)?.players || [];
  const toSheet = (side: "home" | "away", clubName: string, formation: string): MatchdayTeamSheet => {
    const sidePlayers = firstPlayers
      .filter((p: any) => String(p.side || "").toLowerCase() === side)
      .slice(0, 11);
    const starters = sidePlayers.map((p: any, idx: number) => ({
      player_id: String(p.player_id || `${side}-${idx}`),
      full_name: String(p.player_name || p.name || `${clubName.split(" ")[0]} #${p.shirt_number || idx + 1}`),
      short_name: String(p.player_name || p.name || `Player ${p.shirt_number || idx + 1}`).split(" ").slice(-1)[0],
      shirt_number: Number(p.shirt_number || idx + 1),
      position: String(p.role || (idx === 0 ? "GK" : idx <= 4 ? "DF" : idx <= 7 ? "MF" : "FW")),
      rating: 82 + (idx % 5),
      portrait_url: null,
      is_captain: idx === 3,
      is_signed: true,
    }));
    const hero = starters[3] || starters[0];
    return {
      clubId: side,
      clubName,
      formation,
      starters,
      substitutes: [
        { player_id: `${side}-sub-1`, full_name: "Tunde Adeyemi", short_name: "Adeyemi", shirt_number: 13, position: "GK", rating: 78, portrait_url: null },
        { player_id: `${side}-sub-2`, full_name: "Chuka Eze", short_name: "Eze", shirt_number: 15, position: "MF", rating: 80, portrait_url: null },
        { player_id: `${side}-sub-3`, full_name: "Kola Balogun", short_name: "Balogun", shirt_number: 18, position: "FW", rating: 81, portrait_url: null },
      ],
      hero,
      avgRating: 84,
      signedStarterCount: starters.length,
    };
  };

  const homeSheet = toSheet("home", homeName, match.home_team?.formation || "4-3-3");
  const awaySheet = toSheet("away", awayName, match.away_team?.formation || "4-3-3");

  return (
    <main className="min-h-screen bg-[#07111c] px-4 py-2.5 text-white">
      <div className="mx-auto max-w-5xl space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <h1 className="text-sm font-black uppercase tracking-widest text-emerald-300">
              GTEX 2D / 2.5D Broadcast &amp; Lineup Verification
            </h1>
            <div className="flex items-center gap-1 rounded border border-white/10 bg-slate-900/90 p-0.5">
              <button
                type="button"
                data-testid="review-tab-pitch"
                onClick={() => setActivePanel("pitch")}
                className={`rounded px-2.5 py-0.5 text-[11px] font-black uppercase ${
                  activePanel === "pitch" ? "bg-emerald-500/25 text-emerald-200" : "text-slate-400 hover:text-white"
                }`}
              >
                Pitch
              </button>
              <button
                type="button"
                data-testid="review-tab-lineups"
                onClick={() => setActivePanel("lineups")}
                className={`rounded px-2.5 py-0.5 text-[11px] font-black uppercase ${
                  activePanel === "lineups" ? "bg-emerald-500/25 text-emerald-200" : "text-slate-400 hover:text-white"
                }`}
              >
                Lineups
              </button>
            </div>
          </div>
          {activePanel === "pitch" && (
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setPaused((p) => !p)}
                className="rounded border border-white/15 bg-slate-900 px-3 py-1 text-xs font-black uppercase text-slate-200 hover:text-white"
              >
                {paused ? "Play" : "Pause"}
              </button>
              <div className="flex items-center gap-1 rounded border border-white/10 bg-slate-900/90 p-0.5">
                {([1, 2, 3, 4] as const).map((spd) => (
                  <button
                    key={spd}
                    type="button"
                    data-testid={`review-speed-${spd}x`}
                    onClick={() => setPlaybackSpeed(spd)}
                    className={`rounded px-2 py-0.5 font-mono text-[11px] font-black ${
                      playbackSpeed === spd
                        ? "bg-emerald-500/25 text-emerald-200"
                        : "text-slate-400 hover:text-white"
                    }`}
                  >
                    {spd}x
                  </button>
                ))}
              </div>
              {(["2d", "2.5d"] as PitchCameraMode[]).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  data-testid={`review-mode-${mode}`}
                  onClick={() => setCameraMode(mode)}
                  className={`rounded border px-3 py-1 text-xs font-black uppercase ${
                    cameraMode === mode
                      ? "border-emerald-400 bg-emerald-500/20 text-emerald-200"
                      : "border-white/15 bg-slate-900 text-slate-300"
                  }`}
                >
                  {mode.toUpperCase()}
                </button>
              ))}
              <LiveFpsPill />
            </div>
          )}
        </div>

        {activePanel === "pitch" ? (
          <div className="space-y-3">
            <Pitch2DView
              matchId="visual-review-match2d"
              frames={match.frames as any}
              timeSeconds={timeSeconds}
              events={match.events as any}
              homeName={homeName}
              awayName={awayName}
              homeColor={homeColor}
              awayColor={awayColor}
              homeScore={2}
              awayScore={1}
              clockMinute={Math.floor((timeSeconds / 300) * 90)}
              cameraMode={cameraMode}
              onCameraModeChange={setCameraMode}
              isPaused={paused}
              playbackSpeed={playbackSpeed}
              durationSeconds={300}
            />
            <MatchTimelineScrubber
              model={timelineModel}
              currentSeconds={timeSeconds}
              readOnly={false}
              homeColor={homeColor}
              awayColor={awayColor}
              onSeek={(s) => setTimeSeconds(s)}
            />
          </div>
        ) : (
          <div className="space-y-4 pt-2" data-testid="review-lineups-section">
            <KitPlayerPortrait
              shirtNumber={homeSheet.hero?.shirt_number || 4}
              playerName={homeSheet.hero?.full_name || "Captain"}
              primaryColor={homeColor}
            />
            <div className="grid gap-5 xl:grid-cols-2">
              <TunnelStartingXICard
                sheet={homeSheet}
                opponentName={awayName}
                competitionName="GTEX MATCHDAY LIVE"
                roundLabel="MATCHDAY 1"
                kitColor={homeColor}
              />
              <EditorialLineupPosterCard
                sheet={awaySheet}
                venueName={`${homeName} Arena`}
                matchdayNumber={1}
                kitColor={awayColor}
              />
            </div>
          </div>
        )}
      </div>
    </main>
  );
}

export default function VisualReviewPage() {
  const [match, setMatch] = useState<SpectatorSafeMatchView | null>(null);
  const only = new URLSearchParams(window.location.search).get("scene");
  const [activeScene, setActiveScene] = useState<
    "broadcast" | "match2d" | "kit" | "press" | "gift" | "takeover" | "showroom"
  >(only === "match2d" ? "match2d" : "broadcast");

  useEffect(() => {
    if (only && only !== "match2d") return;
    void loadFiveMinuteShowcaseFixture(300).then(setMatch);
  }, [only]);

  if (only === "match2d") {
    return <Match2DReviewStage match={match} />;
  }

  if (only === "arrival") {
    return (
      <main className="min-h-screen bg-[#07111c] text-white">
        <GtexSceneViewport
          sceneId="manager_arrival"
          clubName="GTEX FC"
          subjectName="Tunde Bakare"
          subjectRole="First-Team Manager"
          primaryColor="#10b981"
          secondaryColor="#0f172a"
          title="3D First-Day Training Ground Arrival"
          badgeText="OFFICIAL CLUB UNVEILING"
          className="!h-screen !min-h-0"
        />
      </main>
    );
  }

  if (only === "academy") {
    return (
      <main className="grid min-h-screen grid-cols-2 gap-3 bg-[#07111c] p-3 text-white">
        <GtexSceneViewport
          sceneId="wonderkid_emergence"
          clubName="GTEX FC"
          subjectName="Academy Prodigy"
          primaryColor="#0f766e"
          secondaryColor="#d4a24c"
          title="Wonderkid walkout"
          badgeText="PITCH 3"
          className="!h-[90vh] !min-h-0"
        />
        <GtexSceneViewport
          sceneId="academy_upgrade"
          clubName="GTEX FC"
          subjectName="Youth Complex"
          primaryColor="#0f766e"
          secondaryColor="#d4a24c"
          title="Youth academy campus"
          badgeText="ACADEMY"
          className="!h-[90vh] !min-h-0"
        />
      </main>
    );
  }

  if (only === "campus") {
    return (
      <main className="min-h-screen bg-[#07111c] p-4 text-white">
        <CampusBuilder3D
          gridWidth={24}
          gridHeight={18}
          zones={[]}
          placedModules={[]}
          moduleCatalog={[]}
          selectedInstanceId={null}
          onSelectInstance={() => undefined}
          activeBuildModuleKey={null}
          onClearBuildMode={() => undefined}
          onPlaceNewModule={() => undefined}
          onMoveModule={() => undefined}
          onDemolishModule={() => undefined}
        />
      </main>
    );
  }

  if (only === "headquarters") {
    return (
      <main className="min-h-screen bg-[#07111c] text-white">
        <ClubOperationsCentre3D clubId="review-club" previewHub={HEADQUARTERS_PREVIEW} />
      </main>
    );
  }

  if (only === "jet") {
    return (
      <main className="h-screen bg-black text-white">
        <PrestigeShowroomScene
          assetName="Executive jet"
          assetCategory="jet"
          meshArchetype="private_jet"
          modelName="Gulfstream"
          clubName="GTEX FC"
          primaryColor="#10b981"
          secondaryColor="#d4a24c"
          compact={false}
          className="h-screen rounded-none border-0"
        />
      </main>
    );
  }

  if (only === "takeover") {
    return (
      <main className="min-h-screen bg-[#07111c] text-white">
        <GtexSceneViewport
          sceneId="club_takeover"
          clubName="Harbour Athletic"
          primaryColor="#0f766e"
          secondaryColor="#d4a24c"
          title="The club is yours"
          badgeText="OWNERSHIP"
          className="!h-screen !min-h-0"
        />
      </main>
    );
  }

  const scenes: Array<{ id: typeof activeScene; label: string }> = [
    { id: "broadcast", label: "3D Broadcast" },
    { id: "match2d", label: "2D / 2.5D Match" },
    { id: "kit", label: "Kit Close-Up" },
    { id: "press", label: "Press Room" },
    { id: "gift", label: "Gift Engine" },
    { id: "takeover", label: "Takeover" },
    { id: "showroom", label: "Showroom" },
  ];

  // Mount only ONE WebGL stage at a time so concurrent RAF contexts never contend for GPU frame time.
  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <nav className="sticky top-0 z-30 flex flex-wrap items-center gap-1.5 border-b border-white/10 bg-slate-950/95 px-4 py-2 backdrop-blur">
        <span className="mr-2 text-[10px] font-black uppercase tracking-widest text-emerald-300">
          GTEX Visual Review
        </span>
        {scenes.map((scene) => (
          <button
            key={scene.id}
            type="button"
            onClick={() => setActiveScene(scene.id)}
            className={`rounded border px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider transition-colors ${
              activeScene === scene.id
                ? "border-emerald-400 bg-emerald-500/20 text-emerald-200"
                : "border-white/10 bg-slate-900 text-slate-300 hover:text-white"
            }`}
          >
            {scene.label}
          </button>
        ))}
        <LiveFpsPill />
      </nav>

      {activeScene === "broadcast" && (
        <section id="broadcast" className="h-[calc(100vh-44px)]">
          {match ? (
            <MatchPitchLiveScene
              matchViewState={match}
              isLive
              qualityTier="medium"
              stadiumTier={2}
              weatherPreset="clear_night"
              initialCameraMode="fm_director"
              bloomEnabled={false}
              playbackSpeed={2}
              isPaused={false}
              className="h-full"
            />
          ) : (
            <div className="grid h-full place-items-center text-sm text-slate-400">Loading the showcase match</div>
          )}
        </section>
      )}

      {activeScene === "match2d" && <Match2DReviewStage match={match} />}

      {activeScene === "kit" && (
        <section id="kit" className="bg-slate-950">
          <KitCloseUp />
        </section>
      )}

      {activeScene === "press" && (
        <section id="press" className="bg-slate-950 p-4">
          <PressRoomStage clubName="Harbour Athletic" scoreLine="FT 2 - 1" primaryColor="#C8102E" />
          <div className="mt-3 rounded border border-white/10 bg-slate-900 p-3 text-sm text-slate-200">
            <p className="text-[11px] font-bold text-sky-300">Matchday Wire</p>
            <p className="mt-1 italic">How do you see the second half after the equaliser?</p>
            <button type="button" className="mt-2 rounded border border-white/10 px-3 py-2 text-xs">
              We kept the same shape and asked the wide players to arrive earlier.
            </button>
          </div>
        </section>
      )}

      {activeScene === "gift" && (
        <section id="gift" className="relative h-[640px] bg-black">
          <CinematicGiftingEngine
            soundEnabled={false}
            activeGift={{
              id: "review-coach",
              gift_code: "club_coach",
              gift_name: "Club coach",
              sender: "Review",
              amount: 1,
              rarity: "legendary",
              duration_ms: 600000,
            }}
          />
        </section>
      )}

      {activeScene === "takeover" && (
        <section id="takeover" className="bg-[#07111c] p-4">
          <GtexSceneViewport
            sceneId="club_takeover"
            clubName="Harbour Athletic"
            primaryColor="#0f766e"
            secondaryColor="#d4a24c"
            title="The club is yours"
            badgeText="OWNERSHIP"
          />
        </section>
      )}

      {activeScene === "showroom" && (
        <section id="showroom" className="h-[720px] bg-black">
          <PrestigeShowroomScene
            assetName="Executive convoy"
            assetCategory="vehicle"
            meshArchetype="luxury_suv"
            modelName="Executive SUV"
            clubName="Harbour Athletic"
            primaryColor="#C8102E"
            compact={false}
          />
        </section>
      )}
    </main>
  );
}
