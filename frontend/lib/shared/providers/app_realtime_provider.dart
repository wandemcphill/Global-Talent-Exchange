import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/gte_app_config.dart';
import '../../data/gte_api_repository.dart';
import '../../features/competitions/live_competitions_provider.dart';
import '../../features/transfer_market/live_market_provider.dart';
import '../../services/reliability/reliable_websocket_manager.dart';
import 'auth_provider.dart';

final Provider<AppRealtimeSyncController> appRealtimeSyncProvider =
    Provider<AppRealtimeSyncController>((Ref ref) {
      final GteBackendMode mode = ref.watch(criticalBackendModeProvider);
      final String baseUrl = ref.watch(apiBaseUrlProvider);
      final String? accessToken = ref.watch(accessTokenProvider);
      final controller = AppRealtimeSyncController(
        enabled: mode != GteBackendMode.fixture,
        socketUri: _buildRealtimeUri(baseUrl, accessToken: accessToken),
        invalidateMarket: () => ref.invalidate(marketDashboardProvider),
        invalidateCompetitions: () {
          ref.invalidate(competitionHubProvider);
          ref.invalidate(gtexCompetitionDetailProvider);
          ref.invalidate(hostedCompetitionDetailProvider);
          ref.invalidate(streamerTournamentDetailProvider);
        },
      )..start();
      ref.onDispose(controller.dispose);
      return controller;
    });

class AppRealtimeSyncController {
  AppRealtimeSyncController({
    required this.enabled,
    required this.socketUri,
    required this.invalidateMarket,
    required this.invalidateCompetitions,
    this.fallbackPollingInterval = const Duration(seconds: 5),
    this.fallbackActivationDelay = const Duration(seconds: 10),
    ReliableWebSocketManager Function(Uri socketUri)? managerFactory,
  }) : _managerFactory =
           managerFactory ??
           ((Uri socketUri) => ReliableWebSocketManager(socketUri: socketUri));

  final bool enabled;
  final Uri? socketUri;
  final VoidCallback invalidateMarket;
  final VoidCallback invalidateCompetitions;
  final Duration fallbackPollingInterval;
  final Duration fallbackActivationDelay;
  final ReliableWebSocketManager Function(Uri socketUri) _managerFactory;

  ReliableWebSocketManager? _manager;
  StreamSubscription<dynamic>? _messageSubscription;
  StreamSubscription<ReliableWebSocketState>? _stateSubscription;
  Timer? _fallbackTimer;
  Timer? _fallbackActivationTimer;

  void start() {
    if (!enabled || socketUri == null) {
      _startFallbackPollingNow();
      return;
    }
    final ReliableWebSocketManager manager = _managerFactory(socketUri!);
    _manager = manager;
    _messageSubscription = manager.messages.listen(_handleMessage);
    _stateSubscription = manager.connectionStates.listen(_handleStateChange);
    manager.connect();
  }

  void _handleMessage(dynamic rawMessage) {
    final Object? decoded = _decodeMessage(rawMessage);
    if (decoded is! Map) {
      return;
    }
    final String type = (decoded['type'] ?? '').toString().trim().toLowerCase();
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

  void _handleStateChange(ReliableWebSocketState state) {
    switch (state) {
      case ReliableWebSocketState.connected:
        _stopFallbackPolling();
        return;
      case ReliableWebSocketState.paused:
      case ReliableWebSocketState.disposed:
        _stopFallbackPolling();
        return;
      case ReliableWebSocketState.connecting:
      case ReliableWebSocketState.disconnected:
      case ReliableWebSocketState.reconnecting:
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
    await _messageSubscription?.cancel();
    await _stateSubscription?.cancel();
    await _manager?.dispose();
  }
}

Uri? _buildRealtimeUri(String baseUrl, {required String? accessToken}) {
  final Uri? base = Uri.tryParse(baseUrl);
  if (base == null || !base.hasScheme || base.host.trim().isEmpty) {
    return null;
  }
  final String scheme = switch (base.scheme) {
    'https' => 'wss',
    'http' => 'ws',
    'ws' || 'wss' => base.scheme,
    _ => 'wss',
  };
  final List<String> topics = <String>['market', 'competition'];
  if (accessToken != null && accessToken.trim().isNotEmpty) {
    topics.add('wallet');
  }
  return base.replace(
    scheme: scheme,
    path: '/realtime/stream',
    queryParameters: <String, String>{
      'topics': topics.join(','),
      if (accessToken != null && accessToken.trim().isNotEmpty)
        'token': accessToken.trim(),
    },
  );
}

Object? _decodeMessage(dynamic rawMessage) {
  if (rawMessage is String) {
    final String trimmed = rawMessage.trim();
    if (trimmed.isEmpty) {
      return null;
    }
    try {
      return jsonDecode(trimmed);
    } catch (_) {
      return null;
    }
  }
  return rawMessage;
}
