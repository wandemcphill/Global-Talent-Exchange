import 'package:gte_frontend/data/gte_models.dart';

import 'match_type.dart';

enum CompetitionFormat { league, cup }

enum CompetitionVisibility { public, private, inviteOnly }

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
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'competition payout',
    );
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
    this.requiresPasscode = false,
  });

  final bool eligible;
  final String? reason;
  final bool requiresInvite;
  final bool requiresPasscode;

  factory CompetitionJoinEligibility.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'competition join eligibility',
    );
    return CompetitionJoinEligibility(
      eligible: GteJson.boolean(json, <String>['eligible'], fallback: false),
      reason: GteJson.stringOrNull(json, <String>['reason']),
      requiresInvite: GteJson.boolean(json, <String>[
        'requires_invite',
        'requiresInvite',
      ], fallback: false),
      requiresPasscode: GteJson.boolean(json, <String>[
        'requires_passcode',
        'requiresPasscode',
      ], fallback: false),
    );
  }

  CompetitionJoinEligibility copyWith({
    bool? eligible,
    String? reason,
    bool? requiresInvite,
    bool? requiresPasscode,
  }) {
    return CompetitionJoinEligibility(
      eligible: eligible ?? this.eligible,
      reason: reason ?? this.reason,
      requiresInvite: requiresInvite ?? this.requiresInvite,
      requiresPasscode: requiresPasscode ?? this.requiresPasscode,
    );
  }
}

class CompetitionDynamicPrizePool {
  const CompetitionDynamicPrizePool({
    required this.enabled,
    required this.baseFunding,
    required this.activityBoost,
    required this.jackpotRollover,
    required this.totalPool,
    required this.activeUsers5m,
    required this.tradeVolume5m,
  });

  final bool enabled;
  final double baseFunding;
  final double activityBoost;
  final double jackpotRollover;
  final double totalPool;
  final int activeUsers5m;
  final double tradeVolume5m;

  factory CompetitionDynamicPrizePool.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'competition dynamic prize pool',
    );
    return CompetitionDynamicPrizePool(
      enabled: GteJson.boolean(json, <String>['enabled'], fallback: false),
      baseFunding: GteJson.number(json, <String>[
        'base_funding',
        'baseFunding',
      ], fallback: 0),
      activityBoost: GteJson.number(json, <String>[
        'activity_boost',
        'activityBoost',
      ], fallback: 0),
      jackpotRollover: GteJson.number(json, <String>[
        'jackpot_rollover',
        'jackpotRollover',
      ], fallback: 0),
      totalPool: GteJson.number(json, <String>[
        'total_pool',
        'totalPool',
      ], fallback: 0),
      activeUsers5m: GteJson.integer(json, <String>[
        'active_users_5min',
        'activeUsers5m',
      ], fallback: 0),
      tradeVolume5m: GteJson.number(json, <String>[
        'trade_volume_5min',
        'tradeVolume5m',
      ], fallback: 0),
    );
  }

  CompetitionDynamicPrizePool copyWith({
    bool? enabled,
    double? baseFunding,
    double? activityBoost,
    double? jackpotRollover,
    double? totalPool,
    int? activeUsers5m,
    double? tradeVolume5m,
  }) {
    return CompetitionDynamicPrizePool(
      enabled: enabled ?? this.enabled,
      baseFunding: baseFunding ?? this.baseFunding,
      activityBoost: activityBoost ?? this.activityBoost,
      jackpotRollover: jackpotRollover ?? this.jackpotRollover,
      totalPool: totalPool ?? this.totalPool,
      activeUsers5m: activeUsers5m ?? this.activeUsers5m,
      tradeVolume5m: tradeVolume5m ?? this.tradeVolume5m,
    );
  }
}

class FastMatchEntitlementView {
  const FastMatchEntitlementView({
    required this.freeMatchesRemaining,
    required this.freeMatchesUsed,
    required this.chargeOnLoss,
    required this.chargeRequiredNow,
    required this.entryCurrency,
    required this.entryCurrencyLabel,
    required this.fanCoinEntryFee,
    required this.entitlementStatus,
    this.matchId,
    this.liveMatchKey,
    this.viewerRoute,
    this.settlementStatus,
    this.result,
  });

  final int freeMatchesRemaining;
  final int freeMatchesUsed;
  final bool chargeOnLoss;
  final bool chargeRequiredNow;
  final String entryCurrency;
  final String entryCurrencyLabel;
  final double fanCoinEntryFee;
  final String entitlementStatus;
  final String? matchId;
  final String? liveMatchKey;
  final String? viewerRoute;
  final String? settlementStatus;
  final String? result;

  String get entryFeeLabel =>
      _formatUnitAmount(fanCoinEntryFee, entryCurrencyLabel);

  String get serverRuleLabel {
    if (chargeRequiredNow) {
      return '$entryFeeLabel required before kickoff.';
    }
    return '$freeMatchesRemaining free matches remaining; $freeMatchesUsed used.';
  }

