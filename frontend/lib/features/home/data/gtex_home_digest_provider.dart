import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../data/gte_authed_api.dart';
import '../../../data/gte_exchange_api_client.dart';
import '../../../data/gte_exchange_models.dart';
import '../../../data/gte_models.dart';
import '../../../domain/ownership/gtex_ownership_models.dart';
import '../../../domain/value/gtex_value_models.dart';
import '../../../features/club_redesign/data/gtex_club_ownership_api.dart';
import '../../../features/club_redesign/models/gtex_club_ownership_models.dart';
import '../../../features/navigation/routing/gte_navigation_route.dart';
import '../../../features/regen_redesign/data/gtex_regen_world_api.dart';
import '../../../features/regen_redesign/models/gtex_regen_wire_models.dart';
import '../../../navigation/app_destinations.dart';
import '../../../shared/providers/auth_provider.dart';
import '../../../shared/providers/live_clients_provider.dart';
import '../../../widgets/gte_formatters.dart';
import '../models/gtex_home_digest_models.dart';

/// How many owned players get an individual matchday-form lookup. Home is
/// the most frequently loaded screen (Phase 4F Step 6), so this stays small
/// and bounded rather than fetching form for a whole portfolio.
const int _formLookupLimit = 5;
const int _ownedHighlightLimit = 5;
const int _moverHighlightLimit = 3;
const int _clubHighlightLimit = 5;
const int _regenHighlightLimit = 5;
const int _activityLimit = 5;
const int _attentionLimit = 5;
const int _regenRankingLookupLimit = 60;

