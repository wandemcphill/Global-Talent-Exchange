import 'package:gte_frontend/data/gte_models.dart';

enum CompetitionFormat {
  league,
  cup,
}

enum CompetitionVisibility {
  public,
  private,
  inviteOnly,
}

enum CompetitionStatus {
  draft,
  published,
  openForJoin,
  filled,
  locked,
  inProgress,
  completed,
  cancelled,
  refunded,
  disputed,
}

enum CompetitionDiscoverySection {
  trending,
  newest,
  freeToJoin,
  paid,
  creator,
  leagues,
  cups,
}

class CompetitionPayoutBreakdown {
  const CompetitionPayoutBreakdown({
    required this.place,
    required this.percent,
    required this.amount,
  });

  final int place;
  final double percent;
  final double amount;

  factory CompetitionPayoutBreakdown.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'competition payout');
    return CompetitionPayoutBreakdown(
      place: GteJson.integer(json, <String>['place'], fallback: 1),
      percent: GteJson.number(json, <String>['percent'], fallback: 0),
      amount: GteJson.number(json, <String>['amount'], fallback: 0),
    );
  }

  CompetitionPayoutBreakdown copyWith({
    int? place,
    double? percent,
    double? amount,
  }) {
    return CompetitionPayoutBreakdown(
      place: place ?? this.place,
      percent: percent ?? this.percent,
      amount: amount ?? this.amount,
    );
  }
}

class CompetitionJoinEligibility {
  const CompetitionJoinEligibility({
    required this.eligible,
    this.reason,
    this.requiresInvite = false,
  });

  final bool eligible;
  final String? reason;
  final bool requiresInvite;

  factory CompetitionJoinEligibility.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'competition join eligibility');
    return CompetitionJoinEligibility(
      eligible: GteJson.boolean(json, <String>['eligible'], fallback: false),
      reason: GteJson.stringOrNull(json, <String>['reason']),
      requiresInvite: GteJson.boolean(
        json,
        <String>['requires_invite', 'requiresInvite'],
        fallback: false,
      ),
    );
  }

  CompetitionJoinEligibility copyWith({
    bool? eligible,
    String? reason,
    bool? requiresInvite,
  }) {
    return CompetitionJoinEligibility(
      eligible: eligible ?? this.eligible,
      reason: reason ?? this.reason,
      requiresInvite: requiresInvite ?? this.requiresInvite,
    );
  }
}

