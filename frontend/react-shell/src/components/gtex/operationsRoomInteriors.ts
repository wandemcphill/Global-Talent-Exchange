import * as THREE from "three";
import type { ClubOperationsHubPayload, OperationsHubDestination } from "@/lib/ownerBriefing";

export interface LiveScreenMetricRow {
  label: string;
  value: string;
  tone?: "accent" | "positive" | "warning" | "muted";
}

export interface LiveScreenSnapshot {
  header: string;
  title: string;
  subtitle: string;
  accent: string;
  rows: LiveScreenMetricRow[];
  footer: string;
  dataAvailable: boolean;
}

export interface DepartmentScreenHandle {
  id: string;
  kind: "banner" | "telemetry" | "terminal";
  destinationKey: string;
  hotspotId?: string;
  hotspotLabel?: string;
  hotspotAction?: string;
  accent: string;
  mesh: THREE.Mesh;
  canvas: HTMLCanvasElement;
  texture: THREE.CanvasTexture;
  snapshot: LiveScreenSnapshot;
  lastSignature: string;
}

export interface DepartmentInteriorBuild {
  group: THREE.Group;
  pickables: THREE.Object3D[];
  animatedActors: THREE.Group[];
  screens: DepartmentScreenHandle[];
}

type Hotspot = OperationsHubDestination["hotspots"][number];

const ROOM_WIDTH = 10.5;
const ROOM_DEPTH = 8.5;
const WALL_HEIGHT = 4.25;

function accentCssColor(accent: THREE.ColorRepresentation): string {
  return typeof accent === "string" ? accent : `#${new THREE.Color(accent).getHexString()}`;
}

function standardMaterial(
  color: THREE.ColorRepresentation,
  roughness = 0.68,
  metalness = 0.08,
): THREE.MeshStandardMaterial {
  return new THREE.MeshStandardMaterial({ color, roughness, metalness });
}

function addBox(
  root: THREE.Group,
  size: [number, number, number],
  position: [number, number, number],
  material: THREE.Material,
  rotationY = 0,
): THREE.Mesh {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(...size), material);
  mesh.position.set(...position);
  mesh.rotation.y = rotationY;
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  root.add(mesh);
  return mesh;
}

function addCylinder(
  root: THREE.Group,
  radiusTop: number,
  radiusBottom: number,
  height: number,
  position: [number, number, number],
  material: THREE.Material,
  radialSegments = 20,
): THREE.Mesh {
  const mesh = new THREE.Mesh(
    new THREE.CylinderGeometry(radiusTop, radiusBottom, height, radialSegments),
    material,
  );
  mesh.position.set(...position);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  root.add(mesh);
  return mesh;
}

function formatGtex(value: unknown): string {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? `${Math.round(numeric).toLocaleString()} GTX` : "DATA UNAVAILABLE";
}

function formatUpperToken(value: unknown): string {
  if (!value) return "DATA UNAVAILABLE";
  return String(value).replace(/_/g, " ").toUpperCase();
}

function rowValueColor(tone: LiveScreenMetricRow["tone"], accent: string): string {
  switch (tone) {
    case "positive":
      return "#34d399";
    case "warning":
      return "#fbbf24";
    case "muted":
      return "#94a3b8";
    case "accent":
    default:
      return accent;
  }
}

