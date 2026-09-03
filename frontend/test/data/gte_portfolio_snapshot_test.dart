import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_models.dart';

/// `GET /api/portfolio/snapshot` — positions plus the cash posture behind them.
void main() {
  test('parses the snapshot envelope', () {
    final GtePortfolioSnapshot snapshot = GtePortfolioSnapshot.fromJson(
      <String, Object?>{
        'user_id': 'user-123',
        'currency': 'coin',
        'available_balance': '80.0000',
        'reserved_balance': '20.0000',
        'total_balance': '100.0000',
        'holdings': <Object?>[
          <String, Object?>{
            'player_id': 'plr_1',
            'quantity': '2.0000',
            'average_cost': '10.0000',
            'current_price': '12.0000',
            'market_value': '24.0000',
            'unrealized_pl': '4.0000',
            'unrealized_pl_percent': '20.0000',
          },
        ],
      },
    );

    expect(snapshot.userId, 'user-123');
    expect(snapshot.availableBalance, 80);
    expect(snapshot.reservedBalance, 20);
    expect(snapshot.totalBalance, 100);
    expect(snapshot.holdings, hasLength(1));
    expect(snapshot.holdings.single.playerId, 'plr_1');
  });

  test('tolerates a missing holdings list', () {
    final GtePortfolioSnapshot snapshot = GtePortfolioSnapshot.fromJson(
      <String, Object?>{
        'user_id': 'user-9',
        'available_balance': '0',
        'reserved_balance': '0',
        'total_balance': '0',
      },
    );
    expect(snapshot.holdings, isEmpty);
    expect(snapshot.currency, 'coin');
  });
}
