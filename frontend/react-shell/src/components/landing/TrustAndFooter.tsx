import React from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight, Globe2, Plus, ShieldCheck } from "lucide-react";
import { useAuth } from "@/lib/auth";

const steps = [
  ["Find your place.", "Create your account and explore the football world. Review the current availability and rules before participating."],
  ["Make it your own.", "Build your starting squad, appoint a manager and shape your club’s identity and facilities."],
  ["Write the next chapter.", "Develop talent, enter eligible competitions and make the sporting and commercial decisions that matter."],
];

const questions = [
  ["What am I buying in GTEX?", "Players, clubs and luxury assets are virtual game assets, not physical possessions. GTEX Coin powers the club economy; Fan Coin is used for gifting and fan actions and is non-withdrawable. Club Support Units provide supporter status, not shares, dividends or investment returns."],
  ["How do deposits, fees and withdrawals work?", "Naira deposits use Paystack when the payment provider is configured. Check the current exchange rate, processor availability and fees in the finance centre before paying. Withdrawals require an eligible balance and pass country, account, KYC and fraud checks; requests are reviewed. Promotional funds and Fan Coin are not withdrawable. A displayed asset value or club revenue figure is not automatically available to withdraw."],
  ["Is television revenue guaranteed?", "No. The broadcast system uses recorded match-viewing and advertising revenue, active rights and the applicable allocation rules. A participating club receives a share only if a balance remains after rights-holder and platform allocations. This page does not advertise broadcast contracts, fixed payments or public club earnings."],
  ["Who can enter competitions or receive prizes?", "Participation depends on each competition’s rules, account eligibility and applicable age, geographic and payment restrictions. Check the current terms in the product before entering or funding an account. This public page does not confirm legal eligibility, publish a jackpot schedule or promise winnings. If the applicable requirements are unavailable, do not proceed with a paid entry."],
  ["Are the stories and images live game results?", "The homepage features clearly labelled editorial introductions and generated illustrative imagery, not actual owners, player profiles, sponsors, balances or match results. The signed-in newsroom provides event-driven reporting with access controls. Private management requests and scouting information remain in the owner workspace."],
];

export function TrustAndFooter() {
  const { user } = useAuth();
  return (
    <>
      <section id="how" className="gp-how" aria-labelledby="how-title"><div className="gp-container gp-section"><p className="gp-eyebrow">Your first chapter</p><h2 id="how-title">From football fan to club builder.</h2><ol className="gp-how-steps">{steps.map(([title, description], i) => <li key={title}><span className="gp-step-number">0{i + 1}</span><h3>{title}</h3><p>{description}</p></li>)}</ol></div></section>
      <section id="eligibility" className="gp-container gp-section gp-trust-grid" aria-labelledby="trust-title"><div><ShieldCheck size={30} aria-hidden="true" /><p className="gp-eyebrow">Clarity comes first</p><h2 id="trust-title">Know the game.<br />Know the rules.</h2><p>Ambition belongs on the pitch.<br />Clarity belongs in every transaction.</p><Link to="/app/finance" className="gp-text-link">Review account eligibility <ArrowUpRight size={18} aria-hidden="true" /></Link></div><div className="gp-faq">{questions.map(([question, answer]) => <details key={question}><summary>{question}<Plus size={18} aria-hidden="true" /></summary><p>{answer}</p></details>)}</div></section>
      <section className="gp-final" aria-labelledby="final-title"><div className="gp-container gp-final-inner"><p className="gp-eyebrow">Your club. Your world. Your legacy.</p><h2 id="final-title">Football has its legends.<br /><em>What will your story be?</em></h2><p>For the talent spotters. The tacticians. The ones who build.</p><div className="gp-final-actions"><Link to={user ? "/app" : "/signup"} className="gp-button gp-button-gold" data-testid="landing-footer-cta">Start your legacy <ArrowUpRight size={18} aria-hidden="true" /></Link><a href="#commercial" className="gp-button gp-button-outline">Explore the business of football <ArrowUpRight size={18} aria-hidden="true" /></a></div><span className="gp-final-note">Virtual football world. Real decisions. No guaranteed financial returns.</span></div></section>
      <footer className="gp-container gp-footer"><div className="gp-footer-top"><Link to="/" className="gp-brand" aria-label="GTEX home"><Globe2 aria-hidden="true" /><span>GTEX<span className="gp-brand-dot">.</span></span></Link><p>Global Talent Exchange<br /><span>A whole world of football.</span></p><nav aria-label="Footer navigation"><a href="#world">The world</a><a href="#how">How it works</a><a href="#eligibility">Payments & eligibility</a><Link to="/login">Sign in</Link></nav></div><div className="gp-footer-bottom"><span>© {new Date().getFullYear()} Global Talent Exchange</span><span>Built for the love of the game.</span></div></footer>
    </>
  );
}
