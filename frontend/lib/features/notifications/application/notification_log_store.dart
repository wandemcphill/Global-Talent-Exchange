import 'dart:async';

import 'package:flutter/foundation.dart';

import '../domain/notification_log_models.dart';
import '../domain/notification_log_parser.dart';

NotificationLogState reduceNotificationLogState(
  NotificationLogState state,
  NotificationLogEvent event,
) {
  final DateTime? eventAt = event.receivedAt;
  switch (event.type) {
    case NotificationLogEventType.snapshot:
      return state.copyWith(
        notifications: event.notifications,
        lastEventAt: eventAt,
      );
    case NotificationLogEventType.upsert:
      final NotificationLogItem? next = event.notification;
      if (next == null) {
        return state;
      }
      final Map<String, NotificationLogItem> byId =
          <String, NotificationLogItem>{
            for (final NotificationLogItem item in state.notifications)
              item.notificationId: item,
          };
      byId[next.notificationId] = next;
      return state.copyWith(notifications: byId.values, lastEventAt: eventAt);
    case NotificationLogEventType.markRead:
      final String? notificationId = event.notificationId?.trim();
      if (notificationId == null || notificationId.isEmpty) {
        return state;
      }
      return state.copyWith(
        notifications: state.notifications.map((NotificationLogItem item) {
          if (item.notificationId != notificationId) {
            return item;
          }
          return item.copyWith(isRead: true, readAt: event.readAt);
        }),
        lastEventAt: eventAt,
      );
    case NotificationLogEventType.markAllRead:
      return state.copyWith(
        notifications: state.notifications.map((NotificationLogItem item) {
          return item.copyWith(isRead: true, readAt: event.readAt);
        }),
        lastEventAt: eventAt,
      );
    case NotificationLogEventType.remove:
      final String? notificationId = event.notificationId?.trim();
      if (notificationId == null || notificationId.isEmpty) {
        return state;
      }
      return state.copyWith(
        notifications: state.notifications.where((NotificationLogItem item) {
          return item.notificationId != notificationId;
        }),
        lastEventAt: eventAt,
      );
    case NotificationLogEventType.connectionChanged:
      final NotificationLogConnectionState? connectionState =
          event.connectionState;
      if (connectionState == null) {
        return state;
      }
      return state.copyWith(
        connectionState: connectionState,
        degradedReason:
            connectionState.isDegraded ? event.degradedReason : null,
        clearDegradedReason: !connectionState.isDegraded,
        lastEventAt: eventAt,
      );
    case NotificationLogEventType.noop:
      return state;
  }
}

class NotificationLogStore extends ChangeNotifier {
  NotificationLogStore({NotificationLogState? initialState})
    : _state = initialState ?? NotificationLogState();

  NotificationLogState _state;
  StreamSubscription<Object?>? _subscription;

  NotificationLogState get state => _state;

  int get unreadCount => _state.unreadCount;

  List<NotificationLogGroup> get groups => _state.groups;

  void applyEvent(NotificationLogEvent event) {
    final NotificationLogState next = reduceNotificationLogState(_state, event);
    if (identical(next, _state)) {
      return;
    }
    _state = next;
    notifyListeners();
  }

  bool applyBackendPayload(Object? payload, {DateTime? receivedAt}) {
    final NotificationLogEvent? event = parseNotificationLogBackendMessage(
      payload,
      receivedAt: receivedAt,
    );
    if (event == null) {
      return false;
    }
    applyEvent(event);
    return event.type != NotificationLogEventType.noop;
  }

  void hydrate(Iterable<NotificationLogItem> notifications) {
    applyEvent(
      NotificationLogEvent(
        type: NotificationLogEventType.snapshot,
        notifications: List<NotificationLogItem>.unmodifiable(notifications),
        receivedAt: DateTime.now().toUtc(),
        rawType: 'hydrate',
      ),
    );
  }

  void setConnectionState(
    NotificationLogConnectionState connectionState, {
    String? degradedReason,
  }) {
    applyEvent(
      NotificationLogEvent(
        type: NotificationLogEventType.connectionChanged,
        connectionState: connectionState,
        degradedReason: degradedReason,
        receivedAt: DateTime.now().toUtc(),
        rawType: 'connection_state',
      ),
    );
  }

  void bindBackendStream(Stream<Object?> stream, {bool markConnecting = true}) {
    unawaited(_subscription?.cancel());
    if (markConnecting) {
      setConnectionState(NotificationLogConnectionState.connecting);
    }
    _subscription = stream.listen(
      (Object? payload) {
        applyBackendPayload(payload);
      },
      onError: (Object error, StackTrace stackTrace) {
        setConnectionState(
          NotificationLogConnectionState.degraded,
          degradedReason: error.toString(),
        );
      },
      onDone: () {
        setConnectionState(NotificationLogConnectionState.disconnected);
      },
    );
  }

  Future<void> unbindBackendStream() async {
    final StreamSubscription<Object?>? subscription = _subscription;
    _subscription = null;
    await subscription?.cancel();
  }

  @override
  void dispose() {
    unawaited(_subscription?.cancel());
    _subscription = null;
    super.dispose();
  }
}
