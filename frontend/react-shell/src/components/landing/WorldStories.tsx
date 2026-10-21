import React from "react";
import { Link } from "react-router-dom";
import { ArrowRight, ArrowUpRight, Building2, Plane, Shield, Plus } from "lucide-react";
import { publicUrl } from "@/lib/publicPath";

export function WorldStories() {
  return (
    <section className="gp-section gp-container" aria-labelledby="world-title">
      <div className="gp-section-heading"><div><p className="gp-eyebrow">Inside the GTEX universe</p><h2 id="world-title">Football never stands still.</h2></div><Link className="gp-text-link" to="/app/newsroom">Enter the newsroom <ArrowUpRight size={18} aria-hidden="true" /></Link></div>
      <p className="gp-section-intro">Beyond the final whistle, there is always another story. Explore the world your club can become part of.</p>
      <div className="gp-editorial-grid">
        <article className="gp-feature-story">
          <a href="#ownership" className="gp-story-image-link"><img src={publicUrl("/img/gtex-club-estate.webp")} alt="Editorial illustration of a football training campus at dusk" width="1536" height="1024" loading="lazy" /><span className="gp-image-tag">The ownership edit</span><ArrowUpRight className="gp-image-arrow" aria-hidden="true" /></a>
          <p className="gp-story-category">Club life · An introduction</p><h3><a href="#ownership">Great clubs are built. <br />Not just bought.</a></h3><p>From the academy to the boardroom, discover the decisions that shape a football institution.</p>
        </article>
        <div className="gp-secondary-stories">
          <article className="gp-small-story"><a href="#talent"><img src={publicUrl("/img/gtex-academy.webp")} alt="Editorial illustration of footballers developing their game in training" width="1536" height="1024" loading="lazy" /></a><div><p className="gp-story-category">The next generation</p><h3><a href="#talent">Every legend starts as a discovery.</a></h3><a className="gp-text-link" href="#talent">Explore the regen journey <ArrowRight size={16} aria-hidden="true" /></a></div></article>
          <article className="gp-small-story"><a href="#club-life"><img src={publicUrl("/img/gtex-aviation.webp")} alt="Editorial illustration of a private jet on the apron at dusk" width="1536" height="1024" loading="lazy" /></a><div><p className="gp-story-category">Beyond the pitch</p><h3><a href="#club-life">An ambition that travels with you.</a></h3><a className="gp-text-link" href="#club-life">Discover club prestige <ArrowRight size={16} aria-hidden="true" /></a></div></article>
        </div>
      </div>
      <div className="gp-editorial-disclosure"><span>Editorial features, not live announcements.</span><span>Verified events and club stories are available in the signed-in newsroom.</span></div>
    </section>
  );
}

export function OwnershipStory() {
  return (
    <section id="ownership" className="gp-ownership" aria-labelledby="ownership-title">
      <div className="gp-container gp-section gp-ownership-grid">
        <div className="gp-ownership-copy"><p className="gp-eyebrow">The owner’s seat</p><h2 id="ownership-title">Don’t just follow<br />a football club.<br /><em>Build one.</em></h2><p>Your identity. Your philosophy. Your decisions. Own up to three clubs and shape everything from the people on the pitch to the place they call home.</p><Link to="/app/clubs" className="gp-text-link">Explore club ownership <ArrowUpRight size={18} aria-hidden="true" /></Link>
          <div className="gp-ownership-fact"><Shield size={28} aria-hidden="true" /><p><strong>A club, not a collection.</strong><span>Squad, manager, facilities and a story that belongs to you.</span></p></div>
        </div>
        <div className="gp-club-preview" id="club-life">
          <figure><img src={publicUrl("/img/gtex-club-estate.webp")} alt="Illustrative training campus and club facilities, not an owned club" loading="lazy" width="1536" height="1024" /><figcaption>Explore the owner experience · Editorial illustration</figcaption></figure>
          <div className="gp-club-preview-body"><div className="gp-club-preview-heading"><div><p className="gp-eyebrow">Your club starts here</p><h3>A home for your ambition.</h3></div><Building2 size={28} aria-hidden="true" /></div>
            <details><summary>Identity & football philosophy<Plus size={18} aria-hidden="true" /></summary><p>Create your club identity, build a starting squad and appoint a manager. The manager’s personality and decisions are part of your club’s story.</p><Link to="/app/clubs">Open club management <ArrowUpRight size={16} aria-hidden="true" /></Link></details>
            <details><summary>Facilities & player development<Plus size={18} aria-hidden="true" /></summary><p>Training, academy, medical and stadium facilities shape the environment you provide. Review upgrade costs inside your club before committing its budget.</p><Link to="/app/academy">Explore your academy <ArrowUpRight size={16} aria-hidden="true" /></Link></details>
            <details><summary>Prestige & eligible luxury assets<Plane size={18} aria-hidden="true" /></summary><p>Eligible assets, including private jets, are virtual club possessions. Jet acquisitions, significant facility upgrades and player gifts can become verified stories. Ordinary luxury purchases do not automatically become global news.</p><Link to="/app/story">Open your club story <ArrowUpRight size={16} aria-hidden="true" /></Link></details>
          </div>
        </div>
      </div>
    </section>
  );
}
