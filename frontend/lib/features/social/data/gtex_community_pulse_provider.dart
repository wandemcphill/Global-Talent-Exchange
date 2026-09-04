import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../data/gte_exchange_api_client.dart';
import '../../../data/gte_exchange_models.dart';
import '../../../data/gte_models.dart';
import '../../../domain/ownership/gtex_ownership_models.dart';
import '../../../domain/value/gtex_value_models.dart';
import '../../../shared/providers/auth_provider.dart';
import '../../../shared/providers/live_clients_provider.dart';
import '../../club_redesign/data/gtex_club_ownership_api.dart';
import '../../club_redesign/models/gtex_club_ownership_models.dart';
import '../../regen_redesign/data/gtex_regen_world_api.dart';
import '../../regen_redesign/models/gtex_regen_wire_models.dart';
import '../models/gtex_community_models.dart';
import 'gtex_community_social_api.dart';
import 'gtex_community_social_models.dart';

/// How many ranking rows are scanned to find the user's own regens.
const int _regenRankingLookupLimit = 60;

/// The reads the community surface is composed from.
///
/// Every entry is an existing published contract. Holding them as function
/// references keeps `loadGtexCommunityPulse` a plain async function that a
/// test can drive - including the partial-failure and anonymous paths -
/// without a container, a transport, or a network.
class GtexCommunitySources {
  const GtexCommunitySources({
    required this.loadMarketMovers,
    required this.loadPortfolio,
    required this.loadClubPortfolio,
    required this.loadRegenRankings,
    required this.loadOrders,
    required this.loadFollows,
    required this.loadClubChallenges,
    required this.loadHolderCount,
    required this.loadPlayerForm,
  });

  final Future<GteMarketMovers> Function() loadMarketMovers;
  final Future<GtePortfolioView> Function() loadPortfolio;
  final Future<GtexClubOwnershipPortfolio> Function() loadClubPortfolio;
  final Future<List<RegenRankingEntry>> Function() loadRegenRankings;
  final Future<GteOrderListView> Function() loadOrders;
  final Future<List<GtexSocialFollow>> Function() loadFollows;
  final Future<List<GtexClubChallengeCard>> Function(String clubId)
  loadClubChallenges;

  /// The real holder count for one player, or `null` when the backend
  /// published none. Implemented over `GET /api/market/players/{id}`.
  final Future<int?> Function(String playerId) loadHolderCount;
  final Future<GtexPlayerForm> Function(String playerId) loadPlayerForm;
}

