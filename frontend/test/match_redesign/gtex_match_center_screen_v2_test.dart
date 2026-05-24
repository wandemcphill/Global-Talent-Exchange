import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/match_redesign/data/gtex_match_demo_repository.dart';
import 'package:gte_frontend/features/match_redesign/presentation/gtex_match_center_screen_v2.dart';

void main() {
  testWidgets('renders the GTEX 2D match center', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: GtexMatchCenterScreenV2(
          matchId: 'test-match',
          repository: GtexMatchDemoRepository(),
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 1000));

    expect(find.text('Match Center'), findsWidgets);
    expect(find.textContaining('Lagos Crown'), findsOneWidget);
    expect(find.text('Timeline'), findsOneWidget);
  });
}
