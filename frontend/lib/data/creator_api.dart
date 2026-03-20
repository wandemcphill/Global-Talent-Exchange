import 'dart:math';

import 'gte_api_repository.dart';
import 'gte_authed_api.dart';
import 'gte_http_transport.dart';
import '../models/creator_models.dart';

class CreatorApi {
  CreatorApi({
    required this.client,
    required this.baseUrl,
    required this.fixtures,
  });

  final GteAuthedApi client;
  final String baseUrl;
  final _CreatorFixtures fixtures;

  factory CreatorApi.standard({
    required String baseUrl,
    required String? accessToken,
    GteBackendMode mode = GteBackendMode.liveThenFixture,
  }) {
    return CreatorApi(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: mode),
        transport: GteHttpTransport(),
        accessToken: accessToken,
        mode: mode,
      ),
      baseUrl: baseUrl,
      fixtures: _CreatorFixtures.seed(baseUrl),
    );
  }

  factory CreatorApi.fixture({
    String baseUrl = 'https://community.gte.local',
  }) {
    return CreatorApi(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.fixture,
        ),
        transport: GteHttpTransport(),
        accessToken: 'fixture-token',
        mode: GteBackendMode.fixture,
      ),
      baseUrl: baseUrl,
      fixtures: _CreatorFixtures.seed(baseUrl),
    );
  }

  Future<CreatorProfile> fetchCreatorProfile({String creatorId = 'me'}) {
    return client.withFallback<CreatorProfile>(
      () async {
        if (creatorId != 'me') {
          final Map<String, dynamic> payload =
              await client.getMap('/api/creators/$creatorId', auth: false);
          return _buildProfileFromPublic(payload, baseUrl: baseUrl);
        }
        final Map<String, dynamic> summaryPayload =
            await client.getMap('/api/creators/me/summary');
        final List<dynamic> competitionsPayload =
            await client.getList('/api/creators/me/competitions');
        final Map<String, dynamic> financePayload =
            await client.getMap('/api/creators/me/finance');
        return _buildProfileFromSummary(
          summaryPayload,
          competitionsPayload,
          financePayload,
          baseUrl: baseUrl,
        );
      },
      () async => fixtures.profile(),
    );
  }

  Future<CreatorCompetitionShareData> fetchCompetitionShare(
    String competitionId,
  ) async {
    final CreatorProfile profile = await fetchCreatorProfile();
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
      headline: 'Share creator competition invite',
      supportingText:
          'Share this creator competition invite with your community. Invite attribution stays tied to qualified contest participation and milestone rewards.',
      attributionNote:
          'Invite attribution is reviewable and tracks qualified community growth.',
    );
  }

  Future<CreatorLeaderboardSnapshot> fetchCreatorLeaderboard() async {
    return fixtures.leaderboard();
  }
}

