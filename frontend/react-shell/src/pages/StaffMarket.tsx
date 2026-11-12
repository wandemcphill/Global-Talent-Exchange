import React, { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { useActiveClub } from "@/lib/owner";
import { clubStaffMarketCandidatesEndpoint } from "@/lib/ownerBriefing";
import { Btn, Empty, Loading, PageHeader } from "@/components/gtex/ui";

const ROLES = [
  { id: "all", label: "All staff" },
  { id: "first_team_manager", label: "First-team manager" },
  { id: "general_manager", label: "General manager" },
  { id: "head_of_youth_development", label: "Head of youth" },
  { id: "chief_scout", label: "Chief scout" },
  { id: "medical_director", label: "Physio and medical lead" },
];

export default function StaffMarket() {
  const { active } = useActiveClub();
  const clubId = active?.club_id;
  const queryClient = useQueryClient();
  const [role, setRole] = useState("all");
  const [wageMax, setWageMax] = useState("");
  const [style, setStyle] = useState("");
  const [temperament, setTemperament] = useState("");
  const [search, setSearch] = useState("");
  const [offerFor, setOfferFor] = useState<string | null>(null);
  const [salary, setSalary] = useState("");
  const [years, setYears] = useState("3");

  const query = useQuery({
    queryKey: ["staff-market", clubId, role, wageMax, style, temperament, search],
    enabled: Boolean(clubId),
    queryFn: async () => {
      const { data } = await api.get(
        clubStaffMarketCandidatesEndpoint(clubId, role, "unemployed", 40, {
          wageMax,
          style,
          temperament,
          search,
        }),
      );
      return data;
    },
  });

  const hire = async (candidate: any) => {
    if (!clubId) return;
    try {
      await api.post(`/owner/clubs/${clubId}/living-world/staff-market/offers`, {
        profile_id: candidate.profile_id,
        role: candidate.role_key,
        offered_salary_gtex: Number(salary || candidate.expected_salary_gtex || 600),
        contract_years: Number(years || 3),
      });
      toast.success(`Offer sent to ${candidate.name}.`);
      setOfferFor(null);
      queryClient.invalidateQueries({ queryKey: ["staff-market", clubId] });
    } catch (error) {
      toast.error(errMsg(error));
    }
  };

  if (!clubId) {
    return (
      <div className="mx-auto max-w-lg p-8 text-center">
        <h1 className="text-2xl font-black text-white">Staff market</h1>
        <p className="mt-2 text-sm text-slate-400">Open a club before you hire a manager, general manager, or physio.</p>
        <Link to="/app/clubs" className="gx-btn gx-btn-primary mt-4 inline-flex">My clubs</Link>
      </div>
    );
  }

  const candidates = query.data?.candidates || [];
  const supply = query.data?.supply;

  return (
    <div className="space-y-5 p-4 md:p-6" data-testid="staff-market-page">
      <PageHeader
        eyebrow="Club staff"
        title="Staff market"
        sub="Filter by wage, style, and temperament. Each general manager works for one club. The free bench refills to 160, and the top wage band stays small."
      />
      <div className="grid gap-3 md:grid-cols-5">
        <select className="gx-input" value={role} onChange={(event) => setRole(event.target.value)} data-testid="staff-role-filter">
          {ROLES.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
        </select>
        <input className="gx-input" placeholder="Max wage" type="number" min="0" value={wageMax} onChange={(event) => setWageMax(event.target.value)} />
        <input className="gx-input" placeholder="Tactical style" value={style} onChange={(event) => setStyle(event.target.value)} />
        <input className="gx-input" placeholder="Temperament" value={temperament} onChange={(event) => setTemperament(event.target.value)} />
        <input className="gx-input" placeholder="Search name" value={search} onChange={(event) => setSearch(event.target.value)} />
      </div>
      <p className="text-xs text-slate-400" data-testid="staff-supply-note">
        {query.data?.total_count ?? 0} people match.
        {supply
          ? ` ${supply.general_manager_available} general managers are free to hire. When that number falls under ${supply.general_manager_floor}, new directors enter across foundation, established, and elite wages.`
          : " Physio is the medical seat."}
      </p>
      {query.isLoading ? <Loading label="Opening the staff market..." /> : null}
      {query.isError ? <Empty title="Staff market unavailable" body={errMsg(query.error)} /> : null}
      {!query.isLoading && candidates.length === 0 ? <Empty title="No staff match" body="Widen the wage, style, or temperament filter." /> : null}
      <div className="grid gap-3">
        {candidates.map((candidate: any) => (
          <article key={candidate.profile_id} className="rounded-xl border border-white/10 bg-slate-950/70 p-4" data-testid={`staff-candidate-${candidate.profile_id}`}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                {candidate.portrait_url ? (
                  <img src={candidate.portrait_url} alt="" className="h-14 w-14 rounded-full object-cover bg-slate-800" />
                ) : null}
                <div>
                <h2 className="text-lg font-black text-white">{candidate.name}</h2>
                <p className="text-xs text-slate-400">{candidate.role_label} · rating {candidate.rating} · {candidate.style} · {candidate.temperament}</p>
                <p className="mt-1 text-sm text-amber-200">Expected wage {Number(candidate.expected_salary_gtex || 0).toLocaleString()} GTX</p>
                </div>
              </div>
              <Btn type="button" onClick={() => { setOfferFor(candidate.profile_id); setSalary(String(candidate.expected_salary_gtex || "")); }}>
                Hire
              </Btn>
            </div>
            {offerFor === candidate.profile_id && (
              <div className="mt-3 flex flex-wrap items-end gap-2">
                <input className="gx-input w-36" type="number" min="100" value={salary} onChange={(event) => setSalary(event.target.value)} />
                <select className="gx-input w-28" value={years} onChange={(event) => setYears(event.target.value)}>
                  {[1, 2, 3, 4, 5].map((year) => <option key={year} value={year}>{year} years</option>)}
                </select>
                <Btn type="button" onClick={() => hire(candidate)}>Send offer</Btn>
              </div>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}
