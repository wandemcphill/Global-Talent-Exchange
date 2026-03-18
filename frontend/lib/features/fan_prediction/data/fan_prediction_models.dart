import '../../shared/data/gte_feature_support.dart';

class FanPredictionFixtureConfigRequest {
  const FanPredictionFixtureConfigRequest({
    this.title,
    this.description,
    this.opensAt,
    this.locksAt,
    this.tokenCost = 1,
    this.promoPoolFancoin = 0,
    this.badgeCode,
    this.maxRewardWinners = 3,
    this.allowCreatorClubSegmentation = true,
    this.metadata = const <String, Object?>{},
  });

  final String? title;
  final String? description;
  final DateTime? opensAt;
  final DateTime? locksAt;
  final int tokenCost;
  final double promoPoolFancoin;
  final String? badgeCode;
  final int maxRewardWinners;
  final bool allowCreatorClubSegmentation;
  final JsonMap metadata;

  JsonMap toJson() => <String, Object?>{
        if (title != null) 'title': title,
        if (description != null) 'description': description,
        if (opensAt != null) 'opens_at': opensAt!.toUtc().toIso8601String(),
        if (locksAt != null) 'locks_at': locksAt!.toUtc().toIso8601String(),
        'token_cost': tokenCost,
        'promo_pool_fancoin': promoPoolFancoin,
        if (badgeCode != null) 'badge_code': badgeCode,
        'max_reward_winners': maxRewardWinners,
        'allow_creator_club_segmentation': allowCreatorClubSegmentation,
        'metadata_json': metadata,
      };
}

class FanPredictionOutcomeOverrideRequest {
  const FanPredictionOutcomeOverrideRequest({
    this.winnerClubId,
    this.firstGoalScorerPlayerId,
    this.totalGoals,
    this.mvpPlayerId,
    this.note,
    this.disburseRewards = true,
    this.metadata = const <String, Object?>{},
  });

  final String? winnerClubId;
  final String? firstGoalScorerPlayerId;
  final int? totalGoals;
  final String? mvpPlayerId;
  final String? note;
  final bool disburseRewards;
  final JsonMap metadata;

  JsonMap toJson() => <String, Object?>{
        if (winnerClubId != null) 'winner_club_id': winnerClubId,
        if (firstGoalScorerPlayerId != null)
          'first_goal_scorer_player_id': firstGoalScorerPlayerId,
        if (totalGoals != null) 'total_goals': totalGoals,
        if (mvpPlayerId != null) 'mvp_player_id': mvpPlayerId,
        if (note != null) 'note': note,
        'disburse_rewards': disburseRewards,
        'metadata_json': metadata,
      };
}

class FanPredictionSubmissionRequest {
  const FanPredictionSubmissionRequest({
    required this.winnerClubId,
    required this.firstGoalScorerPlayerId,
    required this.totalGoals,
    required this.mvpPlayerId,
    this.fanSegmentClubId,
    this.fanGroupId,
    this.metadata = const <String, Object?>{},
  });

  final String winnerClubId;
  final String firstGoalScorerPlayerId;
  final int totalGoals;
  final String mvpPlayerId;
  final String? fanSegmentClubId;
  final String? fanGroupId;
  final JsonMap metadata;

  JsonMap toJson() => <String, Object?>{
        'winner_club_id': winnerClubId,
        'first_goal_scorer_player_id': firstGoalScorerPlayerId,
        'total_goals': totalGoals,
        'mvp_player_id': mvpPlayerId,
        if (fanSegmentClubId != null) 'fan_segment_club_id': fanSegmentClubId,
        if (fanGroupId != null) 'fan_group_id': fanGroupId,
        'metadata_json': metadata,
      };
}

class FanPredictionLeaderboardQuery {
  const FanPredictionLeaderboardQuery({
    this.weekStart,
    this.limit = 25,
  });

  final DateTime? weekStart;
  final int limit;

  Map<String, Object?> toQuery() => compactQuery(<String, Object?>{
        'week_start': dateQueryValue(weekStart),
        'limit': limit,
      });
}

class FanPredictionMatchLeaderboardQuery {
  const FanPredictionMatchLeaderboardQuery({
    this.limit = 20,
  });

  final int limit;

  Map<String, Object?> toQuery() => <String, Object?>{'limit': limit};
}

class FanPredictionSubmission {
  const FanPredictionSubmission._(this.raw);

  final JsonMap raw;

  factory FanPredictionSubmission.fromJson(Object? value) {
    return FanPredictionSubmission._(
      jsonMap(value, label: 'fan prediction submission'),
    );
  }