CreatorProfile _buildProfileFromSummary(
  Map<String, dynamic> summary,
  List<dynamic> competitionsPayload,
  Map<String, dynamic> financePayload, {
  required String baseUrl,
}) {
  final Map<String, dynamic> profileJson =
      summary['profile'] as Map<String, dynamic>? ?? <String, dynamic>{};
  final List<CreatorCompetition> competitions = competitionsPayload
      .map(_creatorCompetitionFromJson)
      .toList(growable: false);
  final CreatorFinanceSummary finance = _creatorFinanceFromJson(financePayload);
  final int totalSignups = (summary['total_signups'] as num?)?.toInt() ?? 0;
  final int qualifiedJoins = (summary['qualified_joins'] as num?)?.toInt() ?? 0;
  final int activeParticipants =
      (summary['active_participants'] as num?)?.toInt() ?? 0;
  final int pendingRewards = (summary['pending_rewards'] as num?)?.toInt() ?? 0;
  final int approvedRewards =
      (summary['approved_rewards'] as num?)?.toInt() ?? 0;

  final CreatorStats stats = CreatorStats(
    communityInvites: totalSignups,
    qualifiedReferrals: qualifiedJoins,
    creatorCompetitions: competitions.length,
    contestParticipants: activeParticipants,
  );
  final CreatorGrowthSummary growthSummary = CreatorGrowthSummary(
    growthHeadline: 'Creator growth',
    growthDetail:
        '$qualifiedJoins qualified joins tied to $totalSignups signups this season.',
    weeklyInviteLift:
        '${max(0, qualifiedJoins ~/ 2)} qualified joins this week',
    topChannel: 'Creator share codes',
    inviteAttributionRate: totalSignups == 0
        ? '0% attribution rate'
        : '${((qualifiedJoins / totalSignups) * 100).toStringAsFixed(1)}% attribution rate',
  );
  final CreatorRewardSummary rewardSummary = CreatorRewardSummary(
    pendingCommunityRewards: '$pendingRewards rewards pending review',
    lifetimeMilestoneRewards: '$approvedRewards rewards approved',
    competitionEntryCredits:
        '${finance.totalGiftIncome.toStringAsFixed(2)} credits unlocked',
    ledgerStatus: finance.pendingWithdrawals > 0
        ? 'Withdrawals in flight'
        : 'Ledger balanced',
  );

  return CreatorProfile(
    creatorId: profileJson['creator_id']?.toString() ?? 'creator',
    userId: profileJson['user_id']?.toString() ?? 'user',
    displayName: profileJson['display_name']?.toString() ?? 'Creator',
    handle: profileJson['handle']?.toString() ?? 'creator',
    shareCode: profileJson['default_share_code']?.toString() ?? 'CREATOR',
    tier: profileJson['tier']?.toString() ?? 'standard',
    status: profileJson['status']?.toString() ?? 'active',
    revenueSharePercent:
        (profileJson['revenue_share_percent'] as num?)?.toDouble(),
    headline: 'Creator tier ${profileJson['tier']?.toString() ?? 'standard'}',
    bio:
        'Creator profile status ${profileJson['status']?.toString() ?? 'active'} with ${competitions.length} hosted competitions.',
    communityTag: 'Creator community',
    profileLink:
        '${_normalizedBase(baseUrl)}/community/creator/${profileJson['handle']?.toString() ?? 'creator'}',
    stats: stats,
    growthSummary: growthSummary,
    rewardSummary: rewardSummary,
    financeSummary: finance,
    competitions: competitions,
  );
}

CreatorProfile _buildProfileFromPublic(
  Map<String, dynamic> payload, {
  required String baseUrl,
}) {
  final CreatorFinanceSummary finance = CreatorFinanceSummary(
    currency: 'credits',
    totalGiftIncome: 0,
    totalRewardIncome: 0,
    totalWithdrawnGross: 0,
    totalWithdrawalFees: 0,
    totalWithdrawnNet: 0,
    pendingWithdrawals: 0,
    activeCompetitions: 0,
    attributedSignups: 0,
    qualifiedJoins: 0,
    insights: const <String>[],
  );
  return CreatorProfile(
    creatorId: payload['creator_id']?.toString() ?? 'creator',
    userId: payload['user_id']?.toString() ?? 'user',
    displayName: payload['display_name']?.toString() ?? 'Creator',
    handle: payload['handle']?.toString() ?? 'creator',
    shareCode: payload['default_share_code']?.toString() ?? 'CREATOR',
    tier: payload['tier']?.toString() ?? 'standard',
    status: payload['status']?.toString() ?? 'active',
    revenueSharePercent: (payload['revenue_share_percent'] as num?)?.toDouble(),
    headline: 'Creator tier ${payload['tier']?.toString() ?? 'standard'}',
    bio: 'Creator profile preview.',
    communityTag: 'Creator community',
    profileLink:
        '${_normalizedBase(baseUrl)}/community/creator/${payload['handle']?.toString() ?? 'creator'}',
    stats: const CreatorStats(
      communityInvites: 0,
      qualifiedReferrals: 0,
      creatorCompetitions: 0,
      contestParticipants: 0,
    ),
    growthSummary: const CreatorGrowthSummary(
      growthHeadline: 'Creator growth',
      growthDetail: 'Profile data loaded from public record.',
      weeklyInviteLift: '0 qualified joins this week',
      topChannel: 'Creator share codes',
      inviteAttributionRate: '0% attribution rate',
    ),
    rewardSummary: const CreatorRewardSummary(
      pendingCommunityRewards: '0 rewards pending review',
      lifetimeMilestoneRewards: '0 rewards approved',
      competitionEntryCredits: '0 credits unlocked',
      ledgerStatus: 'Ledger idle',
    ),
    financeSummary: finance,
    competitions: const <CreatorCompetition>[],
  );
}

