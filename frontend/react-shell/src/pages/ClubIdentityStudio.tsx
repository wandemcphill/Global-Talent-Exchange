import React, { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import * as THREE from "three";
import {
  ArrowLeft,
  Check,
  Crown,
  Eye,
  Layers,
  Palette,
  RefreshCw,
  Save,
  Shield,
  Shirt,
  Sparkles,
  Trophy,
} from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { disposeScene } from "@/lib/3d/disposeScene";
import { useAuth } from "@/lib/auth";
import { useMyClubs } from "@/lib/owner";
import { Btn, Chip, Loading, Panel } from "@/components/gtex/ui";

const BADGE_SHAPES = ["shield", "round", "diamond", "pennant"] as const;
const ICON_FAMILIES = ["lion", "eagle", "crown", "star", "oak", "bolt", "ball"] as const;
const STYLES = ["traditional", "modern", "metallic"] as const;
const PATTERNS = ["solid", "stripes", "hoops", "sash", "chevron", "gradient"] as const;
const COLLAR_STYLES = ["crew", "v_neck", "polo", "wrap"] as const;
const SLEEVE_STYLES = ["short", "long", "raglan", "cuffed"] as const;

export default function ClubIdentityStudio() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [params] = useSearchParams();
  const { data: myClubs, isLoading: loadingClubs } = useMyClubs();

  const selectedClubId = params.get("club") || myClubs?.[0]?.id || myClubs?.[0]?.club_id || "";

  // Fetch current club identity
  const { data: identityData, isLoading: loadingIdentity, refetch } = useQuery({
    queryKey: ["club-identity", selectedClubId],
    queryFn: async () => {
      if (!selectedClubId) return null;
      return (await api.get(`/clubs/${selectedClubId}/identity`)).data;
    },
    enabled: !!selectedClubId,
  });

  const [activeTab, setActiveTab] = useState<"crest" | "home" | "away" | "third" | "goalkeeper">("crest");
  const [busySaving, setBusySaving] = useState(false);
  const [aiPrompt, setAiPrompt] = useState("");
  const [aiBusy, setAiBusy] = useState(false);
  const [aiNote, setAiNote] = useState("");

  // Crest Studio State
  const [crestShape, setCrestShape] = useState<string>("shield");
  const [crestIcon, setCrestIcon] = useState<string>("lion");
  const [crestStyle, setCrestStyle] = useState<string>("traditional");
  const [crestInitials, setCrestInitials] = useState<string>("FC");
  const [trophyStars, setTrophyStars] = useState<number>(1);
  const [crestPrimaryColor, setCrestPrimaryColor] = useState<string>("#1E3A8A");
  const [crestSecondaryColor, setCrestSecondaryColor] = useState<string>("#FFFFFF");
  const [crestAccentColor, setCrestAccentColor] = useState<string>("#F59E0B");

  // Uniform Set State
  const [kits, setKits] = useState<Record<string, any>>({
    home: {
      primary_color: "#1E3A8A",
      secondary_color: "#FFFFFF",
      accent_color: "#F59E0B",
      pattern_type: "stripes",
      collar_style: "crew",
      sleeve_style: "short",
      shorts_color: "#1E3A8A",
      socks_color: "#FFFFFF",
      front_text: "FC",
    },
    away: {
      primary_color: "#F8FAFC",
      secondary_color: "#1E3A8A",
      accent_color: "#F59E0B",
      pattern_type: "sash",
      collar_style: "v_neck",
      sleeve_style: "raglan",
      shorts_color: "#F8FAFC",
      socks_color: "#1E3A8A",
      front_text: "FC",
    },
    third: {
      primary_color: "#0F172A",
      secondary_color: "#F59E0B",
      accent_color: "#38BDF8",
      pattern_type: "chevron",
      collar_style: "polo",
      sleeve_style: "short",
      shorts_color: "#0F172A",
      socks_color: "#0F172A",
      front_text: "FC ALT",
    },
    goalkeeper: {
      primary_color: "#10B981",
      secondary_color: "#064E3B",
      accent_color: "#FACC15",
      pattern_type: "gradient",
      collar_style: "wrap",
      sleeve_style: "long",
      shorts_color: "#064E3B",
      socks_color: "#10B981",
      front_text: "FC GK",
    },
  });

  // Load existing profile values into studio state
  useEffect(() => {
    if (identityData) {
      if (identityData.badge_profile) {
        const b = identityData.badge_profile;
        if (b.shape) setCrestShape(b.shape);
        if (b.icon_family) setCrestIcon(b.icon_family);
        if (b.initials) setCrestInitials(b.initials);
        if (b.trophy_star_count !== undefined) setTrophyStars(b.trophy_star_count);
        if (b.primary_color) setCrestPrimaryColor(b.primary_color);
        if (b.secondary_color) setCrestSecondaryColor(b.secondary_color);
        if (b.accent_color) setCrestAccentColor(b.accent_color);
      }
      if (identityData.jersey_set) {
        setKits((prev) => ({
          home: { ...prev.home, ...(identityData.jersey_set.home || {}) },
          away: { ...prev.away, ...(identityData.jersey_set.away || {}) },
          third: { ...prev.third, ...(identityData.jersey_set.third || {}) },
          goalkeeper: { ...prev.goalkeeper, ...(identityData.jersey_set.goalkeeper || {}) },
        }));
      }
    }
  }, [identityData]);

  // 3D Canvas Preview Mount
  const canvasMountRef = useRef<HTMLDivElement | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const mannequinMeshRef = useRef<THREE.Group | null>(null);
  const [rotationAngle, setRotationAngle] = useState(0);

  useEffect(() => {
    if (!canvasMountRef.current) return;
    const w = canvasMountRef.current.clientWidth || 400;
    const h = canvasMountRef.current.clientHeight || 450;

    const scene = new THREE.Scene();
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(40, w / h, 0.1, 100);
    camera.position.set(0, 1.8, 5.5);
    camera.lookAt(0, 1.2, 0);

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
      renderer.setSize(w, h);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      rendererRef.current = renderer;
      canvasMountRef.current.appendChild(renderer.domElement);
    } catch {
      return;
    }

    // Studio Lights
    const ambient = new THREE.AmbientLight(0xffffff, 0.9);
    scene.add(ambient);

    const keyLight = new THREE.DirectionalLight(0xffffff, 1.5);
    keyLight.position.set(5, 8, 6);
    scene.add(keyLight);

    const rimLight = new THREE.DirectionalLight(0x38bdf8, 1.0);
    rimLight.position.set(-6, 4, -4);
    scene.add(rimLight);

    // 3D Mannequin Group
    const mannequin = new THREE.Group();
    mannequinMeshRef.current = mannequin;

    // Torso Shirt
    const shirtGeo = new THREE.CylinderGeometry(0.72, 0.62, 1.4, 24);
    const activeKit = activeTab === "crest" ? kits.home : kits[activeTab];
    const shirtMat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(activeKit.primary_color),
      roughness: 0.4,
      metalness: 0.1,
    });
    const shirt = new THREE.Mesh(shirtGeo, shirtMat);
    shirt.position.y = 1.4;
    shirt.name = "shirt";
    mannequin.add(shirt);

    // Shoulders & Sleeves
    const leftArmGeo = new THREE.CylinderGeometry(0.2, 0.18, 0.8, 16);
    const armMat = new THREE.MeshStandardMaterial({ color: new THREE.Color(activeKit.primary_color) });
    const leftArm = new THREE.Mesh(leftArmGeo, armMat);
    leftArm.position.set(-0.95, 1.6, 0);
    leftArm.rotation.z = 0.3;
    leftArm.name = "leftArm";
    mannequin.add(leftArm);

    const rightArm = new THREE.Mesh(leftArmGeo, armMat);
    rightArm.position.set(0.95, 1.6, 0);
    rightArm.rotation.z = -0.3;
    rightArm.name = "rightArm";
    mannequin.add(rightArm);

    // Shorts
    const shortsGeo = new THREE.CylinderGeometry(0.64, 0.68, 0.65, 24);
    const shortsMat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(activeKit.shorts_color || activeKit.primary_color),
      roughness: 0.5,
    });
    const shorts = new THREE.Mesh(shortsGeo, shortsMat);
    shorts.position.y = 0.45;
    shorts.name = "shorts";
    mannequin.add(shorts);

    // Socks & Base
    const sockGeo = new THREE.CylinderGeometry(0.18, 0.16, 0.8, 16);
    const sockMat = new THREE.MeshStandardMaterial({
      color: new THREE.Color(activeKit.socks_color || activeKit.secondary_color),
    });
    const leftSock = new THREE.Mesh(sockGeo, sockMat);
    leftSock.position.set(-0.35, -0.3, 0);
    leftSock.name = "leftSock";
    mannequin.add(leftSock);

    const rightSock = new THREE.Mesh(sockGeo, sockMat);
    rightSock.position.set(0.35, -0.3, 0);
    rightSock.name = "rightSock";
    mannequin.add(rightSock);

    scene.add(mannequin);

    let animId: number;
    const handleContextLost = (e: Event) => {
      e.preventDefault();
    };
    renderer.domElement.addEventListener("webglcontextlost", handleContextLost, false);

    const render = () => {
      if (typeof document === "undefined" || !document.hidden) {
        renderer.render(scene, camera);
      }
      animId = requestAnimationFrame(render);
    };
    render();

    return () => {
      cancelAnimationFrame(animId);
      renderer.domElement.removeEventListener("webglcontextlost", handleContextLost);
      disposeScene(scene, rendererRef.current);
      rendererRef.current = null;
    };
  }, []);

  // Update 3D Mannequin Colors when active tab or kit state changes
  useEffect(() => {
    if (!mannequinMeshRef.current) return;
    const activeKit = activeTab === "crest" ? kits.home : kits[activeTab];
    if (!activeKit) return;

    mannequinMeshRef.current.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        if (child.name === "shirt" || child.name === "leftArm" || child.name === "rightArm") {
          (child.material as THREE.MeshStandardMaterial).color.set(activeKit.primary_color);
        } else if (child.name === "shorts") {
          (child.material as THREE.MeshStandardMaterial).color.set(activeKit.shorts_color || activeKit.primary_color);
        } else if (child.name === "leftSock" || child.name === "rightSock") {
          (child.material as THREE.MeshStandardMaterial).color.set(activeKit.socks_color || activeKit.secondary_color);
        }
      }
    });
  }, [activeTab, kits]);

  // Rotate mannequin with slider
  const handleRotate = (angle: number) => {
    setRotationAngle(angle);
    if (mannequinMeshRef.current) {
      mannequinMeshRef.current.rotation.y = (angle * Math.PI) / 180;
    }
  };

  // Conversational AI edit handler
  const handleAiEdit = async () => {
    if (!aiPrompt.trim()) return;
    setAiBusy(true);
    try {
      const activeKit = activeTab === "crest" ? kits.home : kits[activeTab];
      const crestData = {
        shape: crestShape,
        icon_family: crestIcon,
        style: crestStyle,
        initials: crestInitials,
        trophy_stars: trophyStars,
        primary_color: crestPrimaryColor,
        secondary_color: crestSecondaryColor,
        accent_color: crestAccentColor,
      };
      const { data } = await api.post("/clubs/studio/edit", {
        current_kit: activeKit,
        current_crest: crestData,
        instruction: aiPrompt.trim(),
      });

      if (data.crest) {
        if (data.crest.shape) setCrestShape(data.crest.shape);
        if (data.crest.icon_family) setCrestIcon(data.crest.icon_family);
        if (data.crest.primary_color) setCrestPrimaryColor(data.crest.primary_color);
        if (data.crest.accent_color) setCrestAccentColor(data.crest.accent_color);
      }
      if (data.kit) {
        const slot = activeTab === "crest" ? "home" : activeTab;
        setKits((prev) => ({
          ...prev,
          [slot]: { ...prev[slot], ...data.kit },
        }));
      }
      setAiNote(data.summary || "Design refined!");
      setAiPrompt("");
      toast.success(data.summary || "Studio parameters updated!");
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setAiBusy(false);
    }
  };

  // Save all custom identity changes to backend
  const handleSaveIdentity = async () => {
    if (!selectedClubId) return;
    setBusySaving(true);
    try {
      // 1. Update Identity & Badge
      await api.patch(`/clubs/${selectedClubId}/identity`, {
        short_club_code: crestInitials.toUpperCase(),
        badge_profile: {
          shape: crestShape,
          icon_family: crestIcon,
          initials: crestInitials.toUpperCase(),
          trophy_star_count: trophyStars,
          primary_color: crestPrimaryColor,
          secondary_color: crestSecondaryColor,
          accent_color: crestAccentColor,
        },
        color_palette: {
          palette_name: "custom",
          primary_color: kits.home.primary_color,
          secondary_color: kits.home.secondary_color,
          accent_color: kits.home.accent_color,
          shorts_color: kits.home.shorts_color,
          socks_color: kits.home.socks_color,
        },
      });

      // 2. Update Jersey Set
      await api.patch(`/clubs/${selectedClubId}/jerseys`, {
        home: kits.home,
        away: kits.away,
        third: kits.third,
        goalkeeper: kits.goalkeeper,
      });

      await qc.invalidateQueries({ queryKey: ["club-identity", selectedClubId] });
      refetch();
      toast.success("Official Club Identity & Uniforms successfully saved and published!");
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusySaving(false);
    }
  };

  if (loadingClubs || (selectedClubId && loadingIdentity)) {
    return <Loading label="Loading 3D Club Identity Studio" />;
  }

  return (
    <div className="gx-pitch-grid min-h-screen bg-[#070B11] px-4 py-8 sm:px-8" data-testid="club-identity-studio">
      <div className="mx-auto max-w-[1400px]">
        {/* Header toolbar */}
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-4">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="flex h-8 w-8 items-center justify-center rounded border border-white/10 bg-slate-900 text-slate-300 hover:bg-slate-800"
            >
              <ArrowLeft size={16} />
            </button>
            <div>
              <p className="gx-eyebrow text-emerald-400">GTEX AI Club Identity Studio</p>
              <h1 className="text-xl font-bold uppercase tracking-wider text-white">
                3D Crest & Matchday Uniform Designer
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Btn
              variant="primary"
              disabled={busySaving}
              onClick={handleSaveIdentity}
              data-testid="save-club-identity-button"
            >
              <Save size={15} className="mr-1.5" />
              {busySaving ? "Publishing…" : "Publish Official Kit Set"}
            </Btn>
          </div>
        </div>

        {/* Studio Workspace Layout */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          {/* Left Column: 3D Viewport Mannequin */}
          <div className="flex flex-col rounded border border-white/10 bg-slate-950/70 p-4 lg:col-span-5">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                3D Uniform Turntable
              </span>
              <div className="flex gap-1 text-[11px]">
                {[
                  { label: "Front", deg: 0 },
                  { label: "Side", deg: 90 },
                  { label: "Back", deg: 180 },
                ].map((preset) => (
                  <button
                    type="button"
                    key={preset.label}
                    onClick={() => handleRotate(preset.deg)}
                    className="rounded bg-white/10 px-2 py-0.5 text-slate-300 hover:bg-white/20"
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Three.js Canvas Container */}
            <div ref={canvasMountRef} className="relative h-[420px] w-full flex-1">
              <div className="absolute bottom-2 left-2 z-10 rounded bg-black/60 px-2 py-1 text-[10px] text-slate-400">
                360° Studio Lighting · PBR Shaders
              </div>
            </div>

            {/* Rotation Slider */}
            <div className="mt-3 flex items-center gap-3 border-t border-white/10 pt-3">
              <span className="text-[11px] text-slate-400">Rotate</span>
              <input
                type="range"
                min="0"
                max="360"
                value={rotationAngle}
                onChange={(e) => handleRotate(Number(e.target.value))}
                className="w-full cursor-pointer accent-emerald-400"
              />
              <span className="gx-mono text-xs text-emerald-400">{rotationAngle}°</span>
            </div>
          </div>

          {/* Right Column: Customization Controls & AI Assistant */}
          <div className="flex flex-col gap-6 lg:col-span-7">
            {/* Studio Navigation Tabs */}
            <div className="flex flex-wrap gap-2 rounded border border-white/10 bg-slate-950/50 p-2">
              <button
                type="button"
                onClick={() => setActiveTab("crest")}
                className={`flex items-center gap-2 rounded px-3 py-1.5 text-xs font-bold uppercase transition-colors ${
                  activeTab === "crest" ? "bg-emerald-500 text-white" : "text-slate-400 hover:text-white"
                }`}
              >
                <Shield size={14} /> Crest & Badge
              </button>
              {(["home", "away", "third", "goalkeeper"] as const).map((slot) => (
                <button
                  type="button"
                  key={slot}
                  onClick={() => setActiveTab(slot)}
                  className={`flex items-center gap-1.5 rounded px-3 py-1.5 text-xs font-bold uppercase transition-colors ${
                    activeTab === slot ? "bg-emerald-500 text-white" : "text-slate-400 hover:text-white"
                  }`}
                >
                  <Shirt size={14} /> {slot} Kit
                </button>
              ))}
            </div>

            {/* Crest Designer Controls */}
            {activeTab === "crest" && (
              <Panel eyebrow="Vector Heraldry" title="Club Crest & Badge Architecture" className="w-full">
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <label className="text-[11px] font-semibold uppercase text-slate-300">Shield Shape</label>
                    <div className="mt-1.5 grid grid-cols-2 gap-1.5">
                      {BADGE_SHAPES.map((sh) => (
                        <button
                          type="button"
                          key={sh}
                          onClick={() => setCrestShape(sh)}
                          className={`rounded border p-2 text-xs font-semibold capitalize ${
                            crestShape === sh
                              ? "border-emerald-500 bg-emerald-500/20 text-emerald-300"
                              : "border-white/10 bg-slate-900/50 text-slate-400"
                          }`}
                        >
                          {sh}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="text-[11px] font-semibold uppercase text-slate-300">Emblem Symbol</label>
                    <div className="mt-1.5 grid grid-cols-3 gap-1.5">
                      {ICON_FAMILIES.map((ic) => (
                        <button
                          type="button"
                          key={ic}
                          onClick={() => setCrestIcon(ic)}
                          className={`rounded border p-2 text-xs font-semibold capitalize ${
                            crestIcon === ic
                              ? "border-emerald-500 bg-emerald-500/20 text-emerald-300"
                              : "border-white/10 bg-slate-900/50 text-slate-400"
                          }`}
                        >
                          {ic}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="text-[11px] font-semibold uppercase text-slate-300">Initials Wordmark</label>
                    <input
                      className="gx-input mt-1.5 uppercase"
                      maxLength={4}
                      value={crestInitials}
                      onChange={(e) => setCrestInitials(e.target.value)}
                    />
                  </div>

                  <div>
                    <label className="text-[11px] font-semibold uppercase text-slate-300">Trophy Stars Count</label>
                    <input
                      type="number"
                      min={0}
                      max={5}
                      className="gx-input mt-1.5"
                      value={trophyStars}
                      onChange={(e) => setTrophyStars(Math.max(0, parseInt(e.target.value, 10) || 0))}
                    />
                  </div>

                  <div className="sm:col-span-2">
                    <label className="text-[11px] font-semibold uppercase text-slate-300">Color Palette</label>
                    <div className="mt-1.5 flex gap-4">
                      <label className="flex items-center gap-2 text-xs text-slate-400">
                        Primary:
                        <input
                          type="color"
                          value={crestPrimaryColor}
                          onChange={(e) => setCrestPrimaryColor(e.target.value)}
                          className="h-8 w-10 cursor-pointer rounded border border-white/20 bg-transparent"
                        />
                      </label>
                      <label className="flex items-center gap-2 text-xs text-slate-400">
                        Secondary:
                        <input
                          type="color"
                          value={crestSecondaryColor}
                          onChange={(e) => setCrestSecondaryColor(e.target.value)}
                          className="h-8 w-10 cursor-pointer rounded border border-white/20 bg-transparent"
                        />
                      </label>
                      <label className="flex items-center gap-2 text-xs text-slate-400">
                        Accent:
                        <input
                          type="color"
                          value={crestAccentColor}
                          onChange={(e) => setCrestAccentColor(e.target.value)}
                          className="h-8 w-10 cursor-pointer rounded border border-white/20 bg-transparent"
                        />
                      </label>
                    </div>
                  </div>
                </div>
              </Panel>
            )}

            {/* Uniform Kit Controls */}
            {activeTab !== "crest" && (
              <Panel eyebrow={`${activeTab.toUpperCase()} Uniform`} title="Jersey & Kit Tailoring" className="w-full">
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <label className="text-[11px] font-semibold uppercase text-slate-300">Fabric Pattern</label>
                    <div className="mt-1.5 grid grid-cols-3 gap-1.5">
                      {PATTERNS.map((p) => (
                        <button
                          type="button"
                          key={p}
                          onClick={() =>
                            setKits((prev) => ({
                              ...prev,
                              [activeTab]: { ...prev[activeTab], pattern_type: p },
                            }))
                          }
                          className={`rounded border p-2 text-xs font-semibold capitalize ${
                            kits[activeTab].pattern_type === p
                              ? "border-emerald-500 bg-emerald-500/20 text-emerald-300"
                              : "border-white/10 bg-slate-900/50 text-slate-400"
                          }`}
                        >
                          {p}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="text-[11px] font-semibold uppercase text-slate-300">Collar Cut</label>
                    <div className="mt-1.5 grid grid-cols-2 gap-1.5">
                      {COLLAR_STYLES.map((c) => (
                        <button
                          type="button"
                          key={c}
                          onClick={() =>
                            setKits((prev) => ({
                              ...prev,
                              [activeTab]: { ...prev[activeTab], collar_style: c },
                            }))
                          }
                          className={`rounded border p-2 text-xs font-semibold capitalize ${
                            kits[activeTab].collar_style === c
                              ? "border-emerald-500 bg-emerald-500/20 text-emerald-300"
                              : "border-white/10 bg-slate-900/50 text-slate-400"
                          }`}
                        >
                          {c.replace("_", " ")}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="text-[11px] font-semibold uppercase text-slate-300">Sleeves Style</label>
                    <div className="mt-1.5 grid grid-cols-2 gap-1.5">
                      {SLEEVE_STYLES.map((s) => (
                        <button
                          type="button"
                          key={s}
                          onClick={() =>
                            setKits((prev) => ({
                              ...prev,
                              [activeTab]: { ...prev[activeTab], sleeve_style: s },
                            }))
                          }
                          className={`rounded border p-2 text-xs font-semibold capitalize ${
                            kits[activeTab].sleeve_style === s
                              ? "border-emerald-500 bg-emerald-500/20 text-emerald-300"
                              : "border-white/10 bg-slate-900/50 text-slate-400"
                          }`}
                        >
                          {s}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="text-[11px] font-semibold uppercase text-slate-300">Chest Text / Motto</label>
                    <input
                      className="gx-input mt-1.5 uppercase"
                      value={kits[activeTab].front_text || ""}
                      onChange={(e) =>
                        setKits((prev) => ({
                          ...prev,
                          [activeTab]: { ...prev[activeTab], front_text: e.target.value },
                        }))
                      }
                    />
                  </div>

                  <div className="sm:col-span-2">
                    <label className="text-[11px] font-semibold uppercase text-slate-300">Uniform Tones</label>
                    <div className="mt-1.5 flex flex-wrap gap-4">
                      <label className="flex items-center gap-2 text-xs text-slate-400">
                        Jersey Base:
                        <input
                          type="color"
                          value={kits[activeTab].primary_color}
                          onChange={(e) =>
                            setKits((prev) => ({
                              ...prev,
                              [activeTab]: { ...prev[activeTab], primary_color: e.target.value },
                            }))
                          }
                          className="h-8 w-10 cursor-pointer rounded border border-white/20 bg-transparent"
                        />
                      </label>
                      <label className="flex items-center gap-2 text-xs text-slate-400">
                        Secondary:
                        <input
                          type="color"
                          value={kits[activeTab].secondary_color}
                          onChange={(e) =>
                            setKits((prev) => ({
                              ...prev,
                              [activeTab]: { ...prev[activeTab], secondary_color: e.target.value },
                            }))
                          }
                          className="h-8 w-10 cursor-pointer rounded border border-white/20 bg-transparent"
                        />
                      </label>
                      <label className="flex items-center gap-2 text-xs text-slate-400">
                        Shorts:
                        <input
                          type="color"
                          value={kits[activeTab].shorts_color || kits[activeTab].primary_color}
                          onChange={(e) =>
                            setKits((prev) => ({
                              ...prev,
                              [activeTab]: { ...prev[activeTab], shorts_color: e.target.value },
                            }))
                          }
                          className="h-8 w-10 cursor-pointer rounded border border-white/20 bg-transparent"
                        />
                      </label>
                      <label className="flex items-center gap-2 text-xs text-slate-400">
                        Socks:
                        <input
                          type="color"
                          value={kits[activeTab].socks_color || kits[activeTab].secondary_color}
                          onChange={(e) =>
                            setKits((prev) => ({
                              ...prev,
                              [activeTab]: { ...prev[activeTab], socks_color: e.target.value },
                            }))
                          }
                          className="h-8 w-10 cursor-pointer rounded border border-white/20 bg-transparent"
                        />
                      </label>
                    </div>
                  </div>
                </div>
              </Panel>
            )}

            {/* Natural Language AI Design Assistant */}
            <div className="rounded border border-emerald-500/30 bg-emerald-950/20 p-4">
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-emerald-300">
                <Sparkles size={14} />
                <span>Conversational AI Studio Assistant</span>
              </div>
              <p className="mt-1 text-xs text-slate-400">
                Instruct the AI designer in plain English to tune colors, patterns, and badges.
              </p>
              <div className="mt-3 flex gap-2">
                <input
                  className="gx-input flex-1 text-xs"
                  placeholder="e.g. give the away kit a navy diagonal sash with golden borders and polo collar"
                  value={aiPrompt}
                  onChange={(e) => setAiPrompt(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleAiEdit()}
                />
                <Btn disabled={aiBusy || !aiPrompt.trim()} onClick={handleAiEdit}>
                  {aiBusy ? "Applying…" : "Apply AI Edit"}
                </Btn>
              </div>
              {aiNote && <p className="mt-2 text-xs text-emerald-400">✓ {aiNote}</p>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
