import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../lib/ui_gtex/football/gtex_regen_portrait.dart';

gvoid main() {
  testWidgets('renders a Cloudinary regen face-bank portrait URL', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: GtexRegenPortrait(
            portraitUrl:
                'https://res.cloudinary.com/dvxiniqew/image/upload/regen_newgen_faces/script_skin_hair/North_european/Blonde/north-european-blonde-1.png',
            seed: 'regen-test',
            position: 'CM',
            nationalityCode: 'ENG',
          ),
        ),
      ),
    );

    expect(find.byType(Image), findsOneWidget);
    expect(find.text('PORTRAIT PENDING'), findsNothing);
  });

  testWidgets('does not trust an unrelated portrait URL', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: GtexRegenPortrait(
            portraitUrl: 'https://example.com/player.png',
            seed: 'regen-test',
            position: 'CM',
            nationalityCode: 'ENG',
          ),
        ),
      ),
    );

    expect(find.byType(Image), findsNothing);
    expect(find.text('PORTRAIT PENDING'), findsOneWidget);
  });
}
