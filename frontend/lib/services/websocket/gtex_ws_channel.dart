import 'package:gte_frontend/shared/state/gtex_async_surface_state.dart';

import 'gtex_ws_service.dart';

class GtexWsChannel<T> {
  const GtexWsChannel({required this.topic, required this.service});

  final String topic;
  final GtexWsService<T> service;

  Stream<GtexWsMessage<T>> get messages {
    final String normalized = topic.trim();
    return service.messages.where((GtexWsMessage<T> event) {
      return event.topic == normalized;
    });
  }

  Stream<GtexSurfaceState<T>> get surfaceStates => service.surfaceStates;

  void publish(Object data) {
    service.send(<String, Object?>{
      'type': 'publish',
      'topic': topic,
      'data': data,
    });
  }
}