export function buildDestinationScreenSnapshot(
  destination: OperationsHubDestination,
  kind: "banner" | "telemetry" | "terminal",
  hub?: ClubOperationsHubPayload | null,
  hotspot?: Hotspot,
): LiveScreenSnapshot {
  const accent = accentCssColor(destination.accent_color || "#38bdf8");
  const report = (destination.report || {}) as Record<string, any>;
  const hasHub = Boolean(hub?.club);
  const hasReport = Boolean(destination.report && Object.keys(destination.report).length > 0);
  const worldDay = hub?.club?.world_day;

  if (kind === "banner") {
    const lead = destination.staff_lead;
    const subtitle = lead?.is_vacant
      ? "SEAT VACANT  •  RECRUITMENT OPEN"
      : lead?.name
        ? `${lead.name}  •  ${lead.role_label || destination.short_label}`
        : destination.subtitle || destination.short_label;
    return {
      header: worldDay != null ? `GTEX  /  WORLD DAY ${worldDay}` : "GTEX  /  CLUB OPERATIONS",
      title: destination.label,
      subtitle,
      accent,
      rows: [
        {
          label: "OPEN DECISIONS",
          value: String(destination.open_decisions_count ?? 0),
          tone: (destination.open_decisions_count ?? 0) > 0 ? "warning" : "positive",
        },
        {
          label: "ACTIVE EVENTS",
          value: String(destination.active_events_count ?? 0),
          tone: "accent",
        },
      ],
      footer:
        destination.communication_channel_mode === "vacant"
          ? "CHANNEL VACANT  •  RECRUIT STAFF TO UNLOCK DIRECT COMMS"
          : "LIVE HEADQUARTERS  •  SELECT STATIONS TO OPERATE",
      dataAvailable: hasHub || hasReport || Boolean(lead),
    };
  }

  if (!hasHub && !hasReport) {
    const unavailableTitle = hotspot ? hotspot.label : `${destination.short_label} Live Feed`;
    return {
      header: "GTEX  /  LIVE TELEMETRY",
      title: unavailableTitle,
      subtitle: hotspot
        ? `Station action: ${hotspot.action.replace(/_/g, " ")}`
        : "Authoritative metrics unavailable",
      accent,
      rows: [
        { label: "TELEMETRY STATUS", value: "DATA UNAVAILABLE", tone: "warning" },
        { label: "BACKEND SYNC", value: "AWAITING AUTHORITATIVE HUB", tone: "muted" },
      ],
      footer: "ZERO FABRICATED FIGURES  •  CONNECT LIVE HUB",
      dataAvailable: false,
    };
  }

  if (kind === "terminal" && hotspot) {
    const auth = destination.tactical_authority || hub?.club?.manager_tactical_authority;
    const terminalRows: LiveScreenMetricRow[] = (() => {
      if (hotspot.action.startsWith("chat_")) {
        const vacant = destination.staff_lead?.is_vacant || destination.communication_channel_mode === "vacant";
        return [
          {
            label: "CHANNEL STATUS",
            value: vacant ? "VACANT  •  RECRUIT FIRST" : `${destination.staff_lead?.name || "DIRECT"} LIVE`,
            tone: vacant ? "warning" : "positive",
          },
          {
            label: "MESSAGES",
            value: `${destination.recent_messages?.length ?? 0} RECORDED`,
            tone: "accent",
          },
        ];
      }
      switch (hotspot.action) {
        case "inspect_briefing":
        case "briefing":
          return [
            { label: "TREASURY", value: formatGtex(hub?.club?.cash_gtex ?? report?.financial_position?.cash_gtex), tone: "positive" },
            { label: "WORLD DAY", value: worldDay != null ? `DAY ${worldDay}` : "DATA UNAVAILABLE", tone: "accent" },
          ];
        case "inspect_decisions":
        case "decisions":
          return [
            { label: "OPEN DECISIONS", value: String(hub?.actionable_decisions?.total_open_count ?? destination.open_decisions_count ?? 0), tone: "warning" },
            { label: "DILEMMA", value: hub?.actionable_decisions?.boardroom_dilemma ? "AWAITING VOTE" : "CLEAR", tone: hub?.actionable_decisions?.boardroom_dilemma ? "warning" : "positive" },
          ];
        case "inspect_timeline":
          return [
            { label: "TIMELINE LOGS", value: `${hub?.operational_timeline?.length ?? 0} ENTRIES`, tone: "accent" },
            { label: "EVENTS", value: `${destination.active_events_count ?? 0} ACTIVE`, tone: "muted" },
          ];
        case "set_mentality":
        case "mentality":
          return [
            { label: "OWNER REQUEST", value: formatUpperToken(auth?.owner_requested_mentality ?? hub?.club?.owner_requested_mentality ?? hub?.club?.mentality), tone: "muted" },
            { label: "EFFECTIVE XI", value: formatUpperToken(auth?.effective_mentality ?? hub?.club?.effective_matchday_mentality ?? hub?.club?.mentality), tone: auth?.decision_status === "rejected" ? "warning" : "positive" },
          ];
        case "squad_morale": {
          const morale = report?.player_morale;
          const fit = report?.fitness_and_selection;
          return [
            { label: "AVG MORALE", value: morale?.avg_morale != null ? `${morale.avg_morale}%` : "DATA UNAVAILABLE", tone: "accent" },
            { label: "FIT PLAYERS", value: fit?.available_count != null ? `${fit.available_count} READY` : "DATA UNAVAILABLE", tone: "positive" },
          ];
        }
        case "pledge_win_bonus":
        case "match_prep": {
          const prep = report?.upcoming_match_preparation;
          return [
            { label: "WIN BONUS", value: prep?.pledged_win_bonus_gtex != null ? formatGtex(prep.pledged_win_bonus_gtex) : "DATA UNAVAILABLE", tone: "accent" },
            { label: "HOME BONUS", value: prep?.home_advantage_bonus != null ? `+${prep.home_advantage_bonus}` : "DATA UNAVAILABLE", tone: "positive" },
          ];
        }
        case "configure_delegation":
        case "delegation":
          return [
            { label: "POLICY MODE", value: formatUpperToken(report?.administrative_matters?.delegation_policy?.mode), tone: "accent" },
            { label: "STAFF CHANNELS", value: `${destination.open_decisions_count ?? 0} OPEN ITEMS`, tone: "muted" },
          ];
        case "inspect_campus":
        case "campus": {
          const ops = report?.club_operations;
          return [
            { label: "LIVE MODULES", value: ops?.operational_modules_count != null ? String(ops.operational_modules_count) : "DATA UNAVAILABLE", tone: "positive" },
            { label: "IN PROGRESS", value: Array.isArray(ops?.active_construction_projects) ? `${ops.active_construction_projects.length} BUILDS` : "DATA UNAVAILABLE", tone: "warning" },
          ];
        }
        case "staff": {
          const team = report?.staff_and_organisation?.executive_team;
          const appointed = Array.isArray(team) ? team.filter((m: { is_vacant?: boolean }) => !m?.is_vacant).length : null;
          return [
            { label: "ROSTER FILLED", value: appointed != null ? `${appointed}/${team.length} ROLES` : "DATA UNAVAILABLE", tone: "accent" },
            { label: "DIRECTIVES", value: `${destination.active_directives_count ?? 0} ISSUED`, tone: "positive" },
          ];
        }
        case "commission_intake":
        case "intake": {
          const intake = report?.intake_recommendations;
          return [
            { label: "NEXT COHORT", value: intake?.projected_cohort_size != null ? `${intake.projected_cohort_size} PROSPECTS` : "DATA UNAVAILABLE", tone: "positive" },
            { label: "INTAKE COST", value: formatGtex(intake?.next_intake_cost_gtex), tone: "accent" },
          ];
        }
        case "manage_regens":
        case "prospects":
        case "contracts": {
          const acad = report?.academy_development;
          return [
            { label: "REGEN POOL", value: acad?.regen_count != null ? `${acad.regen_count} TALENTS` : "DATA UNAVAILABLE", tone: "accent" },
            { label: "SENIOR READY", value: acad?.ready_for_senior_count != null ? `${acad.ready_for_senior_count} READY` : "DATA UNAVAILABLE", tone: "positive" },
          ];
        }
        case "run_conditioning":
        case "injuries":
        case "rehab": {
          const rehab = report?.rehabilitation_status;
          return [
            { label: "INJURED / REHAB", value: rehab?.active_rehab_count != null ? `${rehab.active_rehab_count} IN REHAB` : "DATA UNAVAILABLE", tone: (rehab?.active_rehab_count ?? 0) > 0 ? "warning" : "positive" },
            { label: "HYDRO & CRYO", value: rehab ? (rehab.protocol_executed_today ? "ACTIVE TODAY" : `STANDBY (${rehab.protocol_cost_gtex ?? 800} GTX)`) : "DATA UNAVAILABLE", tone: rehab?.protocol_executed_today ? "positive" : "accent" },
          ];
        }
        case "inspect_workloads":
        case "fitness": {
          const fitC = report?.squad_fitness_concerns;
          return [
            { label: "AVG FITNESS", value: fitC?.avg_squad_fitness != null ? `${fitC.avg_squad_fitness}%` : "DATA UNAVAILABLE", tone: "positive" },
            { label: "WATCHLIST", value: fitC?.below_85_fitness_count != null ? `${fitC.below_85_fitness_count} <85% FIT` : "DATA UNAVAILABLE", tone: (fitC?.below_85_fitness_count ?? 0) > 0 ? "warning" : "accent" },
          ];
        }
        case "inspect_ledger":
        case "ledger": {
          const bal = report?.balances;
          return [
            { label: "CASH BALANCE", value: formatGtex(bal?.cash_gtex ?? hub?.club?.cash_gtex), tone: "positive" },
            { label: "NET CASHFLOW", value: report?.recent_income_and_expenditure?.net_cashflow_gtex != null ? formatGtex(report.recent_income_and_expenditure.net_cashflow_gtex) : "DATA UNAVAILABLE", tone: "accent" },
          ];
        }
        case "sign_sponsor":
        case "sponsors": {
          const sponsors = report?.sponsor_income;
          return [
            { label: "ACTIVE DEALS", value: Array.isArray(sponsors?.active_deals) ? String(sponsors.active_deals.length) : "DATA UNAVAILABLE", tone: "positive" },
            { label: "OPEN OFFERS", value: Array.isArray(sponsors?.available_offers) ? `${sponsors.available_offers.length} OFFERS` : "DATA UNAVAILABLE", tone: "accent" },
          ];
        }
        case "inspect_matchday_econ":
        case "matchday": {
          const md = report?.matchday_revenue;
          return [
            { label: "CAPACITY", value: md?.stadium_capacity != null ? Number(md.stadium_capacity).toLocaleString() : "DATA UNAVAILABLE", tone: "accent" },
            { label: "PROJECTED GATE", value: formatGtex(md?.projected_next_home_gate_gtex), tone: "positive" },
          ];
        }
        default:
          return [
            { label: "STATION", value: hotspot.label.toUpperCase(), tone: "accent" },
            { label: "OPEN ITEMS", value: String(destination.open_decisions_count ?? 0), tone: "muted" },
          ];
      }
    })();

    return {
      header: `${destination.short_label.toUpperCase()}  /  STATION`,
      title: hotspot.label,
      subtitle: `Operation: ${hotspot.action.replace(/_/g, " ")}`,
      accent,
      rows: terminalRows,
      footer: "CLICK TERMINAL TO OPEN WORKSPACE",
      dataAvailable: true,
    };
  }

  switch (destination.destination_key) {
    case "executive_office": {
      const execBrief = report?.section_key === "executive_briefing" ? report : hub?.daily_briefing?.executive_briefing || report;
      const fin = execBrief?.financial_position;
      const sq = execBrief?.squad_condition_and_availability;
      const risks = execBrief?.urgent_risks;
      const cash = fin?.cash_gtex ?? hub?.club?.cash_gtex;
      const openTotal = hub?.actionable_decisions?.total_open_count ?? execBrief?.outstanding_decisions_count ?? destination.open_decisions_count;
      return {
        header: worldDay != null ? `BOARDROOM  /  WORLD DAY ${worldDay}` : "BOARDROOM  /  EXECUTIVE BRIEF",
        title: `${hub?.club?.club_name || "Club"} Command`,
        subtitle: hub?.daily_briefing?.headline || "Executive overview, treasury & urgent risks",
        accent,
        rows: [
          { label: "CLUB TREASURY", value: cash != null ? formatGtex(cash) : "DATA UNAVAILABLE", tone: "positive" },
          {
            label: "SQUAD STATUS",
            value: sq ? `${sq.available_players}/${sq.squad_size} FIT · ${sq.avg_morale}% MOR` : "DATA UNAVAILABLE",
            tone: "accent",
          },
          {
            label: "URGENT RISKS",
            value: Array.isArray(risks) ? `${risks.length} HIGH PRIORITY` : "DATA UNAVAILABLE",
            tone: Array.isArray(risks) && risks.length > 0 ? "warning" : "positive",
          },
          {
            label: "OPEN DECISIONS",
            value: openTotal != null ? `${openTotal} PENDING` : "DATA UNAVAILABLE",
            tone: Number(openTotal || 0) > 0 ? "warning" : "positive",
          },
        ],
        footer: hub?.actionable_decisions?.boardroom_dilemma
          ? "BOARDROOM DILEMMA OPEN  •  DECISION REQUIRED"
          : "EXECUTIVE COMMAND SYNCHRONIZED",
        dataAvailable: true,
      };
    }
    case "managers_office": {
      const auth = destination.tactical_authority || hub?.club?.manager_tactical_authority;
      const ownerReq = auth?.owner_requested_mentality ?? hub?.club?.owner_requested_mentality ?? hub?.club?.mentality;
      const effMent = auth?.effective_mentality ?? hub?.club?.effective_matchday_mentality ?? report?.tactical_and_squad_concerns?.active_mentality;
      const formation = report?.tactical_and_squad_concerns?.formation;
      const fit = report?.fitness_and_selection;
      const stance = auth
        ? `${formatUpperToken(auth.decision_status)} (${auth.manager_name})`
        : destination.staff_lead?.is_vacant
          ? "NO MANAGER APPOINTED"
          : destination.staff_lead?.name || "DATA UNAVAILABLE";
      return {
        header: "TECHNICAL BENCH  /  TACTICAL AUTHORITY",
        title: "Matchday Tactics & Readiness",
        subtitle: auth?.reasoning || report?.summary || "Formation, mentality authority & conditioning",
        accent,
        rows: [
          { label: "OWNER REQUEST", value: formatUpperToken(ownerReq), tone: "muted" },
          {
            label: "MANAGER STANCE",
            value: stance,
            tone: auth?.decision_status === "rejected" || auth?.decision_status === "modified" ? "warning" : "positive",
          },
          {
            label: "EFFECTIVE MATCHDAY",
            value: effMent ? `${formatUpperToken(effMent)}${formation ? ` · ${formation}` : ""}` : "DATA UNAVAILABLE",
            tone: "accent",
          },
          {
            label: "SQUAD READINESS",
            value: fit ? `${fit.available_count ?? 0} FIT · ${fit.avg_fitness ?? 0}% COND` : "DATA UNAVAILABLE",
            tone: "positive",
          },
        ],
        footer: auth?.is_non_binding_preference
          ? "MANAGER HOLDS MATCHDAY TACTICAL AUTHORITY"
          : "TACTICAL THEATRE SYNCHRONIZED",
        dataAvailable: true,
      };
    }
    case "general_managers_office": {
      const deleg = report?.administrative_matters?.delegation_policy;
      const ops = report?.club_operations;
      const staffOrg = report?.staff_and_organisation;
      const team = Array.isArray(staffOrg?.executive_team) ? staffOrg.executive_team : [];
      const filledCount = team.filter((m: { is_vacant?: boolean }) => !m?.is_vacant).length;
      const projects = Array.isArray(ops?.active_construction_projects) ? ops.active_construction_projects.length : null;
      return {
        header: "ADMINISTRATION  /  CLUB OPERATIONS",
        title: "Delegation, Staffing & Campus",
        subtitle: report?.summary || "Administrative oversight and infrastructure builds",
        accent,
        rows: [
          { label: "DELEGATION MODE", value: formatUpperToken(deleg?.mode), tone: "accent" },
          {
            label: "EXECUTIVE STAFF",
            value: team.length > 0 ? `${filledCount}/${team.length} APPOINTED` : "DATA UNAVAILABLE",
            tone: filledCount < team.length ? "warning" : "positive",
          },
          {
            label: "CAMPUS PROJECTS",
            value: projects != null ? `${projects} IN BUILD · ${ops?.operational_modules_count ?? 0} LIVE` : "DATA UNAVAILABLE",
            tone: "accent",
          },
          {
            label: "DIRECTIVES",
            value: `${destination.active_directives_count ?? 0} ACTIVE · ${report?.administrative_matters?.scheduled_meetings_count ?? 0} MTGS`,
            tone: "positive",
          },
        ],
        footer: "GM OPERATIONS SUITE  •  AUTHORITATIVE REGISTRY",
        dataAvailable: true,
      };
    }
    case "academy_department": {
      const acad = report?.academy_development;
      const intake = report?.intake_recommendations;
      const concerns = Array.isArray(report?.development_concerns) ? report.development_concerns.length : null;
      return {
        header: "YOUTH LAB  /  PLAYER PATHWAY",
        title: "Academy Pipeline & Regens",
        subtitle: report?.summary || "Homegrown intake, development & senior promotion",
        accent,
        rows: [
          {
            label: "REGEN PIPELINE",
            value: acad ? `${acad.regen_count ?? 0} PROSPECTS (L${acad.academy_facility_level ?? 1})` : "DATA UNAVAILABLE",
            tone: "accent",
          },
          {
            label: "SENIOR READY",
            value: acad ? `${acad.ready_for_senior_count ?? 0} READY FOR CALL-UP` : "DATA UNAVAILABLE",
            tone: Number(acad?.ready_for_senior_count || 0) > 0 ? "positive" : "muted",
          },
          {
            label: "NEXT INTAKE",
            value: intake ? `${intake.projected_cohort_size ?? 0} PLAYERS · ${formatGtex(intake.next_intake_cost_gtex)}` : "DATA UNAVAILABLE",
            tone: "accent",
          },
          {
            label: "DEV CONCERNS",
            value: concerns != null ? `${concerns} FLAGGED · +${acad?.campus_development_speed_pct ?? 0}% SPD` : "DATA UNAVAILABLE",
            tone: Number(concerns || 0) > 0 ? "warning" : "positive",
          },
        ],
        footer: "ACADEMY DEVELOPMENT TRACKER",
        dataAvailable: true,
      };
    }
    case "medical_department": {
      const rehab = report?.rehabilitation_status;
      const perf = report?.medical_facility_performance;
      const fitC = report?.squad_fitness_concerns;
      return {
        header: "SPORTS MEDICINE  /  REHAB LAB",
        title: "Rehabilitation & Workload",
        subtitle: report?.summary || "Injury clearance, recovery protocols & player load",
        accent,
        rows: [
          {
            label: "ACTIVE INJURIES",
            value: rehab ? `${rehab.active_rehab_count ?? 0} IN REHAB (L${perf?.medical_facility_level ?? 1})` : "DATA UNAVAILABLE",
            tone: Number(rehab?.active_rehab_count || 0) > 0 ? "warning" : "positive",
          },
          {
            label: "SQUAD FITNESS",
            value: fitC ? `${fitC.avg_squad_fitness ?? 0}% AVG · ${fitC.below_85_fitness_count ?? 0} <85%` : "DATA UNAVAILABLE",
            tone: Number(fitC?.below_85_fitness_count || 0) > 0 ? "warning" : "positive",
          },
          {
            label: "HYDRO & CRYO",
            value: rehab ? (rehab.protocol_executed_today ? "ACTIVE TODAY" : `STANDBY (${rehab.protocol_cost_gtex ?? 800} GTX)`) : "DATA UNAVAILABLE",
            tone: rehab?.protocol_executed_today ? "positive" : "accent",
          },
          {
            label: "HEAL RATE",
            value: rehab && perf ? `${rehab.daily_injury_heal_days ?? 1}d/TICK · -${perf.injury_reduction_pct ?? 0}% RISK` : "DATA UNAVAILABLE",
            tone: "positive",
          },
        ],
        footer: "MEDICAL SUITE  •  AUTHORITATIVE SQUAD TELEMETRY",
        dataAvailable: true,
      };
    }
    case "finance_commercial_office":
    default: {
      const bal = report?.balances;
      const cashflow = report?.recent_income_and_expenditure;
      const sponsors = report?.sponsor_income;
      const md = report?.matchday_revenue;
      const cashVal = bal?.cash_gtex ?? hub?.club?.cash_gtex;
      const fcVal = bal?.fan_coin_balance ?? hub?.club?.fan_coin;
      const net = cashflow?.net_cashflow_gtex;
      const deals = Array.isArray(sponsors?.active_deals) ? sponsors.active_deals.length : null;
      return {
        header: "FINANCE VAULT  /  TREASURY",
        title: "Ledger, Sponsors & Matchday",
        subtitle: report?.summary || "Club balances, commercial agreements & gate projection",
        accent,
        rows: [
          {
            label: "CASH / FAN COIN",
            value: cashVal != null ? `${formatGtex(cashVal)} · ${(fcVal ?? 0).toLocaleString()} FC` : "DATA UNAVAILABLE",
            tone: "positive",
          },
          {
            label: "NET CASHFLOW",
            value: net != null ? `${Number(net) >= 0 ? "+" : ""}${formatGtex(net)}` : "DATA UNAVAILABLE",
            tone: Number(net ?? 0) >= 0 ? "positive" : "warning",
          },
          {
            label: "SPONSORSHIP",
            value: deals != null ? `${deals} ACTIVE · ${formatGtex(sponsors?.per_match_sponsor_income_gtex)}/M` : "DATA UNAVAILABLE",
            tone: "accent",
          },
          {
            label: "MATCHDAY GATE",
            value: md ? `CAP ${(md.stadium_capacity ?? 0).toLocaleString()} · ${formatGtex(md.projected_next_home_gate_gtex)}` : "DATA UNAVAILABLE",
            tone: "positive",
          },
        ],
        footer: "FINANCE DIRECTORATE  •  AUTHORITATIVE LEDGER",
        dataAvailable: true,
      };
    }
  }
}