class CompetitionSummary {
  const CompetitionSummary({
    required this.id,
    required this.name,
    required this.format,
    required this.visibility,
    required this.status,
    required this.creatorId,
    required this.creatorName,
    required this.participantCount,
    required this.capacity,
    required this.currency,
    required this.entryFee,
    required this.platformFeePct,
    required this.hostFeePct,
    required this.platformFeeAmount,
    required this.hostFeeAmount,
    required this.prizePool,
    required this.payoutStructure,
    required this.rulesSummary,
    required this.joinEligibility,
    required this.beginnerFriendly,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String name;
  final CompetitionFormat format;
  final CompetitionVisibility visibility;
  final CompetitionStatus status;
  final String creatorId;
  final String? creatorName;
  final int participantCount;
  final int capacity;
  final String currency;
  final double entryFee;
  final double platformFeePct;
  final double hostFeePct;
  final double platformFeeAmount;
  final double hostFeeAmount;
  final double prizePool;
  final List<CompetitionPayoutBreakdown> payoutStructure;
  final String rulesSummary;
  final CompetitionJoinEligibility joinEligibility;
  final bool? beginnerFriendly;
  final DateTime createdAt;
  final DateTime updatedAt;

  bool get isFreeToJoin => entryFee <= 0.0001;

  bool get isLeague => format == CompetitionFormat.league;

  bool get isCup => format == CompetitionFormat.cup;

  bool get isLockedForPaidEntryEdits => !isFreeToJoin && participantCount > 0;

  bool get hasHostFee => hostFeePct > 0 || hostFeeAmount > 0;

  double get fillRate => capacity <= 0 ? 0 : participantCount / capacity;

  String get safeFormatLabel =>
      format == CompetitionFormat.league ? 'Skill league' : 'Skill cup';

  String get creatorLabel =>
      creatorName?.trim().isNotEmpty == true ? creatorName!.trim() : 'Creator';

  factory CompetitionSummary.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'competition summary');
    final Map<String, Object?> financials = _mapOrEmpty(
      _firstValue(
        <Map<String, Object?>>[json],
        <String>['financials', 'fees', 'fee_summary'],
      ),
    );
    final Map<String, Object?> eligibility = _mapOrEmpty(
      _firstValue(
        <Map<String, Object?>>[json],
        <String>['join_eligibility', 'joinEligibility'],
      ),
    );
    return CompetitionSummary(
      id: _stringFrom(<Map<String, Object?>>[json], <String>['id']),
      name: _stringFrom(<Map<String, Object?>>[json], <String>['name']),
      format: _competitionFormatFromString(
        _stringFrom(
          <Map<String, Object?>>[json],
          <String>['format', 'competition_format', 'competitionFormat'],
          fallback: 'league',
        ),
      ),
      visibility: _competitionVisibilityFromString(
        _stringFrom(
          <Map<String, Object?>>[json],
          <String>['visibility'],
          fallback: 'public',
        ),
      ),
      status: _competitionStatusFromString(
        _stringFrom(
          <Map<String, Object?>>[json],
          <String>['status', 'contest_status', 'contestStatus'],
          fallback: 'draft',
        ),
      ),
      creatorId: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['creator_id', 'creatorId'],
        fallback: 'community-host',
      ),
      creatorName: _stringOrNullFrom(
        <Map<String, Object?>>[json],
        <String>['creator_name', 'creatorName'],
      ),
      participantCount: _intFrom(
        <Map<String, Object?>>[json],
        <String>['participant_count', 'participantCount'],
        fallback: 0,
      ),
      capacity: _intFrom(
        <Map<String, Object?>>[json],
        <String>['capacity', 'max_participants', 'maxParticipants'],
        fallback: 2,
      ),
      currency: _stringFrom(
        <Map<String, Object?>>[json, financials],
        <String>['currency'],
        fallback: 'credit',
      ),
      entryFee: _doubleFrom(
        <Map<String, Object?>>[json, financials],
        <String>['entry_fee', 'entryFee'],
        fallback: 0,
      ),
      platformFeePct: _doubleFrom(
        <Map<String, Object?>>[json, financials],
        <String>['platform_fee_pct', 'platformFeePct'],
        fallback: 0.10,
      ),
      hostFeePct: _doubleFrom(
        <Map<String, Object?>>[json, financials],
        <String>['host_fee_pct', 'hostFeePct'],
        fallback: 0,
      ),
      platformFeeAmount: _doubleFrom(
        <Map<String, Object?>>[json, financials],
        <String>['platform_fee_amount', 'platformFeeAmount'],
        fallback: 0,
      ),
      hostFeeAmount: _doubleFrom(
        <Map<String, Object?>>[json, financials],
        <String>['host_fee_amount', 'hostFeeAmount'],
        fallback: 0,
      ),
      prizePool: _doubleFrom(
        <Map<String, Object?>>[json, financials],
        <String>['prize_pool', 'prizePool'],
        fallback: 0,
      ),
      payoutStructure: _payoutsFrom(
        _firstValue(
          <Map<String, Object?>>[json, financials],
          <String>['payout_structure', 'payoutStructure'],
        ),
      ),
      rulesSummary: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['rules_summary', 'rulesSummary'],
        fallback: 'Skill-based, creator competition with transparent payout.',
      ),
      joinEligibility: eligibility.isEmpty
          ? const CompetitionJoinEligibility(eligible: false)
          : CompetitionJoinEligibility.fromJson(eligibility),
      beginnerFriendly: _boolOrNullFrom(
        <Map<String, Object?>>[json],
        <String>['beginner_friendly', 'beginnerFriendly'],
      ),
      createdAt: _dateFrom(
            <Map<String, Object?>>[json],
            <String>['created_at', 'createdAt'],
          ) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
      updatedAt: _dateFrom(
            <Map<String, Object?>>[json],
            <String>['updated_at', 'updatedAt'],
          ) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
    );
  }

  CompetitionSummary copyWith({
    String? id,
    String? name,
    CompetitionFormat? format,
    CompetitionVisibility? visibility,
    CompetitionStatus? status,
    String? creatorId,
    String? creatorName,
    int? participantCount,
    int? capacity,
    String? currency,
    double? entryFee,
    double? platformFeePct,
    double? hostFeePct,
    double? platformFeeAmount,
    double? hostFeeAmount,
    double? prizePool,
    List<CompetitionPayoutBreakdown>? payoutStructure,
    String? rulesSummary,
    CompetitionJoinEligibility? joinEligibility,
    bool? beginnerFriendly,
    DateTime? createdAt,
    DateTime? updatedAt,
  }) {
    return CompetitionSummary(
      id: id ?? this.id,
      name: name ?? this.name,
      format: format ?? this.format,
      visibility: visibility ?? this.visibility,
      status: status ?? this.status,
      creatorId: creatorId ?? this.creatorId,
      creatorName: creatorName ?? this.creatorName,
      participantCount: participantCount ?? this.participantCount,
      capacity: capacity ?? this.capacity,
      currency: currency ?? this.currency,
      entryFee: entryFee ?? this.entryFee,
      platformFeePct: platformFeePct ?? this.platformFeePct,
      hostFeePct: hostFeePct ?? this.hostFeePct,
      platformFeeAmount: platformFeeAmount ?? this.platformFeeAmount,
      hostFeeAmount: hostFeeAmount ?? this.hostFeeAmount,
      prizePool: prizePool ?? this.prizePool,
      payoutStructure: payoutStructure ?? this.payoutStructure,
      rulesSummary: rulesSummary ?? this.rulesSummary,
      joinEligibility: joinEligibility ?? this.joinEligibility,
      beginnerFriendly: beginnerFriendly ?? this.beginnerFriendly,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }
}

