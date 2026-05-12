import 'package:flutter/foundation.dart';

import 'club_growth_api.dart';
import 'club_growth_models.dart';

class GtexClubGrowthController extends ChangeNotifier {
  GtexClubGrowthController({
    required GtexClubGrowthApi api,
    required String clubId,
    GtexClubGrowthDashboard? initialDashboard,
  }) : _api = api,
       _clubId = clubId,
       _dashboard = initialDashboard;

  final GtexClubGrowthApi _api;
  final String _clubId;
  GtexClubGrowthDashboard? _dashboard;
  bool _loading = false;
  bool _mutating = false;
  String? _error;

  GtexClubGrowthDashboard? get dashboard => _dashboard;
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

  Future<void> hireStaff(String staffId) {
    return _mutate(() async {
      final GtexStaffContract offered = await _api.offerStaffContract(
        _clubId,
        staffId,
      );
      await _api.acceptStaffContract(_clubId, offered.id);
    });
  }

  Future<void> generateProspects() {
    return _mutate(() async {
      await _api.generateProspects(_clubId);
    });
  }

  Future<void> offerAndAcceptProspectContract(String prospectId) {
    return _mutate(() async {
      final GtexAcademyContractOffer offer = await _api.offerProspectContract(
        _clubId,
        prospectId,
      );
      await _api.acceptProspectContract(_clubId, offer.id);
    });
  }

  Future<void> promoteProspect(String prospectId) {
    return _mutate(() async {
      await _api.promoteProspect(_clubId, prospectId);
    });
  }

  Future<void> _mutate(Future<void> Function() action) async {
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