function renderScreenCanvas(
  canvas: HTMLCanvasElement,
  texture: THREE.CanvasTexture,
  snapshot: LiveScreenSnapshot,
): void {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const w = canvas.width || 768;
  const h = canvas.height || 384;

  ctx.fillStyle = "#06101e";
  ctx.fillRect(0, 0, w, h);

  ctx.fillStyle = "#0b1a2e";
  ctx.fillRect(16, 16, w - 32, h - 32);

  ctx.fillStyle = snapshot.accent;
  ctx.fillRect(0, 0, 12, h);

  ctx.fillStyle = "#91a9c4";
  ctx.font = "600 20px Arial, sans-serif";
  ctx.fillText(snapshot.header.slice(0, 42), 36, 48);

  ctx.fillStyle = snapshot.dataAvailable ? "#34d399" : "#fbbf24";
  ctx.font = "700 18px Arial, sans-serif";
  ctx.fillText(snapshot.dataAvailable ? "LIVE SYNC" : "DATA UNAVAILABLE", w - 215, 48);

  ctx.fillStyle = "#f8fafc";
  ctx.font = "700 34px Arial, sans-serif";
  ctx.fillText(snapshot.title.slice(0, 32), 36, 94);

  ctx.fillStyle = "#b6c5d8";
  ctx.font = "20px Arial, sans-serif";
  ctx.fillText(snapshot.subtitle.slice(0, 56), 36, 126);

  ctx.fillStyle = "#1e324b";
  ctx.fillRect(36, 144, w - 72, 2);

  const visibleRows = snapshot.rows.slice(0, 4);
  visibleRows.forEach((row, index) => {
    const y = 180 + index * 40;
    ctx.fillStyle = "#0f233b";
    ctx.fillRect(36, y - 24, w - 72, 32);
    ctx.fillStyle = "#94a3b8";
    ctx.font = "600 18px Arial, sans-serif";
    ctx.fillText(row.label.slice(0, 22), 48, y - 2);
    ctx.fillStyle = rowValueColor(row.tone, snapshot.accent);
    ctx.font = "700 20px Arial, sans-serif";
    ctx.fillText(row.value.slice(0, 30), 270, y - 2);
  });

  ctx.fillStyle = snapshot.accent;
  ctx.fillRect(36, h - 48, 120, 4);

  ctx.fillStyle = "#64748b";
  ctx.font = "16px Arial, sans-serif";
  ctx.fillText(snapshot.footer.slice(0, 56), 172, h - 38);

  texture.needsUpdate = true;
}

