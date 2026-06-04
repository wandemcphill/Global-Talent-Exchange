import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:gte_frontend/features/transfer_center/live_transfer_center_provider.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';
import 'package:gte_frontend/shared/state/gtex_async_surface_state.dart';
import 'package:gte_frontend/shared/widgets/async_state_widget.dart';
import 'package:gte_frontend/shared/widgets/gtex_async_state_view.dart';

import 'market_models.dart';

MarketAccessPolicy marketAccessPolicyFromRef(WidgetRef ref) {
  return MarketAccessPolicy.resolve(
    role: ref.watch(currentUserRoleProvider),
    authenticated: ref.watch(isAuthenticatedProvider),
    hasClubContext: ref.watch(clubContextProvider) != null,
  );
}

GtexSurfaceState<T> marketSurfaceFromAsync<T>(
  AsyncValue<T> value, {
  bool Function(T data)? isEmpty,
  String emptyReason = 'The backend returned no market records.',
}) {
  if (value.hasValue) {
    final T data = value.requireValue;
    if (isEmpty?.call(data) ?? false) {
      return GtexEmpty<T>(reason: emptyReason);
    }
    if (value.isRefreshing || value.isReloading) {
      return GtexSyncing<T>(current: data);
    }
    return GtexData<T>(data: data);
  }
  if (value.isLoading) {
    return GtexLoading<T>();
  }
  if (value.hasError) {
    return GtexError<T>(
      code: 'backend',
      message: value.error?.toString() ?? 'Market request failed.',
    );
  }
  return GtexLoading<T>();
}

GtexSurfaceState<List<MarketListingViewModel>> marketListingSurfaceFromAsync(
  AsyncValue<List<TransferCenterListingRecord>> value, {
  String emptyReason = 'No players match your search',
}) {
  final GtexSurfaceState<List<TransferCenterListingRecord>> source =
      marketSurfaceFromAsync<List<TransferCenterListingRecord>>(
        value,
        isEmpty: (List<TransferCenterListingRecord> data) => data.isEmpty,
        emptyReason: emptyReason,
      );
  return marketMapListingSurface(source);
}

GtexSurfaceState<List<MarketListingViewModel>> marketMapListingSurface(
  GtexSurfaceState<List<TransferCenterListingRecord>> source,
) {
  if (source is GtexLoading<List<TransferCenterListingRecord>>) {
    return const GtexLoading<List<MarketListingViewModel>>();
  }
  if (source is GtexEmpty<List<TransferCenterListingRecord>>) {
    return GtexEmpty<List<MarketListingViewModel>>(reason: source.reason);
  }
  if (source is GtexBlocked<List<TransferCenterListingRecord>>) {
    return GtexBlocked<List<MarketListingViewModel>>(
      reason: source.reason,
      ctaRoute: source.ctaRoute,
    );
  }
  if (source is GtexPending<List<TransferCenterListingRecord>>) {
    return GtexPending<List<MarketListingViewModel>>(
      stale: source.stale?.toMarketListings(),
    );
  }
  if (source is GtexSyncing<List<TransferCenterListingRecord>>) {
    return GtexSyncing<List<MarketListingViewModel>>(
      current: source.current.toMarketListings(),
    );
  }
  if (source is GtexReconnecting<List<TransferCenterListingRecord>>) {
    return GtexReconnecting<List<MarketListingViewModel>>(
      lastKnown: source.lastKnown?.toMarketListings(),
      attempt: source.attempt,
    );
  }
  if (source is GtexDegraded<List<TransferCenterListingRecord>>) {
    return GtexDegraded<List<MarketListingViewModel>>(
      current: source.current.toMarketListings(),
      warning: source.warning,
    );
  }
  if (source is GtexConfirmed<List<TransferCenterListingRecord>>) {
    return GtexConfirmed<List<MarketListingViewModel>>(
      data: source.data.toMarketListings(),
      auditRef: source.auditRef,
    );
  }
  if (source is GtexError<List<TransferCenterListingRecord>>) {
    return GtexError<List<MarketListingViewModel>>(
      code: source.code,
      message: source.message,
    );
  }
  if (source is GtexData<List<TransferCenterListingRecord>>) {
    return GtexData<List<MarketListingViewModel>>(
      data: source.data.toMarketListings(),
    );
  }
  return const GtexLoading<List<MarketListingViewModel>>();
}

