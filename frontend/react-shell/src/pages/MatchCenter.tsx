import React, { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { Flame, Lightbulb, Megaphone, Radio } from "lucide-react";
import { api, errMsg } from "@/lib/api";
import { useRefreshOwner } from "@/lib/owner";
import { Btn, Chip, Loading, Panel } from "@/components/gtex/ui";

const GIFTS = [
  { code: "stadium_roar", name: "Stadium Roar", cost: 10 },
  { code: "captains_armband", name: "Captain's Armband", cost: 20 },
  { code: "home_end_banner", name: "Home End Banner", cost: 30 },
  { code: "golden_boot", name: "Golden Boot", cost: 50 },
  { code: "floodlights", name: "Floodlights", cost: 100 },
  { code: "legendary_stadium", name: "Legendary Stadium", cost: 1000 },
];

function GiftRail({ match, clubId }: any) {
  const refresh = useRefreshOwner();
  const [feed, setFeed] = useState<string[]>([]);
  const targets = [match.home_club_id, match.away_club_id].filter((c: string) => !c.startsWith("ai:"));
  const [target, setTarget] = useState(targets.includes(clubId) ? clubId : targets[0]);
  if (!targets.length) return null;
  const send = async (g: any) => {
    try {
      const { data } = await api.post("/owner/gifts/send", { club_id: target, gift_code: g.code, match_id: match.id });
      setFeed((f) => [`${data.sender} sent ${g.name}`, ...f].slice(0, 5));
      refresh();
    } catch (e) {
      toast.error(errMsg(e));
    }
  };
  return (
    <Panel eyebrow="Gift rail · Fan Coin" title="Back your club" testid="gift-rail">
      {targets.length > 1 && (
        <select data-testid="gift-target-select" className="gx-input mb-3" value={target} onChange={(e) => setTarget(e.target.value)}>
          {targets.map((t: string) => <option key={t} value={t}>{t === match.home_club_id ? match.home_name : match.away_name}</option>)}
        </select>
      )}
      <div className="grid grid-cols-2 gap-2">
        {GIFTS.map((g) => (
          <button key={g.code} data-testid={`gift-${g.code}`} onClick={() => send(g)} className="rounded-sm border border-amber-500/20 bg-amber-500/[0.04] px-3 py-2 text-left text-xs transition-colors hover:border-amber-400/60 hover:bg-amber-500/10">
            <span className="block font-semibold text-amber-200">{g.name}</span>
            <span className="gx-mono text-[10px] text-slate-400">{g.cost} FAN</span>
          </button>
        ))}
      </div>
      <p className="mt-3 text-[11px] text-slate-500">70% goes to the club, 30% platform. Gifts never interrupt the match feed.</p>
      {feed.map((f, i) => <p key={i} className="mt-1 text-xs text-amber-300">{f}</p>)}
    </Panel>
  );
}

function Momentum({ values, upto }: any) {
  return (
    <div className="flex h-16 items-end gap-0.5" data-testid="momentum-bar">
      {values.map((v: number, i: number) => (
        <div key={i} className="flex flex-1 flex-col justify-end">
          <div className={`rounded-t-[1px] transition-[height] duration-500 ${i * 5 <= upto ? (v >= 50 ? "bg-emerald-400" : "bg-cyan-500") : "bg-white/5"}`} style={{ height: `${i * 5 <= upto ? Math.abs(v - 50) * 1.8 + 6 : 6}%` }} />
        </div>
      ))}
    </div>
  );
}

function OwnerView({ view }: any) {
  if (!view) return null;
  return (
    <Panel eyebrow="Post-match · owner view" title={view.headline} testid="post-match-narrative">
      <p className="mb-4 flex items-start gap-2 text-sm italic text-slate-300"><Megaphone size={16} className="mt-0.5 shrink-0 text-emerald-400" />{view.manager_reaction}</p>
      <p className="gx-label">Why it happened</p>
      <div className="mb-4 grid grid-cols-2 gap-2">
        {view.why.map((w: any) => (
          <div key={w.factor} className="rounded-sm border border-white/5 p-2 text-xs">
            <p className="text-slate-500">{w.factor}</p>
            <p className={`gx-mono font-semibold ${w.impact === "positive" ? "text-emerald-300" : w.impact === "negative" ? "text-red-300" : "text-slate-200"}`}>{w.value}</p>
          </div>
        ))}
      </div>
      <p className="gx-label">What you can do next</p>
      <ul className="space-y-1 text-sm text-slate-300">{view.next_actions.map((a: string) => <li key={a} className="flex gap-2"><Lightbulb size={14} className="mt-0.5 text-amber-400" />{a}</li>)}</ul>
      {view.revenue_notes?.length > 0 && <p className="mt-3 text-xs text-slate-500">Revenue: {view.revenue_notes.join(" · ")}. Sponsor income is split 70/30.</p>}
    </Panel>
  );
}

export default function MatchCenter() {
  const { id } = useParams();
  const [params] = useSearchParams();
  const clubId = params.get("club") || "";
  const { data: m, isLoading } = useQuery({ queryKey: ["match", id], queryFn: async () => (await api.get(`/owner/matches/${id}`)).data });
  const [minute, setMinute] = useState(params.get("live") ? 0 : 120);
  useEffect(() => {
    if (minute >= 120) return undefined;
    const t = setTimeout(() => setMinute((x) => x + 3), 380);
    return () => clearTimeout(t);
  }, [minute]);
  const shown = useMemo(() => (m?.events || []).filter((e: any) => e.minute <= minute), [m, minute]);
  if (isLoading || !m) return <Loading label="Loading match" />;
  const score = shown.filter((e: any) => e.type === "goal").reduce((acc: any, e: any) => ({ ...acc, [e.team]: acc[e.team] + 1 }), { home: 0, away: 0 });
  const done = minute >= 90;
  const side = m.home_club_id === clubId ? "home" : m.away_club_id === clubId ? "away" : m.narrative?.home_owner_view ? "home" : "away";
  return (
    <div data-testid="match-center-page" className="grid gap-6 lg:grid-cols-12">
      <div className="space-y-6 lg:col-span-8">
        <section className="gx-panel gx-pitch-grid gx-panel-live relative overflow-hidden">
          <div className="flex items-center justify-between">
            <Chip tone={done ? "slate" : "emerald"}>{done ? "Full time" : <><Radio size={10} className="gx-live-dot" /> Live · {Math.min(minute, 90)}'</>}</Chip>
            {!done && <Btn variant="ghost" onClick={() => setMinute(120)} data-testid="skip-to-full-time">Skip to full time</Btn>}
          </div>
          <div className="my-8 grid grid-cols-3 items-center text-center">
            <p className="gx-display text-xl font-bold uppercase text-white sm:text-3xl">{m.home_name}</p>
            <p className="gx-display text-5xl font-black text-emerald-300 sm:text-7xl" data-testid="match-score">{score.home} – {score.away}</p>
            <p className="gx-display text-xl font-bold uppercase text-white sm:text-3xl">{m.away_name}</p>
          </div>
          <p className="gx-label">Tactical momentum</p>
          <Momentum values={m.narrative?.momentum || []} upto={minute} />
          <p className="mt-2 text-[11px] text-slate-500">Mentality: {m.narrative?.mentality?.home} vs {m.narrative?.mentality?.away}</p>
        </section>
        <Panel eyebrow="Live commentary" title="Event feed" testid="commentary-feed">
          <ol className="space-y-2">
            {[...shown].reverse().map((e: any, i: number) => (
              <li key={i} className={`gx-rise flex gap-3 rounded-sm px-3 py-2 text-sm ${e.type === "goal" ? "border border-emerald-500/30 bg-emerald-500/10 text-white" : "text-slate-300"}`}>
                <span className="gx-mono w-10 shrink-0 text-slate-500">{e.minute}'</span>
                {e.type === "goal" && <Flame size={14} className="mt-0.5 text-emerald-400" />}
                <span>{e.text}</span>
              </li>
            ))}
          </ol>
        </Panel>
      </div>
      <div className="space-y-6 lg:col-span-4">
        {done && <OwnerView view={m.narrative?.[`${side}_owner_view`]} />}
        <GiftRail match={m} clubId={clubId} />
        <Link to={`/app/competitions/${m.competition_id}`} className="gx-btn gx-btn-secondary w-full" data-testid="back-to-competition">Back to competition</Link>
      </div>
    </div>
  );
}