function createScreenMesh(
  root: THREE.Group,
  screens: DepartmentScreenHandle[],
  options: {
    id: string;
    kind: "banner" | "telemetry" | "terminal";
    destinationKey: string;
    snapshot: LiveScreenSnapshot;
    position: [number, number, number];
    size: [number, number];
    rotationY?: number;
    hotspot?: Hotspot;
  },
): THREE.Mesh {
  const canvas = document.createElement("canvas");
  canvas.width = 768;
  canvas.height = 384;
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 4;

  renderScreenCanvas(canvas, texture, options.snapshot);

  const mesh = new THREE.Mesh(
    new THREE.PlaneGeometry(options.size[0], options.size[1]),
    new THREE.MeshBasicMaterial({ map: texture, side: THREE.DoubleSide }),
  );
  mesh.position.set(...options.position);
  mesh.rotation.y = options.rotationY ?? 0;
  mesh.userData = {
    ...mesh.userData,
    liveScreenId: options.id,
    liveScreenKind: options.kind,
    liveScreenSnapshot: options.snapshot,
    screenLines: [
      options.snapshot.header,
      options.snapshot.title,
      options.snapshot.subtitle,
      ...options.snapshot.rows.map((r) => `${r.label}: ${r.value}`),
      options.snapshot.footer,
    ],
  };
  root.add(mesh);

  screens.push({
    id: options.id,
    kind: options.kind,
    destinationKey: options.destinationKey,
    hotspotId: options.hotspot?.id,
    hotspotLabel: options.hotspot?.label,
    hotspotAction: options.hotspot?.action,
    accent: options.snapshot.accent,
    mesh,
    canvas,
    texture,
    snapshot: options.snapshot,
    lastSignature: JSON.stringify(options.snapshot),
  });
  return mesh;
}