extension MarketTransferCenterRecordListMap
    on List<TransferCenterListingRecord> {
  List<MarketListingViewModel> toMarketListings() {
    return map(MarketListingViewModel.fromRecord).toList(growable: false);
  }
}

class MarketScreenScaffold extends StatelessWidget {
  const MarketScreenScaffold({
    super.key,
    required this.title,
    required this.subtitle,
    required this.children,
    this.actions = const <Widget>[],
  });

  final String title;
  final String subtitle;
  final List<Widget> children;
  final List<Widget> actions;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(title), actions: actions),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: <Widget>[
            Text(
              subtitle,
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 20),
            ...children,
          ],
        ),
      ),
    );
  }
}

class MarketAsyncSurface<T> extends StatelessWidget {
  const MarketAsyncSurface({
    super.key,
    required this.state,
    required this.dataBuilder,
    this.loadingBuilder,
    this.emptyTitle = 'No players match your search',
    this.emptyMessage = 'Reset filters or wait for the backend listing feed.',
    this.retry,
  });

  final GtexSurfaceState<T> state;
  final Widget Function(T data) dataBuilder;
  final Widget Function()? loadingBuilder;
  final String emptyTitle;
  final String emptyMessage;
  final VoidCallback? retry;

  @override
  Widget build(BuildContext context) {
    return AsyncStateWidget<T>(
      state: state,
      retry: retry,
      onLoading:
          loadingBuilder ??
          () => const GtexAsyncStateView.loading(
            title: 'Loading market data',
            message: 'Fetching backend transfer listings and bid state.',
          ),
      onEmpty:
          (String? reason) => GtexAsyncStateView.empty(
            title: emptyTitle,
            message: reason ?? emptyMessage,
            actionLabel: retry == null ? null : 'Retry',
            onAction: retry,
          ),
      onBlocked:
          (String reason, String? ctaRoute) => GtexAsyncStateView.blocked(
            title: reason,
            message:
                ctaRoute == null
                    ? 'Market actions remain unavailable for this session.'
                    : 'Continue through $ctaRoute to restore access.',
          ),
      onPending: (T? stale) {
        if (stale == null) {
          return const GtexAsyncStateView.pending(
            title: 'Bid update pending',
            message: 'Waiting for the backend to confirm this market action.',
          );
        }
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            const MarketNoticeBanner(
              title: 'Bid update pending',
              message: 'Actions are disabled until backend confirmation lands.',
              icon: Icons.schedule_rounded,
            ),
            const SizedBox(height: 12),
            dataBuilder(stale),
          ],
        );
      },
      onSyncing:
          (T current) => Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              const LinearProgressIndicator(),
              const SizedBox(height: 12),
              const MarketNoticeBanner(
                title: 'Syncing latest market data',
                message:
                    'Existing backend records remain visible while syncing.',
                icon: Icons.sync_rounded,
              ),
              const SizedBox(height: 12),
              dataBuilder(current),
            ],
          ),
      onReconnecting: (T? lastKnown, int attempt) {
        final Widget banner = MarketNoticeBanner(
          title: 'Reconnecting market feed',
          message:
              'Realtime connection attempt $attempt is in progress. Last-known backend data is marked stale.',
          icon: Icons.wifi_find_rounded,
        );
        if (lastKnown == null) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              banner,
              const SizedBox(height: 12),
              const GtexAsyncStateView.reconnecting(
                title: 'Waiting for last-known data',
              ),
            ],
          );
        }
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            banner,
            const SizedBox(height: 12),
            Opacity(opacity: 0.7, child: dataBuilder(lastKnown)),
          ],
        );
      },
      onDegraded:
          (T current, String warning) => Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              MarketNoticeBanner(
                title: 'Market data may be delayed',
                message: warning,
                icon: Icons.warning_amber_rounded,
              ),
              const SizedBox(height: 12),
              dataBuilder(current),
            ],
          ),
      onConfirmed:
          (T data, String? auditRef) => Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              MarketNoticeBanner(
                title: 'Confirmed',
                message:
                    auditRef == null
                        ? 'Backend confirmed the market action.'
                        : 'Backend confirmed the market action. Audit ref: $auditRef',
                icon: Icons.check_circle_rounded,
              ),
              const SizedBox(height: 12),
              dataBuilder(data),
            ],
          ),
      onError:
          (String code, String message, VoidCallback retryCallback) =>
              GtexAsyncStateView.error(
                title: 'Market error $code',
                message: message,
                actionLabel: 'Retry',
                onAction: retryCallback,
              ),
      onData: dataBuilder,
    );
  }
}

