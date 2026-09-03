import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_exchange_models.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/domain/ownership/gtex_ownership_models.dart';
import 'package:gte_frontend/domain/value/gtex_value_models.dart';
import 'package:gte_frontend/features/club_redesign/models/gtex_club_ownership_models.dart';
import 'package:gte_frontend/features/regen_redesign/models/gtex_regen_wire_models.dart';
import 'package:gte_frontend/features/social/data/gtex_community_social_models.dart';
import 'package:gte_frontend/features/social/models/gtex_community_models.dart';

GteMarketMoverItem _mover(
  String id,
  String name,
  double dayChangePercent, {
  double volume = 100,
}) {
  return GteMarketMoverItem(
    playerId: id,
    playerName: name,
    dayChange: dayChangePercent,
    dayChangePercent: dayChangePercent,
    volume24h: volume,
  );
}

GtexOwnershipBook _bookOf(List<String> playerIds) {
  return GtexOwnershipBook.fromPortfolio(
    GtePortfolioView(
      holdings: playerIds
          .map(
            (String id) => GtePortfolioHolding(
              playerId: id,
              quantity: 2,
              averageCost: 10,
              currentPrice: 12,
              marketValue: 24,
              unrealizedPl: 4,
              unrealizedPlPercent: 20,
              playerName: 'Owned $id',
            ),
          )
          .toList(growable: false),
    ),
  );
}

const GtexClubShareHolding _clubHolding = GtexClubShareHolding(
  clubId: 'club-1',
  clubName: 'Lagos Eclipse FC',
  sharesOwned: 40,
  averagePriceCoin: 1,
  sharePriceCoin: 1.32,
  marketValueCoin: 52.8,
  costBasisCoin: 40,
  unrealizedPlCoin: 12.8,
  unrealizedPlPercent: 32,
  holderCount: 18,
  circulatingSupply: 1000,
  totalSupply: 1000000,
  rewardSharesEarned: 0,
  performanceScore: 0.4,
  winRate: 0.6,
  governanceEnabled: true,
);

