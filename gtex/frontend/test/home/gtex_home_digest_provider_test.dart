import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/domain/ownership/gtex_ownership_models.dart';
import 'package:gte_frontend/domain/value/gtex_value_models.dart';
import 'package:gte_frontend/features/club_redesign/models/gtex_club_ownership_models.dart';
import 'package:gte_frontend/features/home/data/gtex_home_digest_provider.dart';
import 'package:gte_frontend/features/home/models/gtex_home_digest_models.dart';

const GtexOwnershipStake _stake = GtexOwnershipStake(
  playerId: 'p1',
  quantity: 2,
  averageCost: 10,
  marketValue: 24,
  unrealizedPl: 4,
  unrealizedPlPercent: 20,
  currentPrice: 12,
  playerName: 'Ada Obi',
  clubName: 'Enyimba FC',
);

const GtexHomePlayerHighlight _playerHighlight = GtexHomePlayerHighlight(
  playerId: 'p1',
  playerName: 'Ada Obi',
  quantityLabel: '2',
  priceLabel: 'GTC 12',
);

const GtexHomeClubHighlight _clubHighlight = GtexHomeClubHighlight(
  clubId: 'c1',
  clubName: 'Lagos Eclipse FC',
  sharesLabel: '40 shares',
  sharePriceLabel: 'GTC 1.32/share',
  plLabel: '+GTC 12.8',
  isInProfit: true,
  hasPerformanceHistory: true,
);

const GtexHomeRegenHighlight _regenHighlight = GtexHomeRegenHighlight(
  playerId: 'p1',
  playerName: 'Ada Obi',
  rank: 7,
  category: 'overall',
);

const GtexHomeMoverHighlight _moverHighlight = GtexHomeMoverHighlight(
  playerId: 'p1',
  playerName: 'Ada Obi',
  dayChangePercent: 3.2,
  isOwned: true,
);