class MarketNoticeBanner extends StatelessWidget {
  const MarketNoticeBanner({
    super.key,
    required this.title,
    required this.message,
    required this.icon,
  });

  final String title;
  final String message;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    final ColorScheme scheme = Theme.of(context).colorScheme;
    return DecoratedBox(
      decoration: BoxDecoration(
        color: scheme.surfaceContainerHighest.withValues(alpha: 0.78),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: scheme.outlineVariant),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Icon(icon, size: 20, color: scheme.primary),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(title, style: Theme.of(context).textTheme.titleSmall),
                  const SizedBox(height: 4),
                  Text(message, style: Theme.of(context).textTheme.bodySmall),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class MarketRoleBanner extends StatelessWidget {
  const MarketRoleBanner({super.key, required this.policy});

  final MarketAccessPolicy policy;

  @override
  Widget build(BuildContext context) {
    if (!policy.isBlocked && !policy.isScout && !policy.isManager) {
      return MarketNoticeBanner(
        title: policy.roleLabel,
        message: 'Owner market access is active for this club context.',
        icon: Icons.verified_rounded,
      );
    }
    return MarketNoticeBanner(
      title: policy.roleLabel,
      message:
          policy.blockReason ??
          policy.actionBlockReason ??
          policy.checkoutBlockReason ??
          'Market access is limited for this role.',
      icon: policy.isBlocked ? Icons.lock_rounded : Icons.info_rounded,
    );
  }
}

class MarketListingGrid extends StatelessWidget {
  const MarketListingGrid({
    super.key,
    required this.listings,
    required this.policy,
    this.onOpenListing,
  });

  final List<MarketListingViewModel> listings;
  final MarketAccessPolicy policy;
  final ValueChanged<MarketListingViewModel>? onOpenListing;

  @override
  Widget build(BuildContext context) {
    if (listings.isEmpty) {
      return const GtexAsyncStateView.empty(
        title: 'No players match your search',
        message: 'The backend returned zero open transfer listings.',
      );
    }
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool wide = constraints.maxWidth >= 780;
        return GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: listings.length,
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: wide ? 2 : 1,
            crossAxisSpacing: 12,
            mainAxisSpacing: 12,
            mainAxisExtent: 250,
          ),
          itemBuilder: (BuildContext context, int index) {
            return MarketPlayerCard(
              listing: listings[index],
              policy: policy,
              onOpen:
                  onOpenListing == null
                      ? null
                      : () => onOpenListing!(listings[index]),
            );
          },
        );
      },
    );
  }
}

class MarketPlayerCard extends StatelessWidget {
  const MarketPlayerCard({
    super.key,
    required this.listing,
    required this.policy,
    this.onOpen,
    this.onAddToBasket,
    this.onPlaceBid,
  });

  final MarketListingViewModel listing;
  final MarketAccessPolicy policy;
  final VoidCallback? onOpen;
  final VoidCallback? onAddToBasket;
  final VoidCallback? onPlaceBid;

