import 'package:gte_frontend/data/gte_models.dart';

import '../features/admin_command_redesign/models/gtex_admin_command_models.dart';

class JackpotAdminRuntime {
  const JackpotAdminRuntime({
    required this.roundId,
    required this.roundNumber,
    required this.status,
    required this.balance,
    required this.thresholdAmount,
    required this.probabilityLimit,
    required this.probabilityCap,
    required this.contributionRate,
    required this.participantCount,
    required this.failsafeAt,
    required this.distributionMode,
    required this.topSplitPercent,
    required this.minActivityScore,
    required this.failsafeHours,
    this.lastWinnerUserId,
    this.lastTriggerMode,
  });

  final String roundId;
  final int roundNumber;
  final String status;
  final String balance;
  final String thresholdAmount;
  final String probabilityLimit;
  final String probabilityCap;
  final String contributionRate;
  final int participantCount;
  final DateTime failsafeAt;
  final String distributionMode;
  final String topSplitPercent;
  final String minActivityScore;
  final int failsafeHours;
  final String? lastWinnerUserId;
  final String? lastTriggerMode;

  factory JackpotAdminRuntime.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'jackpot admin runtime');
    return JackpotAdminRuntime(
      roundId: GteJson.string(json, <String>['round_id', 'roundId']),
      roundNumber: GteJson.integer(json, <String>['round_number', 'roundNumber']),
      status: GteJson.string(json, <String>['status'], fallback: 'unknown'),
      balance: GteJson.string(json, <String>['balance'], fallback: '0'),
      thresholdAmount: GteJson.string(
        json,
        <String>['threshold_amount', 'thresholdAmount'],
        fallback: '0',
      ),
      probabilityLimit: GteJson.string(
        json,
        <String>['probability_limit', 'probabilityLimit'],
        fallback: '0',
      ),
      probabilityCap: GteJson.string(
        json,
        <String>['probability_cap', 'probabilityCap'],
        fallback: '0',
      ),
      contributionRate: GteJson.string(
        json,
        <String>['contribution_rate', 'contributionRate'],
        fallback: '0',
      ),
      participantCount: GteJson.integer(
        json,
        <String>['participant_count', 'participantCount'],
        fallback: 0,
      ),
      failsafeAt: GteJson.dateTime(json, <String>['failsafe_at', 'failsafeAt']),
      distributionMode: GteJson.string(
        json,
        <String>['distribution_mode', 'distributionMode'],
        fallback: 'single_winner',
      ),
      topSplitPercent: GteJson.string(
        json,
        <String>['top_split_percent', 'topSplitPercent'],
        fallback: '0',
      ),
      minActivityScore: GteJson.string(
        json,
        <String>['min_activity_score', 'minActivityScore'],
        fallback: '0',
      ),
      failsafeHours: GteJson.integer(
        json,
        <String>['failsafe_hours', 'failsafeHours'],
        fallback: 1,
      ),
      lastWinnerUserId: GteJson.stringOrNull(
        json,
        <String>['last_winner_user_id', 'lastWinnerUserId'],
      ),
      lastTriggerMode: GteJson.stringOrNull(
        json,
        <String>['last_trigger_mode', 'lastTriggerMode'],
      ),
    );
  }

  GtexJackpotRound toRoundTile() {
    return GtexJackpotRound(
      id: roundId,
      title: 'Round $roundNumber',
      poolLabel: '$balance GTEX',
      status: status.toUpperCase(),
      entriesLabel: '$participantCount participants',
      drawTimeLabel: 'Failsafe ${failsafeAt.toLocal()}',
      winnerLabel: lastWinnerUserId == null
          ? 'No winner yet'
          : 'Last winner $lastWinnerUserId',
    );
  }

  Map<String, Object?> toSettingsBody() {
    return <String, Object?>{
      'threshold_amount': thresholdAmount,
      'probability_limit': probabilityLimit,
      'probability_cap': probabilityCap,
      'failsafe_hours': failsafeHours,
      'contribution_rate': contributionRate,
      'distribution_mode': distributionMode,
      'top_split_percent': topSplitPercent,
      'min_activity_score': minActivityScore,
    };
  }
}

class JackpotHistoryItem {
  const JackpotHistoryItem({
    required this.id,
    required this.roundNumber,
    required this.status,
    required this.distributionMode,
    required this.currentBalance,
    this.winningUserId,
    this.triggeredAt,
    this.settledAt,
  });

  final String id;
  final int roundNumber;
  final String status;
  final String distributionMode;
  final String currentBalance;
  final String? winningUserId;
  final DateTime? triggeredAt;
  final DateTime? settledAt;

  factory JackpotHistoryItem.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'jackpot history item');
    return JackpotHistoryItem(
      id: GteJson.string(json, <String>['id']),
      roundNumber: GteJson.integer(json, <String>['round_number', 'roundNumber']),
      status: GteJson.string(json, <String>['status'], fallback: 'unknown'),
      distributionMode: GteJson.string(
        json,
        <String>['distribution_mode', 'distributionMode'],
        fallback: 'single_winner',
      ),
      currentBalance: GteJson.string(
        json,
        <String>['current_balance', 'currentBalance'],
        fallback: '0',
      ),
      winningUserId: GteJson.stringOrNull(
        json,
        <String>['winning_user_id', 'winningUserId'],
      ),
      triggeredAt: GteJson.dateTimeOrNull(
        json,
        <String>['triggered_at', 'triggeredAt'],
      ),
      settledAt: GteJson.dateTimeOrNull(
        json,
        <String>['settled_at', 'settledAt'],
      ),
    );
  }
}
