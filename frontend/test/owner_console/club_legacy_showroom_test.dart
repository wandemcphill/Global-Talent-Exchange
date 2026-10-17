import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/owner_console/data/owner_console_api.dart';
import 'package:gte_frontend/features/owner_console/widgets/club_legacy_showroom.dart';

const ShowroomExhibit _jet = ShowroomExhibit(
  id: 'jet-1',
  name: 'Harbour Jet',
  category: 'jet',
  ownershipLabel: 'Club',
  fallbackLabel: 'Static jet card',
  owned: true,
);

const ShowroomExhibit _watch = ShowroomExhibit(
  id: 'watch-1',
  name: 'Icon Watch',
  category: 'watch',
  ownershipLabel: 'Owner',
  fallbackLabel: 'Static watch card',
  owned: true,
);

Future<void> _pump(WidgetTester tester, {bool reduceMotion = false, bool forceStatic = false}) {
  tester.view.physicalSize = const Size(900, 1400);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  return tester.pumpWidget(
    MaterialApp(
      home: MediaQuery(
        data: MediaQueryData(disableAnimations: reduceMotion),
        child: Scaffold(
          body: ClubLegacyShowroom(exhibits: const <ShowroomExhibit>[_jet, _watch], forceStatic: forceStatic),
        ),
      ),
    ),
  );
}

void main() {
  testWidgets('showroom labels the owner and turns the preview', (WidgetTester tester) async {
    await _pump(tester);
    expect(find.text('Club'), findsWidgets);
    expect(find.byKey(const Key('club-showroom-zoom')), findsOneWidget);
    expect(find.text('Turn 0.0'), findsOneWidget);

    await tester.tap(find.byKey(const Key('club-showroom-rotate-right')));
    await tester.pump();
    expect(find.text('Turn 0.4'), findsOneWidget);

    await tester.tap(find.byKey(const Key('club-showroom-reset')));
    await tester.pump();
    expect(find.text('Turn 0.0'), findsOneWidget);

    await tester.tap(find.byKey(const Key('club-showroom-pick-watch-1')));
    await tester.pump();
    expect(find.text('Owner'), findsWidgets);
    expect(find.text('Turn 0.0'), findsOneWidget);
  });

  testWidgets('reduced motion uses the static card', (WidgetTester tester) async {
    await _pump(tester, reduceMotion: true);
    expect(find.byKey(const Key('club-showroom-static')), findsOneWidget);
    expect(find.byKey(const Key('club-showroom-static-card')), findsOneWidget);
    expect(find.text('Static jet card'), findsWidgets);
    expect(find.byKey(const Key('club-showroom-rotate-right')), findsNothing);
    expect(find.byKey(const Key('club-showroom-zoom')), findsNothing);
  });

  testWidgets('full screen opens its own view and closes', (WidgetTester tester) async {
    await _pump(tester);
    await tester.tap(find.byKey(const Key('club-showroom-fullscreen')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('club-showroom-fullscreen-view')), findsOneWidget);
    expect(find.byKey(const Key('club-showroom-fullscreen-ownership')), findsOneWidget);
    expect(find.text('Club'), findsWidgets);

    await tester.tap(find.byKey(const Key('club-showroom-fullscreen-rotate')));
    await tester.pump();
    expect(find.text('Turn 0.4'), findsWidgets);

    await tester.tap(find.byKey(const Key('club-showroom-fullscreen-close')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('club-showroom-fullscreen-view')), findsNothing);
    expect(find.byKey(const Key('club-showroom')), findsOneWidget);
  });
}
