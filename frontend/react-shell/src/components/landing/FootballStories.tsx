import React, { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, ArrowUpRight, Trophy, Globe2, Clock3, Flag } from "lucide-react";
import { publicUrl } from "@/lib/publicPath";

const journey = [
  { title: "Discover", headline: "See the player they could become.", body: "Scout the regen market for talent that fits your club. Look beyond a single rating: age, role, personality and potential all belong in the decision.", link: "/app/market", action: "Explore the player market" },
  { title: "Develop", headline: "Potential needs the right environment.", body: "Build your academy and training facilities, work with your manager and give your prospects a place to grow. Development is a journey, not a guaranteed increase in value.", link: "/app/academy", action: "Explore player development" },
  { title: "Define their future", headline: "Build around them. Or open a new door.", body: "Keep a player central to your sporting ambitions or review eligible transfer offers. Only a completed transfer creates sale proceeds; a valuation is not cash.", link: "/app/squad", action: "Explore squad decisions" },
];

export function TalentStory() {
  const [stage, setStage] = useState(0);
  const current = journey[stage];
  return (
    <section id="talent" className="gp-talent-section" aria-labelledby="talent-title"><div className="gp-container gp-section gp-talent-grid">
      <div className="gp-talent-image"><img src={publicUrl("/img/gtex-academy.webp")} alt="Editorial illustration of a young adult footballer training under the lights" width="1536" height="1024" loading="lazy" /><span className="gp-image-tag">Talent is everywhere. Vision is rare.</span><span className="gp-image-credit">Editorial illustration · Not a player profile</span></div>
      <div className="gp-talent-copy"><p className="gp-eyebrow">The next name on everyone’s lips</p><h2 id="talent-title">Before the world<br />knows their name.<br /><em>You do.</em></h2><p>Discover regens. Nurture ability. Shape a career. Your next defining signing could begin in your own academy.</p>
        <div className="gp-journey-controls" role="group" aria-label="Player development journey">{journey.map((item, i) => <button key={item.title} type="button" aria-pressed={stage === i} aria-controls="talent-stage" onClick={() => setStage(i)}><span>0{i + 1}</span>{item.title}</button>)}</div>
        <div className="gp-journey-content" id="talent-stage" aria-live="polite" aria-atomic="true"><h3>{current.headline}</h3><p>{current.body}</p><Link className="gp-text-link" to={current.link}>{current.action}<ArrowUpRight size={18} aria-hidden="true" /></Link></div>
      </div>
    </div></section>
  );
}

export function CompetitionStory() {
  return (
    <>
      <section id="competitions" className="gp-container gp-section" aria-labelledby="competitions-title">
        <div className="gp-section-heading"><div><p className="gp-eyebrow">Everything to play for</p><h2 id="competitions-title">The badge. The belief. The big nights.</h2></div><Link to="/app/competitions" className="gp-text-link">Explore competitions <ArrowUpRight size={18} aria-hidden="true" /></Link></div>
        <div className="gp-competition-banner"><img src={publicUrl("/img/gtex-world-hero.webp")} alt="Illustrative stadium setting for the competition experience" loading="lazy" width="1536" height="1024" /><div className="gp-competition-copy"><Trophy size={32} aria-hidden="true" /><p className="gp-eyebrow">Write your football history</p><h3>Some nights<br />change everything.</h3><p>Leagues, cup runs and the pursuit of silverware. Find your competition, follow the fixtures and see where your club stands.</p><Link to="/app/competitions" className="gp-button gp-button-gold">Find your next challenge <ArrowUpRight size={18} aria-hidden="true" /></Link></div><span className="gp-image-credit">Editorial illustration · Not a live fixture</span></div>
        <div className="gp-competition-info"><div><Trophy size={22} aria-hidden="true" /><div><h3>Compete on the published terms.</h3><p>View entries, fixtures, standings and prize rules inside each competition. Entry does not guarantee a prize.</p></div></div><div><Clock3 size={22} aria-hidden="true" /><div><h3>Jackpot events, without the guesswork.</h3><p>A fixed four-drop daily schedule is not confirmed for this public page. No unverified times, balances or countdowns are advertised.</p><a href="#eligibility" className="gp-text-link">Read participation information <ArrowRight size={16} aria-hidden="true" /></a></div></div></div>
      </section>
      <section className="gp-worldwide" aria-labelledby="worldwide-title"><div className="gp-container gp-section gp-worldwide-grid"><div><p className="gp-eyebrow">Beyond your home ground</p><h2 id="worldwide-title">Club pride.<br /><em>Global ambition.</em></h2><p>The football world is bigger than one badge. Explore national-team competitions, tournament player rentals and the managers who bring a squad together.</p><Link to="/app/national" className="gp-text-link">Explore the international game <ArrowUpRight size={18} aria-hidden="true" /></Link></div><div className="gp-worldwide-details"><Globe2 className="gp-worldwide-icon" strokeWidth={1} size={64} aria-hidden="true" /><div><Flag size={24} aria-hidden="true" /><h3>A different kind of call-up.</h3><p>Eligible tournament rentals let managers assemble a national-team squad under the competition’s rules. A rental is not a permanent player purchase.</p></div><div><h3>The right person in the dugout.</h3><p>Appoint a manager with their own traits and demands. Keep personal requests, scouting and club decisions in your private owner workspace.</p></div></div></div></section>
      <section id="commercial" className="gp-container gp-section gp-commercial" aria-labelledby="commercial-title"><div><p className="gp-eyebrow">An institution in the making</p><h2 id="commercial-title">Build a club<br />with a future.</h2></div><div><p>Squad development, facilities and commercial activity contribute to the story of a club. Explore valuations and eligible ownership transactions without confusing an in-game valuation with a guaranteed sale price.</p><details className="gp-commercial-details"><summary>Understand valuations & ownership transfers <ArrowUpRight size={18} aria-hidden="true" /></summary><p>The platform distinguishes system valuation, market valuation, an asking price and an executed sale. Listings must be available and transfers must pass ownership and eligibility checks. No club sale or return is promised.</p></details><a href="#business" className="gp-text-link">Explore commercial opportunities <ArrowUpRight size={18} aria-hidden="true" /></a></div></section>
    </>
  );
}
