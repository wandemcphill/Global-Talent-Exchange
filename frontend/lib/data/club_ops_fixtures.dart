import 'package:gte_frontend/models/academy_models.dart';
import 'package:gte_frontend/models/club_finance_models.dart';
import 'package:gte_frontend/models/scouting_models.dart';
import 'package:gte_frontend/models/sponsorship_models.dart';

String clubOpsDisplayClubName(String clubId) {
  return clubId
      .split('-')
      .where((String fragment) => fragment.isNotEmpty)
      .map((String fragment) =>
          '${fragment[0].toUpperCase()}${fragment.substring(1)}')
      .join(' ');
}

ClubFinanceSnapshot fixtureClubFinance(String clubId, String? clubName) {
  final String resolvedClubName = clubName ?? clubOpsDisplayClubName(clubId);
  return ClubFinanceSnapshot(
    clubId: clubId,
    clubName: resolvedClubName,
    balanceSummary: ClubBalanceSummary(
      currentBalance: 3425000,
      operatingBudget: 8800000,
      reserveTarget: 2500000,
      monthlyIncome: 1480000,
      monthlyExpenses: 1295000,
      payrollCommitment: 680000,
      nextPayrollDate: DateTime.utc(2026, 3, 25),
      nextPayrollAmount: 670000,
      cashRunwayMonths: 5.3,
      balanceDeltaPercent: 8.4,
    ),
    budgetAllocations: const <FinanceCategoryBreakdown>[
      FinanceCategoryBreakdown(
        label: 'First-team payroll',
        amount: 3400000,
        sharePercent: 38.6,
        detail: 'Includes salaries, match bonuses, and medical cover.',
      ),
      FinanceCategoryBreakdown(
        label: 'Academy pathway',
        amount: 1760000,
        sharePercent: 20.0,
        detail: 'Staffing, education, nutrition, and accommodation.',
      ),
      FinanceCategoryBreakdown(
        label: 'Scouting pipeline',
        amount: 960000,
        sharePercent: 10.9,
        detail: 'Regional scouting travel, tournament access, and reporting.',
      ),
      FinanceCategoryBreakdown(
        label: 'Facilities and logistics',
        amount: 1420000,
        sharePercent: 16.1,
        detail: 'Training ground upkeep, transport, and stadium operations.',
      ),
      FinanceCategoryBreakdown(
        label: 'Commercial delivery',
        amount: 1260000,
        sharePercent: 14.4,
        detail: 'Sponsorship activation, content production, and fan events.',
      ),
    ],
    incomeBreakdown: const <FinanceCategoryBreakdown>[
      FinanceCategoryBreakdown(
        label: 'Broadcast and league share',
        amount: 520000,
        sharePercent: 35.1,
      ),
      FinanceCategoryBreakdown(
        label: 'Sponsorship contracts',
        amount: 410000,
        sharePercent: 27.7,
      ),
      FinanceCategoryBreakdown(
        label: 'Matchday operations',
        amount: 310000,
        sharePercent: 20.9,
      ),
      FinanceCategoryBreakdown(
        label: 'Player development grants',
        amount: 140000,
        sharePercent: 9.5,
      ),
      FinanceCategoryBreakdown(
        label: 'Merchandise and hospitality',
        amount: 100000,
        sharePercent: 6.8,
      ),
    ],
    expenseBreakdown: const <FinanceCategoryBreakdown>[
      FinanceCategoryBreakdown(
        label: 'Payroll',
        amount: 680000,
        sharePercent: 52.5,
      ),
      FinanceCategoryBreakdown(
        label: 'Academy operations',
        amount: 240000,
        sharePercent: 18.5,
      ),
      FinanceCategoryBreakdown(
        label: 'Travel and logistics',
        amount: 155000,
        sharePercent: 12.0,
      ),
      FinanceCategoryBreakdown(
        label: 'Scouting coverage',
        amount: 125000,
        sharePercent: 9.7,
      ),
      FinanceCategoryBreakdown(
        label: 'Commercial activation',
        amount: 95000,
        sharePercent: 7.3,
      ),
    ],
    cashflow: const <CashflowPoint>[
      CashflowPoint(
        label: 'Nov',
        inflow: 1310000,
        outflow: 1275000,
        closingBalance: 2960000,
      ),
      CashflowPoint(
        label: 'Dec',
        inflow: 1460000,
        outflow: 1280000,
        closingBalance: 3140000,
      ),
      CashflowPoint(
        label: 'Jan',
        inflow: 1520000,
        outflow: 1315000,
        closingBalance: 3345000,
      ),
      CashflowPoint(
        label: 'Feb',
        inflow: 1410000,
        outflow: 1300000,
        closingBalance: 3455000,
      ),
      CashflowPoint(
        label: 'Mar',
        inflow: 1480000,
        outflow: 1295000,
        closingBalance: 3425000,
      ),
    ],
    ledgerEntries: <LedgerEntry>[
      LedgerEntry(
        id: 'ledger-1',
        title: 'Principal shirt sponsorship installment',
        category: 'Commercial',
        counterparty: 'North Star Mobility',
        type: LedgerEntryType.income,
        amount: 185000,
        runningBalance: 3425000,
        occurredAt: DateTime.utc(2026, 3, 8),
        note: 'Quarterly contract milestone cleared after content delivery review.',
      ),
      LedgerEntry(
        id: 'ledger-2',
        title: 'Academy staff payroll',
        category: 'Academy pathway',
        counterparty: 'People operations',
        type: LedgerEntryType.expense,
        amount: 96000,
        runningBalance: 3240000,
        occurredAt: DateTime.utc(2026, 3, 6),
        note: 'Monthly wages for academy coaches, analysts, and welfare staff.',
      ),
      LedgerEntry(
        id: 'ledger-3',
        title: 'Regional scouting travel block',
        category: 'Scouting pipeline',
        counterparty: 'Travel desk',
        type: LedgerEntryType.expense,
        amount: 38000,
        runningBalance: 3336000,
        occurredAt: DateTime.utc(2026, 3, 5),
        note: 'West Africa and Iberia tournament coverage for March scouting window.',
      ),
      LedgerEntry(
        id: 'ledger-4',
        title: 'League facility grant',
        category: 'Development grant',
        counterparty: 'National league office',
        type: LedgerEntryType.income,
        amount: 120000,
        runningBalance: 3374000,
        occurredAt: DateTime.utc(2026, 3, 2),
        note: 'Facility improvement tranche linked to academy classroom upgrade.',
      ),
      LedgerEntry(
        id: 'ledger-5',
        title: 'Matchday operations settlement',
        category: 'Facilities and logistics',
        counterparty: 'Stadium operations vendor',
        type: LedgerEntryType.expense,
        amount: 52000,
        runningBalance: 3254000,
        occurredAt: DateTime.utc(2026, 3, 1),
        note: 'Security, stewarding, and broadcast compound access for home fixture.',
      ),
    ],
    financeNotes: const <String>[
      'Operating balance remains above the reserve target for the fifth straight month.',
      'Payroll is stable, but summer contract renewals should be aligned before June.',
      'Development spend is being protected to keep the academy pathway on plan.',
    ],
  );
}

