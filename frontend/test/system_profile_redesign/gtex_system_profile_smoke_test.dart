import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/system_profile_redesign/models/gtex_profile_models.dart';
import 'package:gte_frontend/features/system_profile_redesign/presentation/gtex_profile_controller.dart';
import 'package:gte_frontend/screens/profile/gtex_profile_screen_v2.dart';
import 'package:gte_frontend/screens/profile/gtex_settings_screen_v2.dart';
import 'package:gte_frontend/screens/system/gtex_system_states_gallery_v2.dart';

void main() {
  testWidgets('profile screen renders GTEX profile identity', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: GtexProfileScreenV2(
          controller: GtexProfileController(loader: _testProfile),
        ),
      ),
    );
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

Future<GtexProfileSummary> _testProfile() async {
  return const GtexProfileSummary(
    userId: 'user-test-001',
    displayName: 'GTEX Test Owner',
    email: 'owner@gtex.test',
    roleLabel: 'Club Owner',
    countryLabel: 'Nigeria',
    clubName: 'GTEX Test FC',
    kycStatus: 'Pending Review',
    walletStatus: 'Active',
    unreadNotifications: 8,
    openDisputes: 1,
    securityScore: 82,
    profileCompletion: 76,
  );
}
