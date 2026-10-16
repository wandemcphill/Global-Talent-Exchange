import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:gte_frontend/core/theme/app_theme.dart';
import 'package:gte_frontend/features/club/club_screen.dart';
import 'package:gte_frontend/shared/models/club.dart';
import 'package:gte_frontend/shared/providers/club_provider.dart';

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
        overrides: [clubProvider.overrideWithValue(_fixtureClub)],
        child: MaterialApp(
          theme: AppTheme.dark(),
          home: const Scaffold(body: ClubScreen(allowFixtureData: true)),
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

  testWidgets('blocks legacy fixture club state by default', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          theme: AppTheme.dark(),
          home: const Scaffold(body: ClubScreen()),
        ),
      ),
    );
    await tester.pump();

    expect(find.text('Live club workspace unavailable'), findsOneWidget);
  });
}

const Club _fixtureClub = Club(
  id: 'fixture-club',
  name: 'Fixture Club',
  country: 'Testland',
  league: 'Fixture League',
  stadium: 'Fixture Ground',
  budgetInMillions: 186,
  startingXiRating: 84,
  academyLevel: 5,
  formLabel: 'WWDWW',
  fans: 3240000,
  badgeAsset: 'assets/branding/gtex_logo.png',
);