  factory FastMatchEntitlementView.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'fast match entitlement',
    );
    return FastMatchEntitlementView(
      freeMatchesRemaining: _intFrom(
        <Map<String, Object?>>[json],
        <String>['free_matches_remaining', 'freeMatchesRemaining'],
        fallback: 0,
      ),
      freeMatchesUsed: _intFrom(
        <Map<String, Object?>>[json],
        <String>['free_matches_used', 'freeMatchesUsed'],
        fallback: 0,
      ),
      chargeOnLoss: _boolFrom(
        <Map<String, Object?>>[json],
        <String>['charge_on_loss', 'chargeOnLoss'],
        fallback: true,
      ),
      chargeRequiredNow: _boolFrom(
        <Map<String, Object?>>[json],
        <String>['charge_required_now', 'chargeRequiredNow'],
        fallback: false,
      ),
      entryCurrency: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['entry_currency', 'entryCurrency'],
        fallback: 'credit',
      ),
      entryCurrencyLabel: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['entry_currency_label', 'entryCurrencyLabel'],
        fallback: 'Fan Coin',
      ),
      fanCoinEntryFee: _doubleFrom(
        <Map<String, Object?>>[json],
        <String>['fan_coin_entry_fee', 'fanCoinEntryFee', 'entry_fee'],
        fallback: 0,
      ),
      entitlementStatus: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['entitlement_status', 'entitlementStatus', 'status'],
        fallback: 'unknown',
      ),
      matchId: _stringOrNullFrom(
        <Map<String, Object?>>[json],
        <String>['match_id', 'matchId'],
      ),
      liveMatchKey: _stringOrNullFrom(
        <Map<String, Object?>>[json],
        <String>['live_match_key', 'liveMatchKey'],
      ),
      viewerRoute: _stringOrNullFrom(
        <Map<String, Object?>>[json],
        <String>['viewer_route', 'viewerRoute'],
      ),
      settlementStatus: _stringOrNullFrom(
        <Map<String, Object?>>[json],
        <String>['settlement_status', 'settlementStatus'],
      ),
      result: _stringOrNullFrom(
        <Map<String, Object?>>[json],
        <String>['result'],
      ),
    );
  }
}

class FastCupRegistrationView {
  const FastCupRegistrationView({
    required this.registrationId,
    required this.escrowStatus,
    required this.entryFeeAmount,
    required this.entryFeeCurrency,
    this.payoutStatus,
    this.walletLedgerId,
  });

  final String? registrationId;
  final String escrowStatus;
  final double entryFeeAmount;
  final String entryFeeCurrency;
  final String? payoutStatus;
  final String? walletLedgerId;

  bool get isEscrowBacked => <String>{
    'reserved',
    'escrowed',
    'released',
  }.contains(escrowStatus.trim().toLowerCase());

  String get entryFeeLabel =>
      _formatUnitAmount(entryFeeAmount, _currencyLabel(entryFeeCurrency));

  String get escrowStatusLabel =>
      _sentenceCase(escrowStatus.trim().isEmpty ? 'pending' : escrowStatus);

