import 'dart:async';

import 'package:flutter/foundation.dart';

import '../data/gtex_match_demo_repository.dart';
import '../data/gtex_match_models.dart';

class GtexMatchCenterController extends ChangeNotifier {
  GtexMatchCenterController({
    required this.matchId,
    GtexMatchRepository? repository,
  }) : repository = repository ?? const GtexMatchDemoRepository();

  final String matchId;
  final GtexMatchRepository repository;

  StreamSubscription<GtexLiveMatchState>? _subscription;
  GtexLiveMatchState? state;
  Object? error;
  bool isLoading = false;
  bool isSendingInstruction = false;
  int selectedTab = 0;

  Future<void> load() async {
    isLoading = true;
    error = null;
    notifyListeners();
    try {
      state = await repository.fetchLiveMatch(matchId);
      _subscription?.cancel();
      _subscription = repository.watchLiveMatch(matchId).listen((event) {
        state = event;
        notifyListeners();
      }, onError: (Object err) {
        error = err;
        notifyListeners();
      });
    } catch (err) {
      error = err;
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }

  void selectTab(int index) {
    selectedTab = index;
    notifyListeners();
  }

  void selectPitchPlayer(String playerId) {
    final current = state;
    if (current == null) return;
    state = current.copyWith(selectedPlayerId: playerId);
    notifyListeners();
  }

  Future<void> sendInstruction(GtexTacticalInstruction instruction) async {
    isSendingInstruction = true;
    notifyListeners();
    try {
      await repository.sendTacticalInstruction(matchId, instruction);
    } finally {
      isSendingInstruction = false;
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _subscription?.cancel();
    super.dispose();
  }
}