void main() {
  group('resolveGtexHomeUserState', () {
    test('nothing owned is a new user', () {
      expect(
        resolveGtexHomeUserState(
          ownedPlayers: const <GtexHomePlayerHighlight>[],
          clubs: const <GtexHomeClubHighlight>[],
          regens: const <GtexHomeRegenHighlight>[],
        ),
        GtexHomeUserState.newUser,
      );
    });

    test('players only is a player owner', () {
      expect(
        resolveGtexHomeUserState(
          ownedPlayers: const <GtexHomePlayerHighlight>[_playerHighlight],
          clubs: const <GtexHomeClubHighlight>[],
          regens: const <GtexHomeRegenHighlight>[],
        ),
        GtexHomeUserState.playerOwner,
      );
    });

    test('clubs only is a club owner', () {
      expect(
        resolveGtexHomeUserState(
          ownedPlayers: const <GtexHomePlayerHighlight>[],
          clubs: const <GtexHomeClubHighlight>[_clubHighlight],
          regens: const <GtexHomeRegenHighlight>[],
        ),
        GtexHomeUserState.clubOwner,
      );
    });

    test('regens only is a regen investor', () {
      expect(
        resolveGtexHomeUserState(
          ownedPlayers: const <GtexHomePlayerHighlight>[],
          clubs: const <GtexHomeClubHighlight>[],
          regens: const <GtexHomeRegenHighlight>[_regenHighlight],
        ),
        GtexHomeUserState.regenInvestor,
      );
    });

    test('two or more asset classes is multi-asset', () {
      expect(
        resolveGtexHomeUserState(
          ownedPlayers: const <GtexHomePlayerHighlight>[_playerHighlight],
          clubs: const <GtexHomeClubHighlight>[_clubHighlight],
          regens: const <GtexHomeRegenHighlight>[],
        ),
        GtexHomeUserState.multiAsset,
      );
    });
  });

  group('buildGtexHomeHeadline', () {
    test('new user gets discovery copy, never a fabricated activity count', () {
      expect(
        buildGtexHomeHeadline(
          userState: GtexHomeUserState.newUser,
          yourMoversToday: const <GtexHomeMoverHighlight>[],
        ),
        'Explore GTEX and start building your football world.',
      );
    });

    test('an owner with no daily movers is told it is quiet, not zero', () {
      expect(
        buildGtexHomeHeadline(
          userState: GtexHomeUserState.playerOwner,
          yourMoversToday: const <GtexHomeMoverHighlight>[],
        ),
        'Your GTEX world is quiet today.',
      );
    });

    test('singular player movement is grammatically singular', () {
      expect(
        buildGtexHomeHeadline(
          userState: GtexHomeUserState.playerOwner,
          yourMoversToday: const <GtexHomeMoverHighlight>[_moverHighlight],
        ),
        '1 player moved today.',
      );
    });

    test('plural player movement is grammatically plural', () {
      expect(
        buildGtexHomeHeadline(
          userState: GtexHomeUserState.playerOwner,
          yourMoversToday: const <GtexHomeMoverHighlight>[
            _moverHighlight,
            _moverHighlight,
          ],
        ),
        '2 players moved today.',
      );
    });
  });

  group('buildGtexHomeAttentionItems', () {
    test('nothing to act on yields no items - never a dead placeholder action', () {
      final List<GtexHomeAttentionItem> items = buildGtexHomeAttentionItems(
        yourMoversToday: const <GtexHomeMoverHighlight>[],
        ownedPlayers: const <GtexHomePlayerHighlight>[],
        clubs: const <GtexHomeClubHighlight>[],
        regens: const <GtexHomeRegenHighlight>[],
        opportunityMovers: const <GtexHomeMoverHighlight>[],
      );
      expect(items, isEmpty);
    });

    test('every real signal produces exactly one routable action', () {
      final List<GtexHomeAttentionItem> items = buildGtexHomeAttentionItems(
        yourMoversToday: const <GtexHomeMoverHighlight>[_moverHighlight],
        ownedPlayers: const <GtexHomePlayerHighlight>[
          GtexHomePlayerHighlight(
            playerId: 'p1',
            playerName: 'Ada Obi',
            quantityLabel: '2',
            priceLabel: 'GTC 12',
            formTrendLabel: 'Form +0.4%',
          ),
        ],
        clubs: const <GtexHomeClubHighlight>[_clubHighlight],
        regens: const <GtexHomeRegenHighlight>[_regenHighlight],
        opportunityMovers: const <GtexHomeMoverHighlight>[_moverHighlight],
      );
      final Set<String> ids = items.map((GtexHomeAttentionItem i) => i.id).toSet();
      expect(ids, <String>{
        'movers-today',
        'matchday-form',
        'club-shares',
        'regen-scout',
        'market-opportunities',
      });
      for (final GtexHomeAttentionItem item in items) {
        expect(item.routeLocation, isNotEmpty);
      }
    });
  });

  group('gtexHomePlayerHighlightFromStake', () {
    test('no form data leaves the matchday fields absent, never a fake trend', () {
      final GtexHomePlayerHighlight highlight = gtexHomePlayerHighlightFromStake(
        _stake,
        null,
      );
      expect(highlight.playerId, 'p1');
      expect(highlight.playerName, 'Ada Obi');
      expect(highlight.formTrendLabel, isNull);
      expect(highlight.matchdayNote, isNull);
      expect(highlight.unrealizedPlPercent, 20);
    });

    test('form that exists but is not applied never claims a value link', () {
      const GtexPlayerForm form = GtexPlayerForm(
        playerId: 'p1',
        hasSample: true,
        matchesCounted: 4,
        signal: GtexMatchdaySignal(
          applied: false,
          adjustmentPct: 0,
          reasonCode: 'below_minimum_matches',
        ),
      );
      final GtexHomePlayerHighlight highlight = gtexHomePlayerHighlightFromStake(
        _stake,
        form,
      );
      expect(
        highlight.formTrendLabel,
        isNull,
        reason: 'signal.applied is false — Home must not claim causality',
      );
      expect(highlight.matchdayNote, '4 matches counted this window');
    });

    test('an applied signal produces a signed form trend label', () {
      const GtexPlayerForm form = GtexPlayerForm(
        playerId: 'p1',
        hasSample: true,
        matchesCounted: 5,
        signal: GtexMatchdaySignal(
          applied: true,
          adjustmentPct: 1.8,
          reasonCode: 'strong_recent_form',
        ),
      );
      final GtexHomePlayerHighlight highlight = gtexHomePlayerHighlightFromStake(
        _stake,
        form,
      );
      expect(highlight.formTrendLabel, 'Form +1.8%');
    });

    test('an unknown current price never renders a fake number', () {
      const GtexOwnershipStake stakeWithNoMark = GtexOwnershipStake(
        playerId: 'p2',
        quantity: 1,
        averageCost: 0,
        marketValue: 0,
        unrealizedPl: 0,
      );
      final GtexHomePlayerHighlight highlight = gtexHomePlayerHighlightFromStake(
        stakeWithNoMark,
        null,
      );
      expect(highlight.priceLabel, 'Price unknown');
    });
  });

  group('gtexHomeClubHighlightFromHolding', () {
    test('maps the club-share holding fields verbatim', () {
      const GtexClubShareHolding holding = GtexClubShareHolding(
        clubId: 'c1',
        clubName: 'Lagos Eclipse FC',
        sharesOwned: 40,
        averagePriceCoin: 1,
        sharePriceCoin: 1.32,
        marketValueCoin: 52.8,
        costBasisCoin: 40,
        unrealizedPlCoin: 12.8,
        performanceScore: 0.4,
      );
      final GtexHomeClubHighlight highlight = gtexHomeClubHighlightFromHolding(
        holding,
      );
      expect(highlight.clubName, 'Lagos Eclipse FC');
      expect(highlight.sharesLabel, '40 shares');
      expect(highlight.isInProfit, isTrue);
      expect(highlight.plLabel, startsWith('+'));
      expect(highlight.hasPerformanceHistory, isTrue);
    });

    test('a club with no settled matches never claims performance history', () {
      const GtexClubShareHolding holding = GtexClubShareHolding(
        clubId: 'c2',
        clubName: 'Fresh Start FC',
        sharesOwned: 10,
        averagePriceCoin: 1,
        sharePriceCoin: 1,
        marketValueCoin: 10,
        costBasisCoin: 10,
        unrealizedPlCoin: 0,
      );
      final GtexHomeClubHighlight highlight = gtexHomeClubHighlightFromHolding(
        holding,
      );
      expect(highlight.hasPerformanceHistory, isFalse);
      expect(highlight.isInProfit, isFalse);
    });
  });

  group('gtexHomeRecentActivityFrom', () {
    GteOrderRecord order({
      required String id,
      required String playerId,
      required GteOrderSide side,
      required GteOrderStatus status,
      DateTime? executedAt,
    }) {
      return GteOrderRecord(
        id: id,
        playerId: playerId,
        side: side,
        status: status,
        quantity: 1,
        remainingQuantity: 0,
        maxPrice: 10,
        reservedAmount: 10,
        executionSummary: GteOrderExecutionSummary(
          executionCount: 1,
          totalNotional: 10,
          averagePrice: 10,
          lastExecutedAt: executedAt,
        ),
      );
    }

    test('only settled orders become activity - open/cancelled are excluded', () {
      final GteOrderListView orders = GteOrderListView(
        items: <GteOrderRecord>[
          order(
            id: 'o1',
            playerId: 'p1',
            side: GteOrderSide.buy,
            status: GteOrderStatus.filled,
            executedAt: DateTime.utc(2026, 9, 1),
          ),
          order(
            id: 'o2',
            playerId: 'p2',
            side: GteOrderSide.sell,
            status: GteOrderStatus.open,
          ),
          order(
            id: 'o3',
            playerId: 'p3',
            side: GteOrderSide.buy,
            status: GteOrderStatus.cancelled,
          ),
        ],
        limit: 20,
        offset: 0,
        total: 3,
      );
      final List<GtexHomeActivityItem> items = gtexHomeRecentActivityFrom(
        orders,
        GtexOwnershipBook.empty(),
      );
      expect(items, hasLength(1));
      expect(items.single.id, 'o1');
      expect(items.single.label, startsWith('Bought'));
    });

    test('sorts most recently executed first', () {
      final GteOrderListView orders = GteOrderListView(
        items: <GteOrderRecord>[
          order(
            id: 'older',
            playerId: 'p1',
            side: GteOrderSide.buy,
            status: GteOrderStatus.filled,
            executedAt: DateTime.utc(2026, 8, 1),
          ),
          order(
            id: 'newer',
            playerId: 'p2',
            side: GteOrderSide.sell,
            status: GteOrderStatus.filled,
            executedAt: DateTime.utc(2026, 9, 1),
          ),
        ],
        limit: 20,
        offset: 0,
        total: 2,
      );
      final List<GtexHomeActivityItem> items = gtexHomeRecentActivityFrom(
        orders,
        GtexOwnershipBook.empty(),
      );
      expect(items.map((GtexHomeActivityItem i) => i.id), <String>['newer', 'older']);
    });

    test('a known ownership name replaces a bare player id', () {
      final GteOrderListView orders = GteOrderListView(
        items: <GteOrderRecord>[
          order(
            id: 'o1',
            playerId: 'p1',
            side: GteOrderSide.buy,
            status: GteOrderStatus.filled,
            executedAt: DateTime.utc(2026, 9, 1),
          ),
        ],
        limit: 20,
        offset: 0,
        total: 1,
      );
      final GtexOwnershipBook book = GtexOwnershipBook(<String, GtexOwnershipStake>{
        'p1': _stake,
      });
      final List<GtexHomeActivityItem> items = gtexHomeRecentActivityFrom(
        orders,
        book,
      );
      expect(items.single.label, 'Bought Ada Obi');
    });
  });
}
