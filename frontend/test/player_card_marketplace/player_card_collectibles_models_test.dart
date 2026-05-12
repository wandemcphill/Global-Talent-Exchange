import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/player_card_marketplace/data/player_card_marketplace_models.dart';

void main() {
  test('player card collectible pack and opening parse live api payloads', () {
    final PlayerCardPack pack = PlayerCardPack.fromJson(const <String, Object?>{
      'pack_key': 'starter-draft',
      'title': 'Starter Draft Pack',
      'description': 'Live supply pack',
      'price_credits': 0,
      'cards_per_pack': 3,
      'drop_odds_json': <String, Object?>{'gold': 8, 'elite': 2},
      'is_active': true,
    });
    final PlayerCardPackOpening opening = PlayerCardPackOpening.fromJson(
      const <String, Object?>{
        'opening_id': 'opening-1',
        'pack_key': 'starter-draft',
        'status': 'opened',
        'price_credits': 0,
        'opened_cards': <Object?>[
          <String, Object?>{
            'player_card_id': 'card-1',
            'display_name': 'Ayo Striker Gold',
            'tier_name': 'Gold',
          },
        ],
      },
    );

    expect(pack.packKey, 'starter-draft');
    expect(pack.cardsPerPack, 3);
    expect(pack.dropOdds['elite'], 2);
    expect(opening.openedCards.single['player_card_id'], 'card-1');
  });

  test('player card marketplace models expose GSI quality signals', () {
    final PlayerCardMarketplaceListing listing =
        PlayerCardMarketplaceListing.fromJson(const <String, Object?>{
          'listing_id': 'listing-1',
          'player_card_id': 'card-1',
          'player_id': 'player-1',
          'player_name': 'Ayo Striker',
          'tier_code': 'gold',
          'tier_name': 'Gold',
          'rarity_rank': 3,
          'edition_code': 'season-1',
          'status': 'open',
          'availability': 'available',
          'asset_origin': 'real_player',
          'global_scouting_index': 88.4,
        });
    final PlayerCardHolding holding = PlayerCardHolding.fromJson(
      const <String, Object?>{
        'holding_id': 'holding-1',
        'player_card_id': 'card-1',
        'player_id': 'player-1',
        'player_name': 'Ayo Striker',
        'tier_code': 'gold',
        'tier_name': 'Gold',
        'edition_code': 'season-1',
        'quantity_total': 1,
        'quantity_reserved': 0,
        'quantity_available': 1,
        'player_snapshot': <String, Object?>{'gsi': 91},
      },
    );

    expect(listing.gsiScore, 88);
    expect(listing.gsiTierLabel, 'High-grade GSI');
    expect(holding.gsiScore, 91);
    expect(holding.gsiTierLabel, 'Elite GSI');
  });
}
