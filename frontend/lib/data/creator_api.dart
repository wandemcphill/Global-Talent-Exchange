import 'dart:math';

import 'gte_api_repository.dart';
import 'gte_authed_api.dart';
import '../features/shared/data/gte_feature_support.dart';
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
    GteBackendMode mode = GteBackendMode.live,
  }) {
    final GteBackendMode resolvedMode = gteProductionBackendMode(mode);
    return CreatorApi(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: resolvedMode),
        transport: createModeAwareTransport(resolvedMode),
        accessToken: accessToken,
        mode: resolvedMode,
      ),
      baseUrl: baseUrl,
      fixtures: _CreatorFixtures.seed(baseUrl),
    );
  }

  factory CreatorApi.fixture({
    String baseUrl = 'https://community.gte.local',
    CreatorProfile? profile,
    CreatorFinanceSummary? financeSummary,
  }) {
    final CreatorProfile seededProfile =
        profile ?? _buildFixtureProfile(baseUrl);
    return CreatorApi(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.fixture,
        ),
        transport: createModeAwareTransport(GteBackendMode.fixture),
        accessToken: 'fixture-token',
        mode: GteBackendMode.fixture,
      ),
      baseUrl: baseUrl,
      fixtures: _CreatorFixtures(
        seededProfile,
        financeSummary: financeSummary ?? seededProfile.financeSummary,
      ),
    );
  }

  Future<CreatorProfile> fetchCreatorProfile({String creatorId = 'me'}) {
    if (client.mode == GteBackendMode.fixture) {
      return fixtures.profile();
    }
    if (creatorId != 'me') {
      return client.withFallback<CreatorProfile>(() async {
        final Map<String, dynamic> payload = await _getMapWithLegacyFallback(
          '/api/creators/$creatorId',
          auth: false,
        );
        return _buildProfileFromPublic(payload, baseUrl: baseUrl);
      }, () async => fixtures.profile());
    }
    return _fetchCurrentCreatorProfile();
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

  Future<CreatorCopilotAnalysis> analyzeCopilotDraft(
    CreatorCopilotDraft draft,
  ) async {
    if (client.mode == GteBackendMode.fixture) {
      return fixtures.copilotAnalysis(draft);
    }
    return client.withFallback<CreatorCopilotAnalysis>(() async {
      final Object? response = await _postWithLegacyFallback(
        '/api/creators/me/copilot/analyze',
        body: draft.toJson(),
      );
      if (response is Map) {
        return _creatorCopilotAnalysisFromJson(
          Map<String, dynamic>.from(response),
        );
      }
      throw const GteApiException(
        type: GteApiErrorType.parsing,
        message: 'Unexpected copilot response shape.',
      );
    }, () async => fixtures.copilotAnalysis(draft));
  }

  Future<CreatorFinanceSummary> fetchCreatorFinance() async {
    if (client.mode == GteBackendMode.fixture) {
      return fixtures.financeSummary();
    }
    final Map<String, dynamic> financePayload = await _getMapWithLegacyFallback(
      '/api/creators/me/finance',
    );
    return _creatorFinanceFromJson(financePayload);
  }

  Future<CreatorProfile> _fetchCurrentCreatorProfile() async {
    final Map<String, dynamic> summaryPayload = await _getMapWithLegacyFallback(
      '/api/creators/me/summary',
    );
    final List<dynamic> competitionsPayload = await _getListWithLegacyFallback(
      '/api/creators/me/competitions',
    );
    final Map<String, dynamic> financePayload = await _getMapWithLegacyFallback(
      '/api/creators/me/finance',
    );
    return _buildProfileFromSummary(
      summaryPayload,
      competitionsPayload,
      financePayload,
      baseUrl: baseUrl,
    );
  }

  Future<Map<String, dynamic>> _getMapWithLegacyFallback(
    String path, {
    bool auth = true,
  }) async {
    return _withLegacyNotFoundFallback<Map<String, dynamic>>(
      path,
      (String resolvedPath) => client.getMap(resolvedPath, auth: auth),
    );
  }

  Future<List<dynamic>> _getListWithLegacyFallback(
    String path, {
    bool auth = true,
  }) async {
    return _withLegacyNotFoundFallback<List<dynamic>>(
      path,
      (String resolvedPath) => client.getList(resolvedPath, auth: auth),
    );
  }

  Future<Object?> _postWithLegacyFallback(
    String path, {
    required Object? body,
    bool auth = true,
  }) async {
    return _withLegacyNotFoundFallback<Object?>(
      path,
      (String resolvedPath) =>
          client.post(resolvedPath, body: body, auth: auth),
    );
  }

  Future<T> _withLegacyNotFoundFallback<T>(
    String path,
    Future<T> Function(String path) action,
  ) async {
    try {
      return await action(path);
    } on GteApiException catch (error) {
      if (error.type != GteApiErrorType.notFound || _isAbsoluteUrl(path)) {
        rethrow;
      }
      return action(_legacyAbsolutePath(path));
    }
  }

  String _legacyAbsolutePath(String path) {
    return '${_normalizedBase(baseUrl)}$path';
  }
}