SponsorshipDashboard fixtureSponsorships(String clubId, String? clubName) {
  final String resolvedClubName = clubName ?? clubOpsDisplayClubName(clubId);
  return SponsorshipDashboard(
    clubId: clubId,
    clubName: resolvedClubName,
    activeContractValue: 4980000,
    projectedRenewalValue: 5410000,
    packages: const <SponsorshipPackage>[
      SponsorshipPackage(
        id: 'principal-package',
        name: 'Principal partnership',
        tierLabel: 'Premier',
        description:
            'Front-of-shirt placement, matchday storytelling, and academy impact programming.',
        value: 2100000,
        durationMonths: 24,
        assetCount: 6,
        inventorySummary: 'Shirt front, backdrop, content series, and academy clinic rights.',
        deliverables: <String>[
          'Men’s first-team shirt front',
          'Academy pathway documentary series',
          'Matchday LED rotation',
        ],
        isFeatured: true,
      ),
      SponsorshipPackage(
        id: 'sleeve-package',
        name: 'Matchday sleeve partner',
        tierLabel: 'Club',
        description:
            'Premium sleeve visibility paired with hospitality and social content delivery.',
        value: 720000,
        durationMonths: 18,
        assetCount: 4,
        inventorySummary: 'Sleeve logo, hospitality allocation, and social recap support.',
        deliverables: <String>[
          'First-team sleeve',
          'Hospitality package',
          'Digital recap placement',
        ],
      ),
      SponsorshipPackage(
        id: 'academy-package',
        name: 'Academy pathway partner',
        tierLabel: 'Development',
        description:
            'Training centre visibility and education support attached to youth development outcomes.',
        value: 560000,
        durationMonths: 12,
        assetCount: 5,
        inventorySummary: 'Training centre signage, scholarship stories, and grassroots clinics.',
        deliverables: <String>[
          'Academy training centre branding',
          'Scholarship content support',
          'Community clinic presence',
        ],
      ),
    ],
    contracts: <SponsorshipContract>[
      SponsorshipContract(
        id: 'contract-north-star',
        sponsorName: 'North Star Mobility',
        packageName: 'Principal partnership',
        status: SponsorshipContractStatus.active,
        totalValue: 2100000,
        startDate: DateTime.utc(2025, 7, 1),
        endDate: DateTime.utc(2027, 6, 30),
        renewalWindowLabel: 'Review begins in January 2027',
        visibilityLabel: 'Highest visibility inventory',
        contactName: 'Amina Yusuf',
        moderationState: SponsorModerationState.approved,
        deliverables: const <String>[
          'Shirt front placement',
          'Academy pathway content series',
          'Three player appearance windows',
        ],
        notes: const <String>[
          'All creative assets approved through end of season.',
          'Quarterly performance review scheduled after Matchweek 31.',
        ],
      ),
      SponsorshipContract(
        id: 'contract-solaris',
        sponsorName: 'Solaris Bank',
        packageName: 'Matchday sleeve partner',
        status: SponsorshipContractStatus.renewalDue,
        totalValue: 720000,
        startDate: DateTime.utc(2025, 1, 15),
        endDate: DateTime.utc(2026, 7, 15),
        renewalWindowLabel: 'Renewal pack due in six weeks',
        visibilityLabel: 'Broadcast-facing inventory',
        contactName: 'Marco Alves',
        moderationState: SponsorModerationState.approved,
        deliverables: const <String>[
          'Sleeve branding',
          'Tunnel camera board',
          'Fan hospitality activation',
        ],
        notes: const <String>[
          'Commercial team preparing renewal valuation update.',
        ],
      ),
      SponsorshipContract(
        id: 'contract-greenroots',
        sponsorName: 'GreenRoots Foods',
        packageName: 'Academy pathway partner',
        status: SponsorshipContractStatus.pendingApproval,
        totalValue: 560000,
        startDate: DateTime.utc(2026, 4, 1),
        endDate: DateTime.utc(2027, 3, 31),
        renewalWindowLabel: 'Launch after asset moderation closes',
        visibilityLabel: 'Academy and community inventory',
        contactName: 'Leila Okafor',
        moderationState: SponsorModerationState.underReview,
        deliverables: const <String>[
          'Academy facility branding',
          'Nutrition education workshops',
          'Scholarship launch event',
        ],
        notes: const <String>[
          'Two asset variants still in moderation review.',
        ],
      ),
    ],
    assetSlots: const <SponsorAssetSlot>[
      SponsorAssetSlot(
        id: 'slot-shirt-front',
        surfaceName: 'First-team shirt front',
        placementLabel: 'Home, away, and cup kits',
        visibilityLabel: 'Peak live match visibility',
        moderationState: SponsorModerationState.approved,
        sponsorName: 'North Star Mobility',
      ),
      SponsorAssetSlot(
        id: 'slot-led-ribbon',
        surfaceName: 'Matchday LED ribbon',
        placementLabel: 'Touchline rotation',
        visibilityLabel: 'High in-stadium and broadcast visibility',
        moderationState: SponsorModerationState.approved,
        sponsorName: 'Solaris Bank',
      ),
      SponsorAssetSlot(
        id: 'slot-academy-wall',
        surfaceName: 'Academy welcome wall',
        placementLabel: 'Training centre entrance',
        visibilityLabel: 'Player, guardian, and visitor visibility',
        moderationState: SponsorModerationState.underReview,
        sponsorName: 'GreenRoots Foods',
        note: 'Updated artwork pending moderation sign-off.',
      ),
      SponsorAssetSlot(
        id: 'slot-content-title',
        surfaceName: 'Pathway content title card',
        placementLabel: 'Owned video series',
        visibilityLabel: 'Club channels and partner media',
        moderationState: SponsorModerationState.needsChanges,
        sponsorName: 'GreenRoots Foods',
        note: 'Nutrition claim language requires compliance edit.',
      ),
    ],
    notes: const <String>[
      'Commercial inventory is contract-based and fully visible to club staff before approval.',
      'Asset moderation is keeping sponsor creative aligned with club and league standards.',
      'Academy package pricing is being benchmarked against delivery workload, not vanity exposure.',
    ],
  );
}

