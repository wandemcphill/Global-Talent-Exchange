import React, { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowDown, ArrowUpRight, Radio, Handshake, Repeat2, Ticket, ShieldCheck } from "lucide-react";

// Grounded in broadcast_rights/service.py and owner_console/competitions.py; no simulated financial results.
export const REVENUE_STORIES = [
  { id: "broadcast", label: "Television & broadcast", icon: Radio, title: "A bigger stage. A wider audience.", body: "GTEX’s broadcast system records match-viewing revenue and distributes it between rights holders, the platform and participating clubs under the applicable rights.", steps: ["Recorded viewing & advertising revenue", "Applicable rights-holder and platform shares", "Remaining revenue shared by participating clubs"], note: "A club share exists only when revenue remains after those allocations. This is a rules overview, not a guaranteed payment or a withdrawable balance." },
  { id: "sponsorship", label: "Sponsorship & endorsements", icon: Handshake, title: "Build relationships beyond the touchline.", body: "Active club sponsorships and player endorsements settle against their agreed per-match terms. The owner-console settlement records the gross amount, platform fee and net club income.", steps: ["An active sponsorship or endorsement deal", "Per-match settlement under its terms", "Net proceeds recorded to club cash"], note: "The current owner-console settlement applies a 30% platform fee to sponsorship and endorsement proceeds. Deals have a limited number of matches; income is not perpetual." },
  { id: "transfers", label: "Player trading", icon: Repeat2, title: "Develop talent. Decide its next chapter.", body: "A completed player sale can contribute to club finances. Keep a prospect at the heart of your squad or consider an eligible offer; potential value is not the same as a completed sale.", steps: ["Recruit and develop your squad", "Review an eligible transfer offer", "Completed sale recorded with fees and net proceeds"], note: "Players are in-game assets. Offers, transfer values and development outcomes are not guaranteed. Check the transaction’s applicable fees before accepting." },
  { id: "matchday", label: "Matchday & competition", icon: Ticket, title: "Give your supporters a reason to believe.", body: "The owner simulation records home-match gate receipts and competition prizes. Stadium facilities, fans and sporting results each play a role in the club’s wider story.", steps: ["An eligible home match or competition result", "Gate receipts or awarded competition prize", "Recorded income in the club economy"], note: "Prize eligibility and awards depend on the competition’s rules and result. In-game club income is not a promise of real-money earnings." },
];

export function FinanceStory() {
  const [selected, setSelected] = useState("broadcast");
  const story = REVENUE_STORIES.find((item) => item.id === selected)!;
  return (
    <section id="business" className="gp-container gp-section" aria-labelledby="business-title">
      <div className="gp-section-heading"><div><p className="gp-eyebrow">The business behind the badge</p><h2 id="business-title">Think beyond the scoreboard.</h2></div><p className="gp-heading-aside">Sporting ambition meets commercial decisions.<br />Understand what supports your club.</p></div>
      <div className="gp-finance-layout">
        <div className="gp-revenue-menu" role="group" aria-label="Explore club revenue sources">{REVENUE_STORIES.map((item) => <button key={item.id} type="button" aria-pressed={selected === item.id} aria-controls="revenue-explanation" onClick={() => setSelected(item.id)}><item.icon size={22} aria-hidden="true" /><span>{item.label}</span><ArrowUpRight size={18} aria-hidden="true" /></button>)}<p>Revenue sources explained.<br />No illustrative balances or invented returns.</p></div>
        <div className="gp-finance-explanation" id="revenue-explanation" aria-live="polite" aria-atomic="true"><div className="gp-finance-heading"><span className="gp-eyebrow">{story.label}</span><story.icon size={26} aria-hidden="true" /></div><h3>{story.title}</h3><p>{story.body}</p><ol className="gp-revenue-flow">{story.steps.map((step, i) => <li key={step}><span>{step}</span>{i < story.steps.length - 1 && <ArrowDown size={18} aria-hidden="true" />}</li>)}</ol><p className="gp-finance-note"><ShieldCheck size={18} aria-hidden="true" /><span>{story.note}</span></p></div>
      </div>
      <div className="gp-finance-footer"><p>Club finances and personal wallet balances are different. Always check the recorded balance classification.</p><Link className="gp-text-link" to="/app/finance">Open your finance centre <ArrowUpRight size={18} aria-hidden="true" /></Link></div>
    </section>
  );
}
