import 'dart:async';

import 'package:flutter/foundation.dart';

import '../data/gtex_match_feed.dart';
import '../data/gtex_match_models.dart';
import '../data/gtex_match_repository.dart';

/// Drives the GTEX match centre.
///
/// Responsibilities beyond plain fetching:
///  * keeps an explicit [GtexMatchConnectionStatus] so the UI never renders a
///    blank panel while the feed is re-establishing;
///  * drops duplicate / stale / malformed frames via [GtexMatchFeedGuard] so a
///    chatty socket cannot cause redundant rebuilds or rewind the scoreline;
///  * survives transport errors by reconnecting with bounded exponential
///    backoff instead of tearing the subscription down permanently;
///  * stops streaming once the match reaches full time.
class GtexMatchCenterController extends ChangeNotifier {
  GtexMatchCenterController({
    required this.matchId,
    GtexMatchRepository? repository,
    GtexMatchReconnectPolicy reconnectPolicy =
        const GtexMatchReconnectPolicy(),
  }) : repository = repository ?? const GtexUnavailableMatchRepository(),
       _reconnectPolicy = reconnectPolicy,
       _guard = GtexMatchFeedGuard(matchId: matchId);

  final String matchId;
  final GtexMatchRepository repository;
  final GtexMatchReconnectPolicy _reconnectPolicy;
  final GtexMatchFeedGuard _guard;

  StreamSubscription<GtexLiveMatchState>? _subscription;
  Timer? _reconnectTimer;
  int _reconnectAttempt = 0;
  bool _disposed = false;

  GtexMatchConnectionStatus _connection = GtexMatchConnectionStatus.idle;
  Object? _error;
  bool _isLoading = false;
  bool _isSendingInstruction = false;
  int _selectedTab = 0;

  /// Last accepted snapshot, or null before the first successful load.
  GtexLiveMatchState? get state => _guard.current;

  /// Fatal error, only set while there is nothing to render.
  Object? get error => _error;

  bool get isLoading => _isLoading;
  bool get isSendingInstruction => _isSendingInstruction;
  int get selectedTab => _selectedTab;

  GtexMatchConnectionStatus get connection => _connection;
  GtexMatchFeedDiagnostics get diagnostics => _guard.diagnostics;

  /// True when a snapshot is on screen but the feed behind it is degraded.
  bool get isShowingStaleData =>
      _guard.current != null && _connection.isDegraded;

  /// Entry point used by the screen on mount and by the retry affordance.
  Future<void> load() async {
    _cancelReconnect();
    await _subscription?.cancel();
    _subscription = null;
    _reconnectAttempt = 0;
    _error = null;
    _isLoading = true;
    _connection = GtexMatchConnectionStatus.connecting;
    _notify();

    try {
      final GtexLiveMatchState initial = await repository.fetchLiveMatch(
        matchId,
      );
      _guard.offer(initial);
      _error = null;
    } catch (err) {
      // Only surface a hard error when there is nothing to show. If a previous
      // snapshot is still on screen we degrade to reconnecting instead.
      if (_guard.current == null) {
        _error = err;
        _isLoading = false;
        _connection = GtexMatchConnectionStatus.offline;
        _notify();
        return;
      }
    }

    _isLoading = false;
    if (_guard.isFinished) {
      _connection = GtexMatchConnectionStatus.finished;
      _notify();
      return;
    }
    _connection = GtexMatchConnectionStatus.live;
    _notify();
    _attachStream();
  }

  /// Retry alias so the UI reads clearly at the call site.
  Future<void> retry() => load();

  void _attachStream() {
    if (_disposed) {
      return;
    }
    _subscription?.cancel();
    _subscription = repository
        .watchLiveMatch(matchId)
        .listen(
          _handleSnapshot,
          onError: _handleStreamError,
          onDone: _handleStreamDone,
          cancelOnError: false,
        );
  }

  void _handleSnapshot(GtexLiveMatchState snapshot) {
    if (_disposed) {
      return;
    }
    // A frame arriving proves the transport is healthy again.
    final bool wasDegraded = _connection.isDegraded;
    _reconnectAttempt = 0;

    final GtexMatchFeedVerdict verdict = _guard.offer(snapshot);
    final bool finished = _guard.isFinished;

    if (finished) {
      _connection = GtexMatchConnectionStatus.finished;
      _teardownStream();
      _notify();
      return;
    }

    if (verdict != GtexMatchFeedVerdict.accepted) {
      // Redundant or bogus frame. Repair the banner if we were degraded, but
      // otherwise stay silent so the widget tree does not rebuild.
      if (wasDegraded) {
        _connection = GtexMatchConnectionStatus.live;
        _notify();
      }
      return;
    }

    _error = null;
    _connection = GtexMatchConnectionStatus.live;
    _notify();
  }

  void _handleStreamError(Object err) {
    if (_disposed) {
      return;
    }
    _guard.recordMalformed();
    if (_guard.current == null) {
      _error = err;
      _connection = GtexMatchConnectionStatus.offline;
      _notify();
      return;
    }
    // Keep the last good snapshot on screen and try to recover.
    _scheduleReconnect();
  }

  void _handleStreamDone() {
    if (_disposed || _guard.isFinished) {
      return;
    }
    // The transport closed before full time; treat it as a drop.
    _scheduleReconnect();
  }

  void _scheduleReconnect() {
    if (_disposed || _reconnectTimer != null) {
      return;
    }
    _teardownStream();
    _reconnectAttempt += 1;
    if (!_reconnectPolicy.shouldRetry(_reconnectAttempt)) {
      _connection = GtexMatchConnectionStatus.offline;
      _notify();
      return;
    }
    _guard.recordReconnect();
    _connection = GtexMatchConnectionStatus.reconnecting;
    _notify();
    _reconnectTimer = Timer(
      _reconnectPolicy.delayForAttempt(_reconnectAttempt),
      () {
        _reconnectTimer = null;
        if (_disposed) {
          return;
        }
        _attachStream();
      },
    );
  }

  void _teardownStream() {
    _subscription?.cancel();
    _subscription = null;
  }

  void _cancelReconnect() {
    _reconnectTimer?.cancel();
    _reconnectTimer = null;
  }

  void selectTab(int index) {
    if (_selectedTab == index) {
      return;
    }
    _selectedTab = index;
    _notify();
  }

  void selectPitchPlayer(String playerId) {
    final GtexLiveMatchState? current = _guard.current;
    if (current == null || current.selectedPlayerId == playerId) {
      return;
    }
    _guard.mutateLocally(current.copyWith(selectedPlayerId: playerId));
    _notify();
  }

  Future<void> sendInstruction(GtexTacticalInstruction instruction) async {
    if (_isSendingInstruction) {
      return;
    }
    _isSendingInstruction = true;
    _notify();
    try {
      await repository.sendTacticalInstruction(matchId, instruction);
    } finally {
      _isSendingInstruction = false;
      _notify();
    }
  }

  void _notify() {
    if (_disposed) {
      return;
    }
    notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    _cancelReconnect();
    _subscription?.cancel();
    _subscription = null;
    super.dispose();
  }
}
