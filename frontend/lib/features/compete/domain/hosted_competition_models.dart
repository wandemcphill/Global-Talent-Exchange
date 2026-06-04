import 'package:gte_frontend/data/gte_models.dart';

class HostedCompetitionTemplate {
  const HostedCompetitionTemplate({
    required this.id,
    required this.templateKey,
    required this.title,
    required this.description,
    required this.competitionType,
    required this.teamType,
    required this.ageGrade,
    required this.cupOrLeague,
    required this.participants,
    required this.viewingMode,
    required this.giftRules,
    required this.seedingMethod,
    required this.isUserHostable,
    required this.entryFeeFancoin,
    required this.rewardPoolFancoin,
    required this.platformFeeBps,
    required this.metadata,
    required this.active,
  });

  final String id;
  final String templateKey;
  final String title;
  final String description;
  final String competitionType;
  final String teamType;
  final String ageGrade;
  final String cupOrLeague;
  final int participants;
  final String viewingMode;
  final Map<String, Object?> giftRules;
  final String seedingMethod;
  final bool isUserHostable;
  final double entryFeeFancoin;
  final double rewardPoolFancoin;
  final int platformFeeBps;
  final Map<String, Object?> metadata;
  final bool active;

  factory HostedCompetitionTemplate.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'hosted template',
    );
    return HostedCompetitionTemplate(
      id: GteJson.string(json, <String>['id']),
      templateKey: GteJson.string(json, <String>[
        'template_key',
        'templateKey',
      ]),
      title: GteJson.string(json, <String>['title']),
      description: GteJson.string(json, <String>['description'], fallback: ''),
      competitionType: GteJson.string(json, <String>[
        'competition_type',
        'competitionType',
      ], fallback: 'general'),
      teamType: GteJson.string(json, <String>[
        'team_type',
        'teamType',
      ], fallback: 'club'),
      ageGrade: GteJson.string(json, <String>[
        'age_grade',
        'ageGrade',
      ], fallback: 'senior'),
      cupOrLeague: GteJson.string(json, <String>[
        'cup_or_league',
        'cupOrLeague',
      ], fallback: 'cup'),
      participants: GteJson.integer(json, <String>[
        'participants',
      ], fallback: 0),
      viewingMode: GteJson.string(json, <String>[
        'viewing_mode',
        'viewingMode',
      ], fallback: 'standard'),
      giftRules: GteJson.map(
        json,
        keys: <String>['gift_rules', 'giftRules'],
        fallback: const <String, Object?>{},
      ),
      seedingMethod: GteJson.string(json, <String>[
        'seeding_method',
        'seedingMethod',
      ], fallback: 'balanced'),
      isUserHostable: GteJson.boolean(json, <String>[
        'is_user_hostable',
        'isUserHostable',
      ], fallback: false),
      entryFeeFancoin: GteJson.number(json, <String>[
        'entry_fee_fancoin',
        'entryFeeFancoin',
      ], fallback: 0),
      rewardPoolFancoin: GteJson.number(json, <String>[
        'reward_pool_fancoin',
        'rewardPoolFancoin',
      ], fallback: 0),
      platformFeeBps: GteJson.integer(json, <String>[
        'platform_fee_bps',
        'platformFeeBps',
      ], fallback: 0),
      metadata: GteJson.map(
        json,
        keys: <String>['metadata_json', 'metadataJson', 'metadata'],
        fallback: const <String, Object?>{},
      ),
      active: GteJson.boolean(json, <String>['active'], fallback: true),
    );
  }
}