AcademyDashboard fixtureAcademy(String clubId, String? clubName) {
  final String resolvedClubName = clubName ?? clubOpsDisplayClubName(clubId);
  return AcademyDashboard(
    clubId: clubId,
    clubName: resolvedClubName,
    pathwaySummary: const AcademyPathwaySummary(
      developmentBudget: 1760000,
      squadSize: 32,
      promotionsThisSeason: 4,
      graduationRatePercent: 12.5,
      staffCoverageLabel: 'Nine full-time staff across coaching, analysis, and welfare',
      facilityLabel: 'Category A regional performance centre',
    ),
    programs: const <AcademyProgram>[
      AcademyProgram(
        id: 'u17-transition',
        name: 'U17 transition group',
        ageBand: '16-17',
        focusArea: 'Decision speed and physical adaptation',
        staffLead: 'Coach Imani Cole',
        weeklyHours: 14,
        enrolledPlayers: 12,
        statusLabel: 'In season',
        outcomeLabel: 'Three players pushing for B-team minutes',
        description:
            'Bridges technical polish with senior tactical demands and match intensity.',
      ),
      AcademyProgram(
        id: 'u15-foundation',
        name: 'U15 foundation program',
        ageBand: '14-15',
        focusArea: 'Ball mastery and position-specific habits',
        staffLead: 'Coach Luis Mendes',
        weeklyHours: 11,
        enrolledPlayers: 10,
        statusLabel: 'In season',
        outcomeLabel: 'Six players ahead of planned development checkpoints',
        description:
            'Builds core technical repeatability before role specialization deepens.',
      ),
      AcademyProgram(
        id: 'scholarship-readiness',
        name: 'Scholarship readiness block',
        ageBand: '17-18',
        focusArea: 'Senior integration and life-skills support',
        staffLead: 'Coach Tega Bassey',
        weeklyHours: 9,
        enrolledPlayers: 10,
        statusLabel: 'Review week',
        outcomeLabel: 'Two contract recommendations due this month',
        description:
            'Prepares graduates for senior squad standards, loans, or scholarship conversion.',
      ),
    ],
    players: const <AcademyPlayer>[
      AcademyPlayer(
        id: 'academy-amara-cole',
        name: 'Amara Cole',
        position: 'CM',
        age: 17,
        pathwayStage: 'Scholarship readiness',
        potentialBand: 'High senior upside',
        developmentProgressPercent: 82,
        readinessScore: 78,
        minutesTarget: 540,
        statusLabel: 'Promotion watch',
        nextMilestone: 'Three B-team starts before April review',
        strengths: <String>['Scanning under pressure', 'Tempo control'],
        focusAreas: <String>['Acceleration', 'Long-range passing'],
      ),
      AcademyPlayer(
        id: 'academy-kofi-armah',
        name: 'Kofi Armah',
        position: 'CB',
        age: 16,
        pathwayStage: 'U17 transition group',
        potentialBand: 'Strong pathway fit',
        developmentProgressPercent: 74,
        readinessScore: 70,
        minutesTarget: 630,
        statusLabel: 'Stable progression',
        nextMilestone: 'Leadership review after next tournament block',
        strengths: <String>['Recovery speed', 'Aerial timing'],
        focusAreas: <String>['Distribution range', 'Body orientation'],
      ),
      AcademyPlayer(
        id: 'academy-sade-aluko',
        name: 'Sade Aluko',
        position: 'LW',
        age: 15,
        pathwayStage: 'U15 foundation program',
        potentialBand: 'Elite dribbling profile',
        developmentProgressPercent: 68,
        readinessScore: 61,
        minutesTarget: 720,
        statusLabel: 'High-ceiling project',
        nextMilestone: 'Progressive running load increase',
        strengths: <String>['1v1 carry', 'Final-third creativity'],
        focusAreas: <String>['Press resistance', 'Defensive recovery'],
      ),
      AcademyPlayer(
        id: 'academy-jonas-pereira',
        name: 'Jonas Pereira',
        position: 'GK',
        age: 18,
        pathwayStage: 'Scholarship readiness',
        potentialBand: 'Senior depth option',
        developmentProgressPercent: 88,
        readinessScore: 81,
        minutesTarget: 900,
        statusLabel: 'Promoted',
        nextMilestone: 'Senior cup squad integration',
        strengths: <String>['Claiming crosses', 'Set positioning'],
        focusAreas: <String>['Short build-up', 'Communication'],
        promotedToSenior: true,
      ),
    ],
    trainingCycles: <TrainingCycle>[
      TrainingCycle(
        id: 'cycle-march-transition',
        title: 'March transition cycle',
        phaseLabel: 'Integration',
        focus: 'Speed of play and off-ball structure',
        cohortLabel: 'U17 transition group',
        startDate: DateTime.utc(2026, 3, 2),
        endDate: DateTime.utc(2026, 3, 15),
        attendancePercent: 96,
        intensityLabel: 'High',
        expectedPromotionCount: 2,
        objective:
            'Prepare top transition players for B-team tactical demands and controlled exposure.',
      ),
      TrainingCycle(
        id: 'cycle-march-foundation',
        title: 'March foundation cycle',
        phaseLabel: 'Technical load',
        focus: 'Ball striking and first-touch consistency',
        cohortLabel: 'U15 foundation program',
        startDate: DateTime.utc(2026, 3, 3),
        endDate: DateTime.utc(2026, 3, 18),
        attendancePercent: 94,
        intensityLabel: 'Moderate',
        expectedPromotionCount: 0,
        objective:
            'Reinforce technical habits without overloading growth-stage players.',
      ),
    ],
    promotions: <AcademyPromotion>[
      AcademyPromotion(
        playerName: 'Jonas Pereira',
        destination: 'Senior squad cup rotation',
        occurredAt: DateTime.utc(2026, 2, 20),
        note: 'Promoted after six clean sheets in academy competition.',
      ),
      AcademyPromotion(
        playerName: 'Lina Duarte',
        destination: 'Partner club development loan',
        occurredAt: DateTime.utc(2026, 1, 28),
        note: 'Loan pathway selected to accelerate match minutes.',
      ),
    ],
    notes: const <String>[
      'Pathway planning is being led around minutes, readiness, and welfare support rather than one-off promotion decisions.',
      'The scholarship-readiness cohort is carrying the strongest senior integration group in two seasons.',
      'Training cycles are sequenced to protect development load across age bands.',
    ],
  );
}

