import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/core/theme/app_theme.dart';
import 'package:gte_frontend/features/match/match_screen.dart';

void main() {
  testWidgets(
    'match screen renders broadcast layers and draggable stats panel',
    (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1440, 1200);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() {
        tester.view.resetPhysicalSize();
        tester.view.resetDevicePixelRatio();
      });

      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            theme: AppTheme.dark(),
            home: const Scaffold(body: MatchScreen()),
          ),
        ),
      );

      await tester.pumpAndSettle();

      expect(
        find.byKey(const Key('match-broadcast-placeholder')),
        findsOneWidget,
      );
      expect(find.byKey(const Key('match-score-overlay')), findsOneWidget);
      expect(find.byKey(const Key('match-push-overlay')), findsOneWidget);
      expect(find.byKey(const Key('match-commentary-bar')), findsOneWidget);
      expect(find.byKey(const Key('match-stats-panel')), findsOneWidget);
      expect(find.text('BUILD'), findsWidgets);
      expect(find.text('Live Win %'), findsOneWidget);

      await tester.pump(const Duration(seconds: 3));
      await tester.pumpAndSettle();

      expect(find.text('LIVE'), findsWidgets);

      await tester.drag(
        find.byKey(const Key('match-stats-handle')),
        const Offset(0, -220),
      );
      await tester.pumpAndSettle();

      expect(find.text('Match Stats'), findsOneWidget);
      expect(find.text('Market Pulse'), findsOneWidget);
      expect(find.text('Event Tape'), findsOneWidget);
      expect(find.text('Push Signal'), findsOneWidget);
      expect(find.text('Other Live Windows'), findsOneWidget);

      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pump();
    },
  );
}