class HostedCompetition {
  const HostedCompetition({
    required this.id,
    required this.templateId,
    required this.hostUserId,
    required this.title,
    required this.slug,
    required this.description,
    required this.status,
    required this.visibility,
    required this.startsAt,
    required this.lockAt,
    required this.maxParticipants,
    required this.entryFeeFancoin,
    required this.rewardPoolFancoin,
    required this.platformFeeAmount,
    required this.metadata,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String templateId;
  final String hostUserId;
  final String title;
  final String slug;
  final String description;
  final String status;
  final String visibility;
  final DateTime? startsAt;
  final DateTime? lockAt;
  final int maxParticipants;
  final double entryFeeFancoin;
  final double rewardPoolFancoin;
  final double platformFeeAmount;
  final Map<String, Object?> metadata;
  final DateTime createdAt;
  final DateTime updatedAt;

  bool get isGtexHosted {
    final Object? hostType = metadata['host_type'];
    return GteJson.boolean(metadata, <String>[
          'gtex_hosted',
          'gtexHosted',
        ], fallback: false) ||
        hostType?.toString().trim().toLowerCase() == 'gtex_hosted';
  }

  bool get requiresPasscode {
    if (GteJson.boolean(metadata, <String>[
      'join_passcode_required',
      'requires_passcode',
    ], fallback: false)) {
      return true;
    }
    return visibility.trim().toLowerCase() == 'passcode';
  }

  factory HostedCompetition.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'hosted competition',
    );
    return HostedCompetition(
      id: GteJson.string(json, <String>['id']),
      templateId: GteJson.string(json, <String>['template_id', 'templateId']),
      hostUserId: GteJson.string(json, <String>['host_user_id', 'hostUserId']),
      title: GteJson.string(json, <String>['title']),
      slug: GteJson.string(json, <String>['slug'], fallback: ''),
      description: GteJson.string(json, <String>['description'], fallback: ''),
      status: GteJson.string(json, <String>['status'], fallback: 'draft'),
      visibility: GteJson.string(json, <String>[
        'visibility',
      ], fallback: 'public'),
      startsAt: GteJson.dateTimeOrNull(json, <String>['starts_at', 'startsAt']),
      lockAt: GteJson.dateTimeOrNull(json, <String>['lock_at', 'lockAt']),
      maxParticipants: GteJson.integer(json, <String>[
        'max_participants',
        'maxParticipants',
      ], fallback: 0),
      entryFeeFancoin: GteJson.number(json, <String>[
        'entry_fee_fancoin',
        'entryFeeFancoin',
      ], fallback: 0),
      rewardPoolFancoin: GteJson.number(json, <String>[
        'reward_pool_fancoin',
        'rewardPoolFancoin',
      ], fallback: 0),
      platformFeeAmount: GteJson.number(json, <String>[
        'platform_fee_amount',
        'platformFeeAmount',
      ], fallback: 0),
      metadata: GteJson.map(
        json,
        keys: <String>['metadata_json', 'metadataJson', 'metadata'],
        fallback: const <String, Object?>{},
      ),
      createdAt: GteJson.dateTime(json, <String>['created_at', 'createdAt']),
      updatedAt: GteJson.dateTime(json, <String>['updated_at', 'updatedAt']),
    );
  }
}

class HostedCompetitionParticipant {
  const HostedCompetitionParticipant({
    required this.id,
    required this.competitionId,
    required this.userId,
    required this.joinedAt,
    required this.entryFeeFancoin,
    required this.payoutEligible,
    required this.metadata,
  });

  final String id;
  final String competitionId;
  final String userId;
  final DateTime joinedAt;
  final double entryFeeFancoin;
  final bool payoutEligible;
  final Map<String, Object?> metadata;

  factory HostedCompetitionParticipant.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'hosted participant',
    );
    return HostedCompetitionParticipant(
      id: GteJson.string(json, <String>['id']),
      competitionId: GteJson.string(json, <String>[
        'competition_id',
        'competitionId',
      ]),
      userId: GteJson.string(json, <String>['user_id', 'userId']),
      joinedAt: GteJson.dateTime(json, <String>['joined_at', 'joinedAt']),
      entryFeeFancoin: GteJson.number(json, <String>[
        'entry_fee_fancoin',
        'entryFeeFancoin',
      ], fallback: 0),
      payoutEligible: GteJson.boolean(json, <String>[
        'payout_eligible',
        'payoutEligible',
      ], fallback: false),
      metadata: GteJson.map(
        json,
        keys: <String>['metadata_json', 'metadataJson', 'metadata'],
        fallback: const <String, Object?>{},
      ),
    );
  }
}

class HostedCompetitionInvite {
  const HostedCompetitionInvite({
    required this.competitionId,
    required this.inviteId,
    required this.invitedByUserId,
    required this.recipientUserId,
    required this.recipientEmail,
    required this.status,
    required this.message,
    required this.createdAt,
    required this.respondedAt,
  });

  final String competitionId;
  final String inviteId;
  final String invitedByUserId;
  final String? recipientUserId;
  final String? recipientEmail;
  final String status;
  final String message;
  final DateTime createdAt;
  final DateTime? respondedAt;

