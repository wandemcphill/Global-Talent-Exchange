import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:gte_frontend/shared/realtime/realtime.dart' as shared;

export 'package:gte_frontend/shared/realtime/gtex_realtime_models.dart';
export 'package:gte_frontend/shared/realtime/gtex_realtime_service.dart';

final Provider<Uri?> gtexRealtimeUriProvider =
    shared.gtexRealtimeEndpointProvider;

final Provider<shared.GtexRealtimeClient?> gtexRealtimeServiceProvider =
    shared.gtexRealtimeClientProvider;

final StreamProvider<shared.GtexRealtimeStatus>
gtexRealtimeConnectionStateProvider =
    shared.gtexRealtimeConnectionStatusProvider;

final StreamProvider<shared.GtexRealtimeStatus> gtexRealtimeStatusProvider =
    gtexRealtimeConnectionStateProvider;

final StreamProvider<shared.GtexRealtimeEvent> gtexLivePulseProvider =
    shared.gtexRealtimeLivePulseProvider;

final StreamProvider<shared.GtexRealtimeEvent> gtexNotificationStreamProvider =
    shared.gtexRealtimeNotificationStreamProvider;

final StreamProvider<shared.GtexRealtimeEvent> gtexActivityEventStreamProvider =
    shared.gtexRealtimeActivityStreamProvider;
