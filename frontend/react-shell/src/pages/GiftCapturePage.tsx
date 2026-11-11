import React, { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { CinematicGiftingEngine, type CinematicGiftEvent } from "@/lib/3d/gifting/CinematicGiftingEngine";

export const GIFT_CAPTURE_SHOTS: CinematicGiftEvent[] = [
  {
    gift_code: "paris_skyline",
    gift_name: "Paris: City of Light",
    sender: "Ayo",
    recipient: "Harbour Athletic",
    amount: 750,
    rarity: "epic",
    animation_key: "city_paris",
    sound_key: "paris_lights_twinkle",
    duration_ms: 5000,
  },
  {
    gift_code: "maracana_stadium",
    gift_name: "Maracana Experience",
    sender: "Ayo",
    recipient: "Harbour Athletic",
    amount: 2500,
    rarity: "legendary",
    animation_key: "stadium_maracana",
    sound_key: "maracana_samba_cheer",
    duration_ms: 5200,
  },
  {
    gift_code: "private_jet",
    gift_name: "Club Owner Private Jet",
    sender: "Ayo",
    recipient: "Harbour Athletic",
    amount: 3500,
    rarity: "legendary",
    animation_key: "luxury_private_jet",
    sound_key: "jet_turbine_flyby",
    duration_ms: 5000,
  },
  {
    gift_code: "superyacht",
    gift_name: "Mediterranean Superyacht",
    sender: "Ayo",
    recipient: "Harbour Athletic",
    amount: 4500,
    rarity: "legendary",
    animation_key: "luxury_superyacht",
    sound_key: "yacht_harbor_chime",
    duration_ms: 5000,
  },
  {
    gift_code: "ballon_dor",
    gift_name: "Ballon d'Or",
    sender: "Ayo",
    recipient: "Harbour Athletic",
    amount: 10000,
    rarity: "mythic",
    animation_key: "ballon_dor",
    sound_key: "stadium_ceremony_roar",
    duration_ms: 5200,
    combo_count: 3,
  },
  {
    gift_code: "bicycle_kick",
    gift_name: "Bicycle Kick",
    sender: "Ayo",
    recipient: "Harbour Athletic",
    amount: 850,
    rarity: "legendary",
    animation_key: "bicycle_kick",
    sound_key: "bicycle_kick_whoosh",
    duration_ms: 4800,
  },
  {
    gift_code: "golden_stadium",
    gift_name: "Golden Sovereign Arena",
    sender: "Ayo",
    recipient: "Harbour Athletic",
    amount: 8000,
    rarity: "mythic",
    animation_key: "golden_stadium_reveal",
    sound_key: "celestial_stadium_choir",
    duration_ms: 5200,
  },
  {
    gift_code: "last_minute_winner",
    gift_name: "Last-Minute Winner",
    sender: "Ayo",
    recipient: "Harbour Athletic",
    amount: 350,
    rarity: "epic",
    animation_key: "last_minute_winner",
    sound_key: "net_ripple_roar",
    duration_ms: 4500,
  },
];

export default function GiftCapturePage() {
  const [params] = useSearchParams();
  const requested = (params.get("gift") || "").trim().toLowerCase();
  const loop = params.get("loop") !== "0";
  const muted = params.get("sound") !== "1";
  const playlist = useMemo(() => {
    if (!requested) return GIFT_CAPTURE_SHOTS;
    const hit = GIFT_CAPTURE_SHOTS.filter(
      (shot) => shot.gift_code === requested || shot.animation_key === requested
    );
    return hit.length ? hit : GIFT_CAPTURE_SHOTS;
  }, [requested]);
  const [index, setIndex] = useState(0);

  useEffect(() => {
    setIndex(0);
  }, [requested]);

  const shot = playlist[index % playlist.length];
  const activeGift: CinematicGiftEvent = {
    ...shot,
    id: `${shot.gift_code}-${index}`,
  };

  return (
    <main
      data-testid="gift-capture-stage"
      data-gift-code={shot.gift_code}
      className="relative h-screen w-screen overflow-hidden bg-slate-950 text-white"
    >
      <div
        aria-hidden
        className="absolute inset-0"
        style={{ background: "#07111f" }}
      />
      <CinematicGiftingEngine
        activeGift={activeGift}
        soundEnabled={!muted}
        onAnimationComplete={() => {
          if (!loop && index >= playlist.length - 1) return;
          setIndex((current) => current + 1);
        }}
      />
    </main>
  );
}
