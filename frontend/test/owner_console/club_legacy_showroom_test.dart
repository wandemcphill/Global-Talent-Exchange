import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/owner_console/data/owner_console_api.dart';
import 'package:gte_frontend/features/owner_console/data/showroom_glb.dart';
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

Future<void> _pump(
  WidgetTester tester, {
  bool reduceMotion = false,
  bool forceStatic = false,
}) {
  tester.view.physicalSize = const Size(900, 1400);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  return tester.pumpWidget(
    MaterialApp(
      home: MediaQuery(
        data: MediaQueryData(disableAnimations: reduceMotion),
        child: Scaffold(
          body: ClubLegacyShowroom(
            exhibits: const <ShowroomExhibit>[_jet, _watch],
            forceStatic: forceStatic,
          ),
        ),
      ),
    ),
  );
}

void _expectHeavyModel(WidgetTester tester, String fileName) {
  final Text label = tester.widget<Text>(
    find.byKey(const Key('club-showroom-model-file')),
  );
  final String text = label.data ?? '';
  expect(text, contains(fileName));
  final RegExpMatch? size = RegExp(r'(\d+) KB').firstMatch(text);
  final RegExpMatch? triangles = RegExp(r'(\d+) triangles').firstMatch(text);
  expect(size, isNotNull);
  expect(triangles, isNotNull);
  expect(int.parse(size!.group(1)!), greaterThan(20));
  expect(int.parse(triangles!.group(1)!), greaterThan(1000));
}

void main() {
  testWidgets('showroom labels the owner and turns the preview', (
    WidgetTester tester,
  ) async {
    await _pump(tester);
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('club-showroom-model-loaded')), findsOneWidget);
    _expectHeavyModel(tester, 'aurelius_x1_private_jet.glb');
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
    await tester.pumpAndSettle();
    _expectHeavyModel(tester, 'meridian_luxury_watch.glb');
    expect(find.text('Owner'), findsWidgets);
    expect(find.text('Turn 0.0'), findsOneWidget);
  });

  testWidgets('an exhibit model file overrides the category mesh', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(900, 1400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: ClubLegacyShowroom(
            exhibits: <ShowroomExhibit>[
              ShowroomExhibit(
                id: 'routed-jet',
                name: 'Harbour Jet',
                category: 'jet',
                ownershipLabel: 'Club',
                fallbackLabel: 'Static jet card',
                modelFile: 'assets/showroom/gtex_voyager_club_coach.glb',
                owned: true,
              ),
            ],
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    _expectHeavyModel(tester, 'gtex_voyager_club_coach.glb');
  });

  testWidgets('reduced motion uses the static card', (
    WidgetTester tester,
  ) async {
    await _pump(tester, reduceMotion: true);
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('club-showroom-static')), findsOneWidget);
    expect(find.byKey(const Key('club-showroom-preview')), findsOneWidget);
    expect(find.text('Static jet card'), findsWidgets);
    expect(find.byKey(const Key('club-showroom-rotate-right')), findsNothing);
    expect(find.byKey(const Key('club-showroom-zoom')), findsNothing);
  });

  testWidgets('full screen opens its own view and closes', (
    WidgetTester tester,
  ) async {
    await _pump(tester);
    await tester.tap(find.byKey(const Key('club-showroom-fullscreen')));
    await tester.pumpAndSettle();
    expect(
      find.byKey(const Key('club-showroom-fullscreen-view')),
      findsOneWidget,
    );
    expect(
      find.byKey(const Key('club-showroom-fullscreen-model')),
      findsOneWidget,
    );
    expect(
      find.byKey(const Key('club-showroom-fullscreen-ownership')),
      findsOneWidget,
    );
    expect(find.text('Club'), findsWidgets);

    await tester.tap(find.byKey(const Key('club-showroom-fullscreen-rotate')));
    await tester.pump();
    expect(find.text('Turn 0.4'), findsWidgets);

    await tester.tap(find.byKey(const Key('club-showroom-fullscreen-close')));
    await tester.pumpAndSettle();
    expect(
      find.byKey(const Key('club-showroom-fullscreen-view')),
      findsNothing,
    );
    expect(find.byKey(const Key('club-showroom')), findsOneWidget);
  });

  testWidgets('a missing model shows the preview image', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(900, 1400);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: ClubLegacyShowroom(
            exhibits: <ShowroomExhibit>[
              ShowroomExhibit(
                id: 'broken',
                name: 'Harbour Jet',
                category: 'jet',
                ownershipLabel: 'Club',
                fallbackLabel: 'Static jet card',
                modelFile: 'assets/showroom/does_not_exist.glb',
                previewFile: 'assets/showroom/aurelius_x1_private_jet.png',
                owned: true,
              ),
            ],
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.textContaining('Could not read'), findsOneWidget);
    expect(find.byKey(const Key('club-showroom-preview')), findsOneWidget);
    expect(find.byKey(const Key('club-showroom-model-loaded')), findsNothing);
  });

  testWidgets('a phone width still frames the loaded model', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(390, 700);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: ClubLegacyShowroom(exhibits: <ShowroomExhibit>[_jet]),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
    expect(find.byKey(const Key('club-showroom-model-loaded')), findsOneWidget);
    await tester.drag(
      find.byKey(const Key('club-showroom-zoom')),
      const Offset(90, 0),
    );
    await tester.pump();
    expect(find.text('Turn 0.0'), findsNothing);
  });

  test('all six starter models load at their source size', () async {
    TestWidgetsFlutterBinding.ensureInitialized();
    const Map<String, int> triangles = <String, int>{
      'assets/showroom/aurelius_x1_private_jet.glb': 6144,
      'assets/showroom/gtex_voyager_club_coach.glb': 2444,
      'assets/showroom/velocity_r_hypercar.glb': 4500,
      'assets/showroom/meridian_luxury_watch.glb': 1300,
      'assets/showroom/legacy_arena_stadium.glb': 3900,
      'assets/showroom/gtex_performance_campus.glb': 3924,
    };
    for (final MapEntry<String, int> entry in triangles.entries) {
      final ShowroomGlb model = await loadShowroomGlb(entry.key);
      expect(model.byteLength, greaterThan(20000));
      expect(model.triangleCount, entry.value);
      expect(model.parts, isNotEmpty);
    }
    final ShowroomGlb watch = await loadShowroomGlb(
      'assets/showroom/meridian_luxury_watch.glb',
    );
    final ShowroomGlb stadium = await loadShowroomGlb(
      'assets/showroom/legacy_arena_stadium.glb',
    );
    expect(watch.sourceExtent, lessThan(1));
    expect(stadium.sourceExtent, greaterThan(100));
  });
}
