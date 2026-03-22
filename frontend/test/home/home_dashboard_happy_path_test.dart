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

    await tester.dragUntilVisible(
      find.text('NEXT MATCH'),
      find.byType(SingleChildScrollView).first,
      const Offset(0, -300),
    );
    await tester.pumpAndSettle();

    expect(find.text('NEXT MATCH'), findsOneWidget);

    await tester.dragUntilVisible(
      find.textContaining('Ibadan Lions FC go in with'),
      find.byType(SingleChildScrollView).first,
      const Offset(0, -300),
    );
    await tester.pumpAndSettle();

    expect(find.textContaining('Ibadan Lions FC go in with'), findsOneWidget);

    await tester.dragUntilVisible(
      find.text('RECENT REPLAY'),
      find.byType(SingleChildScrollView).first,
      const Offset(0, -300),
    );
    await tester.pumpAndSettle();

    expect(find.text('RECENT REPLAY'), findsOneWidget);
  });
}

GteAuthSession _authenticatedSession({
  required String userId,
  required String userName,
  required String clubId,
  required String clubName,
}) {
  return GteAuthSession.fromJson(
    <String, Object?>{
      'access_token': 'test-token',
      'token_type': 'bearer',
      'expires_in': 3600,
      'current_club_id': clubId,
      'current_club_name': clubName,
      'user': <String, Object?>{
        'id': userId,
        'email': '$userId@gtex.test',
        'username': userId,
        'display_name': userName,
        'role': 'user',
        'current_club_id': clubId,
        'current_club_name': clubName,
      },
    },
  );
}
