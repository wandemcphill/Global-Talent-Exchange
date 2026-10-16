import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_exchange_models.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/domain/ownership/gtex_ownership_models.dart';
import 'package:gte_frontend/domain/value/gtex_value_models.dart';
import 'package:gte_frontend/features/club_redesign/models/gtex_club_ownership_models.dart';
import 'package:gte_frontend/features/regen_redesign/models/gtex_regen_wire_models.dart';
import 'package:gte_frontend/features/social/data/gtex_community_pulse_provider.dart';
import 'package:gte_frontend/features/social/data/gtex_community_social_models.dart';
import 'package:gte_frontend/features/social/models/gtex_community_models.dart';

GteMarketMoverItem _mover(String id, String name, double pct) {
  return GteMarketMoverItem(
    playerId: id,
    playerName: name,
    dayChange: pct,
    dayChangePercent: pct,
    volume24h: 100,
  );
}

const GtePortfolioView _emptyPortfolio = GtePortfolioView(
  holdings: <GtePortfolioHolding>[],
);

const GteOrderListView _emptyOrders = GteOrderListView(
  items: <GteOrderRecord>[],
  limit: 0,
  offset: 0,
  total: 0,
);

GtePortfolioView _portfolioOf(List<String> ids) {
  return GtePortfolioView(
    holdings: ids
        .map(
          (String id) => GtePortfolioHolding(
            playerId: id,
            quantity: 1,
            averageCost: 10,
            currentPrice: 12,
            marketValue: 12,
            unrealizedPl: 2,
            unrealizedPlPercent: 20,
            playerName: 'Owned $id',
          ),
        )
        .toList(growable: false),
  );
}

/// A recorder for every read the loader makes, so a test can assert the
/// surface stays bounded rather than fanning out over a portfolio.
class _Recorder {
  final List<String> holderCountCalls = <String>[];
  final List<String> formCalls = <String>[];
  final List<String> challengeCalls = <String>[];
}

GtexCommunitySources _sources({
  required _Recorder recorder,
  GteMarketMovers movers = GteMarketMovers.empty,
  GtePortfolioView portfolio = _emptyPortfolio,
  GtexClubOwnershipPortfolio? clubPortfolio,
  List<RegenRankingEntry> regens = const <RegenRankingEntry>[],
  GteOrderListView orders = _emptyOrders,
  List<GtexSocialFollow> follows = const <GtexSocialFollow>[],
  List<GtexClubChallengeCard> challenges = const <GtexClubChallengeCard>[],
  Map<String, int?> holderCounts = const <String, int?>{},
  Object? moversError,
  Object? clubPortfolioError,
  Object? followsError,
  Object? challengeError,
  Object? holderCountError,
}) {
  return GtexCommunitySources(
    loadMarketMovers: () async {
      if (moversError != null) {
        throw moversError;
      }
      return movers;
    },
    loadPortfolio: () async => portfolio,
    loadClubPortfolio: () async {
      if (clubPortfolioError != null) {
        throw clubPortfolioError;
      }
      return clubPortfolio ?? GtexClubOwnershipPortfolio.empty();
    },
    loadRegenRankings: () async => regens,
    loadOrders: () async => orders,
    loadFollows: () async {
      if (followsError != null) {
        throw followsError;
      }
      return follows;
    },
    loadClubChallenges: (String clubId) async {
      recorder.challengeCalls.add(clubId);
      if (challengeError != null) {
        throw challengeError;
      }
      return challenges;
    },
    loadHolderCount: (String playerId) async {
      recorder.holderCountCalls.add(playerId);
      if (holderCountError != null) {
        throw holderCountError;
      }
      return holderCounts[playerId];
    },
    loadPlayerForm: (String playerId) async {
      recorder.formCalls.add(playerId);
      return GtexPlayerForm.unknown(playerId);
    },
  );
}

GtexClubShareHolding _club(String id, String name) {
  return GtexClubShareHolding(
    clubId: id,
    clubName: name,
    sharesOwned: 1,
    averagePriceCoin: 1,
    sharePriceCoin: 1,
    marketValueCoin: 1,
    costBasisCoin: 1,
    unrealizedPlCoin: 0,
    holderCount: 4,
    circulatingSupply: 10,
    totalSupply: 10,
    rewardSharesEarned: 0,
    governanceEnabled: false,
  );
}