export function updateDepartmentScreens(
  screens: DepartmentScreenHandle[],
  destinations: OperationsHubDestination[],
  hub?: ClubOperationsHubPayload | null,
): number {
  const destMap = new Map<string, OperationsHubDestination>();
  destinations.forEach((d) => destMap.set(d.destination_key, d));

  let updatedCount = 0;
  screens.forEach((handle) => {
    const dest = destMap.get(handle.destinationKey);
    if (!dest) return;
    const hotspot =
      handle.kind === "terminal" && handle.hotspotId
        ? (dest.hotspots || []).find((h) => h.id === handle.hotspotId)
        : undefined;
    const nextSnapshot = buildDestinationScreenSnapshot(dest, handle.kind, hub, hotspot);
    const nextSignature = JSON.stringify(nextSnapshot);
    if (nextSignature === handle.lastSignature) return;

    handle.snapshot = nextSnapshot;
    handle.lastSignature = nextSignature;
    renderScreenCanvas(handle.canvas, handle.texture, nextSnapshot);
    handle.mesh.userData.liveScreenSnapshot = nextSnapshot;
    handle.mesh.userData.screenLines = [
      nextSnapshot.header,
      nextSnapshot.title,
      nextSnapshot.subtitle,
      ...nextSnapshot.rows.map((r) => `${r.label}: ${r.value}`),
      nextSnapshot.footer,
    ];
    updatedCount += 1;
  });
  return updatedCount;
}

function addStaffActor(
  root: THREE.Group,
  position: [number, number, number],
  palette: { jacket: number; shirt: number; tie: number; skin: number; hair: number },
  phase: number,
): THREE.Group {
  const actor = new THREE.Group();
  actor.name = "department-staff-actor";
  actor.position.set(...position);
  actor.userData = { idlePhase: phase, baseY: position[1] };

  const jacket = standardMaterial(palette.jacket, 0.48, 0.12);
  const shirt = standardMaterial(palette.shirt, 0.82, 0.02);
  const tie = standardMaterial(palette.tie, 0.42, 0.18);
  const skin = standardMaterial(palette.skin, 0.88, 0.01);
  const hair = standardMaterial(palette.hair, 0.92, 0.01);
  const trousers = standardMaterial(0x172335, 0.72, 0.04);
  const shoes = standardMaterial(0x080d16, 0.34, 0.16);

  // A clean, stylised club-staff figure built from low-poly forms; no external
  // character asset or texture dependency is required.
  addCylinder(actor, 0.29, 0.38, 0.82, [0, 1.22, 0], jacket, 12);
  addCylinder(actor, 0.12, 0.12, 0.16, [0, 1.72, 0], skin, 12);
  const head = new THREE.Group();
  head.position.set(0, 1.96, 0);
  const face = new THREE.Mesh(new THREE.SphereGeometry(0.19, 12, 10), skin);
  face.position.y = 0.02;
  face.castShadow = true;
  head.add(face);
  const hairCap = new THREE.Mesh(new THREE.SphereGeometry(0.195, 12, 8), hair);
  hairCap.scale.set(1.02, 0.58, 1.02);
  hairCap.position.set(0, 0.13, -0.015);
  head.add(hairCap);
  actor.add(head);

  addBox(actor, [0.14, 0.46, 0.035], [0, 1.28, 0.345], shirt);
  addBox(actor, [0.07, 0.42, 0.045], [0, 1.27, 0.37], tie);
  const leftArm = new THREE.Group();
  leftArm.position.set(-0.34, 1.52, 0);
  addCylinder(leftArm, 0.105, 0.13, 0.56, [0, -0.29, 0], jacket, 10);
  addCylinder(leftArm, 0.075, 0.085, 0.22, [0, -0.65, 0], skin, 10);
  actor.add(leftArm);
  const rightArm = new THREE.Group();
  rightArm.position.set(0.34, 1.52, 0);
  addCylinder(rightArm, 0.105, 0.13, 0.56, [0, -0.29, 0], jacket, 10);
  addCylinder(rightArm, 0.075, 0.085, 0.22, [0, -0.65, 0], skin, 10);
  actor.add(rightArm);

  [-0.15, 0.15].forEach((x) => {
    addCylinder(actor, 0.105, 0.13, 0.72, [x, 0.42, 0], trousers, 10);
    addBox(actor, [0.22, 0.12, 0.38], [x, 0.08, 0.055], shoes);
  });

  actor.userData.leftArmPivot = leftArm;
  actor.userData.rightArmPivot = rightArm;
  actor.userData.headPivot = head;
  root.add(actor);
  return actor;
}

function addDepartmentScreen(
  root: THREE.Group,
  screens: DepartmentScreenHandle[],
  destination: OperationsHubDestination,
  kind: "banner" | "telemetry",
  hub: ClubOperationsHubPayload | null | undefined,
  position: [number, number, number],
  size: [number, number],
  rotationY = 0,
): THREE.Mesh {
  const snapshot = buildDestinationScreenSnapshot(destination, kind, hub);
  return createScreenMesh(root, screens, {
    id: `${destination.destination_key}:${kind}`,
    kind,
    destinationKey: destination.destination_key,
    snapshot,
    position,
    size,
    rotationY,
  });
}

