import 'package:flutter/foundation.dart';

class OptimisticUiHandler<KeyT, StateT> {
  OptimisticUiHandler({VoidCallback? onStateChanged})
    : _onStateChanged = onStateChanged;

  final VoidCallback? _onStateChanged;
  final Set<KeyT> _pendingKeys = <KeyT>{};

  bool isPending(KeyT key) => _pendingKeys.contains(key);

  Future<void> run({
    required KeyT key,
    required StateT currentState,
    required StateT Function(StateT currentState) optimisticState,
    required void Function(StateT nextState) apply,
    required Future<void> Function() commit,
  }) async {
    if (_pendingKeys.contains(key)) {
      return;
    }

    final StateT previousState = currentState;
    _pendingKeys.add(key);
    _onStateChanged?.call();

    apply(optimisticState(currentState));
    try {
      await commit();
    } catch (_) {
      apply(previousState);
      rethrow;
    } finally {
      _pendingKeys.remove(key);
      _onStateChanged?.call();
    }
  }
}