  @override
  Widget build(BuildContext context) {
    final ColorScheme scheme = Theme.of(context).colorScheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Container(
                  width: 48,
                  height: 48,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: scheme.primaryContainer,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(
                    Icons.person_search_rounded,
                    color: scheme.onPrimaryContainer,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        listing.playerName,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        [
                          listing.position ?? 'Position not returned',
                          listing.currentClubName ?? 'Club not returned',
                        ].join(' | '),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
                MarketStatusChip(label: listing.status),
              ],
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: <Widget>[
                MarketMetricPill(
                  label: 'Base',
                  value: marketMoney(listing.basePrice),
                ),
                MarketMetricPill(
                  label: 'Current bid',
                  value: marketMoney(listing.currentHighestBid),
                ),
                MarketMetricPill(label: 'Bids', value: '${listing.bidCount}'),
                MarketMetricPill(
                  label: 'Window',
                  value: marketDurationLabel(listing.timeRemaining),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              listing.marketSignal,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const Spacer(),
            MarketActionBar(
              policy: policy,
              compact: true,
              onView: onOpen,
              onAddToBasket: onAddToBasket,
              onPlaceBid: onPlaceBid,
            ),
          ],
        ),
      ),
    );
  }
}

class MarketActionBar extends StatelessWidget {
  const MarketActionBar({
    super.key,
    required this.policy,
    this.onView,
    this.onAddToBasket,
    this.onPlaceBid,
    this.onAcceptBid,
    this.compact = false,
  });

  final MarketAccessPolicy policy;
  final VoidCallback? onView;
  final VoidCallback? onAddToBasket;
  final VoidCallback? onPlaceBid;
  final VoidCallback? onAcceptBid;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    if (policy.isBlocked || policy.isScout) {
      return MarketNoticeBanner(
        title: policy.isScout ? 'Scout read-only access' : 'Market blocked',
        message:
            policy.blockReason ??
            policy.actionBlockReason ??
            'No market action buttons are available.',
        icon: Icons.lock_rounded,
      );
    }

    final List<Widget> buttons = <Widget>[
      OutlinedButton.icon(
        onPressed: onView,
        icon: const Icon(Icons.open_in_new_rounded),
        label: const Text('View'),
      ),
      OutlinedButton.icon(
        onPressed: policy.canUseBasket ? onAddToBasket : null,
        icon: const Icon(Icons.playlist_add_check_rounded),
        label: const Text('Basket'),
      ),
      FilledButton.icon(
        onPressed: policy.canBid ? onPlaceBid : null,
        icon: const Icon(Icons.gavel_rounded),
        label: const Text('Bid'),
      ),
      if (onAcceptBid != null)
        FilledButton.tonalIcon(
          onPressed: policy.canActOnBids ? onAcceptBid : null,
          icon: const Icon(Icons.handshake_rounded),
          label: const Text('Accept'),
        ),
    ];

    if (compact) {
      return Wrap(
        spacing: 8,
        runSpacing: 8,
        children: buttons.take(3).toList(),
      );
    }
    return Wrap(spacing: 10, runSpacing: 10, children: buttons);
  }
}

class MarketMetricPill extends StatelessWidget {
  const MarketMetricPill({super.key, required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final ColorScheme scheme = Theme.of(context).colorScheme;
    return DecoratedBox(
      decoration: BoxDecoration(
        color: scheme.surfaceContainerHigh,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: scheme.outlineVariant),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(label, style: Theme.of(context).textTheme.labelSmall),
            const SizedBox(height: 2),
            Text(value, style: Theme.of(context).textTheme.labelLarge),
          ],
        ),
      ),
    );
  }
}

class MarketStatusChip extends StatelessWidget {
  const MarketStatusChip({super.key, required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Chip(
      label: Text(label.isEmpty ? 'unknown' : label),
      avatar: const Icon(Icons.circle, size: 10),
    );
  }
}

class MarketBidStatusBadge extends StatelessWidget {
  const MarketBidStatusBadge({super.key, required this.status});

  final MarketBidLifecycleStatus status;

