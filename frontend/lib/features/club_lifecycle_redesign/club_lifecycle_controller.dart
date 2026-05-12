import 'package:flutter/foundation.dart';

import 'club_lifecycle_api.dart';
import 'club_lifecycle_models.dart';

class GtexClubLifecycleController extends ChangeNotifier {
  GtexClubLifecycleController({
    required GtexClubLifecycleApi api,
    required String clubId,
    GtexClubOperatingDashboard? initialDashboard,
  }) : _api = api,
       _clubId = clubId,
       _dashboard = initialDashboard;

  final GtexClubLifecycleApi _api;
  final String _clubId;
  GtexClubOperatingDashboard? _dashboard;
  bool _loading = false;
  bool _mutating = false;
  String? _error;

  GtexClubOperatingDashboard? get dashboard => _dashboard;
  bool get loading => _loading;
  bool get mutating => _mutating;
  bool get busy => _loading || _mutating;
  String? get error => _error;

  Future<void> load() async {
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      _dashboard = await _api.fetchDashboard(_clubId);
    } catch (error) {
      _error = error.toString();
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<void> syncSquadRegistration() {
    return _mutate(() => _api.syncSquadRegistration(_clubId));
  }

  Future<void> submitSquadRegistration() {
    return _mutate(() => _api.submitSquadRegistration(_clubId));
  }

  Future<void> lockSquadRegistration() {
    return _mutate(() => _api.lockSquadRegistration(_clubId));
  }

  Future<void> advanceLifecycle() {
    return _mutate(() => _api.advanceLifecycle(_clubId));
  }

  Future<void> _mutate(Future<Object?> Function() action) async {
    _mutating = true;
    _error = null;
    notifyListeners();
    try {
      await action();
      _dashboard = await _api.fetchDashboard(_clubId);
    } catch (error) {
      _error = error.toString();
    } finally {
      _mutating = false;
      notifyListeners();
    }
  }
}
