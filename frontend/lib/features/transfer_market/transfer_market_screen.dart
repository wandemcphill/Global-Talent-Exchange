import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/app_feedback.dart';
import '../../features/shared/data/gte_feature_support.dart';
import '../../navigation/app_destinations.dart';
import '../../shared/models/auth_session.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/providers/auth_provider.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';
import '../../shared/widgets/gtex_premium_panels.dart';
import '../../widgets/gte_state_panel.dart';
import 'live_market_provider.dart';

class TransferMarketScreen extends ConsumerWidget {
  const TransferMarketScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<MarketDashboardData> marketValue = ref.watch(
      marketDashboardProvider,
    );
    final MarketDashboardData? snapshot = marketValue.asData?.value;
    return AppPageLayout(
      title: 'Market',
      subtitle:
          'Premium live trading surface for player shares, transfer listings, wallet state, and compliance truth.',
      trailing: DataSourceBadge(
        status:
            marketValue.hasError
                ? DataSourceStatus.blocked
                : DataSourceStatus.live,
      ),
      children: <Widget>[
        GtexHeroPanel(
          eyebrow: 'LIVE MARKET DESK',
          title:
              'Trade shares, inspect listings, and route negotiations cleanly.',
          description:
              'The active shell separates player-share discovery from transfer inventory, keeps wallet/compliance honest, and pushes deep listing flows into the dedicated transfer center.',
          metrics: <Widget>[
            GtexStatTile(
              label: 'Share markets',
              value:
                  snapshot == null ? '...' : '${snapshot.playerShares.length}',
              support: 'Real-player tradability inventory',
              tone: GtexSurfaceTone.live,
            ),
            GtexStatTile(
              label: 'Transfer listings',
              value:
                  snapshot == null
                      ? '...'
                      : '${snapshot.transferListings.length}',
              support: 'Live bid inventory',
              tone: GtexSurfaceTone.info,
            ),
            GtexStatTile(
              label: 'Wallet',
              value:
                  snapshot?.wallet == null
                      ? 'Blocked'
                      : snapshot!.wallet!.totalEquity.toStringAsFixed(0),
              support:
                  snapshot?.wallet == null
                      ? 'Sign in or compliance blocked'
                      : snapshot!.wallet!.complianceMessage,
              tone:
                  snapshot?.wallet == null
                      ? GtexSurfaceTone.warning
                      : GtexSurfaceTone.success,
            ),
          ],
          actions: <Widget>[
            FilledButton.icon(
              onPressed: () => context.push(AppRoutes.transferCenter),
              icon: const Icon(Icons.swap_horiz_rounded),
              label: const Text('Open transfer center'),
            ),
          ],
        ),
        GtexSectionPanel(
          eyebrow: 'SEARCH',
          title: 'Search real players',
          subtitle:
              'Discovery is backed by the real-player universe and does not invent tradable assets.',
          child: TextField(
            onChanged:
                (String value) => ref
                    .read(marketSearchQueryProvider.notifier)
                    .setQuery(value),
            decoration: const InputDecoration(
              labelText: 'Search real players',
              hintText: 'Search /players/real-universe',
              prefixIcon: Icon(Icons.search_rounded),
            ),
          ),
        ),
        marketValue.when(
          data: (MarketDashboardData market) => _MarketBody(data: market),
          loading:
              () => GteStatePanel(
                title: 'Loading market',
                message:
                    'The active shell is fetching player shares, transfer listings, and compliance state from live endpoints.',
                isLoading: true,
              ),
          error:
              (Object error, StackTrace stackTrace) => GteStatePanel(
                title: 'Market is blocked',
                message: AppFeedback.messageFor(error),
                icon: Icons.error_outline_rounded,
                accentColor: Theme.of(context).colorScheme.error,
              ),
        ),
      ],
    );
  }
}

class _MarketBody extends ConsumerWidget {
  const _MarketBody({required this.data});

