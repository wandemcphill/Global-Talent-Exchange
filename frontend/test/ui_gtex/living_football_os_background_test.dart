import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

void main() {
  testWidgets('GtexAppShell renders LivingFootballOSBackground behind shell', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: GtexAppShell(
          title: 'GTEX Command',
          subtitle: 'Football operating system',
          destinations: <GtexShellDestination>[
            GtexShellDestination(
              label: 'Home',
              icon: Icons.home_outlined,
              selectedIcon: Icons.home,
              isSelected: true,
              onTap: () {},
            ),
            GtexShellDestination(
              label: 'Market',
              icon: Icons.storefront_outlined,
              selectedIcon: Icons.storefront,
              isSelected: false,
              onTap: () {},
            ),
          ],
          child: const Center(child: Text('Route content')),
        ),
      ),
    );
    await tester.pump();

    expect(find.byType(LivingFootballOSBackground), findsOneWidget);
    expect(
      find.byKey(const Key('living-football-os-background')),
      findsOneWidget,
    );
    expect(
      find.byKey(const Key('living-football-os-atmosphere')),
      findsOneWidget,
    );
    expect(
      find.byKey(const Key('living-football-os-stadium-lights')),
      findsOneWidget,
    );
    expect(find.byKey(const Key('living-football-os-tactics')), findsOneWidget);
    expect(
      find.byKey(const Key('living-football-os-particles')),
      findsOneWidget,
    );
    expect(find.text('GTEX Command'), findsOneWidget);
    expect(find.text('Route content'), findsOneWidget);
  });

  testWidgets(
    'LivingFootballOSBackground uses static fallback when motion is off',
    (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: MediaQuery(
            data: MediaQueryData(
              size: Size(1280, 800),
              disableAnimations: true,
            ),
            child: LivingFootballOSBackground(
              motionEnabledOverride: false,
              child: Directionality(
                textDirection: TextDirection.ltr,
                child: Text('Static workspace'),
              ),
            ),
          ),
        ),
      );
      await tester.pump();

      expect(
        find.byKey(const Key('living-football-os-static-wallpaper')),
        findsOneWidget,
      );
      expect(find.text('Static workspace'), findsOneWidget);
    },
  );

  testWidgets('GtexPageSurface renders a glass surface over content', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: GtexPageSurface(child: Text('Glass command panel')),
        ),
      ),
    );

    expect(find.byType(GtexPageSurface), findsOneWidget);
    expect(find.text('Glass command panel'), findsOneWidget);
  });

  testWidgets('shared background survives representative shell route changes', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1440, 1000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    const List<String> routeLabels = <String>[
      'Home workspace',
      'Transfer Hub workspace',
      'Wallet workspace',
      'Club workspace',
      'Social workspace',
      'Admin workspace',
    ];

    for (final String routeLabel in routeLabels) {
      await tester.pumpWidget(
        MaterialApp(
          home: GtexAppShell(
            title: 'GTEX Command',
            subtitle: routeLabel,
            destinations: <GtexShellDestination>[
              GtexShellDestination(
                label: 'Home',
                icon: Icons.home_outlined,
                selectedIcon: Icons.home,
                isSelected: routeLabel.startsWith('Home'),
                onTap: () {},
              ),
              GtexShellDestination(
                label: 'Transfer Hub',
                icon: Icons.storefront_outlined,
                selectedIcon: Icons.storefront,
                isSelected: routeLabel.startsWith('Transfer'),
                onTap: () {},
              ),
              GtexShellDestination(
                label: 'Wallet',
                icon: Icons.account_balance_wallet_outlined,
                selectedIcon: Icons.account_balance_wallet,
                isSelected: routeLabel.startsWith('Wallet'),
                onTap: () {},
              ),
              GtexShellDestination(
                label: 'Club',
                icon: Icons.shield_outlined,
                selectedIcon: Icons.shield,
                isSelected: routeLabel.startsWith('Club'),
                onTap: () {},
              ),
              GtexShellDestination(
                label: 'Social',
                icon: Icons.forum_outlined,
                selectedIcon: Icons.forum,
                isSelected: routeLabel.startsWith('Social'),
                onTap: () {},
              ),
            ],
            child: Center(child: Text(routeLabel)),
          ),
        ),
      );
      await tester.pump();

      expect(
        find.byType(LivingFootballOSBackground),
        findsOneWidget,
        reason: '$routeLabel should use the shared shell background',
      );
      expect(find.text(routeLabel), findsWidgets);
    }
  });
}
