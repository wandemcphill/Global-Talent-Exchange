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
  setUp(() {
    TestWidgetsFlutterBinding.ensureInitialized();
  });

  testWidgets(
    'guest dashboard renders public role scaffold with blocked state',
    (WidgetTester tester) async {
      await _pumpDashboard(tester);

      expect(find.text('Guest'), findsWidgets);
      expect(find.text('GTEX public operating board'), findsOneWidget);
      expect(find.text('Live ecosystem pulse'), findsOneWidget);
      expect(find.text('Public newsroom'), findsOneWidget);
      expect(find.text('Private economy state is blocked'), findsOneWidget);
      expect(find.text('Create account'), findsWidgets);
    },
  );

  testWidgets(
    'fan without club keeps no-club quick links and blocked club state',
    (WidgetTester tester) async {
      final GteExchangeController controller = _controllerWithSession(
        _session(userId: 'fan-1', userName: 'Lagos Scout'),
      );

      await _pumpDashboard(
        tester,
        controller: controller,
        dependencies: _dependencies(
          isAuthenticated: true,
          userName: 'Lagos Scout',
        ),
      );

      expect(find.text('Fan / No club'), findsOneWidget);
      expect(find.text('This account has no club yet'), findsOneWidget);
      expect(find.text('National rentals'), findsOneWidget);
      expect(find.text('Player discovery'), findsOneWidget);
      expect(find.text('Scout players'), findsWidgets);
      expect(find.text('Open world'), findsWidgets);
      expect(find.text('Open matchday'), findsWidgets);
      expect(find.text('Open funds'), findsWidgets);
    },
  );

  testWidgets('club owner scaffold surfaces canonical club priorities', (
    WidgetTester tester,
  ) async {
    final GteExchangeController controller = _controllerWithSession(
      _session(
        userId: 'owner-1',
        userName: 'Ibadan Owner',
        clubId: 'ibadan-lions',
        clubName: 'Ibadan Lions FC',
      ),
    );

    await _pumpDashboard(
      tester,
      controller: controller,
      clubId: 'ibadan-lions',
      clubName: 'Ibadan Lions FC',
      dependencies: _dependencies(
        isAuthenticated: true,
        userName: 'Ibadan Owner',
        clubId: 'ibadan-lions',
        clubName: 'Ibadan Lions FC',
      ),
    );

    expect(find.text('Club owner'), findsOneWidget);
    expect(find.text('Club operating command'), findsOneWidget);
    expect(find.text('Squad readiness'), findsOneWidget);
    expect(find.text('Formation health'), findsOneWidget);
    expect(find.text('Transfer pipeline'), findsOneWidget);
    expect(find.text('Injuries and morale'), findsOneWidget);
    expect(find.text('HOME ONBOARDING'), findsNothing);
    expect(find.text('Create or join a club to unlock Home'), findsNothing);
  });

  testWidgets('special account roles select their dedicated scaffolds', (
    WidgetTester tester,
  ) async {
    await _pumpDashboard(
      tester,
      controller: _controllerWithSession(
        _session(
          userId: 'trader-1',
          userName: 'Liquidity Desk',
          role: 'coin_trader',
          accountType: 'coin_trader',
        ),
      ),
      dependencies: _dependencies(
        isAuthenticated: true,
        userName: 'Liquidity Desk',
        role: 'coin_trader',
      ),
    );
    expect(find.text('Coin trader'), findsOneWidget);
    expect(find.text('Order book'), findsOneWidget);
    expect(find.text('Settlement status'), findsOneWidget);

    await _pumpDashboard(
      tester,
      controller: _controllerWithSession(
        _session(
          userId: 'creator-1',
          userName: 'Creator Desk',
          role: 'creator',
          accountType: 'creator',
        ),
      ),
      dependencies: _dependencies(
        isAuthenticated: true,
        userName: 'Creator Desk',
        role: 'creator',
      ),
    );
    expect(find.text('Creator'), findsOneWidget);
    expect(find.text('Campaigns'), findsOneWidget);
    expect(find.text('Earnings and settlements'), findsOneWidget);

    await _pumpDashboard(
      tester,
      controller: _controllerWithSession(
        _session(
          userId: 'host-1',
          userName: 'Host Desk',
          role: 'competition_host',
          accountType: 'competition_host',
        ),
      ),
      canHostCompetitions: true,
      dependencies: _dependencies(
        isAuthenticated: true,
        userName: 'Host Desk',
        role: 'competition_host',
        canHostCompetitions: true,
      ),
    );
    expect(find.text('Competition host'), findsOneWidget);
    expect(find.text('Entries'), findsOneWidget);
    expect(find.text('Settlement readiness'), findsOneWidget);

    await _pumpDashboard(
      tester,
      controller: _controllerWithSession(
        _session(
          userId: 'admin-1',
          userName: 'Admin Desk',
          role: 'admin',
          accountType: 'admin',
        ),
      ),
      dependencies: _dependencies(
        isAuthenticated: true,
        userName: 'Admin Desk',
        role: 'admin',
      ),
    );
    expect(find.text('Admin'), findsOneWidget);
    expect(find.text('Operational command system'), findsOneWidget);
    expect(find.text('Treasury'), findsOneWidget);
    expect(find.text('Fraud alerts'), findsOneWidget);
  });

  testWidgets('home scaffold keeps route migration expansion lanes working', (
    WidgetTester tester,
  ) async {
    int marketOpens = 0;
    await _pumpDashboard(
      tester,
      controller: _controllerWithSession(
        _session(
          userId: 'owner-2',
          userName: 'Route Owner',
          clubId: 'route-fc',
          clubName: 'Route FC',
        ),
      ),
      clubId: 'route-fc',
      clubName: 'Route FC',
      onOpenMarket: () {
        marketOpens += 1;
      },
      dependencies: _dependencies(
        isAuthenticated: true,
        userName: 'Route Owner',
        clubId: 'route-fc',
        clubName: 'Route FC',
      ),
    );

    expect(find.text('Expansion lanes'), findsOneWidget);
    final Finder fanPredictionsButton = find.widgetWithText(
      FilledButton,
      'Fan predictions (live match only)',
    );
    expect(tester.widget<FilledButton>(fanPredictionsButton).onPressed, isNull);
    expect(
      find.text(
        'Fan predictions unlock from live-match routes after a canonical match id is present.',
      ),
      findsOneWidget,
    );

    await tester.tap(find.text('Player cards'));
    await tester.pump();

    expect(marketOpens, 1);
  });
}