  factory FastCupRegistrationView.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'fast cup registration',
    );
    return FastCupRegistrationView(
      registrationId: _stringOrNullFrom(
        <Map<String, Object?>>[json],
        <String>['registration_id', 'registrationId', 'id'],
      ),
      escrowStatus: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['escrow_status', 'escrowStatus'],
        fallback: 'pending',
      ),
      entryFeeAmount: _doubleFrom(
        <Map<String, Object?>>[json],
        <String>['entry_fee_amount', 'entryFeeAmount', 'entry_fee', 'entryFee'],
        fallback: 0,
      ),
      entryFeeCurrency: _stringFrom(
        <Map<String, Object?>>[json],
        <String>[
          'entry_fee_currency',
          'entryFeeCurrency',
          'currency',
          'entry_currency',
        ],
        fallback: 'credit',
      ),
      payoutStatus: _stringOrNullFrom(
        <Map<String, Object?>>[json],
        <String>['payout_status', 'payoutStatus'],
      ),
      walletLedgerId: _stringOrNullFrom(
        <Map<String, Object?>>[json],
        <String>['wallet_ledger_id', 'walletLedgerId'],
      ),
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
    this.remainingSlots = 0,
    required this.currency,
    required this.entryFee,
    this.grossPot = 0,
    this.netPayoutPot = 0,
    required this.platformFeePct,
    required this.hostFeePct,
    required this.platformFeeAmount,
    required this.hostFeeAmount,
    required this.prizePool,
    required this.payoutStructure,
    required this.rulesSummary,
    required this.matchType,
    required this.joinEligibility,
    required this.beginnerFriendly,
    required this.createdAt,
    required this.updatedAt,
    this.competitionMode = 'competition',
    this.prizeMode = 'entry_funded',
    this.payoutMode = 'winner_takes_all',
    this.isRanked = true,
    this.registrationDeadline,
    this.hostFundedPrizeTotal = 0,
    this.hostFundingRequired = 0,
    this.hostFundingEscrowed = 0,
    this.hostPlatformFee = 0,
    this.fixedPrizes = const <String, double>{},
    this.eligibilityRules = const <String, Object?>{},
    this.rankingPolicy = const <String, Object?>{},
    this.featured = false,
    this.manualApprovalRequired = false,
    this.onlineNow = false,
    this.dynamicPrizePool,
    this.requiresPasscode = false,
    this.scheduledStartAt,
    this.specialRules,
    this.fastMatchEntitlement,
    this.fastCupRegistration,
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
  final int remainingSlots;
  final String currency;
  final double entryFee;
  final double grossPot;
  final double netPayoutPot;
  final double platformFeePct;
  final double hostFeePct;
  final double platformFeeAmount;
  final double hostFeeAmount;
  final double prizePool;
  final List<CompetitionPayoutBreakdown> payoutStructure;
  final String rulesSummary;
  final MatchType matchType;
  final CompetitionJoinEligibility joinEligibility;
  final CompetitionDynamicPrizePool? dynamicPrizePool;
  final String competitionMode;
  final String prizeMode;
  final String payoutMode;
  final bool isRanked;
  final DateTime? registrationDeadline;
  final double hostFundedPrizeTotal;
  final double hostFundingRequired;
  final double hostFundingEscrowed;
  final double hostPlatformFee;
  final Map<String, double> fixedPrizes;
  final Map<String, Object?> eligibilityRules;
  final Map<String, Object?> rankingPolicy;
  final bool featured;
  final bool manualApprovalRequired;
  final bool onlineNow;
  final bool? beginnerFriendly;
  final bool requiresPasscode;
  final DateTime? scheduledStartAt;
  final String? specialRules;
  final FastMatchEntitlementView? fastMatchEntitlement;
  final FastCupRegistrationView? fastCupRegistration;
  final DateTime createdAt;
  final DateTime updatedAt;

  bool get isFreeToJoin => entryFee <= 0.0001;

  bool get isLeague => format == CompetitionFormat.league;

  bool get isCup => format == CompetitionFormat.cup;

  bool get isLockedForPaidEntryEdits => !isFreeToJoin && participantCount > 0;

  bool get hasHostFee => hostFeePct > 0 || hostFeeAmount > 0;

  double get fillRate => capacity <= 0 ? 0 : participantCount / capacity;

  bool get isGtexHosted => matchType == MatchType.gtexHosted;

  bool get isUserHosted => matchType == MatchType.userHosted;

  bool get isFastMatch => matchType == MatchType.fastMatch;

  bool get hasDynamicPrizePool => dynamicPrizePool?.enabled == true;

  bool get isNationalCompetition {
    final String text =
        '$competitionMode ${eligibilityRules['competition_scope'] ?? ''} '
                '$rulesSummary $name'
            .toLowerCase();
    return text.contains('national') ||
        text.contains('country team') ||
        text.contains('international');
  }

  bool get hasRewards =>
      prizePool > 0.0001 ||
      netPayoutPot > 0.0001 ||
      hostFundedPrizeTotal > 0.0001 ||
      fixedPrizes.isNotEmpty;

  bool get isHostFundedPrize => prizeMode == 'host_funded_fixed';

  bool get isEntryFundedPrize => prizeMode == 'entry_funded';

  String get rankingLabel =>
      isRanked ? 'Ranked competition' : 'Unranked competition';

  String get prizeModeLabel {
    switch (prizeMode) {
      case 'host_funded_fixed':
        return 'Host-funded fixed prize';
      case 'entry_funded':
        return isFreeToJoin ? 'No entry pot yet' : 'Entry-funded pot';
      case 'none':
        return 'No prize';
      default:
        return _sentenceCase(prizeMode);
    }
  }

  String get safeFormatLabel =>
      format == CompetitionFormat.league ? 'Skill league' : 'Skill cup';

  String get creatorLabel =>
      creatorName?.trim().isNotEmpty == true ? creatorName!.trim() : 'Creator';

  String get hostSummary {
    switch (matchType) {
      case MatchType.gtexHosted:
        return '$safeFormatLabel - GTEX hosted';
      case MatchType.userHosted:
        return '$safeFormatLabel - Hosted by $creatorLabel';
      case MatchType.fastMatch:
        return '$safeFormatLabel - Quick Match lane';
    }
  }

  String get entryButtonLabel => matchType.actionLabel;

  String get economyNotice {
    final FastMatchEntitlementView? entitlement = fastMatchEntitlement;
    final FastCupRegistrationView? registration = fastCupRegistration;
    switch (matchType) {
      case MatchType.gtexHosted:
        return 'GTEX competitions are free to join. Win real money on verified results.';
      case MatchType.userHosted:
        if (registration != null) {
          return 'Fast Cup entry is ${registration.entryFeeLabel}; escrow is ${registration.escrowStatusLabel.toLowerCase()} by the server before payouts settle.';
        }
        return 'User competitions use Fan Coin for buy-ins, entries, and prize pools.';
      case MatchType.fastMatch:
        if (entitlement != null) {
          if (entitlement.chargeRequiredNow) {
            return 'Fast Match is paid for this account now: ${entitlement.entryFeeLabel} is required before kickoff.';
          }
          return 'Server entitlement: ${entitlement.freeMatchesRemaining} free matches remaining (${entitlement.freeMatchesUsed} used). Draws count; a loss ends the free run.';
        }
        return 'Fast Match entitlement loads from the server before kickoff. Fan Coin is used when a paid entry is required.';
    }
  }

  factory CompetitionSummary.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'competition summary',
    );
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
      remainingSlots: _intFrom(
        <Map<String, Object?>>[json],
        <String>['remaining_slots', 'remainingSlots'],
        fallback: 0,
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
      grossPot: _doubleFrom(
        <Map<String, Object?>>[json, financials],
        <String>['gross_pot', 'grossPot', 'gross_pool', 'grossPool'],
        fallback: 0,
      ),
      netPayoutPot: _doubleFrom(
        <Map<String, Object?>>[json, financials],
        <String>['net_payout_pot', 'netPayoutPot', 'prize_pool', 'prizePool'],
        fallback: 0,
      ),
      platformFeePct: _doubleFrom(
        <Map<String, Object?>>[json, financials],
        <String>['platform_fee_pct', 'platformFeePct'],
        fallback: 0.20,
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
      matchType: _matchTypeFromMaps(
        <Map<String, Object?>>[json, financials],
        creatorId: _stringFrom(
          <Map<String, Object?>>[json],
          <String>['creator_id', 'creatorId'],
          fallback: 'community-host',
        ),
        creatorName: _stringOrNullFrom(
          <Map<String, Object?>>[json],
          <String>['creator_name', 'creatorName'],
        ),
        name: _stringFrom(<Map<String, Object?>>[json], <String>['name']),
      ),
      joinEligibility:
          eligibility.isEmpty
              ? const CompetitionJoinEligibility(eligible: false)
              : CompetitionJoinEligibility.fromJson(eligibility),
      dynamicPrizePool: _dynamicPrizePoolFromMaps(
        <Map<String, Object?>>[json, financials],
        prizePool: _doubleFrom(
          <Map<String, Object?>>[json, financials],
          <String>['prize_pool', 'prizePool'],
          fallback: 0,
        ),
        entryFee: _doubleFrom(
          <Map<String, Object?>>[json, financials],
          <String>['entry_fee', 'entryFee'],
          fallback: 0,
        ),
      ),
      competitionMode: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['competition_mode', 'competitionMode'],
        fallback: 'competition',
      ),
      prizeMode: _stringFrom(
        <Map<String, Object?>>[json, financials],
        <String>['prize_mode', 'prizeMode'],
        fallback: 'entry_funded',
      ),
      payoutMode: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['payout_mode', 'payoutMode'],
        fallback: 'winner_takes_all',
      ),
      isRanked: _boolFrom(
        <Map<String, Object?>>[json, financials],
        <String>['is_ranked', 'isRanked', 'ranked'],
        fallback: true,
      ),
      registrationDeadline: _dateFrom(
        <Map<String, Object?>>[json],
        <String>['registration_deadline', 'registrationDeadline'],
      ),
      hostFundedPrizeTotal: _doubleFrom(
        <Map<String, Object?>>[json, financials],
        <String>['host_funded_prize_total', 'hostFundedPrizeTotal'],
        fallback: 0,
      ),
      hostFundingRequired: _doubleFrom(
        <Map<String, Object?>>[json, financials],
        <String>['host_funding_required', 'hostFundingRequired'],
        fallback: 0,
      ),
      hostFundingEscrowed: _doubleFrom(
        <Map<String, Object?>>[json, financials],
        <String>['host_funding_escrowed', 'hostFundingEscrowed'],
        fallback: 0,
      ),
      hostPlatformFee: _doubleFrom(
        <Map<String, Object?>>[json],
        <String>['host_platform_fee', 'hostPlatformFee'],
        fallback: 0,
      ),
      fixedPrizes: _doubleMapFrom(
        _firstValue(
          <Map<String, Object?>>[json],
          <String>['fixed_prizes', 'fixedPrizes'],
        ),
      ),
      eligibilityRules: _mapOrEmpty(
        _firstValue(
          <Map<String, Object?>>[json],
          <String>['eligibility_rules', 'eligibilityRules'],
        ),
      ),
      rankingPolicy: _mapOrEmpty(
        _firstValue(
          <Map<String, Object?>>[json],
          <String>['ranking_policy', 'rankingPolicy'],
        ),
      ),
      featured: _boolFrom(
        <Map<String, Object?>>[json],
        <String>['featured'],
        fallback: false,
      ),
      manualApprovalRequired: _boolFrom(
        <Map<String, Object?>>[json],
        <String>['manual_approval_required', 'manualApprovalRequired'],
        fallback: false,
      ),
      onlineNow: _boolFrom(
        <Map<String, Object?>>[json],
        <String>['online_now', 'onlineNow'],
        fallback: false,
      ),
      beginnerFriendly: _boolOrNullFrom(
        <Map<String, Object?>>[json],
        <String>['beginner_friendly', 'beginnerFriendly'],
      ),
      requiresPasscode: _boolFrom(
        <Map<String, Object?>>[json],
        <String>['requires_passcode', 'requiresPasscode'],
        fallback: false,
      ),
      scheduledStartAt: _dateFrom(
        <Map<String, Object?>>[json],
        <String>['scheduled_start_at', 'scheduledStartAt', 'startDateTime'],
      ),
      specialRules: _stringOrNullFrom(
        <Map<String, Object?>>[json],
        <String>['special_rules', 'specialRules'],
      ),
      fastMatchEntitlement: _fastMatchEntitlementFromMaps(
        <Map<String, Object?>>[json, financials],
      ),
      fastCupRegistration: _fastCupRegistrationFromMaps(<Map<String, Object?>>[
        json,
        financials,
      ]),
      createdAt:
          _dateFrom(
            <Map<String, Object?>>[json],
            <String>['created_at', 'createdAt'],
          ) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
      updatedAt:
          _dateFrom(
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
    int? remainingSlots,
    String? currency,
    double? entryFee,
    double? grossPot,
    double? netPayoutPot,
    double? platformFeePct,
    double? hostFeePct,
    double? platformFeeAmount,
    double? hostFeeAmount,
    double? prizePool,
    List<CompetitionPayoutBreakdown>? payoutStructure,
    String? rulesSummary,
    MatchType? matchType,
    CompetitionJoinEligibility? joinEligibility,
    CompetitionDynamicPrizePool? dynamicPrizePool,
    String? competitionMode,
    String? prizeMode,
    String? payoutMode,
    bool? isRanked,
    DateTime? registrationDeadline,
    double? hostFundedPrizeTotal,
    double? hostFundingRequired,
    double? hostFundingEscrowed,
    double? hostPlatformFee,
    Map<String, double>? fixedPrizes,
    Map<String, Object?>? eligibilityRules,
    Map<String, Object?>? rankingPolicy,
    bool? featured,
    bool? manualApprovalRequired,
    bool? onlineNow,
    bool? beginnerFriendly,
    bool? requiresPasscode,
    DateTime? scheduledStartAt,
    String? specialRules,
    FastMatchEntitlementView? fastMatchEntitlement,
    FastCupRegistrationView? fastCupRegistration,
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
      remainingSlots: remainingSlots ?? this.remainingSlots,
      currency: currency ?? this.currency,
      entryFee: entryFee ?? this.entryFee,
      grossPot: grossPot ?? this.grossPot,
      netPayoutPot: netPayoutPot ?? this.netPayoutPot,
      platformFeePct: platformFeePct ?? this.platformFeePct,
      hostFeePct: hostFeePct ?? this.hostFeePct,
      platformFeeAmount: platformFeeAmount ?? this.platformFeeAmount,
      hostFeeAmount: hostFeeAmount ?? this.hostFeeAmount,
      prizePool: prizePool ?? this.prizePool,
      payoutStructure: payoutStructure ?? this.payoutStructure,
      rulesSummary: rulesSummary ?? this.rulesSummary,
      matchType: matchType ?? this.matchType,
      joinEligibility: joinEligibility ?? this.joinEligibility,
      dynamicPrizePool: dynamicPrizePool ?? this.dynamicPrizePool,
      competitionMode: competitionMode ?? this.competitionMode,
      prizeMode: prizeMode ?? this.prizeMode,
      payoutMode: payoutMode ?? this.payoutMode,
      isRanked: isRanked ?? this.isRanked,
      registrationDeadline: registrationDeadline ?? this.registrationDeadline,
      hostFundedPrizeTotal: hostFundedPrizeTotal ?? this.hostFundedPrizeTotal,
      hostFundingRequired: hostFundingRequired ?? this.hostFundingRequired,
      hostFundingEscrowed: hostFundingEscrowed ?? this.hostFundingEscrowed,
      hostPlatformFee: hostPlatformFee ?? this.hostPlatformFee,
      fixedPrizes: fixedPrizes ?? this.fixedPrizes,
      eligibilityRules: eligibilityRules ?? this.eligibilityRules,
      rankingPolicy: rankingPolicy ?? this.rankingPolicy,
      featured: featured ?? this.featured,
      manualApprovalRequired:
          manualApprovalRequired ?? this.manualApprovalRequired,
      onlineNow: onlineNow ?? this.onlineNow,
      beginnerFriendly: beginnerFriendly ?? this.beginnerFriendly,
      requiresPasscode: requiresPasscode ?? this.requiresPasscode,
      scheduledStartAt: scheduledStartAt ?? this.scheduledStartAt,
      specialRules: specialRules ?? this.specialRules,
      fastMatchEntitlement: fastMatchEntitlement ?? this.fastMatchEntitlement,
      fastCupRegistration: fastCupRegistration ?? this.fastCupRegistration,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
    );
  }
}

