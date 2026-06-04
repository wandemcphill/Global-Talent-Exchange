import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/club_hub/presentation/club_hub_screen.dart';
import 'package:gte_frontend/features/compete/presentation/gte_compete_bracket_screen.dart';
import 'package:gte_frontend/features/home_dashboard/home_dashboard_screen.dart';
import 'package:gte_frontend/features/navigation/presentation/gte_navigation_shell_screen.dart';
import 'package:gte_frontend/features/navigation/routing/gte_navigation_route.dart';
import 'package:gte_frontend/features/social/social_screen.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/admin/admin_command_center_screen.dart';
import 'package:gte_frontend/screens/gte_market_players_screen.dart';
import 'package:gte_frontend/screens/gte_portfolio_screen.dart';
import 'package:gte_frontend/screens/referrals/referral_hub_screen.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  test('canonical shell role URLs parse to primary destinations', () {
    expect(
      GteNavigationRoute.parse('/app/world').primaryDestination,
      GtePrimaryDestination.home,
    );
    expect(
      GteNavigationRoute.parse('/app/market').primaryDestination,
      GtePrimaryDestination.market,
    );
    expect(
      GteNavigationRoute.parse('/app/club').primaryDestination,
      GtePrimaryDestination.club,
    );
    expect(
      GteNavigationRoute.parse('/app/compete').primaryDestination,
      GtePrimaryDestination.competitions,
    );
    expect(
      GteNavigationRoute.parse('/app/creator').primaryDestination,
      GtePrimaryDestination.hub,
    );
    expect(
      GteNavigationRoute.parse('/app/community').primaryDestination,
      GtePrimaryDestination.community,
    );
    expect(
      GteNavigationRoute.parse('/app/capital').primaryDestination,
      GtePrimaryDestination.wallet,
    );
    expect(
      GteNavigationRoute.parse('/app/admin').primaryDestination,
      GtePrimaryDestination.admin,
    );
  });

  group('role route guards', () {
    testWidgets('fan and owner sessions can open football user lanes', (
      WidgetTester tester,
    ) async {
      _setLargeViewport(tester);

      await _pumpRoleShell(
        tester,
        initialPath: '/app/market',
        session: _session(userId: 'fan-1', userName: 'Lagos Scout'),
      );
      await _expectEventually(tester, find.byType(GteMarketPlayersScreen));
      expect(find.text('Player trading is a Football User lane'), findsNothing);

      await _pumpRoleShell(
        tester,
        initialPath: '/app/club',
        session: _session(
          userId: 'owner-1',
          userName: 'Ibadan Owner',
          clubId: 'ibadan-lions',
          clubName: 'Ibadan Lions FC',
        ),
      );
      await _expectEventually(tester, find.byType(ClubHubScreen));
      expect(
        find.text('Club operations belong to Football User accounts'),
        findsNothing,
      );

      await _pumpRoleShell(
        tester,
        initialPath: '/app/compete',
        session: _session(
          userId: 'owner-2',
          userName: 'Abeokuta Owner',
          clubId: 'abeokuta-rangers',
          clubName: 'Abeokuta Rangers',
        ),
      );
      await _expectEventually(tester, find.byType(GteCompeteBracketScreen));
      expect(
        find.text('Club tournaments require a Football User account'),
        findsNothing,
      );
    });

    testWidgets('creator and trader sessions can open shared lanes', (
      WidgetTester tester,
    ) async {
      _setLargeViewport(tester);

      for (final GteAuthSession session in <GteAuthSession>[
        _session(
          userId: 'creator-shared',
          userName: 'Creator Shared',
          role: 'creator',
          accountType: 'creator',
        ),
        _session(
          userId: 'trader-shared',
          userName: 'Trader Shared',
          role: 'coin_trader',
          accountType: 'coin_trader',
        ),
      ]) {
        await _pumpRoleShell(
          tester,
          initialPath: '/app/world',
          session: session,
        );
        await _expectEventually(tester, find.byType(HomeDashboardScreen));

        await _pumpRoleShell(
          tester,
          initialPath: '/app/community',
          session: session,
        );
        await _expectEventually(tester, find.byType(CommunityScreen));
      }
    });

    testWidgets('non-admin football users are blocked from admin command', (
      WidgetTester tester,
    ) async {
      _setLargeViewport(tester);

      for (final GteAuthSession session in <GteAuthSession>[
        _session(userId: 'fan-admin-block', userName: 'Fan Preview'),
        _session(
          userId: 'owner-admin-block',
          userName: 'Owner Preview',
          clubId: 'owner-fc',
          clubName: 'Owner FC',
        ),
      ]) {
        await _pumpRoleShell(
          tester,
          initialPath: '/app/admin',
          session: session,
        );
        await _expectEventually(
          tester,
          find.text('Admin command requires scoped access'),
        );
        expect(find.byType(AdminCommandCenterScreen), findsNothing);
      }
    });

    testWidgets('unrecognized roles see a blocked admin state without errors', (
      WidgetTester tester,
    ) async {
      _setLargeViewport(tester);

      await _pumpRoleShell(
        tester,
        initialPath: '/app/admin',
        session: _session(
          userId: 'unknown-admin-block',
          userName: 'Unknown Role',
          role: 'league_oracle',
          accountType: 'league_oracle',
        ),
      );

      await _expectEventually(
        tester,
        find.text('Admin command requires scoped access'),
      );
      expect(find.byType(AdminCommandCenterScreen), findsNothing);
    });

    testWidgets('creator can open Creator Hub but not football/admin lanes', (
      WidgetTester tester,
    ) async {
      _setLargeViewport(tester);

      final GteAuthSession creator = _session(
        userId: 'creator-1',
        userName: 'Creator Desk',
        role: 'creator',
        accountType: 'creator',
      );

      await _pumpRoleShell(
        tester,
        initialPath: '/app/creator',
        session: creator,
      );
      await _expectEventually(tester, find.byType(ReferralHubScreen));

      await _expectBlockedRoute(
        tester,
        initialPath: '/app/market',
        session: creator,
        message: 'Player trading is a Football User lane',
      );
      await _expectBlockedRoute(
        tester,
        initialPath: '/app/club',
        session: creator,
        message: 'Club operations belong to Football User accounts',
      );
      await _expectBlockedRoute(
        tester,
        initialPath: '/app/compete',
        session: creator,
        message: 'Club tournaments require a Football User account',
      );
      await _expectBlockedRoute(
        tester,
        initialPath: '/app/admin',
        session: creator,
        message: 'Admin command requires scoped access',
      );
    });

    testWidgets('trader can open capital but not football/admin lanes', (
      WidgetTester tester,
    ) async {
      _setLargeViewport(tester);

      final GteAuthSession trader = _session(
        userId: 'trader-1',
        userName: 'Liquidity Desk',
        role: 'coin_trader',
        accountType: 'coin_trader',
      );

      await _pumpRoleShell(
        tester,
        initialPath: '/app/capital',
        session: trader,
      );
      await _expectEventually(tester, find.byType(GtePortfolioScreen));

      await _expectBlockedRoute(
        tester,
        initialPath: '/app/market',
        session: trader,
        message: 'Player trading is a Football User lane',
      );
      await _expectBlockedRoute(
        tester,
        initialPath: '/app/club',
        session: trader,
        message: 'Club operations belong to Football User accounts',
      );
      await _expectBlockedRoute(
        tester,
        initialPath: '/app/compete',
        session: trader,
        message: 'Club tournaments require a Football User account',
      );
      await _expectBlockedRoute(
        tester,
        initialPath: '/app/admin',
        session: trader,
        message: 'Admin command requires scoped access',
      );
    });

    testWidgets('admin can open admin command and football user lanes', (
      WidgetTester tester,
    ) async {
      _setLargeViewport(tester);

      final GteAuthSession admin = _session(
        userId: 'admin-1',
        userName: 'Admin Desk',
        role: 'admin',
        accountType: 'admin',
        clubId: 'admin-fc',
        clubName: 'Admin FC',
      );

      await _pumpRoleShell(tester, initialPath: '/app/admin', session: admin);
      await _expectEventually(tester, find.byType(AdminCommandCenterScreen));
      expect(find.text('Admin command requires scoped access'), findsNothing);

      await _pumpRoleShell(tester, initialPath: '/app/market', session: admin);
      await _expectEventually(tester, find.byType(GteMarketPlayersScreen));
      expect(find.text('Player trading is a Football User lane'), findsNothing);

      await _pumpRoleShell(tester, initialPath: '/app/compete', session: admin);
      await _expectEventually(tester, find.byType(GteCompeteBracketScreen));
      expect(
        find.text('Club tournaments require a Football User account'),
        findsNothing,
      );
    });
  });
}