  bool get isPending => status.toLowerCase() == 'pending';

  factory HostedCompetitionInvite.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'hosted invite',
    );
    return HostedCompetitionInvite(
      competitionId: GteJson.string(json, <String>[
        'competition_id',
        'competitionId',
      ]),
      inviteId: GteJson.string(json, <String>['invite_id', 'inviteId']),
      invitedByUserId: GteJson.string(json, <String>[
        'invited_by_user_id',
        'invitedByUserId',
      ]),
      recipientUserId: GteJson.stringOrNull(json, <String>[
        'recipient_user_id',
        'recipientUserId',
      ]),
      recipientEmail: GteJson.stringOrNull(json, <String>[
        'recipient_email',
        'recipientEmail',
      ]),
      status: GteJson.string(json, <String>['status'], fallback: 'pending'),
      message: GteJson.string(json, <String>['message'], fallback: ''),
      createdAt: GteJson.dateTime(json, <String>['created_at', 'createdAt']),
      respondedAt: GteJson.dateTimeOrNull(json, <String>[
        'responded_at',
        'respondedAt',
      ]),
    );
  }
}

class HostedCompetitionStanding {
  const HostedCompetitionStanding({
    required this.id,
    required this.competitionId,
    required this.userId,
    required this.finalRank,
    required this.points,
    required this.wins,
    required this.draws,
    required this.losses,
    required this.goalsFor,
    required this.goalsAgainst,
    required this.payoutAmount,
    required this.metadata,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String competitionId;
  final String userId;
  final int? finalRank;
  final int points;
  final int wins;
  final int draws;
  final int losses;
  final int goalsFor;
  final int goalsAgainst;
  final double payoutAmount;
  final Map<String, Object?> metadata;
  final DateTime createdAt;
  final DateTime updatedAt;

  factory HostedCompetitionStanding.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'hosted standing',
    );
    return HostedCompetitionStanding(
      id: GteJson.string(json, <String>['id']),
      competitionId: GteJson.string(json, <String>[
        'competition_id',
        'competitionId',
      ]),
      userId: GteJson.string(json, <String>['user_id', 'userId']),
      finalRank: GteJson.integerOrNull(json, <String>[
        'final_rank',
        'finalRank',
      ]),
      points: GteJson.integer(json, <String>['points'], fallback: 0),
      wins: GteJson.integer(json, <String>['wins'], fallback: 0),
      draws: GteJson.integer(json, <String>['draws'], fallback: 0),
      losses: GteJson.integer(json, <String>['losses'], fallback: 0),
      goalsFor: GteJson.integer(json, <String>[
        'goals_for',
        'goalsFor',
      ], fallback: 0),
      goalsAgainst: GteJson.integer(json, <String>[
        'goals_against',
        'goalsAgainst',
      ], fallback: 0),
      payoutAmount: GteJson.number(json, <String>[
        'payout_amount',
        'payoutAmount',
      ], fallback: 0),
      metadata: GteJson.map(
        json,
        keys: <String>['metadata_json', 'metadataJson', 'metadata'],
        fallback: const <String, Object?>{},
      ),
      createdAt: GteJson.dateTime(json, <String>['created_at', 'createdAt']),
      updatedAt: GteJson.dateTime(json, <String>['updated_at', 'updatedAt']),
    );
  }
}

class HostedCompetitionFinance {
  const HostedCompetitionFinance({
    required this.currency,
    required this.participantCount,
    required this.entryFeeFancoin,
    required this.grossCollected,
    required this.projectedRewardPool,
    required this.projectedPlatformFee,
    required this.escrowBalance,
    required this.settledPrizes,
    required this.settledPlatformFee,
    required this.status,
    required this.settlementReadiness,
  });

  final String currency;
  final int participantCount;
  final double entryFeeFancoin;
  final double grossCollected;
  final double projectedRewardPool;
  final double projectedPlatformFee;
  final double escrowBalance;
  final double settledPrizes;
  final double settledPlatformFee;
  final String status;
  final HostedSettlementReadiness settlementReadiness;