class CompetitionListResponse {
  const CompetitionListResponse({required this.total, required this.items});

  final int total;
  final List<CompetitionSummary> items;

  factory CompetitionListResponse.fromJson(Object? value) {
    if (value is List) {
      final List<CompetitionSummary> items = value
          .map(CompetitionSummary.fromJson)
          .toList(growable: false);
      return CompetitionListResponse(total: items.length, items: items);
    }
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'competition list',
    );
    return CompetitionListResponse(
      total: GteJson.integer(json, <String>['total'], fallback: 0),
      items: GteJson.typedList(json, <String>[
        'items',
      ], CompetitionSummary.fromJson),
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
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'competition invite',
    );
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
      createdAt:
          _dateFrom(
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
    this.dynamicPrizePool,
    this.prizeMode = 'entry_funded',
    this.isRanked = true,
    this.remainingSlots = 0,
    this.hostFundedPrizeTotal = 0,
    this.hostFundingRequired = 0,
    this.hostFundingEscrowed = 0,
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
  final CompetitionDynamicPrizePool? dynamicPrizePool;
  final String prizeMode;
  final bool isRanked;
  final int remainingSlots;
  final double hostFundedPrizeTotal;
  final double hostFundingRequired;
  final double hostFundingEscrowed;

  factory CompetitionFinancialSummary.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'competition financial summary',
    );
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
      dynamicPrizePool: _dynamicPrizePoolFromMaps(
        <Map<String, Object?>>[json],
        prizePool: _doubleFrom(
          <Map<String, Object?>>[json],
          <String>['prize_pool', 'prizePool'],
          fallback: 0,
        ),
        entryFee: _doubleFrom(
          <Map<String, Object?>>[json],
          <String>['entry_fee', 'entryFee'],
          fallback: 0,
        ),
      ),
      currency: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['currency'],
        fallback: 'credit',
      ),
      prizeMode: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['prize_mode', 'prizeMode'],
        fallback: 'entry_funded',
      ),
      isRanked: _boolFrom(
        <Map<String, Object?>>[json],
        <String>['is_ranked', 'isRanked', 'ranked'],
        fallback: true,
      ),
      remainingSlots: _intFrom(
        <Map<String, Object?>>[json],
        <String>['remaining_slots', 'remainingSlots'],
        fallback: 0,
      ),
      hostFundedPrizeTotal: _doubleFrom(
        <Map<String, Object?>>[json],
        <String>['host_funded_prize_total', 'hostFundedPrizeTotal'],
        fallback: 0,
      ),
      hostFundingRequired: _doubleFrom(
        <Map<String, Object?>>[json],
        <String>['host_funding_required', 'hostFundingRequired'],
        fallback: 0,
      ),
      hostFundingEscrowed: _doubleFrom(
        <Map<String, Object?>>[json],
        <String>['host_funding_escrowed', 'hostFundingEscrowed'],
        fallback: 0,
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
    CompetitionDynamicPrizePool? dynamicPrizePool,
    String? prizeMode,
    bool? isRanked,
    int? remainingSlots,
    double? hostFundedPrizeTotal,
    double? hostFundingRequired,
    double? hostFundingEscrowed,
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
      dynamicPrizePool: dynamicPrizePool ?? this.dynamicPrizePool,
      prizeMode: prizeMode ?? this.prizeMode,
      isRanked: isRanked ?? this.isRanked,
      remainingSlots: remainingSlots ?? this.remainingSlots,
      hostFundedPrizeTotal: hostFundedPrizeTotal ?? this.hostFundedPrizeTotal,
      hostFundingRequired: hostFundingRequired ?? this.hostFundingRequired,
      hostFundingEscrowed: hostFundingEscrowed ?? this.hostFundingEscrowed,
    );
  }
}

