import 'gte_api_repository.dart';
import 'gte_authed_api.dart';
import 'gte_http_transport.dart';
import '../models/referral_models.dart';
import '../shared/auth/auth_identity_store.dart';

class ReferralApi {
  ReferralApi._({
    required this.baseUrl,
    required this.mode,
    required this.latency,
    required this.client,
  });

  final String baseUrl;
  final GteBackendMode mode;
  final Duration latency;
  final GteAuthedApi client;

  factory ReferralApi.standard({
    required String baseUrl,
    GteBackendMode mode = GteBackendMode.live,
    String? accessToken,
    AuthSessionStore? authSessionStore,
    GteAuthedApi? client,
  }) {
    final GteBackendMode resolvedMode = gteProductionBackendMode(mode);
    return ReferralApi._(
      baseUrl: baseUrl,
      mode: resolvedMode,
      latency: const Duration(milliseconds: 180),
      client:
          client ??
          GteAuthedApi(
            config: GteRepositoryConfig(baseUrl: baseUrl, mode: resolvedMode),
            transport: GteHttpTransport(),
            accessToken: accessToken,
            authSessionStore: authSessionStore ?? SecureAuthSessionStore(),
            mode: resolvedMode,
          ),
    );
  }

  factory ReferralApi.fixture({
    String baseUrl = 'https://community.gte.local',
    Duration latency = Duration.zero,
  }) {
    return ReferralApi._(
      baseUrl: baseUrl,
      mode: GteBackendMode.fixture,
      latency: latency,
      client: GteAuthedApi(
        config: GteRepositoryConfig(
          baseUrl: baseUrl,
          mode: GteBackendMode.fixture,
        ),
        transport: GteHttpTransport(),
        accessToken: 'fixture-token',
        mode: GteBackendMode.fixture,
      ),
    );
  }

  Future<ReferralHubData> fetchReferralHub() async {
    await Future<void>.delayed(latency);
    return client.withFallback<ReferralHubData>(() async {
      final List<Object?> payload =
          await Future.wait<Object?>(<Future<Object?>>[
            client.getMap('/api/referrals/me/summary'),
            client.getList('/api/referrals/me/rewards'),
            client.getList('/api/referrals/me/invites'),
            client.getList('/api/referrals/share-codes/me'),
          ]);
      final Map<String, dynamic> summary = Map<String, dynamic>.from(
        payload[0] as Map<String, dynamic>,
      );
      final List<dynamic> rewards = payload[1] as List<dynamic>;
      final List<dynamic> invites = payload[2] as List<dynamic>;
      final List<dynamic> shareCodes = payload[3] as List<dynamic>;

      final Map<String, dynamic> shareCode = await _resolveShareCode(
        summary: summary,
        shareCodes: shareCodes,
      );
      final String code = (shareCode['code'] as String? ?? '').trim();
      final String vanity = (shareCode['vanity_code'] as String? ?? '').trim();
      final String creatorHandle =
          vanity.isNotEmpty ? '@$vanity' : '@${code.toLowerCase()}';

      return ReferralHubData(
        shareCode: code,
        shareUrl: '${_normalizedBase(baseUrl)}/community/invite/$code',
        creatorHandle: creatorHandle,
        welcomeTitle: 'Creator referral desk',
        welcomeDetail:
            'Track share-code performance, qualified joins, and community reward progress from live referral data.',
        summary: ReferralSummary(
          invitesSent: _intValue(summary['total_invites']),
          qualifiedReferrals: _intValue(summary['qualified_users']),
          inviteAttributions: _intValue(summary['total_signups']),
          rewardBalanceLabel:
              '${_intValue(summary['approved_rewards']) + _intValue(summary['paid_rewards'])} reward approvals',
          rewardDetail:
              '${_intValue(summary['pending_rewards'])} pending, ${_intValue(summary['blocked_rewards'])} blocked',
        ),
        milestones: _buildMilestones(summary),
        rewardHistory: rewards
            .whereType<Map<dynamic, dynamic>>()
            .map((Map<dynamic, dynamic> item) => _mapRewardEntry(item))
            .toList(growable: false),
        invites: invites
            .whereType<Map<dynamic, dynamic>>()
            .map((Map<dynamic, dynamic> item) => _mapInviteEntry(item))
            .toList(growable: false),
      );
    }, () async => _fixtureHub(baseUrl));
  }

