import 'package:flutter/foundation.dart';

import 'launch_control_api.dart';
import 'launch_control_models.dart';

class GtexLaunchControlController extends ChangeNotifier {
  GtexLaunchControlController({
    required GtexLaunchControlApi api,
    GtexLaunchControlSnapshot? initialSnapshot,
  }) : _api = api,
       _snapshot = initialSnapshot;

  final GtexLaunchControlApi _api;
  GtexLaunchControlSnapshot? _snapshot;
  List<GtexClientFeatureFlag> _clientFlags = const <GtexClientFeatureFlag>[];
  bool _loading = false;
  bool _actionLoading = false;
  String? _error;
  String? _actionMessage;
  String? _actionError;

  GtexLaunchControlSnapshot? get snapshot => _snapshot;
  List<GtexClientFeatureFlag> get clientFlags => _clientFlags;
  bool get loading => _loading;
  bool get actionLoading => _actionLoading;
  String? get error => _error;
  String? get actionMessage => _actionMessage;
  String? get actionError => _actionError;

  List<GtexLaunchControlFlag> get flags =>
      _snapshot?.flags ?? const <GtexLaunchControlFlag>[];

  Future<void> load() async {
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      _snapshot = await _api.fetchDashboard();
      await _refreshClientFlagsQuietly();
    } catch (error) {
      _error = error.toString();
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<void> toggleFlag(GtexLaunchControlFlag flag) async {
    final bool nextValue = !flag.enabled;
    await _runAction(() async {
      final GtexLaunchControlFlag updated = await _api.setFlagEnabled(
        featureKey: flag.featureKey,
        enabled: nextValue,
        reason: 'Updated from GTEX launch-control screen.',
      );
      _snapshot = _snapshot?.replaceFlag(updated);
      await _refreshClientFlagsQuietly();
      return '${updated.title} ${updated.enabled ? 'enabled' : 'disabled'}.';
    });
  }

  Future<void> toggleKillSwitch(GtexLaunchControlFlag flag) async {
    final bool nextValue = !flag.killSwitchEnabled;
    await _runAction(() async {
      final GtexLaunchControlFlag updated = await _api.setKillSwitch(
        featureKey: flag.featureKey,
        enabled: nextValue,
        reason: 'Updated from GTEX launch-control screen.',
      );
      _snapshot = _snapshot?.replaceFlag(updated);
      await _refreshClientFlagsQuietly();
      return updated.killSwitchEnabled
          ? '${updated.title} kill switch enabled.'
          : '${updated.title} kill switch cleared.';
    });
  }

  Future<void> changeLaunchState(
    GtexLaunchControlFlag flag,
    GtexLaunchState launchState,
  ) async {
    if (flag.launchState == launchState) {
      return;
    }
    await _runAction(() async {
      final GtexLaunchControlFlag updated = await _api.updateFlag(
        featureKey: flag.featureKey,
        launchState: launchState,
        reason: 'Launch state updated from GTEX launch-control screen.',
      );
      _snapshot = _snapshot?.replaceFlag(updated);
      await _refreshClientFlagsQuietly();
      return '${updated.title} moved to ${gtexLaunchStateLabel(updated.launchState)}.';
    });
  }

  Future<void> setBetaOnly(
    GtexLaunchControlFlag flag, {
    required bool betaOnly,
  }) async {
    if (flag.betaOnly == betaOnly) {
      return;
    }
    await _runAction(() async {
      final GtexLaunchControlFlag updated = await _api.updateFlag(
        featureKey: flag.featureKey,
        betaOnly: betaOnly,
        reason: 'Beta access rule updated from GTEX launch-control screen.',
      );
      _snapshot = _snapshot?.replaceFlag(updated);
      await _refreshClientFlagsQuietly();
      return updated.betaOnly
          ? '${updated.title} now requires beta access.'
          : '${updated.title} no longer requires beta access.';
    });
  }

  Future<void> refreshClientFlags() async {
    await _runAction(() async {
      _clientFlags = await _api.fetchClientFlags();
      return 'Client flag snapshot refreshed.';
    });
  }

  Future<void> grantBetaAccess({
    required String featureKey,
    required String userId,
    String? notes,
    DateTime? expiresAt,
  }) async {
    await _runAction(() async {
      final GtexBetaAccessGrant grant = await _api.grantBetaAccess(
        featureKey: featureKey,
        userId: userId,
        notes: notes,
        expiresAt: expiresAt,
      );
      _snapshot = _snapshot?.replaceGrant(grant);
      await _refreshClientFlagsQuietly();
      return 'Beta access granted to ${grant.userId}.';
    });
  }

  Future<void> revokeBetaAccess(GtexBetaAccessGrant grant) async {
    await _runAction(() async {
      final GtexBetaAccessGrant revoked = await _api.revokeBetaAccess(
        featureKey: grant.featureKey,
        userId: grant.userId,
      );
      _snapshot = _snapshot?.replaceGrant(revoked);
      await _refreshClientFlagsQuietly();
      return 'Beta access revoked for ${grant.userId}.';
    });
  }

  void replaceSnapshot(GtexLaunchControlSnapshot snapshot) {
    _snapshot = snapshot;
    _error = null;
    notifyListeners();
  }

  Future<void> _refreshClientFlagsQuietly() async {
    try {
      _clientFlags = await _api.fetchClientFlags();
    } catch (_) {
      // The dashboard remains usable even if the public client snapshot is unavailable.
    }
  }

  Future<void> _runAction(Future<String> Function() action) async {
    _actionLoading = true;
    _actionMessage = null;
    _actionError = null;
    notifyListeners();
    try {
      _actionMessage = await action();
    } catch (error) {
      _actionError = error.toString();
    } finally {
      _actionLoading = false;
      notifyListeners();
    }
  }
}