class CompetitionParticipant {
  const CompetitionParticipant({
    required this.participantId,
    required this.competitionId,
    required this.clubId,
    required this.status,
    required this.entryFeeAmount,
    required this.entryFeeCurrency,
    required this.escrowStatus,
    required this.joinedAt,
    this.userId,
    this.clubName,
    this.walletLedgerId,
    this.refundedAt,
  });

  final String participantId;
  final String competitionId;
  final String? userId;
  final String clubId;
  final String? clubName;
  final String status;
  final double entryFeeAmount;
  final String entryFeeCurrency;
  final String escrowStatus;
  final String? walletLedgerId;
  final DateTime joinedAt;
  final DateTime? refundedAt;

  String get entryFeeLabel =>
      _formatUnitAmount(entryFeeAmount, _currencyLabel(entryFeeCurrency));

  factory CompetitionParticipant.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'competition participant',
    );
    return CompetitionParticipant(
      participantId: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['participant_id', 'participantId', 'id'],
      ),
      competitionId: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['competition_id', 'competitionId'],
      ),
      userId: _stringOrNullFrom(
        <Map<String, Object?>>[json],
        <String>['user_id', 'userId'],
      ),
      clubId: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['club_id', 'clubId'],
      ),
      clubName: _stringOrNullFrom(
        <Map<String, Object?>>[json],
        <String>['club_name', 'clubName'],
      ),
      status: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['status'],
        fallback: 'joined',
      ),
      entryFeeAmount: _doubleFrom(
        <Map<String, Object?>>[json],
        <String>['entry_fee_amount', 'entryFeeAmount'],
        fallback: 0,
      ),
      entryFeeCurrency: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['entry_fee_currency', 'entryFeeCurrency', 'currency'],
        fallback: 'credit',
      ),
      escrowStatus: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['escrow_status', 'escrowStatus'],
        fallback: 'none',
      ),
      walletLedgerId: _stringOrNullFrom(
        <Map<String, Object?>>[json],
        <String>['wallet_ledger_id', 'walletLedgerId'],
      ),
      joinedAt:
          _dateFrom(
            <Map<String, Object?>>[json],
            <String>['joined_at', 'joinedAt'],
          ) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
      refundedAt: _dateFrom(
        <Map<String, Object?>>[json],
        <String>['refunded_at', 'refundedAt'],
      ),
    );
  }
}

