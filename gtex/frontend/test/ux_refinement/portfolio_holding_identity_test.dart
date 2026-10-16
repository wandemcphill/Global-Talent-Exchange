import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_models.dart';

/// Portfolio holdings used to render the raw player id, so the one question
/// the portfolio exists to answer -- "what do I own?" -- was unanswerable.
void main() {
  test('holding parses the identity the portfolio API now returns', () {
    final GtePortfolioHolding holding = GtePortfolioHolding.fromJson(
      <String, Object?>{
        'player_id': 'plr_8fa2c41b',
        'player_name': 'Emmanuel Adebayo-Oluwaseun',
        'club_name': 'Enyimba FC',
        'quantity': '2.0000',
        'average_cost': '10.0000',
        'current_price': '12.0000',
        'market_value': '24.0000',
        'unrealized_pl': '4.0000',
        'unrealized_pl_percent': '20.0000',
      },
    );

    expect(holding.playerName, 'Emmanuel Adebayo-Oluwaseun');
    expect(holding.clubName, 'Enyimba FC');
    expect(holding.displayName, 'Emmanuel Adebayo-Oluwaseun');
  });

  test('display name falls back to the id when identity is absent', () {
    final GtePortfolioHolding holding = GtePortfolioHolding.fromJson(
      <String, Object?>{
        'player_id': 'plr_8fa2c41b',
        'quantity': '1.0000',
        'average_cost': '10.0000',
        'current_price': '10.0000',
        'market_value': '10.0000',
        'unrealized_pl': '0.0000',
        'unrealized_pl_percent': '0.0000',
      },
    );

    expect(holding.playerName, isNull);
    expect(holding.displayName, 'plr_8fa2c41b');
  });

  test('blank identity is treated as absent', () {
    final GtePortfolioHolding holding = GtePortfolioHolding.fromJson(
      <String, Object?>{
        'player_id': 'plr_1',
        'player_name': '   ',
        'quantity': '1.0000',
        'average_cost': '1.0000',
        'current_price': '1.0000',
        'market_value': '1.0000',
        'unrealized_pl': '0.0000',
        'unrealized_pl_percent': '0.0000',
      },
    );

    expect(holding.displayName, 'plr_1');
  });
}