function addRoomShell(
  root: THREE.Group,
  screens: DepartmentScreenHandle[],
  destination: OperationsHubDestination,
  hub: ClubOperationsHubPayload | null | undefined,
  accent: THREE.ColorRepresentation,
): void {
  const floor = addBox(
    root,
    [ROOM_WIDTH, 0.24, ROOM_DEPTH],
    [0, -0.12, 0],
    standardMaterial(0x172335, 0.42, 0.3),
  );
  floor.receiveShadow = true;

  const back = addBox(
    root,
    [ROOM_WIDTH, WALL_HEIGHT, 0.18],
    [0, WALL_HEIGHT / 2, -ROOM_DEPTH / 2],
    standardMaterial(0x101b2b, 0.82, 0.08),
  );
  back.receiveShadow = true;

  // Side walls stop short of the front edge, leaving the room readable as a cutaway.
  addBox(root, [0.18, WALL_HEIGHT, ROOM_DEPTH], [-ROOM_WIDTH / 2, WALL_HEIGHT / 2, 0], standardMaterial(0x122034));
  addBox(root, [0.18, WALL_HEIGHT, ROOM_DEPTH], [ROOM_WIDTH / 2, WALL_HEIGHT / 2, 0], standardMaterial(0x122034));

  // Architectural frame, ceiling ribs and restrained accent lighting.
  const accentMat = new THREE.MeshStandardMaterial({
    color: accent,
    emissive: accent,
    emissiveIntensity: 0.24,
    metalness: 0.32,
    roughness: 0.4,
  });
  addBox(root, [ROOM_WIDTH, 0.12, 0.16], [0, WALL_HEIGHT, -ROOM_DEPTH / 2 + 0.12], accentMat);
  addBox(root, [0.12, WALL_HEIGHT, 0.16], [-ROOM_WIDTH / 2 + 0.12, WALL_HEIGHT / 2, -ROOM_DEPTH / 2 + 0.12], accentMat);
  addBox(root, [0.12, WALL_HEIGHT, 0.16], [ROOM_WIDTH / 2 - 0.12, WALL_HEIGHT / 2, -ROOM_DEPTH / 2 + 0.12], accentMat);

  const trim = new THREE.Mesh(
    new THREE.BoxGeometry(ROOM_WIDTH - 0.6, 0.035, 0.035),
    new THREE.MeshBasicMaterial({ color: accent }),
  );
  trim.position.set(0, 0.06, ROOM_DEPTH / 2 - 0.18);
  root.add(trim);

  addDepartmentScreen(
    root,
    screens,
    destination,
    "banner",
    hub,
    [0, 3.55, -ROOM_DEPTH / 2 + 0.115],
    [3.4, 0.92],
  );
  const ceilingLight = new THREE.PointLight(accent, 1.8, 18);
  ceilingLight.position.set(0, 3.85, -0.2);
  root.add(ceilingLight);
}

function addChair(root: THREE.Group, x: number, z: number, accent: THREE.ColorRepresentation, rotation = 0): void {
  const dark = standardMaterial(0x17253a, 0.35, 0.35);
  const seat = addBox(root, [0.82, 0.18, 0.78], [x, 0.65, z], dark, rotation);
  addBox(root, [0.82, 0.92, 0.16], [x, 1.14, z - 0.28], dark, rotation);
  addCylinder(root, 0.07, 0.07, 0.52, [x, 0.31, z], dark, 10);
  addBox(root, [0.68, 0.06, 0.06], [x, 0.16, z], standardMaterial(accent), rotation);
  seat.userData = { furniture: "chair" };
}

function addTerminal(
  root: THREE.Group,
  screens: DepartmentScreenHandle[],
  destination: OperationsHubDestination,
  hotspot: Hotspot,
  hub: ClubOperationsHubPayload | null | undefined,
  pickables: THREE.Object3D[],
): void {
  const [x, hotspotY, z] = hotspot.offset;
  const accent = destination.accent_color || "#38bdf8";
  const bodyMat = standardMaterial(0x24344a, 0.34, 0.48);
  const base = addBox(root, [0.88, 0.92, 0.68], [x, 0.56, z], bodyMat);
  const top = addBox(root, [1.08, 0.08, 0.78], [x, 1.06, z], standardMaterial(0x0b1422, 0.28, 0.56));
  const stem = addBox(root, [0.12, 0.34, 0.12], [x, 1.27, z - 0.22], standardMaterial(0x64748b, 0.3, 0.72));
  const terminalSnapshot = buildDestinationScreenSnapshot(destination, "terminal", hub, hotspot);
  const screen = createScreenMesh(root, screens, {
    id: `${destination.destination_key}:terminal:${hotspot.id}`,
    kind: "terminal",
    destinationKey: destination.destination_key,
    snapshot: terminalSnapshot,
    position: [x, Math.max(1.55, hotspotY + 0.18), z + 0.03],
    size: [0.92, 0.52],
    hotspot,
  });

  const ring = new THREE.Mesh(
    new THREE.RingGeometry(0.56, 0.72, 24),
    new THREE.MeshStandardMaterial({
      color: accent,
      emissive: accent,
      emissiveIntensity: 0.45,
      roughness: 0.35,
      side: THREE.DoubleSide,
    }),
  );
  ring.rotation.x = -Math.PI / 2;
  ring.position.set(x, 0.07, z);
  root.add(ring);

  const actionData = {
    destinationKey: destination.destination_key,
    hotspotId: hotspot.id,
    hotspotLabel: hotspot.label,
    hotspotAction: hotspot.action,
  };
  [base, top, stem, screen, ring].forEach((object) => {
    object.userData = { ...object.userData, ...actionData };
  });
  ring.userData.isStationRing = true;
  pickables.push(base, top, screen);
}

function addExecutiveBoardroom(
  root: THREE.Group,
  screens: DepartmentScreenHandle[],
  destination: OperationsHubDestination,
  hub: ClubOperationsHubPayload | null | undefined,
): void {
  const wood = standardMaterial(0x493723, 0.3, 0.28);
  addBox(root, [4.5, 0.22, 1.8], [0, 0.98, -1.95], wood);
  addBox(root, [0.22, 0.9, 0.22], [-1.8, 0.43, -1.95], standardMaterial(0x273449, 0.3, 0.6));
  addBox(root, [0.22, 0.9, 0.22], [1.8, 0.43, -1.95], standardMaterial(0x273449, 0.3, 0.6));
  [-3.0, -1.0, 1.0, 3.0].forEach((x) => {
    addChair(root, x, -0.65, 0xd6b56d, Math.PI);
    addChair(root, x, -3.15, 0xd6b56d, 0);
  });
  addBox(root, [3.2, 0.045, 0.025], [0, 1.13, -1.95], standardMaterial(0xd6b56d, 0.25, 0.7));
  addBox(root, [1.7, 0.08, 0.6], [0, 1.14, -1.95], standardMaterial(0x0d2235, 0.25, 0.2));
  addBox(root, [2.4, 1.45, 0.12], [0, 1.82, -4.02], standardMaterial(0x0d1a2b, 0.28, 0.32));
  addDepartmentScreen(root, screens, destination, "telemetry", hub, [0, 1.88, -3.94], [2.1, 0.96]);
  addCylinder(root, 0.62, 0.62, 0.14, [-4.1, 0.08, -3.2], standardMaterial(0x162c3d, 0.3, 0.35));
  addCylinder(root, 0.48, 0.48, 0.28, [-4.1, 0.27, -3.2], standardMaterial(0x2c4b58, 0.25, 0.42));
  addBox(root, [1.0, 1.2, 0.5], [4.1, 0.6, -3.1], standardMaterial(0x202f40, 0.58, 0.18));
}