/// Composes the personalized Home digest strictly from PHASE4-B's ownership
/// book, PHASE4-A's market movers, PHASE4-D's club-share holdings and
/// PHASE4-E's matchday form - the exact dependency set the Phase 4F contract
/// specifies. Nothing here recomputes value, price, or performance; every
/// figure is read from those published models.
///
/// A per-source failure (a club-portfolio sync error, a form lookup timing
/// out) is recorded as a warning and never hides the sources that did load -
/// mirroring the pattern already used by `marketDashboardProvider`.
final FutureProvider<GtexHomeDigest> homeDigestProvider =
    FutureProvider<GtexHomeDigest>((Ref ref) async {
      final bool authenticated = ref.watch(isAuthenticatedProvider);
      if (!authenticated) {
        return GtexHomeDigest.empty();
      }

      final GteExchangeApiClient exchange = ref.watch(exchangeApiClientProvider);
      final GteAuthedApi authedApi = ref.watch(authedApiProvider);
      final GtexClubOwnershipApi clubApi = GtexClubOwnershipApi(client: authedApi);
      final GtexRegenWorldApi regenApi = GtexRegenWorldApi(client: authedApi);

      final List<String> warnings = <String>[];

      GtePortfolioView portfolio = const GtePortfolioView(
        holdings: <GtePortfolioHolding>[],
      );
      try {
        portfolio = await exchange.fetchPortfolio();
      } catch (error) {
        warnings.add('Your squad could not be loaded: $error');
      }
      final GtexOwnershipBook ownership = GtexOwnershipBook.fromPortfolio(
        portfolio,
      );

      GteMarketMovers movers = GteMarketMovers.empty;
      try {
        movers = await exchange.fetchMarketMovers(limit: 20);
      } catch (error) {
        warnings.add('Market movement could not be loaded: $error');
      }

      GtexClubOwnershipPortfolio clubPortfolio =
          GtexClubOwnershipPortfolio.empty();
      try {
        clubPortfolio = await clubApi.fetchMyClubPortfolio();
      } catch (error) {
        warnings.add('Your club shares could not be loaded: $error');
      }

      List<RegenRankingEntry> regenRankings = const <RegenRankingEntry>[];
      try {
        regenRankings = await regenApi.listRankings(
          limit: _regenRankingLookupLimit,
        );
      } catch (error) {
        warnings.add('Regen rankings could not be loaded: $error');
      }

      GteOrderListView orders = const GteOrderListView(
        items: <GteOrderRecord>[],
        limit: 0,
        offset: 0,
        total: 0,
      );
      try {
        orders = await exchange.listOrders(limit: 20);
      } catch (error) {
        warnings.add('Recent activity could not be loaded: $error');
      }

      final List<GtexOwnershipStake> stakesByMovement = ownership.stakes
          .toList(growable: false)
        ..sort(
          (GtexOwnershipStake a, GtexOwnershipStake b) => (b
                      .unrealizedPlPercent
                      ?.abs() ??
                  0)
              .compareTo(a.unrealizedPlPercent?.abs() ?? 0),
        );
      final List<GtexOwnershipStake> topStakes = stakesByMovement
          .take(_ownedHighlightLimit)
          .toList(growable: false);

      final Map<String, GtexPlayerForm> formById = <String, GtexPlayerForm>{};
      for (final GtexOwnershipStake stake
          in topStakes.take(_formLookupLimit)) {
        try {
          formById[stake.playerId] = await exchange.fetchPlayerForm(
            stake.playerId,
          );
        } catch (_) {
          // A single player's form failing to load must not hide the rest
          // of the squad or the position itself (P6) - it is simply absent.
        }
      }

      final List<GtexHomePlayerHighlight> ownedPlayers = topStakes
          .map(
            (GtexOwnershipStake stake) => gtexHomePlayerHighlightFromStake(
              stake,
              formById[stake.playerId],
            ),
          )
          .toList(growable: false);

      final List<GteMarketMoverItem> allMovers = <GteMarketMoverItem>[
        ...movers.topGainers,
        ...movers.topLosers,
        ...movers.trending,
        ...movers.mostTraded,
      ];
      final Map<String, GteMarketMoverItem> deduped = <String, GteMarketMoverItem>{};
      for (final GteMarketMoverItem item in allMovers) {
        deduped.putIfAbsent(item.playerId, () => item);
      }
      final List<GtexHomeMoverHighlight> yourMoversToday = deduped.values
          .where((GteMarketMoverItem item) => ownership.owns(item.playerId))
          .map(
            (GteMarketMoverItem item) => GtexHomeMoverHighlight(
              playerId: item.playerId,
              playerName: item.playerName,
              dayChangePercent: item.dayChangePercent,
              isOwned: true,
            ),
          )
          .take(_moverHighlightLimit)
          .toList(growable: false);
      final List<GtexHomeMoverHighlight> opportunityMovers = movers.topGainers
          .where((GteMarketMoverItem item) => !ownership.owns(item.playerId))
          .map(
            (GteMarketMoverItem item) => GtexHomeMoverHighlight(
              playerId: item.playerId,
              playerName: item.playerName,
              dayChangePercent: item.dayChangePercent,
              isOwned: false,
            ),
          )
          .take(_moverHighlightLimit)
          .toList(growable: false);

      final List<GtexHomeClubHighlight> clubs = clubPortfolio.holdings
          .take(_clubHighlightLimit)
          .map(gtexHomeClubHighlightFromHolding)
          .toList(growable: false);

      final List<GtexHomeRegenHighlight> regens = regenRankings
          .where((RegenRankingEntry entry) => ownership.owns(entry.playerId))
          .take(_regenHighlightLimit)
          .map(
            (RegenRankingEntry entry) => GtexHomeRegenHighlight(
              playerId: entry.playerId,
              playerName: entry.playerName,
              rank: entry.rank,
              category: entry.category,
            ),
          )
          .toList(growable: false);

      final List<GtexHomeActivityItem> recentActivity = gtexHomeRecentActivityFrom(
        orders,
        ownership,
      );

      final GtexHomeUserState userState = resolveGtexHomeUserState(
        ownedPlayers: ownedPlayers,
        clubs: clubs,
        regens: regens,
      );
      final String headline = buildGtexHomeHeadline(
        userState: userState,
        yourMoversToday: yourMoversToday,
      );
      final List<GtexHomeAttentionItem> attentionItems = buildGtexHomeAttentionItems(
        yourMoversToday: yourMoversToday,
        ownedPlayers: ownedPlayers,
        clubs: clubs,
        regens: regens,
        opportunityMovers: opportunityMovers,
      );

      return GtexHomeDigest(
        userState: userState,
        headline: headline,
        ownedPlayers: ownedPlayers,
        yourMoversToday: yourMoversToday,
        opportunityMovers: opportunityMovers,
        clubs: clubs,
        regens: regens,
        attentionItems: attentionItems,
        recentActivity: recentActivity,
        warnings: warnings,
      );
    });

