import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:gte_frontend/features/transfer_center/live_transfer_center_provider.dart';
import 'package:gte_frontend/shared/state/gtex_async_surface_state.dart';

import '../widgets/market_models.dart';
import '../widgets/market_widgets.dart';

class MarketSearchScreen extends ConsumerStatefulWidget {
  const MarketSearchScreen({super.key, this.onOpenListing});

  final ValueChanged<MarketListingViewModel>? onOpenListing;

  @override
  ConsumerState<MarketSearchScreen> createState() => _MarketSearchScreenState();
}

class _MarketSearchScreenState extends ConsumerState<MarketSearchScreen> {
  String _query = '';

  @override
  Widget build(BuildContext context) {
    final MarketAccessPolicy policy = marketAccessPolicyFromRef(ref);
    final GtexSurfaceState<List<MarketListingViewModel>> state =
        policy.isBlocked
            ? GtexBlocked<List<MarketListingViewModel>>(
              reason: policy.blockReason ?? 'Market blocked',
            )
            : _filterSurface(
              marketListingSurfaceFromAsync(
                ref.watch(transferCenterListingsProvider),
                emptyReason: 'No players match your search',
              ),
              _query,
            );

    return MarketScreenScaffold(
      title: 'Market Search',
      subtitle:
          'Filter backend transfer listings by player, club, status, or channel.',
      children: <Widget>[
        MarketRoleBanner(policy: policy),
        const SizedBox(height: 16),
        TextField(
          decoration: const InputDecoration(
            prefixIcon: Icon(Icons.search_rounded),
            labelText: 'Search backend listings',
            border: OutlineInputBorder(),
          ),
          onChanged: (String value) => setState(() => _query = value),
        ),
        const SizedBox(height: 16),
        MarketAsyncSurface<List<MarketListingViewModel>>(
          state: state,
          loadingBuilder: () => const MarketPlayerCardSkeleton(),
          dataBuilder:
              (List<MarketListingViewModel> listings) => MarketListingGrid(
                listings: listings,
                policy: policy,
                onOpenListing: widget.onOpenListing,
              ),
        ),
      ],
    );
  }
}

GtexSurfaceState<List<MarketListingViewModel>> _filterSurface(
  GtexSurfaceState<List<MarketListingViewModel>> source,
  String query,
) {
  final String normalized = query.trim().toLowerCase();
  if (normalized.isEmpty) {
    return source;
  }
  List<MarketListingViewModel> filter(List<MarketListingViewModel> listings) {
    return listings
        .where((MarketListingViewModel listing) {
          final String haystack =
              <String>[
                listing.playerName,
                listing.playerId,
                listing.position ?? '',
                listing.currentClubName ?? '',
                listing.status,
                listing.channel,
              ].join(' ').toLowerCase();
          return haystack.contains(normalized);
        })
        .toList(growable: false);
  }

  if (source is GtexData<List<MarketListingViewModel>>) {
    final List<MarketListingViewModel> filtered = filter(source.data);
    return filtered.isEmpty
        ? const GtexEmpty<List<MarketListingViewModel>>(
          reason: 'No players match your search',
        )
        : GtexData<List<MarketListingViewModel>>(data: filtered);
  }
  if (source is GtexSyncing<List<MarketListingViewModel>>) {
    return GtexSyncing<List<MarketListingViewModel>>(
      current: filter(source.current),
    );
  }
  if (source is GtexDegraded<List<MarketListingViewModel>>) {
    return GtexDegraded<List<MarketListingViewModel>>(
      current: filter(source.current),
      warning: source.warning,
    );
  }
  if (source is GtexConfirmed<List<MarketListingViewModel>>) {
    return GtexConfirmed<List<MarketListingViewModel>>(
      data: filter(source.data),
      auditRef: source.auditRef,
    );
  }
  if (source is GtexReconnecting<List<MarketListingViewModel>>) {
    return GtexReconnecting<List<MarketListingViewModel>>(
      lastKnown: source.lastKnown == null ? null : filter(source.lastKnown!),
      attempt: source.attempt,
    );
  }
  if (source is GtexPending<List<MarketListingViewModel>>) {
    return GtexPending<List<MarketListingViewModel>>(
      stale: source.stale == null ? null : filter(source.stale!),
    );
  }
  return source;
}