function addManagerTechnicalRoom(
  root: THREE.Group,
  screens: DepartmentScreenHandle[],
  destination: OperationsHubDestination,
  hub: ClubOperationsHubPayload | null | undefined,
): void {
  const turf = standardMaterial(0x174c3d, 0.85, 0.02);
  addBox(root, [5.2, 0.08, 3.4], [0, 0.06, -2.25], turf);
  const line = new THREE.Mesh(
    new THREE.PlaneGeometry(4.8, 3.0),
    new THREE.MeshBasicMaterial({ color: 0xd6f7e8, transparent: true, opacity: 0.55, side: THREE.DoubleSide }),
  );
  line.rotation.x = -Math.PI / 2;
  line.position.set(0, 0.112, -2.25);
  root.add(line);
  const pitchMark = new THREE.Mesh(
    new THREE.RingGeometry(0.48, 0.52, 32),
    new THREE.MeshBasicMaterial({ color: 0xe4f8ec, side: THREE.DoubleSide }),
  );
  pitchMark.rotation.x = -Math.PI / 2;
  pitchMark.position.set(0, 0.12, -2.25);
  root.add(pitchMark);
  addBox(root, [3.8, 1.5, 0.16], [0, 1.9, -4.02], standardMaterial(0x0c1727, 0.22, 0.52));
  addDepartmentScreen(root, screens, destination, "telemetry", hub, [0, 1.9, -3.92], [3.3, 1.15]);
  for (let i = 0; i < 5; i += 1) {
    addBox(root, [0.74, 0.16, 0.46], [-4.15 + i * 0.92, 0.16, 3.55], standardMaterial(0x26384e, 0.42, 0.24));
    addBox(root, [0.74, 1.1, 0.08], [-4.15 + i * 0.92, 0.76, 3.73], standardMaterial(0x1c2c40, 0.52, 0.2));
  }
  addBox(root, [2.3, 0.72, 1.0], [0, 0.52, -0.05], standardMaterial(0x182a40, 0.28, 0.48));
  addBox(root, [2.1, 0.025, 0.8], [0, 0.9, -0.05], standardMaterial(0x0d6b58, 0.4, 0.15));
  [-1.3, 1.3].forEach((x) => addChair(root, x, 0.25, 0x38bdf8));
}

function addGeneralManagerSuite(
  root: THREE.Group,
  screens: DepartmentScreenHandle[],
  destination: OperationsHubDestination,
  hub: ClubOperationsHubPayload | null | undefined,
): void {
  const wood = standardMaterial(0x5a4635, 0.34, 0.18);
  addBox(root, [2.9, 0.18, 1.45], [0, 0.93, -1.7], wood);
  addBox(root, [0.16, 0.78, 0.16], [-1.15, 0.42, -1.2], standardMaterial(0x29384a, 0.36, 0.46));
  addBox(root, [0.16, 0.78, 0.16], [1.15, 0.42, -1.2], standardMaterial(0x29384a, 0.36, 0.46));
  addChair(root, 0, 0.0, 0xa78bfa, Math.PI);
  [-3.9, -3.0, -2.1].forEach((z, index) => {
    addBox(root, [1.1, 0.16, 0.72], [4.0, 0.36 + index * 0.62, z], standardMaterial(0x26384a, 0.52, 0.14));
    addBox(root, [0.95, 0.05, 0.55], [4.0, 0.47 + index * 0.62, z], standardMaterial(0x394d61, 0.65, 0.08));
  });
  addBox(root, [3.0, 1.5, 0.15], [0, 1.85, -4.02], standardMaterial(0x141d32, 0.32, 0.38));
  addDepartmentScreen(root, screens, destination, "telemetry", hub, [0, 1.85, -3.92], [2.7, 1.1]);
  addBox(root, [1.0, 0.05, 0.65], [-3.9, 0.12, -3.4], standardMaterial(0x34485e, 0.52, 0.12));
}

function addAcademyDevelopmentLab(
  root: THREE.Group,
  screens: DepartmentScreenHandle[],
  destination: OperationsHubDestination,
  hub: ClubOperationsHubPayload | null | undefined,
): void {
  addBox(root, [5.2, 0.08, 3.3], [0, 0.05, -2.25], standardMaterial(0x23513a, 0.94, 0.01));
  const markings = new THREE.Group();
  const markMat = new THREE.MeshBasicMaterial({ color: 0xd9f4e3, transparent: true, opacity: 0.75 });
  const centerLine = new THREE.Mesh(new THREE.BoxGeometry(0.025, 0.012, 3.0), markMat);
  centerLine.position.set(0, 0.11, -2.25);
  markings.add(centerLine);
  const circle = new THREE.Mesh(new THREE.RingGeometry(0.42, 0.46, 32), markMat);
  circle.rotation.x = -Math.PI / 2;
  circle.position.set(0, 0.12, -2.25);
  markings.add(circle);
  root.add(markings);
  addBox(root, [1.3, 0.9, 0.15], [0, 0.56, -3.95], standardMaterial(0xe2e8f0, 0.58, 0.04));
  addBox(root, [0.08, 1.0, 0.08], [-0.61, 0.54, -3.95], standardMaterial(0xe2e8f0));
  addBox(root, [0.08, 1.0, 0.08], [0.61, 0.54, -3.95], standardMaterial(0xe2e8f0));
  addBox(root, [1.3, 0.08, 0.08], [0, 1.02, -3.95], standardMaterial(0xe2e8f0));
  [-3.5, -2.3, 2.3, 3.5].forEach((x, index) => {
    addCylinder(root, 0.12, 0.15, 0.42, [x, 0.3, 0.25 + (index % 2) * 0.55], standardMaterial(index % 2 ? 0xf59e0b : 0x38bdf8), 12);
  });
  addBox(root, [2.4, 1.15, 0.22], [3.9, 0.78, -3.5], standardMaterial(0x172b3f, 0.34, 0.42));
  addDepartmentScreen(root, screens, destination, "telemetry", hub, [3.9, 1.2, -3.36], [2.05, 0.9]);
  addBox(root, [1.8, 0.8, 0.9], [-3.7, 0.5, -3.3], standardMaterial(0x273a4b, 0.5, 0.1));
}