/// Composes the GTEX community surface from the football economy that already
/// exists.
///
/// Signed out this is the public world lane alone. Signed in it adds the
/// user's own football: owned players that moved, matchday form that was
/// actually applied, club share positions with their real owner counts, club
/// challenge activity, owned regens on the ranking board, and settled
/// ownership changes.
///
/// Failure is per source. A club portfolio that 500s costs the club lane and
/// contributes one warning; it does not blank the market lane and it never
/// turns an unknown count into a zero.
Future<GtexCommunityPulse> loadGtexCommunityPulse({
  required bool authenticated,
  required GtexCommunitySources sources,
}) async {
  final List<String> warnings = <String>[];

  Future<T> guarded<T>(
    Future<T> Function() load,
    T fallback,
    String warning,
  ) async {
    try {
      return await load();
    } catch (error) {
      warnings.add('$warning: $error');
      return fallback;
    }
  }

  if (!authenticated) {
    final GteMarketMovers movers = await guarded<GteMarketMovers>(
      sources.loadMarketMovers,
      GteMarketMovers.empty,
      'Market movement could not be loaded',
    );
    final List<GtexCommunitySignal> worldSignals =
        buildGtexCommunityWorldSignals(movers);
    return GtexCommunityPulse.anonymous(
      worldSignals: worldSignals,
      warnings: warnings,
    );
  }

  // Independent reads run together; each degrades on its own.
  final List<Object> loaded = await Future.wait<Object>(<Future<Object>>[
    guarded<GteMarketMovers>(
      sources.loadMarketMovers,
      GteMarketMovers.empty,
      'Market movement could not be loaded',
    ),
    guarded<GtePortfolioView>(
      sources.loadPortfolio,
      const GtePortfolioView(holdings: <GtePortfolioHolding>[]),
      'Your squad could not be loaded',
    ),
    guarded<GtexClubOwnershipPortfolio>(
      sources.loadClubPortfolio,
      GtexClubOwnershipPortfolio.empty(),
      'Your club shares could not be loaded',
    ),
    guarded<List<RegenRankingEntry>>(
      () => sources.loadRegenRankings(),
      const <RegenRankingEntry>[],
      'Regen rankings could not be loaded',
    ),
    guarded<GteOrderListView>(
      sources.loadOrders,
      const GteOrderListView(
        items: <GteOrderRecord>[],
        limit: 0,
        offset: 0,
        total: 0,
      ),
      'Recent ownership changes could not be loaded',
    ),
    guarded<List<GtexSocialFollow>>(
      sources.loadFollows,
      const <GtexSocialFollow>[],
      'Your follows could not be loaded',
    ),
  ]);

  final GteMarketMovers movers = loaded[0] as GteMarketMovers;
  final GtexOwnershipBook ownership = GtexOwnershipBook.fromPortfolio(
    loaded[1] as GtePortfolioView,
  );
  final GtexClubOwnershipPortfolio clubPortfolio =
      loaded[2] as GtexClubOwnershipPortfolio;
  final List<RegenRankingEntry> regenRankings =
      loaded[3] as List<RegenRankingEntry>;
  final GteOrderListView orders = loaded[4] as GteOrderListView;
  final List<GtexSocialFollow> follows = loaded[5] as List<GtexSocialFollow>;

  final Set<GtexCommunityFollowTarget> followedTargets =
      gtexCommunityFollowTargetsFrom(follows);

  final List<GtexClubShareHolding> clubHoldings = clubPortfolio.holdings
      .take(gtexCommunityClubLookupLimit)
      .toList(growable: false);

  // One bounded set of player lookups feeds both lanes, so the same player is
  // never fetched twice for two different sections.
  final List<String> lookupPlayerIds = gtexCommunityPlayerLookupIds(
    ownership: ownership,
    movers: movers,
    followedTargets: followedTargets,
  );

  final Map<String, int?> holderCountByPlayerId = <String, int?>{};
  final Map<String, GtexPlayerForm> formByPlayerId =
      <String, GtexPlayerForm>{};
  await Future.wait<void>(
    lookupPlayerIds.map((String playerId) async {
      final List<Object?> results = await Future.wait<Object?>(<Future<Object?>>[
        sources.loadHolderCount(playerId).catchError((Object _) => null),
        sources
            .loadPlayerForm(playerId)
            .then<GtexPlayerForm?>((GtexPlayerForm form) => form)
            .catchError((Object _) => null),
      ]);
      final Object? holderCount = results[0];
      if (holderCount is int) {
        holderCountByPlayerId[playerId] = holderCount;
      }
      final Object? form = results[1];
      if (form is GtexPlayerForm && ownership.owns(playerId)) {
        formByPlayerId[playerId] = form;
      }
    }),
  );

  final List<GtexClubChallengeCard> challenges = <GtexClubChallengeCard>[];
  final List<List<GtexClubChallengeCard>> challengeResults =
      await Future.wait<List<GtexClubChallengeCard>>(
        clubHoldings.map(
          (GtexClubShareHolding holding) => guarded<List<GtexClubChallengeCard>>(
            () => sources.loadClubChallenges(holding.clubId),
            const <GtexClubChallengeCard>[],
            'Challenge activity for ${holding.clubName} could not be loaded',
          ),
        ),
      );
  for (final List<GtexClubChallengeCard> result in challengeResults) {
    challenges.addAll(result);
  }

  final List<GtexCommunitySignal> worldSignals = buildGtexCommunityWorldSignals(
    movers,
    holderCountByPlayerId: holderCountByPlayerId,
  );
  final List<GtexCommunitySignal> yourSignals = buildGtexCommunityYourSignals(
    ownership: ownership,
    movers: movers,
    holderCountByPlayerId: holderCountByPlayerId,
    formByPlayerId: formByPlayerId,
    clubHoldings: clubHoldings,
    challenges: challenges,
    regenRankings: regenRankings,
    orders: orders,
    followedTargets: followedTargets,
  );

  return GtexCommunityPulse(
    access: GtexCommunityAccess.authenticated,
    headline: buildGtexCommunityHeadline(
      access: GtexCommunityAccess.authenticated,
      worldSignals: worldSignals,
      yourSignals: yourSignals,
    ),
    worldSignals: worldSignals,
    yourSignals: yourSignals,
    followedTargets: followedTargets,
    warnings: warnings,
  );
}

/// The follow set, read straight back from the server's own rows.
Set<GtexCommunityFollowTarget> gtexCommunityFollowTargetsFrom(
  List<GtexSocialFollow> follows,
) {
  final Set<GtexCommunityFollowTarget> targets =
      <GtexCommunityFollowTarget>{};
  for (final GtexSocialFollow follow in follows) {
    final String? playerId = follow.playerId;
    final String? clubId = follow.clubId;
    if (follow.targetType == 'player' &&
        playerId != null &&
        playerId.isNotEmpty) {
      targets.add(GtexCommunityFollowTarget.player(playerId));
    } else if (follow.targetType == 'club' &&
        clubId != null &&
        clubId.isNotEmpty) {
      targets.add(GtexCommunityFollowTarget.club(clubId));
    }
  }
  return targets;
}

