import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/shell/shell.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

void main() {
  testWidgets('canonical topbar primitives render and dispatch actions', (
    WidgetTester tester,
  ) async {
    bool commandSelected = false;
    bool walletTapped = false;
    bool roleTapped = false;
    bool clubTapped = false;
    bool notificationsTapped = false;
    bool themeTapped = false;
    bool quickTapped = false;

    await tester.pumpWidget(
      _Harness(
        child: GtexShellTopbar(
          title: 'World',
          contextLine: 'Ayo FC',
          tickerItems: const <String>['Matchday pulse confirmed'],
          commandActions: <GtexCommandAction>[
            GtexCommandAction(
              id: 'market.open',
              label: 'Open market',
              description: 'Open transfer market',
              icon: Icons.storefront_outlined,
              onSelected: () => commandSelected = true,
            ),
          ],
          walletBalance: 25,
          walletCurrency: 'FC',
          roleLabel: 'Manager',
          clubLabel: 'Ayo FC',
          clubState: GtexSurfaceState.confirmed,
          connectionState: GtexSurfaceState.confirmed,
          connectionLabel: 'Live',
          notificationCount: 4,
          compact: true,
          onOpenWallet: () => walletTapped = true,
          onRoleSwitcher: () => roleTapped = true,
          onClubSelector: () => clubTapped = true,
          onNotifications: () => notificationsTapped = true,
          onToggleTheme: () => themeTapped = true,
          onQuickAction: () => quickTapped = true,
        ),
      ),
    );

    expect(find.text('World'), findsOneWidget);
    expect(find.text('Matchday pulse confirmed'), findsOneWidget);
    expect(find.text('Manager'), findsOneWidget);
    expect(find.text('Ayo FC'), findsWidgets);
    expect(find.text('FC 25.00'), findsOneWidget);
    expect(find.text('4'), findsOneWidget);

    await tester.tap(find.text('Manager'));
    await tester.tap(find.text('Ayo FC').last);
    await tester.tap(find.text('FC 25.00'));
    await tester.tapAt(
      tester.getCenter(_iconButtonWithTooltip('Notifications')) -
          const Offset(14, 0),
    );
    await tester.tap(_iconButtonWithTooltip('Theme'));
    await tester.tap(_iconButtonWithTooltip('Quick actions'));

    await tester.tap(find.byTooltip('Search'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Open market'));
    await tester.pumpAndSettle();

    expect(commandSelected, isTrue);
    expect(walletTapped, isTrue);
    expect(roleTapped, isTrue);
    expect(clubTapped, isTrue);
    expect(notificationsTapped, isTrue);
    expect(themeTapped, isTrue);
    expect(quickTapped, isTrue);
  });

  testWidgets('canonical shell primitives render operational content', (
    WidgetTester tester,
  ) async {
    bool commandSelected = false;
    bool walletTapped = false;

    await tester.pumpWidget(
      _Harness(
        child: Column(
          children: <Widget>[
            const GtexLiveTicker(items: <String>['3 deals moved +12%']),
            GtexWalletChip(
              balance: 12400,
              currencyCode: 'FC',
              onTap: () => walletTapped = true,
            ),
            SizedBox(
              height: 220,
              child: GtexContextRail(
                state: GtexSurfaceState.degraded,
                stateMessage:
                    'Confirmed context remains visible while live intelligence recovers.',
                items: const <GtexContextRailItem>[
                  GtexContextRailItem(
                    id: 'trader-desk',
                    eyebrow: 'Trader',
                    title: 'Ayo Liquidity Desk',
                    detail:
                        'Online with stable settlement ETA. Trust score 96.',
                    state: GtexSurfaceState.confirmed,
                    icon: Icons.storefront_outlined,
                    metrics: <GtexEntityMetric>[
                      GtexEntityMetric(label: 'Trust', value: '96'),
                    ],
                  ),
                ],
              ),
            ),
            GtexCommandPalette(
              actions: <GtexCommandAction>[
                GtexCommandAction(
                  id: 'market.open',
                  label: 'Open transfer market',
                  description: 'Review player liquidity and baskets.',
                  icon: Icons.swap_horiz,
                  onSelected: () => commandSelected = true,
                ),
                GtexCommandAction(
                  id: 'admin.locked',
                  label: 'Open fraud queue',
                  description: 'Requires admin permission.',
                  icon: Icons.security,
                  isEnabled: false,
                  onSelected: () {},
                ),
              ],
            ),
          ],
        ),
      ),
    );

    expect(find.text('LIVE PULSE'), findsOneWidget);
    expect(find.text('3 deals moved +12%'), findsOneWidget);
    expect(find.text('FC 12400.00'), findsOneWidget);
    expect(find.text('Ayo Liquidity Desk'), findsOneWidget);
    expect(find.text('TRUST'), findsOneWidget);
    expect(find.text('96'), findsOneWidget);
    expect(find.text('Degraded'), findsOneWidget);
    expect(find.text('Open transfer market'), findsOneWidget);

    await tester.tap(find.text('FC 12400.00'));
    await tester.tap(find.text('Open transfer market'));

    expect(walletTapped, isTrue);
    expect(commandSelected, isTrue);
  });

  testWidgets('entity surfaces, banners, and empty rails use surface states', (
    WidgetTester tester,
  ) async {
    bool retryTapped = false;
    bool entityActionTapped = false;

    await tester.pumpWidget(
      _Harness(
        child: Column(
          children: <Widget>[
            GtexStateBanner(
              state: GtexSurfaceState.error,
              title: 'Shell data unavailable',
              message: 'Retry after the shell service is reachable.',
              actionLabel: 'Retry',
              onAction: () => retryTapped = true,
            ),
            GtexEntitySurface(
              state: GtexSurfaceState.blocked,
              eyebrow: 'Club',
              title: '',
              subtitle: '',
              icon: Icons.shield_outlined,
              actions: <GtexEntityAction>[
                GtexEntityAction(
                  label: 'Resolve',
                  icon: Icons.lock_open_outlined,
                  state: GtexSurfaceState.confirmed,
                  onSelected: () => entityActionTapped = true,
                ),
              ],
            ),
            const SizedBox(
              height: 220,
              child: GtexContextRail(
                items: <GtexContextRailItem>[],
                state: GtexSurfaceState.loading,
                emptyTitle: 'Loading rail',
                emptyMessage: 'Waiting for canonical shell intelligence.',
              ),
            ),
          ],
        ),
      ),
    );

    expect(find.text('Shell data unavailable'), findsOneWidget);
    expect(find.text('Context blocked'), findsNothing);
    expect(find.text('Blocked'), findsOneWidget);
    expect(find.text('Loading rail'), findsOneWidget);
    expect(
      find.text('Waiting for canonical shell intelligence.'),
      findsOneWidget,
    );

    await tester.tap(find.text('Retry'));
    await tester.tap(find.text('Resolve'));

    expect(retryTapped, isTrue);
    expect(entityActionTapped, isTrue);
  });

  testWidgets('toast, modal, and drawer hosts render actions', (
    WidgetTester tester,
  ) async {
    bool toastActionTapped = false;
    bool modalPrimaryTapped = false;
    bool drawerClosed = false;

    await tester.pumpWidget(
      _Harness(
        child: GtexToastHost(
          toasts: <GtexToastEntry>[
            GtexToastEntry(
              id: 'proof-approved',
              title: 'Payment proof approved',
              message: 'Audit reference GTEX-101 is confirmed.',
              actionLabel: 'Open',
              onAction: () => toastActionTapped = true,
            ),
          ],
          child: const SizedBox.expand(),
        ),
      ),
    );
    await tester.tap(find.text('Open'));
    expect(toastActionTapped, isTrue);

    await tester.pumpWidget(
      _Harness(
        child: GtexModalHost(
          modal: GtexModalEntry(
            title: 'Confirm settlement',
            body: const Text('Release coins after treasury confirmation.'),
            primaryLabel: 'Confirm',
            onPrimary: () => modalPrimaryTapped = true,
          ),
          child: const SizedBox.expand(),
        ),
      ),
    );
    await tester.tap(find.text('Confirm'));
    expect(modalPrimaryTapped, isTrue);

    await tester.pumpWidget(
      _Harness(
        child: GtexDrawerHost(
          drawer: GtexDrawerEntry(
            title: 'Transfer basket',
            child: const Text('Two player movements pending review.'),
            onClose: () => drawerClosed = true,
          ),
          child: const SizedBox.expand(),
        ),
      ),
    );
    await tester.tap(find.byTooltip('Close drawer'));
    expect(drawerClosed, isTrue);
  });

  testWidgets('command palette filters to empty state', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _Harness(
        child: GtexCommandPalette(
          actions: <GtexCommandAction>[
            GtexCommandAction(
              id: 'club.hq',
              label: 'Open Club HQ',
              description: 'Review squad readiness.',
              icon: Icons.shield_outlined,
              onSelected: () {},
            ),
          ],
        ),
      ),
    );

    await tester.enterText(find.byType(TextField), 'settlement desk');
    await tester.pump();

    expect(find.text('No command matches this search.'), findsOneWidget);
    expect(find.text('Open Club HQ'), findsNothing);
  });
}

class _Harness extends StatelessWidget {
  const _Harness({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      theme: GteShellTheme.build(),
      home: Scaffold(body: child),
    );
  }
}

Finder _iconButtonWithTooltip(String tooltip) {
  return find.byWidgetPredicate(
    (Widget widget) => widget is IconButton && widget.tooltip == tooltip,
    description: 'IconButton with tooltip $tooltip',
  );
}
