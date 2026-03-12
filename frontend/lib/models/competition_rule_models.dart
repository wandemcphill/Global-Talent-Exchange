import 'package:gte_frontend/models/competition_models.dart';

enum CompetitionTieBreaker {
  headToHead,
  scoreDifference,
  playoffRound,
}

class CompetitionRuleSet {
  const CompetitionRuleSet({
    required this.allowLateJoin,
    required this.lineupLockMinutes,
    required this.reviewWindowHours,
    required this.tieBreaker,
    required this.requireVerification,
    required this.showEscrowLedger,
  });

  final bool allowLateJoin;
  final int lineupLockMinutes;
  final int reviewWindowHours;
  final CompetitionTieBreaker tieBreaker;
  final bool requireVerification;
  final bool showEscrowLedger;

  factory CompetitionRuleSet.defaults(CompetitionFormat format) {
    return CompetitionRuleSet(
      allowLateJoin: format == CompetitionFormat.league,
      lineupLockMinutes: format == CompetitionFormat.league ? 30 : 45,
      reviewWindowHours: 12,
      tieBreaker: format == CompetitionFormat.league
          ? CompetitionTieBreaker.headToHead
          : CompetitionTieBreaker.playoffRound,
      requireVerification: true,
      showEscrowLedger: true,
    );
  }

  CompetitionRuleSet copyWith({
    bool? allowLateJoin,
    int? lineupLockMinutes,
    int? reviewWindowHours,
    CompetitionTieBreaker? tieBreaker,
    bool? requireVerification,
    bool? showEscrowLedger,
  }) {
    return CompetitionRuleSet(
      allowLateJoin: allowLateJoin ?? this.allowLateJoin,
      lineupLockMinutes:
          _clamp(lineupLockMinutes ?? this.lineupLockMinutes, 15, 180),
      reviewWindowHours:
          _clamp(reviewWindowHours ?? this.reviewWindowHours, 2, 48),
      tieBreaker: tieBreaker ?? this.tieBreaker,
      requireVerification: requireVerification ?? this.requireVerification,
      showEscrowLedger: showEscrowLedger ?? this.showEscrowLedger,
    );
  }

  List<String> bullets(CompetitionFormat format) {
    return <String>[
      format == CompetitionFormat.league
          ? 'Skill league standings use verified performance totals.'
          : 'Skill cup advancement follows verified head-to-head results.',
      allowLateJoin
          ? 'Late entries remain available until the first scoring window closes.'
          : 'Entries lock before the first scoring window begins.',
      'Lineups lock $lineupLockMinutes minutes before each scoring window.',
      'Result review stays open for $reviewWindowHours hours.',
      switch (tieBreaker) {
        CompetitionTieBreaker.headToHead =>
          'Ties resolve by head-to-head results before score difference.',
        CompetitionTieBreaker.scoreDifference =>
          'Ties resolve by score difference before head-to-head results.',
        CompetitionTieBreaker.playoffRound =>
          'Ties trigger an extra playoff round under the published rules.',
      },
      requireVerification
          ? 'Results are verified before the transparent payout settles.'
          : 'Results settle automatically at the end of the review window.',
      showEscrowLedger
          ? 'Entry fees move into secure escrow until results settle.'
          : 'Entry fees still follow the published payout summary.',
    ];
  }

  String summary(CompetitionFormat format) {
    final String text = bullets(format).take(4).join(' ');
    if (text.length <= 280) {
      return text;
    }
    return '${text.substring(0, 277).trimRight()}...';
  }
}

class CompetitionDraftPayoutRule {
  const CompetitionDraftPayoutRule({
    required this.place,
    required this.percent,
  });

  final int place;
  final double percent;

  CompetitionDraftPayoutRule copyWith({
    int? place,
    double? percent,
  }) {
    return CompetitionDraftPayoutRule(
      place: place ?? this.place,
      percent: percent ?? this.percent,
    );
  }
}