GtexHomePlayerHighlight gtexHomePlayerHighlightFromStake(
  GtexOwnershipStake stake,
  GtexPlayerForm? form,
) {
  final bool signalApplied = form?.signal?.applied == true;
  final String? formTrendLabel =
      signalApplied
          ? 'Form ${form!.signal!.adjustmentPct >= 0 ? '+' : ''}${form.signal!.adjustmentPct.toStringAsFixed(1)}%'
          : null;
  String? matchdayNote;
  if (form != null && form.hasSample) {
    matchdayNote =
        '${form.matchesCounted} match${form.matchesCounted == 1 ? '' : 'es'} counted this window';
  }
  return GtexHomePlayerHighlight(
    playerId: stake.playerId,
    playerName: stake.playerName ?? stake.playerId,
    clubName: stake.clubName,
    quantityLabel: stake.quantityLabel,
    priceLabel:
        stake.currentPrice == null
            ? 'Price unknown'
            : gteFormatGtc(stake.currentPrice!),
    unrealizedPlPercent: stake.unrealizedPlPercent,
    formTrendLabel: formTrendLabel,
    matchdayNote: matchdayNote,
  );
}

GtexHomeClubHighlight gtexHomeClubHighlightFromHolding(GtexClubShareHolding holding) {
  return GtexHomeClubHighlight(
    clubId: holding.clubId,
    clubName: holding.clubName,
    sharesLabel: '${holding.sharesOwned} share${holding.sharesOwned == 1 ? '' : 's'}',
    sharePriceLabel: '${gteFormatGtc(holding.sharePriceCoin)}/share',
    plLabel:
        '${holding.unrealizedPlCoin >= 0 ? '+' : ''}${gteFormatGtc(holding.unrealizedPlCoin)}',
    isInProfit: holding.isInProfit,
    hasPerformanceHistory: holding.hasPerformanceHistory,
  );
}

List<GtexHomeActivityItem> gtexHomeRecentActivityFrom(
  GteOrderListView orders,
  GtexOwnershipBook ownership,
) {
  final List<GteOrderRecord> settled = orders.items
      .where(
        (GteOrderRecord order) =>
            order.status == GteOrderStatus.filled ||
            order.status == GteOrderStatus.partiallyFilled,
      )
      .toList(growable: false)
    ..sort((GteOrderRecord a, GteOrderRecord b) {
      final DateTime? aWhen =
          a.executionSummary.lastExecutedAt ?? a.updatedAt ?? a.createdAt;
      final DateTime? bWhen =
          b.executionSummary.lastExecutedAt ?? b.updatedAt ?? b.createdAt;
      if (aWhen == null || bWhen == null) {
        return 0;
      }
      return bWhen.compareTo(aWhen);
    });
  return settled.take(_activityLimit).map((GteOrderRecord order) {
    final String? knownName = ownership.stakeFor(order.playerId)?.playerName;
    final String playerLabel = knownName ?? order.playerId;
    final String verb = order.side == GteOrderSide.buy ? 'Bought' : 'Sold';
    final DateTime? when =
        order.executionSummary.lastExecutedAt ?? order.updatedAt ?? order.createdAt;
    return GtexHomeActivityItem(
      id: order.id,
      label: '$verb $playerLabel',
      timestampLabel: gteFormatRelativeTime(when),
      playerId: order.playerId,
    );
  }).toList(growable: false);
}

