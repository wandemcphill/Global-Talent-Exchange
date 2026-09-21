import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/navigation/routing/gte_navigation_route.dart';

void main() {
  group('Market & Ownership Routing & Parsing Tests', () {
    test('parses /market into canonical GteNavigationRoute.market()', () {
      final route = GteNavigationRoute.parse('/market');
      expect(route.primaryDestination, GtePrimaryDestination.market);
      expect(route.marketDeskMode, GtexMarketDeskMode.market);
      expect(route.path, '/app/market');
    });

    test('parses /market?mode=ownership into GteNavigationRoute.market(mode: ownership)', () {
      final route = GteNavigationRoute.parse('/market?mode=ownership');
      expect(route.primaryDestination, GtePrimaryDestination.market);
      expect(route.marketDeskMode, GtexMarketDeskMode.ownership);
      expect(route.path, '/app/market?mode=ownership');
    });

    test('parses /market?tab=holdings into GteNavigationRoute.market(mode: ownership)', () {
      final route = GteNavigationRoute.parse('/market?tab=holdings');
      expect(route.primaryDestination, GtePrimaryDestination.market);
      expect(route.marketDeskMode, GtexMarketDeskMode.ownership);
    });

    test('parses legacy aliases /player-market, /player-cards, /football/transfer-center', () {
      expect(GteNavigationRoute.parse('/player-market').primaryDestination, GtePrimaryDestination.market);
      expect(GteNavigationRoute.parse('/player-cards').primaryDestination, GtePrimaryDestination.market);
      expect(GteNavigationRoute.parse('/football/transfer-center').primaryDestination, GtePrimaryDestination.market);
    });
  });
}