class CompetitionListResponse {
  const CompetitionListResponse({
    required this.total,
    required this.items,
  });

  final int total;
  final List<CompetitionSummary> items;

  factory CompetitionListResponse.fromJson(Object? value) {
    if (value is List) {
      final List<CompetitionSummary> items = value
          .map(CompetitionSummary.fromJson)
          .toList(growable: false);
      return CompetitionListResponse(total: items.length, items: items);
    }
    final Map<String, Object?> json =
        GteJson.map(value, label: 'competition list');
    return CompetitionListResponse(
      total: GteJson.integer(json, <String>['total'], fallback: 0),
      items: GteJson.typedList(
        json,
        <String>['items'],
        CompetitionSummary.fromJson,
      ),
    );
  }
}

class CompetitionInviteView {
  const CompetitionInviteView({
    required this.inviteCode,
    required this.issuedBy,
    required this.createdAt,
    required this.expiresAt,
    required this.maxUses,
    required this.uses,
    required this.note,
  });

  final String inviteCode;
  final String issuedBy;
  final DateTime createdAt;
  final DateTime? expiresAt;
  final int maxUses;
  final int uses;
  final String? note;

  factory CompetitionInviteView.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'competition invite');
    return CompetitionInviteView(
      inviteCode: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['invite_code', 'inviteCode'],
      ),
      issuedBy: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['issued_by', 'issuedBy'],
        fallback: 'community-host',
      ),
      createdAt: _dateFrom(
            <Map<String, Object?>>[json],
            <String>['created_at', 'createdAt'],
          ) ??
          DateTime.now().toUtc(),
      expiresAt: _dateFrom(
        <Map<String, Object?>>[json],
        <String>['expires_at', 'expiresAt'],
      ),
      maxUses: _intFrom(
        <Map<String, Object?>>[json],
        <String>['max_uses', 'maxUses'],
        fallback: 1,
      ),
      uses: _intFrom(
        <Map<String, Object?>>[json],
        <String>['uses'],
        fallback: 0,
      ),
      note: _stringOrNullFrom(<Map<String, Object?>>[json], <String>['note']),
    );
  }
}

