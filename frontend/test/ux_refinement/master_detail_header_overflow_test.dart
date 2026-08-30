import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

/// The master-detail header used to lay the action `Wrap` out as an
/// unbounded child of a `Row`, so wide action sets overflowed the header
/// horizontally (169px on the live club-owner dashboard). These tests pin
/// the responsive behaviour without hard-coding pixel geometry.
void main() {
  Widget harness(Size size, {List<Widget> actions = const <Widget>[]}) {
    return MaterialApp(
      theme: ThemeData.dark(),
      home: MediaQuery(
        data: MediaQueryData(size: size),
        child: Scaffold(
          backgroundColor: GtexColors.surfaceBase,
          body: GtexMasterDetailScaffold(
            title: 'Club command',
            subtitle: 'Ikorodu City Football Club - owner workspace',
            leftPanel: const Text('Sections'),
            detail: const Text('Detail'),
            rightPanel: const Text('Right rail'),
            actions: actions,
          ),
        ),
      ),
    );
  }

  List<Widget> clubActions() => <Widget>[
    GtexActionButton(
      label: 'Market',
      icon: Icons.shopping_basket_outlined,
      onPressed: () {},
      accent: GtexColors.pitch,
    ),
    GtexActionButton(
      label: 'Create competition',
      icon: Icons.add_circle_outline,
      onPressed: () {},
      accent: GtexColors.gold,
    ),
  ];

  for (final ({String name, Size size}) variant in <({String name, Size size})>[
    (name: 'previously failing tablet width', size: Size(900, 700)),
    (name: 'desktop', size: Size(1440, 900)),
    (name: 'narrow desktop', size: Size(1024, 768)),
    (name: 'mobile', size: Size(390, 844)),
  ]) {
    testWidgets('master-detail header does not overflow - ${variant.name}', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = variant.size;
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);

      await tester.pumpWidget(harness(variant.size, actions: clubActions()));
      await tester.pump();

      // Any RenderFlex overflow is reported through the exception channel.
      expect(tester.takeException(), isNull);

      // Title survives.
      expect(find.text('Club command'), findsOneWidget);
      // Actions stay visible and usable at every width.
      expect(find.text('Market'), findsOneWidget);
      expect(find.text('Create competition'), findsOneWidget);
    });
  }

  testWidgets('long titles do not push actions off-screen', (
    WidgetTester tester,
  ) async {
    const Size size = Size(900, 700);
    tester.view.physicalSize = size;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      MaterialApp(
        theme: ThemeData.dark(),
        home: MediaQuery(
          data: const MediaQueryData(size: size),
          child: Scaffold(
            body: GtexMasterDetailScaffold(
              title:
                  'Federation of Association Football Clubs Command Workspace '
                  'For Owners And Delegated Administrators',
              subtitle:
                  'An intentionally very long subtitle that would previously '
                  'have forced the action row past the right edge.',
              leftPanel: const Text('Sections'),
              detail: const Text('Detail'),
              actions: clubActions(),
            ),
          ),
        ),
      ),
    );
    await tester.pump();

    expect(tester.takeException(), isNull);
    expect(find.text('Market'), findsOneWidget);
    expect(find.text('Create competition'), findsOneWidget);

    // Actions render inside the viewport, not clipped off the right edge.
    final Rect actionRect = tester.getRect(find.text('Create competition'));
    expect(actionRect.right, lessThanOrEqualTo(size.width));
    expect(actionRect.left, greaterThanOrEqualTo(0));
  });
}
