import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:gte_frontend/core/theme/app_theme.dart';
import 'package:gte_frontend/features/compete/presentation/tournaments_compat.dart';

void main() {
  testWidgets('legacy tournament route resolves to canonical compete arena', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          theme: AppTheme.dark(),
          home: const Scaffold(body: TournamentsScreen()),
        ),
      ),
    );
    await tester.pump();

    expect(find.text('Arena'), findsWidgets);
    expect(find.byKey(const Key('tournament-launch-open-intro')), findsNothing);
    expect(find.byKey(const Key('tournament-fixtures-view')), findsNothing);
  });
}