  String get id => stringValue(raw['id']);
  String get fixtureId => stringValue(raw['fixture_id']);
  String get userId => stringValue(raw['user_id']);
  String? get fanSegmentClubId => stringOrNullValue(raw['fan_segment_club_id']);
  String? get fanGroupId => stringOrNullValue(raw['fan_group_id']);
  String get winnerClubId => stringValue(raw['winner_club_id']);
  String get firstGoalScorerPlayerId =>
      stringValue(raw['first_goal_scorer_player_id']);
  int get totalGoals => intValue(raw['total_goals']);
  String get mvpPlayerId => stringValue(raw['mvp_player_id']);
  int get tokensSpent => intValue(raw['tokens_spent']);
  String get status => stringValue(raw['status']);
  int get pointsAwarded => intValue(raw['points_awarded']);
  int get correctPickCount => intValue(raw['correct_pick_count']);
  bool get perfectCard => boolValue(raw['perfect_card']);
  int? get rewardRank =>
      raw['reward_rank'] == null ? null : intValue(raw['reward_rank']);
  DateTime? get settledAt => dateTimeValue(raw['settled_at']);
  JsonMap get metadata =>
      jsonMap(raw['metadata_json'], fallback: const <String, Object?>{});
  DateTime? get createdAt => dateTimeValue(raw['created_at']);
  DateTime? get updatedAt => dateTimeValue(raw['updated_at']);
}

class FanPredictionFixture {
  const FanPredictionFixture._(this.raw);

  final JsonMap raw;

  factory FanPredictionFixture.fromJson(Object? value) {
    return FanPredictionFixture._(
      jsonMap(value, label: 'fan prediction fixture'),
    );
  }

  String get id => stringValue(raw['id']);
  String get matchId => stringValue(raw['match_id']);
  String get competitionId => stringValue(raw['competition_id']);
  String? get seasonId => stringOrNullValue(raw['season_id']);
  String get homeClubId => stringValue(raw['home_club_id']);
  String get awayClubId => stringValue(raw['away_club_id']);
  String get title => stringValue(raw['title']);
  String? get description => stringOrNullValue(raw['description']);
  String get status => stringValue(raw['status']);
  DateTime? get opensAt => dateTimeValue(raw['opens_at']);
  DateTime? get locksAt => dateTimeValue(raw['locks_at']);
  DateTime? get settledAt => dateTimeValue(raw['settled_at']);
  int get tokenCost => intValue(raw['token_cost']);
  double get promoPoolFancoin => numberValue(raw['promo_pool_fancoin']);
  String get rewardFundingSource => stringValue(raw['reward_funding_source']);
  String? get badgeCode => stringOrNullValue(raw['badge_code']);
  int get maxRewardWinners => intValue(raw['max_reward_winners']);
  bool get allowCreatorClubSegmentation =>
      boolValue(raw['allow_creator_club_segmentation']);
  String get settlementRuleVersion =>
      stringValue(raw['settlement_rule_version']);
  JsonMap get metadata =>
      jsonMap(raw['metadata_json'], fallback: const <String, Object?>{});
  JsonMap get scoring =>
      jsonMap(raw['scoring'], fallback: const <String, Object?>{});
  JsonMap? get outcome => jsonMapOrNull(raw['outcome']);
  FanPredictionSubmission? get mySubmission {
    final JsonMap? payload = jsonMapOrNull(raw['my_submission']);
    if (payload == null) {
      return null;
    }
    return FanPredictionSubmission.fromJson(payload);
  }

  List<JsonMap> get rewardGrants =>
      jsonMapList(raw['reward_grants'], label: 'fan prediction reward grants');
  DateTime? get createdAt => dateTimeValue(raw['created_at']);
  DateTime? get updatedAt => dateTimeValue(raw['updated_at']);
}

class FanPredictionTokenSummary {
  const FanPredictionTokenSummary._(this.raw);

  final JsonMap raw;

  factory FanPredictionTokenSummary.fromJson(Object? value) {
    return FanPredictionTokenSummary._(
      jsonMap(value, label: 'fan prediction token summary'),
    );
  }

  int get availableTokens => intValue(raw['available_tokens']);
  int get dailyRefillTokens => intValue(raw['daily_refill_tokens']);
  int get seasonPassBonusTokens => intValue(raw['season_pass_bonus_tokens']);
  int get todayTokenGrants => intValue(raw['today_token_grants']);
  String? get latestEffectiveDate =>
      stringOrNullValue(raw['latest_effective_date']);
  List<JsonMap> get ledger =>
      jsonMapList(raw['ledger'], label: 'fan prediction token ledger');
}

class FanPredictionLeaderboard {
  const FanPredictionLeaderboard._(this.raw);

  final JsonMap raw;

  factory FanPredictionLeaderboard.fromJson(Object? value) {
    return FanPredictionLeaderboard._(
      jsonMap(value, label: 'fan prediction leaderboard'),
    );
  }

  String get scope => stringValue(raw['scope']);
  String get weekStart => stringValue(raw['week_start']);
  String? get fixtureId => stringOrNullValue(raw['fixture_id']);
  String? get clubId => stringOrNullValue(raw['club_id']);
  List<JsonMap> get entries =>
      jsonMapList(raw['entries'], label: 'fan prediction leaderboard entries');
}
