import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/home/models/gtex_home_digest_models.dart';

void main() {
  group('GtexHomePlayerHighlight', () {
    test('movement label states unknown rather than a fake zero', () {
      const GtexHomePlayerHighlight highlight = GtexHomePlayerHighlight(
        playerId: 'p1',
        playerName: 'Ada Obi',
        quantityLabel: '2',
        priceLabel: 'GTC 40',
      );
      expect(highlight.unrealizedPlPercent, isNull);
      expect(highlight.movementLabel, 'Unknown movement');
      expect(highlight.hasMovement, isFalse);
    });

    test('movement label signs a positive percent', () {
      const GtexHomePlayerHighlight highlight = GtexHomePlayerHighlight(
        playerId: 'p1',
        playerName: 'Ada Obi',
        quantityLabel: '2',
        priceLabel: 'GTC 40',
        unrealizedPlPercent: 3.75,
      );
      expect(highlight.movementLabel, '+3.8%');
      expect(highlight.hasMovement, isTrue);
    });

    test('movement label signs a negative percent without a double minus', () {
      const GtexHomePlayerHighlight highlight = GtexHomePlayerHighlight(
        playerId: 'p1',
        playerName: 'Ada Obi',
        quantityLabel: '2',
        priceLabel: 'GTC 40',
        unrealizedPlPercent: -1.2,
      );
      expect(highlight.movementLabel, '-1.2%');
    });
  });

  group('GtexHomeMoverHighlight', () {
    test('isRising is exactly the sign of the real day change', () {
      const GtexHomeMoverHighlight riser = GtexHomeMoverHighlight(
        playerId: 'p1',
        playerName: 'Ada Obi',
        dayChangePercent: 2.5,
        isOwned: true,
      );
      const GtexHomeMoverHighlight faller = GtexHomeMoverHighlight(
        playerId: 'p2',
        playerName: 'Bola Ade',
        dayChangePercent: -1.1,
        isOwned: false,
      );
      expect(riser.isRising, isTrue);
      expect(riser.movementLabel, '+2.5%');
      expect(faller.isRising, isFalse);
      expect(faller.movementLabel, '-1.1%');
    });
  });

  group('GtexHomeDigest', () {
    test('empty() is the honest guest state, not a fabricated portfolio', () {
      final GtexHomeDigest digest = GtexHomeDigest.empty();
      expect(digest.hasAnyOwnership, isFalse);
      expect(digest.ownedPlayers, isEmpty);
      expect(digest.clubs, isEmpty);
      expect(digest.regens, isEmpty);
      expect(digest.attentionItems, isEmpty);
      expect(digest.recentActivity, isEmpty);
    });

    test('isQuiet is true only when there is ownership but no daily movers', () {
      const GtexHomeDigest withOwnershipNoMovers = GtexHomeDigest(
        userState: GtexHomeUserState.playerOwner,
        headline: 'Your GTEX world is quiet today.',
        ownedPlayers: <GtexHomePlayerHighlight>[
          GtexHomePlayerHighlight(
            playerId: 'p1',
            playerName: 'Ada Obi',
            quantityLabel: '2',
            priceLabel: 'GTC 40',
          ),
        ],
        yourMoversToday: <GtexHomeMoverHighlight>[],
        opportunityMovers: <GtexHomeMoverHighlight>[],
        clubs: <GtexHomeClubHighlight>[],
        regens: <GtexHomeRegenHighlight>[],
        attentionItems: <GtexHomeAttentionItem>[],
        recentActivity: <GtexHomeActivityItem>[],
        warnings: <String>[],
      );
      expect(withOwnershipNoMovers.isQuiet, isTrue);

      final GtexHomeDigest newUser = GtexHomeDigest.empty();
      expect(newUser.isQuiet, isFalse, reason: 'a new user is not "quiet" — they own nothing yet');
    });
  });
}