  Future<ReferralAnalyticsSnapshot> fetchReferralAnalytics() async {
    await Future<void>.delayed(latency);
    return client.withFallback<ReferralAnalyticsSnapshot>(() async {
      final List<Object?> payload =
          await Future.wait<Object?>(<Future<Object?>>[
            client.getMap('/api/admin/referrals/dashboard'),
            client.getMap('/api/admin/referrals/analytics/summary'),
            client.getList('/api/admin/referrals/flags'),
            client.getList('/api/admin/referrals/creators'),
            client.getList('/api/admin/referrals/share-codes'),
          ]);
      final Map<String, dynamic> dashboard = Map<String, dynamic>.from(
        payload[0] as Map<String, dynamic>,
      );
      final Map<String, dynamic> summary = Map<String, dynamic>.from(
        payload[1] as Map<String, dynamic>,
      );
      final List<dynamic> flags = payload[2] as List<dynamic>;
      final List<dynamic> creators = payload[3] as List<dynamic>;
      final List<dynamic> shareCodes = payload[4] as List<dynamic>;

      final _ReferralAnalyticsContext analyticsContext = _buildAnalyticsContext(
        creators: creators,
        shareCodes: shareCodes,
      );

      final int attributedSignups = _intValue(summary['attributed_signups']);
      final int qualifiedReferrals = _intValue(summary['qualified_referrals']);
      final int retainedUsers = _intValue(summary['retained_users']);
      final int creatorCompetitionJoins = _intValue(
        summary['creator_competition_joins'],
      );
      final int pendingRewards = _intValue(summary['pending_rewards']);
      final int blockedRewards = _intValue(summary['blocked_rewards']);
      final int totalFlags = _intValue(dashboard['total_flags']);

      return ReferralAnalyticsSnapshot(
        growthHeadline:
            '$qualifiedReferrals qualified referrals across $attributedSignups attributed signups',
        growthDetail:
            '$creatorCompetitionJoins creator competition joins, $retainedUsers retained users, and $totalFlags active integrity flags are currently shaping referral quality.',
        activeShareCodes:
            '${_intValue(dashboard['active_share_codes'])} live / ${_intValue(dashboard['total_share_codes'])} total',
        qualifiedParticipationLabel:
            '$qualifiedReferrals qualified from $attributedSignups attributed signups',
        communityRewardReviewLabel:
            '$pendingRewards pending, $blockedRewards blocked',
        topChannelLabel: _topChannelLabel(summary['retention_by_source']),
        flags: flags
            .whereType<Map<dynamic, dynamic>>()
            .map(
              (Map<dynamic, dynamic> item) =>
                  _mapAnalyticsFlag(item, analyticsContext),
            )
            .toList(growable: false),
      );
    }, _fixtureAnalytics);
  }

  Future<Map<String, dynamic>> _resolveShareCode({
    required Map<String, dynamic> summary,
    required List<dynamic> shareCodes,
  }) async {
    final String preferredCode =
        (summary['default_share_code'] as String? ?? '').trim();
    for (final dynamic item in shareCodes) {
      if (item is! Map) {
        continue;
      }
      final Map<String, dynamic> shareCode = Map<String, dynamic>.from(item);
      if ((shareCode['code'] as String? ?? '').trim() == preferredCode &&
          preferredCode.isNotEmpty) {
        return shareCode;
      }
    }
    for (final dynamic item in shareCodes) {
      if (item is Map) {
        return Map<String, dynamic>.from(item);
      }
    }

    final Object? created = await client.post(
      '/api/referrals/share-codes',
      body: <String, Object?>{
        'share_code_type': 'creator_share',
        'use_as_default': true,
        'metadata': const <String, String>{'origin': 'referral_hub'},
      },
    );
    return Map<String, dynamic>.from(created as Map);
  }
}

