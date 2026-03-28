import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/core/theme/app_theme.dart';
import 'package:gte_frontend/features/player_detail/player_detail_screen.dart';
import 'package:gte_frontend/shared/models/player.dart';

void main() {
  testWidgets('renders player detail tabs and generated content', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1280, 1800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    const Player player = Player(
      id: 'detail-okoro',
      name: 'Daniel Okoro',
      position: 'ST',
      country: 'Nigeria',
      age: 20,
      rating: 91,
      potential: 95,
      valueInMillions: 42,
      pace: 0.9,
      technique: 0.86,
      mentality: 0.84,
      image: 'assets/branding/gtex_icon.png',
      isHot: true,
    );

    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.dark(),
        home: const PlayerDetailScreen(
          player: player,
          heroTag: 'player-detail-test-hero',
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));

    expect(find.text('Player Detail'), findsOneWidget);
    expect(find.text('Daniel Okoro'), findsOneWidget);
    expect(find.text('Elite'), findsOneWidget);
    expect(find.byType(Hero), findsOneWidget);
    expect(find.byKey(const Key('player-detail-stats-view')), findsOneWidget);

    await tester.tap(find.byKey(const Key('player-detail-tab-story')));
    await tester.pumpAndSettle();

    expect(find.text('First-team ignition'), findsOneWidget);

    await tester.tap(find.byKey(const Key('player-detail-tab-career')));
    await tester.pumpAndSettle();

    expect(find.text('GTEX Youth Select'), findsOneWidget);

    await tester.tap(find.byKey(const Key('player-detail-tab-offers')));
    await tester.pumpAndSettle();

    expect(find.text('North Star FC'), findsOneWidget);
    expect(find.text('Leading offer'), findsOneWidget);
  });
}
