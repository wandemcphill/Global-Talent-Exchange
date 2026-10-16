import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/controllers/gtex_watchlist_controller.dart';
import 'package:gte_frontend/data/player_card_watchlist_api.dart';

void main() {
  group('PlayerCardWatchlistApi & GtexWatchlistController', () {
    late FixturePlayerCardWatchlistApi api;
    late GtexWatchlistController controller;

    setUp(() {
      api = FixturePlayerCardWatchlistApi();
      controller = GtexWatchlistController(api: api);
    });

    test('initial state is empty', () {
      expect(controller.entries, isEmpty);
      expect(controller.watchlistedPlayerIds, isEmpty);
      expect(controller.isLoading, isFalse);
      expect(controller.isMutating, isFalse);
      expect(controller.error, null);
    });

    test('add to watchlist creates entry and updates state', () async {
      final bool added = await controller.addToWatchlist('player-101', notes: 'Top target');
      expect(added, isTrue);
      expect(controller.isWatchlisted('player-101'), isTrue);
      expect(controller.watchlistedPlayerIds, contains('player-101'));
      expect(controller.entries.length, 1);
      expect(controller.entries.first.playerId, 'player-101');
      expect(controller.entries.first.notes, 'Top target');
    });

    test('remove from watchlist removes entry', () async {
      await controller.addToWatchlist('player-101');
      expect(controller.isWatchlisted('player-101'), isTrue);

      final bool removed = await controller.removeFromWatchlist('player-101');
      expect(removed, isTrue);
      expect(controller.isWatchlisted('player-101'), isFalse);
      expect(controller.watchlistedPlayerIds, isEmpty);
      expect(controller.entries, isEmpty);
    });

    test('toggleWatchlist adds when unwatchlisted and removes when watchlisted', () async {
      await controller.toggleWatchlist('player-202');
      expect(controller.isWatchlisted('player-202'), isTrue);

      await controller.toggleWatchlist('player-202');
      expect(controller.isWatchlisted('player-202'), isFalse);
    });

    test('load fetches watchlist entries from API', () async {
      await api.addWatchlist(playerId: 'player-303', notes: 'Seeded');
      await controller.load(force: true);

      expect(controller.isWatchlisted('player-303'), isTrue);
      expect(controller.entries.length, 1);
      expect(controller.syncedAt, isNotNull);
    });
  });
}
