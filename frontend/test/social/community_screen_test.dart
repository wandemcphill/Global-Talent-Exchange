import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/community_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/navigation/presentation/gte_navigation_shell_screen.dart';
import 'package:gte_frontend/features/navigation/routing/gte_navigation_route.dart';
import 'package:gte_frontend/features/social/social_screen.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets(
    'community screen exposes live watchlist, thread, dm, and follow actions',
    (WidgetTester tester) async {
      _setLargeViewport(tester);
      final CommunityApi api = CommunityApi.fixture();

      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: Scaffold(
            body: CommunityScreen(
              api: api,
              baseUrl: 'http://127.0.0.1:8000',
              backendMode: GteBackendMode.fixture,
              accessToken: 'fixture-token',
              isAuthenticated: true,
              currentClubId: 'ibadan-lions',
              currentClubName: 'Ibadan Lions FC',
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Creator Cup Night'), findsOneWidget);
      expect(find.text('Matchday derby watch party'), findsOneWidget);
      expect(find.text('Transfer room collab'), findsOneWidget);
      expect(find.text('Community canonical surface'), findsOneWidget);
      expect(find.text('Authenticated member'), findsOneWidget);
      expect(find.text('Reports'), findsOneWidget);
      expect(find.text('Gifting'), findsOneWidget);
      expect(find.widgetWithText(FilledButton, 'Unfollow'), findsOneWidget);

      await tester.tap(find.widgetWithText(FilledButton, 'Unfollow'));
      await tester.pumpAndSettle();
      expect(find.widgetWithText(FilledButton, 'Follow'), findsOneWidget);

      await tester.tap(find.text('Add competition'));
      await tester.pumpAndSettle();
      await tester.enterText(
        find.widgetWithText(TextField, 'Competition key'),
        'all-stars',
      );
      await tester.enterText(
        find.widgetWithText(TextField, 'Competition title'),
        'All Stars Cup',
      );
      await tester.enterText(
        find.widgetWithText(TextField, 'Competition type'),
        'creator',
      );
      await tester.tap(find.widgetWithText(FilledButton, 'Add'));
      await tester.pumpAndSettle();
      expect(find.text('All Stars Cup'), findsOneWidget);

      await tester.tap(find.text('Start thread'));
      await tester.pumpAndSettle();
      await tester.enterText(
        find.widgetWithText(TextField, 'Thread key'),
        'all-stars-watch',
      );
      await tester.enterText(
        find.widgetWithText(TextField, 'Thread title'),
        'All Stars Watch Party',
      );
      await tester.enterText(
        find.widgetWithText(TextField, 'Competition key (optional)'),
        'all-stars',
      );
      await tester.tap(find.widgetWithText(FilledButton, 'Open thread'));
      await tester.pumpAndSettle();
      expect(find.text('All Stars Watch Party'), findsWidgets);

      await tester.enterText(
        find.widgetWithText(TextField, 'Reply to thread'),
        'Kickoff soon.',
      );
      await tester.tap(find.widgetWithText(FilledButton, 'Send'));
      await tester.pumpAndSettle();
      expect(find.text('Kickoff soon.'), findsOneWidget);

      Navigator.of(tester.element(find.byType(CommunityScreen))).pop();
      await tester.pumpAndSettle();

      await tester.tap(find.text('New DM'));
      await tester.pumpAndSettle();
      await tester.enterText(
        find.widgetWithText(TextField, 'Participant user IDs'),
        'user-7',
      );
      await tester.enterText(
        find.widgetWithText(TextField, 'Subject'),
        'All Stars Prep',
      );
      await tester.enterText(
        find.widgetWithText(TextField, 'Initial message'),
        'Let us align before kickoff.',
      );
      await tester.tap(find.widgetWithText(FilledButton, 'Open DM'));
      await tester.pumpAndSettle();
      expect(find.text('All Stars Prep'), findsWidgets);

      await tester.enterText(
        find.widgetWithText(TextField, 'Reply in thread'),
        'Ready from the creator desk.',
      );
      await tester.tap(find.widgetWithText(FilledButton, 'Send'));
      await tester.pumpAndSettle();
      expect(find.text('Ready from the creator desk.'), findsOneWidget);
    },
  );

  testWidgets(
    'community screen keeps canonical private surfaces role gated for readers',
    (WidgetTester tester) async {
      _setLargeViewport(tester);
      final CommunityApi api = CommunityApi.fixture();
      bool openedLogin = false;

      await tester.pumpWidget(
        MaterialApp(
          theme: GteShellTheme.build(),
          home: Scaffold(
            body: CommunityScreen(
              api: api,
              baseUrl: 'http://127.0.0.1:8000',
              backendMode: GteBackendMode.fixture,
              isAuthenticated: false,
              onOpenLogin: () {
                openedLogin = true;
              },
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Community canonical surface'), findsOneWidget);
      expect(find.text('Public reader'), findsOneWidget);
      expect(
        find.text(
          'BLOCKED: direct chat is locked until a live token is present.',
        ),
        findsOneWidget,
      );
      expect(find.text('Transfer room collab'), findsNothing);

      await tester.tap(find.text('Sign in').first);
      await tester.pump();

      expect(openedLogin, isTrue);
    },
  );

  testWidgets(
    'community route mounts the live community surface instead of hub aliasing',
    (WidgetTester tester) async {
      _setLargeViewport(tester);
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
          home: GteNavigationShellScreen(
            controller: controller,
            apiBaseUrl: 'http://127.0.0.1:8000',
            backendMode: GteBackendMode.fixture,
            initialRoute: const GteNavigationRoute.community(),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Competition watchlist'), findsOneWidget);
      expect(find.text('Creator Cup Night'), findsOneWidget);
      expect(find.text('Maya Scout community desk'), findsNothing);
      expect(
        find.text(
          'Watchlists, live threads, direct messages, and creator-club follows are wired to live community endpoints.',
        ),
        findsWidgets,
      );
    },
  );
}

void _setLargeViewport(WidgetTester tester) {
  tester.view.physicalSize = const Size(1600, 3200);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });
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
