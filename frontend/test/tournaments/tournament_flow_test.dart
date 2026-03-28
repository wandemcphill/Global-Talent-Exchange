import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:gte_frontend/core/theme/app_theme.dart';
import 'package:gte_frontend/features/tournaments/tournaments_screen.dart';

void main() {
  testWidgets('opens tournament intro and enters tournament screen', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1280, 1800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          theme: AppTheme.dark(),
          home: const Scaffold(body: TournamentsScreen()),
        ),
      ),
    );
    await tester.pump();

    expect(find.text('Tournaments'), findsOneWidget);

    await tester.tap(find.byKey(const Key('tournament-launch-open-intro')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('tournament-enter-button')), findsOneWidget);

    await tester.tap(find.byKey(const Key('tournament-enter-button')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('tournament-fixtures-view')), findsOneWidget);
    expect(find.text('Feature Match'), findsOneWidget);

    await tester.tap(find.byKey(const Key('tournament-tab-standings')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('tournament-standings-view')), findsOneWidget);
    expect(find.text('Lagos Atlas FC'), findsOneWidget);

    await tester.tap(find.byKey(const Key('tournament-tab-squad')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('tournament-squad-view')), findsOneWidget);
    expect(find.text('Daniel Okoro'), findsWidgets);
  });
}