ScoutingDashboard fixtureScouting(String clubId, String? clubName) {
  final String resolvedClubName = clubName ?? clubOpsDisplayClubName(clubId);
  return ScoutingDashboard(
    clubId: clubId,
    clubName: resolvedClubName,
    openAssignments: 6,
    activeRegions: 4,
    liveProspects: 18,
    trialsScheduled: 3,
    assignments: <ScoutAssignment>[
      ScoutAssignment(
        id: 'assignment-west-africa-midfield',
        scoutName: 'Nadia Mensah',
        region: 'West Africa',
        competition: 'U17 Coastal Invitational',
        focusArea: 'Press-resistant midfielders',
        priorityLabel: 'Priority',
        statusLabel: 'Report due this week',
        dueDate: DateTime.utc(2026, 3, 16),
        activeProspects: 5,
        travelWindow: 'Mar 10-15',
        objective:
            'Refresh the central-midfield shortlist before the April trial window.',
      ),
      ScoutAssignment(
        id: 'assignment-iberia-fullbacks',
        scoutName: 'Rui Esteves',
        region: 'Iberia',
        competition: 'Regional elite academy circuit',
        focusArea: 'Two-way full-backs',
        priorityLabel: 'Active',
        statusLabel: 'Travel complete',
        dueDate: DateTime.utc(2026, 3, 19),
        activeProspects: 4,
        travelWindow: 'Mar 5-12',
        objective:
            'Find one full-back profile ready for scholarship evaluation within 12 months.',
      ),
      ScoutAssignment(
        id: 'assignment-local-goalkeepers',
        scoutName: 'Jared Bello',
        region: 'Domestic catchment',
        competition: 'Schools cup series',
        focusArea: 'Goalkeeper succession',
        priorityLabel: 'Monitoring',
        statusLabel: 'Video follow-up pending',
        dueDate: DateTime.utc(2026, 3, 22),
        activeProspects: 3,
        travelWindow: 'Mar 14-21',
        objective:
            'Update the goalkeeper succession board for the next two intake cycles.',
      ),
    ],
    prospects: <Prospect>[
      Prospect(
        id: 'prospect-lamine-diallo',
        name: 'Lamine Diallo',
        position: 'CM',
        age: 16,
        region: 'Senegal',
        currentClub: 'Dakar Horizon Academy',
        stage: ProspectStage.shortlisted,
        readinessScore: 73,
        developmentProjection: 'High-volume midfield connector with senior upside',
        pathwayFitLabel: 'Strong fit for U17 transition',
        nextAction: 'Schedule live follow-up in April',
        availabilityLabel: 'Scholarship route open',
        lastUpdated: DateTime.utc(2026, 3, 9),
        strengths: <String>['Scanning', 'Line-breaking passing'],
        focusAreas: <String>['Duel strength', 'Final-third timing'],
      ),
      Prospect(
        id: 'prospect-marta-ramos',
        name: 'Marta Ramos',
        position: 'RB',
        age: 15,
        region: 'Portugal',
        currentClub: 'Porto Atlhetica Youth',
        stage: ProspectStage.trial,
        readinessScore: 69,
        developmentProjection: 'Dynamic two-way full-back with volume capacity',
        pathwayFitLabel: 'Good fit for foundation-to-transition handoff',
        nextAction: 'Confirm April training trial',
        availabilityLabel: 'Trial agreed in principle',
        lastUpdated: DateTime.utc(2026, 3, 7),
        strengths: <String>['Recovery pace', 'Crossing on the move'],
        focusAreas: <String>['Body strength', 'Defensive footwork'],
      ),
      Prospect(
        id: 'prospect-elias-simoes',
        name: 'Elias Simoes',
        position: 'GK',
        age: 17,
        region: 'Domestic catchment',
        currentClub: 'Rivergate Schools',
        stage: ProspectStage.monitored,
        readinessScore: 64,
        developmentProjection: 'Agile keeper with long-term pathway value',
        pathwayFitLabel: 'Goalkeeper succession option',
        nextAction: 'Collect second live report',
        availabilityLabel: 'Monitoring only',
        lastUpdated: DateTime.utc(2026, 3, 5),
        strengths: <String>['Reflexes', 'Starting position'],
        focusAreas: <String>['Aerial command', 'Passing detail'],
      ),
      Prospect(
        id: 'prospect-chioma-adebayo',
        name: 'Chioma Adebayo',
        position: 'LW',
        age: 16,
        region: 'Nigeria',
        currentClub: 'Lagos Promise Project',
        stage: ProspectStage.scholarship,
        readinessScore: 77,
        developmentProjection: 'Direct winger with clear academy progression runway',
        pathwayFitLabel: 'Scholarship offer prepared',
        nextAction: 'Guardian meeting and welfare review',
        availabilityLabel: 'Offer pack pending',
        lastUpdated: DateTime.utc(2026, 3, 8),
        strengths: <String>['Explosive take-ons', 'End-product variety'],
        focusAreas: <String>['Pressing shape', 'Decision speed'],
      ),
    ],
    reports: <ProspectReport>[
      ProspectReport(
        id: 'report-diallo',
        prospectId: 'prospect-lamine-diallo',
        scoutName: 'Nadia Mensah',
        headline: 'Midfield profile built for circulation under pressure',
        createdAt: DateTime.utc(2026, 3, 9),
        overallFit: 'Strong shortlist case',
        technicalNote:
            'Receives on the half-turn comfortably and rarely kills possession tempo.',
        physicalNote:
            'Needs another block of strength work before consistent duels at higher level.',
        characterNote:
            'Coach feedback highlights training discipline and quick adaptation.',
        recommendation:
            'Keep on shortlist and assign live follow-up before scholarship decision.',
      ),
      ProspectReport(
        id: 'report-ramos',
        prospectId: 'prospect-marta-ramos',
        scoutName: 'Rui Esteves',
        headline: 'Reliable full-back engine with modern delivery profile',
        createdAt: DateTime.utc(2026, 3, 7),
        overallFit: 'Trial recommended',
        technicalNote:
            'Timing on overlap and cutback selection is advanced for current age band.',
        physicalNote:
            'Carries intensity well over repeated actions and recovers quickly.',
        characterNote:
            'Consistent, coachable, and competitive in training tasks.',
        recommendation:
            'Proceed with trial and benchmark defensive adaptation against transition group.',
      ),
    ],
    notes: const <String>[
      'Assignments are planned around role needs, regional coverage, and pathway timing rather than speculative volume scouting.',
      'Shortlist progression is transparent from monitored to trial to scholarship review.',
      'The next trial block is being aligned with academy staffing capacity and welfare support.',
    ],
  );
}

