import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

void main() {
  testWidgets('regen card displays explicit GSI above generic rating', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 420,
            child: GtexRegenCard(
              name: 'Liam Carver',
              archetype: 'Manager-Sim Regen',
              nationality: 'England',
              countryCode: 'ENG',
              position: 'CAM',
              gsiLabel: 'GSI 82',
              gsiTierLabel: 'High-grade',
              ratingLabel: 'OVR 78',
              potentialLabel: '88 POT',
              ageLabel: '19 yrs',
              portraitSeed: 'regen-liam-carver',
              generationLabel: 'Gen 2',
              traitLabels: <String>['Clinical Finisher', 'High Press'],
              lineageLabel: 'Inherited from Academy Lineage A',
              awardLabels: <String>['Rare Trait Discovery'],
            ),
          ),
        ),
      ),
    );

    expect(find.text('82'), findsOneWidget);
    expect(find.text('GSI'), findsOneWidget);
    expect(find.text('OVR 78'), findsOneWidget);
    expect(find.text('High-grade'), findsWidgets);
    expect(find.text('REGEN DNA'), findsOneWidget);
    expect(find.text('Gen 2'), findsOneWidget);
    expect(find.text('Clinical Finisher'), findsOneWidget);
    expect(find.text('High Press'), findsOneWidget);
    expect(find.text('Inherited from Academy Lineage A'), findsOneWidget);
    expect(find.text('Rare Trait Discovery'), findsOneWidget);
  });

  testWidgets('regen card displays portraitUrl from approved face bank', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 420,
            child: GtexRegenCard(
              name: 'Liam Carver',
              archetype: 'Manager-Sim Regen',
              nationality: 'England',
              countryCode: 'ENG',
              position: 'CAM',
              ratingLabel: '78',
              potentialLabel: '88 POT',
              ageLabel: '19 yrs',
              portraitSeed: 'regen-liam-carver',
              portraitUrl:
                  'https://media.test/generated-media/regen_newgen_faces/script_skin_hair/African/Black/African-Black-001.png',
            ),
          ),
        ),
      ),
    );

    expect(find.byKey(const Key('gtex-regen-bank-portrait')), findsOneWidget);
    expect(find.text('78'), findsOneWidget);
    expect(find.text('GSI'), findsOneWidget);
    expect(find.text('PORTRAIT PENDING'), findsNothing);
    expect(find.byIcon(Icons.auto_awesome), findsNothing);
  });

  testWidgets('regen card shows pending state without a bank portrait url', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 420,
            child: GtexRegenCard(
              name: 'Kojo Mensah',
              archetype: 'Ball-Winning Wonderkid',
              nationality: 'Ghana',
              countryCode: 'GHA',
              position: 'DM',
              ratingLabel: '71',
              potentialLabel: '91 POT',
              portraitSeed: 'regen-kojo-mensah',
            ),
          ),
        ),
      ),
    );

    expect(find.text('KOJO MENSAH'), findsOneWidget);
    expect(find.text('PORTRAIT PENDING'), findsOneWidget);
    expect(find.byIcon(Icons.person_outline), findsOneWidget);
    expect(find.byIcon(Icons.auto_awesome), findsNothing);
  });

  testWidgets('regen card does not display FM-AI fallback portraits', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 420,
            child: GtexRegenCard(
              name: 'Ayo Okafor',
              archetype: 'Academy Striker',
              nationality: 'Nigeria',
              countryCode: 'NGA',
              position: 'ST',
              ratingLabel: '74',
              potentialLabel: '92 POT',
              portraitSeed: 'regen-ayo-okafor',
              portraitUrl:
                  'https://media.test/generated-media/regen_newgen_faces/fm_ai/Caucasian1.png',
            ),
          ),
        ),
      ),
    );

    expect(find.byType(Image), findsNothing);
    expect(find.text('PORTRAIT PENDING'), findsOneWidget);
  });

  testWidgets('regen card rejects non-bank external portrait urls', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 420,
            child: GtexRegenCard(
              name: 'Mateo Silva',
              archetype: 'Created Son',
              nationality: 'Brazil',
              countryCode: 'BRA',
              position: 'LW',
              ratingLabel: '69',
              potentialLabel: '89 POT',
              portraitSeed: 'regen-mateo-silva',
              portraitUrl: 'https://licensed.test/portraits/mateo.png',
            ),
          ),
        ),
      ),
    );

    expect(find.byType(Image), findsNothing);
    expect(find.text('PORTRAIT PENDING'), findsOneWidget);
  });
}
