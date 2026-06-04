import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../data/gte_api_repository.dart';
import '../../../shared/providers/auth_provider.dart';
import 'gtex_realtime_models.dart';
import 'gtex_realtime_service.dart';

final Provider<Uri?> gtexRealtimeUriProvider = Provider<Uri?>((Ref ref) {
  final String baseUrl = ref.watch(apiBaseUrlProvider);
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
  final String? accessToken = ref.watch(accessTokenProvider)?.trim();
  return base.replace(
    scheme: scheme,
    path: '/realtime/stream',
    queryParameters: <String, String>{
      'topics': 'live_pulse,notifications,activity',
      if (accessToken != null && accessToken.isNotEmpty) 'token': accessToken,
    },
  );
});

final Provider<GtexRealtimeClient?> gtexRealtimeServiceProvider =
    Provider<GtexRealtimeClient?>((Ref ref) {
      if (ref.watch(criticalBackendModeProvider) == GteBackendMode.fixture) {
        return null;
      }
      final Uri? socketUri = ref.watch(gtexRealtimeUriProvider);
      if (socketUri == null) {
        return null;
      }
      final GtexRealtimeService service = GtexRealtimeService(
        socketUri: socketUri,
      )..connect();
      ref.onDispose(() {
        unawaited(service.dispose());
      });
      return service;
    });

final StreamProvider<GtexRealtimeStatus> gtexRealtimeConnectionStateProvider =
    StreamProvider<GtexRealtimeStatus>((Ref ref) {
      final GtexRealtimeClient? service = ref.watch(
        gtexRealtimeServiceProvider,
      );
      return _statusStream(service);
    });

final StreamProvider<GtexRealtimeStatus> gtexRealtimeStatusProvider =
    gtexRealtimeConnectionStateProvider;

final StreamProvider<GtexRealtimeEvent> gtexLivePulseProvider =
    StreamProvider<GtexRealtimeEvent>((Ref ref) {
      return _eventStream(ref).where((GtexRealtimeEvent event) {
        return event.isLivePulse;
      });
    });

final StreamProvider<GtexRealtimeEvent> gtexNotificationStreamProvider =
    StreamProvider<GtexRealtimeEvent>((Ref ref) {
      return _eventStream(ref).where((GtexRealtimeEvent event) {
        return event.isNotification;
      });
    });

final StreamProvider<GtexRealtimeEvent> gtexActivityEventStreamProvider =
    StreamProvider<GtexRealtimeEvent>((Ref ref) {
      return _eventStream(ref).where((GtexRealtimeEvent event) {
        return event.isActivity;
      });
    });

Stream<GtexRealtimeStatus> _statusStream(GtexRealtimeClient? service) {
  if (service == null) {
    return Stream<GtexRealtimeStatus>.value(GtexRealtimeStatus.disconnected);
  }
  return Stream<GtexRealtimeStatus>.multi((
    MultiStreamController<GtexRealtimeStatus> controller,
  ) {
    controller.add(service.status);
    final StreamSubscription<GtexRealtimeStatus> subscription = service.statuses
        .listen(controller.add, onError: controller.addError);
    controller.onCancel = subscription.cancel;
  });
}

Stream<GtexRealtimeEvent> _eventStream(Ref ref) {
  final GtexRealtimeClient? service = ref.watch(gtexRealtimeServiceProvider);
  if (service == null) {
    return const Stream<GtexRealtimeEvent>.empty();
  }
  return service.events;
}