YouthPipelineSnapshot fixtureYouthPipeline(String clubId, String? clubName) {
  return const YouthPipelineSnapshot(
    trackedProspects: 48,
    shortlistedProspects: 18,
    trialists: 7,
    scholarshipOffers: 4,
    promotedPlayers: 2,
    conversionPercent: 4.2,
    stages: <YouthPipelineStage>[
      YouthPipelineStage(
        label: 'Tracked',
        count: 48,
        description: 'Live reports and monitoring clips active in the scouting board.',
      ),
      YouthPipelineStage(
        label: 'Shortlisted',
        count: 18,
        description: 'Prospects with repeat viewings and pathway fit confirmed.',
      ),
      YouthPipelineStage(
        label: 'Trial',
        count: 7,
        description: 'Players invited into supervised training or match observation.',
      ),
      YouthPipelineStage(
        label: 'Scholarship',
        count: 4,
        description: 'Offer packs prepared with guardian, welfare, and schooling review.',
      ),
      YouthPipelineStage(
        label: 'Promoted',
        count: 2,
        description: 'Prospects converted into active academy or senior pathway steps.',
      ),
    ],
    notes: <String>[
      'Pipeline flow is reviewed weekly with academy staff to keep conversion decisions grounded in readiness.',
      'Guardian engagement and welfare checks remain mandatory before scholarship progression.',
      'Promotions are capped by staffing and minutes planning rather than headline volume.',
    ],
  );
}