bool _isAbsoluteUrl(String path) {
  return path.startsWith('http://') || path.startsWith('https://');
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
    inviteAttributionRate:
        totalSignups == 0
            ? '0% attribution rate'
            : '${((qualifiedJoins / totalSignups) * 100).toStringAsFixed(1)}% attribution rate',
  );
  final CreatorRewardSummary rewardSummary = CreatorRewardSummary(
    pendingCommunityRewards: '$pendingRewards rewards pending review',
    lifetimeMilestoneRewards: '$approvedRewards rewards approved',
    competitionEntryCredits:
        '${finance.totalGiftIncome.toStringAsFixed(2)} credits unlocked',
    ledgerStatus:
        finance.pendingWithdrawals > 0
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
    totalClipIncome: 0,
    totalClipViews: 0,
    monetizedClips: 0,
    viralClipCount: 0,
    totalViralBonus: 0,
    totalReferralBonus: 0,
    totalWeeklyTopCreatorBonus: 0,
    totalWithdrawnGross: 0,
    totalWithdrawalFees: 0,
    totalWithdrawnNet: 0,
    pendingWithdrawals: 0,
    walletBalance: 0,
    walletAvailableBalance: 0,
    walletCurrency: 'credits',
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
    totalClipIncome: (json['total_clip_income'] as num?)?.toDouble() ?? 0,
    totalClipViews: (json['total_clip_views'] as num?)?.toInt() ?? 0,
    monetizedClips: (json['monetized_clips'] as num?)?.toInt() ?? 0,
    viralClipCount: (json['viral_clip_count'] as num?)?.toInt() ?? 0,
    totalViralBonus: (json['total_viral_bonus'] as num?)?.toDouble() ?? 0,
    totalReferralBonus: (json['total_referral_bonus'] as num?)?.toDouble() ?? 0,
    totalWeeklyTopCreatorBonus:
        (json['total_weekly_top_creator_bonus'] as num?)?.toDouble() ?? 0,
    totalWithdrawnGross:
        (json['total_withdrawn_gross'] as num?)?.toDouble() ?? 0,
    totalWithdrawalFees:
        (json['total_withdrawal_fees'] as num?)?.toDouble() ?? 0,
    totalWithdrawnNet: (json['total_withdrawn_net'] as num?)?.toDouble() ?? 0,
    pendingWithdrawals: (json['pending_withdrawals'] as num?)?.toDouble() ?? 0,
    walletBalance: (json['wallet_balance'] as num?)?.toDouble() ?? 0,
    walletAvailableBalance:
        (json['wallet_available_balance'] as num?)?.toDouble() ?? 0,
    walletCurrency: json['wallet_currency']?.toString() ?? 'credits',
    activeCompetitions: (json['active_competitions'] as num?)?.toInt() ?? 0,
    attributedSignups: (json['attributed_signups'] as num?)?.toInt() ?? 0,
    qualifiedJoins: (json['qualified_joins'] as num?)?.toInt() ?? 0,
    insights: (json['insights'] as List<dynamic>? ?? const <dynamic>[])
        .map((dynamic item) => item.toString())
        .toList(growable: false),
  );
}

class _CreatorFixtures {
  _CreatorFixtures(this._profile, {CreatorFinanceSummary? financeSummary})
    : _financeSummary = financeSummary ?? _profile.financeSummary;

  final CreatorProfile _profile;
  final CreatorFinanceSummary _financeSummary;

  static _CreatorFixtures seed(String baseUrl) {
    final CreatorProfile profile = _buildFixtureProfile(baseUrl);
    return _CreatorFixtures(profile, financeSummary: profile.financeSummary);
  }

  Future<CreatorProfile> profile() async => _profile;

  Future<CreatorFinanceSummary> financeSummary() async => _financeSummary;

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