GtexHomeUserState resolveGtexHomeUserState({
  required List<GtexHomePlayerHighlight> ownedPlayers,
  required List<GtexHomeClubHighlight> clubs,
  required List<GtexHomeRegenHighlight> regens,
}) {
  final bool hasPlayers = ownedPlayers.isNotEmpty;
  final bool hasClubs = clubs.isNotEmpty;
  final bool hasRegens = regens.isNotEmpty;
  final int categoryCount =
      (hasPlayers ? 1 : 0) + (hasClubs ? 1 : 0) + (hasRegens ? 1 : 0);
  if (categoryCount == 0) {
    return GtexHomeUserState.newUser;
  }
  if (categoryCount >= 2) {
    return GtexHomeUserState.multiAsset;
  }
  if (hasClubs) {
    return GtexHomeUserState.clubOwner;
  }
  if (hasRegens) {
    return GtexHomeUserState.regenInvestor;
  }
  return GtexHomeUserState.playerOwner;
}

String buildGtexHomeHeadline({
  required GtexHomeUserState userState,
  required List<GtexHomeMoverHighlight> yourMoversToday,
}) {
  if (userState == GtexHomeUserState.newUser) {
    return 'Explore GTEX and start building your football world.';
  }
  if (yourMoversToday.isEmpty) {
    return 'Your GTEX world is quiet today.';
  }
  final int count = yourMoversToday.length;
  return '$count player${count == 1 ? '' : 's'} moved today.';
}

List<GtexHomeAttentionItem> buildGtexHomeAttentionItems({
  required List<GtexHomeMoverHighlight> yourMoversToday,
  required List<GtexHomePlayerHighlight> ownedPlayers,
  required List<GtexHomeClubHighlight> clubs,
  required List<GtexHomeRegenHighlight> regens,
  required List<GtexHomeMoverHighlight> opportunityMovers,
}) {
  final List<GtexHomeAttentionItem> items = <GtexHomeAttentionItem>[];

  if (yourMoversToday.isNotEmpty) {
    final int n = yourMoversToday.length;
    items.add(
      GtexHomeAttentionItem(
        id: 'movers-today',
        label: 'Review $n player${n == 1 ? '' : 's'} whose value moved today',
        routeLocation: AppRoutes.profile,
      ),
    );
  }

  final int withForm = ownedPlayers
      .where((GtexHomePlayerHighlight p) => p.formTrendLabel != null)
      .length;
  if (withForm > 0) {
    items.add(
      GtexHomeAttentionItem(
        id: 'matchday-form',
        label:
            'New matchday form for $withForm player${withForm == 1 ? '' : 's'}',
        routeLocation: AppRoutes.profile,
      ),
    );
  }

  if (clubs.isNotEmpty) {
    items.add(
      GtexHomeAttentionItem(
        id: 'club-shares',
        label: 'Check your club shares',
        routeLocation: const GteNavigationRoute.club().path,
      ),
    );
  }

  if (regens.isNotEmpty) {
    final int n = regens.length;
    items.add(
      GtexHomeAttentionItem(
        id: 'regen-scout',
        label:
            'Scout $n rising regen${n == 1 ? '' : 's'} you own',
        routeLocation: AppRoutes.regens,
      ),
    );
  }

  if (opportunityMovers.isNotEmpty) {
    final int n = opportunityMovers.length;
    items.add(
      GtexHomeAttentionItem(
        id: 'market-opportunities',
        label: '$n market opportunit${n == 1 ? 'y' : 'ies'} worth a look',
        routeLocation: AppRoutes.market,
        useGo: true,
      ),
    );
  }

  return items.take(_attentionLimit).toList(growable: false);
}