ClubOpsAdminSnapshot fixtureClubOpsAdmin() {
  return const ClubOpsAdminSnapshot(
    clubsMonitored: 24,
    totalOperatingBudget: 168400000,
    activeContracts: 81,
    academyPromotions: 29,
    activeAssignments: 57,
    youthConversionPercent: 6.8,
    statusNotes: <String>[
      'Most clubs remain inside planned reserve and development budget thresholds.',
      'Commercial review load is concentrated in academy and community-facing sponsor assets.',
      'Youth conversion is trending up where scouting calendars and pathway staffing stay aligned.',
    ],
  );
}

ClubFinanceAnalyticsSnapshot fixtureFinanceAnalytics() {
  return const ClubFinanceAnalyticsSnapshot(
    averageMonthlyBalance: 6940000,
    operatingMarginPercent: 11.4,
    payrollSharePercent: 49.2,
    developmentSharePercent: 21.6,
    commercialSharePercent: 24.8,
    revenueReliabilityLabel: 'Renewals are steady and matchday variance is low',
    topExpenseLabel: 'Payroll remains the largest cost centre',
    categoryMix: <FinanceCategoryBreakdown>[
      FinanceCategoryBreakdown(label: 'Payroll', amount: 82200000, sharePercent: 49.2),
      FinanceCategoryBreakdown(label: 'Academy pathway', amount: 36000000, sharePercent: 21.6),
      FinanceCategoryBreakdown(label: 'Facilities', amount: 24400000, sharePercent: 14.6),
      FinanceCategoryBreakdown(label: 'Scouting pipeline', amount: 15700000, sharePercent: 9.4),
      FinanceCategoryBreakdown(label: 'Commercial delivery', amount: 8900000, sharePercent: 5.2),
    ],
    quarterlyCashflow: <CashflowPoint>[
      CashflowPoint(label: 'Q1', inflow: 41800000, outflow: 37400000, closingBalance: 65800000),
      CashflowPoint(label: 'Q2', inflow: 43600000, outflow: 38400000, closingBalance: 71000000),
      CashflowPoint(label: 'Q3', inflow: 40100000, outflow: 37200000, closingBalance: 73900000),
      CashflowPoint(label: 'Q4', inflow: 44800000, outflow: 39400000, closingBalance: 79300000),
    ],
  );
}