ReferralHubData _fixtureHub(String baseUrl) {
  return ReferralHubData(
    shareCode: 'MAYA-GROWTH',
    shareUrl: '${_normalizedBase(baseUrl)}/community/invite/MAYA-GROWTH',
    creatorHandle: '@maya_scout',
    welcomeTitle: 'Invite friends into creator competitions',
    welcomeDetail:
        'Share your code, grow your circle, and unlock milestone rewards when invited managers join community contests and complete qualified participation.',
    summary: const ReferralSummary(
      invitesSent: 184,
      qualifiedReferrals: 72,
      inviteAttributions: 54,
      rewardBalanceLabel: '420 competition credits',
      rewardDetail: 'Reviewable community rewards and participation credits',
    ),
    milestones: const <MilestoneProgress>[
      MilestoneProgress(
        title: 'Welcome milestone',
        detail: 'First 10 qualified joins',
        currentValue: 10,
        targetValue: 10,
        rewardLabel: 'Unlocked welcome bonus',
        unlocked: true,
      ),
      MilestoneProgress(
        title: 'Contest participation milestone',
        detail: '50 invited managers enter a creator competition',
        currentValue: 41,
        targetValue: 50,
        rewardLabel: '120 competition entry credits',
        unlocked: false,
      ),
    ],
    rewardHistory: <RewardHistoryEntry>[
      RewardHistoryEntry(
        rewardId: 'fixture-reward-1',
        title: 'Welcome reward',
        detail: 'Your first qualified referral unlocked the onboarding reward.',
        category: ReferralRewardCategory.welcomeBonus,
        rewardLabel: '25 competition credits',
        issuedAt: DateTime.utc(2026, 2, 26),
        ledgerNote: 'Approved',
      ),
      RewardHistoryEntry(
        rewardId: 'fixture-reward-2',
        title: 'Qualified join reward',
        detail: 'Referral conversion milestone reached.',
        category: ReferralRewardCategory.participationCredit,
        rewardLabel: '40 competition credits',
        issuedAt: DateTime.utc(2026, 3, 1),
        ledgerNote: 'Approved',
      ),
      RewardHistoryEntry(
        rewardId: 'fixture-reward-3',
        title: 'Creator community reward',
        detail:
            'High-quality creator competition participation triggered the community reward review bonus.',
        category: ReferralRewardCategory.creatorCommunityReward,
        rewardLabel: '80 competition credits',
        issuedAt: DateTime.utc(2026, 3, 4),
        ledgerNote: 'Review cleared',
      ),
    ],
    invites: <ReferralInviteEntry>[
      ReferralInviteEntry(
        inviteeLabel: 'Manager invite',
        competitionLabel: 'Creator competition',
        channel: InviteChannel.copyLink,
        sentAt: DateTime.utc(2026, 3, 2),
        statusLabel: 'Qualified',
        inviteAttributionLabel: 'direct_link',
        isQualified: true,
      ),
    ],
  );
}

List<MilestoneProgress> _buildMilestones(Map<String, dynamic> summary) {
  final int shareCodes = _intValue(summary['generated_share_codes']);
  final int qualified = _intValue(summary['qualified_users']);
  final int activeParticipants = _intValue(summary['active_participants']);
  return <MilestoneProgress>[
    MilestoneProgress(
      title: 'Share code live',
      detail: 'Generate at least one active share code',
      currentValue: shareCodes,
      targetValue: 1,
      rewardLabel: 'Creator lane enabled',
      unlocked: shareCodes > 0,
    ),
    MilestoneProgress(
      title: 'Qualified joins',
      detail: 'Reach 10 qualified referred users',
      currentValue: qualified,
      targetValue: 10,
      rewardLabel: 'Creator milestone review',
      unlocked: qualified >= 10,
    ),
    MilestoneProgress(
      title: 'Active participants',
      detail: 'Convert 25 active participants through referrals',
      currentValue: activeParticipants,
      targetValue: 25,
      rewardLabel: 'Community growth unlock',
      unlocked: activeParticipants >= 25,
    ),
  ];
}

