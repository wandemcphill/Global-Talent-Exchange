import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/features/club_sale_market/presentation/club_sale_market_screen.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/navigation/presentation/gte_navigation_shell_screen.dart';
import 'package:gte_frontend/features/navigation/routing/gte_navigation_route.dart';
import 'package:gte_frontend/ui_gtex/layout/gtex_app_shell.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/wallet/gte_wallet_overview_screen.dart';
import 'package:gte_frontend/theme/gte_theme_controller.dart';
import 'package:gte_frontend/theme/gte_theme_metadata.dart';
import 'package:gte_frontend/theme/gte_theme_picker_sheet.dart';
import 'package:gte_frontend/theme/gte_theme_registry.dart';
import 'package:gte_frontend/theme/gte_theme_scope.dart';
import 'package:gte_frontend/theme/gte_theme_store.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  group('controlled merge source contract', () {
    test('app entry preserves theme bootstrap and root hookup', () {
      final String mainSource = _readSource('lib/main.dart');
      final String appSource = _readSource('lib/app/gte_frontend_app.dart');

      expect(mainSource, contains('GteThemeController.bootstrap('));
      expect(
        mainSource,
        contains('child: GtexApp(themeController: themeController),'),
      );
      expect(appSource, contains('GteThemeControllerScope('));
      expect(
        appSource,
        contains('theme: GteShellTheme.build(_themeController.activeTheme),'),
      );
      expect(appSource, contains("this.initialPath = '/app/home',"));
    });

    testWidgets(
      'navigation shell orders primary lanes per workspace role',
      (WidgetTester tester) async {
        // Lane order is a per-role architectural contract, not a source
        // layout one: the shell keeps a distinct destination list for each
        // workspace, so assert the rendered rail rather than the byte
        // offsets of the first matching enum literal in the file.
        for (final _WorkspaceLaneCase laneCase in _workspaceLaneCases) {
          final List<String> lanes = await _renderShellLanes(
            tester,
            session: laneCase.session,
          );
          expect(lanes, orderedEquals(laneCase.lanes), reason: laneCase.role);
          expect(lanes.first, 'Home', reason: laneCase.role);
          expect(lanes.toSet(), hasLength(lanes.length), reason: laneCase.role);
        }
      },
    );

    testWidgets('navigation shell keeps theme and capital utilities reachable', (
      WidgetTester tester,
    ) async {
      await _renderShellLanes(tester, session: _roleSession(role: 'user'));

      expect(find.byTooltip('Club funds'), findsOneWidget);
      expect(
        find.byWidgetPredicate(
          (Widget widget) =>
              widget is IconButton &&
              (widget.tooltip?.startsWith('Theme: ') ?? false),
        ),
        findsOneWidget,
      );
    });

    test('home dashboard preserves hero to secondary information order', () {
      final String homeSource = _readSource(
        'lib/features/home_dashboard/home_dashboard_screen.dart',
      );

      final int heroV2 = _indexOfOrThrow(homeSource, '_HomeHeroPanelV2(');
      final int quickActions = _indexOfOrThrow(
        homeSource,
        '_HomeQuickActionsStrip(',
      );
      final int runtimePanel = _indexOfOrThrow(
        homeSource,
        '_HomeRuntimeSignalPanel(',
      );
      final int status = _indexOfOrThrow(homeSource, 'GteSyncStatusCard(');
      final int banner = _indexOfOrThrow(
        homeSource,
        'HomeFeaturedEventBanner(',
      );
      final int majorMoves = _indexOfOrThrow(
        homeSource,
        "eyebrow: 'LIVE BOARD'",
      );
      final int journey = _indexOfOrThrow(homeSource, '_HomeJourneyPanel(');
      final int quieterSignals = _indexOfOrThrow(
        homeSource,
        "eyebrow: 'QUIETER SIGNALS'",
      );

      expect(heroV2, lessThan(banner));
      expect(banner, lessThan(quickActions));
      expect(quickActions, lessThan(runtimePanel));
      expect(runtimePanel, lessThan(status));
      expect(status, lessThan(majorMoves));
      expect(quickActions, lessThan(journey));
      expect(journey, lessThan(quieterSignals));
    });
  });

  group('controlled merge runtime contract', () {
    test('theme registry still exposes six selectable themes', () {
      expect(GteThemeRegistry.themes, hasLength(6));
      expect(
        GteThemeRegistry.themes.map(
          (GteThemeDefinition definition) => definition.metadata.id,
        ),
        orderedEquals(GteThemeId.values),
      );
    });

    test('route aliases still preserve shell compatibility', () {
      expect(
        GteNavigationRoute.parse('/app/play').primaryDestination,
        GtePrimaryDestination.competitions,
      );
      expect(
        GteNavigationRoute.parse('/app/competitions').primaryDestination,
        GtePrimaryDestination.competitions,
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
        GteNavigationRoute.parse('/app/wallet').primaryDestination,
        GtePrimaryDestination.wallet,
      );
    });

    testWidgets('theme picker switches themes and persists selection', (
      WidgetTester tester,
    ) async {
      final GteMemoryThemeStore store = GteMemoryThemeStore();
      final GteThemeController controller = GteThemeController(store: store);

      await tester.pumpWidget(_ThemePickerHarness(controller: controller));

      await tester.tap(find.text('Open theme picker'));
      await tester.pumpAndSettle();

      final Finder pickerScrollView = find.byType(Scrollable).last;
      for (final GteThemeDefinition definition in GteThemeRegistry.themes) {
        await tester.scrollUntilVisible(
          find.text(definition.metadata.label),
          200,
          scrollable: pickerScrollView,
        );
        await tester.pumpAndSettle();
        expect(find.text(definition.metadata.label), findsOneWidget);
      }

      // The loop above finishes on the last theme in the sheet, which
      // evicts Ultra Red from the virtualized list, so bring it back into
      // view before tapping it.
      await tester.scrollUntilVisible(
        find.text('Ultra Red'),
        -200,
        scrollable: pickerScrollView,
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('Ultra Red'));
      await tester.pumpAndSettle();

      expect(controller.activeThemeId, GteThemeId.ultraRed);

      final GteThemeController restored = GteThemeController(store: store);
      await restored.restore();
      expect(restored.activeThemeId, GteThemeId.ultraRed);
    });

    testWidgets('wallet overview surface opens against fixture data', (
      WidgetTester tester,
    ) async {
      final GteExchangeController controller = GteExchangeController(
        api: GteExchangeApiClient.fixture(),
      );

      await tester.pumpWidget(
        MaterialApp(home: GteWalletOverviewScreen(controller: controller)),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));
      await tester.pumpAndSettle();

      expect(find.text('Club funds'), findsOneWidget);
      expect(find.text('GTEX COIN'), findsOneWidget);
      expect(find.text('FAN COIN'), findsOneWidget);
      expect(find.text('Deposit'), findsOneWidget);
    });

    testWidgets('club sale market surface opens against fixture data', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: ClubSaleMarketScreen(
            baseUrl: 'http://127.0.0.1:8000',
            backendMode: GteBackendMode.fixture,
          ),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 300));
      await tester.pumpAndSettle();

      expect(find.text('Club sale market'), findsOneWidget);
      expect(find.text('CLUB SALE MARKET'), findsOneWidget);
      expect(
        find.text(
          'Public valuations, asking prices, and live deal posture stay readable.',
        ),
        findsOneWidget,
      );
    });
  });
}