SponsorshipAnalyticsSnapshot fixtureSponsorshipAnalytics() {
  final SponsorshipDashboard dashboard =
      fixtureSponsorships('royal-lagos-fc', 'Royal Lagos FC');
  return SponsorshipAnalyticsSnapshot(
    totalRevenue: 21400000,
    averageContractValue: 792000,
    renewalRatePercent: 72.0,
    assetUtilizationPercent: 88.0,
    pendingReviews: 6,
    flaggedAssets: 2,
    topContracts: dashboard.contracts,
    reviewQueue: dashboard.assetSlots
        .where((SponsorAssetSlot slot) =>
            slot.moderationState != SponsorModerationState.approved)
        .toList(growable: false),
  );
}

AcademyAnalyticsSnapshot fixtureAcademyAnalytics() {
  final AcademyDashboard dashboard =
      fixtureAcademy('royal-lagos-fc', 'Royal Lagos FC');
  return AcademyAnalyticsSnapshot(
    conversionRatePercent: 12.4,
    retentionRatePercent: 86.0,
    averageReadinessScore: 71,
    promotionsThisSeason: dashboard.pathwaySummary.promotionsThisSeason,
    pathwayHealthLabel: 'Healthy balance between intake, minutes, and promotion readiness',
    programMix: dashboard.programs,
  );
}

ScoutingAnalyticsSnapshot fixtureScoutingAnalytics() {
  final ScoutingDashboard dashboard =
      fixtureScouting('royal-lagos-fc', 'Royal Lagos FC');
  return ScoutingAnalyticsSnapshot(
    assignmentCompletionPercent: 79.0,
    regionalCoveragePercent: 84.0,
    shortlistToTrialPercent: 38.0,
    trialToScholarshipPercent: 57.0,
    youthConversionPercent: 6.8,
    funnel: fixtureYouthPipeline('royal-lagos-fc', 'Royal Lagos FC').stages,
    assignmentLoad: dashboard.assignments,
  );
}
