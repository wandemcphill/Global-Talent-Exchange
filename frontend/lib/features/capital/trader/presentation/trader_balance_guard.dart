import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:gte_frontend/shared/state/gtex_async_surface_state.dart';

const String traderBalanceUnavailableReason =
    'Balance data unavailable - sync in progress.';

class TraderBalancePayload {
  const TraderBalancePayload({
    required this.available,
    this.reserved,
    required this.currency,
    this.lastSyncedAt,
  });

  final double? available;
  final double? reserved;
  final String currency;
  final DateTime? lastSyncedAt;
}

class TraderBalanceSnapshot {
  const TraderBalanceSnapshot({
    required this.available,
    this.reserved,
    required this.currency,
    this.lastSyncedAt,
  });

  final double available;
  final double? reserved;
  final String currency;
  final DateTime? lastSyncedAt;
}

final traderBalanceSurfaceProvider = Provider.family<
  GtexSurfaceState<TraderBalanceSnapshot>,
  TraderBalancePayload
>((Ref ref, TraderBalancePayload payload) {
  return traderBalanceSurfaceFromBackend(payload);
});

GtexSurfaceState<TraderBalanceSnapshot> traderBalanceSurfaceFromBackend(
  TraderBalancePayload payload,
) {
  final double? available = payload.available;
  if (available == null) {
    return const GtexBlocked<TraderBalanceSnapshot>(
      reason: traderBalanceUnavailableReason,
    );
  }

  final String currency = payload.currency.trim();
  if (currency.isEmpty) {
    return const GtexBlocked<TraderBalanceSnapshot>(
      reason: 'Balance currency unavailable - sync in progress.',
    );
  }

  return GtexData<TraderBalanceSnapshot>(
    data: TraderBalanceSnapshot(
      available: available,
      reserved: payload.reserved,
      currency: currency,
      lastSyncedAt: payload.lastSyncedAt,
    ),
  );
}

bool traderBalanceAllowsActions(GtexSurfaceState<TraderBalanceSnapshot> state) {
  return state is GtexData<TraderBalanceSnapshot> ||
      state is GtexConfirmed<TraderBalanceSnapshot>;
}
