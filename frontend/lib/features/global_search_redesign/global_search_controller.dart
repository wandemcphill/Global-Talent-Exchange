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
  }) : _api = api,
       _admin = admin;

  final GtexGlobalSearchApi _api;
  final bool _admin;
  String _query = '';
  List<GtexGlobalSearchResult> _results = const <GtexGlobalSearchResult>[];
  bool _loading = false;
  String? _error;

  String get query => _query;
  List<GtexGlobalSearchResult> get results => _results;
  bool get loading => _loading;
  String? get error => _error;

  Future<void> search(String value) async {
    _query = value;
    final String term = value.trim();
    if (term.length < 2) {
      _results = const <GtexGlobalSearchResult>[];
      _error = null;
      notifyListeners();
      return;
    }
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      _results = await _filterLaunchVisible(
        await _api.search(term, admin: _admin),
      );
    } catch (error) {
      _error = error.toString();
    } finally {
      _loading = false;
      notifyListeners();
    }
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
