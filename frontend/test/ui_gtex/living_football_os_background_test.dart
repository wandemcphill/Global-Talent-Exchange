import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/navigation/model/gtex_shell_navigation_model.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

const ShellNavigationModel _testNavigationModel = ShellNavigationModel(
  capabilities: GtexShellCapabilities(
    isAuthenticated: true,
    ownedClubIds: <String>['royal-lagos-fc'],
    activeClubId: 'royal-lagos-fc',
    isAdmin: true,
    clubLegacyEnabled: true,
  ),
);

void main() {
  testWidgets(
    'GtexShellScaffold renders LivingFootballOSBackground behind shell',
    (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: GtexShellScaffold(
            navigationModel: _testNavigationModel,
            selectedSlotId: GtexShellSlotId.home,
            onSelectSlot: (_) {},
            topBar: const GtexTopBar(
              title: 'GTEX Command',
              subtitle: 'Football operating system',
            ),
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
      expect(
        find.byKey(const Key('living-football-os-tactics')),
        findsOneWidget,
      );
      expect(
        find.byKey(const Key('living-football-os-particles')),
        findsOneWidget,
      );
      expect(find.text('GTEX Command'), findsOneWidget);
      expect(find.text('Route content'), findsOneWidget);
    },
  );

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
          home: GtexShellScaffold(
            navigationModel: _testNavigationModel,
            selectedSlotId: GtexShellSlotId.home,
            onSelectSlot: (_) {},
            topBar: GtexTopBar(title: 'GTEX Command', subtitle: routeLabel),
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

  testWidgets('compact shell keeps overflow destinations reachable', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    String? tapped;

    await tester.pumpWidget(
      MaterialApp(
        home: GtexShellScaffold(
          navigationModel: _testNavigationModel,
          selectedSlotId: GtexShellSlotId.home,
          onSelectSlot: (_) {},
          onSelectSecondary: (GtexSecondaryDestinationSpec item) {
            tapped = item.label;
          },
          topBar: const GtexTopBar(title: 'GTEX Command'),
          child: const SizedBox.shrink(),
        ),
      ),
    );
    await tester.pump();

    expect(find.text('More'), findsOneWidget);
    expect(find.text('Admin'), findsNothing);

    await tester.tap(find.text('More'));
    await tester.pumpAndSettle();

    expect(find.text('Admin'), findsOneWidget);
    await tester.tap(find.text('Admin'));
    await tester.pumpAndSettle();
    expect(tapped, 'Admin');
  });
}
