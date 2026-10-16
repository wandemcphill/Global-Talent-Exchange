import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/screens/system/gtex_system_states_gallery_v2.dart';

void main() {
  testWidgets('system states gallery renders reusable states', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: GtexSystemStatesGalleryV2()),
    );
    expect(find.text('GTEX system states'), findsOneWidget);
    expect(find.text('Nothing here yet'), findsOneWidget);
  });
}
