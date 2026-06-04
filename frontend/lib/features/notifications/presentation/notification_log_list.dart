import 'package:flutter/material.dart';

import '../domain/notification_log_models.dart';

typedef NotificationLogItemCallback = void Function(NotificationLogItem item);

class NotificationLogList extends StatelessWidget {
  const NotificationLogList({
    super.key,
    required this.state,
    this.onNotificationTap,
    this.padding = const EdgeInsets.all(16),
    this.shrinkWrap = false,
    this.physics,
  });

  final NotificationLogState state;
  final NotificationLogItemCallback? onNotificationTap;
  final EdgeInsetsGeometry padding;
  final bool shrinkWrap;
  final ScrollPhysics? physics;

  @override
  Widget build(BuildContext context) {
    final List<Widget> children = <Widget>[
      if (state.isDegraded)
        NotificationLogDegradedBanner(reason: state.degradedReason),
      if (state.isEmpty) const NotificationLogEmptyState(),
      if (!state.isEmpty)
        for (final NotificationLogGroup group in state.groups) ...<Widget>[
          NotificationLogGroupHeader(group: group),
          for (final NotificationLogItem notification in group.notifications)
            NotificationLogTile(
              notification: notification,
              onTap:
                  onNotificationTap == null
                      ? null
                      : () => onNotificationTap!(notification),
            ),
          const SizedBox(height: 8),
        ],
    ];

    return ListView(
      padding: padding,
      shrinkWrap: shrinkWrap,
      physics: physics,
      children: children,
    );
  }
}

class NotificationLogDegradedBanner extends StatelessWidget {
  const NotificationLogDegradedBanner({super.key, this.reason});

  final String? reason;

  @override
  Widget build(BuildContext context) {
    final ColorScheme colors = Theme.of(context).colorScheme;
    final String resolvedReason =
        reason?.trim().isNotEmpty == true
            ? reason!.trim()
            : 'Showing persisted log while the websocket recovers.';
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: colors.errorContainer.withValues(alpha: 0.55),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: colors.error.withValues(alpha: 0.35)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(Icons.warning_amber_rounded, color: colors.error, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'Notification stream degraded',
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: colors.onErrorContainer,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  resolvedReason,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: colors.onErrorContainer,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class NotificationLogEmptyState extends StatelessWidget {
  const NotificationLogEmptyState({super.key});

  @override
  Widget build(BuildContext context) {
    final ColorScheme colors = Theme.of(context).colorScheme;
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 40),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Icon(
              Icons.notifications_none_outlined,
              color: colors.onSurfaceVariant,
              size: 32,
            ),
            const SizedBox(height: 12),
            Text(
              'No notifications',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 4),
            Text(
              'Backend notifications will appear here after delivery.',
              textAlign: TextAlign.center,
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: colors.onSurfaceVariant),
            ),
          ],
        ),
      ),
    );
  }
}

class NotificationLogGroupHeader extends StatelessWidget {
  const NotificationLogGroupHeader({super.key, required this.group});

  final NotificationLogGroup group;

  @override
  Widget build(BuildContext context) {
    final ColorScheme colors = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.fromLTRB(2, 12, 2, 8),
      child: Row(
        children: <Widget>[
          Expanded(
            child: Text(
              group.label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                color: colors.onSurface,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          const SizedBox(width: 8),
          NotificationLogUnreadLabel(unreadCount: group.unreadCount),
        ],
      ),
    );
  }
}

class NotificationLogUnreadLabel extends StatelessWidget {
  const NotificationLogUnreadLabel({super.key, required this.unreadCount});

  final int unreadCount;

  @override
  Widget build(BuildContext context) {
    final bool hasUnread = unreadCount > 0;
    final ColorScheme colors = Theme.of(context).colorScheme;
    final Color background =
        hasUnread ? colors.primaryContainer : colors.surfaceContainerHighest;
    final Color foreground =
        hasUnread ? colors.onPrimaryContainer : colors.onSurfaceVariant;
    return DecoratedBox(
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        child: Text(
          hasUnread ? '$unreadCount unread' : 'All read',
          style: Theme.of(context).textTheme.labelSmall?.copyWith(
            color: foreground,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
    );
  }
}

class NotificationLogTile extends StatelessWidget {
  const NotificationLogTile({
    super.key,
    required this.notification,
    this.onTap,
  });

  final NotificationLogItem notification;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final ColorScheme colors = Theme.of(context).colorScheme;
    final bool unread = notification.isUnread;
    final Color accent = unread ? colors.primary : colors.outlineVariant;
    return Card(
      elevation: 0,
      margin: const EdgeInsets.only(bottom: 8),
      color:
          unread
              ? colors.primaryContainer.withValues(alpha: 0.24)
              : colors.surface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
        side: BorderSide(color: accent.withValues(alpha: unread ? 0.42 : 0.7)),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Icon(
                unread
                    ? Icons.mark_chat_unread_outlined
                    : Icons.mark_chat_read_outlined,
                color: accent,
                size: 20,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Expanded(
                          child: Text(
                            notification.message,
                            style: Theme.of(context).textTheme.titleSmall
                                ?.copyWith(fontWeight: FontWeight.w700),
                          ),
                        ),
                        const SizedBox(width: 8),
                        _ReadStatePill(isUnread: unread),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      _metadataLine(notification),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: colors.onSurfaceVariant,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _formatTimestamp(notification.createdAt),
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: colors.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ReadStatePill extends StatelessWidget {
  const _ReadStatePill({required this.isUnread});

  final bool isUnread;

  @override
  Widget build(BuildContext context) {
    final ColorScheme colors = Theme.of(context).colorScheme;
    return DecoratedBox(
      decoration: BoxDecoration(
        color:
            isUnread
                ? colors.primary.withValues(alpha: 0.12)
                : colors.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        child: Text(
          isUnread ? 'Unread' : 'Read',
          style: Theme.of(context).textTheme.labelSmall?.copyWith(
            color: isUnread ? colors.primary : colors.onSurfaceVariant,
            fontWeight: FontWeight.w800,
          ),
        ),
      ),
    );
  }
}

String _metadataLine(NotificationLogItem notification) {
  final List<String> parts = <String>[
    notification.topic,
    if (notification.templateKey?.trim().isNotEmpty == true)
      notification.templateKey!.trim(),
    if (notification.resourceId?.trim().isNotEmpty == true)
      notification.resourceId!.trim(),
  ];
  return parts.join(' / ');
}

String _formatTimestamp(DateTime value) {
  String twoDigits(int input) => input.toString().padLeft(2, '0');
  return '${value.year}-${twoDigits(value.month)}-${twoDigits(value.day)} '
      '${twoDigits(value.hour)}:${twoDigits(value.minute)}';
}
