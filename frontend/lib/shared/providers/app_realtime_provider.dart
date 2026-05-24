import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/gte_app_config.dart';
import '../../core/runtime/gtex_realtime_client.dart';
import '../../data/gte_api_repository.dart';
import '../../features/competitions/live_competitions_provider.dart';
import '../../features/transfer_market/live_market_provider.dart';
import 'auth_provider.dart';

final Provider<AppRealtimeSyncController> appRealtimeSyncProvider =
    Provider<AppRealtimeSyncController>((Ref ref) {
      final GteBackendMode mode = ref.watch(criticalBackendModeProvider);
      final String baseUrl = ref.watch(apiBaseUrlProvider);
      final String? accessToken = ref.watch(accessTokenProvider);
      final controller = AppRealtimeSyncController(
        enabled: mode != GteBackendMode.fixture,
        apiBaseUrl: baseUrl,
        includeWallet: accessToken != null && accessToken.trim().isNotEmpty,
        invalidateMarket: () => ref.invalidate(marketDashboardProvider),
        invalidateCompetitions: () {
          ref.invalidate(competitionHubProvider);
          ref.invalidate(gtexCompetitionDetailProvider);
          ref.invalidate(hostedCompetitionDetailProvider);
          ref.invalidate(streamerTournamentDetailProvider);
        },
        clientFactory:
            () => GtexRealtimeClient(
              apiBaseUrl: baseUrl,
              accessTokenProvider: () => ref.read(accessTokenProvider),
            ),
      )..start();
      ref.onDispose(controller.dispose);
      return controller;
    });

class AppRealtimeSyncController {
  AppRealtimeSyncController({
    required this.enabled,
    required this.apiBaseUrl,
    required this.includeWallet,
    required this.invalidateMarket,
    required this.invalidateCompetitions,
    this.fallbackPollingInterval = const Duration(seconds: 5),
    this.fallbackActivationDelay = const Duration(seconds: 10),
    GtexRealtimeClient Function()? clientFactory,
  }) : _clientFactory =
           clientFactory ??
           (() => GtexRealtimeClient(
             apiBaseUrl: apiBaseUrl,
             accessTokenProvider: () => null,
           ));

  final bool enabled;
  final String apiBaseUrl;
  final bool includeWallet;
  final VoidCallback invalidateMarket;
  final VoidCallback invalidateCompetitions;
  final Duration fallbackPollingInterval;
  final Duration fallbackActivationDelay;
  final GtexRealtimeClient Function() _clientFactory;

  GtexRealtimeClient? _client;
  final List<StreamSubscription<Map<String, Object?>>> _eventSubscriptions =
      <StreamSubscription<Map<String, Object?>>>[];
  StreamSubscription<GtexRealtimeConnectionState>? _stateSubscription;
  Timer? _fallbackTimer;
  Timer? _fallbackActivationTimer;

  void start() {
    if (!enabled || !_hasLiveRealtimeBaseUrl(apiBaseUrl)) {
      _startFallbackPollingNow();
      return;
    }
    final GtexRealtimeClient client = _clientFactory();
    _client = client;
    _stateSubscription = client.connectionStates.listen(_handleStateChange);
    _eventSubscriptions
      ..add(
        client
            .subscribe('market')
            .listen(_handleEvent, onError: _handleStreamError),
      )
      ..add(
        client
            .subscribe('competition')
            .listen(_handleEvent, onError: _handleStreamError),
      );
    if (includeWallet) {
      _eventSubscriptions.add(
        client
            .subscribe('wallet')
            .listen(_handleEvent, onError: _handleStreamError),
      );
    }
  }

  void _handleEvent(Map<String, Object?> event) {
    final String type = (event['type'] ?? '').toString().trim().toLowerCase();
    switch (type) {
      case 'market_price_update':
      case 'wallet_update':
        invalidateMarket();
        return;
      case 'competition_update':
        invalidateCompetitions();
        return;
      default:
        return;
    }
  }

  void _handleStreamError(Object error, StackTrace stackTrace) {
    _scheduleFallbackPolling();
  }

  void _handleStateChange(GtexRealtimeConnectionState state) {
    switch (state) {
      case GtexRealtimeConnectionState.connected:
        _stopFallbackPolling();
        return;
      case GtexRealtimeConnectionState.disposed:
        _stopFallbackPolling();
        return;
      case GtexRealtimeConnectionState.connecting:
      case GtexRealtimeConnectionState.disconnected:
      case GtexRealtimeConnectionState.reconnecting:
      case GtexRealtimeConnectionState.failed:
        _scheduleFallbackPolling();
        return;
    }
  }

  void _startFallbackPollingNow() {
    _fallbackActivationTimer?.cancel();
    _fallbackActivationTimer = null;
    _fallbackTimer ??= Timer.periodic(fallbackPollingInterval, (_) {
      invalidateMarket();
      invalidateCompetitions();
    });
  }

  void _scheduleFallbackPolling() {
    if (_fallbackTimer != null || _fallbackActivationTimer != null) {
      return;
    }
    _fallbackActivationTimer = Timer(fallbackActivationDelay, () {
      _fallbackActivationTimer = null;
      _startFallbackPollingNow();
      invalidateMarket();
      invalidateCompetitions();
    });
  }

  void _stopFallbackPolling() {
    _fallbackActivationTimer?.cancel();
    _fallbackActivationTimer = null;
    _fallbackTimer?.cancel();
    _fallbackTimer = null;
  }

  Future<void> dispose() async {
    _stopFallbackPolling();
    for (final StreamSubscription<Map<String, Object?>> subscription
        in _eventSubscriptions) {
      await subscription.cancel();
    }
    _eventSubscriptions.clear();
    await _stateSubscription?.cancel();
    await _client?.dispose();
  }
}

bool _hasLiveRealtimeBaseUrl(String baseUrl) {
  final Uri? base = Uri.tryParse(baseUrl);
  if (base == null || !base.hasScheme || base.host.trim().isEmpty) {
    return false;
  }
  return base.scheme == 'http' ||
      base.scheme == 'https' ||
      base.scheme == 'ws' ||
      base.scheme == 'wss';
}
