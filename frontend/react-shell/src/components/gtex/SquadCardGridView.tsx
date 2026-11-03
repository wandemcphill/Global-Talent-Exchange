/**
 * GTEX Skin Engine — Football Module View: Squad Card Grid View
 * Visual card grid presentation for Squad Management (Layer 3).
 */

import React from "react";
import { PlayerCard } from "./PlayerCard";
import { Btn, Coin } from "./ui";
import { fmt } from "@/lib/owner";

interface SquadCardGridViewProps {
  squad: any[];
  onSelectPlayer: (player: any) => void;
  targetPlayerId?: string | null;
}

export function SquadCardGridView({ squad, onSelectPlayer, targetPlayerId }: SquadCardGridViewProps) {
  if (!squad || squad.length === 0) {
    return (
      <div className="py-12 text-center text-slate-500 rounded-xl border border-white/10 bg-black/30">
        No registered squad players yet.
      </div>
    );
  }

  return (
    <div
      className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-6"
      data-testid="squad-card-grid-view"
    >
      {squad.map((p: any) => {
        const pid = String(p.player_ref || p.player_id || p.id);
        const isTarget = targetPlayerId && String(targetPlayerId) === pid;
        const rating = Number(p.rating || p.overall_rating || 72);
        const tier = rating >= 85 ? "legendary" : rating >= 78 ? "elite" : "standard";

        return (
          <div
            key={pid}
            className={`relative rounded-2xl transition-all ${
              isTarget ? "ring-2 ring-cyan-400 shadow-[0_0_24px_rgba(6,182,212,0.5)]" : ""
            }`}
          >
            <PlayerCard
              testid={`squad-card-${pid}`}
              name={p.name || p.canonical_display_name}
              rating={rating}
              position={p.position}
              age={p.age}
              nationality={p.nationality}
              club={p.current_club_name || p.club_name}
              image={p.image_url}
              tier={tier}
              badge={p.archetype || (p.is_regen ? "ACADEMY REGEN" : undefined)}
              onClick={() => onSelectPlayer(p)}
              stats={[
                { k: "Morale", v: p.morale || 85 },
                { k: "Value", v: fmt(p.value_coin || 0, 1) },
                { k: "Wage", v: `${fmt(p.wage || 0)}/m` },
                { k: "Form", v: p.average_rating || 7.0 },
              ]}
              footer={
                <Btn
                  variant="secondary"
                  className="w-full text-xs"
                  onClick={() => onSelectPlayer(p)}
                  data-testid={`inspect-squad-player-${pid}`}
                >
                  View Dossier
                </Btn>
              }
            />
          </div>
        );
      })}
    </div>
  );
}
