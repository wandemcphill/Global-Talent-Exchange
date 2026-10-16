import '../models/gtex_competition_models.dart';

abstract class GtexCompetitionRepository {
  Future<List<GtexCompetitionSummary>> listCompetitions();
  Future<GtexCompetitionDetail> getCompetitionDetail(String competitionId);
  Future<void> joinCompetition(String competitionId);
  Future<void> createCompetition(GtexCompetitionDraft draft);
}

class DemoGtexCompetitionRepository implements GtexCompetitionRepository {
  const DemoGtexCompetitionRepository();

  @override
  Future<List<GtexCompetitionSummary>> listCompetitions() async {
    return _summaries;
  }

  @override
  Future<GtexCompetitionDetail> getCompetitionDetail(String competitionId) async {
    final GtexCompetitionSummary selected = _summaries.firstWhere(
      (GtexCompetitionSummary item) => item.id == competitionId,
      orElse: () => _summaries.first,
    );
    return GtexCompetitionDetail(
      summary: selected,
      fixtures: const <GtexCompetitionFixture>[
        GtexCompetitionFixture(
          id: 'fx-001',
          homeClub: 'Lagos Royals FC',
          awayClub: 'Accra Merchants',
          stage: 'Group A',
          timeLabel: 'Today • 19:30',
          homeScore: 2,
          awayScore: 1,
          isLive: true,
        ),
        GtexCompetitionFixture(
          id: 'fx-002',
          homeClub: 'Arsenal Shortlist XI',
          awayClub: 'Ibadan Galaxy',
          stage: 'Group A',
          timeLabel: 'Tomorrow • 20:00',
        ),
        GtexCompetitionFixture(
          id: 'fx-003',
          homeClub: 'Cape Town Atlas',
          awayClub: 'Kumasi Talents',
          stage: 'Quarter Final',
          timeLabel: 'Sat • 18:00',
        ),
      ],
      standings: const <GtexCompetitionStanding>[
        GtexCompetitionStanding(rank: 1, clubName: 'Lagos Royals FC', played: 3, wins: 2, draws: 1, losses: 0, goalDifference: 5, points: 7),
        GtexCompetitionStanding(rank: 2, clubName: 'Arsenal Shortlist XI', played: 3, wins: 2, draws: 0, losses: 1, goalDifference: 2, points: 6),
        GtexCompetitionStanding(rank: 3, clubName: 'Accra Merchants', played: 3, wins: 1, draws: 1, losses: 1, goalDifference: 0, points: 4),
        GtexCompetitionStanding(rank: 4, clubName: 'Ibadan Galaxy', played: 3, wins: 0, draws: 0, losses: 3, goalDifference: -7, points: 0),
      ],
      stages: const <GtexTournamentStageProgress>[
        GtexTournamentStageProgress(title: 'Registration', statusLabel: 'Complete', progressPercent: 1, summary: '32 clubs registered and verified.'),
        GtexTournamentStageProgress(title: 'Group Stage', statusLabel: 'Live', progressPercent: .62, summary: '18 of 30 fixtures completed.'),
        GtexTournamentStageProgress(title: 'Knockouts', statusLabel: 'Pending', progressPercent: .05, summary: 'Seeded from group rankings.'),
        GtexTournamentStageProgress(title: 'Final + Awards', statusLabel: 'Pending', progressPercent: 0, summary: 'Winner reveal, MVP and regen award story.'),
      ],
      rules: const <GtexCompetitionRule>[
        GtexCompetitionRule(title: 'Squad size', description: '18 registered players. Up to 4 rented national-team eligible players where the competition permits.'),
        GtexCompetitionRule(title: 'Eligibility lock', description: 'Players are locked at kickoff. Shortlist purchases must settle before registration close.'),
        GtexCompetitionRule(title: 'Prize settlement', description: 'Prize coins are released after admin dispute window closes.'),
      ],
      newsSignals: const <String>[
        'AI News: Lagos Royals stun Accra with late regen winner.',
        'Transfer desk: three clubs shortlisted Arsenal wide players before Group A deadline.',
        'Awards watch: academy regen Musa Adeyemi now leads the U20 golden boot race.',
      ],
    );
  }

  @override
  Future<void> joinCompetition(String competitionId) async {}

  @override
  Future<void> createCompetition(GtexCompetitionDraft draft) async {}
}

const List<GtexCompetitionSummary> _summaries = <GtexCompetitionSummary>[
  GtexCompetitionSummary(
    id: 'gtex-afcon-u20',
    title: 'GTEX U20 AFCON Cup',
    kind: GtexCompetitionKind.nationalTeam,
    status: GtexCompetitionStatus.registrationOpen,
    regionLabel: 'Africa • U20',
    entryFeeCredits: 250,
    prizePoolCredits: 12500,
    registeredClubs: 18,
    maxClubs: 32,
    progressPercent: .42,
    currentStage: 'Registration',
    startsAtLabel: 'Starts in 3 days',
    description: 'National-team rental enabled tournament for emerging U20 squads and pre-seeded regens.',
  ),
  GtexCompetitionSummary(
    id: 'global-talent-cup',
    title: 'Global Talent Cup',
    kind: GtexCompetitionKind.gtexTournament,
    status: GtexCompetitionStatus.live,
    regionLabel: 'Worldwide',
    entryFeeCredits: 500,
    prizePoolCredits: 45000,
    registeredClubs: 32,
    maxClubs: 32,
    progressPercent: .66,
    currentStage: 'Group Stage',
    startsAtLabel: 'Live now',
    description: 'Premier GTEX club tournament featuring owned players, purchased stars, and elite regens.',
  ),
  GtexCompetitionSummary(
    id: 'creator-friday-night',
    title: 'Friday Night Creator League',
    kind: GtexCompetitionKind.creatorHosted,
    status: GtexCompetitionStatus.registrationOpen,
    regionLabel: 'Creator hosted',
    entryFeeCredits: 150,
    prizePoolCredits: 8000,
    registeredClubs: 11,
    maxClubs: 16,
    progressPercent: .31,
    currentStage: 'Registration',
    startsAtLabel: 'Friday • 21:00',
    description: 'Creator-hosted weekly competition with streamable finals and AI newsroom coverage.',
    creatorName: 'GTEX Creators',
  ),
  GtexCompetitionSummary(
    id: 'user-lagos-ladder',
    title: 'Lagos Weekend Ladder',
    kind: GtexCompetitionKind.userHosted,
    status: GtexCompetitionStatus.draft,
    regionLabel: 'Nigeria • User hosted',
    entryFeeCredits: 50,
    prizePoolCredits: 1200,
    registeredClubs: 0,
    maxClubs: 8,
    progressPercent: 0,
    currentStage: 'Draft setup',
    startsAtLabel: 'Unpublished',
    description: 'Example user-hosted competition awaiting rule confirmation and publish preview.',
    ownerClubName: 'Your Club',
  ),
];