  factory HostedCompetitionFinance.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'hosted finance',
    );
    return HostedCompetitionFinance(
      currency: GteJson.string(json, <String>['currency'], fallback: 'FAN'),
      participantCount: GteJson.integer(json, <String>[
        'participant_count',
        'participantCount',
      ], fallback: 0),
      entryFeeFancoin: GteJson.number(json, <String>[
        'entry_fee_fancoin',
        'entryFeeFancoin',
      ], fallback: 0),
      grossCollected: GteJson.number(json, <String>[
        'gross_collected',
        'grossCollected',
      ], fallback: 0),
      projectedRewardPool: GteJson.number(json, <String>[
        'projected_reward_pool',
        'projectedRewardPool',
      ], fallback: 0),
      projectedPlatformFee: GteJson.number(json, <String>[
        'projected_platform_fee',
        'projectedPlatformFee',
      ], fallback: 0),
      escrowBalance: GteJson.number(json, <String>[
        'escrow_balance',
        'escrowBalance',
      ], fallback: 0),
      settledPrizes: GteJson.number(json, <String>[
        'settled_prizes',
        'settledPrizes',
      ], fallback: 0),
      settledPlatformFee: GteJson.number(json, <String>[
        'settled_platform_fee',
        'settledPlatformFee',
      ], fallback: 0),
      status: GteJson.string(json, <String>['status'], fallback: 'draft'),
      settlementReadiness: HostedSettlementReadiness.fromJson(
        GteJson.value(json, <String>[
          'settlement_readiness',
          'settlementReadiness',
          'readiness',
        ]),
      ),
    );
  }
}

enum HostedSettlementReadinessStatus {
  unknown,
  syncing,
  ready,
  blocked,
  degraded,
  settled,
}

class HostedSettlementReadiness {
  const HostedSettlementReadiness({
    required this.status,
    required this.rawStatus,
    this.reason,
    this.blockedReason,
    this.missingData = const <String>[],
    this.requiredApprovals = 0,
    this.pendingApprovals = 0,
    this.escrowBalanced,
    this.standingsComplete,
    this.placementsSubmitted,
    this.updatedAt,
  });

  final HostedSettlementReadinessStatus status;
  final String rawStatus;
  final String? reason;
  final String? blockedReason;
  final List<String> missingData;
  final int requiredApprovals;
  final int pendingApprovals;
  final bool? escrowBalanced;
  final bool? standingsComplete;
  final bool? placementsSubmitted;
  final DateTime? updatedAt;

  bool get isReady => status == HostedSettlementReadinessStatus.ready;

  bool get isSettled => status == HostedSettlementReadinessStatus.settled;

  bool get isBlocked =>
      status == HostedSettlementReadinessStatus.blocked ||
      blockedReason?.trim().isNotEmpty == true;

  bool get isDegraded =>
      status == HostedSettlementReadinessStatus.degraded ||
      missingData.isNotEmpty;

  bool get hasAuthoritativePayload => rawStatus != 'missing';

  String get displayLabel {
    switch (status) {
      case HostedSettlementReadinessStatus.ready:
        return 'Settlement ready';
      case HostedSettlementReadinessStatus.syncing:
        return 'Settlement syncing';
      case HostedSettlementReadinessStatus.blocked:
        return 'Settlement blocked';
      case HostedSettlementReadinessStatus.degraded:
        return 'Settlement degraded';
      case HostedSettlementReadinessStatus.settled:
        return 'Settlement complete';
      case HostedSettlementReadinessStatus.unknown:
        return 'Settlement readiness unknown';
    }
  }

