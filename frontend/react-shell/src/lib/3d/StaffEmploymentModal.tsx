/**
 * GTEX Living Football Ecosystem — Stage 4 Autonomous Staff Career & Employment Market
 * StaffEmploymentModal: Executive Hiring, Contract Ratification & Free Agency Release HUD.
 *
 * Surfaced from the Executive Boardroom Suite or Tactical Operations Center.
 * Features:
 *   - Role Vacancies & Executive Incumbent Roster
 *   - Global Free Agent & Staff Candidate Market with AI Suitability evaluation
 *   - Historical Career Dossiers (past club tenures, win rates, exit circumstances)
 *   - Authoritative Contract Negotiation & Ratification
 *   - Dismissal to Free Agency with Severance Ledger settlement
 */

import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  X,
  Briefcase,
  UserPlus,
  UserMinus,
  Users,
  Award,
  Shield,
  Sparkles,
  Coins,
  History,
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Search,
  Building2,
  Clock,
  ArrowRight,
  TrendingUp,
  AlertTriangle,
} from "lucide-react";
import { api, errMsg } from "@/lib/api";
import {
  clubStaffMarketVacanciesEndpoint,
  clubStaffMarketCandidatesEndpoint,
  clubStaffMarketOffersEndpoint,
  clubStaffMarketDismissEndpoint,
  type StaffVacanciesResponse,
  type StaffMarketPoolResponse,
  type StaffMarketCandidate,
  type StaffVacancyItem,
  type StaffFilledRoleItem,
  type StaffOfferSubmitPayload,
  type StaffOfferResponse,
  type StaffDismissPayload,
  type StaffDismissResponse,
} from "@/lib/ownerBriefing";

export interface StaffEmploymentModalProps {
  clubId: string;
  isOpen: boolean;
  onClose: () => void;
  initialRole?: string | null;
  initialTab?: "vacancies" | "market";
  onHireComplete?: (response: StaffOfferResponse) => void;
  onDismissComplete?: (response: StaffDismissResponse) => void;
}

const ROLE_OPTIONS: Array<{ key: string; label: string }> = [
  { key: "all", label: "All Roles" },
  { key: "first_team_manager", label: "First-Team Manager" },
  { key: "general_manager", label: "General Manager" },
  { key: "chief_scout", label: "Chief Scout" },
  { key: "head_of_youth_development", label: "Head of Youth Dev" },
  { key: "medical_director", label: "Medical Director" },
  { key: "technical_director", label: "Technical Director" },
  { key: "performance_director", label: "Performance Director" },
];