  Future<CreatorCopilotAnalysis> copilotAnalysis(
    CreatorCopilotDraft draft,
  ) async {
    return _buildFixtureCopilotAnalysis(draft);
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
      totalClipIncome: 132.5,
      totalClipViews: 68400,
      monetizedClips: 6,
      viralClipCount: 1,
      totalViralBonus: 12,
      totalReferralBonus: 4.5,
      totalWeeklyTopCreatorBonus: 6,
      totalWithdrawnGross: 600,
      totalWithdrawalFees: 45,
      totalWithdrawnNet: 555,
      pendingWithdrawals: 120,
      walletBalance: 214.5,
      walletAvailableBalance: 214.5,
      walletCurrency: 'credits',
      activeCompetitions: 2,
      attributedSignups: 184,
      qualifiedJoins: 72,
      insights: <String>[
        '2 creator competitions are currently linked to your profile.',
        'Gift income settled: 420.0000 credits.',
        'Clip monetization is active with one viral highlight this week.',
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

CreatorCopilotAnalysis _creatorCopilotAnalysisFromJson(Object? value) {
  final Map<String, dynamic> json =
      value as Map<String, dynamic>? ?? <String, dynamic>{};
  return CreatorCopilotAnalysis(
    creatorId: json['creator_id']?.toString() ?? 'creator',
    draft: _creatorCopilotDraftFromJson(json['draft']),
    prediction: _creatorCopilotPredictionFromJson(json['prediction']),
    variantStrategy: _creatorCopilotVariantStrategyFromJson(
      json['variant_strategy'],
    ),
    timing: _creatorCopilotTimingFromJson(json['timing']),
    hookAnalysis: _creatorCopilotHookAnalysisFromJson(json['hook_analysis']),
    strategyProfile: _creatorCopilotStrategyProfileFromJson(
      json['strategy_profile'],
    ),
    liveCoaching: _creatorCopilotLiveCoachingFromJson(json['live_coaching']),
    actionPlan: _stringList(json['action_plan']),
  );
}

CreatorCopilotDraft _creatorCopilotDraftFromJson(Object? value) {
  final Map<String, dynamic> json =
      value as Map<String, dynamic>? ?? <String, dynamic>{};
  return CreatorCopilotDraft(
    title: json['title']?.toString() ?? 'Upload draft',
    durationSeconds: (json['duration_seconds'] as num?)?.toDouble() ?? 18,
    eventType: json['event_type']?.toString() ?? 'goal',
    tags: _stringList(json['tags']),
    preferredFormat: json['preferred_format']?.toString() ?? 'instant',
    introSeconds: (json['intro_seconds'] as num?)?.toDouble() ?? 1.1,
    visualIntensity: (json['visual_intensity'] as num?)?.toDouble() ?? 0.62,
    eventDensity: (json['event_density'] as num?)?.toDouble() ?? 0.58,
    audienceCluster: json['audience_cluster']?.toString() ?? 'general',
    hasReactionOverlay: json['has_reaction_overlay'] == true,
  );
}

CreatorCopilotPrediction _creatorCopilotPredictionFromJson(Object? value) {
  final Map<String, dynamic> json =
      value as Map<String, dynamic>? ?? <String, dynamic>{};
  return CreatorCopilotPrediction(
    viralProbability: (json['viral_probability'] as num?)?.toDouble() ?? 0,
    expectedViews: (json['expected_views'] as num?)?.toInt() ?? 0,
    bestFormat: json['best_format']?.toString() ?? 'instant',
    riskFlags: _stringList(json['risk_flags']),
  );
}

CreatorCopilotVariantStrategy _creatorCopilotVariantStrategyFromJson(
  Object? value,
) {
  final Map<String, dynamic> json =
      value as Map<String, dynamic>? ?? <String, dynamic>{};
  return CreatorCopilotVariantStrategy(
    recommendedVariants: (json['recommended_variants'] as List<dynamic>? ??
            const <dynamic>[])
        .map(_creatorCopilotVariantRecommendationFromJson)
        .toList(growable: false),
    explorationFactor: (json['exploration_factor'] as num?)?.toDouble() ?? 0.2,
    rationale: _stringList(json['rationale']),
  );
}

CreatorCopilotVariantRecommendation
_creatorCopilotVariantRecommendationFromJson(Object? value) {
  final Map<String, dynamic> json =
      value as Map<String, dynamic>? ?? <String, dynamic>{};
  return CreatorCopilotVariantRecommendation(
    type: json['type']?.toString() ?? 'instant',
    confidence: (json['confidence'] as num?)?.toDouble() ?? 0,
    reason: json['reason']?.toString() ?? 'No reason provided.',
    exploratory: json['exploratory'] == true,
  );
}

CreatorCopilotTiming _creatorCopilotTimingFromJson(Object? value) {
  final Map<String, dynamic> json =
      value as Map<String, dynamic>? ?? <String, dynamic>{};
  return CreatorCopilotTiming(
    postNow: json['post_now'] == true,
    bestTimeInMinutes: (json['best_time_in_minutes'] as num?)?.toInt() ?? 0,
    reason: json['reason']?.toString() ?? 'Window unavailable.',
    competitionDensity: (json['competition_density'] as num?)?.toDouble() ?? 0,
    audienceActivity: (json['audience_activity'] as num?)?.toDouble() ?? 0,
  );
}

CreatorCopilotHookAnalysis _creatorCopilotHookAnalysisFromJson(Object? value) {
  final Map<String, dynamic> json =
      value as Map<String, dynamic>? ?? <String, dynamic>{};
  return CreatorCopilotHookAnalysis(
    hookScore: (json['hook_score'] as num?)?.toDouble() ?? 0,
    suggestion: json['suggestion']?.toString() ?? 'Tighten the opening beat.',
    introStrength: json['intro_strength']?.toString() ?? 'weak',
    eventDensity: (json['event_density'] as num?)?.toDouble() ?? 0,
    visualIntensity: (json['visual_intensity'] as num?)?.toDouble() ?? 0,
  );
}

CreatorCopilotStrategyProfile _creatorCopilotStrategyProfileFromJson(
  Object? value,
) {
  final Map<String, dynamic> json =
      value as Map<String, dynamic>? ?? <String, dynamic>{};
  return CreatorCopilotStrategyProfile(
    profileKey: json['profile_key']?.toString() ?? 'creator:copilot:strategy',
    archetype: json['archetype']?.toString() ?? 'instant closer',
    summary:
        json['summary']?.toString() ?? 'This creator wins with instant clips.',
    confidence: (json['confidence'] as num?)?.toDouble() ?? 0,
    winningFormats: _stringList(json['winning_formats']),
    winningDuration: json['winning_duration']?.toString(),
    audienceCluster: json['audience_cluster']?.toString(),
  );
}

CreatorCopilotLiveCoaching _creatorCopilotLiveCoachingFromJson(Object? value) {
  final Map<String, dynamic> json =
      value as Map<String, dynamic>? ?? <String, dynamic>{};
  return CreatorCopilotLiveCoaching(
    eventName: json['event_name']?.toString() ?? 'copilot.alert.triggered',
    headline: json['headline']?.toString() ?? 'Switch fast if pace softens',
    message:
        json['message']?.toString() ??
        'If early retention drops, switch the lead variant immediately.',
    recommendedAction:
        json['recommended_action']?.toString() ??
        'Promote the stronger variant and shorten the intro.',
  );
}

CreatorCopilotAnalysis _buildFixtureCopilotAnalysis(CreatorCopilotDraft draft) {
  final double hookScore = _clampDouble(
    ((1 - (draft.introSeconds / 3.5)) * 0.5) +
        (draft.visualIntensity * 0.24) +
        (draft.eventDensity * 0.2) +
        (draft.hasReactionOverlay ? 0.06 : 0),
  );
  final String bestFormat;
  if (draft.eventType == 'analysis' || draft.preferredFormat == 'debate') {
    bestFormat = 'debate';
  } else if (draft.preferredFormat == 'meme' && draft.hasReactionOverlay) {
    bestFormat = 'meme';
  } else if (draft.durationSeconds <= 18 && draft.eventDensity >= 0.6) {
    bestFormat = 'instant';
  } else {
    bestFormat = draft.preferredFormat;
  }
  final double viralProbability = _clampDouble(
    0.34 +
        (hookScore * 0.26) +
        (draft.eventDensity * 0.14) +
        (draft.visualIntensity * 0.12) +
        (draft.durationSeconds <= 20 ? 0.08 : 0.0) +
        (bestFormat == 'debate' ? 0.04 : 0.0),
  );
  final List<String> riskFlags = <String>[
    if (draft.durationSeconds > 24) 'too long',
    if (hookScore < 0.5) 'low hook strength',
  ];
  final List<CreatorCopilotVariantRecommendation> recommendations =
      bestFormat == 'debate'
          ? const <CreatorCopilotVariantRecommendation>[
            CreatorCopilotVariantRecommendation(
              type: 'debate',
              confidence: 0.91,
              reason: 'creator history and audience fit both lean analytical',
              exploratory: false,
            ),
            CreatorCopilotVariantRecommendation(
              type: 'tactical',
              confidence: 0.81,
              reason:
                  'a second explainer lane keeps depth without losing intent',
              exploratory: false,
            ),
            CreatorCopilotVariantRecommendation(
              type: 'instant',
              confidence: 0.59,
              reason: 'exploration slot kept for a faster first-test cut',
              exploratory: true,
            ),
          ]
          : const <CreatorCopilotVariantRecommendation>[
            CreatorCopilotVariantRecommendation(
              type: 'meme',
              confidence: 0.89,
              reason: 'fast payoff plus overlay energy lifts share odds',
              exploratory: false,
            ),
            CreatorCopilotVariantRecommendation(
              type: 'instant',
              confidence: 0.83,
              reason: 'keeps the opening cleaner for first-window testing',
              exploratory: false,
            ),
            CreatorCopilotVariantRecommendation(
              type: 'debate',
              confidence: 0.54,
              reason: 'exploration slot preserved to avoid style lock-in',
              exploratory: true,
            ),
          ];
  final bool postNow = viralProbability >= 0.7 && hookScore >= 0.56;
  final int bestTimeInMinutes = postNow ? 0 : 23;
  final String durationLabel =
      draft.durationSeconds <= 20 ? 'under 20s' : 'around 20-30s';
  final String summary =
      'This creator wins with ${bestFormat == 'debate' ? 'precise' : 'chaotic'} $bestFormat clips $durationLabel.';
  return CreatorCopilotAnalysis(
    creatorId: 'creator-maya',
    draft: draft,
    prediction: CreatorCopilotPrediction(
      viralProbability: viralProbability,
      expectedViews:
          (68400 *
                  (0.72 + viralProbability) *
                  (bestFormat == 'debate' ? 0.92 : 0.98))
              .round(),
      bestFormat: bestFormat,
      riskFlags: riskFlags,
    ),
    variantStrategy: CreatorCopilotVariantStrategy(
      recommendedVariants: recommendations,
      explorationFactor: 0.2,
      rationale: <String>[
        if (bestFormat == 'debate')
          'Analytical drafts are outperforming slower creative lanes.'
        else
          'Fast-payoff formats are favored for this draft.',
        'One slot remains exploratory so creativity does not collapse into one style.',
      ],
    ),
    timing: CreatorCopilotTiming(
      postNow: postNow,
      bestTimeInMinutes: bestTimeInMinutes,
      reason:
          postNow
              ? 'current audience activity is healthy and competition pressure is manageable'
              : 'high competition window',
      competitionDensity: postNow ? 0.46 : 0.74,
      audienceActivity: 0.71,
    ),
    hookAnalysis: CreatorCopilotHookAnalysis(
      hookScore: hookScore,
      suggestion:
          hookScore < 0.5
              ? 'start with goal moment, not buildup'
              : 'hook is competitive; keep the payoff inside the first beat',
      introStrength:
          hookScore >= 0.78
              ? 'elite'
              : hookScore >= 0.56
              ? 'solid'
              : 'weak',
      eventDensity: draft.eventDensity,
      visualIntensity: draft.visualIntensity,
    ),
    strategyProfile: CreatorCopilotStrategyProfile(
      profileKey: 'creator:creator-maya:strategy_profile',
      archetype:
          bestFormat == 'debate'
              ? 'conversation spike operator'
              : 'chaotic meme accelerator',
      summary: summary,
      confidence: 0.84,
      winningFormats: <String>[
        bestFormat,
        recommendations.first.type,
        recommendations[1].type,
      ],
      winningDuration: durationLabel,
      audienceCluster: draft.audienceCluster,
    ),
    liveCoaching: CreatorCopilotLiveCoaching(
      eventName: 'copilot.alert.triggered',
      headline: 'Switch fast if first-minute pace softens',
      message:
          'If the first 60 seconds land below 60% of expected pace, switch emphasis to ${recommendations.first.type}.',
      recommendedAction:
          'Promote the ${recommendations.first.type} variant and trim the intro immediately.',
    ),
    actionPlan: <String>[
      'Lead with the $bestFormat format.',
      if (riskFlags.contains('low hook strength'))
        'Start with the payoff, not the buildup.',
      if (!postNow) 'Wait $bestTimeInMinutes minutes before posting.',
      'Keep ${recommendations.first.type} ready as the first performance fallback.',
    ],
  );
}

List<String> _stringList(Object? value) {
  return (value as List<dynamic>? ?? const <dynamic>[])
      .map((dynamic item) => item.toString())
      .toList(growable: false);
}

double _clampDouble(double value) {
  if (value < 0) {
    return 0;
  }
  if (value > 0.99) {
    return 0.99;
  }
  return value;
}
