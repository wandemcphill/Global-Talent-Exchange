import React, { useRef, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { validateClubLocation } from "./clubCreationLocation";
import { fmt, label, useActiveClub, useClub, useClubShowroom, useControlCenter, useRefreshOwner } from "@/lib/owner";
import { Btn, Chip, Coin, Empty, Loading, PageHeader, Panel, Stat } from "@/components/gtex/ui";
import { Building, Gift, Sparkles, BookOpen, ExternalLink, CheckCircle, Coins, LockKeyhole, X, PackageCheck } from "lucide-react";

function Facilities({ club }: any) {
  const refresh = useRefreshOwner();
  const [busy, setBusy] = useState<string | null>(null);
  const up = async (kind: string) => {
    setBusy(kind);
    try {
      const { data } = await api.post(`/owner/clubs/${club.club_id}/facilities/${kind}/upgrade`);
      toast.success(`${label(kind)} level ${data.level}. ${data.effect}`);
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(null);
    }
  };
  return (
    <Panel eyebrow="Club building" title="Facilities & Static Imagery" testid="facilities-panel" className="lg:col-span-7">
      <div className="grid gap-4 sm:grid-cols-2">
        {Object.entries(club.facilities).map(([k, f]: any) => (
          <div key={k} className="rounded-xl border border-white/10 bg-slate-950/40 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="gx-display text-base font-bold uppercase text-white">{k}</p>
                <span className="text-[11px] text-slate-400">Infrastructure Asset</span>
              </div>
              <span className="gx-mono text-xs font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                L{f.level}/5
              </span>
            </div>

            <div className="flex gap-1.5">
              {[1, 2, 3, 4, 5].map((n) => (
                <span
                  key={n}
                  className={`h-1.5 flex-1 rounded-full ${n <= f.level ? "bg-emerald-400 shadow-sm" : "bg-white/10"}`}
                />
              ))}
            </div>

            <Btn
              variant="secondary"
              className="mt-2 w-full text-xs font-bold"
              disabled={!f.next_cost || busy === k}
              onClick={() => up(k)}
              data-testid={`upgrade-${k}-button`}
            >
              {f.next_cost ? <>Upgrade · {fmt(f.next_cost)} GTX</> : "Max level achieved"}
            </Btn>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function ShowroomPanel({ club }: any) {
  const refresh = useRefreshOwner();
  const { data, isLoading } = useClubShowroom(club.club_id);
  const { data: clubDetail } = useClub(club.club_id);
  const [busyItem, setBusyItem] = useState<string | null>(null);
  const [acquiringItem, setAcquiringItem] = useState<any | null>(null);
  const [giftingItem, setGiftingItem] = useState<any | null>(null);
  const [selectedPlayerId, setSelectedPlayerId] = useState<string>("");
  const [giftNote, setGiftNote] = useState<string>("");
  const [giftReceipt, setGiftReceipt] = useState<any | null>(null);
  const [purchaseReceipt, setPurchaseReceipt] = useState<any | null>(null);
  // Keep one idempotency key per user intent across network retries. Keys are
  // discarded only after a confirmed response so a lost response cannot turn
  // a retry into a second charge.
  const purchaseIntentKeys = useRef(new Map<string, string>());
  const giftIntentKeys = useRef(new Map<string, string>());
  const stableIntentKey = (store: React.MutableRefObject<Map<string, string>>, identity: string, prefix: string) => {
    const existing = store.current.get(identity);
    if (existing) return existing;
    const nonce = typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const created = `${prefix}:${club.club_id}:${identity}:${nonce}`;
    store.current.set(identity, created);
    return created;
  };

  // Current API returns {catalog, owned_assets}; accept the older transformed
  // shape too so this panel remains compatible with existing deployed builds.
  const rawCatalog = data?.catalog ?? data?.showroom?.catalog ?? data?.showroom;
  const rawOwnedAssets = data?.owned_assets ?? data?.showroom?.owned_assets;
  const rawSquad = data?.squad ?? clubDetail?.squad ?? club.squad;
  const items: any[] = Array.isArray(rawCatalog) ? rawCatalog : [];
  const ownedAssets: any[] = Array.isArray(rawOwnedAssets) ? rawOwnedAssets : [];
  const squad: any[] = Array.isArray(rawSquad) ? rawSquad : [];
  const eligibleRegens: any[] = squad.filter((player: any) => player?.is_regen === true);
  const selectedPlayer = eligibleRegens.find((p: any) => p.id === selectedPlayerId);
  const keyOf = (item: any) => String(item?.catalog_key || item?.key || item?.id || "");
  const formatPrice = (item: any) => fmt(item?.price_gtex, 2);
  const assetImage = (item: any) => item?.image_url || "";

  const handlePurchase = async (item: any) => {
    const catalogKey = keyOf(item);
    if (!catalogKey || busyItem) return;
    setBusyItem(catalogKey);
    try {
      const res = await api.post(`/owner/clubs/${club.club_id}/showroom/purchase`, {
        catalog_key: catalogKey,
        idempotency_key: stableIntentKey(purchaseIntentKeys, catalogKey, "showroom-purchase"),
      });
      const result = res.data ?? {};
      // A 2xx response is authoritative even if optional receipt fields are
      // omitted by an older server response shape.
      purchaseIntentKeys.current.delete(catalogKey);
      setAcquiringItem(null);
      setPurchaseReceipt({ item, result });
      const acquiredName = result?.asset?.custom_name || item?.name || "prestige asset";
      if (result?.broadcast_globally === true) {
        toast.success(`Acquired ${acquiredName}. Verified notice published to the GTEX global wire.`);
      } else {
        toast.success(`Acquired ${acquiredName} for club operations. This purchase stays private unless GTEX confirms a public notice.`);
      }
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusyItem(null);
    }
  };

  const handleGift = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!giftingItem || !selectedPlayerId || busyItem) return;
    const catalogKey = keyOf(giftingItem);
    if (!catalogKey) {
      toast.error("This showroom item is missing its catalogue reference.");
      return;
    }
    const giftIntent = `${catalogKey}:${selectedPlayerId}`;
    setBusyItem(`gift:${catalogKey}`);
    try {
      const { data: responseData } = await api.post(`/owner/clubs/${club.club_id}/showroom/gift`, {
        player_id: selectedPlayerId,
        catalog_key: catalogKey,
        note: giftNote.trim(),
        idempotency_key: stableIntentKey(giftIntentKeys, giftIntent, "showroom-gift"),
      });
      const result = responseData ?? {};
      giftIntentKeys.current.delete(giftIntent);
      const recipient = result?.player || selectedPlayer;
      setGiftReceipt({ item: giftingItem, player: recipient, note: giftNote.trim(), result });
      setGiftingItem(null);
      setSelectedPlayerId("");
      setGiftNote("");
      const giftName = giftingItem?.name || result?.asset?.custom_name || "luxury gift";
      if (result?.broadcast_event) {
        toast.success(`GTEX confirmed ${giftName} for ${recipient?.name || "your player"}; a verified gift event was recorded.`);
      } else {
        toast.success(`GTEX recorded ${giftName} for ${recipient?.name || "your player"}.`);
      }
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusyItem(null);
    }
  };

  const rarityFor = (item: any) => {
    const category = String(item.category || "").toLowerCase();
    if (category === "jet" || item.price_gtex >= 4000) return "Prestige";
    if (item.can_gift_to_player) return "Player eligible";
    if (category === "facility") return "Infrastructure";
    return "Private collection";
  };

  return (
    <Panel
      eyebrow="Luxury Fleet & Gifting"
      title="Showroom & Prestige Assets"
      testid="showroom-panel"
      className="lg:col-span-12"
    >
      <div className="mb-5 flex flex-col gap-3 rounded-xl border border-amber-500/20 bg-gradient-to-r from-amber-500/[0.09] via-slate-900/60 to-transparent p-4 sm:flex-row sm:items-center">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-amber-300/30 bg-amber-400/10 text-amber-200">
          <Sparkles className="h-6 w-6" />
        </div>
        <div className="min-w-0">
          <div className="text-[10px] font-black uppercase tracking-[0.23em] text-amber-200">The owner's private collection</div>
          <p className="mt-1 max-w-3xl text-xs leading-5 text-slate-300">
            Acquire prestige assets through the club treasury, or purchase a player-eligible gift and deliver it directly to a registered squad member. Only eligible, verified events are published to the global wire.
          </p>
        </div>
        <div className="sm:ml-auto flex items-center gap-3 shrink-0">
          <Link
            to="/app/showroom"
            className="flex items-center gap-1 rounded-lg border border-amber-400/40 bg-amber-400/10 px-3 py-2 text-xs font-bold text-amber-200 hover:bg-amber-400/20 transition-colors"
            data-testid="open-dedicated-showroom-link"
          >
            <span>Dedicated Showroom</span>
            <ExternalLink className="h-3 w-3" />
          </Link>
          <div className="shrink-0 rounded-lg border border-slate-700 bg-slate-950/70 px-3 py-2">
            <div className="text-[9px] uppercase tracking-wider text-slate-500">Treasury</div>
            <div className="font-mono text-sm font-bold text-amber-200">{fmt(club.cash)} GTX</div>
          </div>
        </div>
      </div>

      {isLoading ? (
        <Loading />
      ) : items.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-700 bg-slate-950/40 p-8 text-center">
          <Gift className="mx-auto mb-3 h-8 w-8 text-amber-300" />
          <div className="text-sm font-bold text-white">Showroom catalogue unavailable</div>
          <p className="mx-auto mt-2 max-w-md text-xs text-slate-400">
            GTEX did not return the luxury catalogue. Refresh the club data before trying to purchase or gift any item.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {items.map((it: any) => {
            const key = keyOf(it);
            const isJet = it.category === "jet";
            const isBusy = busyItem === key;
            return (
              <article
                key={key}
                data-testid={`showroom-item-${key}`}
                className="group flex min-w-0 flex-col overflow-hidden rounded-2xl border border-slate-800 bg-gradient-to-b from-slate-900 to-slate-950 shadow-lg shadow-black/15 transition-all duration-300 hover:-translate-y-0.5 hover:border-amber-400/40 hover:shadow-amber-900/10"
              >
                <div className="relative h-44 overflow-hidden border-b border-white/5 bg-slate-950">
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
                    <div className="flex h-full items-center justify-center bg-gradient-to-br from-slate-900 via-slate-950 to-amber-900/10">
                      <Building className="h-12 w-12 text-amber-300/70" />
                    </div>
                  )}
                  <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/10 to-transparent" />
                  <div className="absolute left-3 top-3">
                    <span className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[9px] font-black uppercase tracking-wider ${isJet ? "border-amber-300/40 bg-amber-400/15 text-amber-200" : "border-slate-600 bg-slate-950/80 text-slate-300"}`}>
                      {isJet ? <ExternalLink className="h-3 w-3" /> : <LockKeyhole className="h-3 w-3" />}
                      {isJet ? "Eligible global wire" : "Private"}
                    </span>
                  </div>
                  <div className="absolute bottom-3 left-3 right-3 flex items-end justify-between gap-2">
                    <span className="rounded-md border border-white/10 bg-slate-950/75 px-2 py-1 text-[9px] font-bold uppercase tracking-wider text-slate-200">{rarityFor(it)}</span>
                    <span className="flex items-center gap-1 rounded-md bg-slate-950/80 px-2 py-1 font-mono text-[11px] font-black text-amber-200">
                      <Coins className="h-3 w-3" /> {formatPrice(it)} GTX
                    </span>
                  </div>
                </div>

                <div className="flex flex-1 flex-col p-4">
                  <div className="min-h-[92px]">
                    <h4 className="text-sm font-extrabold leading-snug text-white">{it.name}</h4>
                    <p className="mt-1 line-clamp-3 text-[11px] leading-5 text-slate-400">{it.model || it.description || "A limited prestige asset for your club collection."}</p>
                  </div>
                  <div className="mt-auto space-y-2 border-t border-slate-800 pt-3">
                    <div className="flex items-center justify-between gap-2 text-[10px] text-slate-500">
                      <span>Club treasury debit</span>
                      <span className="font-mono font-bold text-slate-300">{formatPrice(it)} GTX</span>
                    </div>
                    <div className="flex gap-2">
                      <Btn
                        variant="secondary"
                        className="flex-1 text-xs"
                        disabled={!key || !!busyItem}
                        onClick={() => setAcquiringItem(it)}
                      >
                        {isBusy ? "Processing…" : "Acquire asset"}
                      </Btn>
                      {it.can_gift_to_player && (
                        <div className="min-w-0 flex-1">
                          <Btn
                            variant="ghost"
                            className="w-full border border-purple-400/25 px-3 text-xs text-purple-300 hover:border-purple-300/60 hover:text-purple-200"
                            disabled={!!busyItem || eligibleRegens.length === 0}
                            title={eligibleRegens.length > 0
                              ? `Gift ${it.name} to an academy regen`
                              : "Luxury gifts are reserved for academy regens"}
                            onClick={() => {
                              setGiftingItem(it);
                              setSelectedPlayerId(eligibleRegens[0]?.id || "");
                            }}
                          >
                            <Gift className="mr-1 h-3.5 w-3.5" /> Gift a regen
                          </Btn>
                          {eligibleRegens.length === 0 && (
                            <p className="mt-1 text-[9px] leading-4 text-slate-500">
                              Regen only · add an academy regen first
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}

      {ownedAssets.length > 0 && (
        <section className="mt-6 rounded-xl border border-slate-800 bg-slate-950/50 p-4">
          <div className="mb-3 flex items-center gap-2">
            <BookOpen className="h-4 w-4 text-amber-300" />
            <div>
              <h3 className="text-xs font-extrabold text-white">Verified luxury & gifting moments</h3>
              <p className="text-[10px] text-slate-500">Recent events returned by the GTEX owner newsroom service</p>
            </div>
          </div>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {ownedAssets.slice(0, 6).map((event: any) => (
              <div key={event.id} className="flex items-center gap-3 rounded-lg border border-slate-800 bg-slate-900/70 p-3">
                {event.image_url ? (
                  <img src={event.image_url} alt="" className="h-12 w-12 rounded-lg object-cover" />
                ) : (
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-amber-400/10 text-amber-300"><Gift className="h-5 w-5" /></div>
                )}
                <div className="min-w-0">
                  <div className="truncate text-xs font-bold text-slate-200">{event.item_name || event.custom_name || "Luxury event"}</div>
                  <div className="mt-1 truncate text-[10px] text-slate-500">{(event.player_name || event.gifted_to_player_name) ? `Gifted to ${event.player_name || event.gifted_to_player_name}` : event.created_at ? new Date(event.created_at).toLocaleDateString() : "Recorded on GTEX wire"}</div>
                  {event.purchase_price_gtex != null && <div className="mt-1 font-mono text-[10px] text-amber-300">{fmt(event.purchase_price_gtex, 2)} GTX</div>}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Purchase is explicit and confirmed before GTEX debits the club treasury. */}
      {acquiringItem && (
        <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/80 p-4 backdrop-blur-md" role="dialog" aria-modal="true" data-testid="showroom-purchase-confirm">
          <div className="w-full max-w-md overflow-hidden rounded-2xl border border-amber-300/35 bg-gradient-to-br from-slate-900 via-slate-950 to-amber-950/20 shadow-2xl shadow-amber-950/20">
            <div className="relative h-40 bg-slate-950">
              {assetImage(acquiringItem) && <img src={assetImage(acquiringItem)} alt={acquiringItem.name} className="h-full w-full object-cover" />}
              <div className="absolute inset-0 bg-gradient-to-t from-slate-950 to-transparent" />
              <button type="button" onClick={() => setAcquiringItem(null)} className="absolute right-3 top-3 rounded-full border border-white/15 bg-black/60 p-2 text-white" aria-label="Close purchase confirmation"><X className="h-4 w-4" /></button>
              <div className="absolute bottom-3 left-4 right-4">
                <div className="text-[9px] font-black uppercase tracking-[0.2em] text-amber-200">Treasury authorisation</div>
                <h3 className="mt-1 text-lg font-black text-white">{acquiringItem.name}</h3>
              </div>
            </div>
            <div className="space-y-4 p-5">
              <p className="text-xs leading-5 text-slate-300">Confirm this acquisition. GTEX will validate the catalogue item and debit the verified price from your club treasury.</p>
              <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-black/25 px-3 py-3">
                <span className="text-xs text-slate-400">Total price</span>
                <span className="font-mono text-base font-black text-amber-200">{formatPrice(acquiringItem)} GTX</span>
              </div>
              {acquiringItem.category === "jet" ? (
                <div className="flex gap-2 rounded-lg border border-amber-400/20 bg-amber-400/[0.06] p-3 text-[11px] leading-5 text-amber-100"><ExternalLink className="mt-0.5 h-4 w-4 shrink-0" /><span>Private jet acquisitions publish a verified global wire notice. Ordinary luxury purchases stay private.</span></div>
              ) : (
                <div className="flex gap-2 rounded-lg border border-slate-700 bg-slate-950/50 p-3 text-[11px] leading-5 text-slate-400"><LockKeyhole className="mt-0.5 h-4 w-4 shrink-0" /><span>This acquisition is private; the screen will only show a global notice if the server confirms one.</span></div>
              )}
              <div className="flex gap-2">
                <button type="button" onClick={() => setAcquiringItem(null)} className="flex-1 rounded-lg border border-slate-700 px-4 py-3 text-xs font-bold text-slate-300 hover:bg-white/5" disabled={!!busyItem}>Cancel</button>
                <button type="button" onClick={() => handlePurchase(acquiringItem)} className="flex-1 rounded-lg bg-amber-300 px-4 py-3 text-xs font-black text-slate-950 transition hover:bg-amber-200 disabled:opacity-50" disabled={!!busyItem}>
                  {busyItem ? "Processing…" : `Confirm · ${formatPrice(acquiringItem)} GTX`}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Player selection includes real squad metadata before spending is confirmed. */}
      {giftingItem && (
        <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/80 p-4 backdrop-blur-md" role="dialog" aria-modal="true" data-testid="showroom-gift-confirm">
          <div className="w-full max-w-lg overflow-hidden rounded-2xl border border-purple-400/30 bg-gradient-to-br from-slate-900 via-slate-950 to-purple-950/25 shadow-2xl shadow-purple-950/25">
            <div className="relative h-44 bg-slate-950">
              {assetImage(giftingItem) && <img src={assetImage(giftingItem)} alt={giftingItem.name} className="h-full w-full object-cover opacity-90" />}
              <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/10 to-transparent" />
              <button type="button" onClick={() => setGiftingItem(null)} className="absolute right-3 top-3 rounded-full border border-white/15 bg-black/60 p-2 text-white" aria-label="Close gift dialog"><X className="h-4 w-4" /></button>
              <div className="absolute bottom-3 left-4 right-4">
                <div className="flex items-center gap-1 text-[9px] font-black uppercase tracking-[0.2em] text-purple-200"><Gift className="h-3 w-3" /> A personal club reward</div>
                <h3 className="mt-1 text-lg font-black text-white">{giftingItem.name}</h3>
                <div className="mt-1 font-mono text-xs font-bold text-amber-200">{formatPrice(giftingItem)} GTX · charged to club treasury</div>
              </div>
            </div>
            <form onSubmit={handleGift} className="space-y-4 p-5">
              <div className="rounded-lg border border-purple-400/20 bg-purple-400/[0.06] p-3 text-xs leading-5 text-slate-300">
                This luxury incentive is reserved for an academy regen. GTEX charges the club treasury, records the verified gift event, and shows only the actual morale change returned by the server.
              </div>
              <div>
                <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Choose academy regen</label>
                <div className="mt-2 grid max-h-52 gap-2 overflow-y-auto sm:grid-cols-2">
                  {eligibleRegens.map((p: any) => (
                    <button
                      type="button"
                      key={p.id}
                      onClick={() => setSelectedPlayerId(p.id)}
                      className={`flex items-center gap-3 rounded-xl border p-3 text-left transition ${selectedPlayerId === p.id ? "border-purple-300/70 bg-purple-400/10" : "border-slate-800 bg-slate-950/50 hover:border-slate-600"}`}
                    >
                      {p.portrait_url ? <img src={p.portrait_url} alt="" className="h-11 w-11 shrink-0 rounded-full border border-white/10 object-cover" /> : <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-slate-800 text-xs font-black text-amber-200">{String(p.name || "?").slice(0, 1)}</div>}
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-xs font-extrabold text-white">{p.name}</div>
                        <div className="mt-0.5 text-[10px] text-slate-500">{p.position || "Regen player"} · OVR {p.rating ?? "—"}</div>
                        <div className="mt-0.5 text-[8px] font-black tracking-[0.16em] text-amber-300">ACADEMY REGEN</div>
                        <div className="text-[10px] text-slate-400">Morale {p.morale ?? "—"}%</div>
                      </div>
                      {selectedPlayerId === p.id && <CheckCircle className="h-4 w-4 shrink-0 text-purple-200" />}
                    </button>
                  ))}
                </div>
                {eligibleRegens.length === 0 && <p className="mt-2 text-xs text-amber-200">No eligible academy regens are available. Develop an academy regen before sending a luxury gift.</p>}
              </div>
              <div>
                <label className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Personal note</label>
                <input
                  type="text"
                  maxLength={180}
                  value={giftNote}
                  onChange={(e) => setGiftNote(e.target.value)}
                  placeholder="A reward for the performance. A message from the owner."
                  className="mt-1 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-3 text-xs text-white outline-none transition focus:border-purple-300/60"
                />
              </div>
              <div className="flex gap-2 pt-1">
                <button type="button" onClick={() => setGiftingItem(null)} className="flex-1 rounded-lg border border-slate-700 px-4 py-3 text-xs font-bold text-slate-300 hover:bg-white/5" disabled={!!busyItem}>Cancel</button>
                <button type="submit" disabled={!selectedPlayerId || !!busyItem} className="flex-1 rounded-lg bg-purple-500 px-4 py-3 text-xs font-black text-white transition hover:bg-purple-400 disabled:opacity-50">
                  {busyItem === `gift:${keyOf(giftingItem)}` ? "Delivering gift…" : `Confirm gift · ${formatPrice(giftingItem)} GTX`}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {purchaseReceipt && (
        <div className="fixed inset-0 z-[90] flex items-center justify-center bg-black/80 p-4 backdrop-blur-md" role="dialog" aria-modal="true" data-testid="showroom-purchase-receipt">
          <div className="relative w-full max-w-md overflow-hidden rounded-2xl border border-amber-300/50 bg-gradient-to-br from-slate-900 via-slate-950 to-amber-950/25 p-6 text-center shadow-2xl shadow-amber-900/20">
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_25%,rgba(251,191,36,0.16),transparent_52%)]" />
            <div className="relative">
              <div className="mx-auto flex h-28 w-28 animate-pulse items-center justify-center rounded-full border border-amber-300/50 bg-amber-400/10 p-3">
                {assetImage(purchaseReceipt.item) ? <img src={assetImage(purchaseReceipt.item)} alt="" className="h-full w-full rounded-full object-cover" /> : <PackageCheck className="h-12 w-12 text-amber-200" />}
              </div>
              <div className="mt-5 text-[10px] font-black uppercase tracking-[0.22em] text-emerald-300"><CheckCircle className="mr-1 inline h-3.5 w-3.5" /> Acquisition confirmed</div>
              <h3 className="mt-2 text-xl font-black text-white">{purchaseReceipt.result?.asset?.custom_name || purchaseReceipt.item.name}</h3>
              <p className="mt-2 text-xs leading-5 text-slate-300">The GTEX showroom has confirmed the purchase and recorded the charge against your club treasury.</p>
              <div className="mt-4 rounded-lg border border-slate-800 bg-black/30 px-4 py-3">
                <div className="text-[10px] uppercase tracking-wider text-slate-500">Verified transaction</div>
                <div className="mt-1 font-mono text-lg font-black text-amber-200">{fmt(purchaseReceipt.result?.asset?.price_gtex ?? purchaseReceipt.item.price_gtex, 2)} GTX</div>
                <div className="mt-1 text-[10px] text-slate-400">{purchaseReceipt.result?.broadcast_globally ? "A verified global wire announcement was published." : "This item is a private collection acquisition."}</div>
              </div>
              <button type="button" onClick={() => setPurchaseReceipt(null)} className="mt-5 w-full rounded-lg bg-amber-300 px-4 py-3 text-xs font-black text-slate-950 hover:bg-amber-200">Return to showroom</button>
            </div>
          </div>
        </div>
      )}

      {giftReceipt && (
        <div className="fixed inset-0 z-[90] flex items-center justify-center bg-black/85 p-4 backdrop-blur-md" role="dialog" aria-modal="true" data-testid="showroom-gift-receipt">
          <div className="relative w-full max-w-md overflow-hidden rounded-2xl border border-purple-300/50 bg-gradient-to-br from-slate-900 via-slate-950 to-purple-950/30 p-6 text-center shadow-2xl shadow-purple-950/30">
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_25%,rgba(192,132,252,0.20),transparent_52%)]" />
            <div className="relative">
              <div className="mx-auto flex h-32 w-32 animate-bounce items-center justify-center rounded-full border border-purple-200/50 bg-purple-400/10 p-3">
                {assetImage(giftReceipt.item) ? <img src={assetImage(giftReceipt.item)} alt="" className="h-full w-full rounded-full object-cover" /> : <Gift className="h-12 w-12 text-purple-200" />}
              </div>
              <div className="mt-5 text-[10px] font-black uppercase tracking-[0.22em] text-emerald-300"><CheckCircle className="mr-1 inline h-3.5 w-3.5" /> Gift delivery confirmed</div>
              <h3 className="mt-2 text-xl font-black text-white">{giftReceipt.item.name}</h3>
              <p className="mt-2 text-xs text-slate-300">A personal gift from the club owner to</p>
              <div className="mx-auto mt-4 flex max-w-xs items-center gap-3 rounded-xl border border-purple-300/20 bg-black/30 p-3 text-left">
                {giftReceipt.player?.portrait_url ? <img src={giftReceipt.player.portrait_url} alt="" className="h-14 w-14 rounded-full border border-purple-300/30 object-cover" /> : <div className="flex h-14 w-14 items-center justify-center rounded-full bg-purple-400/10 text-lg font-black text-purple-200">{String(giftReceipt.player?.name || "P").slice(0,1)}</div>}
                <div className="min-w-0">
                  <div className="truncate text-sm font-extrabold text-white">{giftReceipt.player?.name || "Squad player"}</div>
                  <div className="text-[10px] text-slate-400">{giftReceipt.player?.position || "First-team squad"}</div>
                  {Number(giftReceipt.result?.morale_delta || 0) > 0 && <div className="mt-1 text-[10px] font-bold text-emerald-300">Morale +{giftReceipt.result.morale_delta} · confirmed</div>}
                </div>
                <CheckCircle className="h-5 w-5 shrink-0 text-emerald-300" />
              </div>
              {giftReceipt.note && <blockquote className="mt-4 text-xs italic text-purple-100">“{giftReceipt.note}”</blockquote>}
              <div className="mt-4 rounded-lg border border-slate-800 bg-black/30 px-4 py-3">
                <div className="text-[10px] uppercase tracking-wider text-slate-500">Gift transaction</div>
                <div className="mt-1 font-mono text-base font-black text-purple-200">{fmt(giftReceipt.result?.asset?.price_gtex ?? giftReceipt.item.price_gtex, 2)} GTX</div>
                <div className="mt-1 text-[10px] leading-4 text-slate-400">GTEX has recorded the gift event and the resulting player morale adjustment.</div>
              </div>
              <button type="button" onClick={() => setGiftReceipt(null)} className="mt-5 w-full rounded-lg bg-purple-400 px-4 py-3 text-xs font-black text-slate-950 hover:bg-purple-300">Return to the club</button>
            </div>
          </div>
        </div>
      )}
    </Panel>
  );
}

function Capital({ club, clubs }: any) {
  const refresh = useRefreshOwner();
  const [amount, setAmount] = useState("1000");
  const [target, setTarget] = useState("");
  const run = async (path: string, body: any, ok: string) => {
    try {
      await api.post(path, body);
      toast.success(ok);
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
  const sisters = clubs.filter((c: any) => c.club_id !== club.club_id);
  return (
    <Panel eyebrow="Approved capital actions" title="Treasury" testid="capital-panel" className="lg:col-span-5">
      <div className="grid grid-cols-2 gap-4">
        <Stat label="Club cash" value={<Coin amount={club.economy.cash_gtex} />} />
        <Stat label="Pending payouts" value={<Coin amount={club.economy.pending_payouts} />} />
      </div>
      <label className="gx-label mt-5">Amount (GTX)</label>
      <input
        data-testid="capital-amount-input"
        className="gx-input"
        value={amount}
        onChange={(e) => setAmount(e.target.value)}
      />
      <div className="mt-3 flex flex-wrap gap-2">
        <Btn
          variant="secondary"
          data-testid="inject-capital-button"
          onClick={() =>
            run(
              "/owner/capital/inject",
              { club_id: club.club_id, amount: Number(amount) },
              "Capital injected from your wallet."
            )
          }
        >
          Inject from wallet
        </Btn>
        <Btn
          variant="secondary"
          data-testid="distribute-button"
          onClick={() =>
            run(
              "/owner/capital/distribute",
              { club_id: club.club_id, amount: Number(amount) },
              "Distributed earned revenue to your wallet."
            )
          }
        >
          Distribute earnings
        </Btn>
      </div>
      <p className="mt-2 text-xs text-slate-500">
        Only earned club revenue (gate, prizes, sponsors, sales) can be distributed. Launch grants stay in the club.
      </p>
      {sisters.length > 0 && (
        <div className="mt-5 border-t border-white/5 pt-4">
          <label className="gx-label">Move to sister club (capped 25%, disclosed)</label>
          <div className="flex gap-2">
            <select
              data-testid="sister-club-select"
              className="gx-input"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
            >
              <option value="">Select club</option>
              {sisters.map((s: any) => (
                <option key={s.club_id} value={s.club_id}>
                  {s.club_name}
                </option>
              ))}
            </select>
            <Btn
              variant="secondary"
              disabled={!target}
              data-testid="sister-transfer-button"
              onClick={() =>
                run(
                  "/owner/capital/sister-transfer",
                  { from_club_id: club.club_id, to_club_id: target, amount: Number(amount) },
                  "Related-party capital move ledgered."
                )
              }
            >
              Move
            </Btn>
          </div>
        </div>
      )}
    </Panel>
  );
}

function Commercial({ club }: any) {
  const { data } = useQuery({
    queryKey: ["supporters", club.club_id],
    queryFn: async () => (await api.get(`/owner/clubs/${club.club_id}/supporters`)).data.leaderboard,
  });
  return (
    <>
      <Panel eyebrow="Commercial · 70/30 split" title="Sponsors" testid="sponsors-panel" className="lg:col-span-4">
        {club.sponsors.length === 0 ? (
          <Empty title="No sponsors" body="Sponsor offers arrive in your inbox as fans and commercial level grow." />
        ) : (
          <div className="space-y-2">
            {club.sponsors.map((s: any) => (
              <div
                key={s.id}
                className="flex items-center justify-between rounded-sm border border-white/5 p-3 text-sm"
              >
                <div>
                  <p className="text-white">{s.sponsor}</p>
                  <p className="text-xs text-slate-500">
                    {s.slot} · {s.matches_remaining} matches left
                  </p>
                </div>
                <div className="text-right">
                  <Coin amount={s.club_share} />
                  <p className="text-[10px] text-slate-500">club share / match</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </Panel>
      <Panel eyebrow="Supporters" title="Gift leaderboard" testid="supporters-panel" className="lg:col-span-4">
        {(data || []).length === 0 ? (
          <Empty title="No gifts yet" body="Fans gift during and after matches." />
        ) : (
          <ol className="space-y-2">
            {data.map((r: any, i: number) => (
              <li key={r.user_id} className="flex justify-between text-sm">
                <span>
                  <span className="gx-mono mr-2 text-slate-500">{i + 1}</span>
                  {r.username}
                </span>
                <Coin amount={r.fan_coin_sent} currency="FAN" />
              </li>
            ))}
          </ol>
        )}
      </Panel>
      <Panel eyebrow="Transparency" title="Related-party history" testid="disclosures-panel" className="lg:col-span-4">
        {club.disclosures.length === 0 ? (
          <p className="text-sm text-slate-500">No related-party transfers disclosed.</p>
        ) : (
          club.disclosures.map((d: any) => (
            <div key={d.id} className="mb-2 rounded-sm border border-amber-500/20 p-3 text-xs text-slate-300">
              {d.player_name}: fee {fmt(d.fee)} (fair value {fmt(d.fair_value)})
            </div>
          ))
        )}
      </Panel>
    </>
  );
}

function NewClub({ count, max }: any) {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [countryCode, setCountryCode] = useState("");
  const [cityName, setCityName] = useState("");
  const [busy, setBusy] = useState(false);
  if (count >= max) return null;
  const location = validateClubLocation(countryCode, cityName);
  const clubName = name.trim();
  const create = async () => {
    if (clubName.length < 3) {
      toast.error("Enter a club name with at least 3 characters.");
      return;
    }
    const validatedLocation = validateClubLocation(countryCode, cityName);
    if ("error" in validatedLocation) {
      toast.error(validatedLocation.error);
      return;
    }
    setBusy(true);
    try {
      const slug = `${clubName.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-${Date.now().toString(36).slice(-4)}`;
      await api.post("/clubs", {
        club_name: clubName,
        slug,
        short_name: clubName.slice(0, 12),
        primary_color: "#0F766E",
        secondary_color: "#F8FAFC",
        accent_color: "#F59E0B",
        country_code: validatedLocation.countryCode,
        city_name: validatedLocation.cityName,
        club_type: "community",
      });
      navigate("/onboarding");
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Panel eyebrow={`Expand · ${count}/${max} clubs`} title="Add a club" testid="new-club-panel">
      <p className="mb-3 text-sm text-slate-400">
        Owning several clubs makes you a labelled multi-club ownership group. Sister clubs can't share a prize bracket,
        and transfers between them must sit inside a fair-value band.
      </p>
      <div className="space-y-2">
        <input
          data-testid="new-club-name-input"
          aria-label="Club name"
          className="gx-input"
          placeholder="Club name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <div className="grid grid-cols-2 gap-2">
          <input
            data-testid="new-club-country-input"
            aria-label="Country code"
            className="gx-input"
            placeholder="Country code (NG)"
            autoComplete="country"
            maxLength={2}
            value={countryCode}
            onChange={(e) => setCountryCode(e.target.value)}
          />
          <input
            data-testid="new-club-city-input"
            aria-label="City"
            className="gx-input"
            placeholder="City"
            autoComplete="address-level2"
            value={cityName}
            onChange={(e) => setCityName(e.target.value)}
          />
        </div>
        <Btn disabled={clubName.length < 3 || !location.valid || busy} onClick={create} data-testid="create-club-button">
          Create
        </Btn>
      </div>
    </Panel>
  );
}

export default function MyClubs() {
  const { clubs, active, select } = useActiveClub();
  const { data: cc } = useControlCenter();
  const { data: club, isLoading } = useClub(active?.club_id);
  return (
    <div data-testid="my-clubs-page">
      <PageHeader
        eyebrow="My clubs"
        title={club?.club_name || "Clubs"}
        sub={club?.ownership_group?.label}
        action={
          <div className="flex items-center gap-2">
            {club && (
              <Link
                to={`/app/clubs/${club.club_id}/story`}
                className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs transition-colors"
              >
                <BookOpen className="w-3.5 h-3.5" />
                <span>Club Story</span>
              </Link>
            )}
            <div className="flex gap-1">
              {clubs.map((c: any) => (
                <button
                  key={c.club_id}
                  data-testid={`select-club-${c.club_id}`}
                  onClick={() => select(c.club_id)}
                  className={`gx-btn ${c.club_id === active?.club_id ? "gx-btn-primary" : "gx-btn-secondary"}`}
                >
                  {c.club_name}
                </button>
              ))}
            </div>
          </div>
        }
      />
      {isLoading || !club ? (
        <Loading />
      ) : (
        <div className="grid gap-6 lg:grid-cols-12">
          <Panel className="lg:col-span-12" testid="club-summary">
            <div className="grid grid-cols-2 gap-6 md:grid-cols-6">
              <Stat label="Club value" value={<Coin amount={club.value} />} />
              <Stat label="Fans" value={fmt(club.health.fans)} />
              <Stat label="Prestige" value={club.health.prestige} />
              <Stat label="Squad" value={club.health.squad_size} />
              <Stat label="Manager" value={club.manager?.name || "-"} />
              <Stat
                label="Status"
                value={<Chip tone={club.stage === "active" ? "emerald" : "gold"}>{club.stage}</Chip>}
              />
            </div>
          </Panel>
          <ShowroomPanel club={club} />
          <Facilities club={club} />
          <Capital club={club} clubs={clubs} />
          <Commercial club={club} />
          <div className="lg:col-span-12">
            <NewClub count={clubs.length} max={cc?.max_clubs || 3} />
          </div>
        </div>
      )}
    </div>
  );
}
