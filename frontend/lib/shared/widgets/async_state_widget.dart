import 'package:flutter/widgets.dart';

import '../state/gtex_surface_state.dart';

class AsyncStateWidget<T> extends StatelessWidget {
  const AsyncStateWidget({
    super.key,
    required this.state,
    required this.onLoading,
    required this.onEmpty,
    required this.onBlocked,
    required this.onPending,
    required this.onSyncing,
    required this.onReconnecting,
    required this.onDegraded,
    required this.onConfirmed,
    required this.onError,
    required this.onData,
    this.retry,
  });

  final GtexSurfaceState<T> state;
  final Widget Function() onLoading;
  final Widget Function(String? reason) onEmpty;
  final Widget Function(String reason, String? ctaRoute) onBlocked;
  final Widget Function(T? stale) onPending;
  final Widget Function(T current) onSyncing;
  final Widget Function(T? lastKnown, int attempt) onReconnecting;
  final Widget Function(T current, String warning) onDegraded;
  final Widget Function(T data, String? auditRef) onConfirmed;
  final Widget Function(String code, String message, VoidCallback retry)
  onError;
  final Widget Function(T data) onData;
  final VoidCallback? retry;

  @override
  Widget build(BuildContext context) {
    final currentState = state;

    if (currentState is GtexLoading<T>) {
      return onLoading();
    }
    if (currentState is GtexEmpty<T>) {
      return onEmpty(currentState.reason);
    }
    if (currentState is GtexBlocked<T>) {
      return onBlocked(currentState.reason, currentState.ctaRoute);
    }
    if (currentState is GtexPending<T>) {
      return onPending(currentState.stale);
    }
    if (currentState is GtexSyncing<T>) {
      return onSyncing(currentState.current);
    }
    if (currentState is GtexReconnecting<T>) {
      return onReconnecting(currentState.lastKnown, currentState.attempt);
    }
    if (currentState is GtexDegraded<T>) {
      return onDegraded(currentState.current, currentState.warning);
    }
    if (currentState is GtexConfirmed<T>) {
      return onConfirmed(currentState.data, currentState.auditRef);
    }
    if (currentState is GtexError<T>) {
      return onError(currentState.code, currentState.message, retry ?? _noop);
    }
    if (currentState is GtexData<T>) {
      return onData(currentState.data);
    }

    throw StateError('Unsupported GtexSurfaceState: $currentState');
  }
}

void _noop() {}
