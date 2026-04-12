import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/app_feedback.dart';
import '../../data/gte_api_repository.dart';
import '../../features/shared/data/gte_feature_support.dart';
import '../../navigation/app_destinations.dart';
import '../../providers/gte_exchange_controller.dart';
import '../../screens/wallet/gte_policy_compliance_center_screen.dart';
import '../../shared/models/auth_session.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/providers/auth_provider.dart';
import '../../shared/providers/live_clients_provider.dart';
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
    final String walletMetricValue;
    final String walletMetricSupport;
    final GtexSurfaceTone walletMetricTone;
    if (snapshot == null) {
      walletMetricValue = '...';
      walletMetricSupport = 'Checking wallet and compliance state';
      walletMetricTone = GtexSurfaceTone.info;
    } else if (!snapshot.authenticated) {
      walletMetricValue = 'Sign in';
      walletMetricSupport = 'Preview mode only';
      walletMetricTone = GtexSurfaceTone.warning;
    } else if (snapshot.wallet == null) {
      walletMetricValue = 'Retry';
      walletMetricSupport = 'Wallet and compliance checks did not complete';
      walletMetricTone = GtexSurfaceTone.warning;
    } else if (!snapshot.wallet!.canTradeMarket) {
      walletMetricValue = 'Compliance';
      walletMetricSupport = snapshot.wallet!.complianceMessage;
      walletMetricTone = GtexSurfaceTone.warning;
    } else {
      walletMetricValue = snapshot.wallet!.totalEquity.toStringAsFixed(0);
      walletMetricSupport = snapshot.wallet!.complianceMessage;
      walletMetricTone = GtexSurfaceTone.success;
    }
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
                  snapshot == null
                      ? '...'
                      : '${snapshot.tradablePlayerShares.length}',
              support:
                  snapshot == null
                      ? 'Tradable inventory loading'
                      : snapshot.upcomingPlayerShares.isEmpty
                      ? 'Issued player-share markets'
                      : '${snapshot.upcomingPlayerShares.length} upcoming markets parked separately',
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
              value: walletMetricValue,
              support: walletMetricSupport,
              tone: walletMetricTone,
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
    final List<PlayerShareSummary> tradableShares = data.tradablePlayerShares;
    final List<PlayerShareSummary> upcomingShares = data.upcomingPlayerShares;
    final bool walletUnavailable = authenticated && data.wallet == null;
    final bool canTradeMarket = data.wallet?.canTradeMarket == true;
    final bool showAccessPanel =
        !authenticated ||
        walletUnavailable ||
        data.wallet?.canTradeMarket == false;
    final List<String> supplementalWarnings = data.warnings
        .where(
          (String warning) =>
              !warning.startsWith('Wallet/compliance unavailable:'),
        )
        .toList(growable: false);
    return Column(
      children: <Widget>[
        if (showAccessPanel) ...<Widget>[
          _MarketAccessPanel(
            authenticated: authenticated,
            data: data,
            onSignIn: () => context.push(AppRoutes.profileLogin),
            onRetry: () => ref.invalidate(marketDashboardProvider),
            onOpenComplianceCenter: () => _openComplianceCenter(context, ref),
          ),
          const SizedBox(height: 24),
        ],
        GtexSectionPanel(
          eyebrow: 'WALLET + COMPLIANCE',
          title: 'Wallet & Compliance',
          subtitle:
              !authenticated
                  ? 'Preview mode is active. Sign in to load live wallet and compliance state.'
                  : data.wallet == null
                  ? 'Live wallet and compliance checks did not complete. Retry the market desk or re-authenticate.'
                  : data.wallet!.canTradeMarket
                  ? data.wallet!.complianceMessage
                  : 'Trading is paused until compliance clears this account.',
          child: Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              GtexStatTile(
                label: 'Coin balance',
                value:
                    !authenticated
                        ? 'Sign in'
                        : data.wallet == null
                        ? 'Unavailable'
                        : data.wallet!.coinBalance.toStringAsFixed(2),
                support:
                    !authenticated
                        ? 'Guest preview'
                        : data.wallet == null
                        ? 'Live wallet feed missing'
                        : 'Spendable market coin',
                tone:
                    !authenticated || data.wallet == null
                        ? GtexSurfaceTone.warning
                        : GtexSurfaceTone.live,
              ),
              GtexStatTile(
                label: 'Credit balance',
                value:
                    !authenticated
                        ? 'Sign in'
                        : data.wallet == null
                        ? 'Unavailable'
                        : data.wallet!.creditBalance.toStringAsFixed(2),
                support:
                    !authenticated
                        ? 'Guest preview'
                        : data.wallet == null
                        ? 'Live wallet feed missing'
                        : 'Available account credit',
                tone:
                    !authenticated || data.wallet == null
                        ? GtexSurfaceTone.warning
                        : GtexSurfaceTone.info,
              ),
              GtexStatTile(
                label: 'Total equity',
                value:
                    !authenticated
                        ? 'Sign in'
                        : data.wallet == null
                        ? 'Unavailable'
                        : data.wallet!.totalEquity.toStringAsFixed(2),
                support:
                    !authenticated
                        ? 'Authentication required'
                        : data.wallet == null
                        ? 'Live wallet feed missing'
                        : 'Live wallet equity',
                tone:
                    !authenticated || data.wallet == null
                        ? GtexSurfaceTone.warning
                        : GtexSurfaceTone.success,
              ),
              GtexStatTile(
                label: 'Trade',
                value:
                    !authenticated
                        ? 'Sign in'
                        : data.wallet == null
                        ? 'Retry desk'
                        : data.wallet!.canTradeMarket
                        ? 'Enabled'
                        : 'Compliance required',
                support:
                    !authenticated
                        ? 'Authentication required'
                        : data.wallet == null
                        ? 'No live compliance result'
                        : data.wallet!.complianceMessage,
                tone:
                    canTradeMarket
                        ? GtexSurfaceTone.success
                        : GtexSurfaceTone.warning,
              ),
            ],
          ),
        ),
        if (supplementalWarnings.isNotEmpty) ...<Widget>[
          const SizedBox(height: 24),
          GteStatePanel(
            title: 'Additional live warnings',
            message: supplementalWarnings.join('\n'),
            icon: Icons.warning_amber_rounded,
            accentColor: Theme.of(context).colorScheme.tertiary,
          ),
        ],
        const SizedBox(height: 24),
        GtexSectionPanel(
          eyebrow: 'SHARES',
          title: 'Player Shares',
          subtitle:
              'Tradable share markets appear first. Real players without an issued share market are separated below as upcoming inventory.',
          child: Column(
            children:
                tradableShares.isEmpty
                    ? const <Widget>[
                      _MarketEmptyState(
                        title: 'No tradable share markets are live yet',
                        message:
                            'The market desk is connected, but none of the surfaced players currently have an issued share market.',
                        icon: Icons.candlestick_chart_rounded,
                      ),
                    ]
                    : tradableShares
                        .map(
                          (PlayerShareSummary item) => Padding(
                            padding: const EdgeInsets.only(bottom: 12),
                            child: _buildTradableShareTile(
                              context,
                              ref,
                              item,
                              authenticated: authenticated,
                              canTradeMarket: canTradeMarket,
                            ),
                          ),
                        )
                        .toList(growable: false),
          ),
        ),
        if (upcomingShares.isNotEmpty) ...<Widget>[
          const SizedBox(height: 24),
          GtexSectionPanel(
            eyebrow: 'UPCOMING',
            title: 'Upcoming share markets',
            subtitle:
                'Real players discovered from the live universe before a share market has been issued.',
            child: Column(
              children: upcomingShares
                  .map(
                    (PlayerShareSummary item) => Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: _buildUpcomingShareTile(context, ref, item),
                    ),
                  )
                  .toList(growable: false),
            ),
          ),
        ],
        const SizedBox(height: 24),
        GtexSectionPanel(
          eyebrow: 'TRANSFERS',
          title: 'Transfer Listings',
          subtitle:
              clubContext == null
                  ? 'Live listings stay readable while transfer actions remain gated to verified club sessions.'
                  : 'Transfer listings are live. Actions use the club context carried by the active session.',
          child: Column(
            children: <Widget>[
              if (clubContext == null) ...<Widget>[
                _TransferActionGate(
                  authenticated: authenticated,
                  onSignIn: () => context.push(AppRoutes.profileLogin),
                  onOpenProfile: () => context.push(AppRoutes.profile),
                ),
                const SizedBox(height: 16),
              ],
              if (data.transferListings.isEmpty)
                const _MarketEmptyState(
                  title: 'No live transfer listings are open right now',
                  message:
                      'The transfer desk is mounted, but there are no active listings to inspect yet.',
                  icon: Icons.swap_horiz_rounded,
                )
              else
                ...data.transferListings.map(
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
                ),
            ],
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

  Widget _buildTradableShareTile(
    BuildContext context,
    WidgetRef ref,
    PlayerShareSummary item, {
    required bool authenticated,
    required bool canTradeMarket,
  }) {
    return GtexListTile(
      title: item.playerName,
      subtitle:
          '${item.position ?? 'N/A'} | ${item.currentClubName ?? 'No club'} | ${item.marketMessage}',
      leadingIcon: Icons.person_search_rounded,
      tone: GtexSurfaceTone.live,
      trailing: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: <Widget>[
          GtexPill(
            label: '${item.sharePriceCoin!.toStringAsFixed(0)} coin',
            tone: GtexSurfaceTone.live,
          ),
          TextButton(
            onPressed: () => _openPlayerDetail(context, ref, item),
            child: const Text('Detail'),
          ),
          FilledButton(
            onPressed:
                authenticated && canTradeMarket
                    ? () => _buyShares(context, ref, item)
                    : null,
            child: const Text('Buy'),
          ),
        ],
      ),
    );
  }

  Widget _buildUpcomingShareTile(
    BuildContext context,
    WidgetRef ref,
    PlayerShareSummary item,
  ) {
    return GtexListTile(
      title: item.playerName,
      subtitle:
          '${item.position ?? 'N/A'} | ${item.currentClubName ?? 'No club'} | ${item.marketMessage}',
      leadingIcon: Icons.schedule_rounded,
      tone: GtexSurfaceTone.warning,
      trailing: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: <Widget>[
          const GtexPill(
            label: 'Awaiting issuance',
            tone: GtexSurfaceTone.warning,
          ),
          TextButton(
            onPressed: () => _openPlayerDetail(context, ref, item),
            child: const Text('Detail'),
          ),
        ],
      ),
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
      if (!context.mounted) {
        return;
      }
      await _handleProtectedActionError(context, ref, error);
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
      if (!context.mounted) {
        return;
      }
      await _handleProtectedActionError(context, ref, error);
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
      if (!context.mounted) {
        return;
      }
      await _handleProtectedActionError(context, ref, error);
    }
  }

  Future<void> _openComplianceCenter(
    BuildContext context,
    WidgetRef ref,
  ) async {
    final GteExchangeController controller = GteExchangeController(
      api: ref.read(exchangeApiClientProvider),
    );
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (_) => GtePolicyComplianceCenterScreen(controller: controller),
      ),
    );
    ref.invalidate(marketDashboardProvider);
  }

  Future<void> _handleProtectedActionError(
    BuildContext context,
    WidgetRef ref,
    Object error,
  ) async {
    if (error is GteApiException &&
        error.type == GteApiErrorType.unauthorized) {
      await ref.read(exchangeApiClientProvider).logout();
      await ref.read(appSessionControllerProvider.notifier).clear();
      if (!context.mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Your session expired. Sign in again to continue.'),
        ),
      );
      context.push(AppRoutes.profileLogin);
      return;
    }
    if (context.mounted) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(AppFeedback.messageFor(error))));
    }
  }
}