class CompetitionFinancialSummary {
  const CompetitionFinancialSummary({
    required this.competitionId,
    required this.participantCount,
    required this.entryFee,
    required this.grossPool,
    required this.platformFeeAmount,
    required this.hostFeeAmount,
    required this.prizePool,
    required this.payoutStructure,
    required this.currency,
  });

  final String competitionId;
  final int participantCount;
  final double entryFee;
  final double grossPool;
  final double platformFeeAmount;
  final double hostFeeAmount;
  final double prizePool;
  final List<CompetitionPayoutBreakdown> payoutStructure;
  final String currency;

  factory CompetitionFinancialSummary.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'competition financial summary');
    return CompetitionFinancialSummary(
      competitionId: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['competition_id', 'competitionId'],
      ),
      participantCount: _intFrom(
        <Map<String, Object?>>[json],
        <String>['participant_count', 'participantCount'],
        fallback: 0,
      ),
      entryFee: _doubleFrom(
        <Map<String, Object?>>[json],
        <String>['entry_fee', 'entryFee'],
        fallback: 0,
      ),
      grossPool: _doubleFrom(
        <Map<String, Object?>>[json],
        <String>['gross_pool', 'grossPool'],
        fallback: 0,
      ),
      platformFeeAmount: _doubleFrom(
        <Map<String, Object?>>[json],
        <String>['platform_fee_amount', 'platformFeeAmount'],
        fallback: 0,
      ),
      hostFeeAmount: _doubleFrom(
        <Map<String, Object?>>[json],
        <String>['host_fee_amount', 'hostFeeAmount'],
        fallback: 0,
      ),
      prizePool: _doubleFrom(
        <Map<String, Object?>>[json],
        <String>['prize_pool', 'prizePool'],
        fallback: 0,
      ),
      payoutStructure: _payoutsFrom(
        _firstValue(
          <Map<String, Object?>>[json],
          <String>['payout_structure', 'payoutStructure'],
        ),
      ),
      currency: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['currency'],
        fallback: 'credit',
      ),
    );
  }

  CompetitionFinancialSummary copyWith({
    String? competitionId,
    int? participantCount,
    double? entryFee,
    double? grossPool,
    double? platformFeeAmount,
    double? hostFeeAmount,
    double? prizePool,
    List<CompetitionPayoutBreakdown>? payoutStructure,
    String? currency,
  }) {
    return CompetitionFinancialSummary(
      competitionId: competitionId ?? this.competitionId,
      participantCount: participantCount ?? this.participantCount,
      entryFee: entryFee ?? this.entryFee,
      grossPool: grossPool ?? this.grossPool,
      platformFeeAmount: platformFeeAmount ?? this.platformFeeAmount,
      hostFeeAmount: hostFeeAmount ?? this.hostFeeAmount,
      prizePool: prizePool ?? this.prizePool,
      payoutStructure: payoutStructure ?? this.payoutStructure,
      currency: currency ?? this.currency,
    );
  }
}

CompetitionFormat _competitionFormatFromString(String value) {
  return value.toLowerCase() == 'cup'
      ? CompetitionFormat.cup
      : CompetitionFormat.league;
}

CompetitionVisibility _competitionVisibilityFromString(String value) {
  switch (value.toLowerCase()) {
    case 'private':
      return CompetitionVisibility.private;
    case 'invite_only':
    case 'inviteonly':
      return CompetitionVisibility.inviteOnly;
    default:
      return CompetitionVisibility.public;
  }
}

