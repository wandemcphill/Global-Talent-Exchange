import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/home/home_screen.dart';
import 'package:gte_frontend/features/profile/live_profile_provider.dart';
import 'package:gte_frontend/navigation/app_destinations.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

/// PHASE 4H - every persona Home now serves must actually render.
///
/// Home resolves five personas, but three of them (club owner, coin trader,
/// admin) were intercepted by the shell before Home ever built, so their
/// branches had never run in the app. Routing those sessions to Home means
/// their code paths are live for the first time - and the club-owner one
/// threw immediately.
///
/// Its quick actions navigate to `/coaches` and `/lineup`. Both have had a
/// live route and a real screen all along, but neither was published in
/// `appRouteInventory`, and the panel resolved each action's surface with a
/// null-check operator - so a club owner's Home lost its whole quick-actions
/// panel to a red error box.
void main() {
  Future<List<Object>> pumpPersona(
    WidgetTester tester, {
    required Map<String, Object?> user,
    Map<String, Object?>? club,
  }) async {
    tester.view.physicalSize = const Size(1440, 3000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          isAuthenticatedProvider.overrideWithValue(true),
          profileDataProvider.overrideWith(
            (Ref ref) async => ProfileData(
              authenticated: true,
              user: user,
              affinityProfile: const <String, Object?>{},
              club: club,
              followers: 0,
              following: 0,
            ),
          ),
        ],
        child: MaterialApp(
          theme: GteShellTheme.build(),
          home: const Scaffold(body: HomeScreen()),
        ),
      ),
    );
    for (int pump = 0; pump < 40; pump += 1) {
      await tester.pump(const Duration(milliseconds: 50));
    }

    final List<Object> errors = <Object>[];
    for (int i = 0; i < 40; i += 1) {
      final Object? error = tester.takeException();
      if (error == null) {
        break;
      }
      errors.add(error);
    }
    return errors;
  }

  testWidgets('a club owner Home builds its quick actions', (
    WidgetTester tester,
  ) async {
    final List<Object> errors = await pumpPersona(
      tester,
      user: const <String, Object?>{'id': 'u1', 'role': 'user'},
      club: const <String, Object?>{'id': 'c1', 'name': 'Ibadan Lions FC'},
    );
    expect(
      errors,
      isEmpty,
      reason:
          'the club-owner quick actions threw - a destination they navigate '
          'to is missing from appRouteInventory: ${errors.join(' | ')}',
    );
    expect(find.text('Hire coaches'), findsWidgets);
    expect(find.text('Set lineup'), findsWidgets);
  });

  testWidgets('a coin trader Home builds its quick actions', (
    WidgetTester tester,
  ) async {
    final List<Object> errors = await pumpPersona(
      tester,
      user: const <String, Object?>{'id': 'u2', 'role': 'coin_trader'},
    );
    expect(errors, isEmpty, reason: errors.join(' | '));
  });

  testWidgets('an admin Home builds its quick actions', (
    WidgetTester tester,
  ) async {
    final List<Object> errors = await pumpPersona(
      tester,
      user: const <String, Object?>{'id': 'u3', 'role': 'admin'},
    );
    expect(errors, isEmpty, reason: errors.join(' | '));
  });

  testWidgets('a creator Home builds its quick actions', (
    WidgetTester tester,
  ) async {
    final List<Object> errors = await pumpPersona(
      tester,
      user: const <String, Object?>{'id': 'u4', 'role': 'creator'},
    );
    expect(errors, isEmpty, reason: errors.join(' | '));
  });

  testWidgets('a session with no club builds its quick actions', (
    WidgetTester tester,
  ) async {
    final List<Object> errors = await pumpPersona(
      tester,
      user: const <String, Object?>{'id': 'u5', 'role': 'user'},
    );
    expect(errors, isEmpty, reason: errors.join(' | '));
  });

  test('no Home quick action claims a destination that resolves nowhere', () {
    // Both were published as live and rendered as working buttons - `/tasks`
    // on the coin trader's Home, `/national-teams` on the no-club Home -
    // while nothing registered either, so tapping one landed on "Route
    // unavailable". `/national-teams` was the plural of the live
    // `/national-team` and only lacked its alias; `/tasks` had a provider and
    // no screen, and now has both a screen and a route. Live is the truth for
    // both again.
    for (final String location in <String>[
      AppRoutes.tasks,
      AppRoutes.nationalTeams,
    ]) {
      expect(
        appRouteSurfaceFor(location)?.state,
        AppRouteSurfaceState.live,
        reason:
            '\$location resolves now, so the inventory should say so - and if '
            'it ever stops resolving it must not keep claiming to be live',
      );
    }
  });

  test('every route the Home quick actions navigate to is published', () {
    // The panel now drops an unpublished destination rather than throwing, so
    // the failure mode became a silently missing button. This is what keeps
    // that from going unnoticed.
    const List<String> quickActionDestinations = <String>[
      AppRoutes.clips,
      AppRoutes.coaches,
      AppRoutes.competitions,
      AppRoutes.lineup,
      AppRoutes.market,
      AppRoutes.matches,
      AppRoutes.nationalTeams,
      AppRoutes.profile,
      AppRoutes.profileAdmin,
      AppRoutes.profileLogin,
      AppRoutes.regens,
      AppRoutes.tasks,
      AppRoutes.transferCenter,
    ];

    final List<String> unpublished = quickActionDestinations
        .where((String location) => appRouteSurfaceFor(location) == null)
        .toList(growable: false);

    expect(
      unpublished,
      isEmpty,
      reason:
          'Home navigates to these but appRouteInventory does not publish '
          'them, so each is a button that silently disappears: '
          '${unpublished.join(', ')}',
    );
  });
}
