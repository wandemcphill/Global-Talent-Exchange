import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/regen_redesign/data/gtex_regen_repository.dart';
import 'package:gte_frontend/features/regen_redesign/presentation/gtex_admin_create_son_screen_v2.dart';

void main() {
  testWidgets('admin Create-a-Son queue loads live fixture orders', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1600, 1200);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: GtexAdminCreateSonScreenV2(allowFixtureData: true),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Admin Create-a-Son'), findsOneWidget);
    expect(find.text('Adebayo Jr'), findsWidgets);
    expect(find.text('Pay with wallet'), findsOneWidget);
    expect(find.text('Generate after payment'), findsOneWidget);
  });

  test('demo repository exposes creation-order actions', () async {
    const DemoGtexRegenRepository repository = DemoGtexRegenRepository();
    final orders = await repository.listCreationOrders();
    expect(orders, isNotEmpty);
    final paid = await repository.payCreationOrder(orders.first.id);
    expect(paid.status, 'paid');
    final generated = await repository.generateCreationOrder(orders.first.id);
    expect(generated.status, 'generated');
    expect(generated.generatedPlayer, isNotNull);
  });
}
