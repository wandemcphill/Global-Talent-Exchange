import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/tasks/gtex_daily_challenges_screen.dart';
import 'package:gte_frontend/features/tasks/live_tasks_provider.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

/// The daily-challenge desk. `/tasks` was published as a live surface and
/// rendered as a quick action on Home while `lib/features/tasks/` held only a
/// provider, so the button led to "Route unavailable". These cover the screen
/// that was missing - every state it can land in, and the honesty rules it
/// has to keep.
void main() {
  const List<double> ladder = <double>[390, 430, 768, 1024, 1280, 1440, 1920];

  LiveTasksData tasks({
    bool authenticated = true,
    bool featureEnabled = true,
    List<DailyChallengeSummary> challenges = const <DailyChallengeSummary>[],
    List<DailyChallengeClaimSummary> claimsToday =
        const <DailyChallengeClaimSummary>[],
    int currentStreak = 0,
    int longestStreak = 0,
    double nextBonusAmount = 0,
  }) {
    return LiveTasksData(
      authenticated: authenticated,
      featureEnabled: featureEnabled,
      challenges: challenges,
      claimsToday: claimsToday,
      currentStreak: currentStreak,
      longestStreak: longestStreak,
      nextBonusAmount: nextBonusAmount,
    );
  }

  DailyChallengeSummary challenge({
    String key = 'daily-login',
    String title = 'Daily login',
    bool claimedToday = false,
    bool availableToday = true,
    int claimLimitPerDay = 1,
    String rewardSummary = '25 GTC',
  }) {
    return DailyChallengeSummary(
      challengeKey: key,
      title: title,
      description: 'Open GTEX and check the board.',
      rewardSummary: rewardSummary,
      claimLimitPerDay: claimLimitPerDay,
      claimedToday: claimedToday,
      availableToday: availableToday,
    );
  }

  /// Pumps the desk with the task state the provider would have produced.
  ///
  /// Omitting [data] holds the provider pending, which is the screen's
  /// loading state.
  Future<void> pumpScreen(
    WidgetTester tester, {
    LiveTasksData? data,
    double width = 1280,
    VoidCallback? onSignIn,
  }) async {
    tester.view.physicalSize = Size(width, 2200);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          liveTasksProvider.overrideWith((Ref ref) async {
            if (data == null) {
              // Never completes: holds the screen in its loading state.
              return Completer<LiveTasksData>().future;
            }
            return data;
          }),
        ],
        child: MaterialApp(
          theme: GteShellTheme.build(),
          home: Scaffold(body: GtexDailyChallengesScreen(onSignIn: onSignIn)),
        ),
      ),
    );
    // The provider settles on a microtask, so the screen needs a few frames
    // to move out of its loading state.
    for (int i = 0; i < 5; i += 1) {
      await tester.pump(const Duration(milliseconds: 20));
    }
  }

  testWidgets('a loading desk says so rather than showing empty counts', (
    WidgetTester tester,
  ) async {
    await pumpScreen(tester);
    expect(find.text('Loading daily challenges'), findsOneWidget);
    expect(find.textContaining('CURRENT STREAK'), findsNothing);
  });

  testWidgets('a failed load explains itself and offers a retry', (
    WidgetTester tester,
  ) async {
    // Completed with an error after the first frame, which is how a real
    // failed fetch arrives: a pending load that resolves into an error.
    // Throwing straight out of the override instead leaves Riverpod in a
    // refreshing-with-error state, which is not a state the app produces.
    final Completer<LiveTasksData> completer = Completer<LiveTasksData>();
    tester.view.physicalSize = const Size(1280, 2200);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          liveTasksProvider.overrideWith((Ref ref) => completer.future),
        ],
        child: MaterialApp(
          theme: GteShellTheme.build(),
          home: const Scaffold(body: GtexDailyChallengesScreen()),
        ),
      ),
    );
    await tester.pump();
    expect(find.text('Loading daily challenges'), findsOneWidget);

    completer.completeError(Exception('challenge service unavailable'));
    for (int i = 0; i < 5; i += 1) {
      await tester.pump(const Duration(milliseconds: 20));
    }

    expect(find.text('Daily challenges could not be loaded'), findsOneWidget);
    expect(find.textContaining('challenge service unavailable'), findsOneWidget);
    expect(find.text('Retry'), findsOneWidget);
  });

  testWidgets('a disabled programme reads as blocked, not as empty', (
    WidgetTester tester,
  ) async {
    await pumpScreen(
      tester,
      data: tasks(
        featureEnabled: false,
        challenges: <DailyChallengeSummary>[challenge()],
      ),
    );
    expect(find.byType(GtexBlockedState), findsOneWidget);
    expect(find.text('Daily challenges are switched off'), findsOneWidget);
  });

  testWidgets('an empty pool reads as empty, not as broken', (
    WidgetTester tester,
  ) async {
    await pumpScreen(tester, data: tasks());
    expect(find.byType(GtexEmptyState), findsOneWidget);
  });

  testWidgets('a visitor is never shown a streak of zero', (
    WidgetTester tester,
  ) async {
    // `/api/daily-challenges/me` is only fetched for a signed-in session, so
    // for a visitor the streak fields are absent rather than zero. Printing
    // them would state figures about someone the product has not measured.
    await pumpScreen(
      tester,
      data: tasks(
        authenticated: false,
        challenges: <DailyChallengeSummary>[challenge()],
      ),
      onSignIn: () {},
    );

    expect(find.text('CURRENT STREAK'), findsNothing);
    expect(find.text('LONGEST STREAK'), findsNothing);
    expect(find.text('NEXT BONUS'), findsNothing);
    expect(find.byKey(const Key('daily-challenges-sign-in')), findsOneWidget);
    // The pool itself is public, so it still shows.
    expect(find.text('Daily login'), findsOneWidget);
  });

  testWidgets('a signed-in desk shows the streak the backend settled', (
    WidgetTester tester,
  ) async {
    await pumpScreen(
      tester,
      data: tasks(
        challenges: <DailyChallengeSummary>[challenge()],
        currentStreak: 4,
        longestStreak: 11,
        nextBonusAmount: 150,
      ),
    );
    expect(find.text('CURRENT STREAK'), findsOneWidget);
    expect(find.text('4'), findsWidgets);
    expect(find.text('11'), findsWidgets);
    expect(find.text('150'), findsWidgets);
  });

  testWidgets('an already-claimed challenge cannot be claimed again', (
    WidgetTester tester,
  ) async {
    await pumpScreen(
      tester,
      data: tasks(
        challenges: <DailyChallengeSummary>[challenge(claimedToday: true)],
      ),
    );

    expect(find.text('Claimed today'), findsOneWidget);
    final GtexActionButton action = tester.widget<GtexActionButton>(
      find.byKey(const Key('daily-challenge-claim-daily-login')),
    );
    expect(
      action.onPressed,
      isNull,
      reason: 'a challenge already settled today must not offer a claim',
    );
  });

  testWidgets('a challenge closed for today is disabled and says why', (
    WidgetTester tester,
  ) async {
    await pumpScreen(
      tester,
      data: tasks(
        challenges: <DailyChallengeSummary>[challenge(availableToday: false)],
      ),
    );
    expect(find.text('Not available today'), findsOneWidget);
    final GtexActionButton action = tester.widget<GtexActionButton>(
      find.byKey(const Key('daily-challenge-claim-daily-login')),
    );
    expect(action.onPressed, isNull);
  });

  testWidgets('a claimable challenge offers a live claim', (
    WidgetTester tester,
  ) async {
    await pumpScreen(
      tester,
      data: tasks(challenges: <DailyChallengeSummary>[challenge()]),
    );
    final GtexActionButton action = tester.widget<GtexActionButton>(
      find.byKey(const Key('daily-challenge-claim-daily-login')),
    );
    expect(action.onPressed, isNotNull);
    expect(action.label, 'Claim');
  });

  testWidgets('a claim limit is shown only when the backend gave one', (
    WidgetTester tester,
  ) async {
    await pumpScreen(
      tester,
      data: tasks(
        challenges: <DailyChallengeSummary>[
          challenge(claimLimitPerDay: 0),
          challenge(key: 'streak', title: 'Streak keeper', claimLimitPerDay: 3),
        ],
      ),
    );
    expect(find.text('3 per day'), findsOneWidget);
    expect(
      find.text('0 per day'),
      findsNothing,
      reason: 'an absent claim limit must not be rendered as a limit of zero',
    );
  });

  testWidgets('settled claims are listed with what they paid', (
    WidgetTester tester,
  ) async {
    await pumpScreen(
      tester,
      data: tasks(
        challenges: <DailyChallengeSummary>[challenge(claimedToday: true)],
        claimsToday: <DailyChallengeClaimSummary>[
          DailyChallengeClaimSummary(
            claimId: 'claim-1',
            challengeKey: 'daily-login',
            challengeTitle: 'Daily login',
            rewardLabel: '25 GTC',
            bonusAwardedLabel: '5 GTC',
            claimedAt: DateTime.utc(2026, 9, 4),
            streakBeforeClaim: 3,
          ),
        ],
      ),
    );
    expect(find.text('Claimed today'), findsWidgets);
    expect(find.textContaining('25 GTC'), findsWidgets);
    expect(find.text('Bonus 5 GTC'), findsOneWidget);
  });

  for (final double width in ladder) {
    testWidgets('the desk lays out at ${width.toInt()}px', (
      WidgetTester tester,
    ) async {
      await pumpScreen(
        tester,
        width: width,
        data: tasks(
          challenges: <DailyChallengeSummary>[
            challenge(),
            challenge(
              key: 'streak',
              title: 'Keep the streak alive for a very long run of days',
            ),
          ],
          currentStreak: 4,
          longestStreak: 11,
          nextBonusAmount: 150,
        ),
      );

      final List<String> errors = <String>[];
      for (int i = 0; i < 20; i += 1) {
        final Object? error = tester.takeException();
        if (error == null) {
          break;
        }
        errors.add(error.toString().split('\n').first);
      }
      expect(
        errors,
        isEmpty,
        reason:
            'the daily-challenge desk reported unrenderable layout at '
            '${width.toInt()}px:\n  ${errors.join('\n  ')}',
      );
      expect(find.text('Daily login'), findsOneWidget);
      expect(
        find.byKey(const Key('daily-challenge-claim-daily-login')),
        findsOneWidget,
        reason: 'the claim action must stay reachable at ${width.toInt()}px',
      );
    });
  }
}
