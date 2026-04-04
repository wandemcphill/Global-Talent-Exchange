import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/home_dashboard/home_dashboard_screen.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets(
    'home keeps the canonical club context active after onboarding changes',
    (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1600, 2200);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final GteExchangeController controller = GteExchangeController(
        api: GteExchangeApiClient.fixture(),
      );
      controller.session = _authenticatedSession(
        userId: 'user-ibadan',
        userName: 'Ibadan Owner',
        clubId: 'ibadan-lions',
        clubName: 'Ibadan Lions FC',
      );

      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: HomeDashboardScreen(
            exchangeController: controller,
            apiBaseUrl: 'http://127.0.0.1:8000',
            backendMode: GteBackendMode.fixture,
            navigationDependencies: const GteNavigationDependencies(
              apiBaseUrl: 'http://127.0.0.1:8000',
              backendMode: GteBackendMode.fixture,
              currentUserId: 'user-ibadan',
              currentUserName: 'Ibadan Owner',
              currentClubId: 'ibadan-lions',
              currentClubName: 'Ibadan Lions FC',
              isAuthenticated: true,
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('HOME ONBOARDING'), findsNothing);
      expect(find.text('Create or join a club to unlock Home'), findsNothing);

      final Finder scrollable = find.byType(Scrollable).first;

      await tester.dragUntilVisible(
        find.text('NEXT MATCH'),
        scrollable,
        const Offset(0, -300),
      );
      await tester.pumpAndSettle();

      expect(find.text('NEXT MATCH'), findsOneWidget);

      await tester.dragUntilVisible(
        find.textContaining('Ibadan Lions FC go in with'),
        scrollable,
        const Offset(0, -300),
      );
      await tester.pumpAndSettle();

      expect(find.textContaining('Ibadan Lions FC go in with'), findsOneWidget);

      await tester.dragUntilVisible(
        find.text('RISING STARS'),
        scrollable,
        const Offset(0, -300),
      );
      await tester.pumpAndSettle();

      expect(find.text('RISING STARS'), findsOneWidget);
      expect(find.text('SCOUTING FEED'), findsOneWidget);
      expect(find.byKey(const Key('home-regen-rising-stars')), findsOneWidget);
      expect(find.byKey(const Key('home-regen-scouting-feed')), findsOneWidget);

      await tester.dragUntilVisible(
        find.text('MATCHDAY BRIEF'),
        scrollable,
        const Offset(0, -300),
      );
      await tester.pumpAndSettle();

      expect(find.text('MATCHDAY BRIEF'), findsOneWidget);
    },
  );

  testWidgets(
    'no-club home still exposes live matchday, player, world, and GTEX wallet lanes',
    (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1600, 2200);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      final GteExchangeController controller = GteExchangeController(
        api: GteExchangeApiClient.fixture(),
      );
      controller.session = _authenticatedSession(
        userId: 'user-lagos',
        userName: 'Lagos Scout',
      );

      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: HomeDashboardScreen(
            exchangeController: controller,
            apiBaseUrl: 'http://127.0.0.1:8000',
            backendMode: GteBackendMode.fixture,
            onOpenWalletTab: () {},
            onOpenCompetitionsTab: () {},
            navigationDependencies: const GteNavigationDependencies(
              apiBaseUrl: 'http://127.0.0.1:8000',
              backendMode: GteBackendMode.fixture,
              currentUserId: 'user-lagos',
              currentUserName: 'Lagos Scout',
              isAuthenticated: true,
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('This account does not own a club yet'), findsOneWidget);
      expect(find.text('Open player universe'), findsWidgets);
      expect(find.text('Open world'), findsWidgets);
      expect(find.text('Open matchday'), findsWidgets);
      expect(find.text('Open wallet'), findsWidgets);
    },
  );
}

GteAuthSession _authenticatedSession({
  required String userId,
  required String userName,
  String? clubId,
  String? clubName,
}) {
  return GteAuthSession.fromJson(<String, Object?>{
    'access_token': 'test-token',
    'session_id': 'session-$userId',
    'token_type': 'bearer',
    'expires_in': 3600,
    if (clubId != null) 'current_club_id': clubId,
    if (clubName != null) 'current_club_name': clubName,
    'user': <String, Object?>{
      'id': userId,
      'email': '$userId@gtex.test',
      'username': userId,
      'display_name': userName,
      'role': 'user',
      if (clubId != null) 'current_club_id': clubId,
      if (clubName != null) 'current_club_name': clubName,
    },
  });
}
