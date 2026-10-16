import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/launch_control_redesign/launch_control_api.dart';
import 'package:gte_frontend/features/launch_control_redesign/launch_control_feature_gate.dart';
import 'package:gte_frontend/features/launch_control_redesign/launch_control_models.dart';

import 'global_search_api.dart';
import 'global_search_models.dart';

class GtexGlobalSearchController extends ChangeNotifier {
  GtexGlobalSearchController({
    required GtexGlobalSearchApi api,
    bool admin = false,
    Duration debounce = const Duration(milliseconds: 280),
  }) : _api = api,
       _admin = admin,
       _debounce = debounce;

  /// Shortest term the backend will accept.
  static const int minimumQueryLength = 2;

  final GtexGlobalSearchApi _api;
  final bool _admin;

  /// Keystroke settle time before a request is issued. Without it every
  /// character typed produced its own round trip.
  final Duration _debounce;

  Timer? _debounceTimer;

  /// Completes when the currently scheduled search settles or is superseded.
  Completer<void>? _pendingCompleter;

  /// Monotonic id of the most recently *issued* request. Responses carrying an
  /// older id are discarded, so a slow early request can never overwrite the
  /// results of a later one.
  int _requestSerial = 0;

  /// Serial of the newest response actually applied to [_results].
  int _appliedSerial = 0;

  String _query = '';
  String _lastExecutedTerm = '';
  List<GtexGlobalSearchResult> _results = const <GtexGlobalSearchResult>[];
  bool _loading = false;
  String? _error;
  bool _disposed = false;

  String get query => _query;
  List<GtexGlobalSearchResult> get results => _results;
  bool get loading => _loading;
  String? get error => _error;

  /// Debounced entry point bound to the text field.
  ///
  /// Returns a future that completes once the debounced request settles (or
  /// once the call is superseded), so callers and tests can await a search
  /// without knowing about the timer.
  Future<void> search(String value) {
    _query = value;
    final String term = value.trim();
    _cancelPending();

    if (term.length < minimumQueryLength) {
      // Abandon any in-flight request so its result cannot land after the
      // user has already cleared the box.
      _requestSerial += 1;
      _lastExecutedTerm = '';
      _results = const <GtexGlobalSearchResult>[];
      _error = null;
      _loading = false;
      _notify();
      return Future<void>.value();
    }

    if (term == _lastExecutedTerm && _results.isNotEmpty && _error == null) {
      // Same term already satisfied (e.g. trailing whitespace typed).
      _loading = false;
      _notify();
      return Future<void>.value();
    }

    _loading = true;
    _error = null;
    _notify();

    final Completer<void> completer = Completer<void>();
    _pendingCompleter = completer;
    _debounceTimer = Timer(_debounce, () async {
      _debounceTimer = null;
      await _execute(term);
      if (_pendingCompleter == completer && !completer.isCompleted) {
        _pendingCompleter = null;
        completer.complete();
      }
    });
    return completer.future;
  }

  /// Cancels a scheduled search and releases anyone awaiting it.
  void _cancelPending() {
    _debounceTimer?.cancel();
    _debounceTimer = null;
    final Completer<void>? pending = _pendingCompleter;
    _pendingCompleter = null;
    if (pending != null && !pending.isCompleted) {
      pending.complete();
    }
  }

  /// Issues a search immediately, bypassing the debounce.
  ///
  /// Used by the submit action so pressing enter does not wait out the timer.
  Future<void> searchNow(String value) {
    _query = value;
    final String term = value.trim();
    _cancelPending();
    if (term.length < minimumQueryLength) {
      _requestSerial += 1;
      _lastExecutedTerm = '';
      _results = const <GtexGlobalSearchResult>[];
      _error = null;
      _loading = false;
      _notify();
      return Future<void>.value();
    }
    _loading = true;
    _error = null;
    _notify();
    return _execute(term);
  }

  /// Re-runs the current term, used by the error-state retry affordance.
  Future<void> retry() => searchNow(_query);

  Future<void> _execute(String term) async {
    final int serial = ++_requestSerial;
    try {
      final List<GtexGlobalSearchResult> visible = await _filterLaunchVisible(
        await _api.search(term, admin: _admin),
      );
      if (_disposed || serial < _appliedSerial || serial != _requestSerial) {
        // A newer request has been issued or already applied; drop this one.
        return;
      }
      _appliedSerial = serial;
      _lastExecutedTerm = term;
      _results = visible;
      _error = null;
    } catch (error) {
      if (_disposed || serial != _requestSerial) {
        return;
      }
      _appliedSerial = serial;
      _error = error.toString();
    } finally {
      if (!_disposed && serial == _requestSerial) {
        _loading = false;
        _notify();
      }
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
    _cancelPending();
    super.dispose();
  }

  Future<List<GtexGlobalSearchResult>> _filterLaunchVisible(
    List<GtexGlobalSearchResult> results,
  ) async {
    final List<GtexGlobalSearchResult> canonicalResults = results
        .map(
          (GtexGlobalSearchResult result) => result.copyWith(
            route: gtexCanonicalGlobalSearchRoute(
              result.route,
              isAdmin: _admin,
            ),
          ),
        )
        .toList(growable: false);
    if (_admin || results.isEmpty) {
      return canonicalResults;
    }
    if (!canonicalResults.any(
      (GtexGlobalSearchResult result) =>
          GtexLaunchControlFeatureGate.featureKeyForPath(result.route) != null,
    )) {
      return canonicalResults;
    }

    late final List<GtexClientFeatureFlag> flags;
    try {
      final GtexLaunchControlApi launchControlApi =
          _api.client.mode == GteBackendMode.fixture
              ? GtexLaunchControlApi.fixture()
              : GtexLaunchControlApi.standard(
                baseUrl: _api.client.config.baseUrl,
                accessToken: _api.client.accessToken,
                mode: _api.client.mode,
              );
      flags = await launchControlApi.fetchClientFlags();
    } catch (_) {
      flags = const <GtexClientFeatureFlag>[];
    }

    final List<GtexGlobalSearchResult> visible = <GtexGlobalSearchResult>[];
    for (final GtexGlobalSearchResult result in canonicalResults) {
      final String canonicalRoute = result.route;
      if (canonicalRoute == '/app/home' && result.adminOnly) {
        continue;
      }
      final String? featureKey = GtexLaunchControlFeatureGate.featureKeyForPath(
        canonicalRoute,
      );
      final GtexFeatureGateDecision decision =
          GtexLaunchControlFeatureGate.resolveFromClientFlags(
            featureKey: featureKey,
            route: canonicalRoute,
            isAdmin: _admin,
            flags: flags,
          );
      if (decision.allowed) {
        visible.add(result.copyWith(route: canonicalRoute));
      }
    }
    return visible;
  }
}
