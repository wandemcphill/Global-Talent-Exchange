@Tags(<String>['golden'])
library;

import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/onboarding_redesign/components/gtex_club_ownership_section.dart';
import 'package:gte_frontend/features/onboarding_redesign/components/gtex_competitions_and_jackpot_section.dart';
import 'package:gte_frontend/features/onboarding_redesign/components/gtex_living_world_section.dart';
import 'package:gte_frontend/features/onboarding_redesign/components/gtex_regen_economy_section.dart';
import 'package:gte_frontend/features/onboarding_redesign/components/gtex_tv_and_finance_section.dart';
import 'package:gte_frontend/features/onboarding_redesign/gtex_public_landing_screen_v2.dart';

const String _out = '../../../design-concepts/public/implemented';
const Key _frame = ValueKey<String>('capture-frame');

Future<ByteData> _fontFile(String path) async =>
    ByteData.sublistView(Uint8List.fromList(File(path).readAsBytesSync()));

Future<void> _loadFonts() async {
  final Map<String, List<String>> families = <String, List<String>>{
    'Inter': <String>[
      'assets/fonts/Inter.ttf',
    ],
    'BarlowCondensed': <String>[
      'assets/fonts/BarlowCondensed-Regular.ttf',
      'assets/fonts/BarlowCondensed-SemiBold.ttf',
      'assets/fonts/BarlowCondensed-Bold.ttf',
    ],
    'DMMono': <String>[
      'assets/fonts/DMMono-Regular.ttf',
      'assets/fonts/DMMono-Medium.ttf',
    ],
  };

  for (final MapEntry<String, List<String>> entry in families.entries) {
    final FontLoader loader = FontLoader(entry.key);
    for (final String path in entry.value) {
      if (File(path).existsSync()) {
        loader.addFont(_fontFile(path));
      }
    }
    await loader.load();
  }
}

ThemeData _testTheme() {
  return ThemeData(
    brightness: Brightness.dark,
    fontFamily: 'Inter',
  );
}

Future<void> _capture(
  WidgetTester tester, {
  required String name,
  required Size size,
  required Widget child,
}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);
  try {
    await tester.pumpWidget(RepaintBoundary(key: _frame, child: child));
    for (int i = 0; i < 30; i += 1) {
      await tester.pump(const Duration(milliseconds: 50));
    }
    while (tester.takeException() != null) {}
    await expectLater(find.byKey(_frame), matchesGoldenFile('$_out/$name.png'));
  } finally {}
}

void main() {
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    await _loadFonts();
  });

  testWidgets('capture landing desktop', (WidgetTester tester) async {
    await _capture(
      tester,
      name: 'landing-desktop',
      size: const Size(1440, 1000),
      child: MaterialApp(
        debugShowCheckedModeBanner: false,
        theme: _testTheme(),
        home: const GtexPublicLandingScreenV2(),
      ),
    );
  });

  testWidgets('capture landing mobile', (WidgetTester tester) async {
    await _capture(
      tester,
      name: 'landing-mobile',
      size: const Size(390, 844),
      child: MaterialApp(
        debugShowCheckedModeBanner: false,
        theme: _testTheme(),
        home: const GtexPublicLandingScreenV2(),
      ),
    );
  });

  testWidgets('capture landing ownership desktop', (WidgetTester tester) async {
    await _capture(
      tester,
      name: 'landing-ownership-desktop',
      size: const Size(1440, 1100),
      child: MaterialApp(
        debugShowCheckedModeBanner: false,
        theme: _testTheme(),
        home: const Scaffold(
          backgroundColor: Color(0xFF0B1626),
          body: SingleChildScrollView(child: GtexClubOwnershipSection()),
        ),
      ),
    );
  });

  testWidgets('capture landing tv finance desktop', (WidgetTester tester) async {
    await _capture(
      tester,
      name: 'landing-tv-finance-desktop',
      size: const Size(1440, 1050),
      child: MaterialApp(
        debugShowCheckedModeBanner: false,
        theme: _testTheme(),
        home: const Scaffold(
          backgroundColor: Color(0xFF0B1626),
          body: SingleChildScrollView(child: GtexTvAndFinanceSection()),
        ),
      ),
    );
  });

  testWidgets('capture landing regens desktop', (WidgetTester tester) async {
    await _capture(
      tester,
      name: 'landing-regens-desktop',
      size: const Size(1440, 1100),
      child: MaterialApp(
        debugShowCheckedModeBanner: false,
        theme: _testTheme(),
        home: const Scaffold(
          backgroundColor: Color(0xFF0B1626),
          body: SingleChildScrollView(child: GtexRegenEconomySection()),
        ),
      ),
    );
  });

  testWidgets('capture landing competitions desktop', (WidgetTester tester) async {
    await _capture(
      tester,
      name: 'landing-competitions-desktop',
      size: const Size(1440, 1050),
      child: MaterialApp(
        debugShowCheckedModeBanner: false,
        theme: _testTheme(),
        home: const Scaffold(
          backgroundColor: Color(0xFF0B1626),
          body: SingleChildScrollView(child: GtexCompetitionsAndJackpotSection()),
        ),
      ),
    );
  });

  testWidgets('capture landing newsroom desktop', (WidgetTester tester) async {
    await _capture(
      tester,
      name: 'landing-newsroom-desktop',
      size: const Size(1440, 1050),
      child: MaterialApp(
        debugShowCheckedModeBanner: false,
        theme: _testTheme(),
        home: const Scaffold(
          backgroundColor: Color(0xFF0B1626),
          body: SingleChildScrollView(child: GtexLivingWorldSection()),
        ),
      ),
    );
  });
}