  final MarketDashboardData data;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ClubContext? clubContext = ref.watch(clubContextProvider);
    final bool authenticated = ref.watch(isAuthenticatedProvider);
    return Column(
      children: <Widget>[
        GtexSectionPanel(
          eyebrow: 'WALLET + COMPLIANCE',
          title: 'Wallet & Compliance',
          subtitle:
              data.wallet == null
                  ? authenticated
                      ? 'Wallet or compliance endpoints are blocked for this session.'
                      : 'Sign in to load live wallet and compliance state.'
                  : data.wallet!.complianceMessage,
          child: Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              GtexStatTile(
                label: 'Coin balance',
                value: data.wallet?.coinBalance.toStringAsFixed(2) ?? 'Blocked',
                tone: GtexSurfaceTone.live,
              ),
              GtexStatTile(
                label: 'Credit balance',
                value:
                    data.wallet?.creditBalance.toStringAsFixed(2) ?? 'Blocked',
                tone: GtexSurfaceTone.info,
              ),
              GtexStatTile(
                label: 'Total equity',
                value: data.wallet?.totalEquity.toStringAsFixed(2) ?? 'Blocked',
                tone: GtexSurfaceTone.success,
              ),
              GtexStatTile(
                label: 'Trade',
                value:
                    data.wallet == null
                        ? 'Blocked'
                        : data.wallet!.canTradeMarket
                        ? 'Enabled'
                        : 'Blocked',
                support:
                    data.wallet == null
                        ? 'No compliance state'
                        : data.wallet!.complianceMessage,
                tone:
                    data.wallet?.canTradeMarket == true
                        ? GtexSurfaceTone.success
                        : GtexSurfaceTone.warning,
              ),
            ],
          ),
        ),
        if (data.warnings.isNotEmpty) ...<Widget>[
          const SizedBox(height: 24),
          GteStatePanel(
            title: 'Live warnings',
            message: data.warnings.join('\n'),
            icon: Icons.warning_amber_rounded,
            accentColor: Theme.of(context).colorScheme.tertiary,
          ),
        ],
        const SizedBox(height: 24),
        GtexSectionPanel(
          eyebrow: 'SHARES',
          title: 'Player Shares',
          subtitle:
              'Discovery is fed by /players/real-universe and tradability only appears when /players/{player_id}/shares/market exists.',
          child: Column(
            children: data.playerShares
                .map(
                  (PlayerShareSummary item) => Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: GtexListTile(
                      title: item.playerName,
                      subtitle:
                          '${item.position ?? 'N/A'} | ${item.currentClubName ?? 'No club'} | ${item.marketMessage}',
                      leadingIcon: Icons.person_search_rounded,
                      tone:
                          item.isTradable
                              ? GtexSurfaceTone.live
                              : GtexSurfaceTone.warning,
                      trailing: Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: <Widget>[
                          GtexPill(
                            label:
                                item.sharePriceCoin == null
                                    ? 'No issued market'
                                    : '${item.sharePriceCoin!.toStringAsFixed(0)} coin',
                            tone:
                                item.isTradable
                                    ? GtexSurfaceTone.live
                                    : GtexSurfaceTone.warning,
                          ),
                          TextButton(
                            onPressed:
                                () => _openPlayerDetail(context, ref, item),
                            child: const Text('Detail'),
                          ),
                          FilledButton(
                            onPressed:
                                !authenticated
                                    ? null
                                    : item.isTradable
                                    ? () => _buyShares(context, ref, item)
                                    : null,
                            child: const Text('Buy'),
                          ),
                        ],
                      ),
                    ),
                  ),
                )
                .toList(growable: false),
          ),
        ),
        const SizedBox(height: 24),
        GtexSectionPanel(
          eyebrow: 'TRANSFERS',
          title: 'Transfer Listings',
          subtitle:
              clubContext == null
                  ? 'Bidding and watchlisting are blocked because this session has no verified club context.'
                  : 'Transfer listings are live. Actions use the club context carried by the active session.',
          child: Column(
            children: data.transferListings
                .map(
                  (TransferListingSummary listing) => Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: GtexListTile(
                      title: listing.playerName,
                      subtitle:
                          '${listing.status} | bid ${listing.currentHighestBid.toStringAsFixed(0)} | watchlist ${listing.watchlistCount}',
                      leadingIcon: Icons.trending_up_rounded,
                      tone: GtexSurfaceTone.info,
                      trailing: Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: <Widget>[
                          GtexPill(
                            label:
                                'Base ${listing.basePrice.toStringAsFixed(0)}',
                            tone: GtexSurfaceTone.warning,
                          ),
                          OutlinedButton(
                            onPressed:
                                clubContext == null
                                    ? null
                                    : () => _watchlistListing(
                                      context,
                                      ref,
                                      listing,
                                      clubContext,
                                    ),
                            child: const Text('Watchlist'),
                          ),
                          FilledButton(
                            onPressed:
                                () => context.push(
                                  AppRoutes.transferCenterDetailLocation(
                                    listing.id,
                                  ),
                                ),
                            child: const Text('Detail'),
                          ),
                          FilledButton(
                            onPressed:
                                clubContext == null
                                    ? null
                                    : () => _placeBid(
                                      context,
                                      ref,
                                      listing,
                                      clubContext,
                                    ),
                            child: const Text('Bid'),
                          ),
                        ],
                      ),
                    ),
                  ),
                )
                .toList(growable: false),
          ),
        ),
        if (data.holdings.isNotEmpty) ...<Widget>[
          const SizedBox(height: 24),
          GtexSectionPanel(
            eyebrow: 'PORTFOLIO',
            title: 'Share Holdings',
            subtitle: 'Live holdings from /players/me/shares/holdings.',
            child: Column(
              children: data.holdings
                  .map(
                    (PlayerShareHoldingSummary holding) => Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: GtexListTile(
                        title: holding.playerId,
                        subtitle:
                            'Shares ${holding.shareCount} | Avg cost ${holding.averageCostCoin.toStringAsFixed(2)} | Dividends ${holding.dividendsEarnedCoin.toStringAsFixed(2)}',
                        leadingIcon: Icons.account_balance_wallet_rounded,
                        tone: GtexSurfaceTone.success,
                      ),
                    ),
                  )
                  .toList(growable: false),
            ),
          ),
        ],
      ],
    );
  }

  Future<void> _openPlayerDetail(
    BuildContext context,
    WidgetRef ref,
    PlayerShareSummary item,
  ) async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (BuildContext context) {
        return Padding(
          padding: const EdgeInsets.all(24),
          child: Consumer(
            builder: (BuildContext context, WidgetRef ref, Widget? child) {
              final AsyncValue<PlayerShareDetailData> detailValue = ref.watch(
                playerShareDetailProvider(item),
              );
              return detailValue.when(
                data:
                    (PlayerShareDetailData detail) => SingleChildScrollView(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: <Widget>[
                          Text(
                            item.playerName,
                            style: Theme.of(context).textTheme.headlineSmall,
                          ),
                          const SizedBox(height: 12),
                          Text(
                            detail.playerDetail.entries
                                .take(12)
                                .map(
                                  (MapEntry<String, Object?> entry) =>
                                      '${entry.key}: ${entry.value}',
                                )
                                .join('\n'),
                          ),
                          const SizedBox(height: 16),
                          Text(
                            'Share events',
                            style: Theme.of(context).textTheme.titleLarge,
                          ),
                          const SizedBox(height: 12),
                          if (detail.events.isEmpty)
                            const Text('No share events returned yet.')
                          else
                            ...detail.events
                                .take(8)
                                .map(
                                  (JsonMap event) => Padding(
                                    padding: const EdgeInsets.only(bottom: 12),
                                    child: GtexListTile(
                                      title: stringValue(
                                        event['event_type'],
                                        fallback: 'Share event',
                                      ),
                                      subtitle: event.entries
                                          .take(4)
                                          .map(
                                            (MapEntry<String, Object?> entry) =>
                                                '${entry.key}: ${entry.value}',
                                          )
                                          .join(' | '),
                                      tone: GtexSurfaceTone.info,
                                    ),
                                  ),
                                ),
                        ],
                      ),
                    ),
                loading: () => const Center(child: CircularProgressIndicator()),
                error:
                    (Object error, StackTrace stackTrace) =>
                        Text(AppFeedback.messageFor(error)),
              );
            },
          ),
        );
      },
    );
  }

  Future<void> _buyShares(
    BuildContext context,
    WidgetRef ref,
    PlayerShareSummary item,
  ) async {
    final TextEditingController controller = TextEditingController(text: '1');
    final int? count = await showDialog<int>(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: Text('Buy ${item.playerName} shares'),
          content: TextField(
            controller: controller,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: 'Share count'),
          ),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed:
                  () => Navigator.of(
                    context,
                  ).pop(int.tryParse(controller.text.trim()) ?? 1),
              child: const Text('Buy'),
            ),
          ],
        );
      },
    );
    if (count == null) {
      return;
    }
    try {
      await ref
          .read(authedApiProvider)
          .post(
            '/players/${item.playerId}/shares/buy',
            body: <String, Object?>{'share_count': count},
          );
      ref.invalidate(marketDashboardProvider);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Bought $count share(s) of ${item.playerName}.'),
          ),
        );
      }
    } catch (error) {
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(AppFeedback.messageFor(error))));
      }
    }
  }

  Future<void> _watchlistListing(
    BuildContext context,
    WidgetRef ref,
    TransferListingSummary listing,
    ClubContext clubContext,
  ) async {
    try {
      await ref
          .read(authedApiProvider)
          .post(
            '/api/transfer-market/watchlist',
            body: <String, Object?>{
              'club_id': clubContext.id,
              'player_id': listing.playerId,
              'source': 'market',
              'discovery_score': 72,
              'metadata_json': <String, Object?>{'listing_id': listing.id},
            },
          );
      ref.invalidate(marketDashboardProvider);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('${listing.playerName} added to watchlist.')),
        );
      }
    } catch (error) {
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(AppFeedback.messageFor(error))));
      }
    }
  }

  Future<void> _placeBid(
    BuildContext context,
    WidgetRef ref,
    TransferListingSummary listing,
    ClubContext clubContext,
  ) async {
    final TextEditingController controller = TextEditingController(
      text: listing.basePrice.toStringAsFixed(0),
    );
    final double? amount = await showDialog<double>(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: Text('Bid for ${listing.playerName}'),
          content: TextField(
            controller: controller,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: 'Bid amount'),
          ),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed:
                  () => Navigator.of(
                    context,
                  ).pop(double.tryParse(controller.text.trim())),
              child: const Text('Submit bid'),
            ),
          ],
        );
      },
    );
    if (amount == null) {
      return;
    }
    try {
      await ref
          .read(authedApiProvider)
          .post(
            '/api/transfer-market/listings/${listing.id}/bids',
            body: <String, Object?>{
              'bidder_club_id': clubContext.id,
              'amount': amount,
            },
          );
      ref.invalidate(marketDashboardProvider);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Bid submitted for ${listing.playerName}.')),
        );
      }
    } catch (error) {
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(AppFeedback.messageFor(error))));
      }
    }
  }
}