ReferralAnalyticsSnapshot _fixtureAnalytics() {
  return const ReferralAnalyticsSnapshot(
    growthHeadline: '72 qualified referrals across 184 attributed signups',
    growthDetail:
        '54 creator competition joins, 39 retained users, and 6 flagged patterns are shaping review pressure across the referral network.',
    activeShareCodes: '8 live / 10 total',
    qualifiedParticipationLabel: '72 qualified from 184 attributed signups',
    communityRewardReviewLabel: '5 pending, 2 blocked',
    topChannelLabel: 'Copy link - 96 signups',
    flags: <ReferralFlagEntry>[
      ReferralFlagEntry(
        flagId: 'fixture-flag-1',
        creatorHandle: '@maya_scout',
        shareCode: 'MAYA-GROWTH',
        issueLabel: 'High reward cost with weak participation quality',
        riskSignal:
            'Reward cost is climbing faster than qualified creator competition participation for this campaign.',
        reviewStatus: 'Open review',
        recommendedAction:
            'Freeze creator rewards until campaign quality improves.',
        qualifiedParticipationLabel: '9 qualified from 34 attributed signups',
        severity: ReferralRiskSeverity.high,
      ),
      ReferralFlagEntry(
        flagId: 'fixture-flag-2',
        creatorHandle: '@maya_scout',
        shareCode: 'MAYA-GROWTH',
        issueLabel: 'Rapid signup and join burst',
        riskSignal:
            'Multiple invite signups clustered into a short contest-join window and need chain review.',
        reviewStatus: 'Open review',
        recommendedAction:
            'Inspect the attribution chain before approving more rewards.',
        qualifiedParticipationLabel:
            '4 linked accounts inside the burst window',
        severity: ReferralRiskSeverity.medium,
      ),
    ],
  );
}

RewardHistoryEntry _mapRewardEntry(Map<dynamic, dynamic> raw) {
  final Map<String, dynamic> item = Map<String, dynamic>.from(raw);
  final String amountLabel = _rewardLabel(item);
  final String milestone = (item['trigger_milestone'] as String? ?? '').trim();
  return RewardHistoryEntry(
    rewardId: (item['reward_id'] as String? ?? '').trim(),
    title: (item['label'] as String? ?? 'Referral reward').trim(),
    detail:
        milestone.isEmpty
            ? 'Referral reward recorded from live community data.'
            : 'Triggered by ${milestone.replaceAll('_', ' ')}.',
    category: _rewardCategory(item['reward_type'] as String?),
    rewardLabel: amountLabel,
    issuedAt: _dateTimeValue(item['created_at']),
    ledgerNote:
        (item['status'] as String? ?? 'pending').replaceAll('_', ' ').trim(),
  );
}

ReferralInviteEntry _mapInviteEntry(Map<dynamic, dynamic> raw) {
  final Map<String, dynamic> item = Map<String, dynamic>.from(raw);
  final List<String> milestones = (item['milestones'] as List<dynamic>? ??
          const <dynamic>[])
      .map((dynamic value) => value.toString())
      .toList(growable: false);
  final String referredUserId =
      (item['referred_user_id'] as String? ?? 'invitee').trim();
  final String linkedCompetitionId =
      (item['linked_competition_id'] as String? ?? '').trim();
  final String status =
      (item['attribution_status'] as String? ?? 'pending').trim();
  return ReferralInviteEntry(
    inviteeLabel:
        'User ${referredUserId.length > 6 ? referredUserId.substring(0, 6) : referredUserId}',
    competitionLabel:
        linkedCompetitionId.isEmpty
            ? 'Community referral'
            : linkedCompetitionId,
    channel: _inviteChannel(item['source_channel'] as String?),
    sentAt: _dateTimeValue(item['first_touched_at']),
    statusLabel: status.replaceAll('_', ' '),
    inviteAttributionLabel: (item['source_channel'] as String? ?? 'direct_link')
        .replaceAll('_', ' '),
    isQualified:
        status == 'qualified' ||
        milestones.contains('first_creator_competition_joined') ||
        milestones.contains('first_competition_joined'),
  );
}

