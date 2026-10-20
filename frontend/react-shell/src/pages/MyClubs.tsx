import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { fmt, label, useActiveClub, useClub, useClubShowroom, useControlCenter, useRefreshOwner } from "@/lib/owner";
import { Btn, Chip, Coin, Empty, Loading, PageHeader, Panel, Stat } from "@/components/gtex/ui";
import { Plane, Building, Gift, Sparkles, BookOpen, ExternalLink, CheckCircle } from "lucide-react";

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
  const [busyItem, setBusyItem] = useState<string | null>(null);
  const [giftingItem, setGiftingItem] = useState<any | null>(null);
  const [selectedPlayerId, setSelectedPlayerId] = useState<string>("");
  const [giftNote, setGiftNote] = useState<string>("");

  const items: any[] = data?.showroom || [];
  const squad: any[] = data?.squad || club.squad || [];

  const handlePurchase = async (catalogKey: string) => {
    setBusyItem(catalogKey);
    try {
      const res = await api.post(`/owner/clubs/${club.club_id}/showroom/purchase`, {
        catalog_key: catalogKey,
      });
      const d = res.data;
      if (d.broadcast_globally) {
        toast.success(`Acquired ${d.asset.custom_name}! Broadcast live to GTEX global ticker.`);
      } else {
        toast.success(`Acquired ${d.asset.custom_name} for club operations.`);
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
    if (!giftingItem || !selectedPlayerId) return;
    setBusyItem(giftingItem.key);
    try {
      await api.post(`/owner/clubs/${club.club_id}/showroom/gift`, {
        player_id: selectedPlayerId,
        catalog_key: giftingItem.key,
        note: giftNote,
      });
      toast.success(`Gifted ${giftingItem.name} to player! Broadcast live to GTEX wire.`);
      setGiftingItem(null);
      setSelectedPlayerId("");
      setGiftNote("");
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setBusyItem(null);
    }
  };

  return (
    <Panel
      eyebrow="Luxury Fleet & Gifting"
      title="Showroom & Prestige Assets"
      testid="showroom-panel"
      className="lg:col-span-12"
    >
      <p className="text-xs text-slate-400 mb-4 max-w-2xl">
        Jets and player gifts broadcast instantly on the global live wire upon confirmed blockchain/ledger settlement.
        Personal luxury purchases remain confidential to your boardroom.
      </p>

      {isLoading ? (
        <Loading />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {items.map((it: any) => {
            const isJet = it.category === "jet";
            return (
              <div
                key={it.key}
                className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 flex flex-col justify-between space-y-3 hover:border-amber-500/30 transition-colors"
              >
                <div className="space-y-2">
                  <div className="h-28 rounded-lg bg-slate-900 overflow-hidden relative border border-white/5 flex items-center justify-center">
                    <img
                      src={it.image_url}
                      alt={it.name}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        (e.target as HTMLElement).style.display = "none";
                      }}
                    />
                    <div className="absolute top-2 right-2">
                      {isJet ? (
                        <span className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase bg-amber-500/20 text-amber-300 border border-amber-500/30">
                          Global Wire
                        </span>
                      ) : (
                        <span className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase bg-slate-800 text-slate-400">
                          Private
                        </span>
                      )}
                    </div>
                  </div>

                  <div>
                    <h4 className="text-sm font-bold text-white">{it.name}</h4>
                    <p className="text-[11px] text-slate-400">{it.model || it.description}</p>
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-900 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-500">Price</span>
                    <span className="font-mono font-bold text-amber-400">{fmt(it.price_gtex)} GTX</span>
                  </div>

                  <div className="flex gap-2">
                    <Btn
                      variant="secondary"
                      className="flex-1 text-xs"
                      disabled={busyItem === it.key}
                      onClick={() => handlePurchase(it.key)}
                    >
                      {busyItem === it.key ? "…" : "Acquire"}
                    </Btn>

                    {it.can_gift_to_player && squad.length > 0 && (
                      <Btn
                        variant="ghost"
                        className="text-xs px-2.5 text-purple-400 hover:text-purple-300"
                        title="Gift to squad player"
                        onClick={() => {
                          setGiftingItem(it);
                          setSelectedPlayerId(squad[0]?.id || "");
                        }}
                      >
                        <Gift className="w-3.5 h-3.5" />
                      </Btn>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Gift Modal */}
      {giftingItem && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <h3 className="text-base font-bold text-white flex items-center space-x-2">
              <Gift className="w-4 h-4 text-purple-400" />
              <span>Gift {giftingItem.name} to Player</span>
            </h3>
            <p className="text-xs text-slate-400">
              Gifting luxury assets boosts player morale (+15%) and announces your club's prestige on the GTEX Global Wire.
            </p>

            <form onSubmit={handleGift} className="space-y-3">
              <div>
                <label className="text-xs font-medium text-slate-300">Select Squad Player</label>
                <select
                  value={selectedPlayerId}
                  onChange={(e) => setSelectedPlayerId(e.target.value)}
                  className="w-full mt-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-purple-400"
                >
                  {squad.map((p: any) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.position}) · Morale: {p.morale}%
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs font-medium text-slate-300">Award Memo / Note</label>
                <input
                  type="text"
                  value={giftNote}
                  onChange={(e) => setGiftNote(e.target.value)}
                  placeholder="e.g. Hat-trick performance reward"
                  className="w-full mt-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-purple-400"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setGiftingItem(null)}
                  className="px-4 py-2 rounded-lg text-xs font-semibold text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={busyItem === giftingItem.key}
                  className="px-4 py-2 rounded-lg text-xs font-bold bg-purple-600 hover:bg-purple-500 text-white transition-colors"
                >
                  {busyItem === giftingItem.key ? "Gifting…" : `Gift · ${fmt(giftingItem.price_gtex)} GTX`}
                </button>
              </div>
            </form>
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
  const [busy, setBusy] = useState(false);
  if (count >= max) return null;
  const create = async () => {
    setBusy(true);
    try {
      const slug = `${name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-${Date.now().toString(36).slice(-4)}`;
      await api.post("/clubs", {
        club_name: name,
        slug,
        short_name: name.slice(0, 12),
        primary_color: "#0F766E",
        secondary_color: "#F8FAFC",
        accent_color: "#F59E0B",
        country_code: "NG",
        city_name: "Lagos",
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
      <div className="flex gap-2">
        <input
          data-testid="new-club-name-input"
          className="gx-input"
          placeholder="Abuja Eagles FC"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <Btn disabled={name.length < 3 || busy} onClick={create} data-testid="create-club-button">
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
