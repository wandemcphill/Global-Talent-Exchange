import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/shell/shell.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('desktop shell keeps left rail and right intelligence rail', (
    WidgetTester tester,
  ) async {
    await _pumpShell(tester, size: const Size(1440, 920));

    expect(find.byKey(_leftRailKey), findsOneWidget);
    expect(find.byKey(_rightIntelligenceRailKey), findsOneWidget);
    expect(find.byKey(_mobileBottomNavKey), findsNothing);
    expect(find.byTooltip('Open intelligence rail'), findsNothing);
    expect(find.text('INTELLIGENCE'), findsOneWidget);
    expect(find.text('Scouting confidence'), findsOneWidget);
  });

  testWidgets('tablet shell uses compact rail and intelligence drawer', (
    WidgetTester tester,
  ) async {
    await _pumpShell(tester, size: const Size(900, 820));

    expect(find.byKey(_leftRailKey), findsOneWidget);
    expect(find.byKey(_rightIntelligenceRailKey), findsNothing);
    expect(find.byKey(_mobileBottomNavKey), findsNothing);
    expect(find.byTooltip('Open navigation drawer'), findsNothing);
    expect(find.byTooltip('Open intelligence rail'), findsOneWidget);

    await tester.tap(find.byTooltip('Open intelligence rail'));
    await tester.pump();

    expect(find.byKey(_intelligenceDrawerKey), findsOneWidget);
    expect(find.text('Scouting confidence'), findsOneWidget);
    expect(find.textContaining('Feed is degraded'), findsOneWidget);
  });

  testWidgets('mobile shell exposes bottom nav and navigation drawer', (
    WidgetTester tester,
  ) async {
    String? selectedDestination;
    await _pumpShell(
      tester,
      size: const Size(430, 860),
      onDestinationSelected: (String destinationId) {
        selectedDestination = destinationId;
      },
    );

    expect(find.byKey(_leftRailKey), findsNothing);
    expect(find.byKey(_rightIntelligenceRailKey), findsNothing);
    expect(find.byKey(_mobileBottomNavKey), findsOneWidget);
    expect(find.byTooltip('Open navigation drawer'), findsOneWidget);
    expect(find.byTooltip('Open intelligence rail'), findsOneWidget);

    await tester.tap(
      find.descendant(
        of: find.byKey(_mobileBottomNavKey),
        matching: find.text('Wallet'),
      ),
    );
    expect(selectedDestination, 'wallet');

    await tester.tap(find.byTooltip('Open navigation drawer'));
    await tester.pump();

    final Finder navigationDrawer = find.byKey(_navigationDrawerKey);
    expect(navigationDrawer, findsOneWidget);
    expect(
      find.descendant(of: navigationDrawer, matching: find.text('Club Alpha')),
      findsOneWidget,
    );

    await tester.tap(
      find.descendant(of: navigationDrawer, matching: find.text('Market')),
    );
    await tester.pump();

    expect(selectedDestination, 'market');
    expect(find.byKey(_navigationDrawerKey), findsNothing);
  });

  testWidgets('right rail reports missing shell data with surface states', (
    WidgetTester tester,
  ) async {
    const Map<GtexSurfaceState, String> expectedTitles =
        <GtexSurfaceState, String>{
          GtexSurfaceState.confirmed: 'No intelligence selected',
          GtexSurfaceState.loading: 'Loading intelligence',
          GtexSurfaceState.blocked: 'Intelligence blocked',
          GtexSurfaceState.degraded: 'Intelligence degraded',
          GtexSurfaceState.error: 'Intelligence failed',
        };

    for (final MapEntry<GtexSurfaceState, String> entry
        in expectedTitles.entries) {
      await _pumpShell(
        tester,
        size: const Size(1280, 820),
        contextItems: const <GtexContextRailItem>[],
        connectionState: entry.key,
      );

      expect(find.byKey(_rightIntelligenceRailKey), findsOneWidget);
      expect(find.text(entry.value), findsOneWidget);
    }
  });
}

const ValueKey<String> _leftRailKey = ValueKey<String>('gtex-shell-left-rail');
const ValueKey<String> _rightIntelligenceRailKey = ValueKey<String>(
  'gtex-shell-right-intelligence-rail',
);
const ValueKey<String> _mobileBottomNavKey = ValueKey<String>(
  'gtex-shell-mobile-bottom-nav',
);
const ValueKey<String> _navigationDrawerKey = ValueKey<String>(
  'gtex-shell-navigation-drawer',
);
const ValueKey<String> _intelligenceDrawerKey = ValueKey<String>(
  'gtex-shell-intelligence-drawer',
);

Future<void> _pumpShell(
  WidgetTester tester, {
  required Size size,
  List<GtexContextRailItem>? contextItems,
  GtexSurfaceState connectionState = GtexSurfaceState.confirmed,
  ValueChanged<String>? onDestinationSelected,
}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1.0;
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });

  await tester.pumpWidget(
    MaterialApp(
      theme: GteShellTheme.build(),
      home: GtexOperatingShell(
        destinations: _destinations,
        activeDestinationId: 'world',
        onDestinationSelected: onDestinationSelected ?? (_) {},
        title: 'GTEX Command',
        contextLine: 'Canonical shell responsive test',
        tickerItems: const <String>['Live market pulse confirmed'],
        contextItems: contextItems ?? _contextItems,
        commandActions: <GtexCommandAction>[
          GtexCommandAction(
            id: 'search.players',
            label: 'Search players',
            description: 'Find players, clubs, and trader desks.',
            icon: Icons.search_rounded,
            onSelected: () {},
          ),
        ],
        walletBalance: 4200,
        walletCurrency: 'FC',
        roleLabel: 'Trader',
        clubLabel: 'Club Alpha',
        connectionLabel: connectionState.name,
        connectionState: connectionState,
        body: const ColoredBox(
          color: Colors.transparent,
          child: Center(child: Text('Responsive shell body')),
        ),
      ),
    ),
  );
  await tester.pump();
}

const List<GtexShellDestination> _destinations = <GtexShellDestination>[
  GtexShellDestination(
    id: 'world',
    label: 'World',
    icon: Icons.public_outlined,
    selectedIcon: Icons.public,
    tone: Color(0xFF69F3A4),
  ),
  GtexShellDestination(
    id: 'market',
    label: 'Market',
    icon: Icons.swap_horiz_outlined,
    selectedIcon: Icons.swap_horiz,
    tone: Color(0xFF66D7FF),
  ),
  GtexShellDestination(
    id: 'wallet',
    label: 'Wallet',
    icon: Icons.account_balance_wallet_outlined,
    selectedIcon: Icons.account_balance_wallet,
    tone: Color(0xFFFFD75B),
  ),
];

const List<GtexContextRailItem> _contextItems = <GtexContextRailItem>[
  GtexContextRailItem(
    id: 'scouting',
    eyebrow: 'Scouting',
    title: 'Scouting confidence',
    detail: 'Feed is degraded while the last confirmed profile remains shown.',
    state: GtexSurfaceState.degraded,
    icon: Icons.insights_outlined,
  ),
];
