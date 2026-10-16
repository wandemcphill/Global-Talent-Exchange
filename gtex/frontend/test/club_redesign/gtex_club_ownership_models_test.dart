import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/club_redesign/models/gtex_club_ownership_models.dart';

void main() {
  group('GtexClubShareHolding.fromJson', () {
    test('parses a live-valued club-share position', () {
      final GtexClubShareHolding holding = GtexClubShareHolding.fromJson(
        const <String, dynamic>{
          'club_id': 'club-1',
          'club_name': 'Port Harcourt Dynamos',
          'tokens_owned': 30,
          'avg_price_coin': '1.0000',
          'share_price_coin': '1.3200',
          'market_value_coin': '39.6000',
          'cost_basis_coin': '30.0000',
          'unrealized_pl_coin': '9.6000',
          'unrealized_pl_pct': 32.0,
          'ownership_pct': 3.0,
          'holder_count': 12,
          'circulating_supply': 1000,
          'total_supply': 1000000,
          'reward_tokens_earned': 1,
          'performance_score': '0.4200',
          'win_rate': '0.6000',
          'fan_demand_score': '0.1800',
          'treasury_balance_coin': '640.0000',
          'governance_enabled': true,
        },
      );

      expect(holding.clubName, 'Port Harcourt Dynamos');
      expect(holding.sharesOwned, 30);
      expect(holding.sharePriceCoin, 1.32);
      expect(holding.isInProfit, isTrue);
      expect(holding.ownershipPercent, 3.0);
      expect(holding.hasPerformanceHistory, isTrue);
    });

    test('keeps unknown ratios null rather than zero', () {
      final GtexClubShareHolding holding = GtexClubShareHolding.fromJson(
        const <String, dynamic>{
          'club_id': 'club-2',
          'club_name': 'Kano Comets',
          'tokens_owned': 5,
          'avg_price_coin': '1.0000',
          'share_price_coin': '1.0000',
          'market_value_coin': '5.0000',
          'cost_basis_coin': '5.0000',
          'unrealized_pl_coin': '0.0000',
          // no unrealized_pl_pct, no ownership_pct, no performance fields
          'governance_enabled': false,
        },
      );

      expect(holding.unrealizedPlPercent, isNull);
      expect(holding.ownershipPercent, isNull);
      expect(holding.performanceScore, isNull);
      expect(holding.winRate, isNull);
      expect(holding.isFlat, isTrue);
      expect(holding.hasPerformanceHistory, isFalse);
    });
  });

  test('GtexClubOwnershipPortfolio.empty is an honest empty book', () {
    final GtexClubOwnershipPortfolio portfolio =
        GtexClubOwnershipPortfolio.empty();
    expect(portfolio.isEmpty, isTrue);
    expect(portfolio.clubCount, 0);
    expect(portfolio.totalMarketValueCoin, 0);
  });

  test('GtexClubOwnershipPortfolio.fromJson aggregates holdings', () {
    final GtexClubOwnershipPortfolio portfolio =
        GtexClubOwnershipPortfolio.fromJson(const <String, dynamic>{
      'club_count': 2,
      'total_market_value_coin': '61.6000',
      'total_cost_basis_coin': '50.0000',
      'total_unrealized_pl_coin': '11.6000',
      'holdings': <Map<String, dynamic>>[
        <String, dynamic>{
          'club_id': 'club-1',
          'club_name': 'Port Harcourt Dynamos',
          'tokens_owned': 30,
          'avg_price_coin': '1.0000',
          'share_price_coin': '1.3200',
          'market_value_coin': '39.6000',
          'cost_basis_coin': '30.0000',
          'unrealized_pl_coin': '9.6000',
          'governance_enabled': true,
        },
        <String, dynamic>{
          'club_id': 'club-2',
          'club_name': 'Kano Comets',
          'tokens_owned': 20,
          'avg_price_coin': '1.0000',
          'share_price_coin': '1.1000',
          'market_value_coin': '22.0000',
          'cost_basis_coin': '20.0000',
          'unrealized_pl_coin': '2.0000',
          'governance_enabled': true,
        },
      ],
    });

    expect(portfolio.clubCount, 2);
    expect(portfolio.holdings, hasLength(2));
    expect(portfolio.isInProfit, isTrue);
    expect(portfolio.holdings.first.clubName, 'Port Harcourt Dynamos');
  });
}
