import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/player_detail/gtex_fm_player_profile_screen.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';

/// Phase 2A consolidated the orphaned exchange detail screen into the
/// canonical player detail. These cover the harvested behaviour so it cannot
/// silently regress back to being unreachable.
void main() {
  Future<GteExchangeController> signedInController(WidgetTester tester) async {
    late GteExchangeController controller;
    await tester.runAsync(() async {
      controller = GteExchangeController(api: GteExchangeApiClient.fixture());
      await controller.bootstrap();
      await controller.signIn(
        email: 'fixture.trader@gte.local',
        password: 'DemoPass123', // pragma: allowlist secret
      );
    });
    return controller;
  }

  Future<void> settle(WidgetTester tester) async {
    for (int i = 0; i < 20; i++) {
      await tester.pump(const Duration(milliseconds: 120));
    }
  }

  testWidgets('canonical player detail renders live market depth', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(420, 2000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    final GteExchangeController controller = await signedInController(tester);
    final String playerId = controller.players.first.playerId;

    await tester.pumpWidget(
      MaterialApp(
        home: GtexFmPlayerProfileScreen(
          playerId: playerId,
          baseUrl: 'http://fixture.local',
          backendMode: GteBackendMode.fixture,
          apiClient: GteExchangeApiClient.fixture(),
          controller: controller,
        ),
      ),
    );
    await settle(tester);

    final GteOrderBook? book = controller.selectedPlayer?.orderBook;
    expect(book, isNotNull);

    if (book!.bids.isEmpty && book.asks.isEmpty) {
      // An empty book must not be drawn as if it were depth.
      expect(find.text('ORDER BOOK'), findsNothing);
    } else {
      expect(find.text('ORDER BOOK'), findsOneWidget);
      expect(find.text('BIDS'), findsOneWidget);
      expect(find.text('ASKS'), findsOneWidget);
    }
  });

  testWidgets('order detail and trade action stay on one screen', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(420, 2000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    final GteExchangeController controller = await signedInController(tester);
    final String playerId = controller.players.first.playerId;

    await tester.pumpWidget(
      MaterialApp(
        home: GtexFmPlayerProfileScreen(
          playerId: playerId,
          baseUrl: 'http://fixture.local',
          backendMode: GteBackendMode.fixture,
          apiClient: GteExchangeApiClient.fixture(),
          controller: controller,
        ),
      ),
    );
    await settle(tester);

    // The single canonical player detail carries both the profile and the
    // real trading entry point.
    expect(find.text('ATTRIBUTES'), findsOneWidget);
    expect(find.text('ASSET & MARKET INTELLIGENCE'), findsOneWidget);
    expect(find.text('Trade player'), findsOneWidget);
  });

  test('cancellable orders are the ones the API marks cancellable', () {
    final GteOrderRecord working = GteOrderRecord.fromJson(<String, Object?>{
      'id': 'ord-1',
      'player_id': 'plr-1',
      'side': 'buy',
      'status': 'open',
      'quantity': '2.0000',
      'filled_quantity': '0.0000',
      'reserved_amount': '20.0000',
    });
    expect(working.canCancel, isTrue);

    final GteOrderRecord filled = GteOrderRecord.fromJson(<String, Object?>{
      'id': 'ord-2',
      'player_id': 'plr-1',
      'side': 'buy',
      'status': 'filled',
      'quantity': '2.0000',
      'filled_quantity': '2.0000',
      'reserved_amount': '0.0000',
    });
    expect(filled.canCancel, isFalse);
  });
}