class _ThemePickerHarness extends StatelessWidget {
  const _ThemePickerHarness({required this.controller});

  final GteThemeController controller;

  @override
  Widget build(BuildContext context) {
    return GteThemeControllerScope(
      controller: controller,
      child: AnimatedBuilder(
        animation: controller,
        builder: (BuildContext context, Widget? child) {
          return MaterialApp(
            theme: GteShellTheme.build(controller.activeTheme),
            home: Builder(
              builder:
                  (BuildContext context) => Scaffold(
                    body: Center(
                      child: FilledButton(
                        onPressed: () {
                          showModalBottomSheet<void>(
                            context: context,
                            isScrollControlled: true,
                            builder:
                                (BuildContext context) =>
                                    const GteThemePickerSheet(),
                          );
                        },
                        child: const Text('Open theme picker'),
                      ),
                    ),
                  ),
            ),
          );
        },
      ),
    );
  }
}

class _WorkspaceLaneCase {
  const _WorkspaceLaneCase({
    required this.role,
    required this.session,
    required this.lanes,
  });

  final String role;
  final GteAuthSession? session;
  final List<String> lanes;
}

final List<_WorkspaceLaneCase> _workspaceLaneCases = <_WorkspaceLaneCase>[
  const _WorkspaceLaneCase(
    role: 'guest',
    session: null,
    lanes: <String>['Home', 'Club', 'Transfer Hub', 'Matchday', 'Community'],
  ),
  _WorkspaceLaneCase(
    role: 'admin',
    session: _roleSession(role: 'admin'),
    lanes: const <String>[
      'Home',
      'Transfer Hub',
      'Matchday',
      'Club',
      'Wallet',
      'Studio',
      'Community',
    ],
  ),
  _WorkspaceLaneCase(
    role: 'coin trader',
    session: _roleSession(role: 'coin_trader'),
    lanes: const <String>['Home', 'Wallet', 'Transfer Hub', 'Community'],
  ),
  _WorkspaceLaneCase(
    role: 'creator',
    session: _roleSession(role: 'creator'),
    lanes: const <String>[
      'Home',
      'Studio',
      'Community',
      'Transfer Hub',
      'Wallet',
    ],
  ),
  _WorkspaceLaneCase(
    role: 'club owner',
    session: _roleSession(role: 'user', clubId: 'royal-lagos-fc'),
    lanes: const <String>[
      'Home',
      'Club',
      'Transfer Hub',
      'Matchday',
      'Wallet',
      'Studio',
      'Community',
    ],
  ),
  _WorkspaceLaneCase(
    role: 'staff',
    session: _roleSession(role: 'scout'),
    lanes: const <String>[
      'Home',
      'Transfer Hub',
      'Club',
      'Wallet',
      'Community',
    ],
  ),
  _WorkspaceLaneCase(
    role: 'authenticated without a club',
    session: _roleSession(role: 'user'),
    lanes: const <String>[
      'Home',
      'Transfer Hub',
      'Club',
      'Matchday',
      'Wallet',
      'Community',
    ],
  ),
];

