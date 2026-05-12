import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/screens/profile/gtex_profile_screen_v2.dart';
import 'package:gte_frontend/screens/profile/gtex_settings_screen_v2.dart';
import 'package:gte_frontend/screens/system/gtex_system_states_gallery_v2.dart';

void main() {
  testWidgets('profile screen renders GTEX profile identity', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: GtexProfileScreenV2()));
    await tester.pumpAndSettle();
    expect(find.text('GTEX PROFILE'), findsOneWidget);
    expect(find.text('Account command profile'), findsOneWidget);
  });

  testWidgets('settings screen renders settings sections', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: GtexSettingsScreenV2()));
    expect(find.text('SETTINGS'), findsOneWidget);
    expect(find.text('Account'), findsWidgets);
  });

  testWidgets('system states gallery renders reusable states', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: GtexSystemStatesGalleryV2()),
    );
    expect(find.text('GTEX system states'), findsOneWidget);
    expect(find.text('Nothing here yet'), findsOneWidget);
  });
}