void main() {
  group('anonymous access', () {
    test('sees the public world lane and never a personal lane', () async {
      final _Recorder recorder = _Recorder();
      final GtexCommunityPulse pulse = await loadGtexCommunityPulse(
        authenticated: false,
        sources: _sources(
          recorder: recorder,
          movers: GteMarketMovers(
            topGainers: <GteMarketMoverItem>[_mover('p1', 'Ada Obi', 4.2)],
          ),
          portfolio: _portfolioOf(<String>['p1']),
        ),
      );
      expect(pulse.access, GtexCommunityAccess.anonymous);
      expect(pulse.worldSignals, hasLength(1));
      expect(pulse.yourSignals, isEmpty);
      expect(pulse.followedTargets, isEmpty);
      // No authenticated read is attempted at all for a guest session.
      expect(recorder.holderCountCalls, isEmpty);
      expect(recorder.formCalls, isEmpty);
      expect(recorder.challengeCalls, isEmpty);
    });

    test('a failing public read degrades to a warning, not an exception', () async {
      final GtexCommunityPulse pulse = await loadGtexCommunityPulse(
        authenticated: false,
        sources: _sources(
          recorder: _Recorder(),
          moversError: StateError('market down'),
        ),
      );
      expect(pulse.worldSignals, isEmpty);
      expect(pulse.warnings, hasLength(1));
      expect(pulse.warnings.single, contains('Market movement'));
      expect(pulse.headline, 'The GTEX football economy is quiet right now.');
    });
  });

  group('authenticated composition', () {
    test('joins ownership, clubs, challenges, regens and follows', () async {
      final _Recorder recorder = _Recorder();
      final GtexCommunityPulse pulse = await loadGtexCommunityPulse(
        authenticated: true,
        sources: _sources(
          recorder: recorder,
          movers: GteMarketMovers(
            topGainers: <GteMarketMoverItem>[
              _mover('mine', 'Mine', 6.1),
              _mover('stranger', 'Stranger', 9.9),
            ],
          ),
          portfolio: _portfolioOf(<String>['mine']),
          clubPortfolio: GtexClubOwnershipPortfolio(
            clubCount: 1,
            totalMarketValueCoin: 1,
            totalCostBasisCoin: 1,
            totalUnrealizedPlCoin: 0,
            holdings: <GtexClubShareHolding>[_club('c1', 'Lagos Eclipse FC')],
          ),
          challenges: const <GtexClubChallengeCard>[
            GtexClubChallengeCard(
              challengeId: 'ch1',
              title: 'Derby',
              issuingClubId: 'c1',
              issuingClubName: 'Lagos Eclipse FC',
              status: 'open',
              shareCount: 2,
            ),
          ],
          regens: const <RegenRankingEntry>[
            RegenRankingEntry(
              id: 'r',
              playerId: 'mine',
              playerName: 'Owned mine',
              category: 'overall',
              score: 90,
              rank: 3,
            ),
          ],
          follows: const <GtexSocialFollow>[
            GtexSocialFollow(
              id: 'f1',
              targetKey: 'club:c1',
              targetType: 'club',
              clubId: 'c1',
            ),
          ],
          holderCounts: const <String, int?>{'mine': 7},
        ),
      );

      expect(pulse.access, GtexCommunityAccess.authenticated);
      expect(pulse.followedTargets, <GtexCommunityFollowTarget>{
        GtexCommunityFollowTarget.club('c1'),
      });
      final Set<GtexCommunityObject> objects = pulse.yourSignals
          .map((GtexCommunitySignal s) => s.object)
          .toSet();
      expect(
        objects,
        containsAll(<GtexCommunityObject>[
          GtexCommunityObject.player,
          GtexCommunityObject.club,
          GtexCommunityObject.challenge,
        ]),
      );
      expect(
        pulse.yourSignals.first.socialProof,
        '7 owners',
        reason: 'the owned mover carries its real holder count',
      );
      expect(pulse.warnings, isEmpty);
      expect(recorder.challengeCalls, <String>['c1']);
    });

    test('bounds per-player lookups and prefers the user\'s own players', () async {
      final _Recorder recorder = _Recorder();
      await loadGtexCommunityPulse(
        authenticated: true,
        sources: _sources(
          recorder: recorder,
          movers: GteMarketMovers(
            topGainers: <GteMarketMoverItem>[
              for (int i = 0; i < 20; i += 1) _mover('w$i', 'World $i', 20.0 - i),
              _mover('mine', 'Mine', 0.5),
            ],
          ),
          portfolio: _portfolioOf(<String>['mine']),
        ),
      );
      expect(
        recorder.holderCountCalls,
        hasLength(gtexCommunityPlayerLookupLimit),
      );
      expect(
        recorder.holderCountCalls.first,
        'mine',
        reason: 'an owned player outranks a bigger stranger move for lookups',
      );
      // The same bounded set feeds both lookups: no duplicated market request.
      expect(recorder.formCalls, recorder.holderCountCalls);
      expect(
        recorder.holderCountCalls.toSet(),
        hasLength(recorder.holderCountCalls.length),
      );
    });

    test('bounds club challenge lookups', () async {
      final _Recorder recorder = _Recorder();
      await loadGtexCommunityPulse(
        authenticated: true,
        sources: _sources(
          recorder: recorder,
          clubPortfolio: GtexClubOwnershipPortfolio(
            clubCount: 9,
            totalMarketValueCoin: 9,
            totalCostBasisCoin: 9,
            totalUnrealizedPlCoin: 0,
            holdings: <GtexClubShareHolding>[
              for (int i = 0; i < 9; i += 1) _club('c$i', 'Club $i'),
            ],
          ),
        ),
      );
      expect(
        recorder.challengeCalls,
        hasLength(gtexCommunityClubLookupLimit),
      );
    });
  });

  group('partial failure', () {
    test('a failing club read keeps the market lane and warns once', () async {
      final GtexCommunityPulse pulse = await loadGtexCommunityPulse(
        authenticated: true,
        sources: _sources(
          recorder: _Recorder(),
          movers: GteMarketMovers(
            topGainers: <GteMarketMoverItem>[_mover('p1', 'Ada Obi', 4.2)],
          ),
          clubPortfolioError: StateError('clubs down'),
        ),
      );
      expect(pulse.worldSignals, hasLength(1));
      expect(pulse.warnings, hasLength(1));
      expect(pulse.warnings.single, contains('club shares'));
    });

    test('a failing challenge read warns and drops only that club', () async {
      final GtexCommunityPulse pulse = await loadGtexCommunityPulse(
        authenticated: true,
        sources: _sources(
          recorder: _Recorder(),
          clubPortfolio: GtexClubOwnershipPortfolio(
            clubCount: 1,
            totalMarketValueCoin: 1,
            totalCostBasisCoin: 1,
            totalUnrealizedPlCoin: 0,
            holdings: <GtexClubShareHolding>[_club('c1', 'Lagos Eclipse FC')],
          ),
          challengeError: StateError('challenges down'),
        ),
      );
      expect(pulse.warnings.single, contains('Lagos Eclipse FC'));
      expect(
        pulse.yourSignals
            .where((GtexCommunitySignal s) =>
                s.object == GtexCommunityObject.challenge)
            .toList(),
        isEmpty,
      );
      expect(
        pulse.yourSignals
            .where(
                (GtexCommunitySignal s) => s.object == GtexCommunityObject.club)
            .toList(),
        hasLength(1),
        reason: 'the club itself still renders from its own source',
      );
    });

    test('a failing holder-count lookup leaves the count unknown, not zero', () async {
      final GtexCommunityPulse pulse = await loadGtexCommunityPulse(
        authenticated: true,
        sources: _sources(
          recorder: _Recorder(),
          movers: GteMarketMovers(
            topGainers: <GteMarketMoverItem>[_mover('mine', 'Mine', 4.2)],
          ),
          portfolio: _portfolioOf(<String>['mine']),
          holderCountError: StateError('detail down'),
        ),
      );
      expect(pulse.yourSignals.single.socialProof, isNull);
    });

    test('a failing follow read does not hide the rest of the surface', () async {
      final GtexCommunityPulse pulse = await loadGtexCommunityPulse(
        authenticated: true,
        sources: _sources(
          recorder: _Recorder(),
          movers: GteMarketMovers(
            topGainers: <GteMarketMoverItem>[_mover('p1', 'Ada Obi', 4.2)],
          ),
          followsError: StateError('follows down'),
        ),
      );
      expect(pulse.followedTargets, isEmpty);
      expect(pulse.worldSignals, hasLength(1));
      expect(pulse.warnings.single, contains('follows'));
    });
  });

  group('empty community', () {
    test('an authenticated user with no football gets an honest headline', () async {
      final GtexCommunityPulse pulse = await loadGtexCommunityPulse(
        authenticated: true,
        sources: _sources(recorder: _Recorder()),
      );
      expect(pulse.isEmpty, isTrue);
      expect(
        pulse.headline,
        'Nothing has happened in the GTEX football economy yet.',
      );
      expect(pulse.warnings, isEmpty);
    });
  });

  group('gtexCommunityFollowTargetsFrom', () {
    test('reads the server rows and ignores malformed ones', () {
      final Set<GtexCommunityFollowTarget> targets =
          gtexCommunityFollowTargetsFrom(const <GtexSocialFollow>[
            GtexSocialFollow(
              id: '1',
              targetKey: 'player:p1',
              targetType: 'player',
              playerId: 'p1',
            ),
            GtexSocialFollow(
              id: '2',
              targetKey: 'club:c1',
              targetType: 'club',
              clubId: 'c1',
            ),
            GtexSocialFollow(
              id: '3',
              targetKey: 'player:',
              targetType: 'player',
            ),
          ]);
      expect(targets, <GtexCommunityFollowTarget>{
        GtexCommunityFollowTarget.player('p1'),
        GtexCommunityFollowTarget.club('c1'),
      });
    });
  });
}