ReferralFlagEntry _mapAnalyticsFlag(
  Map<dynamic, dynamic> raw,
  _ReferralAnalyticsContext context,
) {
  final Map<String, dynamic> item = Map<String, dynamic>.from(raw);
  final Map<String, dynamic> evidence =
      item['evidence'] is Map
          ? Map<String, dynamic>.from(item['evidence'] as Map)
          : const <String, dynamic>{};
  final String flagId = (item['flag_id'] as String? ?? '').trim();
  final String entityType = (item['entity_type'] as String? ?? '').trim();
  final String entityId = (item['entity_id'] as String? ?? '').trim();
  final String shareCode = _flagShareCode(
    flagId: flagId,
    entityType: entityType,
    entityId: entityId,
    evidence: evidence,
    context: context,
  );
  final String creatorHandle = _flagCreatorHandle(
    flagId: flagId,
    entityType: entityType,
    entityId: entityId,
    evidence: evidence,
    context: context,
  );

  return ReferralFlagEntry(
    flagId: flagId,
    creatorHandle: creatorHandle,
    shareCode: shareCode,
    issueLabel: (item['title'] as String? ?? 'Referral integrity flag').trim(),
    riskSignal:
        (item['description'] as String? ??
                'Referral activity needs manual review before further rewards are approved.')
            .trim(),
    reviewStatus: 'Open review',
    recommendedAction: _recommendedActionLabel(
      item['recommended_action'] as String?,
    ),
    qualifiedParticipationLabel: _flagParticipationLabel(
      flagId: flagId,
      entityType: entityType,
      entityId: entityId,
      evidence: evidence,
      context: context,
    ),
    severity: _riskSeverity(item['severity'] as String?),
  );
}

_ReferralAnalyticsContext _buildAnalyticsContext({
  required List<dynamic> creators,
  required List<dynamic> shareCodes,
}) {
  final Map<String, String> creatorHandleById = <String, String>{};
  final Map<String, String> creatorParticipationById = <String, String>{};
  final Map<String, String> shareCodeLabelById = <String, String>{};
  final Map<String, String> shareCodeOwnerCreatorById = <String, String>{};
  final Map<String, String> shareCodeParticipationById = <String, String>{};
  final Map<String, String> flagCreatorHandleById = <String, String>{};
  final Map<String, String> flagShareCodeById = <String, String>{};
  final Map<String, String> flagParticipationById = <String, String>{};

  for (final dynamic rawCreator in creators) {
    if (rawCreator is! Map) {
      continue;
    }
    final Map<String, dynamic> creator = Map<String, dynamic>.from(rawCreator);
    final String creatorId = (creator['creator_id'] as String? ?? '').trim();
    if (creatorId.isEmpty) {
      continue;
    }
    final String creatorHandle = _normalizedCreatorHandle(
      creator['handle'] as String?,
      fallbackId: creatorId,
    );
    creatorHandleById[creatorId] = creatorHandle;
    creatorParticipationById[creatorId] = _qualifiedRatioLabel(
      qualified: _intValue(creator['qualified_participants']),
      total: _intValue(creator['attributed_signups']),
    );
    final List<dynamic> creatorFlags =
        creator['flags'] as List<dynamic>? ?? const <dynamic>[];
    for (final dynamic rawFlag in creatorFlags) {
      if (rawFlag is! Map) {
        continue;
      }
      final String flagId = (rawFlag['flag_id'] as String? ?? '').trim();
      if (flagId.isEmpty) {
        continue;
      }
      flagCreatorHandleById[flagId] = creatorHandle;
      flagParticipationById[flagId] = creatorParticipationById[creatorId]!;
    }
  }

  for (final dynamic rawShareCode in shareCodes) {
    if (rawShareCode is! Map) {
      continue;
    }
    final Map<String, dynamic> shareCode = Map<String, dynamic>.from(
      rawShareCode,
    );
    final String shareCodeId = (shareCode['code_id'] as String? ?? '').trim();
    if (shareCodeId.isEmpty) {
      continue;
    }
    final String shareCodeLabel = (shareCode['code'] as String? ?? '').trim();
    shareCodeLabelById[shareCodeId] =
        shareCodeLabel.isEmpty
            ? 'Code ${_shortId(shareCodeId)}'
            : shareCodeLabel;
    final String ownerCreatorId =
        (shareCode['owner_creator_id'] as String? ?? '').trim();
    if (ownerCreatorId.isNotEmpty) {
      shareCodeOwnerCreatorById[shareCodeId] = ownerCreatorId;
    }
    shareCodeParticipationById[shareCodeId] = _qualifiedRatioLabel(
      qualified: _intValue(shareCode['qualified_referrals']),
      total: _intValue(shareCode['attributed_signups']),
    );
    final List<dynamic> shareCodeFlags =
        shareCode['flags'] as List<dynamic>? ?? const <dynamic>[];
    for (final dynamic rawFlag in shareCodeFlags) {
      if (rawFlag is! Map) {
        continue;
      }
      final String flagId = (rawFlag['flag_id'] as String? ?? '').trim();
      if (flagId.isEmpty) {
        continue;
      }
      flagShareCodeById[flagId] = shareCodeLabelById[shareCodeId]!;
      flagParticipationById[flagId] = shareCodeParticipationById[shareCodeId]!;
      if (ownerCreatorId.isNotEmpty) {
        flagCreatorHandleById[flagId] =
            creatorHandleById[ownerCreatorId] ??
            'Creator ${_shortId(ownerCreatorId)}';
      }
    }
  }

  return _ReferralAnalyticsContext(
    creatorHandleById: creatorHandleById,
    creatorParticipationById: creatorParticipationById,
    shareCodeLabelById: shareCodeLabelById,
    shareCodeOwnerCreatorById: shareCodeOwnerCreatorById,
    shareCodeParticipationById: shareCodeParticipationById,
    flagCreatorHandleById: flagCreatorHandleById,
    flagShareCodeById: flagShareCodeById,
    flagParticipationById: flagParticipationById,
  );
}