class CompetitionParticipantsResponse {
  const CompetitionParticipantsResponse({
    required this.competitionId,
    required this.participants,
  });

  final String competitionId;
  final List<CompetitionParticipant> participants;

  factory CompetitionParticipantsResponse.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'competition participants',
    );
    return CompetitionParticipantsResponse(
      competitionId: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['competition_id', 'competitionId'],
      ),
      participants: GteJson.list(
        _firstValue(<Map<String, Object?>>[json], <String>['participants']) ??
            const <Object?>[],
      ).map(CompetitionParticipant.fromJson).toList(growable: false),
    );
  }
}

class CompetitionPot {
  const CompetitionPot({
    required this.competitionId,
    required this.currency,
    required this.participantCount,
    required this.capacity,
    required this.remainingSlots,
    required this.entryFee,
    required this.grossPot,
    required this.platformFeePct,
    required this.platformFeeAmount,
    required this.hostFeePct,
    required this.hostFeeAmount,
    required this.netPayoutPot,
    required this.prizeMode,
    required this.payoutMode,
    required this.fixedPrizes,
    required this.payoutStructure,
  });

  final String competitionId;
  final String currency;
  final int participantCount;
  final int capacity;
  final int remainingSlots;
  final double entryFee;
  final double grossPot;
  final double platformFeePct;
  final double platformFeeAmount;
  final double hostFeePct;
  final double hostFeeAmount;
  final double netPayoutPot;
  final String prizeMode;
  final String payoutMode;
  final Map<String, double> fixedPrizes;
  final List<CompetitionPayoutBreakdown> payoutStructure;

  factory CompetitionPot.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'competition pot',
    );
    return CompetitionPot(
      competitionId: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['competition_id', 'competitionId'],
      ),
      currency: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['currency'],
        fallback: 'credit',
      ),
      participantCount: _intFrom(
        <Map<String, Object?>>[json],
        <String>['participant_count', 'participantCount'],
        fallback: 0,
      ),
      capacity: _intFrom(
        <Map<String, Object?>>[json],
        <String>['capacity'],
        fallback: 2,
      ),
      remainingSlots: _intFrom(
        <Map<String, Object?>>[json],
        <String>['remaining_slots', 'remainingSlots'],
        fallback: 0,
      ),
      entryFee: _doubleFrom(
        <Map<String, Object?>>[json],
        <String>['entry_fee', 'entryFee'],
        fallback: 0,
      ),
      grossPot: _doubleFrom(
        <Map<String, Object?>>[json],
        <String>['gross_pot', 'grossPot'],
        fallback: 0,
      ),
      platformFeePct: _doubleFrom(
        <Map<String, Object?>>[json],
        <String>['platform_fee_pct', 'platformFeePct'],
        fallback: 0.20,
      ),
      platformFeeAmount: _doubleFrom(
        <Map<String, Object?>>[json],
        <String>['platform_fee_amount', 'platformFeeAmount'],
        fallback: 0,
      ),
      hostFeePct: _doubleFrom(
        <Map<String, Object?>>[json],
        <String>['host_fee_pct', 'hostFeePct'],
        fallback: 0,
      ),
      hostFeeAmount: _doubleFrom(
        <Map<String, Object?>>[json],
        <String>['host_fee_amount', 'hostFeeAmount'],
        fallback: 0,
      ),
      netPayoutPot: _doubleFrom(
        <Map<String, Object?>>[json],
        <String>['net_payout_pot', 'netPayoutPot'],
        fallback: 0,
      ),
      prizeMode: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['prize_mode', 'prizeMode'],
        fallback: 'entry_funded',
      ),
      payoutMode: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['payout_mode', 'payoutMode'],
        fallback: 'winner_takes_all',
      ),
      fixedPrizes: _doubleMapFrom(
        _firstValue(
          <Map<String, Object?>>[json],
          <String>['fixed_prizes', 'fixedPrizes'],
        ),
      ),
      payoutStructure: _payoutsFrom(
        _firstValue(
          <Map<String, Object?>>[json],
          <String>['payout_structure', 'payoutStructure'],
        ),
      ),
    );
  }
}

class ClubCompetitionLeaderboardEntry {
  const ClubCompetitionLeaderboardEntry({
    required this.rank,
    required this.clubId,
    required this.clubName,
    required this.rankingPoints,
    required this.wins,
    required this.draws,
    required this.losses,
    required this.trophies,
    required this.recentForm,
    required this.eligibilityTier,
    required this.gtexHostedEligible,
    this.ownerUserId,
  });

