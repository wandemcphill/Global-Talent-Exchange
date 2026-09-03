import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/domain/ownership/gtex_ownership_models.dart';

GtePortfolioHolding _holding({
  String id = 'plr_1',
  double qty = 2,
  double avg = 10,
  double price = 12,
  double value = 24,
  double pl = 4,
  double plPct = 20,
  String? name = 'Ada Obi',
  String? club = 'Enyimba FC',
}) {
  return GtePortfolioHolding.fromJson(<String, Object?>{
    'player_id': id,
    'player_name': name,
    'club_name': club,
    'quantity': qty.toString(),
    'average_cost': avg.toString(),
    'current_price': price.toString(),
    'market_value': value.toString(),
    'unrealized_pl': pl.toString(),
    'unrealized_pl_percent': plPct.toString(),
  });
}

void main() {
  test('stake carries cost basis and profit direction', () {
    final GtexOwnershipStake stake = GtexOwnershipStake.fromHolding(_holding());
    expect(stake.costBasis, 20);
    expect(stake.isInProfit, isTrue);
    expect(stake.unrealizedPlPercent, 20);
    expect(stake.ownershipLabel, 'You own 2 shares');
  });

  test('return percent is null, never zero, when there is no cost basis', () {
    final GtexOwnershipStake stake = GtexOwnershipStake.fromHolding(
      _holding(qty: 1, avg: 0, price: 0, value: 0, pl: 0, plPct: 0),
    );
    expect(stake.unrealizedPlPercent, isNull);
    expect(stake.currentPrice, isNull);
  });

  test('fractional quantity renders without trailing zeros', () {
    final GtexOwnershipStake stake = GtexOwnershipStake.fromHolding(
      _holding(qty: 2.5),
    );
    expect(stake.ownershipLabel, 'You own 2.5 shares');
  });

  test('singular share label', () {
    final GtexOwnershipStake stake = GtexOwnershipStake.fromHolding(
      _holding(qty: 1),
    );
    expect(stake.ownershipLabel, 'You own 1 share');
  });

  test('book is a lookup keyed by player id', () {
    final GtePortfolioView view = GtePortfolioView(
      holdings: <GtePortfolioHolding>[
        _holding(id: 'a'),
        _holding(id: 'b', name: null, club: null),
      ],
    );
    final GtexOwnershipBook book = GtexOwnershipBook.fromPortfolio(view);
    expect(book.length, 2);
    expect(book.owns('a'), isTrue);
    expect(book.owns('missing'), isFalse);
    expect(book.stakeFor('b')!.playerName, isNull);
  });

  test('null portfolio yields an empty book', () {
    expect(GtexOwnershipBook.fromPortfolio(null).isEmpty, isTrue);
  });
}