  factory HostedSettlementReadiness.fromJson(Object? value) {
    if (value == null) {
      return const HostedSettlementReadiness(
        status: HostedSettlementReadinessStatus.degraded,
        rawStatus: 'missing',
        reason: 'Backend settlement readiness payload is missing.',
        missingData: <String>['settlement_readiness'],
      );
    }
    if (value is String) {
      return HostedSettlementReadiness(
        status: _settlementReadinessStatusFromString(value),
        rawStatus: value,
      );
    }
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'hosted settlement readiness',
    );
    final String rawStatus = GteJson.string(json, <String>[
      'status',
      'state',
      'readiness_status',
      'readinessStatus',
    ], fallback: 'unknown');
    return HostedSettlementReadiness(
      status: _settlementReadinessStatusFromString(rawStatus),
      rawStatus: rawStatus,
      reason: GteJson.stringOrNull(json, <String>[
        'reason',
        'status_reason',
        'statusReason',
      ]),
      blockedReason: GteJson.stringOrNull(json, <String>[
        'blocked_reason',
        'blockedReason',
        'block_reason',
        'blockReason',
      ]),
      missingData: _stringList(
        GteJson.value(json, <String>[
          'missing_data',
          'missingData',
          'missing_fields',
          'missingFields',
        ]),
      ),
      requiredApprovals: GteJson.integer(json, <String>[
        'required_approvals',
        'requiredApprovals',
      ], fallback: 0),
      pendingApprovals: GteJson.integer(json, <String>[
        'pending_approvals',
        'pendingApprovals',
      ], fallback: 0),
      escrowBalanced: _boolOrNull(json, <String>[
        'escrow_balanced',
        'escrowBalanced',
      ]),
      standingsComplete: _boolOrNull(json, <String>[
        'standings_complete',
        'standingsComplete',
      ]),
      placementsSubmitted: _boolOrNull(json, <String>[
        'placements_submitted',
        'placementsSubmitted',
      ]),
      updatedAt: GteJson.dateTimeOrNull(json, <String>[
        'updated_at',
        'updatedAt',
      ]),
    );
  }
}

HostedSettlementReadinessStatus _settlementReadinessStatusFromString(
  String value,
) {
  switch (value.trim().toLowerCase()) {
    case 'ready':
    case 'settlement_ready':
      return HostedSettlementReadinessStatus.ready;
    case 'syncing':
    case 'pending':
    case 'pending_backend':
    case 'awaiting_results':
      return HostedSettlementReadinessStatus.syncing;
    case 'blocked':
    case 'not_ready':
      return HostedSettlementReadinessStatus.blocked;
    case 'degraded':
      return HostedSettlementReadinessStatus.degraded;
    case 'settled':
    case 'complete':
    case 'completed':
    case 'finalized':
      return HostedSettlementReadinessStatus.settled;
    default:
      return HostedSettlementReadinessStatus.unknown;
  }
}

List<String> _stringList(Object? value) {
  if (value is Iterable) {
    return value
        .map((Object? item) => item?.toString().trim() ?? '')
        .where((String item) => item.isNotEmpty)
        .toList(growable: false);
  }
  if (value is String && value.trim().isNotEmpty) {
    return <String>[value.trim()];
  }
  return const <String>[];
}

bool? _boolOrNull(Map<String, Object?> json, List<String> keys) {
  final Object? rawValue = GteJson.value(json, keys);
  if (rawValue == null || (rawValue is String && rawValue.trim().isEmpty)) {
    return null;
  }
  if (rawValue is bool) {
    return rawValue;
  }
  final String normalized = rawValue.toString().trim().toLowerCase();
  if (<String>{'1', 'true', 'yes', 'on'}.contains(normalized)) {
    return true;
  }
  if (<String>{'0', 'false', 'no', 'off'}.contains(normalized)) {
    return false;
  }
  return null;
}

class HostedCompetitionDetail {
  const HostedCompetitionDetail({
    required this.competition,
    required this.template,
    required this.participants,
    required this.currentParticipants,
    required this.joinOpen,
    this.invites = const <HostedCompetitionInvite>[],
  });

  final HostedCompetition competition;
  final HostedCompetitionTemplate template;
  final List<HostedCompetitionParticipant> participants;
  final int currentParticipants;
  final bool joinOpen;
  final List<HostedCompetitionInvite> invites;

  factory HostedCompetitionDetail.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'hosted competition detail',
    );
    return HostedCompetitionDetail(
      competition: HostedCompetition.fromJson(
        GteJson.value(json, <String>['competition']),
      ),
      template: HostedCompetitionTemplate.fromJson(
        GteJson.value(json, <String>['template']),
      ),
      participants: GteJson.typedList(json, <String>[
        'participants',
      ], HostedCompetitionParticipant.fromJson),
      currentParticipants: GteJson.integer(json, <String>[
        'current_participants',
        'currentParticipants',
      ], fallback: 0),
      joinOpen: GteJson.boolean(json, <String>[
        'join_open',
        'joinOpen',
      ], fallback: false),
      invites: GteJson.typedList(json, <String>[
        'invites',
      ], HostedCompetitionInvite.fromJson),
    );
  }
}
