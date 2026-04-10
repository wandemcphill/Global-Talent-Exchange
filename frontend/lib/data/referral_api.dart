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
    GteBackendMode mode = GteBackendMode.liveThenFixture,
    String? accessToken,
    AuthSessionStore? authSessionStore,
  }) {
    return ReferralApi._(
      baseUrl: baseUrl,
      mode: mode,
      latency: const Duration(milliseconds: 180),
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: mode),
        transport: GteHttpTransport(),
        accessToken: accessToken,
        authSessionStore: authSessionStore ?? SecureAuthSessionStore(),
        mode: mode,
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
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: GteBackendMode.fixture),
        transport: GteHttpTransport(),
        accessToken: 'fixture-token',
        mode: GteBackendMode.fixture,
      ),
    );
  }

  Future<ReferralHubData> fetchReferralHub() async {
    await Future<void>.delayed(latency);
    return client.withFallback<ReferralHubData>(
      () async {
        final List<Object?> payload = await Future.wait<Object?>(<Future<Object?>>[
          client.getMap('/api/referrals/me/summary'),
          client.getList('/api/referrals/me/rewards'),
          client.getList('/api/referrals/me/invites'),
          client.getList('/api/referrals/share-codes/me'),
        ]);
        final Map<String, dynamic> summary =
            Map<String, dynamic>.from(payload[0] as Map<String, dynamic>);
        final List<dynamic> rewards = payload[1] as List<dynamic>;
        final List<dynamic> invites = payload[2] as List<dynamic>;
        final List<dynamic> shareCodes = payload[3] as List<dynamic>;

        final Map<String, dynamic> shareCode =
            await _resolveShareCode(summary: summary, shareCodes: shareCodes);
        final String code = (shareCode['code'] as String? ?? '').trim();
        final String vanity = (shareCode['vanity_code'] as String? ?? '').trim();
        final String creatorHandle = vanity.isNotEmpty
            ? '@$vanity'
            : '@${code.toLowerCase()}';

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
      },
      () async => _fixtureHub(baseUrl),
    );
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
    rewardHistory: const <RewardHistoryEntry>[
      RewardHistoryEntry(
        rewardId: 'fixture-reward-1',
        title: 'Qualified join reward',
        detail: 'Referral conversion milestone reached.',
        category: ReferralRewardCategory.participationCredit,
        rewardLabel: '40 competition credits',
        issuedAt: DateTime.utc(2026, 3, 1),
        ledgerNote: 'Approved',
      ),
    ],
    invites: const <ReferralInviteEntry>[
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

RewardHistoryEntry _mapRewardEntry(Map<dynamic, dynamic> raw) {
  final Map<String, dynamic> item = Map<String, dynamic>.from(raw);
  final String amountLabel = _rewardLabel(item);
  final String milestone = (item['trigger_milestone'] as String? ?? '').trim();
  return RewardHistoryEntry(
    rewardId: (item['reward_id'] as String? ?? '').trim(),
    title: (item['label'] as String? ?? 'Referral reward').trim(),
    detail: milestone.isEmpty
        ? 'Referral reward recorded from live community data.'
        : 'Triggered by ${milestone.replaceAll('_', ' ')}.',
    category: _rewardCategory(item['reward_type'] as String?),
    rewardLabel: amountLabel,
    issuedAt: _dateTimeValue(item['created_at']),
    ledgerNote: (item['status'] as String? ?? 'pending')
        .replaceAll('_', ' ')
        .trim(),
  );
}

ReferralInviteEntry _mapInviteEntry(Map<dynamic, dynamic> raw) {
  final Map<String, dynamic> item = Map<String, dynamic>.from(raw);
  final List<String> milestones = (item['milestones'] as List<dynamic>? ?? const <dynamic>[])
      .map((dynamic value) => value.toString())
      .toList(growable: false);
  final String referredUserId =
      (item['referred_user_id'] as String? ?? 'invitee').trim();
  final String linkedCompetitionId =
      (item['linked_competition_id'] as String? ?? '').trim();
  final String status = (item['attribution_status'] as String? ?? 'pending').trim();
  return ReferralInviteEntry(
    inviteeLabel: 'User ${referredUserId.length > 6 ? referredUserId.substring(0, 6) : referredUserId}',
    competitionLabel:
        linkedCompetitionId.isEmpty ? 'Community referral' : linkedCompetitionId,
    channel: _inviteChannel(item['source_channel'] as String?),
    sentAt: _dateTimeValue(item['first_touched_at']),
    statusLabel: status.replaceAll('_', ' '),
    inviteAttributionLabel: (item['source_channel'] as String? ?? 'direct_link')
        .replaceAll('_', ' '),
    isQualified: status == 'qualified' ||
        milestones.contains('first_creator_competition_joined') ||
        milestones.contains('first_competition_joined'),
  );
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

String _normalizedBase(String baseUrl) {
  final String trimmed = baseUrl.trim();
  if (trimmed.endsWith('/')) {
    return trimmed.substring(0, trimmed.length - 1);
  }
  return trimmed;
}
