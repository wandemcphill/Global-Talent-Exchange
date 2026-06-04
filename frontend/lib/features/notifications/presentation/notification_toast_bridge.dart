import 'package:flutter/widgets.dart';

import '../../shell/domain/gtex_surface_state.dart';
import '../../shell/widgets/gtex_toast_host.dart';
import '../domain/notification_log_models.dart';

class NotificationLogToastIntent {
  const NotificationLogToastIntent({
    required this.id,
    required this.title,
    required this.message,
    required this.notificationId,
    required this.groupKey,
    required this.createdAt,
    this.actionLabel = 'Open',
  });

  final String id;
  final String title;
  final String message;
  final String notificationId;
  final String groupKey;
  final DateTime createdAt;
  final String? actionLabel;

  factory NotificationLogToastIntent.fromNotification(
    NotificationLogItem notification, {
    String? actionLabel = 'Open',
  }) {
    return NotificationLogToastIntent(
      id: 'notification:${notification.notificationId}',
      title: notification.groupLabel,
      message: notification.message,
      notificationId: notification.notificationId,
      groupKey: notification.groupKey,
      createdAt: notification.createdAt,
      actionLabel: actionLabel,
    );
  }
}

NotificationLogToastIntent? notificationToastIntentForEvent(
  NotificationLogEvent event, {
  bool includeReadNotifications = false,
  String? actionLabel = 'Open',
}) {
  if (event.type != NotificationLogEventType.upsert) {
    return null;
  }
  final NotificationLogItem? notification = event.notification;
  if (notification == null) {
    return null;
  }
  if (!includeReadNotifications && notification.isRead) {
    return null;
  }
  return NotificationLogToastIntent.fromNotification(
    notification,
    actionLabel: actionLabel,
  );
}

List<NotificationLogToastIntent> notificationToastIntentsForEvents(
  Iterable<NotificationLogEvent> events, {
  bool includeReadNotifications = false,
  String? actionLabel = 'Open',
}) {
  return events
      .map(
        (NotificationLogEvent event) => notificationToastIntentForEvent(
          event,
          includeReadNotifications: includeReadNotifications,
          actionLabel: actionLabel,
        ),
      )
      .whereType<NotificationLogToastIntent>()
      .toList(growable: false);
}

extension NotificationLogToastIntentGtexToast on NotificationLogToastIntent {
  GtexToastEntry toGtexToastEntry({VoidCallback? onAction}) {
    return GtexToastEntry(
      id: id,
      title: title,
      message: message,
      state: GtexSurfaceState.confirmed,
      actionLabel: onAction == null ? null : actionLabel,
      onAction: onAction,
    );
  }
}
