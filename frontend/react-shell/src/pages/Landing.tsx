import React from "react";
import { LandingHero } from "@/components/landing/LandingHero";
import { WorldStories, OwnershipStory } from "@/components/landing/WorldStories";
import { FinanceStory } from "@/components/landing/FinanceStory";
import { TalentStory, CompetitionStory } from "@/components/landing/FootballStories";
import { TrustAndFooter } from "@/components/landing/TrustAndFooter";

export default function Landing() {
  return (
    <div data-testid="landing-page" className="gtex-public font-sans">
      <a className="gp-skip" href="#world">Skip to content</a>
      <LandingHero />
      <main id="world">
        <WorldStories />
        <OwnershipStory />
        <FinanceStory />
        <TalentStory />
        <CompetitionStory />
        <TrustAndFooter />
      </main>
    </div>
  );
}
