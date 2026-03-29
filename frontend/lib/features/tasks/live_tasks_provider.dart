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
    required this.availableToday,
  });

  final String challengeKey;
  final String title;
  final String description;
  final String rewardSummary;
  final int claimLimitPerDay;
  final bool availableToday;
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
  final List<JsonMap> claimsToday;
  final int currentStreak;
  final int longestStreak;
  final double nextBonusAmount;
}

final FutureProvider<LiveTasksData>
liveTasksProvider = FutureProvider<LiveTasksData>((Ref ref) async {
  final GteAuthedApi api = ref.watch(authedApiProvider);
  final bool authenticated = ref.watch(isAuthenticatedProvider);
  final JsonMap challengesPayload = await api.getMap(
    '/daily-challenges',
    auth: false,
  );
  JsonMap? mePayload;
  if (authenticated) {
    mePayload = await api.getMap('/daily-challenges/me');
  }
  final List<String> availableKeys = stringListValue(
    mePayload?['available_challenge_keys'],
  );
  final List<DailyChallengeSummary> challenges = jsonMapList(
        challengesPayload['challenges'],
        label: 'daily challenges',
      )
      .map(
        (JsonMap item) => DailyChallengeSummary(
          challengeKey: stringValue(item['challenge_key']),
          title: stringValue(item['title']),
          description: stringValue(item['description']),
          rewardSummary:
              '${numberValue(item['reward_amount']).toStringAsFixed(0)} ${stringValue(item['reward_unit'])}',
          claimLimitPerDay: intValue(item['claim_limit_per_day']),
          availableToday:
              !authenticated ||
              availableKeys.contains(stringValue(item['challenge_key'])),
        ),
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
    claimsToday: jsonMapList(
      mePayload?['claims_today'],
      label: 'daily challenge claims',
    ),
    currentStreak: intValue(streak['current_streak']),
    longestStreak: intValue(streak['longest_streak']),
    nextBonusAmount: numberValue(streak['next_bonus_amount']),
  );
});
