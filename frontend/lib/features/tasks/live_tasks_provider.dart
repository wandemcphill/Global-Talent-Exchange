import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/gte_authed_api.dart';
import '../../features/shared/data/gte_feature_support.dart';
import '../../shared/providers/auth_provider.dart';

class DailyChallengeSummary {
  const DailyChallengeSummary({
    required this.challengeKey,
    required this.title,
    required this.description,
    required this.rewardSummary,
    required this.claimLimitPerDay,
    required this.claimedToday,
    required this.availableToday,
  });

  final String challengeKey;
  final String title;
  final String description;
  final String rewardSummary;
  final int claimLimitPerDay;
  final bool claimedToday;
  final bool availableToday;
}

class DailyChallengeClaimSummary {
  const DailyChallengeClaimSummary({
    required this.claimId,
    required this.challengeKey,
    required this.challengeTitle,
    required this.rewardLabel,
    required this.bonusAwardedLabel,
    required this.claimedAt,
    required this.streakBeforeClaim,
  });

  final String claimId;
  final String challengeKey;
  final String challengeTitle;
  final String rewardLabel;
  final String bonusAwardedLabel;
  final DateTime? claimedAt;
  final int streakBeforeClaim;

  bool get bonusAwarded => bonusAwardedLabel.isNotEmpty;

  String get rewardDetail =>
      bonusAwarded
          ? 'Settled reward $rewardLabel with streak bonus $bonusAwardedLabel.'
          : 'Settled reward $rewardLabel.';
}

class DailyChallengeClaimFeedback {
  const DailyChallengeClaimFeedback({
    required this.challengeTitle,
    required this.rewardSummary,
    required this.rewardLabel,
    required this.currentStreak,
    required this.nextBonusAmount,
    required this.streakAdvanced,
    required this.bonusAwardedLabel,
  });

  factory DailyChallengeClaimFeedback.fromResponse(
    Object? payload, {
    required LiveTasksData refreshedTasks,
  }) {
    final JsonMap response = jsonMap(
      payload,
      label: 'daily challenge claim response',
    );
    final JsonMap challenge = jsonMap(
      response['challenge'],
      label: 'daily challenge',
    );
    final JsonMap claim = jsonMap(response['claim'], label: 'daily challenge');
    final JsonMap metadata = jsonMap(
      claim['metadata_json'],
      label: 'daily challenge metadata',
      fallback: const <String, Object?>{},
    );
    final String rewardUnit = stringValue(claim['reward_unit']);
    final String rewardLabel = _formatRewardLabel(
      numberValue(claim['reward_amount']),
      rewardUnit,
    );
    final double bonusAwardedAmount = numberValue(metadata['bonus_amount']);
    final String challengeTitle = stringValue(
      challenge['title'],
      fallback: stringValue(
        challenge['challenge_key'],
        fallback: 'Daily challenge',
      ),
    );
    return DailyChallengeClaimFeedback(
      challengeTitle: challengeTitle,
      rewardSummary: stringValue(
        response['reward_summary'],
        fallback: _fallbackRewardSummary(rewardLabel, challengeTitle),
      ),
      rewardLabel: rewardLabel,
      currentStreak: refreshedTasks.currentStreak,
      nextBonusAmount: refreshedTasks.nextBonusAmount,
      streakAdvanced:
          refreshedTasks.currentStreak >
          intValue(metadata['streak_before_claim']),
      bonusAwardedLabel:
          bonusAwardedAmount > 0
              ? _formatRewardLabel(bonusAwardedAmount, rewardUnit)
              : '',
    );
  }

  final String challengeTitle;
  final String rewardSummary;
  final String rewardLabel;
  final int currentStreak;
  final double nextBonusAmount;
  final bool streakAdvanced;
  final String bonusAwardedLabel;

  bool get bonusAwarded => bonusAwardedLabel.isNotEmpty;

  String get nextBonusLabel =>
      'Next bonus ${_formatCompactNumber(nextBonusAmount)}';

  String get statusMessage {
    final List<String> parts = <String>[rewardSummary];
    if (bonusAwarded) {
      parts.add('Included streak bonus $bonusAwardedLabel.');
    }
    parts.add(
      streakAdvanced
          ? 'Login streak is now $currentStreak.'
          : 'Login streak remains $currentStreak.',
    );
    parts.add('$nextBonusLabel.');
    return parts.join(' ');
  }
}

class LiveTasksData {
  const LiveTasksData({
    required this.authenticated,
    required this.featureEnabled,
    required this.challenges,
    required this.claimsToday,
    required this.currentStreak,
    required this.longestStreak,
    required this.nextBonusAmount,
  });

  final bool authenticated;
  final bool featureEnabled;
  final List<DailyChallengeSummary> challenges;
  final List<DailyChallengeClaimSummary> claimsToday;
  final int currentStreak;
  final int longestStreak;
  final double nextBonusAmount;
}

