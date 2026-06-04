import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../realtime/gtex_realtime_models.dart';
import '../realtime/gtex_realtime_service.dart';

final gtexRealtimeEndpointProvider = Provider<Uri?>((Ref ref) => null);

final gtexRealtimeServiceProvider = Provider<GtexRealtimeService>((Ref ref) {
  final GtexRealtimeService service = GtexRealtimeService();
  final Uri? endpoint = ref.watch(gtexRealtimeEndpointProvider);
  if (endpoint != null) {
    service.connect(endpoint);
  }
  ref.onDispose(() {
    unawaited(service.dispose());
  });
  return service;
});

final gtexRealtimeStatusProvider = StreamProvider<GtexRealtimeStatus>((
  Ref ref,
) {
  return ref.watch(gtexRealtimeServiceProvider).statusStream;
});

final gtexLivePulseProvider = StreamProvider<GtexRealtimeEvent>((Ref ref) {
  return ref.watch(gtexRealtimeServiceProvider).livePulseStream;
});

final gtexNotificationStreamProvider = StreamProvider<GtexRealtimeEvent>((
  Ref ref,
) {
  return ref.watch(gtexRealtimeServiceProvider).notificationStream;
});

final gtexActivityStreamProvider = StreamProvider<GtexRealtimeEvent>((Ref ref) {
  return ref.watch(gtexRealtimeServiceProvider).activityStream;
});