class _MarketAccessPanel extends StatelessWidget {
  const _MarketAccessPanel({
    required this.authenticated,
    required this.data,
    required this.onSignIn,
    required this.onRetry,
    required this.onOpenComplianceCenter,
  });

  final bool authenticated;
  final MarketDashboardData data;
  final VoidCallback onSignIn;
  final VoidCallback onRetry;
  final VoidCallback onOpenComplianceCenter;

  @override
  Widget build(BuildContext context) {
    final List<_MarketAccessIssue> issues = <_MarketAccessIssue>[
      if (!authenticated)
        const _MarketAccessIssue(
          title: 'Sign in to unlock market access',
          message:
              'Guest preview mode keeps discovery and listing browsing open, but wallet state, holdings, and executable trades stay locked until authentication succeeds.',
          icon: Icons.login_rounded,
          tone: GtexSurfaceTone.warning,
        ),
      if (authenticated && data.wallet == null)
        const _MarketAccessIssue(
          title: 'Wallet and compliance checks need attention',
          message:
              'This session is authenticated, but the live wallet and compliance calls did not complete. Retry the desk before attempting protected actions.',
          icon: Icons.sync_problem_rounded,
          tone: GtexSurfaceTone.warning,
        ),
      if (data.wallet != null && !data.wallet!.canTradeMarket)
        _MarketAccessIssue(
          title: 'Compliance action required before trading',
          message: data.wallet!.complianceMessage,
          icon: Icons.verified_user_rounded,
          tone: GtexSurfaceTone.warning,
        ),
    ];

    return GtexSectionPanel(
      eyebrow: 'ACCESS CHECK',
      title: 'Resolve market access',
      subtitle:
          'The market desk now surfaces blocked prerequisites before order actions are exposed.',
      child: Column(
        children: <Widget>[
          ...issues.map(
            (_MarketAccessIssue issue) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: GtexListTile(
                title: issue.title,
                subtitle: issue.message,
                leadingIcon: issue.icon,
                tone: issue.tone,
              ),
            ),
          ),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              if (!authenticated)
                FilledButton.icon(
                  onPressed: onSignIn,
                  icon: const Icon(Icons.login_rounded),
                  label: const Text('Sign in'),
                ),
              if (authenticated && data.wallet == null)
                FilledButton.icon(
                  onPressed: onRetry,
                  icon: const Icon(Icons.refresh_rounded),
                  label: const Text('Retry market'),
                ),
              if (data.wallet != null && !data.wallet!.canTradeMarket)
                FilledButton.icon(
                  onPressed: onOpenComplianceCenter,
                  icon: const Icon(Icons.shield_outlined),
                  label: const Text('Open compliance center'),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _TransferActionGate extends StatelessWidget {
  const _TransferActionGate({
    required this.authenticated,
    required this.onSignIn,
    required this.onOpenProfile,
  });

  final bool authenticated;
  final VoidCallback onSignIn;
  final VoidCallback onOpenProfile;

  @override
  Widget build(BuildContext context) {
    return GteStatePanel(
      title:
          authenticated
              ? 'Verified club context required for transfer actions'
              : 'Sign in to bid on transfer listings',
      message:
          authenticated
              ? 'This session is authenticated but carries no verified club. Listings remain visible, but bid and watchlist actions stay disabled until a club-backed session is active.'
              : 'Guest sessions can inspect live transfer listings, but bidding and watchlisting unlock only after sign-in with a club-backed account.',
      actionLabel: authenticated ? 'Open profile' : 'Sign in',
      onAction: authenticated ? onOpenProfile : onSignIn,
      icon: authenticated ? Icons.account_balance_rounded : Icons.login_rounded,
      accentColor:
          authenticated
              ? Theme.of(context).colorScheme.tertiary
              : Theme.of(context).colorScheme.primary,
    );
  }
}

class _MarketEmptyState extends StatelessWidget {
  const _MarketEmptyState({
    required this.title,
    required this.message,
    required this.icon,
  });

  final String title;
  final String message;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return GtexListTile(
      title: title,
      subtitle: message,
      leadingIcon: icon,
      tone: GtexSurfaceTone.neutral,
    );
  }
}

class _MarketAccessIssue {
  const _MarketAccessIssue({
    required this.title,
    required this.message,
    required this.icon,
    required this.tone,
  });

  final String title;
  final String message;
  final IconData icon;
  final GtexSurfaceTone tone;
}