CompetitionStatus _competitionStatusFromString(String value) {
  switch (value.toLowerCase()) {
    case 'published':
      return CompetitionStatus.published;
    case 'open_for_join':
    case 'openforjoin':
      return CompetitionStatus.openForJoin;
    case 'filled':
      return CompetitionStatus.filled;
    case 'locked':
      return CompetitionStatus.locked;
    case 'in_progress':
    case 'inprogress':
      return CompetitionStatus.inProgress;
    case 'completed':
      return CompetitionStatus.completed;
    case 'cancelled':
      return CompetitionStatus.cancelled;
    case 'refunded':
      return CompetitionStatus.refunded;
    case 'disputed':
      return CompetitionStatus.disputed;
    default:
      return CompetitionStatus.draft;
  }
}

Object? _firstValue(
  Iterable<Map<String, Object?>> sources,
  List<String> keys,
) {
  for (final Map<String, Object?> source in sources) {
    final Object? value = GteJson.value(source, keys);
    if (value != null) {
      return value;
    }
  }
  return null;
}

String _stringFrom(
  Iterable<Map<String, Object?>> sources,
  List<String> keys, {
  String? fallback,
}) {
  final Object? value = _firstValue(sources, keys);
  if (value == null) {
    if (fallback != null) {
      return fallback;
    }
    throw GteParsingException('Missing required string field: ${keys.join(' / ')}.');
  }
  final String text = value.toString().trim();
  if (text.isEmpty) {
    return fallback ?? '';
  }
  return text;
}

String? _stringOrNullFrom(
  Iterable<Map<String, Object?>> sources,
  List<String> keys,
) {
  final Object? value = _firstValue(sources, keys);
  if (value == null) {
    return null;
  }
  final String text = value.toString().trim();
  return text.isEmpty ? null : text;
}

int _intFrom(
  Iterable<Map<String, Object?>> sources,
  List<String> keys, {
  int fallback = 0,
}) {
  final Object? value = _firstValue(sources, keys);
  if (value == null) {
    return fallback;
  }
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  return int.tryParse(value.toString()) ?? fallback;
}

double _doubleFrom(
  Iterable<Map<String, Object?>> sources,
  List<String> keys, {
  double fallback = 0,
}) {
  final Object? value = _firstValue(sources, keys);
  if (value == null) {
    return fallback;
  }
  if (value is num) {
    return value.toDouble();
  }
  return double.tryParse(value.toString()) ?? fallback;
}

DateTime? _dateFrom(
  Iterable<Map<String, Object?>> sources,
  List<String> keys,
) {
  final Object? value = _firstValue(sources, keys);
  if (value == null) {
    return null;
  }
  if (value is DateTime) {
    return value.toUtc();
  }
  return DateTime.tryParse(value.toString())?.toUtc();
}

bool? _boolOrNullFrom(
  Iterable<Map<String, Object?>> sources,
  List<String> keys,
) {
  final Object? value = _firstValue(sources, keys);
  if (value == null) {
    return null;
  }
  if (value is bool) {
    return value;
  }
  final String normalized = value.toString().trim().toLowerCase();
  if (<String>{'1', 'true', 'yes', 'on'}.contains(normalized)) {
    return true;
  }
  if (<String>{'0', 'false', 'no', 'off'}.contains(normalized)) {
    return false;
  }
  return null;
}

Map<String, Object?> _mapOrEmpty(Object? value) {
  if (value == null) {
    return const <String, Object?>{};
  }
  try {
    return GteJson.map(value);
  } on GteParsingException {
    return const <String, Object?>{};
  }
}

List<CompetitionPayoutBreakdown> _payoutsFrom(Object? value) {
  if (value == null) {
    return const <CompetitionPayoutBreakdown>[];
  }
  try {
    return GteJson.list(value)
        .map(CompetitionPayoutBreakdown.fromJson)
        .toList(growable: false);
  } on GteParsingException {
    return const <CompetitionPayoutBreakdown>[];
  }
}