final FutureProvider<LiveTasksData> liveTasksProvider =
    FutureProvider<LiveTasksData>((Ref ref) async {
      final GteAuthedApi api = ref.watch(authedApiProvider);
      final bool authenticated = ref.watch(isAuthenticatedProvider);
      final JsonMap challengesPayload = await api.getMap(
        '/api/daily-challenges',
        auth: false,
      );
      JsonMap? mePayload;
      if (authenticated) {
        mePayload = await api.getMap('/api/daily-challenges/me');
      }
      final List<JsonMap> claimsPayload = jsonMapList(
        mePayload?['claims_today'],
        label: 'daily challenge claims',
      );
      final List<String> availableKeys = stringListValue(
        mePayload?['available_challenge_keys'],
      );
      final Map<String, String> titlesByKey = <String, String>{};
      final Set<String> claimedTodayKeys =
          claimsPayload
              .map(
                (JsonMap item) => stringValue(
                  jsonMap(
                    item['metadata_json'],
                    label: 'daily challenge claim metadata',
                    fallback: const <String, Object?>{},
                  )['challenge_key'],
                ),
              )
              .where((String challengeKey) => challengeKey.isNotEmpty)
              .toSet();
      final List<DailyChallengeSummary> challenges = jsonMapList(
            challengesPayload['challenges'],
            label: 'daily challenges',
          )
          .map((JsonMap item) {
            final String challengeKey = stringValue(item['challenge_key']);
            final String title = stringValue(item['title']);
            titlesByKey[challengeKey] = title;
            return DailyChallengeSummary(
              challengeKey: challengeKey,
              title: title,
              description: stringValue(item['description']),
              rewardSummary: _formatRewardLabel(
                numberValue(item['reward_amount']),
                stringValue(item['reward_unit']),
              ),
              claimLimitPerDay: intValue(item['claim_limit_per_day']),
              claimedToday: claimedTodayKeys.contains(challengeKey),
              availableToday:
                  !authenticated || availableKeys.contains(challengeKey),
            );
          })
          .toList(growable: false);
      final List<DailyChallengeClaimSummary> claimsToday = claimsPayload
          .map(
            (JsonMap item) =>
                _claimSummaryFromPayload(item, challengeTitles: titlesByKey),
          )
          .toList(growable: false);
      final JsonMap streak = jsonMap(
        mePayload?['login_streak'],
        label: 'daily login streak',
        fallback: const <String, Object?>{},
      );
      return LiveTasksData(
        authenticated: authenticated,
        featureEnabled: boolValue(challengesPayload['feature_enabled']),
        challenges: challenges,
        claimsToday: claimsToday,
        currentStreak: intValue(streak['current_streak']),
        longestStreak: intValue(streak['longest_streak']),
        nextBonusAmount: numberValue(streak['next_bonus_amount']),
      );
    });

DailyChallengeClaimSummary _claimSummaryFromPayload(
  JsonMap item, {
  required Map<String, String> challengeTitles,
}) {
  final JsonMap metadata = jsonMap(
    item['metadata_json'],
    label: 'daily challenge claim metadata',
    fallback: const <String, Object?>{},
  );
  final String challengeKey = stringValue(metadata['challenge_key']);
  final String rewardUnit = stringValue(item['reward_unit']);
  final double bonusAmount = numberValue(metadata['bonus_amount']);
  return DailyChallengeClaimSummary(
    claimId: stringValue(item['id']),
    challengeKey: challengeKey,
    challengeTitle:
        challengeTitles[challengeKey] ??
        stringValue(item['challenge_id'], fallback: 'Daily challenge'),
    rewardLabel: _formatRewardLabel(
      numberValue(item['reward_amount']),
      rewardUnit,
    ),
    bonusAwardedLabel:
        bonusAmount > 0 ? _formatRewardLabel(bonusAmount, rewardUnit) : '',
    claimedAt: dateTimeValue(item['claimed_at']),
    streakBeforeClaim: intValue(metadata['streak_before_claim']),
  );
}

String _fallbackRewardSummary(String rewardLabel, String challengeTitle) {
  if (rewardLabel.isEmpty) {
    return 'Daily challenge claimed.';
  }
  return 'Claimed $rewardLabel from $challengeTitle.';
}

String _formatRewardLabel(double amount, String unit) {
  final String normalizedUnit = unit.trim();
  final String amountLabel = _formatCompactNumber(amount);
  if (normalizedUnit.isEmpty) {
    return amountLabel;
  }
  return '$amountLabel $normalizedUnit';
}

String _formatCompactNumber(double value) {
  if (value == value.roundToDouble()) {
    return value.toStringAsFixed(0);
  }
  String text = value.toStringAsFixed(4);
  text = text.replaceFirst(RegExp(r'0+$'), '');
  if (text.endsWith('.')) {
    text = text.substring(0, text.length - 1);
  }
  return text;
}