  final int rank;
  final String clubId;
  final String clubName;
  final String? ownerUserId;
  final int rankingPoints;
  final int wins;
  final int draws;
  final int losses;
  final int trophies;
  final String recentForm;
  final String eligibilityTier;
  final bool gtexHostedEligible;

  factory ClubCompetitionLeaderboardEntry.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'club competition leaderboard entry',
    );
    return ClubCompetitionLeaderboardEntry(
      rank: _intFrom(
        <Map<String, Object?>>[json],
        <String>['rank'],
        fallback: 0,
      ),
      clubId: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['club_id', 'clubId'],
      ),
      clubName: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['club_name', 'clubName'],
      ),
      ownerUserId: _stringOrNullFrom(
        <Map<String, Object?>>[json],
        <String>['owner_user_id', 'ownerUserId'],
      ),
      rankingPoints: _intFrom(
        <Map<String, Object?>>[json],
        <String>['ranking_points', 'rankingPoints'],
        fallback: 0,
      ),
      wins: _intFrom(
        <Map<String, Object?>>[json],
        <String>['wins'],
        fallback: 0,
      ),
      draws: _intFrom(
        <Map<String, Object?>>[json],
        <String>['draws'],
        fallback: 0,
      ),
      losses: _intFrom(
        <Map<String, Object?>>[json],
        <String>['losses'],
        fallback: 0,
      ),
      trophies: _intFrom(
        <Map<String, Object?>>[json],
        <String>['trophies'],
        fallback: 0,
      ),
      recentForm: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['recent_form', 'recentForm'],
        fallback: '',
      ),
      eligibilityTier: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['eligibility_tier', 'eligibilityTier'],
        fallback: 'ladder',
      ),
      gtexHostedEligible: _boolFrom(
        <Map<String, Object?>>[json],
        <String>['gtex_hosted_eligible', 'gtexHostedEligible'],
        fallback: false,
      ),
    );
  }
}

class ClubCompetitionLeaderboardResponse {
  const ClubCompetitionLeaderboardResponse({required this.entries});

  final List<ClubCompetitionLeaderboardEntry> entries;

  factory ClubCompetitionLeaderboardResponse.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'club competition leaderboard',
    );
    return ClubCompetitionLeaderboardResponse(
      entries: GteJson.list(
        _firstValue(<Map<String, Object?>>[json], <String>['entries']) ??
            const <Object?>[],
      ).map(ClubCompetitionLeaderboardEntry.fromJson).toList(growable: false),
    );
  }
}

class RandomCompetitionQuote {
  const RandomCompetitionQuote({
    required this.competitionId,
    required this.competitionName,
    required this.mode,
    required this.currency,
    required this.entryFee,
    required this.grossPot,
    required this.platformFeeAmount,
    required this.netPayoutPot,
    required this.ranked,
    required this.confirmationRequired,
    this.startsAt,
  });

  final String competitionId;
  final String competitionName;
  final String mode;
  final String currency;
  final double entryFee;
  final double grossPot;
  final double platformFeeAmount;
  final double netPayoutPot;
  final bool ranked;
  final DateTime? startsAt;
  final bool confirmationRequired;

  factory RandomCompetitionQuote.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'random competition quote',
    );
    return RandomCompetitionQuote(
      competitionId: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['competition_id', 'competitionId'],
      ),
      competitionName: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['competition_name', 'competitionName'],
      ),
      mode: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['mode'],
        fallback: 'one_v_one',
      ),
      currency: _stringFrom(
        <Map<String, Object?>>[json],
        <String>['currency'],
        fallback: 'credit',
      ),
      entryFee: _doubleFrom(
        <Map<String, Object?>>[json],
        <String>['entry_fee', 'entryFee'],
        fallback: 0,
      ),
      grossPot: _doubleFrom(
        <Map<String, Object?>>[json],
        <String>['gross_pot', 'grossPot'],
        fallback: 0,
      ),
      platformFeeAmount: _doubleFrom(
        <Map<String, Object?>>[json],
        <String>['platform_fee_amount', 'platformFeeAmount'],
        fallback: 0,
      ),
      netPayoutPot: _doubleFrom(
        <Map<String, Object?>>[json],
        <String>['net_payout_pot', 'netPayoutPot'],
        fallback: 0,
      ),
      ranked: _boolFrom(
        <Map<String, Object?>>[json],
        <String>['ranked', 'is_ranked', 'isRanked'],
        fallback: true,
      ),
      startsAt: _dateFrom(
        <Map<String, Object?>>[json],
        <String>['starts_at', 'startsAt'],
      ),
      confirmationRequired: _boolFrom(
        <Map<String, Object?>>[json],
        <String>['confirmation_required', 'confirmationRequired'],
        fallback: true,
      ),
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

MatchType _matchTypeFromMaps(
  Iterable<Map<String, Object?>> sources, {
  required String creatorId,
  required String? creatorName,
  required String name,
}) {
  final String? rawType = _stringOrNullFrom(sources, <String>[
    'match_type',
    'matchType',
    'competition_source',
    'competitionSource',
    'host_type',
    'hostType',
  ]);
  if (rawType != null) {
    return _matchTypeFromString(
      rawType,
      creatorId: creatorId,
      creatorName: creatorName,
      name: name,
    );
  }
  return _matchTypeFromString(
    '',
    creatorId: creatorId,
    creatorName: creatorName,
    name: name,
  );
}

CompetitionDynamicPrizePool? _dynamicPrizePoolFromMaps(
  Iterable<Map<String, Object?>> sources, {
  required double prizePool,
  required double entryFee,
}) {
  final Object? value = _firstValue(sources, <String>[
    'dynamic_prize_pool',
    'dynamicPrizePool',
  ]);
  if (value != null) {
    return CompetitionDynamicPrizePool.fromJson(value);
  }
  if (entryFee <= 0.0001 && prizePool > 0) {
    return CompetitionDynamicPrizePool(
      enabled: true,
      baseFunding: prizePool,
      activityBoost: 0,
      jackpotRollover: 0,
      totalPool: prizePool,
      activeUsers5m: 0,
      tradeVolume5m: 0,
    );
  }
  return null;
}

