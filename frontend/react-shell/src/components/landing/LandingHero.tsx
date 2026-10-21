import React, { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowDown, ArrowRight, ArrowUpRight, Globe2, Menu, X } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { publicUrl } from "@/lib/publicPath";

const navigation = [["The world", "#world"], ["Club ownership", "#ownership"], ["The marketplace", "#talent"], ["Competitions", "#competitions"]];

export function LandingHero() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  return (
    <>
      <header className="gp-header">
        <div className="gp-container gp-nav">
          <Link to="/" className="gp-brand" aria-label="GTEX home"><Globe2 aria-hidden="true" /><span>GTEX<span className="gp-brand-dot">.</span></span></Link>
          <nav className="gp-desktop-nav" aria-label="Main navigation">{navigation.map(([name, href]) => <a href={href} key={href}>{name}</a>)}</nav>
          <div className="gp-nav-actions">
            <Link className="gp-signin" to={user ? "/app" : "/login"} data-testid="landing-login-link">{user ? "My club" : "Sign in"}</Link>
            <Link className="gp-button gp-button-gold gp-nav-join" to={user ? "/app" : "/signup"} data-testid="landing-nav-signup">Enter the world <ArrowUpRight size={16} aria-hidden="true" /></Link>
            <button type="button" className="gp-menu-button" aria-label={open ? "Close navigation" : "Open navigation"} aria-expanded={open} aria-controls="public-mobile-nav" onClick={() => setOpen(!open)}>{open ? <X /> : <Menu />}</button>
          </div>
        </div>
        <nav id="public-mobile-nav" aria-label="Mobile navigation" className="gp-mobile-nav" hidden={!open} onKeyDown={(event) => { if (event.key === "Escape") { setOpen(false); document.querySelector<HTMLButtonElement>(".gp-menu-button")?.focus(); } }}>
          {navigation.map(([name, href]) => <a href={href} key={href} onClick={() => setOpen(false)}>{name}<ArrowUpRight size={16} aria-hidden="true" /></a>)}
          <Link to={user ? "/app" : "/signup"} onClick={() => setOpen(false)}>Enter the world<ArrowRight size={16} aria-hidden="true" /></Link>
        </nav>
      </header>
      <section className="gp-hero" aria-labelledby="hero-title">
        <img className="gp-hero-image" src={publicUrl("/img/gtex-world-hero.webp")} width="1536" height="1024" alt="Editorial illustration of a footballer stepping into a floodlit stadium" fetchPriority="high" />
        <div className="gp-hero-shade" />
        <div className="gp-container gp-hero-content">
          <p className="gp-eyebrow gp-hero-eyebrow"><span className="gp-square" /> A whole world of football. Yours to build.</p>
          <h1 id="hero-title">More than<br />a game.<br /><span>Your legacy.</span></h1>
          <p className="gp-hero-description">Build your club. Discover the next superstar.<br className="gp-desktop-break" /> Compete for glory. Leave your mark on a living football world.</p>
          <div className="gp-hero-actions">
            <Link to={user ? "/app" : "/signup"} className="gp-button gp-button-gold" data-testid="landing-activate-club-cta">{user ? "Return to your club" : "Start your legacy"}<ArrowUpRight size={18} aria-hidden="true" /></Link>
            <a href="#how" className="gp-button gp-button-outline">Discover GTEX <ArrowDown size={17} aria-hidden="true" /></a>
          </div>
          <p className="gp-hero-note">Football ownership. Player discovery. A world of possibility.</p>
        </div>
        <span className="gp-image-credit">GTEX world · Editorial illustration</span>
      </section>
      <div className="gp-chapter-bar"><div className="gp-container gp-chapters">
        <a href="#ownership"><span>Build something that lasts</span><strong>Own the club.</strong><ArrowUpRight aria-hidden="true" /></a>
        <a href="#talent"><span>See what others don’t</span><strong>Discover greatness.</strong><ArrowUpRight aria-hidden="true" /></a>
        <a href="#competitions"><span>Make the whole world watch</span><strong>Chase the glory.</strong><ArrowUpRight aria-hidden="true" /></a>
      </div></div>
    </>
  );
}