class CompetitionDraft {
  const CompetitionDraft({
    required this.name,
    required this.format,
    required this.visibility,
    required this.entryFee,
    required this.currency,
    required this.capacity,
    required this.creatorId,
    required this.creatorName,
    required this.payoutRules,
    required this.platformFeePct,
    required this.hostFeePct,
    required this.rules,
    required this.beginnerFriendly,
    this.competitionId,
  });

  final String? competitionId;
  final String name;
  final CompetitionFormat format;
  final CompetitionVisibility visibility;
  final double entryFee;
  final String currency;
  final int capacity;
  final String creatorId;
  final String? creatorName;
  final List<CompetitionDraftPayoutRule> payoutRules;
  final double platformFeePct;
  final double hostFeePct;
  final CompetitionRuleSet rules;
  final bool beginnerFriendly;

  factory CompetitionDraft.initial({
    required String creatorId,
    String? creatorName,
  }) {
    return CompetitionDraft(
      name: '',
      format: CompetitionFormat.league,
      visibility: CompetitionVisibility.public,
      entryFee: 12,
      currency: 'credit',
      capacity: 12,
      creatorId: creatorId,
      creatorName: creatorName,
      payoutRules: defaultPayoutRules(winnerCount: 3),
      platformFeePct: 0.10,
      hostFeePct: 0.00,
      rules: CompetitionRuleSet.defaults(CompetitionFormat.league),
      beginnerFriendly: true,
    );
  }

  bool get isPaid => entryFee > 0.0001;

  String get safeFormatLabel =>
      format == CompetitionFormat.league ? 'Skill league' : 'Skill cup';

  double get payoutTotal {
    return payoutRules.fold<double>(
      0,
      (double sum, CompetitionDraftPayoutRule rule) => sum + rule.percent,
    );
  }

  double get grossPoolAtCapacity => entryFee * capacity;

  double get projectedPlatformFee => grossPoolAtCapacity * platformFeePct;

  double get projectedHostFee => grossPoolAtCapacity * hostFeePct;

  double get projectedPrizePool =>
      grossPoolAtCapacity - projectedPlatformFee - projectedHostFee;

  String get rulesSummary => rules.summary(format);

  List<String> get validationErrors {
    final List<String> errors = <String>[];
    if (name.trim().length < 3) {
      errors.add('Name must be at least 3 characters.');
    }
    if (capacity < 2 || capacity > 500) {
      errors.add('Capacity must stay between 2 and 500 players.');
    }
    if (entryFee < 0 || entryFee > 10000) {
      errors.add('Entry fee must stay between 0 and 10,000 credits.');
    }
    if (platformFeePct < 0 || platformFeePct > 0.20) {
      errors.add('Platform service fee must stay between 0% and 20%.');
    }
    if (hostFeePct < 0 || hostFeePct > 0.15) {
      errors.add('Host fee must stay between 0% and 15%.');
    }
    if ((platformFeePct + hostFeePct) > 0.25) {
      errors.add('Combined fees must stay at or below 25% of entry fees.');
    }
    if (payoutRules.isEmpty) {
      errors.add('Add at least one payout position.');
    }
    if (payoutRules.length > capacity) {
      errors.add('Payout positions cannot exceed the competition capacity.');
    }
    if ((payoutTotal - 1).abs() > 0.0001) {
      errors.add('Payout percentages must total 100% of the prize pool.');
    }
    return errors;
  }