String _flagCreatorHandle({
  required String flagId,
  required String entityType,
  required String entityId,
  required Map<String, dynamic> evidence,
  required _ReferralAnalyticsContext context,
}) {
  final String mapped = context.flagCreatorHandleById[flagId] ?? '';
  if (mapped.isNotEmpty) {
    return mapped;
  }
  final String creatorId = _stringValue(evidence['creator_id']);
  if (creatorId.isNotEmpty) {
    return context.creatorHandleById[creatorId] ??
        'Creator ${_shortId(creatorId)}';
  }
  if (entityType == 'creator_profile') {
    return context.creatorHandleById[entityId] ??
        'Creator ${_shortId(entityId)}';
  }
  if (entityType == 'share_code') {
    final String ownerCreatorId =
        context.shareCodeOwnerCreatorById[entityId] ?? '';
    if (ownerCreatorId.isNotEmpty) {
      return context.creatorHandleById[ownerCreatorId] ??
          'Creator ${_shortId(ownerCreatorId)}';
    }
  }
  return 'Referral review';
}

String _flagShareCode({
  required String flagId,
  required String entityType,
  required String entityId,
  required Map<String, dynamic> evidence,
  required _ReferralAnalyticsContext context,
}) {
  final String mapped = context.flagShareCodeById[flagId] ?? '';
  if (mapped.isNotEmpty) {
    return mapped;
  }
  final String evidenceShareCode = _stringValue(evidence['share_code']);
  if (evidenceShareCode.isNotEmpty) {
    return evidenceShareCode;
  }
  if (entityType == 'share_code') {
    return context.shareCodeLabelById[entityId] ?? 'Code ${_shortId(entityId)}';
  }
  return 'Shared invite';
}

String _flagParticipationLabel({
  required String flagId,
  required String entityType,
  required String entityId,
  required Map<String, dynamic> evidence,
  required _ReferralAnalyticsContext context,
}) {
  final String mapped = context.flagParticipationById[flagId] ?? '';
  if (mapped.isNotEmpty) {
    return mapped;
  }
  if (entityType == 'creator_profile') {
    final String creatorParticipation =
        context.creatorParticipationById[entityId] ?? '';
    if (creatorParticipation.isNotEmpty) {
      return creatorParticipation;
    }
  }
  if (entityType == 'share_code') {
    final String shareCodeParticipation =
        context.shareCodeParticipationById[entityId] ?? '';
    if (shareCodeParticipation.isNotEmpty) {
      return shareCodeParticipation;
    }
  }
  return _flagEvidenceLabel(evidence);
}

