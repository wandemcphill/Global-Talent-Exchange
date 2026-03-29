import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/app_feedback.dart';
import '../../core/constants/app_spacing.dart';
import '../../features/shared/data/gte_feature_support.dart';
import '../../shared/models/auth_session.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/providers/auth_provider.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';
import 'live_market_provider.dart';

class TransferMarketScreen extends ConsumerWidget {
  const TransferMarketScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<MarketDashboardData> marketValue = ref.watch(
      marketDashboardProvider,
    );
    return AppPageLayout(
      title: 'Market',
      subtitle:
          'Player shares, transfer listings, wallet state, and compliance are segmented and live-backed. No local market ticker is left on the shipped path.',
      trailing: DataSourceBadge(
        status:
            marketValue.hasError
                ? DataSourceStatus.blocked
                : DataSourceStatus.live,
      ),
      children: <Widget>[
        Card(
          child: Padding(
            padding: const EdgeInsets.all(spacingLG),
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
        ),
        marketValue.when(
          data: (MarketDashboardData market) => _MarketBody(data: market),
          loading:
              () => const Center(
                child: Padding(
                  padding: EdgeInsets.all(spacingLG),
                  child: CircularProgressIndicator(),
                ),
              ),
          error:
              (Object error, StackTrace stackTrace) => _BlockedCard(
                title: 'Market is blocked',
                message: AppFeedback.messageFor(error),
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
        _SectionCard(
          title: 'Wallet & Compliance',
          subtitle:
              data.wallet == null
                  ? authenticated
                      ? 'Wallet or compliance endpoints are blocked for this session.'
                      : 'Sign in to load live wallet and compliance state.'
                  : data.wallet!.complianceMessage,
          child: Wrap(
            spacing: spacingSM,
            runSpacing: spacingSM,
            children: <Widget>[
              _MetricChip(
                label: 'Coin balance',
                value: data.wallet?.coinBalance.toStringAsFixed(2) ?? 'Blocked',
              ),
              _MetricChip(
                label: 'Credit balance',
                value:
                    data.wallet?.creditBalance.toStringAsFixed(2) ?? 'Blocked',
              ),
              _MetricChip(
                label: 'Total equity',
                value: data.wallet?.totalEquity.toStringAsFixed(2) ?? 'Blocked',
              ),
              _MetricChip(
                label: 'Trade',
                value:
                    data.wallet == null
                        ? 'Blocked'
                        : data.wallet!.canTradeMarket
                        ? 'Enabled'
                        : 'Blocked',
              ),
            ],
          ),
        ),
        if (data.warnings.isNotEmpty) ...<Widget>[
          const SizedBox(height: spacingMD),
          _BlockedCard(
            title: 'Live warnings',
            message: data.warnings.join('\n'),
          ),
        ],
        const SizedBox(height: spacingMD),
        _SectionCard(
          title: 'Player Shares',
          subtitle:
              'Discovery is fed by /players/real-universe and tradability only appears when /players/{player_id}/shares/market exists.',
          child: Column(
            children: data.playerShares
                .map(
                  (PlayerShareSummary item) => ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(item.playerName),
                    subtitle: Text(
                      '${item.position ?? 'N/A'} | ${item.currentClubName ?? 'No club'} | ${item.marketMessage}',
                    ),
                    trailing: Wrap(
                      spacing: spacingSM,
                      children: <Widget>[
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
                )
                .toList(growable: false),
          ),
        ),
        const SizedBox(height: spacingMD),
        _SectionCard(
          title: 'Transfer Listings',
          subtitle:
              clubContext == null
                  ? 'Bidding and watchlisting are blocked because this session has no verified club context.'
                  : 'Transfer listings are live. Actions use the club context carried by the active session.',
          child: Column(
            children: data.transferListings
                .map(
                  (TransferListingSummary listing) => ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(listing.playerName),
                    subtitle: Text(
                      '${listing.status} | bid ${listing.currentHighestBid.toStringAsFixed(0)} | watchlist ${listing.watchlistCount}',
                    ),
                    trailing: Wrap(
                      spacing: spacingSM,
                      children: <Widget>[
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
                )
                .toList(growable: false),
          ),
        ),
        if (data.holdings.isNotEmpty) ...<Widget>[
          const SizedBox(height: spacingMD),
          _SectionCard(
            title: 'Share Holdings',
            subtitle: 'Live holdings from /players/me/shares/holdings.',
            child: Column(
              children: data.holdings
                  .map(
                    (PlayerShareHoldingSummary holding) => ListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text(holding.playerId),
                      subtitle: Text(
                        'Shares ${holding.shareCount} | Avg cost ${holding.averageCostCoin.toStringAsFixed(2)} | Dividends ${holding.dividendsEarnedCoin.toStringAsFixed(2)}',
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
          padding: const EdgeInsets.all(spacingLG),
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
                          const SizedBox(height: spacingSM),
                          Text(
                            detail.playerDetail.entries
                                .take(12)
                                .map(
                                  (MapEntry<String, Object?> entry) =>
                                      '${entry.key}: ${entry.value}',
                                )
                                .join('\n'),
                          ),
                          const SizedBox(height: spacingMD),
                          Text(
                            'Share events',
                            style: Theme.of(context).textTheme.titleLarge,
                          ),
                          const SizedBox(height: spacingSM),
                          if (detail.events.isEmpty)
                            const Text('No share events returned yet.')
                          else
                            ...detail.events
                                .take(8)
                                .map(
                                  (JsonMap event) => ListTile(
                                    dense: true,
                                    contentPadding: EdgeInsets.zero,
                                    title: Text(
                                      stringValue(
                                        event['event_type'],
                                        fallback: 'Share event',
                                      ),
                                    ),
                                    subtitle: Text(
                                      event.entries
                                          .take(4)
                                          .map(
                                            (MapEntry<String, Object?> entry) =>
                                                '${entry.key}: ${entry.value}',
                                          )
                                          .join(' | '),
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

class _SectionCard extends StatelessWidget {
  const _SectionCard({
    required this.title,
    required this.subtitle,
    required this.child,
  });

  final String title;
  final String subtitle;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(spacingLG),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(title, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: spacingXS),
            Text(subtitle),
            const SizedBox(height: spacingMD),
            child,
          ],
        ),
      ),
    );
  }
}

class _MetricChip extends StatelessWidget {
  const _MetricChip({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Chip(label: Text('$label: $value'));
  }
}

class _BlockedCard extends StatelessWidget {
  const _BlockedCard({required this.title, required this.message});

  final String title;
  final String message;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(spacingLG),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(title, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: spacingSM),
            Text(message),
          ],
        ),
      ),
    );
  }
}
