import 'package:flutter/material.dart';

enum GtexAsyncSurfaceState {
  loading,
  empty,
  blocked,
  pending,
  syncing,
  reconnecting,
  degraded,
  confirmed,
  error,
  data,
}

extension GtexAsyncSurfaceStateDefaults on GtexAsyncSurfaceState {
  String get label {
    return switch (this) {
      GtexAsyncSurfaceState.loading => 'Loading',
      GtexAsyncSurfaceState.empty => 'Empty',
      GtexAsyncSurfaceState.blocked => 'Blocked',
      GtexAsyncSurfaceState.pending => 'Pending',
      GtexAsyncSurfaceState.syncing => 'Syncing',
      GtexAsyncSurfaceState.reconnecting => 'Reconnecting',
      GtexAsyncSurfaceState.degraded => 'Degraded',
      GtexAsyncSurfaceState.confirmed => 'Confirmed',
      GtexAsyncSurfaceState.error => 'Error',
      GtexAsyncSurfaceState.data => 'Data',
    };
  }

  String get eyebrow {
    return switch (this) {
      GtexAsyncSurfaceState.loading => 'LIVE SYNC',
      GtexAsyncSurfaceState.empty => 'NO RESULTS',
      GtexAsyncSurfaceState.blocked => 'ACCESS BLOCKED',
      GtexAsyncSurfaceState.pending => 'PENDING',
      GtexAsyncSurfaceState.syncing => 'SYNCING',
      GtexAsyncSurfaceState.reconnecting => 'RECONNECTING',
      GtexAsyncSurfaceState.degraded => 'DEGRADED',
      GtexAsyncSurfaceState.confirmed => 'CONFIRMED',
      GtexAsyncSurfaceState.error => 'ERROR',
      GtexAsyncSurfaceState.data => 'DATA READY',
    };
  }

  String get title {
    return switch (this) {
      GtexAsyncSurfaceState.loading => 'Loading matchday data',
      GtexAsyncSurfaceState.empty => 'Nothing to show yet',
      GtexAsyncSurfaceState.blocked => 'This surface is blocked',
      GtexAsyncSurfaceState.pending => 'Waiting for confirmation',
      GtexAsyncSurfaceState.syncing => 'Syncing latest changes',
      GtexAsyncSurfaceState.reconnecting => 'Reconnecting live feed',
      GtexAsyncSurfaceState.degraded => 'Live feed is degraded',
      GtexAsyncSurfaceState.confirmed => 'Confirmed',
      GtexAsyncSurfaceState.error => 'Something went wrong',
      GtexAsyncSurfaceState.data => 'Data ready',
    };
  }

  String get message {
    return switch (this) {
      GtexAsyncSurfaceState.loading =>
        'We are fetching the latest data for this surface.',
      GtexAsyncSurfaceState.empty =>
        'There is no live data available for this surface right now.',
      GtexAsyncSurfaceState.blocked =>
        'This action cannot continue until the blocking requirement is cleared.',
      GtexAsyncSurfaceState.pending =>
        'Your request is queued and will update when the server confirms it.',
      GtexAsyncSurfaceState.syncing =>
        'Local changes are being reconciled with the live service.',
      GtexAsyncSurfaceState.reconnecting =>
        'The realtime connection dropped, so we are trying to restore it.',
      GtexAsyncSurfaceState.degraded =>
        'Some live updates may be delayed while the service recovers.',
      GtexAsyncSurfaceState.confirmed =>
        'The latest operation was accepted and is visible now.',
      GtexAsyncSurfaceState.error =>
        'The request failed. Try again when the connection is stable.',
      GtexAsyncSurfaceState.data =>
        'The latest data is loaded and ready to render.',
    };
  }

  IconData get icon {
    return switch (this) {
      GtexAsyncSurfaceState.loading => Icons.downloading_rounded,
      GtexAsyncSurfaceState.empty => Icons.inbox_rounded,
      GtexAsyncSurfaceState.blocked => Icons.lock_rounded,
      GtexAsyncSurfaceState.pending => Icons.schedule_rounded,
      GtexAsyncSurfaceState.syncing => Icons.sync_rounded,
      GtexAsyncSurfaceState.reconnecting => Icons.wifi_find_rounded,
      GtexAsyncSurfaceState.degraded =>
        Icons.signal_cellular_connected_no_internet_4_bar_rounded,
      GtexAsyncSurfaceState.confirmed => Icons.check_circle_rounded,
      GtexAsyncSurfaceState.error => Icons.error_rounded,
      GtexAsyncSurfaceState.data => Icons.dataset_rounded,
    };
  }

  bool get showsProgress {
    return switch (this) {
      GtexAsyncSurfaceState.loading ||
      GtexAsyncSurfaceState.syncing ||
      GtexAsyncSurfaceState.reconnecting => true,
      GtexAsyncSurfaceState.empty ||
      GtexAsyncSurfaceState.blocked ||
      GtexAsyncSurfaceState.pending ||
      GtexAsyncSurfaceState.degraded ||
      GtexAsyncSurfaceState.confirmed ||
      GtexAsyncSurfaceState.error ||
      GtexAsyncSurfaceState.data => false,
    };
  }
}

sealed class GtexSurfaceState<T> {
  const GtexSurfaceState();
}

class GtexLoading<T> extends GtexSurfaceState<T> {
  const GtexLoading();
}

class GtexEmpty<T> extends GtexSurfaceState<T> {
  const GtexEmpty({this.reason});

  final String? reason;
}

class GtexBlocked<T> extends GtexSurfaceState<T> {
  const GtexBlocked({required this.reason, this.ctaRoute});

  final String reason;
  final String? ctaRoute;
}

class GtexPending<T> extends GtexSurfaceState<T> {
  const GtexPending({this.stale});

  final T? stale;
}

class GtexSyncing<T> extends GtexSurfaceState<T> {
  const GtexSyncing({required this.current});

  final T current;
}

class GtexReconnecting<T> extends GtexSurfaceState<T> {
  const GtexReconnecting({this.lastKnown, required this.attempt});

  final T? lastKnown;
  final int attempt;
}

class GtexDegraded<T> extends GtexSurfaceState<T> {
  const GtexDegraded({required this.current, required this.warning});

  final T current;
  final String warning;
}

class GtexConfirmed<T> extends GtexSurfaceState<T> {
  const GtexConfirmed({required this.data, this.auditRef});

  final T data;
  final String? auditRef;
}

class GtexError<T> extends GtexSurfaceState<T> {
  const GtexError({required this.code, required this.message});

  final String code;
  final String message;
}

class GtexData<T> extends GtexSurfaceState<T> {
  const GtexData({required this.data});

  final T data;
}