String _flagEvidenceLabel(Map<String, dynamic> evidence) {
  final int blockedAttempts = _intValue(evidence['blocked_attempts']);
  if (blockedAttempts > 0) {
    return '$blockedAttempts blocked self-referral attempts';
  }
  final int blockedRewards = _intValue(evidence['blocked_rewards']);
  if (blockedRewards > 0) {
    return '$blockedRewards blocked rewards require review';
  }
  final int clusterSize = _intValue(evidence['cluster_size']);
  if (clusterSize > 0) {
    return '$clusterSize linked accounts inside the flagged cluster';
  }
  final int attributedSignups = _intValue(evidence['attributed_signups']);
  final String usageShare = _fractionPercentLabel(evidence['usage_share']);
  if (usageShare.isNotEmpty && attributedSignups > 0) {
    return '$usageShare of referral signups came through $attributedSignups attributed joins';
  }
  final String qualityRate = _fractionPercentLabel(evidence['quality_rate']);
  final String rewardCost = _stringValue(evidence['reward_cost']);
  if (qualityRate.isNotEmpty && rewardCost.isNotEmpty) {
    return '$qualityRate qualified participation at reward cost $rewardCost';
  }
  final String retentionRate = _fractionPercentLabel(
    evidence['retention_rate'],
  );
  if (retentionRate.isNotEmpty && attributedSignups > 0) {
    return '$retentionRate retention across $attributedSignups attributed signups';
  }
  final String attributionId = _stringValue(evidence['attribution_id']);
  if (attributionId.isNotEmpty) {
    return 'Attribution ${_shortId(attributionId)} requires review';
  }
  return 'Referral participation requires manual review';
}

String _recommendedActionLabel(String? raw) {
  final String action = (raw ?? '').trim();
  if (action.isEmpty) {
    return 'Review this referral pattern before approving more rewards.';
  }
  switch (action) {
    case 'block_reward_review':
      return 'Block reward approval until the attribution chain is reviewed.';
    case 'inspect_share_code':
      return 'Inspect the share code and its traffic pattern before further promotion.';
    case 'disable_share_code':
      return 'Disable the share code until the referral pattern is cleared.';
    case 'review_campaign_quality':
      return 'Review campaign quality before allowing more referral scaling.';
    case 'freeze_creator_rewards':
      return 'Freeze creator rewards until participation quality improves.';
    case 'inspect_attribution_chain':
      return 'Inspect the attribution chain before approving more rewards.';
    default:
      return '${_humanizeToken(action)}.';
  }
}

ReferralRiskSeverity _riskSeverity(String? raw) {
  switch ((raw ?? '').trim()) {
    case 'high':
      return ReferralRiskSeverity.high;
    case 'medium':
      return ReferralRiskSeverity.medium;
    default:
      return ReferralRiskSeverity.low;
  }
}

String _topChannelLabel(Object? rawRetentionBySource) {
  final List<dynamic> retentionBySource =
      rawRetentionBySource as List<dynamic>? ?? const <dynamic>[];
  Map<String, dynamic>? topSource;
  for (final dynamic rawItem in retentionBySource) {
    if (rawItem is! Map) {
      continue;
    }
    final Map<String, dynamic> item = Map<String, dynamic>.from(rawItem);
    if (topSource == null ||
        _intValue(item['signups']) > _intValue(topSource['signups'])) {
      topSource = item;
    }
  }
  if (topSource == null) {
    return 'No live source data';
  }
  final String source = _humanizeToken(topSource['source_channel'] as String?);
  final int signups = _intValue(topSource['signups']);
  return '$source - $signups signups';
}

String _qualifiedRatioLabel({required int qualified, required int total}) {
  return '$qualified qualified from $total attributed signups';
}