Future<void> _pumpDashboard(
  WidgetTester tester, {
  GteExchangeController? controller,
  GteNavigationDependencies? dependencies,
  String? clubId,
  String? clubName,
  bool canHostCompetitions = false,
  VoidCallback? onOpenMarket,
}) async {
  tester.view.physicalSize = const Size(1600, 3200);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });

  await tester.pumpWidget(
    MaterialApp(
      theme: GteShellTheme.build(),
      home: HomeDashboardScreen(
        exchangeController:
            controller ??
            GteExchangeController(api: GteExchangeApiClient.fixture()),
        apiBaseUrl: 'http://127.0.0.1:8000',
        backendMode: GteBackendMode.fixture,
        clubId: clubId,
        clubName: clubName,
        canHostCompetitions: canHostCompetitions,
        onOpenMarketTab: onOpenMarket,
        onOpenClubTab: () {},
        onOpenCompetitionsTab: () {},
        onOpenHubTab: () {},
        onOpenWalletTab: () {},
        onOpenLogin: () {},
        navigationDependencies: dependencies,
      ),
    ),
  );
  await tester.pumpAndSettle();
}

GteExchangeController _controllerWithSession(GteAuthSession session) {
  return GteExchangeController(api: GteExchangeApiClient.fixture())
    ..session = session;
}

GteNavigationDependencies _dependencies({
  bool isAuthenticated = false,
  String? userName,
  String? role,
  String? clubId,
  String? clubName,
  bool canHostCompetitions = false,
}) {
  return GteNavigationDependencies(
    apiBaseUrl: 'http://127.0.0.1:8000',
    backendMode: GteBackendMode.fixture,
    currentUserId: 'test-user',
    currentUserName: userName,
    currentUserRole: role,
    currentClubId: clubId,
    currentClubName: clubName,
    isAuthenticated: isAuthenticated,
    canHostCompetitions: canHostCompetitions,
  );
}

GteAuthSession _session({
  required String userId,
  required String userName,
  String role = 'user',
  String accountType = 'user',
  String? clubId,
  String? clubName,
}) {
  return GteAuthSession.fromJson(<String, Object?>{
    'access_token': 'test-token-$userId',
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
      'role': role,
      'account_type': accountType,
      if (clubId != null) 'current_club_id': clubId,
      if (clubName != null) 'current_club_name': clubName,
    },
  });
}