/// The hard-bounded set of players worth a per-player lookup.
///
/// Owned or followed movers come first because their social proof lands on
/// the "your community" lane; the world lane fills any remaining slots. The
/// result is capped at [gtexCommunityPlayerLookupLimit] and deduplicated, so
/// the number of per-player requests does not grow with portfolio size.
List<String> gtexCommunityPlayerLookupIds({
  required GtexOwnershipBook ownership,
  required GteMarketMovers movers,
  Set<GtexCommunityFollowTarget> followedTargets =
      const <GtexCommunityFollowTarget>{},
  int limit = gtexCommunityPlayerLookupLimit,
}) {
  final Map<String, GteMarketMoverItem> deduped =
      <String, GteMarketMoverItem>{};
  for (final GteMarketMoverItem item in <GteMarketMoverItem>[
    ...movers.topGainers,
    ...movers.topLosers,
    ...movers.mostTraded,
    ...movers.trending,
  ]) {
    deduped.putIfAbsent(item.playerId, () => item);
  }
  final List<GteMarketMoverItem> ordered = deduped.values.toList()
    ..sort(
      (GteMarketMoverItem a, GteMarketMoverItem b) =>
          b.dayChangePercent.abs().compareTo(a.dayChangePercent.abs()),
    );

  bool isMine(String playerId) =>
      ownership.owns(playerId) ||
      followedTargets.contains(GtexCommunityFollowTarget.player(playerId));

  final List<String> ids = <String>[
    ...ordered
        .where((GteMarketMoverItem item) => isMine(item.playerId))
        .map((GteMarketMoverItem item) => item.playerId),
    ...ordered
        .where((GteMarketMoverItem item) => !isMine(item.playerId))
        .map((GteMarketMoverItem item) => item.playerId),
  ];
  final Set<String> seen = <String>{};
  return ids
      .where((String id) => id.isNotEmpty && seen.add(id))
      .take(limit)
      .toList(growable: false);
}

/// The live community surface for the current session.
final FutureProvider<GtexCommunityPulse> communityPulseProvider =
    FutureProvider<GtexCommunityPulse>((Ref ref) {
      final bool authenticated = ref.watch(isAuthenticatedProvider);
      final GteExchangeApiClient exchange = ref.watch(exchangeApiClientProvider);
      final GtexCommunitySocialApi social = ref.watch(
        communitySocialApiProvider,
      );
      final GtexClubOwnershipApi clubApi = GtexClubOwnershipApi(
        client: ref.watch(authedApiProvider),
      );
      final GtexRegenWorldApi regenApi = GtexRegenWorldApi(
        client: ref.watch(authedApiProvider),
      );

      return loadGtexCommunityPulse(
        authenticated: authenticated,
        sources: GtexCommunitySources(
          loadMarketMovers: () => exchange.fetchMarketMovers(limit: 20),
          loadPortfolio: exchange.fetchPortfolio,
          loadClubPortfolio: clubApi.fetchMyClubPortfolio,
          loadRegenRankings: () =>
              regenApi.listRankings(limit: _regenRankingLookupLimit),
          loadOrders: () => exchange.listOrders(limit: 20),
          loadFollows: social.listMyFollows,
          loadClubChallenges: social.listClubChallenges,
          loadHolderCount: (String playerId) async {
            final GteMarketPlayerDetailView detail = await exchange
                .fetchPlayerDetail(playerId);
            return detail.marketProfile.holderCount;
          },
          loadPlayerForm: exchange.fetchPlayerForm,
        ),
      );
    });

final Provider<GtexCommunitySocialApi> communitySocialApiProvider =
    Provider<GtexCommunitySocialApi>((Ref ref) {
      return GtexCommunitySocialApi(client: ref.watch(authedApiProvider));
    });

/// Which follow toggles are in flight right now.
///
/// A follow is cheap and idempotent server-side, but a control that can be
/// hammered is still a control that generates avoidable writes. Holding the
/// in-flight target keys lets the UI disable exactly the row being toggled
/// while leaving the rest of the surface usable.
class GtexCommunityFollowController extends Notifier<Set<String>> {
  @override
  Set<String> build() => const <String>{};

  bool isBusy(GtexCommunityFollowTarget target) => state.contains(target.key);

  /// Follows or unfollows [target], then re-reads the surface so the rendered
  /// follow state comes from the server rather than from an optimistic guess.
  ///
  /// Returns `true` when the write was accepted.
  Future<bool> toggle({
    required GtexCommunityFollowTarget target,
    required bool currentlyFollowing,
  }) async {
    if (state.contains(target.key)) {
      return false;
    }
    state = <String>{...state, target.key};
    try {
      final GtexCommunitySocialApi api = ref.read(communitySocialApiProvider);
      final String? clubId = target.targetType == 'club' ? target.id : null;
      final String? playerId = target.targetType == 'player' ? target.id : null;
      if (currentlyFollowing) {
        await api.unfollow(
          targetType: target.targetType,
          clubId: clubId,
          playerId: playerId,
        );
      } else {
        await api.follow(
          targetType: target.targetType,
          clubId: clubId,
          playerId: playerId,
        );
      }
      ref.invalidate(communityPulseProvider);
      return true;
    } finally {
      state = <String>{...state}..remove(target.key);
    }
  }
}

final NotifierProvider<GtexCommunityFollowController, Set<String>>
communityFollowControllerProvider =
    NotifierProvider<GtexCommunityFollowController, Set<String>>(
      GtexCommunityFollowController.new,
    );
