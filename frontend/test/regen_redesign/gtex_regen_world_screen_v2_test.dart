import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/regen_universe_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/regen_redesign/presentation/gtex_regen_world_screen_v2.dart';
import 'package:gte_frontend/features/regens/regens_screen_v2.dart';

void main() {
  test('national regen API page exposes the full server population metadata', () {
    final NationalRegenSeedPage page = NationalRegenSeedPage.fromJson(
      <String, dynamic>{
        'items': <Object?>[],
        'pagination': <String, Object?>{
          'page': 2,
          'per_page': 48,
          'total': 214,
          'total_pages': 5,
          'has_next': true,
          'has_previous': true,
        },
      },
    );

    expect(page.items, isEmpty);
    expect(page.page, 2);
    expect(page.perPage, 48);
    expect(page.total, 214);
    expect(page.totalPages, 5);
    expect(page.hasNext, isTrue);
  });


  testWidgets('Regen World V2 renders core surfaces', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(home: Scaffold(body: GtexRegenWorldScreenV2.fixture())),
    );
    await tester.pumpAndSettle();

    expect(find.text('Regen World'), findsOneWidget);
    expect(find.text('Create a Son'), findsWidgets);
    expect(find.text('Prospects'), findsOneWidget);
  });

  testWidgets('live regen route fails closed without API base URL', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(body: RegensScreenV2(backendMode: GteBackendMode.live)),
      ),
    );

    expect(find.text('Regen world configuration missing'), findsOneWidget);
    expect(find.text('Regen World'), findsNothing);
  });
}