Future<void> _expectBlockedRoute(
  WidgetTester tester, {
  required String initialPath,
  required GteAuthSession session,
  required String message,
}) async {
  await _pumpRoleShell(tester, initialPath: initialPath, session: session);
  await _expectEventually(tester, find.text(message));
}

Future<void> _pumpRoleShell(
  WidgetTester tester, {
  required String initialPath,
  required GteAuthSession session,
}) async {
  final GteExchangeController controller = GteExchangeController(
    api: GteExchangeApiClient.fixture(),
  )..session = session;

  await tester.pumpWidget(
    MaterialApp(
      theme: GteShellTheme.build(),
      home: GteNavigationShellScreen.fromPath(
        controller: controller,
        apiBaseUrl: 'http://127.0.0.1:8000',
        backendMode: GteBackendMode.fixture,
        initialPath: initialPath,
      ),
    ),
  );
  await tester.pump();
}

Future<void> _expectEventually(
  WidgetTester tester,
  Finder finder, {
  Duration step = const Duration(milliseconds: 50),
  int maxPumps = 80,
}) async {
  for (int pump = 0; pump < maxPumps; pump += 1) {
    await tester.pump(step);
    if (finder.evaluate().isNotEmpty) {
      await tester.pump(const Duration(seconds: 1));
      return;
    }
  }
  throw TestFailure('Timed out waiting for $finder.');
}

void _setLargeViewport(WidgetTester tester) {
  tester.view.physicalSize = const Size(1800, 2200);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });
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
