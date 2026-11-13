import React from "react";
import { OrgStructure, StaffPosition } from "@/lib/clubAuthority";
import { Crown, UserCheck, UserX, Award, Shield, Compass, Activity, Brain } from "lucide-react";
import { coinWithNaira } from "@/lib/money";

interface OrganizationalStructureViewProps {
  orgStructure: OrgStructure | null;
  isLoading: boolean;
}

const ROLE_ICONS: Record<string, React.ReactNode> = {
  owner: <Crown className="w-5 h-5 text-amber-400" />,
  general_manager: <Shield className="w-5 h-5 text-purple-400" />,
  first_team_manager: <Activity className="w-5 h-5 text-emerald-400" />,
  head_of_youth_development: <Brain className="w-5 h-5 text-sky-400" />,
  chief_scout: <Compass className="w-5 h-5 text-orange-400" />,
  medical_director: <UserCheck className="w-5 h-5 text-rose-400" />,
};

export const OrganizationalStructureView: React.FC<OrganizationalStructureViewProps> = ({
  orgStructure,
  isLoading,
}) => {
  if (isLoading) {
    return (
      <div className="rounded-xl border border-white/10 bg-black/40 p-6 animate-pulse">
        <div className="h-6 w-48 bg-white/10 rounded mb-4" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-40 bg-white/5 rounded-xl border border-white/5" />
          ))}
        </div>
      </div>
    );
  }

  if (!orgStructure) {
    return (
      <div className="rounded-xl border border-white/10 bg-black/40 p-6 text-center text-slate-400 text-sm">
        Organizational structure unavailable.
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="org-structure-view">
      {/* Apex: Owner Executive Card */}
      <div className="relative overflow-hidden rounded-2xl border-2 border-amber-500/40 bg-gradient-to-r from-amber-950/60 via-slate-950 to-slate-900 p-6 shadow-2xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center space-x-4">
            <div className="w-14 h-14 rounded-2xl bg-amber-500/20 border border-amber-400/50 flex items-center justify-center shadow-lg">
              <Crown className="w-8 h-8 text-amber-400" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-[10px] font-black uppercase tracking-widest px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
                  Apex Authority
                </span>
                <span className="text-xs text-slate-400 font-mono">Owner ID: {orgStructure.owner.user_id.slice(0, 10)}...</span>
              </div>
              <h3 className="text-xl font-black text-white mt-1">Club Chairman & Sole Proprietor</h3>
              <p className="text-xs text-amber-200/80">
                Ultimate fiduciary veto, supreme delegation jurisdiction, reserved appointments.
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2 bg-black/40 border border-white/10 px-3.5 py-2 rounded-xl">
            <Shield className="w-4 h-4 text-amber-400" />
            <span className="text-xs font-semibold text-slate-200">100% Retained Sovereign Rights</span>
          </div>
        </div>
      </div>

      {/* Appointed Staff Tier */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-xs font-black uppercase tracking-wider text-slate-400">
            Executive & Sporting Hierarchy ({orgStructure.staff_positions.length} Appointed Roles)
          </h4>
          <span className="text-xs text-slate-500">Subject to Delegation Thresholds</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {orgStructure.staff_positions.map((pos: StaffPosition) => {
            const staff = pos.appointed_staff;
            const icon = ROLE_ICONS[pos.role_key] || <Award className="w-5 h-5 text-purple-400" />;

            return (
              <div
                key={pos.role_key}
                className={`relative rounded-xl border p-4 transition-all duration-200 ${
                  pos.is_vacant
                    ? "border-dashed border-red-500/30 bg-red-950/10"
                    : "border-white/10 bg-slate-900/80 hover:border-purple-500/40 hover:bg-slate-900"
                }`}
                data-testid={`staff-card-${pos.role_key}`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center">
                      {icon}
                    </div>
                    <div>
                      <span className="text-[10px] font-black uppercase tracking-wider text-purple-300">
                        {pos.role_label}
                      </span>
                      <h4 className="text-sm font-bold text-white">
                        {staff ? staff.name : "Vacant Role"}
                      </h4>
                    </div>
                  </div>

                  {staff && (
                    <div className="flex flex-col items-end">
                      <span className="text-xs font-black text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-lg">
                        {staff.rating} OVR
                      </span>
                      <span className="text-[10px] text-slate-400 mt-1">
                        {staff.nationality} · {staff.age}y
                      </span>
                    </div>
                  )}
                </div>

                {staff ? (
                  <div className="mt-4 pt-3 border-t border-white/10 space-y-2">
                    <div className="grid grid-cols-2 gap-2 text-[11px]">
                      {staff.tactical_flexibility !== undefined && (
                        <div className="bg-black/30 rounded p-1.5 flex justify-between">
                          <span className="text-slate-400">Tactics:</span>
                          <span className="font-bold text-emerald-400">{staff.tactical_flexibility}</span>
                        </div>
                      )}
                      {staff.youth_development !== undefined && (
                        <div className="bg-black/30 rounded p-1.5 flex justify-between">
                          <span className="text-slate-400">Youth Dev:</span>
                          <span className="font-bold text-sky-400">{staff.youth_development}</span>
                        </div>
                      )}
                      {staff.scouting_accuracy !== undefined && (
                        <div className="bg-black/30 rounded p-1.5 flex justify-between">
                          <span className="text-slate-400">Scouting:</span>
                          <span className="font-bold text-orange-400">{staff.scouting_accuracy}</span>
                        </div>
                      )}
                      {staff.medical_expertise !== undefined && (
                        <div className="bg-black/30 rounded p-1.5 flex justify-between">
                          <span className="text-slate-400">Medical:</span>
                          <span className="font-bold text-rose-400">{staff.medical_expertise}</span>
                        </div>
                      )}
                      {staff.ambition !== undefined && (
                        <div className="bg-black/30 rounded p-1.5 flex justify-between">
                          <span className="text-slate-400">Ambition:</span>
                          <span className="font-bold text-purple-400">{staff.ambition}</span>
                        </div>
                      )}
                      {staff.loyalty !== undefined && (
                        <div className="bg-black/30 rounded p-1.5 flex justify-between">
                          <span className="text-slate-400">Loyalty:</span>
                          <span className="font-bold text-amber-400">{staff.loyalty}</span>
                        </div>
                      )}
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1">
                      <span>Salary: {coinWithNaira(staff.salary_weekly, "FAN")}/wk</span>
                      <span className="font-semibold text-purple-300">
                        {pos.delegated_activities_count} Delegated Activities
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="mt-4 pt-3 border-t border-red-500/20 text-center">
                    <p className="text-xs text-red-300/80 flex items-center justify-center gap-1.5">
                      <UserX className="w-3.5 h-3.5" /> Direct Owner Operation Required
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