Future<List<String>> _renderShellLanes(
  WidgetTester tester, {
  required GteAuthSession? session,
}) async {
  tester.view.physicalSize = const Size(1600, 2200);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });

  final GteExchangeController controller = GteExchangeController(
    api: GteExchangeApiClient.fixture(),
  );
  controller.session = session;

  await tester.pumpWidget(
    MaterialApp(
      home: GteNavigationShellScreen(
        controller: controller,
        apiBaseUrl: 'http://127.0.0.1:8000',
        backendMode: GteBackendMode.fixture,
        initialRoute: const GteNavigationRoute.home(),
      ),
    ),
  );
  await tester.pumpAndSettle();

  final GtexAppShell shell = tester.widget<GtexAppShell>(
    find.byType(GtexAppShell),
  );
  return shell.destinations
      .map((GtexShellDestination destination) => destination.label)
      .toList(growable: false);
}

GteAuthSession _roleSession({required String role, String? clubId}) {
  return GteAuthSession.fromJson(<String, Object?>{
    'access_token': 'contract-token',
    'token_type': 'bearer',
    'expires_in': 3600,
    if (clubId != null) 'current_club_id': clubId,
    'user': <String, Object?>{
      'id': 'contract-$role',
      'email': 'contract-$role@gtex.test',
      'username': 'contract-$role',
      'display_name': 'Contract $role',
      'role': role,
      if (clubId != null) 'current_club_id': clubId,
    },
  });
}

String _readSource(String relativePath) {
  final File file = File(relativePath);
  if (!file.existsSync()) {
    throw TestFailure('Expected source file to exist: $relativePath');
  }
  return file.readAsStringSync();
}

int _indexOfOrThrow(String source, String snippet) {
  final int index = source.indexOf(snippet);
  if (index < 0) {
    throw TestFailure('Expected snippet not found: $snippet');
  }
  return index;
}
