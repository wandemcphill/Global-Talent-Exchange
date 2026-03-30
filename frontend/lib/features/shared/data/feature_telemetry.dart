import 'dart:async';

import '../../../services/reliability/reliable_event_queue.dart';

void trackFeatureEvent({
  required String topic,
  required String name,
  Map<String, Object?> payload = const <String, Object?>{},
  String? dedupeKey,
}) {
  unawaited(
    gteReliableEventQueue.enqueue(
      topic: topic,
      name: name,
      payload: payload,
      dedupeKey: dedupeKey,
    ),
  );
}