  @override
  Widget build(BuildContext context) {
    final ColorScheme scheme = Theme.of(context).colorScheme;
    final Color color = switch (status) {
      MarketBidLifecycleStatus.pending => scheme.primary,
      MarketBidLifecycleStatus.counter => scheme.tertiary,
      MarketBidLifecycleStatus.accepted => Colors.greenAccent,
      MarketBidLifecycleStatus.rejected => scheme.error,
      MarketBidLifecycleStatus.withdrawn => scheme.outline,
      MarketBidLifecycleStatus.unknown => scheme.onSurfaceVariant,
    };
    return DecoratedBox(
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: 0.5)),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        child: Text(
          status.label,
          style: Theme.of(context).textTheme.labelMedium?.copyWith(
            color: color,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
    );
  }
}

class BidEventTimeline extends StatelessWidget {
  const BidEventTimeline({super.key, required this.bids});

  final List<MarketBidViewModel> bids;

  @override
  Widget build(BuildContext context) {
    if (bids.isEmpty) {
      return const GtexAsyncStateView.empty(
        title: 'No backend bid events',
        message: 'The listing DTO did not include any bidder rows yet.',
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: bids
          .map(
            (MarketBidViewModel bid) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          MarketBidStatusBadge(status: bid.status),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: <Widget>[
                                Text(
                                  bid.clubName,
                                  style: Theme.of(context).textTheme.titleSmall,
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  '${marketOptionalMoney(bid.amount)} | ${marketDateLabel(bid.timestamp)}',
                                  style: Theme.of(context).textTheme.bodySmall,
                                ),
                              ],
                            ),
                          ),
                          if (bid.isHighest)
                            const Icon(Icons.workspace_premium_rounded),
                        ],
                      ),
                      const SizedBox(height: 12),
                      MarketReservationPanel(bid: bid),
                    ],
                  ),
                ),
              ),
            ),
          )
          .toList(growable: false),
    );
  }
}

class MarketReservationPanel extends StatelessWidget {
  const MarketReservationPanel({super.key, required this.bid});

  final MarketBidViewModel bid;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerHigh,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'Reservation truth',
              style: Theme.of(context).textTheme.labelLarge,
            ),
            const SizedBox(height: 8),
            Text(
              'Status: ${bid.walletReservationStatus ?? 'Reservation not reported by backend'}',
            ),
            Text(
              'Reserved amount: ${marketOptionalMoney(bid.walletReservedAmount)}',
            ),
            Text(
              'Reference: ${bid.walletReservationReference ?? 'Reservation reference not reported by backend'}',
            ),
          ],
        ),
      ),
    );
  }
}

class CheckoutReadinessPanel extends StatelessWidget {
  const CheckoutReadinessPanel({
    super.key,
    required this.policy,
    required this.listings,
  });

  final MarketAccessPolicy policy;
  final List<MarketListingViewModel> listings;

  @override
  Widget build(BuildContext context) {
    if (!policy.canCheckout) {
      return GtexAsyncStateView.blocked(
        title: policy.checkoutBlockReason ?? 'Checkout blocked',
        message:
            policy.isManager
                ? 'Club managers can prepare bids, but owners must approve checkout.'
                : 'This role cannot complete transfer checkout.',
      );
    }
    if (listings.isEmpty) {
      return const GtexAsyncStateView.empty(
        title: 'No backend-confirmed basket is active',
        message:
            'Checkout readiness needs basket items returned by the market backend.',
      );
    }
    final int blocked =
        listings
            .where((MarketListingViewModel item) => item.status != 'open')
            .length;
    return MarketNoticeBanner(
      title:
          blocked == 0
              ? 'Checkout ready for owner review'
              : 'Checkout has blockers',
      message:
          blocked == 0
              ? 'Open backend listings can proceed when the owner confirms.'
              : '$blocked listing(s) are no longer open in the backend feed.',
      icon: blocked == 0 ? Icons.verified_user_rounded : Icons.block_rounded,
    );
  }
}

class MarketPlayerCardSkeleton extends StatelessWidget {
  const MarketPlayerCardSkeleton({super.key});

  @override
  Widget build(BuildContext context) {
    final Color color = Theme.of(context).colorScheme.surfaceContainerHighest;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: List<Widget>.generate(
        4,
        (int index) => Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: DecoratedBox(
            decoration: BoxDecoration(
              color: color,
              borderRadius: BorderRadius.circular(8),
            ),
            child: const SizedBox(height: 88),
          ),
        ),
      ),
    );
  }
}
