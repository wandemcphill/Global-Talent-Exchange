import 'package:flutter/foundation.dart';

import '../../core/app_feedback.dart';
import 'matchday_economy_api.dart';
import 'matchday_economy_models.dart';

class GtexMatchdayEconomyController extends ChangeNotifier {
  GtexMatchdayEconomyController({required this.api});

  final GtexMatchdayEconomyApi api;

  GtexMatchdayEconomyOverview? _overview;
  GtexMatchdayEconomyAction? _lastAction;
  bool _isLoading = false;
  bool _isMutating = false;
  String? _errorMessage;

  GtexMatchdayEconomyOverview? get overview => _overview;
  GtexMatchdayEconomyAction? get lastAction => _lastAction;
  bool get isLoading => _isLoading;
  bool get isMutating => _isMutating;
  String? get errorMessage => _errorMessage;

  Future<void> load({bool admin = false}) async {
    if (_isLoading) {
      return;
    }
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();
    try {
      _overview = await api.fetchOverview(admin: admin);
    } catch (error) {
      _errorMessage = AppFeedback.messageFor(error);
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<GtexMatchdayEconomyAction?> resolveFederationSanction(
    String sanctionId, {
    String? note,
  }) {
    return _runAction(
      () => api.resolveFederationSanction(sanctionId: sanctionId, note: note),
    );
  }

  Future<GtexMatchdayEconomyAction?> settlePredictionRewards(
    String fixtureId, {
    String fancoinAmount = '25.0000',
    int maxWinners = 3,
    String? note,
  }) {
    return _runAction(
      () => api.settlePredictionRewards(
        fixtureId: fixtureId,
        fancoinAmount: fancoinAmount,
        maxWinners: maxWinners,
        note: note,
      ),
    );
  }

  Future<GtexMatchdayEconomyAction?> checkInTicket(
    String ticketId, {
    int loyaltyPoints = 25,
    int xpAwarded = 10,
    String? reactionType,
  }) {
    return _runAction(
      () => api.checkInTicket(
        ticketId: ticketId,
        loyaltyPoints: loyaltyPoints,
        xpAwarded: xpAwarded,
        reactionType: reactionType,
      ),
    );
  }

  Future<GtexMatchdayEconomyAction?> settleCardListing(
    String listingId, {
    required String buyerUserId,
    int quantity = 1,
    int feeBps = 400,
  }) {
    return _runAction(
      () => api.settleCardListing(
        listingId: listingId,
        buyerUserId: buyerUserId,
        quantity: quantity,
        feeBps: feeBps,
      ),
    );
  }

  Future<GtexMatchdayEconomyAction?> _runAction(
    Future<GtexMatchdayEconomyAction> Function() action,
  ) async {
    if (_isMutating) {
      return null;
    }
    _isMutating = true;
    _errorMessage = null;
    notifyListeners();
    try {
      _lastAction = await action();
      return _lastAction;
    } catch (error) {
      _errorMessage = AppFeedback.messageFor(error);
      return null;
    } finally {
      _isMutating = false;
      notifyListeners();
    }
  }
}
