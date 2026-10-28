import React, { useId, useMemo, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { toast } from "sonner";
import {
  useActiveClub,
  useClub,
  useClubShowroom,
  useClubStory,
  useRefreshOwner,
  fmt,
} from "@/lib/owner";
import { api } from "@/lib/api";
import { Loading, Btn } from "@/components/gtex/ui";
import { Cinema3DStage } from "@/components/gtex/Cinema3DStage";
import {
  Sparkles,
  Plane,
  Watch,
  Building,
  Car,
  Gift,
  CheckCircle,
  Coins,
  ExternalLink,
  LockKeyhole,
  X,
  PackageCheck,
  ShieldCheck,
  BookOpen,
  Newspaper,
  Inbox,
  Gauge,
  HelpCircle,
} from "lucide-react";

export function Showroom() {
  const { clubId: routeClubId } = useParams<{ clubId?: string }>();
  const { active, clubs } = useActiveClub();
  const clubId = routeClubId || active?.club_id;
  const refresh = useRefreshOwner();

  const { data: clubDetail } = useClub(clubId);
  const { data: storyData } = useClubStory(clubId);
  const { data: showroomData, isLoading } = useClubShowroom(clubId);

  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [acquiringItem, setAcquiringItem] = useState<any | null>(null);
  const [giftingItem, setGiftingItem] = useState<any | null>(null);
  const [recipientType, setRecipientType] = useState<"player" | "staff">("player");
  const [selectedStaffRole, setSelectedStaffRole] = useState<string>("first_team_manager");
  const [selectedPlayerId, setSelectedPlayerId] = useState<string>("");
  const [giftNote, setGiftNote] = useState<string>("");
  const [busyItem, setBusyItem] = useState<string | null>(null);
  const [purchaseReceipt, setPurchaseReceipt] = useState<any | null>(null);
  const [giftReceipt, setGiftReceipt] = useState<any | null>(null);

  const purchaseIntentKeys = useRef(new Map<string, string>());
  const giftIntentKeys = useRef(new Map<string, string>());

  const stableIntentKey = (mapRef: React.MutableRefObject<Map<string, string>>, intent: string, prefix: string) => {
    let key = mapRef.current.get(intent);
    if (!key) {
      key = `${prefix}-${clubId || "club"}-${intent.replace(/[^a-zA-Z0-9_-]/g, "_")}-${Date.now()}`;
      mapRef.current.set(intent, key);
    }
    return key;
  };

  const catalog: any[] = showroomData?.catalog || [];
  const ownedAssets: any[] = showroomData?.owned_assets || [];

  // Squad and regens from club details or story relationships
  const squad: any[] = useMemo(() => {
    if (clubDetail?.squad && Array.isArray(clubDetail.squad) && clubDetail.squad.length > 0) {
      return clubDetail.squad;
    }
    if (storyData?.relationships?.players && Array.isArray(storyData.relationships.players)) {
      return storyData.relationships.players;
    }
    return [];
  }, [clubDetail, storyData]);

  const eligibleRegens = useMemo(() => {
    return squad.filter((p: any) => Boolean(p.is_regen));
  }, [squad]);

  const selectedPlayer = useMemo(() => {
    return squad.find((p: any) => p.id === selectedPlayerId) || eligibleRegens[0] || null;
  }, [squad, eligibleRegens, selectedPlayerId]);

  const clubCash = clubDetail?.economy?.cash_gtex ?? active?.cash ?? 0;
  const clubPrestige = showroomData?.club_prestige ?? clubDetail?.health?.prestige ?? 60;
  const prestigeTierNum = showroomData?.prestige_tier ?? (clubPrestige >= 90 ? 1 : clubPrestige >= 75 ? 2 : clubPrestige >= 55 ? 3 : clubPrestige >= 35 ? 4 : 5);
  const prestigeTierLabel = prestigeTierNum === 1 ? "Tier 1: Global Superclub" : prestigeTierNum === 2 ? "Tier 2: Continental Challenger" : prestigeTierNum === 3 ? "Tier 3: National Contender" : prestigeTierNum === 4 ? "Tier 4: Regional Pioneer" : "Tier 5: Grassroots Foundation";

  const keyOf = (it: any) => it?.catalog_key || it?.id || it?.sku || "";

  const assetImage = (it: any) =>
    it?.image_url || it?.previewFile || it?.preview_file || it?.hero_image_url || "";

  const formatPrice = (it: any) => fmt(it?.price_gtex ?? it?.price ?? 0);

  const categories = [
    { key: "all", label: "All Prestige" },
    { key: "jet", label: "Fleet Aviation", icon: Plane },
    { key: "vehicle", label: "Vehicles & Maritime", icon: Car },
    { key: "watch", label: "Horology", icon: Watch },
    { key: "hospitality", label: "VIP Suites", icon: Building },
    { key: "facility", label: "Infrastructure", icon: Building },
    { key: "owned", label: `Owned Assets (${ownedAssets.length})`, icon: PackageCheck },
  ];

  const filteredItems = useMemo(() => {
    if (selectedCategory === "all") return catalog;
    if (selectedCategory === "owned") return ownedAssets;
    if (selectedCategory === "hospitality") {
      return catalog.filter((it: any) => ["hospitality", "suite", "box"].includes(it.category));
    }
    if (selectedCategory === "vehicle") {
      return catalog.filter((it: any) => ["vehicle", "car", "yacht"].includes(it.category));
    }
    return catalog.filter((it: any) => it.category === selectedCategory);
  }, [catalog, ownedAssets, selectedCategory]);

  const handlePurchase = async (item: any) => {
    if (!clubId) return;
    const key = keyOf(item);
    const purchaseIntent = `purchase:${key}`;
    setBusyItem(key);
    try {
      const idempotencyKey = stableIntentKey(purchaseIntentKeys, purchaseIntent, "showroom-purchase");
      const res = await api.post(`/owner/clubs/${clubId}/showroom/purchase`, {
        catalog_key: key,
        custom_name: item.name,
        idempotency_key: idempotencyKey,
      });
      purchaseIntentKeys.current.delete(purchaseIntent);
      const resultData = res.data;
      setAcquiringItem(null);
      setPurchaseReceipt({ item, result: resultData });
      toast.success(
        resultData?.broadcast_globally
          ? `GTEX verified ${item.name}; announcement dispatched to global wire!`
          : `GTEX confirmed ${item.name} for your club collection.`
      );
      refresh();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail?.detail || e?.response?.data?.detail || "Acquisition failed.");
    } finally {
      setBusyItem(null);
    }
  };

  const handleGift = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!clubId || !giftingItem) return;
    if (recipientType === "player" && !selectedPlayerId) return;
    const key = keyOf(giftingItem);
    const targetIdentifier = recipientType === "player" ? selectedPlayerId : selectedStaffRole;
    const giftIntent = `gift:${key}:${targetIdentifier}`;
    setBusyItem(`gift:${key}`);
    try {
      const idempotencyKey = stableIntentKey(giftIntentKeys, giftIntent, "showroom-gift");
      const res = await api.post(`/owner/clubs/${clubId}/showroom/gift`, {
        player_id: recipientType === "player" ? selectedPlayerId : undefined,
        recipient_type: recipientType,
        staff_role: recipientType === "staff" ? selectedStaffRole : undefined,
        catalog_key: key,
        note: giftNote.trim(),
        idempotency_key: idempotencyKey,
      });
      giftIntentKeys.current.delete(giftIntent);
      const resultData = res.data;
      const recipient =
        recipientType === "player"
          ? resultData?.player || selectedPlayer
          : { name: selectedStaffRole.replace(/_/g, " ").toUpperCase(), role: selectedStaffRole };
      setGiftingItem(null);
      setSelectedPlayerId("");
      setGiftNote("");
      setGiftReceipt({ item: giftingItem, player: recipient, note: giftNote.trim(), result: resultData, recipientType });
      toast.success(
        recipientType === "staff"
          ? `Delivered luxury gift to ${recipient.name} (+15 Mood, +3 Loyalty)!`
          : resultData?.broadcast_event
          ? `GTEX confirmed ${giftingItem.name} for ${recipient?.name || "your academy regen"}; verified broadcast published!`
          : `GTEX recorded luxury gift for ${recipient?.name || "your academy regen"}.`
      );
      refresh();
    } catch (e: any) {
      toast.error(e?.response?.data?.detail?.detail || e?.response?.data?.detail || "Luxury gift delivery failed.");
    } finally {
      setBusyItem(null);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-8" data-testid="showroom-screen">
      {/* Surface Demarcation & Navigation Bridge */}
      <nav aria-label="Showroom Surface Directory" className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-xs">
        <div className="flex items-center gap-2 rounded-xl border border-amber-400/40 bg-amber-400/10 px-3 py-2 text-amber-200 shadow-sm">
          <Sparkles className="h-4 w-4 shrink-0 text-amber-300" />
          <div className="min-w-0">
            <div className="text-[10px] uppercase font-black tracking-wider text-amber-400">Current Surface</div>
            <div className="truncate font-bold text-white">Owner Showroom</div>
          </div>
        </div>
        <Link
          to="/app/story"
          className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/60 px-3 py-2 text-slate-300 hover:border-amber-400/40 hover:text-white transition-colors"
          data-testid="link-to-story"
        >
          <BookOpen className="h-4 w-4 shrink-0 text-amber-300" />
          <div className="min-w-0">
            <div className="text-[10px] uppercase font-bold tracking-wider text-slate-500">Club History</div>
            <div className="truncate font-bold">Club Chronicle</div>
          </div>
        </Link>
        <Link
          to="/app/newsroom"
          className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/60 px-3 py-2 text-slate-300 hover:border-blue-400/40 hover:text-white transition-colors"
          data-testid="link-to-newsroom"
        >
          <Newspaper className="h-4 w-4 shrink-0 text-blue-400" />
          <div className="min-w-0">
            <div className="text-[10px] uppercase font-bold tracking-wider text-slate-500">World Editorial</div>
            <div className="truncate font-bold">AI Newsroom</div>
          </div>
        </Link>
        <Link
          to="/app/inbox"
          className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/60 px-3 py-2 text-slate-300 hover:border-purple-400/40 hover:text-white transition-colors"
          data-testid="link-to-inbox"
        >
          <Inbox className="h-4 w-4 shrink-0 text-purple-400" />
          <div className="min-w-0">
            <div className="text-[10px] uppercase font-bold tracking-wider text-slate-500">Private Desk</div>
            <div className="truncate font-bold">Owner Decisions</div>
          </div>
        </Link>
        <Link
          to="/app"
          className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/60 px-3 py-2 text-slate-300 hover:border-emerald-400/40 hover:text-white transition-colors"
          data-testid="link-to-control-center"
        >
          <Gauge className="h-4 w-4 shrink-0 text-emerald-400" />
          <div className="min-w-0">
            <div className="text-[10px] uppercase font-bold tracking-wider text-slate-500">Daily Health</div>
            <div className="truncate font-bold">Control Center</div>
          </div>
        </Link>
      </nav>

      {/* Editorial Header & Gifting Demarcation Banner */}
      <div className="rounded-2xl border border-amber-500/25 bg-gradient-to-br from-slate-900 via-slate-950 to-amber-950/20 p-6 md:p-8 space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-amber-400 text-xs font-black uppercase tracking-[0.2em]">
              <Sparkles className="h-4 w-4" />
              <span>THE BOARDROOM COLLECTION · AUTHORITATIVE PRESTIGE CATALOGUE</span>
            </div>
            <h1 className="text-3xl sm:text-5xl font-black uppercase tracking-tight text-white leading-none">
              Owner Showroom & Luxury Fleet
            </h1>
            <p className="text-xs sm:text-sm text-slate-300 max-w-3xl leading-relaxed">
              Acquire executive aviation, maritime assets, and horology through the club treasury. Present luxury milestone gifts directly to academy regens to boost squad morale and trigger verified broadcasts on the GTEX global wire.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row md:flex-col gap-3 shrink-0">
            <div className="rounded-xl border border-amber-400/30 bg-slate-950/80 px-4 py-3 text-right">
              <div className="text-[10px] uppercase tracking-wider text-slate-400 font-bold">Club Treasury</div>
              <div className="font-mono text-xl font-black text-amber-300">{fmt(clubCash)} GTX</div>
            </div>
            <div className="rounded-xl border border-amber-500/40 bg-amber-950/40 px-4 py-2.5 text-right">
              <div className="text-[10px] uppercase tracking-wider text-amber-300 font-bold">Club Prestige Standing</div>
              <div className="font-mono text-sm font-black text-white">{clubPrestige}/100 · {prestigeTierLabel}</div>
            </div>
          </div>
        </div>

        {/* Prestige System Strategic Mechanics */}
        <div className="rounded-xl border border-amber-400/30 bg-gradient-to-r from-amber-950/40 via-purple-950/30 to-black/50 p-4 text-xs space-y-2">
          <div className="flex items-center gap-2 font-black uppercase tracking-wider text-amber-300">
            <Sparkles size={15} />
            <span>How Prestige Powers Club Development</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-[11px] text-slate-300">
            <div className="rounded-lg bg-black/40 border border-white/5 p-2.5">
              <b className="text-amber-300 block mb-0.5">Academy Intake Ceiling</b>
              Higher Prestige directly raises the max potential of generated regens (+3 to +15 pts).
            </div>
            <div className="rounded-lg bg-black/40 border border-white/5 p-2.5">
              <b className="text-cyan-300 block mb-0.5">Player & Regen Pull</b>
              World-class stars prioritize clubs with high prestige scores in transfer negotiations.
            </div>
            <div className="rounded-lg bg-black/40 border border-white/5 p-2.5">
              <b className="text-purple-300 block mb-0.5">Elite Staff Hiring</b>
              Bypasses marquee wage premiums when hiring top General Managers and HOYDs.
            </div>
          </div>
        </div>

        {/* Demarcation Card: Owner Luxury Gifting vs. Community FanCoin Gifting */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-white/10 text-xs">
          <div className="rounded-xl border border-purple-500/30 bg-purple-500/[0.08] p-4 space-y-1.5 text-purple-200">
            <div className="flex items-center gap-2 font-bold text-purple-300">
              <Gift className="h-4 w-4 shrink-0 text-purple-300" />
              <span className="uppercase tracking-wider text-[11px]">Owner Luxury Gifting (Club GTEX Coin)</span>
            </div>
            <p className="text-slate-300 text-[11px] leading-5">
              Funded strictly via Club GTEX Coin from the club treasury. Reserved exclusively for academy regens to recognize growth, increase squad morale, generate a personal inbox acknowledgment, and broadcast to the GTEX global wire.
            </p>
          </div>

          <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-4 space-y-1.5 text-slate-400">
            <div className="flex items-center gap-2 font-bold text-slate-300">
              <Coins className="h-4 w-4 shrink-0 text-amber-400" />
              <span className="uppercase tracking-wider text-[11px]">Community Gifting (FanCoin)</span>
            </div>
            <p className="text-slate-400 text-[11px] leading-5">
              Supporter-driven digital celebrations (chants, ceremonies, reveals) using FanCoin during match broadcasts. Community fan gifts do not debit club treasury cash or alter internal boardroom contracts.
            </p>
          </div>
        </div>

        {/* Category Filters */}
        <div className="flex items-center gap-2 overflow-x-auto pt-2 no-scrollbar" data-testid="showroom-categories">
          {categories.map((cat) => {
            const Icon = cat.icon;
            const active = selectedCategory === cat.key;
            return (
              <button
                key={cat.key}
                onClick={() => setSelectedCategory(cat.key)}
                data-testid={`showroom-cat-${cat.key}`}
                className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-bold uppercase tracking-wider whitespace-nowrap transition-all ${
                  active
                    ? "bg-amber-400 text-slate-950 font-black shadow-[0_0_16px_rgba(251,191,36,0.4)]"
                    : "border border-white/10 bg-slate-900/70 text-slate-300 hover:border-amber-400/40 hover:text-white"
                }`}
              >
                {Icon && <Icon className="h-3.5 w-3.5" />}
                <span>{cat.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* 3D Bespoke Luxury Vault & Interactive 360 Turntable */}
      {filteredItems.length > 0 && (
        <Cinema3DStage
          scene="luxury_turntable"
          compact
          title={`3D Luxury Vault · ${filteredItems[0]?.name || "Rose-Gold Tourbillon"}`}
          subtitle={`Interactive 360° 3D Inspection & Gifting Preview · ${active?.club_name || "GTEX FC"}`}
          badgeText="3D SHOWROOM VAULT"
          clubName={active?.club_name || "GTEX FC"}
          subjectName={filteredItems[0]?.name || "G650 Executive Jet"}
          assetCategory={filteredItems[0]?.category || "watch"}
          stats={[
            { label: "Valuation", value: `${formatPrice(filteredItems[0])} GTX`, accent: "#F5B83D" },
            { label: "Prestige Boost", value: `+${filteredItems[0]?.prestige_bonus || 8} PTS`, accent: "#00E676" },
          ]}
        />
      )}

      {/* Catalogue Grid */}
      {isLoading ? (
        <Loading label="Opening the boardroom showroom catalogue..." />
      ) : filteredItems.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-950/40 p-16 text-center">
          <Gift className="mx-auto h-12 w-12 text-slate-600 mb-3" />
          <h3 className="text-lg font-bold text-white">No Assets Found</h3>
          <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
            {selectedCategory === "owned"
              ? "Your club has not acquired any prestige assets yet. Browse the catalogue above to commission your first private jet or luxury timepiece."
              : "No showroom items match the selected category."}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6" data-testid="showroom-grid">
          {filteredItems.map((it: any) => {
            const key = keyOf(it);
            const isJet = it.category === "jet";
            const isBusy = busyItem === key || busyItem === `gift:${key}`;
            const isOwned = ownedAssets.some((oa: any) => keyOf(oa) === key);

            return (
              <article
                key={key}
                data-testid={`showroom-item-${key}`}
                className="group flex flex-col overflow-hidden rounded-2xl border border-slate-800 bg-gradient-to-b from-slate-900 to-slate-950 shadow-xl transition-all duration-300 hover:-translate-y-1 hover:border-amber-400/50 hover:shadow-amber-950/20"
              >
                {/* Visual Header */}
                <div className="relative h-48 overflow-hidden bg-slate-950 border-b border-white/5">
                  {assetImage(it) ? (
                    <img
                      src={assetImage(it)}
                      alt={it.name}
                      className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-105"
                      onError={(e) => {
                        (e.currentTarget as HTMLImageElement).style.opacity = "0";
                      }}
                    />
                  ) : (
                    <div className="flex h-full items-center justify-center bg-gradient-to-br from-slate-900 via-slate-950 to-amber-950/30">
                      <Sparkles className="h-12 w-12 text-amber-400/40" />
                    </div>
                  )}

                  <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/20 to-transparent" />

                  {/* Wire notice badge */}
                  <div className="absolute left-3 top-3">
                    <span
                      className={`inline-flex items-center gap-1 rounded-md px-2 py-1 text-[9px] font-black uppercase tracking-wider ${
                        isJet
                          ? "border border-amber-300/40 bg-amber-400/20 text-amber-200"
                          : "border border-slate-700 bg-slate-950/80 text-slate-300"
                      }`}
                    >
                      {isJet ? <ExternalLink className="h-3 w-3" /> : <LockKeyhole className="h-3 w-3" />}
                      {isJet ? "Global Wire Notice" : "Private Collection"}
                    </span>
                  </div>

                  {/* Price pill */}
                  <div className="absolute bottom-3 right-3 flex items-center gap-1 rounded-md bg-slate-950/90 border border-amber-400/30 px-2.5 py-1 font-mono text-xs font-black text-amber-300">
                    <Coins className="h-3.5 w-3.5 text-amber-400" /> {formatPrice(it)} GTX
                  </div>

                  {isOwned && (
                    <div className="absolute bottom-3 left-3">
                      <span className="inline-flex items-center gap-1 rounded-md bg-emerald-500/20 border border-emerald-500/40 px-2 py-0.5 text-[9px] font-black uppercase tracking-wider text-emerald-300">
                        <CheckCircle className="h-3 w-3" /> Acquired
                      </span>
                    </div>
                  )}
                </div>

                {/* Content */}
                <div className="flex flex-1 flex-col p-5 space-y-4">
                  <div className="space-y-1.5">
                    <div className="text-[10px] font-bold uppercase tracking-wider text-amber-400">
                      {it.category || "Prestige Asset"}
                    </div>
                    <h3 className="text-base font-extrabold text-white leading-snug">{it.name}</h3>
                    <p className="text-xs text-slate-400 leading-relaxed line-clamp-3">
                      {it.model || it.description || "An exclusive luxury asset for club prestige and squad motivation."}
                    </p>

                    {/* Prestige, Academy & Pull Badges */}
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      <span className="rounded bg-amber-400/10 text-amber-300 border border-amber-400/30 px-2 py-0.5 text-[9px] font-bold">
                        +{it.prestige_bonus || 2} Prestige
                      </span>
                      <span className="rounded bg-cyan-400/10 text-cyan-300 border border-cyan-400/30 px-2 py-0.5 text-[9px] font-bold">
                        +{it.academy_ceiling_bonus || 1} Academy Ceiling
                      </span>
                      <span className="rounded bg-purple-400/10 text-purple-300 border border-purple-400/30 px-2 py-0.5 text-[9px] font-bold">
                        +{it.transfer_pull_bonus || it.staff_pull_bonus || 1} Pull
                      </span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="mt-auto space-y-2 pt-3 border-t border-slate-800/80">
                    <div className="flex items-center justify-between text-[11px] text-slate-500">
                      <span>Treasury debit</span>
                      <span className="font-mono font-bold text-slate-300">{formatPrice(it)} GTX</span>
                    </div>

                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => setAcquiringItem(it)}
                        disabled={isBusy}
                        className="flex-1 rounded-lg bg-amber-400 hover:bg-amber-300 text-slate-950 font-black text-xs py-2.5 px-3 transition-colors disabled:opacity-50"
                        data-testid={`acquire-btn-${key}`}
                      >
                        {isBusy ? "Processing..." : isOwned ? "Acquire Another" : "Acquire Asset"}
                      </button>

                      {it.can_gift_to_player && (
                        <button
                          type="button"
                          onClick={() => {
                            setGiftingItem(it);
                            setSelectedPlayerId(eligibleRegens[0]?.id || "");
                          }}
                          disabled={isBusy || eligibleRegens.length === 0}
                          className="flex-1 rounded-lg border border-purple-400/40 bg-purple-500/10 hover:bg-purple-500/20 text-purple-300 font-bold text-xs py-2.5 px-3 flex items-center justify-center gap-1.5 transition-colors disabled:opacity-40"
                          title={
                            eligibleRegens.length > 0
                              ? `Gift ${it.name} to an academy regen`
                              : "Luxury gifts are reserved for academy regens"
                          }
                          data-testid={`gift-btn-${key}`}
                        >
                          <Gift className="h-3.5 w-3.5" />
                          <span>Gift Regen</span>
                        </button>
                      )}
                    </div>

                    {it.can_gift_to_player && eligibleRegens.length === 0 && (
                      <p className="text-[10px] text-amber-400/80 text-center">
                        Academy regen required for luxury gifting
                      </p>
                    )}
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}

      {/* PURCHASE CONFIRMATION MODAL */}
      {acquiringItem && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4"
          role="dialog"
          aria-modal="true"
          data-testid="showroom-purchase-confirm"
        >
          <div className="w-full max-w-md overflow-hidden rounded-2xl border border-amber-400/40 bg-gradient-to-br from-slate-900 via-slate-950 to-amber-950/20 shadow-2xl">
            <div className="relative h-40 bg-slate-950">
              {assetImage(acquiringItem) && (
                <img
                  src={assetImage(acquiringItem)}
                  alt={acquiringItem.name}
                  className="h-full w-full object-cover"
                />
              )}
              <div className="absolute inset-0 bg-gradient-to-t from-slate-950 to-transparent" />
              <button
                type="button"
                onClick={() => setAcquiringItem(null)}
                className="absolute right-3 top-3 rounded-full border border-white/20 bg-black/60 p-2 text-white hover:bg-black"
                aria-label="Close dialog"
              >
                <X className="h-4 w-4" />
              </button>
              <div className="absolute bottom-3 left-4 right-4">
                <div className="text-[10px] font-black uppercase tracking-wider text-amber-400">
                  Treasury Authorization
                </div>
                <h3 className="mt-1 text-lg font-black text-white">{acquiringItem.name}</h3>
              </div>
            </div>

            <div className="p-6 space-y-4">
              <p className="text-xs text-slate-300 leading-relaxed">
                Confirm this acquisition. GTEX will validate catalogue parameters, debit the verified price from your club treasury, and record durable ownership.
              </p>

              <div className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-950/80 px-4 py-3">
                <span className="text-xs text-slate-400">Verified Price</span>
                <span className="font-mono text-base font-black text-amber-300">
                  {formatPrice(acquiringItem)} GTX
                </span>
              </div>

              {acquiringItem.category === "jet" ? (
                <div className="flex gap-2 rounded-xl border border-amber-400/30 bg-amber-400/10 p-3 text-xs text-amber-200">
                  <ExternalLink className="h-4 w-4 shrink-0 mt-0.5" />
                  <span>Private jet acquisitions publish a verified announcement to the GTEX global newsroom and ticker wire.</span>
                </div>
              ) : (
                <div className="flex gap-2 rounded-xl border border-slate-800 bg-slate-950/50 p-3 text-xs text-slate-400">
                  <LockKeyhole className="h-4 w-4 shrink-0 mt-0.5" />
                  <span>This item enters your private club collection; verified dispatches remain scoped to club ownership.</span>
                </div>
              )}

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setAcquiringItem(null)}
                  className="flex-1 rounded-lg border border-slate-700 py-3 text-xs font-bold text-slate-300 hover:bg-white/5"
                  disabled={Boolean(busyItem)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => handlePurchase(acquiringItem)}
                  disabled={Boolean(busyItem)}
                  className="flex-1 rounded-lg bg-amber-400 hover:bg-amber-300 py-3 text-xs font-black text-slate-950 transition-colors disabled:opacity-50"
                  data-testid="confirm-purchase-button"
                >
                  {busyItem ? "Processing..." : `Confirm · ${formatPrice(acquiringItem)} GTX`}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* GIFT TO REGEN CONFIRMATION MODAL */}
      {giftingItem && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-4"
          role="dialog"
          aria-modal="true"
          data-testid="showroom-gift-confirm"
        >
          <div className="w-full max-w-lg overflow-hidden rounded-2xl border border-purple-400/40 bg-gradient-to-br from-slate-900 via-slate-950 to-purple-950/30 shadow-2xl">
            <div className="relative h-44 bg-slate-950">
              {assetImage(giftingItem) && (
                <img
                  src={assetImage(giftingItem)}
                  alt={giftingItem.name}
                  className="h-full w-full object-cover opacity-90"
                />
              )}
              <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/20 to-transparent" />
              <button
                type="button"
                onClick={() => setGiftingItem(null)}
                className="absolute right-3 top-3 rounded-full border border-white/20 bg-black/60 p-2 text-white hover:bg-black"
                aria-label="Close dialog"
              >
                <X className="h-4 w-4" />
              </button>
              <div className="absolute bottom-3 left-4 right-4">
                <div className="flex items-center gap-1 text-[10px] font-black uppercase tracking-wider text-purple-300">
                  <Gift className="h-3.5 w-3.5" /> Owner Luxury Gifting
                </div>
                <h3 className="mt-1 text-lg font-black text-white">{giftingItem.name}</h3>
                <div className="mt-1 font-mono text-xs font-bold text-amber-300">
                  {formatPrice(giftingItem)} GTX · Debited from Club Treasury
                </div>
              </div>
            </div>

            <div className="px-6 pt-4">
              <Cinema3DStage
                scene="luxury_turntable"
                compact
                title={`3D Handover Ceremony · ${giftingItem.name}`}
                subtitle={`Presenting to ${recipientType === "player" ? (selectedPlayer?.name || "Squad Member") : selectedStaffRole.replace(/_/g, " ").toUpperCase()}`}
                badgeText="3D GIFT UNBOXING"
                clubName={active?.club_name || "GTEX FC"}
                subjectName={giftingItem.name}
                assetCategory={giftingItem.category || "watch"}
                quote={giftNote || "A personal token of boardroom appreciation and loyalty."}
              />
            </div>
            <form onSubmit={handleGift} className="p-6 space-y-4">
              <div className="rounded-xl border border-purple-400/20 bg-purple-400/10 p-3 text-xs leading-relaxed text-purple-200">
                Luxury incentives can be gifted to an <b>Academy Regen</b> (boosting squad morale) or an <b>Executive Staff / Coach</b> (boosting mood by +15 and organizational loyalty by +3).
              </div>

              {/* Recipient Type Choice */}
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  Select Recipient Type
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setRecipientType("player")}
                    className={`rounded-lg py-2 px-3 text-xs font-bold uppercase tracking-wider transition ${
                      recipientType === "player"
                        ? "bg-purple-600 text-white border border-purple-400 shadow-md"
                        : "bg-black/40 text-slate-400 border border-white/10 hover:text-white"
                    }`}
                  >
                    Squad Player / Regen
                  </button>
                  <button
                    type="button"
                    onClick={() => setRecipientType("staff")}
                    className={`rounded-lg py-2 px-3 text-xs font-bold uppercase tracking-wider transition ${
                      recipientType === "staff"
                        ? "bg-purple-600 text-white border border-purple-400 shadow-md"
                        : "bg-black/40 text-slate-400 border border-white/10 hover:text-white"
                    }`}
                  >
                    Executive Staff / Coach
                  </button>
                </div>
              </div>

              {recipientType === "player" ? (
                <div>
                  <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    Select Squad Member / Academy Regen ({squad.length} Available)
                  </label>
                  <div className="mt-2 grid max-h-52 gap-2 overflow-y-auto sm:grid-cols-2 no-scrollbar">
                    {squad.map((p: any) => (
                      <button
                        type="button"
                        key={p.id}
                        onClick={() => setSelectedPlayerId(p.id)}
                        data-testid={`select-regen-${p.id}`}
                        className={`flex items-center gap-3 rounded-xl border p-3 text-left transition-all ${
                          selectedPlayerId === p.id
                            ? "border-purple-400 bg-purple-500/20 shadow-md"
                            : "border-slate-800 bg-slate-950/60 hover:border-slate-700"
                        }`}
                      >
                        {p.portrait_url || p.image ? (
                          <img
                            src={p.portrait_url || p.image}
                            alt={p.name}
                            className="h-11 w-11 shrink-0 rounded-full border border-white/10 object-cover"
                          />
                        ) : (
                          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-slate-800 text-xs font-black text-purple-300">
                            {String(p.name || "?").slice(0, 1)}
                          </div>
                        )}
                        <div className="min-w-0 flex-1">
                          <div className="truncate text-xs font-extrabold text-white">{p.name}</div>
                          <div className="text-[10px] text-slate-400">
                            {p.position || "Player"} · {p.rating ?? p.overall_rating ?? "—"} OVR {p.is_regen ? "· Regen" : ""}
                          </div>
                          <div className="text-[9px] font-bold text-emerald-400">
                            Morale: {p.morale ?? 75}%
                          </div>
                        </div>
                        {selectedPlayerId === p.id && (
                          <CheckCircle className="h-4 w-4 shrink-0 text-purple-300" />
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <div>
                  <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    Select Staff Recipient (+15 Mood, +3 Loyalty)
                  </label>
                  <div className="mt-2 grid gap-2 sm:grid-cols-2">
                    {[
                      { key: "first_team_manager", label: "First-Team Manager", effect: "+15 Mood · +3 Tactical Loyalty" },
                      { key: "general_manager", label: "General Manager (GM)", effect: "+15 Mood · +3 Commercial Autonomy" },
                      { key: "head_of_youth_development", label: "Head of Youth Dev (HOYD)", effect: "+15 Mood · +3 Youth Retention" },
                      { key: "chief_scout", label: "Chief Scout", effect: "+15 Mood · +3 Precision Scouting" },
                      { key: "medical_director", label: "Medical Director", effect: "+15 Mood · +3 Physical Recovery" },
                    ].map((staff) => (
                      <button
                        type="button"
                        key={staff.key}
                        onClick={() => setSelectedStaffRole(staff.key)}
                        className={`flex flex-col text-left rounded-xl border p-3 transition-all ${
                          selectedStaffRole === staff.key
                            ? "border-purple-400 bg-purple-500/20 shadow-md"
                            : "border-slate-800 bg-slate-950/60 hover:border-slate-700"
                        }`}
                      >
                        <span className="font-bold text-white text-xs">{staff.label}</span>
                        <span className="text-[10px] text-emerald-300 mt-1">{staff.effect}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  Owner Dedication Note
                </label>
                <input
                  type="text"
                  maxLength={180}
                  value={giftNote}
                  onChange={(e) => setGiftNote(e.target.value)}
                  placeholder="A personal message from the boardroom..."
                  className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2.5 text-xs text-white outline-none focus:border-purple-400"
                  data-testid="gift-note-input"
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setGiftingItem(null)}
                  className="flex-1 rounded-lg border border-slate-700 py-3 text-xs font-bold text-slate-300 hover:bg-white/5"
                  disabled={Boolean(busyItem)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={(recipientType === "player" && !selectedPlayerId) || Boolean(busyItem)}
                  className="flex-1 rounded-lg bg-purple-500 hover:bg-purple-400 py-3 text-xs font-black text-white transition-colors disabled:opacity-50"
                  data-testid="confirm-gift-button"
                >
                  {busyItem ? "Delivering Gift..." : `Deliver Gift · ${formatPrice(giftingItem)} GTX`}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* PURCHASE RECEIPT MODAL */}
      {purchaseReceipt && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-4"
          role="dialog"
          aria-modal="true"
          data-testid="showroom-purchase-receipt"
        >
          <div className="relative w-full max-w-md overflow-hidden rounded-2xl border border-amber-400/50 bg-gradient-to-br from-slate-900 via-slate-950 to-amber-950/25 p-6 text-center shadow-2xl">
            <div className="mx-auto flex h-24 w-24 items-center justify-center rounded-full border border-amber-400/40 bg-amber-400/10 p-2 mb-4">
              {assetImage(purchaseReceipt.item) ? (
                <img
                  src={assetImage(purchaseReceipt.item)}
                  alt=""
                  className="h-full w-full rounded-full object-cover"
                />
              ) : (
                <PackageCheck className="h-12 w-12 text-amber-300" />
              )}
            </div>

            <div className="text-[10px] font-black uppercase tracking-wider text-emerald-400 flex items-center justify-center gap-1">
              <CheckCircle className="h-3.5 w-3.5" /> Acquisition Confirmed
            </div>

            <h3 className="mt-2 text-xl font-black text-white">
              {purchaseReceipt.result?.asset?.custom_name || purchaseReceipt.item.name}
            </h3>
            <p className="mt-2 text-xs text-slate-300 leading-relaxed">
              The GTEX showroom has validated the transaction and debited the verified price from your club treasury.
            </p>

            <div className="mt-4 rounded-xl border border-slate-800 bg-black/40 p-4 space-y-1">
              <div className="text-[10px] uppercase font-bold text-slate-400">Verified Transaction</div>
              <div className="font-mono text-lg font-black text-amber-300">
                {fmt(purchaseReceipt.result?.asset?.price_gtex ?? purchaseReceipt.item.price_gtex)} GTX
              </div>
              <div className="text-[10px] text-slate-400">
                {purchaseReceipt.result?.broadcast_globally
                  ? "A verified broadcast was published to the global ticker and newsroom."
                  : "Recorded to your club's private boardroom collection."}
              </div>
            </div>

            <button
              type="button"
              onClick={() => setPurchaseReceipt(null)}
              className="mt-5 w-full rounded-lg bg-amber-400 hover:bg-amber-300 py-3 text-xs font-black text-slate-950 transition-colors"
              data-testid="close-purchase-receipt"
            >
              Return to Showroom
            </button>
          </div>
        </div>
      )}

      {/* GIFT RECEIPT MODAL */}
      {giftReceipt && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-4"
          role="dialog"
          aria-modal="true"
          data-testid="showroom-gift-receipt"
        >
          <div className="relative w-full max-w-md overflow-hidden rounded-2xl border border-purple-400/50 bg-gradient-to-br from-slate-900 via-slate-950 to-purple-950/30 p-6 text-center shadow-2xl">
            <div className="mx-auto flex h-24 w-24 items-center justify-center rounded-full border border-purple-400/40 bg-purple-500/10 p-2 mb-4">
              {assetImage(giftReceipt.item) ? (
                <img
                  src={assetImage(giftReceipt.item)}
                  alt=""
                  className="h-full w-full rounded-full object-cover"
                />
              ) : (
                <Gift className="h-12 w-12 text-purple-300" />
              )}
            </div>

            <div className="text-[10px] font-black uppercase tracking-wider text-emerald-400 flex items-center justify-center gap-1">
              <CheckCircle className="h-3.5 w-3.5" /> Luxury Gift Delivered
            </div>

            <h3 className="mt-2 text-xl font-black text-white">{giftReceipt.item.name}</h3>
            <p className="mt-1 text-xs text-slate-300">A personal boardroom incentive presented to</p>

            <div className="mx-auto mt-3 flex items-center gap-3 rounded-xl border border-purple-400/30 bg-black/40 p-3 text-left">
              {giftReceipt.player?.portrait_url ? (
                <img
                  src={giftReceipt.player.portrait_url}
                  alt=""
                  className="h-12 w-12 rounded-full border border-purple-400/30 object-cover"
                />
              ) : (
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-purple-500/20 text-sm font-black text-purple-200">
                  {String(giftReceipt.player?.name || "P").slice(0, 1)}
                </div>
              )}
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-extrabold text-white">
                  {giftReceipt.player?.name || "Academy Regen"}
                </div>
                <div className="text-[10px] text-slate-400">
                  {giftReceipt.player?.position || "Academy Squad"}
                </div>
                {Number(giftReceipt.result?.morale_delta || 0) > 0 && (
                  <div className="text-[10px] font-bold text-emerald-300">
                    Morale +{giftReceipt.result.morale_delta} · Confirmed
                  </div>
                )}
              </div>
              <CheckCircle className="h-5 w-5 shrink-0 text-emerald-400" />
            </div>

            {giftReceipt.note && (
              <blockquote className="mt-3 text-xs italic text-purple-200 bg-slate-950/50 p-2.5 rounded border border-purple-500/20">
                “{giftReceipt.note}”
              </blockquote>
            )}

            <div className="mt-4 rounded-xl border border-slate-800 bg-black/40 p-4 space-y-1">
              <div className="text-[10px] uppercase font-bold text-slate-400">Gift Transaction</div>
              <div className="font-mono text-base font-black text-purple-300">
                {fmt(giftReceipt.result?.asset?.price_gtex ?? giftReceipt.item.price_gtex)} GTX
              </div>
              <div className="text-[10px] text-slate-400">
                Logged to club ledger with verified player morale adjustment and owner inbox item.
              </div>
            </div>

            <button
              type="button"
              onClick={() => setGiftReceipt(null)}
              className="mt-5 w-full rounded-lg bg-purple-500 hover:bg-purple-400 py-3 text-xs font-black text-white transition-colors"
              data-testid="close-gift-receipt"
            >
              Return to Showroom
            </button>
          </div>
        </div>
      )}
    </div>
  );
}