FastMatchEntitlementView? _fastMatchEntitlementFromMaps(
  Iterable<Map<String, Object?>> sources,
) {
  final Object? nested = _firstValue(sources, <String>[
    'fast_match_entitlement',
    'fastMatchEntitlement',
    'entitlement',
    'fast_match',
    'fastMatch',
  ]);
  if (nested != null) {
    try {
      return FastMatchEntitlementView.fromJson(nested);
    } on GteParsingException {
      return null;
    }
  }
  if (_firstValue(sources, <String>[
        'free_matches_remaining',
        'freeMatchesRemaining',
        'charge_required_now',
        'chargeRequiredNow',
        'fan_coin_entry_fee',
        'fanCoinEntryFee',
      ]) ==
      null) {
    return null;
  }
  final Map<String, Object?> merged = <String, Object?>{};
  for (final Map<String, Object?> source in sources) {
    merged.addAll(source);
  }
  return FastMatchEntitlementView.fromJson(merged);
}

FastCupRegistrationView? _fastCupRegistrationFromMaps(
  Iterable<Map<String, Object?>> sources,
) {
  final Object? nested = _firstValue(sources, <String>[
    'fast_cup_registration',
    'fastCupRegistration',
    'registration',
    'cup_registration',
    'cupRegistration',
    'payment',
  ]);
  if (nested != null) {
    try {
      return FastCupRegistrationView.fromJson(nested);
    } on GteParsingException {
      return null;
    }
  }
  if (_firstValue(sources, <String>[
        'escrow_status',
        'escrowStatus',
        'entry_fee_amount',
        'entryFeeAmount',
        'registration_id',
        'registrationId',
      ]) ==
      null) {
    return null;
  }
  final Map<String, Object?> merged = <String, Object?>{};
  for (final Map<String, Object?> source in sources) {
    merged.addAll(source);
  }
  return FastCupRegistrationView.fromJson(merged);
}

MatchType _matchTypeFromString(
  String value, {
  required String creatorId,
  required String? creatorName,
  required String name,
}) {
  final String normalized = value.trim().toLowerCase();
  if (<String>{
    'gtex_hosted',
    'gtexhosted',
    'platform',
    'platform_run',
    'platformrun',
    'official',
  }.contains(normalized)) {
    return MatchType.gtexHosted;
  }
  if (<String>{'fast_match', 'fastmatch', 'fast'}.contains(normalized)) {
    return MatchType.fastMatch;
  }
  if (<String>{
    'user_hosted',
    'userhosted',
    'creator',
    'creator_hosted',
    'creatorhosted',
  }.contains(normalized)) {
    return MatchType.userHosted;
  }

  final String creatorIdValue = creatorId.trim().toLowerCase();
  final String creatorNameValue = creatorName?.trim().toLowerCase() ?? '';
  final String nameValue = name.trim().toLowerCase();
  if (nameValue.contains('fast match') || nameValue.contains('fast cup')) {
    return MatchType.fastMatch;
  }
  if (creatorIdValue.startsWith('gtex') ||
      creatorIdValue == 'platform' ||
      creatorNameValue == 'gtex' ||
      creatorNameValue.startsWith('gtex ')) {
    return MatchType.gtexHosted;
  }
  return MatchType.userHosted;
}

String _currencyLabel(String currency) {
  final String normalized = currency.trim().toLowerCase();
  if (<String>{
    'credit',
    'credits',
    'fan_coin',
    'fancoin',
    'fan coin',
  }.contains(normalized)) {
    return 'Fan Coin';
  }
  if (<String>{
    'coin',
    'coins',
    'gtex',
    'gtex_coin',
    'gtex coin',
  }.contains(normalized)) {
    return 'GTEX Coin';
  }
  return currency.trim().isEmpty ? 'Fan Coin' : currency.trim().toUpperCase();
}

String _formatUnitAmount(double value, String unitLabel) {
  final bool whole = value == value.roundToDouble();
  return '${value.toStringAsFixed(whole ? 0 : 2)} $unitLabel';
}

String _sentenceCase(String value) {
  final String normalized = value.replaceAll('_', ' ').trim();
  if (normalized.isEmpty) {
    return value;
  }
  return normalized[0].toUpperCase() + normalized.substring(1);
}

Object? _firstValue(Iterable<Map<String, Object?>> sources, List<String> keys) {
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
    throw GteParsingException(
      'Missing required string field: ${keys.join(' / ')}.',
    );
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

DateTime? _dateFrom(Iterable<Map<String, Object?>> sources, List<String> keys) {
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

bool _boolFrom(
  Iterable<Map<String, Object?>> sources,
  List<String> keys, {
  bool fallback = false,
}) {
  return _boolOrNullFrom(sources, keys) ?? fallback;
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

Map<String, double> _doubleMapFrom(Object? value) {
  final Map<String, Object?> json = _mapOrEmpty(value);
  if (json.isEmpty) {
    return const <String, double>{};
  }
  return json.map(
    (String key, Object? raw) =>
        MapEntry<String, double>(key, _doubleValue(raw)),
  );
}

double _doubleValue(Object? value) {
  if (value is num) {
    return value.toDouble();
  }
  return double.tryParse(value?.toString() ?? '') ?? 0;
}

List<CompetitionPayoutBreakdown> _payoutsFrom(Object? value) {
  if (value == null) {
    return const <CompetitionPayoutBreakdown>[];
  }
  try {
    return GteJson.list(
      value,
    ).map(CompetitionPayoutBreakdown.fromJson).toList(growable: false);
  } on GteParsingException {
    return const <CompetitionPayoutBreakdown>[];
  }
}
