import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/gte_api_repository.dart';
import '../providers/auth_provider.dart';
import 'gtex_realtime_models.dart';
import 'gtex_realtime_service.dart';

const List<String> gtexDefaultRealtimeTopics = <String>[
  'live_pulse',
  'notifications',
  'activity',
];

final Provider<List<String>> gtexRealtimeTopicsProvider =
    Provider<List<String>>((Ref ref) {
      return gtexDefaultRealtimeTopics;
    });

final Provider<Uri?> gtexRealtimeEndpointProvider = Provider<Uri?>((Ref ref) {
  final String baseUrl = ref.watch(apiBaseUrlProvider);
  final String? accessToken = ref.watch(accessTokenProvider);
  final List<String> topics = ref.watch(gtexRealtimeTopicsProvider);
  return buildGtexRealtimeUri(
    baseUrl,
    accessToken: accessToken,
    topics: topics,
  );
});

final Provider<GtexRealtimeClient?> gtexRealtimeClientProvider =
    Provider<GtexRealtimeClient?>((Ref ref) {
      if (ref.watch(criticalBackendModeProvider) == GteBackendMode.fixture) {
        return null;
      }
      final Uri? socketUri = ref.watch(gtexRealtimeEndpointProvider);
      if (socketUri == null) {
        return null;
      }
      final GtexRealtimeService service = GtexRealtimeService(
        socketUri: socketUri,
        topics: ref.watch(gtexRealtimeTopicsProvider),
      )..connect();
      ref.onDispose(() {
        unawaited(service.dispose());
      });
      return service;
    });

final StreamProvider<GtexRealtimeStatus> gtexRealtimeConnectionStatusProvider =
    StreamProvider<GtexRealtimeStatus>((Ref ref) {
      final GtexRealtimeClient? client = ref.watch(gtexRealtimeClientProvider);
      return _statusStream(client);
    });

final StreamProvider<GtexRealtimeEvent> gtexRealtimeLivePulseProvider =
    StreamProvider<GtexRealtimeEvent>((Ref ref) {
      return _eventStream(ref).where((GtexRealtimeEvent event) {
        return event.isLivePulse;
      });
    });

final StreamProvider<GtexRealtimeEvent> gtexRealtimeNotificationStreamProvider =
    StreamProvider<GtexRealtimeEvent>((Ref ref) {
      return _eventStream(ref).where((GtexRealtimeEvent event) {
        return event.isNotification;
      });
    });

final StreamProvider<GtexRealtimeEvent> gtexRealtimeActivityStreamProvider =
    StreamProvider<GtexRealtimeEvent>((Ref ref) {
      return _eventStream(ref).where((GtexRealtimeEvent event) {
        return event.isActivity;
      });
    });

Uri? buildGtexRealtimeUri(
  String baseUrl, {
  String? accessToken,
  Iterable<String> topics = gtexDefaultRealtimeTopics,
}) {
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
  final String topicList = topics
      .map((String topic) => topic.trim())
      .where((String topic) => topic.isNotEmpty)
      .join(',');
  return base.replace(
    scheme: scheme,
    path: '/realtime/stream',
    queryParameters: <String, String>{
      if (topicList.isNotEmpty) 'topics': topicList,
      if (accessToken != null && accessToken.trim().isNotEmpty)
        'token': accessToken.trim(),
    },
  );
}

Stream<GtexRealtimeStatus> _statusStream(GtexRealtimeClient? client) {
  if (client == null) {
    return Stream<GtexRealtimeStatus>.value(GtexRealtimeStatus.disconnected);
  }
  return Stream<GtexRealtimeStatus>.multi((
    MultiStreamController<GtexRealtimeStatus> controller,
  ) {
    controller.add(client.status);
    final StreamSubscription<GtexRealtimeStatus> subscription = client.statuses
        .listen(controller.add, onError: controller.addError);
    controller.onCancel = subscription.cancel;
  });
}

Stream<GtexRealtimeEvent> _eventStream(Ref ref) {
  final GtexRealtimeClient? client = ref.watch(gtexRealtimeClientProvider);
  if (client == null) {
    return const Stream<GtexRealtimeEvent>.empty();
  }
  return client.events;
}
