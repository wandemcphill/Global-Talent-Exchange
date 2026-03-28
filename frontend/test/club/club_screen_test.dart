import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:gte_frontend/core/theme/app_theme.dart';
import 'package:gte_frontend/features/club/club_screen.dart';

void main() {
  testWidgets('renders club dashboard tabs', (WidgetTester tester) async {
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
          home: const Scaffold(body: ClubScreen()),
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 450));

    expect(find.text('Club HQ'), findsOneWidget);
    expect(find.byKey(const Key('club-squad-slot-gk')), findsOneWidget);

    await tester.tap(find.byKey(const Key('club-tab-finance')));
    await tester.pumpAndSettle();
    expect(find.text('Cashflow trend'), findsOneWidget);

    await tester.tap(find.byKey(const Key('club-tab-fans')));
    await tester.pumpAndSettle();
    expect(find.text('Supporter mood'), findsOneWidget);

    await tester.tap(find.byKey(const Key('club-tab-identity')));
    await tester.pumpAndSettle();
    expect(find.text('Identity score'), findsOneWidget);
  });
}
