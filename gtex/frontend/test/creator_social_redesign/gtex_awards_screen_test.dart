import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/awards/gtex_awards_screen_v2.dart';

void main() {
  testWidgets('awards screen renders awards board', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: GtexAwardsScreenV2(backendMode: GteBackendMode.fixture),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('GTEX Awards'), findsOneWidget);
    expect(find.text('No awards board yet'), findsOneWidget);
  });
}