function addMedicalRehabilitationSuite(
  root: THREE.Group,
  screens: DepartmentScreenHandle[],
  destination: OperationsHubDestination,
  hub: ClubOperationsHubPayload | null | undefined,
): void {
  const tile = standardMaterial(0x1a3543, 0.28, 0.36);
  addBox(root, [4.2, 0.11, 1.55], [-2.55, 0.05, -2.2], tile);
  [-3.55, -2.35, -1.15].forEach((x) => {
    addBox(root, [0.92, 0.36, 1.12], [x, 0.34, -2.25], standardMaterial(0x607d8b, 0.25, 0.34));
    addBox(root, [0.82, 0.08, 1.02], [x, 0.57, -2.25], standardMaterial(0x8ad4df, 0.18, 0.2));
    addBox(root, [0.9, 0.06, 0.08], [x, 0.64, -2.75], standardMaterial(0xd5f5f4, 0.22, 0.06));
  });
  [1.4, 3.1].forEach((x) => {
    addBox(root, [1.3, 0.22, 2.1], [x, 0.56, -1.8], standardMaterial(0xd8e2e9, 0.44, 0.05));
    addBox(root, [1.3, 0.6, 0.14], [x, 0.96, -2.7], standardMaterial(0x637c91, 0.48, 0.06));
    addCylinder(root, 0.045, 0.045, 0.75, [x - 0.48, 0.26, -1.05], standardMaterial(0x526a7d), 10);
    addCylinder(root, 0.045, 0.045, 0.75, [x + 0.48, 0.26, -1.05], standardMaterial(0x526a7d), 10);
  });
  addBox(root, [3.8, 1.45, 0.16], [0, 1.9, -4.02], standardMaterial(0x10283a, 0.3, 0.42));
  addDepartmentScreen(root, screens, destination, "telemetry", hub, [0, 1.9, -3.92], [3.2, 1.1]);
  addBox(root, [0.12, 2.2, 0.12], [-0.4, 1.1, 2.9], standardMaterial(0x64748b, 0.3, 0.65));
  addBox(root, [0.12, 2.2, 0.12], [0.4, 1.1, 2.9], standardMaterial(0x64748b, 0.3, 0.65));
  addBox(root, [0.92, 0.08, 0.08], [0, 2.08, 2.9], standardMaterial(0x94a3b8, 0.3, 0.6));
}

function addFinanceCommercialSuite(
  root: THREE.Group,
  screens: DepartmentScreenHandle[],
  destination: OperationsHubDestination,
  hub: ClubOperationsHubPayload | null | undefined,
): void {
  const stone = standardMaterial(0x24364a, 0.28, 0.44);
  addBox(root, [3.8, 0.2, 1.55], [0, 0.92, -1.75], stone);
  addBox(root, [0.18, 0.8, 0.18], [-1.5, 0.42, -1.25], standardMaterial(0x16273a, 0.3, 0.5));
  addBox(root, [0.18, 0.8, 0.18], [1.5, 0.42, -1.25], standardMaterial(0x16273a, 0.3, 0.5));
  [-2.2, 2.2].forEach((x) => addChair(root, x, 0.1, 0x22d3ee, Math.PI));
  // A secure records vault and commercial partner wall make this room visually distinct.
  addBox(root, [1.9, 2.6, 0.75], [-3.8, 1.3, -3.45], standardMaterial(0x34495c, 0.25, 0.72));
  addCylinder(root, 0.42, 0.42, 0.12, [-3.8, 1.3, -3.04], standardMaterial(0x91a4b8, 0.22, 0.82), 32);
  addCylinder(root, 0.12, 0.12, 0.16, [-3.8, 1.3, -2.96], standardMaterial(0x0b1726, 0.22, 0.78), 20);
  addBox(root, [2.5, 1.75, 0.14], [3.75, 1.7, -3.6], standardMaterial(0x0e2032, 0.28, 0.5));
  addDepartmentScreen(root, screens, destination, "telemetry", hub, [3.75, 1.8, -3.48], [2.2, 1.15]);
  addBox(root, [0.9, 1.0, 0.75], [0, 0.5, 2.9], standardMaterial(0x1a2d42, 0.36, 0.46));
  addBox(root, [0.98, 0.55, 0.06], [0, 1.3, 2.48], standardMaterial(0x123b4a, 0.24, 0.58));
}

export function buildDepartmentInterior(
  destination: OperationsHubDestination,
  hub?: ClubOperationsHubPayload | null,
): DepartmentInteriorBuild {
  const group = new THREE.Group();
  group.name = "department-interior-" + destination.destination_key;
  group.userData = { destinationKey: destination.destination_key, departmentInterior: true };
  const pickables: THREE.Object3D[] = [];
  const animatedActors: THREE.Group[] = [];
  const screens: DepartmentScreenHandle[] = [];
  const accent = destination.accent_color || "#38bdf8";

  addRoomShell(group, screens, destination, hub, accent);

  switch (destination.destination_key) {
    case "executive_office":
      addExecutiveBoardroom(group, screens, destination, hub);
      animatedActors.push(addStaffActor(group, [-4.05, 0, 0.55], {
        jacket: 0x1e293b, shirt: 0xf8fafc, tie: 0xd6b56d, skin: 0x9a6548, hair: 0x20202a,
      }, 0.2));
      break;
    case "managers_office":
      addManagerTechnicalRoom(group, screens, destination, hub);
      animatedActors.push(addStaffActor(group, [4.0, 0, 1.5], {
        jacket: 0x153c63, shirt: 0xe8f1fa, tie: 0x38bdf8, skin: 0x86583f, hair: 0x161c25,
      }, 1.1));
      break;
    case "general_managers_office":
      addGeneralManagerSuite(group, screens, destination, hub);
      animatedActors.push(addStaffActor(group, [-4.0, 0, 1.45], {
        jacket: 0x3a315a, shirt: 0xf5f3ff, tie: 0xa78bfa, skin: 0x70452f, hair: 0x191820,
      }, 2.0));
      break;
    case "academy_department":
      addAcademyDevelopmentLab(group, screens, destination, hub);
      animatedActors.push(addStaffActor(group, [-4.05, 0, 1.5], {
        jacket: 0x24533f, shirt: 0xf0fdf4, tie: 0xf59e0b, skin: 0x986447, hair: 0x211d18,
      }, 2.8));
      break;
    case "medical_department":
      addMedicalRehabilitationSuite(group, screens, destination, hub);
      animatedActors.push(addStaffActor(group, [4.0, 0, 1.45], {
        jacket: 0x17616a, shirt: 0xf0fdfa, tie: 0xec4899, skin: 0x8d5e45, hair: 0x25212a,
      }, 3.6));
      break;
    case "finance_commercial_office":
      addFinanceCommercialSuite(group, screens, destination, hub);
      animatedActors.push(addStaffActor(group, [4.05, 0, 0.8], {
        jacket: 0x26394c, shirt: 0xf8fafc, tie: 0x22d3ee, skin: 0x9b694c, hair: 0x20242c,
      }, 4.4));
      break;
  }

  (destination.hotspots || []).forEach((hotspot) =>
    addTerminal(group, screens, destination, hotspot, hub, pickables),
  );
  return { group, pickables, animatedActors, screens };
}
