import React from "react";
import { useParams, Link } from "react-router-dom";
import { useActiveClub } from "@/lib/owner";
import { ClubAuthorityPanel } from "@/components/governance/ClubAuthorityPanel";
import { Shield, ArrowLeft, Building2 } from "lucide-react";

export const ClubAuthorityPage: React.FC = () => {
  const { clubId: routeClubId } = useParams<{ clubId?: string }>();
  const { active, clubs } = useActiveClub();

  const clubId = routeClubId || active?.club_id;
  const clubName = active?.club_name || "Your Club";

  if (!clubId) {
    return (
      <div className="p-8 max-w-7xl mx-auto space-y-6">
        <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-8 text-center space-y-4">
          <Shield className="w-12 h-12 text-purple-400 mx-auto" />
          <h2 className="text-xl font-bold text-white">No Club Found</h2>
          <p className="text-sm text-slate-400 max-w-md mx-auto">
            You must claim or select a club to configure governance and delegation authority policies.
          </p>
          <Link
            to="/app/clubs"
            className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold uppercase tracking-wider transition"
          >
            <span>View My Clubs</span>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-6" data-testid="club-authority-page">
      {/* Breadcrumb / Top Bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3 text-xs text-slate-400">
          <Link to="/app" className="hover:text-white transition flex items-center space-x-1">
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Control Center</span>
          </Link>
          <span>/</span>
          <span className="text-purple-300 font-semibold">{clubName}</span>
          <span>/</span>
          <span className="text-white font-bold">Authority & Governance</span>
        </div>

        {clubs && clubs.length > 1 && (
          <div className="flex items-center space-x-2 text-xs">
            <Building2 className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-400">Managing:</span>
            <span className="font-bold text-white">{clubName}</span>
          </div>
        )}
      </div>

      {/* Main Authority Component */}
      <ClubAuthorityPanel clubId={clubId} />
    </div>
  );
};

export default ClubAuthorityPage;