export const StaffEmploymentModal: React.FC<StaffEmploymentModalProps> = ({
  clubId,
  isOpen,
  onClose,
  initialRole = null,
  initialTab = "vacancies",
  onHireComplete,
  onDismissComplete,
}) => {
  const queryClient = useQueryClient();

  // Active navigation tab
  const [activeTab, setActiveTab] = useState<"vacancies" | "market">(initialTab);

  // Market filters
  const [selectedRoleFilter, setSelectedRoleFilter] = useState<string>(initialRole || "all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [freeAgentsOnly, setFreeAgentsOnly] = useState<boolean>(true);

  // Candidate expanded dossier & offer sheet
  const [expandedCandidateId, setExpandedCandidateId] = useState<string | null>(null);
  const [negotiatingCandidate, setNegotiatingCandidate] = useState<StaffMarketCandidate | null>(null);

  // Offer form state
  const [offerSalary, setOfferSalary] = useState<number>(1000);
  const [offerYears, setOfferYears] = useState<number>(2);
  const [marqueePremium, setMarqueePremium] = useState<boolean>(false);
  const [pitchNote, setPitchNote] = useState<string>("");
  const [lastOfferResult, setLastOfferResult] = useState<StaffOfferResponse | null>(null);

  // Dismissal confirmation state
  const [dismissRoleTarget, setDismissRoleTarget] = useState<StaffFilledRoleItem | null>(null);
  const [dismissReason, setDismissReason] = useState<string>("");

  // 1. Fetch Vacancies & Filled Roles
  const {
    data: vacanciesData,
    isLoading: isVacanciesLoading,
    refetch: refetchVacancies,
  } = useQuery<StaffVacanciesResponse>({
    queryKey: ["club-staff-vacancies", clubId],
    queryFn: async () => {
      const res = await api.get<StaffVacanciesResponse>(clubStaffMarketVacanciesEndpoint(clubId));
      return res.data;
    },
    enabled: isOpen && !!clubId,
  });

  // 2. Fetch Market Candidates
  const roleParam = selectedRoleFilter === "all" ? undefined : selectedRoleFilter;
  const statusParam = freeAgentsOnly ? "unemployed" : "all";

  const {
    data: marketData,
    isLoading: isMarketLoading,
    refetch: refetchMarket,
  } = useQuery<StaffMarketPoolResponse>({
    queryKey: ["club-staff-market", clubId, roleParam, statusParam],
    queryFn: async () => {
      const res = await api.get<StaffMarketPoolResponse>(
        clubStaffMarketCandidatesEndpoint(clubId, roleParam, statusParam, 50)
      );
      return res.data;
    },
    enabled: isOpen && !!clubId && activeTab === "market",
  });

  // 3. Offer Contract Mutation
  const offerMutation = useMutation({
    mutationFn: async (payload: StaffOfferSubmitPayload) => {
      const res = await api.post<StaffOfferResponse>(
        clubStaffMarketOffersEndpoint(clubId),
        payload
      );
      return res.data;
    },
    onSuccess: (data) => {
      setLastOfferResult(data);
      if (data.success && data.status === "accepted") {
        toast.success(data.message || "Contract signed & staff member appointed!");
        queryClient.invalidateQueries({ queryKey: ["club-staff-vacancies", clubId] });
        queryClient.invalidateQueries({ queryKey: ["club-staff-market", clubId] });
        queryClient.invalidateQueries({ queryKey: ["club-briefing", clubId] });
        queryClient.invalidateQueries({ queryKey: ["club-persona-details", clubId] });
        onHireComplete?.(data);
      } else {
        toast.error(data.message || "Offer was not accepted by the candidate");
      }
    },
    onError: (err) => {
      toast.error(errMsg(err) || "Failed to submit contract offer");
    },
  });

  // 4. Dismiss Staff Mutation
  const dismissMutation = useMutation({
    mutationFn: async (payload: StaffDismissPayload) => {
      const res = await api.post<StaffDismissResponse>(
        clubStaffMarketDismissEndpoint(clubId),
        payload
      );
      return res.data;
    },
    onSuccess: (data) => {
      toast.success(
        `Dismissed ${data.staff_name}. Severance of ₦${data.severance_paid.toLocaleString()} paid. Person released to Free Agency.`
      );
      setDismissRoleTarget(null);
      setDismissReason("");
      queryClient.invalidateQueries({ queryKey: ["club-staff-vacancies", clubId] });
      queryClient.invalidateQueries({ queryKey: ["club-staff-market", clubId] });
      queryClient.invalidateQueries({ queryKey: ["club-briefing", clubId] });
      queryClient.invalidateQueries({ queryKey: ["club-persona-details", clubId] });
      onDismissComplete?.(data);
    },
    onError: (err) => {
      toast.error(errMsg(err) || "Failed to dismiss staff member");
    },
  });

  if (!isOpen) return null;

  // Handle start contract negotiation
  const handleOpenNegotiation = (cand: StaffMarketCandidate) => {
    setNegotiatingCandidate(cand);
    setOfferSalary(cand.expected_salary_gtex);
    setOfferYears(2);
    setMarqueePremium(false);
    setPitchNote("");
    setLastOfferResult(null);
  };

  // Submit contract offer
  const handleSubmitOffer = () => {
    if (!negotiatingCandidate) return;
    offerMutation.mutate({
      profile_id: negotiatingCandidate.profile_id,
      role: negotiatingCandidate.role_key,
      offered_salary_gtex: offerSalary,
      contract_years: offerYears,
      marquee_wage_premium: marqueePremium,
      pitch_note: pitchNote.trim() || undefined,
    });
  };

  // Dismiss staff confirmation
  const handleConfirmDismiss = () => {
    if (!dismissRoleTarget) return;
    dismissMutation.mutate({
      role: dismissRoleTarget.role_key,
      reason: dismissReason.trim() || undefined,
    });
  };

  // Switch to market for specific vacancy
  const handleFindCandidatesForVacancy = (vac: StaffVacancyItem) => {
    setSelectedRoleFilter(vac.role_key);
    setActiveTab("market");
  };

  // Suitability badge helper
  const renderSuitabilityBadge = (interest: string, canAttract: boolean) => {
    if (!canAttract || interest === "unlikely") {
      return (
        <span className="inline-flex items-center gap-1 rounded border border-rose-500/30 bg-rose-500/10 px-2 py-0.5 text-[10px] font-bold text-rose-300">
          <AlertCircle className="h-3 w-3 text-rose-400" />
          Prestige Mismatch
        </span>
      );
    }
    if (interest === "requires_premium") {
      return (
        <span className="inline-flex items-center gap-1 rounded border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-bold text-amber-300">
          <Sparkles className="h-3 w-3 text-amber-400" />
          Requires Marquee Premium
        </span>
      );
    }
    if (interest === "very_high") {
      return (
        <span className="inline-flex items-center gap-1 rounded border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-emerald-300">
          <CheckCircle2 className="h-3 w-3 text-emerald-400" />
          High Interest
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 rounded border border-sky-500/30 bg-sky-500/10 px-2 py-0.5 text-[10px] font-bold text-sky-300">
        <Users className="h-3 w-3 text-sky-400" />
        Interested
      </span>
    );
  };

  // Filter candidates locally by search text
  const filteredCandidates = (marketData?.candidates || []).filter((c) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      c.name.toLowerCase().includes(q) ||
      c.role_label.toLowerCase().includes(q) ||
      (c.style && c.style.toLowerCase().includes(q)) ||
      (c.temperament && c.temperament.toLowerCase().includes(q)) ||
      (c.skills && c.skills.some((s) => s.toLowerCase().includes(q)))
    );
  });

  const clubPrestige = vacanciesData?.club_prestige || marketData?.club_prestige || 50;

  return (
    <div
      role="dialog"
      aria-modal="true"
      data-testid="staff-employment-modal"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fade-in"
    >
      <div className="relative flex flex-col w-full max-w-5xl max-h-[90vh] rounded-2xl border border-white/10 bg-slate-900/95 shadow-2xl shadow-emerald-950/30 overflow-hidden text-slate-100">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-white/10 px-6 py-4 bg-slate-950/50">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/20 border border-emerald-500/40 text-emerald-400">
              <Briefcase className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold tracking-tight text-white">
                  Executive Career & Employment Market
                </h2>
                <span className="rounded bg-emerald-500/20 px-2 py-0.5 text-[11px] font-mono font-semibold text-emerald-300">
                  Prestige: {clubPrestige}
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Living professional football ecosystem: Scout free agents, ratify contracts & manage executive careers
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Tab switchers */}
            <div className="flex items-center rounded-xl border border-white/10 bg-slate-950/80 p-1">
              <button
                type="button"
                data-testid="tab-vacancies-btn"
                onClick={() => {
                  setActiveTab("vacancies");
                  setNegotiatingCandidate(null);
                }}
                className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
                  activeTab === "vacancies"
                    ? "bg-emerald-500 text-slate-950 shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <Users className="h-3.5 w-3.5" />
                <span>Club Roster & Vacancies</span>
                {vacanciesData && vacanciesData.vacancies_count > 0 && (
                  <span className="rounded-full bg-rose-500/30 border border-rose-500/40 px-1.5 text-[10px] text-rose-200">
                    {vacanciesData.vacancies_count}
                  </span>
                )}
              </button>

              <button
                type="button"
                data-testid="tab-market-btn"
                onClick={() => {
                  setActiveTab("market");
                  setDismissRoleTarget(null);
                }}
                className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
                  activeTab === "market"
                    ? "bg-emerald-500 text-slate-950 shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <UserPlus className="h-3.5 w-3.5" />
                <span>Global Market & Free Agents</span>
              </button>
            </div>

            {/* Close Button */}
            <button
              type="button"
              data-testid="close-staff-modal-btn"
              onClick={onClose}
              className="rounded-xl border border-white/10 p-2 text-slate-400 transition-colors hover:bg-white/10 hover:text-white"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* TAB 1: VACANCIES & FILLED ROLES */}
          {activeTab === "vacancies" && (
            <div className="space-y-6 animate-fade-in" data-testid="vacancies-tab-content">
              {isVacanciesLoading ? (
                <div className="flex h-64 items-center justify-center">
                  <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" />
                </div>
              ) : (
                <>
                  {/* Vacancies Section */}
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4 text-amber-400" />
                        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300">
                          Open Department Vacancies ({vacanciesData?.vacancies_count ?? 0})
                        </h3>
                      </div>
                      <span className="text-xs text-slate-400">
                        Unfilled technical roles reduce department operational efficiency
                      </span>
                    </div>

                    {vacanciesData?.vacancies && vacanciesData.vacancies.length > 0 ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3" data-testid="vacancies-list">
                        {vacanciesData.vacancies.map((vac) => (
                          <div
                            key={vac.role_key}
                            data-testid={`vacancy-card-${vac.role_key}`}
                            className="flex flex-col justify-between rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 transition-all hover:border-amber-500/50"
                          >
                            <div className="flex items-start justify-between">
                              <div>
                                <span className="inline-block rounded bg-amber-500/20 px-2 py-0.5 text-[10px] font-mono font-bold text-amber-300 uppercase">
                                  {vac.is_urgent ? "Critical Vacancy" : "Open Post"}
                                </span>
                                <h4 className="mt-1 text-base font-bold text-white">{vac.role_label}</h4>
                                <p className="text-xs text-slate-400">
                                  Provisional: <span className="italic">{vac.provisional_name}</span>
                                </p>
                              </div>
                              <div className="text-right">
                                <span className="text-[10px] text-slate-400 uppercase block">Min Target</span>
                                <span className="text-sm font-mono font-bold text-amber-300">
                                  {vac.recommended_min_rating}+ OVR
                                </span>
                              </div>
                            </div>

                            <div className="mt-4 pt-3 border-t border-amber-500/20 flex items-center justify-between">
                              <span className="text-xs text-slate-400">Ready to appoint</span>
                              <button
                                type="button"
                                data-testid={`recruit-btn-${vac.role_key}`}
                                onClick={() => handleFindCandidatesForVacancy(vac)}
                                className="flex items-center gap-1 rounded-lg bg-emerald-500 px-3 py-1.5 text-xs font-bold text-slate-950 transition-all hover:bg-emerald-400"
                              >
                                <Search className="h-3 w-3" />
                                <span>Find Candidates</span>
                                <ArrowRight className="h-3 w-3" />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4 text-center">
                        <CheckCircle2 className="mx-auto h-6 w-6 text-emerald-400 mb-1" />
                        <p className="text-sm font-medium text-emerald-300">
                          All executive & technical roles are actively staffed!
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Filled Roles / Incumbent Roster */}
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <Users className="h-4 w-4 text-emerald-400" />
                        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300">
                          Appointed Club Executives & Staff ({vacanciesData?.filled_roles?.length ?? 0})
                        </h3>
                      </div>
                      <span className="text-xs text-slate-400">
                        Owner authority: Retain or dismiss to free agency with severance
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3" data-testid="filled-roles-list">
                      {vacanciesData?.filled_roles?.map((incumbent) => (
                        <div
                          key={incumbent.role_key}
                          data-testid={`filled-role-card-${incumbent.role_key}`}
                          className="flex flex-col justify-between rounded-xl border border-white/10 bg-slate-950/60 p-4 transition-all hover:border-white/20"
                        >
                          <div>
                            <div className="flex items-start justify-between">
                              <div>
                                <span className="inline-block rounded bg-slate-800 px-2 py-0.5 text-[10px] font-mono text-slate-300 uppercase">
                                  {incumbent.role_label}
                                </span>
                                <h4 className="mt-1 text-base font-bold text-white">{incumbent.incumbent_name}</h4>
                              </div>
                              <span className="inline-flex items-center gap-1 rounded bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 text-xs font-mono text-emerald-300">
                                Mood: {incumbent.mood}%
                              </span>
                            </div>

                            <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-400">
                              <div className="flex items-center gap-1">
                                <Coins className="h-3.5 w-3.5 text-amber-400" />
                                <span>Wage: ₦{incumbent.salary_gtex.toLocaleString()} /yr</span>
                              </div>
                              <div className="flex items-center gap-1">
                                <Clock className="h-3.5 w-3.5 text-sky-400" />
                                <span>Active Contract</span>
                              </div>
                            </div>
                          </div>

                          <div className="mt-4 pt-3 border-t border-white/5 flex items-center justify-between">
                            <span className="text-[11px] text-slate-400">
                              Severance: ₦{Math.round(incumbent.salary_gtex * 0.5).toLocaleString()}
                            </span>
                            <button
                              type="button"
                              data-testid={`dismiss-btn-${incumbent.role_key}`}
                              onClick={() => setDismissRoleTarget(incumbent)}
                              className="flex items-center gap-1 rounded-lg border border-rose-500/30 bg-rose-500/10 px-2.5 py-1 text-xs font-medium text-rose-300 transition-all hover:bg-rose-500/20 hover:border-rose-500/50"
                            >
                              <UserMinus className="h-3.5 w-3.5" />
                              <span>Dismiss</span>
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Inline Dismissal Confirmation Modal / Card */}
                  {dismissRoleTarget && (
                    <div
                      data-testid="dismissal-confirmation-dialog"
                      className="rounded-2xl border border-rose-500/40 bg-rose-950/30 p-5 backdrop-blur-md animate-fade-in"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2">
                          <AlertTriangle className="h-5 w-5 text-rose-400" />
                          <h4 className="text-base font-bold text-rose-200">
                            Confirm Termination & Free Agency Release
                          </h4>
                        </div>
                        <button
                          type="button"
                          onClick={() => setDismissRoleTarget(null)}
                          className="text-slate-400 hover:text-white"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>

                      <p className="mt-2 text-xs text-slate-300 leading-relaxed">
                        You are about to dismiss{" "}
                        <strong className="text-white">{dismissRoleTarget.incumbent_name}</strong> from the role of{" "}
                        <strong className="text-white">{dismissRoleTarget.role_label}</strong>. A mandatory 50%
                        severance fee of{" "}
                        <span className="font-mono font-bold text-amber-300">
                          ₦{Math.round(dismissRoleTarget.salary_gtex * 0.5).toLocaleString()} GTEX
                        </span>{" "}
                        will be settled immediately from the club treasury. They will enter the Global Free Agent pool
                        and can be recruited by other clubs.
                      </p>

                      <div className="mt-3">
                        <label className="text-[11px] font-semibold text-slate-400 uppercase">
                          Executive Exit Note (Optional)
                        </label>
                        <input
                          type="text"
                          data-testid="dismiss-reason-input"
                          value={dismissReason}
                          onChange={(e) => setDismissReason(e.target.value)}
                          placeholder="e.g. Philosophical divergence, tactical rebuild, poor youth promotion..."
                          className="mt-1 w-full rounded-xl border border-white/10 bg-slate-950 px-3 py-2 text-xs text-white placeholder-slate-500 focus:border-rose-500 focus:outline-none"
                        />
                      </div>

                      <div className="mt-4 flex items-center justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => setDismissRoleTarget(null)}
                          className="rounded-lg px-3 py-1.5 text-xs text-slate-400 hover:text-white"
                        >
                          Cancel
                        </button>
                        <button
                          type="button"
                          data-testid="confirm-dismiss-btn"
                          disabled={dismissMutation.isPending}
                          onClick={handleConfirmDismiss}
                          className="flex items-center gap-1.5 rounded-lg bg-rose-600 px-4 py-1.5 text-xs font-bold text-white transition-all hover:bg-rose-500 disabled:opacity-50"
                        >
                          {dismissMutation.isPending ? "Ratifying Dismissal..." : "Ratify Dismissal"}
                        </button>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* TAB 2: GLOBAL MARKET & CANDIDATES */}
          {activeTab === "market" && (
            <div className="space-y-6 animate-fade-in" data-testid="market-tab-content">
              {/* Filter & Search Bar */}
              <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/10 bg-slate-950/60 p-3">
                <div className="flex flex-wrap items-center gap-2">
                  {/* Role Filter Selector */}
                  <div className="flex items-center gap-1">
                    <span className="text-[11px] font-semibold text-slate-400 uppercase">Role:</span>
                    <select
                      data-testid="role-filter-select"
                      value={selectedRoleFilter}
                      onChange={(e) => setSelectedRoleFilter(e.target.value)}
                      className="rounded-lg border border-white/10 bg-slate-900 px-2.5 py-1 text-xs text-slate-200 focus:border-emerald-500 focus:outline-none"
                    >
                      {ROLE_OPTIONS.map((opt) => (
                        <option key={opt.key} value={opt.key}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Free Agent Only Toggle */}
                  <button
                    type="button"
                    data-testid="toggle-free-agents-btn"
                    onClick={() => setFreeAgentsOnly((prev) => !prev)}
                    className={`flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-medium border transition-all ${
                      freeAgentsOnly
                        ? "border-emerald-500/50 bg-emerald-500/20 text-emerald-300"
                        : "border-white/10 bg-slate-900 text-slate-400 hover:text-white"
                    }`}
                  >
                    <span>Free Agents Only</span>
                  </button>
                </div>

                {/* Search query */}
                <div className="relative min-w-[220px]">
                  <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
                  <input
                    type="text"
                    data-testid="market-search-input"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search name, tactical style, skills..."
                    className="w-full rounded-lg border border-white/10 bg-slate-900 pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:border-emerald-500 focus:outline-none"
                  />
                </div>
              </div>

              {/* Candidates Grid */}
              {isMarketLoading ? (
                <div className="flex h-64 items-center justify-center">
                  <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" />
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4" data-testid="candidates-grid">
                  {filteredCandidates.map((cand) => {
                    const isNegotiating = negotiatingCandidate?.profile_id === cand.profile_id;
                    const isExpanded = expandedCandidateId === cand.profile_id;

                    return (
                      <div
                        key={cand.profile_id}
                        data-testid={`candidate-card-${cand.profile_id}`}
                        className={`flex flex-col justify-between rounded-xl border p-4 transition-all ${
                          isNegotiating
                            ? "border-emerald-500 bg-emerald-950/20 shadow-lg shadow-emerald-950/50"
                            : "border-white/10 bg-slate-950/60 hover:border-white/20"
                        }`}
                      >
                        <div>
                          {/* Card Top: Name, Role, Rating */}
                          <div className="flex items-start justify-between">
                            <div>
                              <div className="flex items-center gap-1.5 flex-wrap">
                                <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] font-mono text-slate-300 uppercase">
                                  {cand.role_label}
                                </span>
                                <span className="rounded bg-sky-500/10 border border-sky-500/20 px-1.5 py-0.5 text-[10px] font-mono text-sky-300 uppercase">
                                  {cand.rarity}
                                </span>
                                {cand.employment_status === "unemployed" ? (
                                  <span className="rounded bg-emerald-500/10 border border-emerald-500/20 px-1.5 py-0.5 text-[10px] font-mono text-emerald-300">
                                    Free Agent
                                  </span>
                                ) : (
                                  <span className="rounded bg-slate-700 px-1.5 py-0.5 text-[10px] font-mono text-slate-300">
                                    Employed
                                  </span>
                                )}
                              </div>
                              <h4 className="mt-1.5 text-base font-bold text-white">{cand.name}</h4>
                              <p className="text-xs text-slate-400">
                                {cand.style || "Standard"} • {cand.temperament || "Balanced"}
                              </p>
                            </div>

                            <div className="flex flex-col items-end">
                              <div className="flex items-center gap-1">
                                <Award className="h-4 w-4 text-amber-400" />
                                <span className="text-lg font-mono font-bold text-white">{cand.rating}</span>
                              </div>
                              <span className="text-[10px] text-slate-400">Rep: {cand.reputation}/100</span>
                            </div>
                          </div>

                          {/* Attribute Indicators & Expected Salary */}
                          <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                            <div className="rounded-lg bg-slate-900/80 p-2 border border-white/5">
                              <span className="text-[10px] text-slate-400 uppercase block">Expected Wage</span>
                              <span className="font-mono font-bold text-amber-300">
                                ₦{cand.expected_salary_gtex.toLocaleString()} GTEX
                              </span>
                            </div>
                            <div className="rounded-lg bg-slate-900/80 p-2 border border-white/5">
                              <span className="text-[10px] text-slate-400 uppercase block">Ambition & Loyalty</span>
                              <span className="font-mono text-slate-300">
                                Amb: {cand.ambition} | Loy: {cand.loyalty}
                              </span>
                            </div>
                          </div>

                          {/* Suitability Badge */}
                          <div className="mt-3 flex items-center justify-between">
                            {renderSuitabilityBadge(cand.interest_level, cand.can_attract)}
                            <button
                              type="button"
                              data-testid={`toggle-history-btn-${cand.profile_id}`}
                              onClick={() =>
                                setExpandedCandidateId((prev) =>
                                  prev === cand.profile_id ? null : cand.profile_id
                                )
                              }
                              className="flex items-center gap-1 text-[11px] text-slate-400 hover:text-white"
                            >
                              <History className="h-3 w-3" />
                              <span>Career History ({cand.career_history?.length ?? 0})</span>
                              {isExpanded ? (
                                <ChevronUp className="h-3 w-3" />
                              ) : (
                                <ChevronDown className="h-3 w-3" />
                              )}
                            </button>
                          </div>

                          {/* Expanded Career History */}
                          {isExpanded && (
                            <div
                              data-testid={`candidate-history-drawer-${cand.profile_id}`}
                              className="mt-3 rounded-lg border border-white/10 bg-slate-900/90 p-3 space-y-2 text-xs"
                            >
                              <div className="flex items-center justify-between font-semibold text-slate-300 border-b border-white/5 pb-1">
                                <span>Past Tenures</span>
                                <span>Record</span>
                              </div>
                              {cand.career_history && cand.career_history.length > 0 ? (
                                cand.career_history.map((hist, idx) => (
                                  <div
                                    key={idx}
                                    className="flex items-center justify-between py-1 border-b border-white/5 last:border-0"
                                  >
                                    <div>
                                      <span className="font-bold text-white">{hist.club_name}</span>
                                      <span className="text-[10px] text-slate-400 ml-1.5">
                                        ({hist.tenure_years ?? hist.contract_years ?? 1} yrs - {hist.exit_reason || hist.reason_for_leaving || "Departed"})
                                      </span>
                                    </div>
                                    <div className="font-mono text-[11px] text-slate-300">
                                      {hist.win_rate_pct ?? hist.win_rate ?? 0}% win ({hist.matches_managed ?? 0} matches)
                                    </div>
                                  </div>
                                ))
                              ) : (
                                <p className="text-slate-500 italic text-[11px]">No prior recorded club tenures</p>
                              )}
                            </div>
                          )}
                        </div>

                        {/* Negotiation / Action Trigger */}
                        <div className="mt-4 pt-3 border-t border-white/5 flex items-center justify-between">
                          <span className="text-[11px] text-slate-400">
                            Min Club Prestige: {cand.min_prestige}
                          </span>
                          <button
                            type="button"
                            data-testid={`negotiate-offer-btn-${cand.profile_id}`}
                            onClick={() => handleOpenNegotiation(cand)}
                            className="flex items-center gap-1 rounded-lg bg-emerald-500 px-3 py-1.5 text-xs font-bold text-slate-950 transition-all hover:bg-emerald-400"
                          >
                            <Coins className="h-3.5 w-3.5" />
                            <span>Make Offer</span>
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* NEGOTIATION / FORMAL CONTRACT OFFER SHEET */}
              {negotiatingCandidate && (
                <div
                  data-testid="contract-negotiation-sheet"
                  className="rounded-2xl border border-emerald-500/40 bg-slate-950/90 p-6 shadow-2xl backdrop-blur-md animate-fade-in space-y-4"
                >
                  <div className="flex items-start justify-between border-b border-white/10 pb-3">
                    <div>
                      <span className="text-[10px] font-mono uppercase text-emerald-400">Formal Contract Ratification</span>
                      <h3 className="text-lg font-bold text-white">
                        Negotiating Terms with {negotiatingCandidate.name}
                      </h3>
                      <p className="text-xs text-slate-400">
                        Target Role: <strong className="text-white">{negotiatingCandidate.role_label}</strong> •
                        Baseline Wage: ₦{negotiatingCandidate.expected_salary_gtex.toLocaleString()} GTEX
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setNegotiatingCandidate(null)}
                      className="text-slate-400 hover:text-white"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>

                  {/* Form fields */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* Annual Salary */}
                    <div>
                      <label className="text-xs font-semibold text-slate-300">Annual Wage (GTEX)</label>
                      <input
                        type="number"
                        data-testid="offer-salary-input"
                        value={offerSalary}
                        onChange={(e) => setOfferSalary(Number(e.target.value))}
                        className="mt-1 w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-sm font-mono text-white focus:border-emerald-500 focus:outline-none"
                      />
                      <span className="text-[10px] text-slate-400 mt-1 block">
                        Expected: ₦{negotiatingCandidate.expected_salary_gtex.toLocaleString()}
                      </span>
                    </div>

                    {/* Contract Length */}
                    <div>
                      <label className="text-xs font-semibold text-slate-300">Contract Length (Years)</label>
                      <select
                        data-testid="offer-years-select"
                        value={offerYears}
                        onChange={(e) => setOfferYears(Number(e.target.value))}
                        className="mt-1 w-full rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-sm font-mono text-white focus:border-emerald-500 focus:outline-none"
                      >
                        <option value={1}>1 Year (Short-term)</option>
                        <option value={2}>2 Years (Standard)</option>
                        <option value={3}>3 Years (Long-term)</option>
                        <option value={4}>4 Years (Executive Project)</option>
                        <option value={5}>5 Years (Dynasty Building)</option>
                      </select>
                    </div>

                    {/* Upfront Signing Fee Preview */}
                    <div>
                      <label className="text-xs font-semibold text-slate-300">Upfront Signing Fee (15%)</label>
                      <div className="mt-1 flex items-center justify-between rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-sm font-mono text-amber-300">
                        <span>₦{Math.round(offerSalary * 0.15).toLocaleString()} GTEX</span>
                        <Coins className="h-4 w-4 text-amber-400" />
                      </div>
                      <span className="text-[10px] text-slate-400 mt-1 block">
                        Settled from treasury immediately upon signing
                      </span>
                    </div>
                  </div>

                  {/* Marquee Wage Premium Toggle */}
                  <div className="flex items-center justify-between rounded-xl border border-amber-500/20 bg-amber-500/5 p-3">
                    <div className="flex items-center gap-2">
                      <Sparkles className="h-4 w-4 text-amber-400" />
                      <div>
                        <span className="text-xs font-bold text-amber-200 block">
                          Apply Marquee Wage Premium (+25% Signing Package)
                        </span>
                        <span className="text-[11px] text-slate-400">
                          Overcomes lower club prestige thresholds for elite ambitious candidates
                        </span>
                      </div>
                    </div>
                    <input
                      type="checkbox"
                      data-testid="offer-marquee-premium-toggle"
                      checked={marqueePremium}
                      onChange={(e) => setMarqueePremium(e.target.checked)}
                      className="h-4 w-4 rounded border-amber-500/40 text-emerald-500 focus:ring-0"
                    />
                  </div>

                  {/* Pitch Note */}
                  <div>
                    <label className="text-xs font-semibold text-slate-300">
                      Owner Pitch Note to Candidate (Optional)
                    </label>
                    <textarea
                      data-testid="offer-pitch-note-input"
                      rows={2}
                      value={pitchNote}
                      onChange={(e) => setPitchNote(e.target.value)}
                      placeholder="e.g. Full tactical autonomy, modernized sports science facilities, continental ambition..."
                      className="mt-1 w-full rounded-xl border border-white/10 bg-slate-900 p-2.5 text-xs text-white placeholder-slate-500 focus:border-emerald-500 focus:outline-none"
                    />
                  </div>

                  {/* Negotiation Result Banner */}
                  {lastOfferResult && (
                    <div
                      data-testid="offer-result-banner"
                      className={`rounded-xl border p-3 text-xs ${
                        lastOfferResult.success && lastOfferResult.status === "accepted"
                          ? "border-emerald-500/40 bg-emerald-950/30 text-emerald-200"
                          : "border-rose-500/40 bg-rose-950/30 text-rose-200"
                      }`}
                    >
                      <p className="font-bold">{lastOfferResult.message}</p>
                      {lastOfferResult.reason && (
                        <p className="mt-1 text-[11px] opacity-80">Reason: {lastOfferResult.reason}</p>
                      )}
                      {lastOfferResult.counter_salary_gtex && (
                        <p className="mt-1 text-[11px] font-mono text-amber-300">
                          Candidate Counter-Demand: ₦{lastOfferResult.counter_salary_gtex.toLocaleString()} GTEX
                        </p>
                      )}
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex items-center justify-end gap-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setNegotiatingCandidate(null)}
                      className="rounded-lg px-4 py-2 text-xs text-slate-400 hover:text-white"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      data-testid="submit-contract-offer-btn"
                      disabled={offerMutation.isPending}
                      onClick={handleSubmitOffer}
                      className="flex items-center gap-1.5 rounded-lg bg-emerald-500 px-5 py-2 text-xs font-bold text-slate-950 transition-all hover:bg-emerald-400 disabled:opacity-50"
                    >
                      {offerMutation.isPending ? "Ratifying Contract..." : "Ratify Contract & Hire"}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