CreatorCompetition _creatorCompetitionFromJson(Object? value) {
  final Map<String, dynamic> json =
      value as Map<String, dynamic>? ?? <String, dynamic>{};
  final int activeParticipants =
      (json['active_participants'] as num?)?.toInt() ?? 0;
  final int attributedSignups =
      (json['attributed_signups'] as num?)?.toInt() ?? 0;
  final int qualifiedJoins = (json['qualified_joins'] as num?)?.toInt() ?? 0;
  return CreatorCompetition(
    competitionId: json['competition_id']?.toString() ?? 'competition',
    title: json['title']?.toString() ?? 'Creator competition',
    seasonLabel: 'Active participants: $activeParticipants',
    inviteWindow:
        'Share code ${json['linked_share_code']?.toString() ?? 'CREATOR'}',
    inviteAttributionLabel: '$attributedSignups signups attributed',
    participationLabel: '$activeParticipants participants active',
    rewardLabel: '$qualifiedJoins qualified joins',
    isLive: activeParticipants > 0,
  );
}

CreatorFinanceSummary _creatorFinanceFromJson(Object? value) {
  final Map<String, dynamic> json =
      value as Map<String, dynamic>? ?? <String, dynamic>{};
  return CreatorFinanceSummary(
    currency: json['currency']?.toString() ?? 'credits',
    totalGiftIncome: (json['total_gift_income'] as num?)?.toDouble() ?? 0,
    totalRewardIncome: (json['total_reward_income'] as num?)?.toDouble() ?? 0,
    totalWithdrawnGross:
        (json['total_withdrawn_gross'] as num?)?.toDouble() ?? 0,
    totalWithdrawalFees:
        (json['total_withdrawal_fees'] as num?)?.toDouble() ?? 0,
    totalWithdrawnNet: (json['total_withdrawn_net'] as num?)?.toDouble() ?? 0,
    pendingWithdrawals: (json['pending_withdrawals'] as num?)?.toDouble() ?? 0,
    activeCompetitions: (json['active_competitions'] as num?)?.toInt() ?? 0,
    attributedSignups: (json['attributed_signups'] as num?)?.toInt() ?? 0,
    qualifiedJoins: (json['qualified_joins'] as num?)?.toInt() ?? 0,
    insights: (json['insights'] as List<dynamic>? ?? const <dynamic>[])
        .map((dynamic item) => item.toString())
        .toList(growable: false),
  );
}

class _CreatorFixtures {
  _CreatorFixtures(this._profile);

  final CreatorProfile _profile;

  static _CreatorFixtures seed(String baseUrl) {
    return _CreatorFixtures(_buildFixtureProfile(baseUrl));
  }

  Future<CreatorProfile> profile() async => _profile;

  Future<CreatorLeaderboardSnapshot> leaderboard() async {
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
      ],
    );
  }
}

CreatorProfile _buildFixtureProfile(String baseUrl) {
  return CreatorProfile(
    creatorId: 'creator-maya',
    userId: 'user-maya',
    displayName: 'Maya Scout',
    handle: 'maya_scout',
    shareCode: 'MAYA-GROWTH',
    tier: 'featured',
    status: 'active',
    revenueSharePercent: 12.5,
    headline: 'Community captain for creator competitions',
    bio:
        'Maya runs creator competitions built around scouting picks, contest participation, and community growth.',
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
    financeSummary: const CreatorFinanceSummary(
      currency: 'credits',
      totalGiftIncome: 420,
      totalRewardIncome: 980,
      totalWithdrawnGross: 600,
      totalWithdrawalFees: 45,
      totalWithdrawnNet: 555,
      pendingWithdrawals: 120,
      activeCompetitions: 2,
      attributedSignups: 184,
      qualifiedJoins: 72,
      insights: <String>[
        '2 creator competitions are currently linked to your profile.',
        'Gift income settled: 420.0000 credits.',
      ],
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
    ],
  );
}

String _normalizedBase(String baseUrl) {
  return baseUrl.endsWith('/')
      ? baseUrl.substring(0, baseUrl.length - 1)
      : baseUrl;
}
