import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/club_sale_market/data/club_sale_market_models.dart';
import 'package:gte_frontend/features/club_sale_market/data/club_sale_market_repository.dart';
import 'package:gte_frontend/features/club_sale_market/presentation/club_sale_market_controller.dart';
import 'package:gte_frontend/features/club_sale_market/presentation/club_sale_market_screen.dart';

void main() {
  testWidgets(
      'club sale market renders an Open CTA for public listings when optional fields are missing',
      (WidgetTester tester) async {
    final ClubSaleListingCollection collection = ClubSaleListingCollection.fromJson(
      <String, Object?>{
        'total': 1,
        'listings': <Map<String, Object?>>[
          <String, Object?>{
            'listingId': 'listing-1',
            'clubId': 'ibadan-lions',
            'clubName': 'Ibadan Lions FC',
            'status': 'active',
            'visibility': 'public',
            'currency': 'credits',
            'askingPrice': 1250000,
            'systemValuation': 1200000,
            'createdAt': '2026-03-18T10:00:00Z',
            'updatedAt': '2026-03-19T10:00:00Z',
          },
        ],
      },
    );
    expect(collection.items, hasLength(1));

    final ClubSaleMarketController controller = ClubSaleMarketController(
      repository: _FakeClubSaleMarketRepository(
        collection: collection,
      ),
    );
    await controller.loadPublicListings();

    await tester.pumpWidget(
      MaterialApp(
        home: ClubSaleMarketScreen(
          baseUrl: 'http://127.0.0.1:8000',
          backendMode: GteBackendMode.fixture,
          controller: controller,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(controller.publicListings.items, hasLength(1));
    await tester.dragUntilVisible(
      find.text('Open'),
      find.byType(ListView),
      const Offset(0, -300),
    );
    await tester.pumpAndSettle();
    expect(find.text('Open'), findsOneWidget);
    expect(find.text('No clubs are listed right now'), findsNothing);
  });
}

class _FakeClubSaleMarketRepository implements ClubSaleMarketRepository {
  _FakeClubSaleMarketRepository({
    required this.collection,
  });

  final ClubSaleListingCollection collection;

  @override
  Future<ClubSaleListingCollection> listPublicListings(
    ClubSaleListingsQuery query,
  ) async {
    return collection;
  }

  @override
  dynamic noSuchMethod(Invocation invocation) {
    return super.noSuchMethod(invocation);
  }
}