  CompetitionDraft copyWith({
    String? competitionId,
    String? name,
    CompetitionFormat? format,
    CompetitionVisibility? visibility,
    double? entryFee,
    String? currency,
    int? capacity,
    String? creatorId,
    String? creatorName,
    List<CompetitionDraftPayoutRule>? payoutRules,
    double? platformFeePct,
    double? hostFeePct,
    CompetitionRuleSet? rules,
    bool? beginnerFriendly,
  }) {
    final CompetitionFormat nextFormat = format ?? this.format;
    return CompetitionDraft(
      competitionId: competitionId ?? this.competitionId,
      name: name ?? this.name,
      format: nextFormat,
      visibility: visibility ?? this.visibility,
      entryFee: _clampDouble(entryFee ?? this.entryFee, 0, 10000),
      currency: currency ?? this.currency,
      capacity: _clamp(capacity ?? this.capacity, 2, 500),
      creatorId: creatorId ?? this.creatorId,
      creatorName: creatorName ?? this.creatorName,
      payoutRules: payoutRules ?? this.payoutRules,
      platformFeePct:
          _clampDouble(platformFeePct ?? this.platformFeePct, 0, 0.20),
      hostFeePct: _clampDouble(hostFeePct ?? this.hostFeePct, 0, 0.15),
      rules: rules ?? this.rules,
      beginnerFriendly: beginnerFriendly ?? this.beginnerFriendly,
    );
  }

  Map<String, Object?> toCreateRequestJson() {
    return <String, Object?>{
      'name': name.trim(),
      'format': format.name,
      'visibility': _visibilityWireValue(visibility),
      'entry_fee': entryFee.toStringAsFixed(2),
      'currency': currency,
      'capacity': capacity,
      'creator_id': creatorId,
      if (creatorName != null && creatorName!.trim().isNotEmpty)
        'creator_name': creatorName!.trim(),
      'payout_structure': payoutRules
          .map(
            (CompetitionDraftPayoutRule rule) => <String, Object?>{
              'place': rule.place,
              'percent': rule.percent.toStringAsFixed(4),
            },
          )
          .toList(growable: false),
      'platform_fee_pct': platformFeePct.toStringAsFixed(4),
      'host_fee_pct': hostFeePct.toStringAsFixed(4),
      'rules_summary': rulesSummary,
      'beginner_friendly': beginnerFriendly,
    };
  }
}

List<CompetitionDraftPayoutRule> defaultPayoutRules({
  required int winnerCount,
}) {
  switch (winnerCount) {
    case 1:
      return const <CompetitionDraftPayoutRule>[
        CompetitionDraftPayoutRule(place: 1, percent: 1.0),
      ];
    case 2:
      return const <CompetitionDraftPayoutRule>[
        CompetitionDraftPayoutRule(place: 1, percent: 0.65),
        CompetitionDraftPayoutRule(place: 2, percent: 0.35),
      ];
    case 4:
      return const <CompetitionDraftPayoutRule>[
        CompetitionDraftPayoutRule(place: 1, percent: 0.45),
        CompetitionDraftPayoutRule(place: 2, percent: 0.25),
        CompetitionDraftPayoutRule(place: 3, percent: 0.18),
        CompetitionDraftPayoutRule(place: 4, percent: 0.12),
      ];
    case 5:
      return const <CompetitionDraftPayoutRule>[
        CompetitionDraftPayoutRule(place: 1, percent: 0.40),
        CompetitionDraftPayoutRule(place: 2, percent: 0.24),
        CompetitionDraftPayoutRule(place: 3, percent: 0.16),
        CompetitionDraftPayoutRule(place: 4, percent: 0.12),
        CompetitionDraftPayoutRule(place: 5, percent: 0.08),
      ];
    case 3:
    default:
      return const <CompetitionDraftPayoutRule>[
        CompetitionDraftPayoutRule(place: 1, percent: 0.50),
        CompetitionDraftPayoutRule(place: 2, percent: 0.30),
        CompetitionDraftPayoutRule(place: 3, percent: 0.20),
      ];
  }
}

String _visibilityWireValue(CompetitionVisibility visibility) {
  switch (visibility) {
    case CompetitionVisibility.private:
      return 'private';
    case CompetitionVisibility.inviteOnly:
      return 'invite_only';
    case CompetitionVisibility.public:
      return 'public';
  }
}

int _clamp(int value, int min, int max) {
  if (value < min) {
    return min;
  }
  if (value > max) {
    return max;
  }
  return value;
}

double _clampDouble(double value, double min, double max) {
  if (value < min) {
    return min;
  }
  if (value > max) {
    return max;
  }
  return value;
}