void main() {
  group('gtexCommunityHolderProof', () {
    test('an unknown count is absent, not zero', () {
      expect(gtexCommunityHolderProof(null, noun: 'owner'), isNull);
    });

    test('a zero count is absent rather than claiming "0 owners"', () {
      expect(gtexCommunityHolderProof(0, noun: 'owner'), isNull);
    });

    test('a real count is stated with correct pluralisation', () {
      expect(gtexCommunityHolderProof(1, noun: 'owner'), '1 owner');
      expect(gtexCommunityHolderProof(18, noun: 'owner'), '18 owners');
    });
  });

  group('buildGtexCommunityWorldSignals', () {
    test('is empty when the market published no movement', () {
      expect(buildGtexCommunityWorldSignals(GteMarketMovers.empty), isEmpty);
    });

    test('deduplicates a player that appears in several mover buckets', () {
      final GteMarketMovers movers = GteMarketMovers(
        topGainers: <GteMarketMoverItem>[_mover('p1', 'Ada Obi', 4.2)],
        trending: <GteMarketMoverItem>[_mover('p1', 'Ada Obi', 4.2)],
        mostTraded: <GteMarketMoverItem>[_mover('p1', 'Ada Obi', 4.2)],
      );
      final List<GtexCommunitySignal> signals =
          buildGtexCommunityWorldSignals(movers);
      expect(signals, hasLength(1));
      expect(signals.single.headline, 'Ada Obi moved +4.2%');
    });

    test('orders by the size of the real move, not by bucket', () {
      final GteMarketMovers movers = GteMarketMovers(
        topGainers: <GteMarketMoverItem>[_mover('p1', 'Small', 1.1)],
        topLosers: <GteMarketMoverItem>[_mover('p2', 'Big', -9.4)],
      );
      final List<GtexCommunitySignal> signals =
          buildGtexCommunityWorldSignals(movers);
      expect(
        signals.map((GtexCommunitySignal s) => s.playerId),
        <String>['p2', 'p1'],
      );
      expect(signals.first.headline, 'Big moved -9.4%');
    });

    test('drops flat players rather than reporting a 0.0% "move"', () {
      final GteMarketMovers movers = GteMarketMovers(
        mostTraded: <GteMarketMoverItem>[_mover('p1', 'Flat', 0)],
      );
      expect(buildGtexCommunityWorldSignals(movers), isEmpty);
    });

    test('is bounded', () {
      final GteMarketMovers movers = GteMarketMovers(
        topGainers: List<GteMarketMoverItem>.generate(
          40,
          (int i) => _mover('p$i', 'Player $i', 40.0 - i),
        ),
      );
      expect(
        buildGtexCommunityWorldSignals(movers),
        hasLength(gtexCommunityWorldSignalLimit),
      );
    });

    test('renders social proof only when a holder count was published', () {
      final GteMarketMovers movers = GteMarketMovers(
        topGainers: <GteMarketMoverItem>[
          _mover('known', 'Known', 5),
          _mover('unknown', 'Unknown', 4),
        ],
      );
      final List<GtexCommunitySignal> signals =
          buildGtexCommunityWorldSignals(
            movers,
            holderCountByPlayerId: const <String, int?>{
              'known': 12,
              'unknown': null,
            },
          );
      expect(signals.first.socialProof, '12 owners');
      expect(signals.last.socialProof, isNull);
    });
  });

  group('buildGtexCommunityYourSignals relevance', () {
    test('keeps only players the user owns or follows', () {
      final GteMarketMovers movers = GteMarketMovers(
        topGainers: <GteMarketMoverItem>[
          _mover('mine', 'Mine', 4.2),
          _mover('followed', 'Followed', 3.1),
          _mover('stranger', 'Stranger', 8.8),
        ],
      );
      final List<GtexCommunitySignal> signals =
          buildGtexCommunityYourSignals(
            ownership: _bookOf(<String>['mine']),
            movers: movers,
            followedTargets: <GtexCommunityFollowTarget>{
              GtexCommunityFollowTarget.player('followed'),
            },
          );
      expect(
        signals.map((GtexCommunitySignal s) => s.playerId),
        containsAll(<String>['mine', 'followed']),
      );
      expect(
        signals.map((GtexCommunitySignal s) => s.playerId),
        isNot(contains('stranger')),
      );
    });

    test('is empty for a user who owns and follows nothing', () {
      final GteMarketMovers movers = GteMarketMovers(
        topGainers: <GteMarketMoverItem>[_mover('stranger', 'Stranger', 8.8)],
      );
      expect(
        buildGtexCommunityYourSignals(
          ownership: GtexOwnershipBook.empty(),
          movers: movers,
        ),
        isEmpty,
      );
    });

    test('names an owned player by the ownership book, not the mover row', () {
      final GteMarketMovers movers = GteMarketMovers(
        topGainers: <GteMarketMoverItem>[_mover('mine', 'Stale name', 4.2)],
      );
      final List<GtexCommunitySignal> signals =
          buildGtexCommunityYourSignals(
            ownership: _bookOf(<String>['mine']),
            movers: movers,
          );
      expect(signals.single.headline, 'Owned mine moved +4.2%');
      expect(signals.single.detail, 'You own 2 shares.');
    });
  });

  group('buildGtexCommunityYourSignals matchday form', () {
    test('reports a form signal only once Phase 4E actually applied it', () {
      final GtexPlayerForm applied = GtexPlayerForm.fromJson(
        <String, dynamic>{
          'player_id': 'mine',
          'has_sample': true,
          'matches_counted': 4,
          'competitions_counted': 2,
          'signal': <String, dynamic>{
            'applied': true,
            'adjustment_pct': 1.8,
            'reason_code': 'form_positive',
            'confidence': 0.8,
            'capped': false,
            'matches_counted': 4,
            'competitions_counted': 2,
            'minimum_matches_required': 3,
            'effective_max_adjustment_pct': 2.4,
          },
        },
      );
      final GtexPlayerForm notApplied = GtexPlayerForm.fromJson(
        <String, dynamic>{
          'player_id': 'other',
          'has_sample': true,
          'matches_counted': 1,
          'signal': <String, dynamic>{
            'applied': false,
            'adjustment_pct': 0,
            'reason_code': 'insufficient_matches',
            'confidence': 0,
            'capped': false,
            'matches_counted': 1,
            'competitions_counted': 1,
            'minimum_matches_required': 3,
            'effective_max_adjustment_pct': 2.4,
          },
        },
      );
      final List<GtexCommunitySignal> signals =
          buildGtexCommunityYourSignals(
            ownership: _bookOf(<String>['mine', 'other']),
            movers: GteMarketMovers.empty,
            formByPlayerId: <String, GtexPlayerForm>{
              'mine': applied,
              'other': notApplied,
            },
          );
      expect(signals, hasLength(1));
      expect(signals.single.headline, 'Owned mine matchday form +1.8%');
      expect(signals.single.detail, '4 matches counted across 2 competitions.');
    });
  });

  group('buildGtexCommunityYourSignals clubs', () {
    test('states the real owner count and the real position movement', () {
      final List<GtexCommunitySignal> signals =
          buildGtexCommunityYourSignals(
            ownership: GtexOwnershipBook.empty(),
            movers: GteMarketMovers.empty,
            clubHoldings: const <GtexClubShareHolding>[_clubHolding],
          );
      expect(signals.single.socialProof, '18 owners');
      expect(
        signals.single.headline,
        'Lagos Eclipse FC: Your position +32.0%',
      );
      expect(
        signals.single.detail,
        'Club form is feeding the share price.',
      );
      expect(signals.single.action, GtexCommunityAction.openClub);
    });

    test('refuses a form claim for a club with no match history', () {
      const GtexClubShareHolding unplayed = GtexClubShareHolding(
        clubId: 'club-2',
        clubName: 'Kano Pillars FC',
        sharesOwned: 5,
        averagePriceCoin: 1,
        sharePriceCoin: 1,
        marketValueCoin: 5,
        costBasisCoin: 5,
        unrealizedPlCoin: 0,
        holderCount: 2,
        circulatingSupply: 100,
        totalSupply: 100,
        rewardSharesEarned: 0,
        governanceEnabled: false,
      );
      final List<GtexCommunitySignal> signals =
          buildGtexCommunityYourSignals(
            ownership: GtexOwnershipBook.empty(),
            movers: GteMarketMovers.empty,
            clubHoldings: const <GtexClubShareHolding>[unplayed],
          );
      expect(
        signals.single.detail,
        'No club match history yet, so no performance signal.',
      );
      // No unrealised percentage published, so the copy states the position is
      // open rather than inventing a 0.0% move.
      expect(signals.single.headline, 'Kano Pillars FC: Share position open');
      expect(signals.single.socialProof, '2 owners');
    });
  });

  group('buildGtexCommunityYourSignals challenges', () {
    test('uses the real share count and omits an unknown one', () {
      final List<GtexCommunitySignal> signals =
          buildGtexCommunityYourSignals(
            ownership: GtexOwnershipBook.empty(),
            movers: GteMarketMovers.empty,
            challenges: const <GtexClubChallengeCard>[
              GtexClubChallengeCard(
                challengeId: 'ch-1',
                title: 'Lagos derby',
                issuingClubId: 'club-1',
                issuingClubName: 'Lagos Eclipse FC',
                status: 'open',
                opponentClubName: 'Ibadan Lions FC',
                shareCount: 3,
              ),
              GtexClubChallengeCard(
                challengeId: 'ch-2',
                title: 'Open call',
                issuingClubId: 'club-1',
                issuingClubName: 'Lagos Eclipse FC',
                status: 'open',
              ),
            ],
          );
      expect(signals.first.socialProof, '3 shares');
      expect(
        signals.first.headline,
        'Lagos Eclipse FC challenged Ibadan Lions FC',
      );
      expect(signals.last.socialProof, isNull);
      expect(signals.last.headline, contains('an open opponent'));
    });
  });

  group('buildGtexCommunityYourSignals regens', () {
    test('lists owned regens by real rank, best first', () {
      final List<GtexCommunitySignal> signals =
          buildGtexCommunityYourSignals(
            ownership: _bookOf(<String>['r2', 'r1']),
            movers: GteMarketMovers.empty,
            regenRankings: const <RegenRankingEntry>[
              RegenRankingEntry(
                id: 'e2',
                playerId: 'r2',
                playerName: 'Second',
                category: 'overall',
                score: 70,
                rank: 9,
              ),
              RegenRankingEntry(
                id: 'e1',
                playerId: 'r1',
                playerName: 'First',
                category: 'overall',
                score: 90,
                rank: 2,
              ),
              RegenRankingEntry(
                id: 'e3',
                playerId: 'not-mine',
                playerName: 'Stranger',
                category: 'overall',
                score: 99,
                rank: 1,
              ),
            ],
          );
      expect(
        signals.map((GtexCommunitySignal s) => s.playerId),
        <String>['r1', 'r2'],
      );
      expect(signals.first.headline, 'First is ranked #2 in overall');
      expect(signals.first.action, GtexCommunityAction.openRegens);
    });
  });

  group('buildGtexCommunityYourSignals bounds and dedupe', () {
    test('never renders the same signal id twice', () {
      final GteMarketMovers movers = GteMarketMovers(
        topGainers: <GteMarketMoverItem>[_mover('mine', 'Mine', 4.2)],
        trending: <GteMarketMoverItem>[_mover('mine', 'Mine', 4.2)],
      );
      final List<GtexCommunitySignal> signals =
          buildGtexCommunityYourSignals(
            ownership: _bookOf(<String>['mine']),
            movers: movers,
          );
      final Set<String> ids =
          signals.map((GtexCommunitySignal s) => s.id).toSet();
      expect(ids, hasLength(signals.length));
    });

    test('is bounded', () {
      final GteMarketMovers movers = GteMarketMovers(
        topGainers: List<GteMarketMoverItem>.generate(
          40,
          (int i) => _mover('p$i', 'Player $i', 40.0 - i),
        ),
      );
      expect(
        buildGtexCommunityYourSignals(
          ownership: _bookOf(
            List<String>.generate(40, (int i) => 'p$i'),
          ),
          movers: movers,
        ),
        hasLength(gtexCommunityYourSignalLimit),
      );
    });
  });

  group('follow targets', () {
    test('a player signal resolves to a player follow target', () {
      const GtexCommunitySignal signal = GtexCommunitySignal(
        id: 's',
        object: GtexCommunityObject.player,
        lane: GtexCommunityLane.yours,
        headline: 'h',
        detail: 'd',
        playerId: 'p1',
        isFollowable: true,
      );
      expect(signal.followTarget, GtexCommunityFollowTarget.player('p1'));
      expect(signal.followTarget!.key, 'player:p1');
    });

    test('a challenge signal is not followable', () {
      const GtexCommunitySignal signal = GtexCommunitySignal(
        id: 's',
        object: GtexCommunityObject.challenge,
        lane: GtexCommunityLane.yours,
        headline: 'h',
        detail: 'd',
        clubId: 'c1',
      );
      expect(signal.followTarget, isNull);
    });
  });

  group('buildGtexCommunityHeadline', () {
    test('signed out with movement invites sign-in without promising data', () {
      expect(
        buildGtexCommunityHeadline(
          access: GtexCommunityAccess.anonymous,
          worldSignals: const <GtexCommunitySignal>[
            GtexCommunitySignal(
              id: 'a',
              object: GtexCommunityObject.market,
              lane: GtexCommunityLane.world,
              headline: 'h',
              detail: 'd',
            ),
          ],
          yourSignals: const <GtexCommunitySignal>[],
        ),
        'Sign in to see what is happening to the players and clubs you own.',
      );
    });

    test('signed out with a quiet economy says so', () {
      expect(
        buildGtexCommunityHeadline(
          access: GtexCommunityAccess.anonymous,
          worldSignals: const <GtexCommunitySignal>[],
          yourSignals: const <GtexCommunitySignal>[],
        ),
        'The GTEX football economy is quiet right now.',
      );
    });

    test('signed in with nothing of their own does not pretend otherwise', () {
      expect(
        buildGtexCommunityHeadline(
          access: GtexCommunityAccess.authenticated,
          worldSignals: const <GtexCommunitySignal>[
            GtexCommunitySignal(
              id: 'a',
              object: GtexCommunityObject.market,
              lane: GtexCommunityLane.world,
              headline: 'h',
              detail: 'd',
            ),
          ],
          yourSignals: const <GtexCommunitySignal>[],
        ),
        'Nothing has moved around your football yet. The wider economy is still live.',
      );
    });

    test('signed in counts only real signals', () {
      expect(
        buildGtexCommunityHeadline(
          access: GtexCommunityAccess.authenticated,
          worldSignals: const <GtexCommunitySignal>[],
          yourSignals: const <GtexCommunitySignal>[
            GtexCommunitySignal(
              id: 'a',
              object: GtexCommunityObject.player,
              lane: GtexCommunityLane.yours,
              headline: 'h',
              detail: 'd',
            ),
          ],
        ),
        '1 thing happened around your football.',
      );
    });
  });

  group('gtexCommunitySignedPercent', () {
    test('always carries the sign', () {
      expect(gtexCommunitySignedPercent(4.24), '+4.2%');
      expect(gtexCommunitySignedPercent(-1.75), '-1.8%');
      expect(gtexCommunitySignedPercent(0), '+0.0%');
    });
  });
}