String _fractionPercentLabel(Object? raw) {
  final double? fraction = double.tryParse(_stringValue(raw));
  if (fraction == null) {
    return '';
  }
  final double percent = fraction * 100;
  if (percent == percent.roundToDouble()) {
    return '${percent.toStringAsFixed(0)}%';
  }
  return '${percent.toStringAsFixed(1)}%';
}

String _normalizedCreatorHandle(
  String? rawHandle, {
  required String fallbackId,
}) {
  final String handle = (rawHandle ?? '').trim();
  if (handle.isNotEmpty) {
    return handle.startsWith('@') ? handle : '@$handle';
  }
  return 'Creator ${_shortId(fallbackId)}';
}

String _humanizeToken(String? raw) {
  final String token = (raw ?? '').trim();
  if (token.isEmpty) {
    return 'Unknown';
  }
  final List<String> words = token
      .replaceAll('-', '_')
      .split('_')
      .where((String word) => word.trim().isNotEmpty)
      .map((String word) => word.trim())
      .toList(growable: false);
  if (words.isEmpty) {
    return token;
  }
  return words
      .map(
        (String word) =>
            '${word[0].toUpperCase()}${word.length > 1 ? word.substring(1) : ''}',
      )
      .join(' ');
}

String _stringValue(Object? value) => value?.toString().trim() ?? '';

String _shortId(String value) {
  final String trimmed = value.trim();
  if (trimmed.length <= 8) {
    return trimmed;
  }
  return trimmed.substring(0, 8);
}

String _rewardLabel(Map<String, dynamic> item) {
  final Object? amount = item['amount'];
  final String unit = (item['unit'] as String? ?? '').trim();
  if (amount == null) {
    return (item['label'] as String? ?? 'Referral reward').trim();
  }
  return unit.isEmpty ? '$amount' : '$amount $unit';
}

ReferralRewardCategory _rewardCategory(String? rawType) {
  switch ((rawType ?? '').trim()) {
    case 'welcome_bonus':
      return ReferralRewardCategory.welcomeBonus;
    case 'badge_unlock':
      return ReferralRewardCategory.badgeUnlock;
    case 'creator_reward':
    case 'creator_share_reward':
      return ReferralRewardCategory.creatorCommunityReward;
    case 'milestone_reward':
      return ReferralRewardCategory.milestoneReward;
    default:
      return ReferralRewardCategory.participationCredit;
  }
}

InviteChannel _inviteChannel(String? rawChannel) {
  switch ((rawChannel ?? '').trim()) {
    case 'dm':
      return InviteChannel.systemShare;
    case 'community_post':
    case 'community_invite':
      return InviteChannel.telegram;
    case 'direct_share':
      return InviteChannel.copyCode;
    default:
      return InviteChannel.copyLink;
  }
}

int _intValue(Object? value) {
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  return int.tryParse(value?.toString() ?? '') ?? 0;
}

DateTime _dateTimeValue(Object? value) {
  if (value is DateTime) {
    return value.toUtc();
  }
  return DateTime.tryParse(value?.toString() ?? '')?.toUtc() ??
      DateTime.fromMillisecondsSinceEpoch(0, isUtc: true);
}

class _ReferralAnalyticsContext {
  const _ReferralAnalyticsContext({
    required this.creatorHandleById,
    required this.creatorParticipationById,
    required this.shareCodeLabelById,
    required this.shareCodeOwnerCreatorById,
    required this.shareCodeParticipationById,
    required this.flagCreatorHandleById,
    required this.flagShareCodeById,
    required this.flagParticipationById,
  });

  final Map<String, String> creatorHandleById;
  final Map<String, String> creatorParticipationById;
  final Map<String, String> shareCodeLabelById;
  final Map<String, String> shareCodeOwnerCreatorById;
  final Map<String, String> shareCodeParticipationById;
  final Map<String, String> flagCreatorHandleById;
  final Map<String, String> flagShareCodeById;
  final Map<String, String> flagParticipationById;
}

String _normalizedBase(String baseUrl) {
  final String trimmed = baseUrl.trim();
  if (trimmed.endsWith('/')) {
    return trimmed.substring(0, trimmed.length - 1);
  }
  return trimmed;
}
