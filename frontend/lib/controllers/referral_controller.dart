import 'package:flutter/foundation.dart';

import '../data/gte_api_repository.dart';
import '../data/referral_api.dart';
import '../models/referral_models.dart';

class ReferralController extends ChangeNotifier {
  ReferralController({
    required ReferralApi api,
  }) : _api = api;

  final ReferralApi _api;
  final GteRequestGate _loadGate = GteRequestGate();

  bool isLoading = false;
  String? errorMessage;
  ReferralHubData? hub;

  bool get hasData => hub != null;

  Future<void> load({bool force = false}) async {
    if (isLoading || (hub != null && !force)) {
      return;
    }
    final int requestId = _loadGate.begin();
    isLoading = true;
    errorMessage = null;
    notifyListeners();

    try {
      final ReferralHubData data = await _api.fetchReferralHub();
      if (!_loadGate.isActive(requestId)) {
        return;
      }
      hub = data;
      errorMessage = null;
    } catch (error) {
      if (_loadGate.isActive(requestId)) {
        errorMessage = error.toString();
      }
    } finally {
      if (_loadGate.isActive(requestId)) {
        isLoading = false;
        notifyListeners();
      }
    }
  }
}
