import '../data/gte_api_repository.dart';
import '../models/creator_models.dart';

class CreatorApi {
  CreatorApi._({
    required this.baseUrl,
    required this.mode,
    required this.latency,
  });

  final String baseUrl;
  final GteBackendMode mode;
  final Duration latency;

  factory CreatorApi.standard({
    required String baseUrl,
    GteBackendMode mode = GteBackendMode.liveThenFixture,
  }) {
    return CreatorApi._(
      baseUrl: baseUrl,
      mode: mode,
      latency: const Duration(milliseconds: 180),
    );
  }

  factory CreatorApi.fixture({
    String baseUrl = 'https://community.gte.local',
    Duration latency = Duration.zero,
  }) {
    return CreatorApi._(
      baseUrl: baseUrl,
      mode: GteBackendMode.fixture,
      latency: latency,
    );
  }

  Future<CreatorProfile> fetchCreatorProfile({
    String creatorId = _defaultCreatorId,
  }) async {
    await Future<void>.delayed(latency);
    return _buildProfile(baseUrl, creatorId);
  }

  Future<CreatorCompetitionShareData> fetchCompetitionShare(
    String competitionId,
  ) async {
    await Future<void>.delayed(latency);
    final CreatorProfile profile = _buildProfile(baseUrl, _defaultCreatorId);
    final CreatorCompetition competition = profile.competitions.firstWhere(
      (CreatorCompetition item) => item.competitionId == competitionId,
      orElse: () => profile.competitions.first,
    );
    return CreatorCompetitionShareData(
      competition: competition,
      shareCode:
          '${profile.shareCode}-${competition.competitionId.toUpperCase()}',
      shareUrl:
          '${_normalizedBase(baseUrl)}/community/creator/${profile.handle}/competitions/${competition.competitionId}',
      headline: 'Invite friends to join creator competition',
      supportingText:
          'Share this creator competition with your community. Invite attribution stays tied to qualified contest participation and milestone rewards.',
      attributionNote:
          'Invite attribution is reviewable and tracks qualified community growth.',
    );
  }

  Future<CreatorLeaderboardSnapshot> fetchCreatorLeaderboard() async {
    await Future<void>.delayed(latency);
    return const CreatorLeaderboardSnapshot(
      growthHeadline: 'Top creators',
      growthDetail:
          'Community growth is ranked by qualified participation, creator competition health, and reviewable invite attribution.',
      topCreatorLabel: 'Maya Scout leads this week',
      strongestCompetitionLabel:
          'Spring Scout Sprint has the strongest creator competition lift',
      highestQualifiedParticipationLabel:
          '72 qualified joins remain the highest verified participation mark',
      entries: <CreatorLeaderboardEntry>[
        CreatorLeaderboardEntry(
          rank: 1,
          creatorId: 'creator-maya',
          displayName: 'Maya Scout',
          handle: 'maya_scout',
          shareCode: 'MAYA-GROWTH',
          communityInvites: 184,
          qualifiedParticipation: 72,
          creatorCompetitions: 4,
          communityRewardLabel: '420 competition credits pending review',
          highlightLabel: 'Strongest creator competition conversion',
          flaggedForReview: false,
        ),
        CreatorLeaderboardEntry(
          rank: 2,
          creatorId: 'creator-ade',
          displayName: 'Ade Tactics',
          handle: 'ade_tactics',
          shareCode: 'ADE-CREW',
          communityInvites: 160,
          qualifiedParticipation: 61,
          creatorCompetitions: 3,
          communityRewardLabel: '360 competition credits approved',
          highlightLabel: 'Highest WhatsApp participation share',
          flaggedForReview: false,
        ),
        CreatorLeaderboardEntry(
          rank: 3,
          creatorId: 'creator-rina',
          displayName: 'Rina XI',
          handle: 'rina_xi',
          shareCode: 'RINA-XI',
          communityInvites: 142,
          qualifiedParticipation: 54,
          creatorCompetitions: 2,
          communityRewardLabel: '240 competition credits under review',
          highlightLabel: 'Fastest weekly community growth',
          flaggedForReview: true,
        ),
      ],
    );
  }
}

const String _defaultCreatorId = 'creator-maya';

CreatorProfile _buildProfile(String baseUrl, String creatorId) {
  return CreatorProfile(
    creatorId: creatorId,
    displayName: 'Maya Scout',
    handle: 'maya_scout',
    shareCode: 'MAYA-GROWTH',
    headline: 'Community captain for creator competitions',
    bio:
        'Maya runs creator competitions built around scouting picks, contest participation, and community growth. Her invite drops focus on welcoming new managers and turning first-time joins into repeat competition entries.',
    communityTag: 'Creator competition host',
    profileLink: '${_normalizedBase(baseUrl)}/community/creator/maya_scout',
    stats: const CreatorStats(
      communityInvites: 184,
      qualifiedReferrals: 72,
      creatorCompetitions: 4,
      contestParticipants: 236,
    ),
    growthSummary: const CreatorGrowthSummary(
      growthHeadline: 'Growth summary',
      growthDetail:
          'Community invites are converting steadily into contest participation, with the strongest lift coming from matchday reminder shares.',
      weeklyInviteLift: '+18 qualified joins this week',
      topChannel: 'WhatsApp circles',
      inviteAttributionRate: '39% invite attribution rate',
    ),
    rewardSummary: const CreatorRewardSummary(
      pendingCommunityRewards: '280 competition credits pending review',
      lifetimeMilestoneRewards: '1,420 competition credits lifetime',
      competitionEntryCredits: '96 entry credits available',
      ledgerStatus: 'Ledger reviewed within 24 hours',
    ),
    competitions: const <CreatorCompetition>[
      CreatorCompetition(
        competitionId: 'spring-scout-sprint',
        title: 'Spring Scout Sprint',
        seasonLabel: 'Round 4 community invite window',
        inviteWindow: 'Invite friends before Friday 18:00 UTC',
        inviteAttributionLabel: '26 qualified joins attributed',
        participationLabel: '88 contest participants active',
        rewardLabel: 'Milestone reward unlock at 100 participants',
        isLive: true,
      ),
      CreatorCompetition(
        competitionId: 'creator-captains-cup',
        title: 'Creator Captains Cup',
        seasonLabel: 'Bracket reveal next week',
        inviteWindow: 'Share code active for seven days',
        inviteAttributionLabel: '14 invite attributions confirmed',
        participationLabel: '64 community entries locked',
        rewardLabel: 'Creator community reward in review',
        isLive: false,
      ),
    ],
  );
}

String _normalizedBase(String baseUrl) {
  return baseUrl.endsWith('/')
      ? baseUrl.substring(0, baseUrl.length - 1)
      : baseUrl;
}
