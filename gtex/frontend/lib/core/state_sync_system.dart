import 'dart:async';

import 'package:flutter/foundation.dart';

class StateSyncSystem {
  StateSyncSystem({
    required Duration interval,
    required Future<void> Function() onSync,
    VoidCallback? onStateChanged,
  }) : _interval = interval,
       _onSync = onSync,
       _onStateChanged = onStateChanged;

  final Duration _interval;
  final Future<void> Function() _onSync;
  final VoidCallback? _onStateChanged;

  Timer? _timer;
  int _attachments = 0;
  bool _isSyncing = false;
  DateTime? _lastSyncedAt;
  Future<void>? _activeSync;
  bool _rerunRequested = false;

  bool get isSyncing => _isSyncing;

  DateTime? get lastSyncedAt => _lastSyncedAt;

  void attach({bool syncImmediately = false}) {
    _attachments += 1;
    if (_attachments != 1) {
      return;
    }
    _startTimer();
    if (syncImmediately) {
      unawaited(sync());
    }
  }

  void detach() {
    if (_attachments == 0) {
      return;
    }
    _attachments -= 1;
    if (_attachments == 0) {
      stop();
    }
  }

  Future<void> sync() async {
    final Future<void>? activeSync = _activeSync;
    if (activeSync != null) {
      return activeSync;
    }
    final Future<void> nextSync = _runSyncLoop();
    _activeSync = nextSync;
    return nextSync;
  }

  Future<void> syncAfterCriticalAction() {
    if (_activeSync != null) {
      _rerunRequested = true;
    }
    return sync();
  }

  void stop() {
    _timer?.cancel();
    _timer = null;
  }

  void _startTimer() {
    _timer?.cancel();
    _timer = Timer.periodic(_interval, (_) {
      unawaited(sync());
    });
  }

  Future<void> _runSyncLoop() async {
    _setSyncing(true);
    try {
      do {
        _rerunRequested = false;
        await _onSync();
        _lastSyncedAt = DateTime.now().toUtc();
        _onStateChanged?.call();
      } while (_rerunRequested);
    } finally {
      _activeSync = null;
      _setSyncing(false);
    }
  }

  void _setSyncing(bool value) {
    if (_isSyncing == value) {
      return;
    }
    _isSyncing = value;
    _onStateChanged?.call();
  }
}
