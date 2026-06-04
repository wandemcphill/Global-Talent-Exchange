import 'package:flutter/material.dart';

import '../domain/gtex_surface_state.dart';
import '../realtime/gtex_realtime_models.dart';
import 'gtex_state_panel.dart';

enum GtexRealtimeEventStreamKind { notifications, activity }

class GtexConnectionStatusBadge extends StatelessWidget {
  const GtexConnectionStatusBadge({
    super.key,
    required this.status,
    this.label,
    this.compact = false,
    this.tooltip,
  });

  factory GtexConnectionStatusBadge.fromSurfaceState({
    Key? key,
    required GtexSurfaceState state,
    String? label,
    bool compact = false,
    String? tooltip,
  }) {
    return GtexConnectionStatusBadge(
      key: key,
      status: _statusForSurfaceState(state),
      label: label,
      compact: compact,
      tooltip: tooltip,
    );
  }

  final GtexRealtimeStatus status;
  final String? label;
  final bool compact;
  final String? tooltip;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final Color tone = _toneForStatus(theme, status);
    final String resolvedLabel = _clean(label) ?? status.label;
    return Semantics(
      liveRegion: status.requiresAttention,
      label: 'Connection status $resolvedLabel',
      child: Tooltip(
        message: tooltip ?? 'Connection status: $resolvedLabel',
        child: Container(
          height: 38,
          constraints: BoxConstraints(maxWidth: compact ? 154 : 220),
          padding: EdgeInsets.symmetric(horizontal: compact ? 9 : 10),
          decoration: BoxDecoration(
            color: tone.withValues(alpha: 0.10),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: tone.withValues(alpha: 0.28)),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Icon(_iconForStatus(status), color: tone, size: 16),
              if (!compact) ...<Widget>[
                const SizedBox(width: 8),
                Flexible(
                  child: Text(
                    resolvedLabel,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: theme.textTheme.labelLarge?.copyWith(
                      color: tone,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 0,
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class GtexNotificationStream extends StatelessWidget {
  const GtexNotificationStream({
    super.key,
    required this.events,
    this.state = GtexSurfaceState.confirmed,
    this.title,
    this.emptyTitle,
    this.emptyMessage,
    this.maxItems = 6,
    this.onEventSelected,
  });

  final Iterable<GtexRealtimeEvent> events;
  final GtexSurfaceState state;
  final String? title;
  final String? emptyTitle;
  final String? emptyMessage;
  final int maxItems;
  final ValueChanged<GtexRealtimeEvent>? onEventSelected;

  @override
  Widget build(BuildContext context) {
    return GtexRealtimeEventList(
      events: events,
      kind: GtexRealtimeEventStreamKind.notifications,
      state: state,
      title: title,
      emptyTitle: emptyTitle,
      emptyMessage: emptyMessage,
      maxItems: maxItems,
      onEventSelected: onEventSelected,
    );
  }
}

class GtexActivityEventStream extends StatelessWidget {
  const GtexActivityEventStream({
    super.key,
    required this.events,
    this.state = GtexSurfaceState.confirmed,
    this.title,
    this.emptyTitle,
    this.emptyMessage,
    this.maxItems = 6,
    this.onEventSelected,
  });

  final Iterable<GtexRealtimeEvent> events;
  final GtexSurfaceState state;
  final String? title;
  final String? emptyTitle;
  final String? emptyMessage;
  final int maxItems;
  final ValueChanged<GtexRealtimeEvent>? onEventSelected;

  @override
  Widget build(BuildContext context) {
    return GtexRealtimeEventList(
      events: events,
      kind: GtexRealtimeEventStreamKind.activity,
      state: state,
      title: title,
      emptyTitle: emptyTitle,
      emptyMessage: emptyMessage,
      maxItems: maxItems,
      onEventSelected: onEventSelected,
    );
  }
}

class GtexRealtimeEventList extends StatelessWidget {
  const GtexRealtimeEventList({
    super.key,
    required this.events,
    required this.kind,
    this.state = GtexSurfaceState.confirmed,
    this.title,
    this.emptyTitle,
    this.emptyMessage,
    this.maxItems = 6,
    this.onEventSelected,
  });

  final Iterable<GtexRealtimeEvent> events;
  final GtexRealtimeEventStreamKind kind;
  final GtexSurfaceState state;
  final String? title;
  final String? emptyTitle;
  final String? emptyMessage;
  final int maxItems;
  final ValueChanged<GtexRealtimeEvent>? onEventSelected;

  @override
  Widget build(BuildContext context) {
    final List<GtexRealtimeEvent> visibleEvents = events
        .where((GtexRealtimeEvent event) => _matchesKind(kind, event))
        .take(maxItems)
        .toList(growable: false);
    if (visibleEvents.isEmpty) {
      final GtexSurfaceState effectiveState =
          _isConfirmedLike(state) ? GtexSurfaceState.empty : state;
      return GtexStatePanel(
        state: effectiveState,
        eyebrow: _streamEyebrow(kind),
        title: emptyTitle ?? _emptyTitle(kind),
        message: emptyMessage ?? _emptyMessage(kind),
        icon: _emptyIcon(kind),
      );
    }

    final ThemeData theme = Theme.of(context);
    final Color tone = _toneForSurfaceState(theme, state);
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        Row(
          children: <Widget>[
            Icon(_headerIcon(kind), color: tone, size: 18),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                (title ?? _streamTitle(kind)).toUpperCase(),
                overflow: TextOverflow.ellipsis,
                style: theme.textTheme.labelLarge?.copyWith(
                  color: tone,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 0,
                ),
              ),
            ),
            _RealtimeStateBadge(state: state),
          ],
        ),
        if (!_isConfirmedLike(state)) ...<Widget>[
          const SizedBox(height: 10),
          _InlineStateBanner(state: state),
        ],
        const SizedBox(height: 10),
        ListView.separated(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: visibleEvents.length,
          separatorBuilder:
              (BuildContext context, int index) => const SizedBox(height: 8),
          itemBuilder: (BuildContext context, int index) {
            final GtexRealtimeEvent event = visibleEvents[index];
            return _RealtimeEventTile(
              event: event,
              kind: kind,
              onTap:
                  onEventSelected == null
                      ? null
                      : () => onEventSelected!(event),
            );
          },
        ),
      ],
    );
  }
}

class GtexLivePulseCard extends StatelessWidget {
  const GtexLivePulseCard({
    super.key,
    this.event,
    this.state = GtexSurfaceState.confirmed,
    this.onSelected,
  });

  final GtexRealtimeEvent? event;
  final GtexSurfaceState state;
  final ValueChanged<GtexRealtimeEvent>? onSelected;

  @override
  Widget build(BuildContext context) {
    final GtexRealtimeEvent? pulse =
        event != null && event!.isLivePulse ? event : null;
    if (pulse == null) {
      final GtexSurfaceState effectiveState =
          _isConfirmedLike(state) ? GtexSurfaceState.empty : state;
      return GtexStatePanel(
        state: effectiveState,
        eyebrow: 'LIVE PULSE',
        title: 'No live pulse',
        message: 'Waiting for the backend live_pulse stream.',
        icon: Icons.monitor_heart_outlined,
      );
    }

    final ThemeData theme = Theme.of(context);
    final Color tone = _toneForSurfaceState(theme, _eventSurfaceState(pulse));
    final String title =
        _firstPayloadString(pulse, const <String>[
          'headline',
          'title',
          'summary',
          'name',
        ]) ??
        'Live pulse event';
    final String detail =
        _firstPayloadString(pulse, const <String>[
          'message',
          'detail',
          'description',
          'body',
          'summary',
        ]) ??
        'Live pulse payload received from ${pulse.topic}.';

    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: onSelected == null ? null : () => onSelected!(pulse),
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: tone.withValues(alpha: 0.07),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: tone.withValues(alpha: 0.22)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Row(
                children: <Widget>[
                  Icon(Icons.monitor_heart_outlined, color: tone, size: 18),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'LIVE PULSE',
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.labelLarge?.copyWith(
                        color: tone,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 0,
                      ),
                    ),
                  ),
                  _RealtimeStateBadge(state: _eventSurfaceState(pulse)),
                ],
              ),
              const SizedBox(height: 10),
              Text(
                title,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: theme.textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w900,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                detail,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: theme.colorScheme.onSurface.withValues(alpha: 0.72),
                  height: 1.32,
                ),
              ),
              const SizedBox(height: 10),
              Text(
                _eventMeta(pulse),
                overflow: TextOverflow.ellipsis,
                style: theme.textTheme.labelSmall?.copyWith(
                  color: theme.colorScheme.onSurface.withValues(alpha: 0.58),
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _RealtimeEventTile extends StatelessWidget {
  const _RealtimeEventTile({
    required this.event,
    required this.kind,
    required this.onTap,
  });

  final GtexRealtimeEvent event;
  final GtexRealtimeEventStreamKind kind;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final GtexSurfaceState state = _eventSurfaceState(event);
    final Color tone = _toneForSurfaceState(theme, state);
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: tone.withValues(alpha: 0.06),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: tone.withValues(alpha: 0.18)),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Container(
                width: 34,
                height: 34,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: tone.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(_tileIcon(kind, state), color: tone, size: 18),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    Text(
                      _eventTitle(event, kind),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 5),
                    Text(
                      _eventDetail(event, kind),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurface.withValues(
                          alpha: 0.68,
                        ),
                        height: 1.25,
                      ),
                    ),
                    const SizedBox(height: 7),
                    Text(
                      _eventMeta(event),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.labelSmall?.copyWith(
                        color: theme.colorScheme.onSurface.withValues(
                          alpha: 0.54,
                        ),
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              _RealtimeStateBadge(state: state, compact: true),
            ],
          ),
        ),
      ),
    );
  }
}

class _InlineStateBanner extends StatelessWidget {
  const _InlineStateBanner({required this.state});

  final GtexSurfaceState state;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final Color tone = _toneForSurfaceState(theme, state);
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: tone.withValues(alpha: 0.07),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: tone.withValues(alpha: 0.2)),
      ),
      child: Row(
        children: <Widget>[
          Icon(_iconForSurfaceState(state), color: tone, size: 18),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              _stateMessage(state),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: theme.textTheme.bodySmall?.copyWith(height: 1.25),
            ),
          ),
        ],
      ),
    );
  }
}

class _RealtimeStateBadge extends StatelessWidget {
  const _RealtimeStateBadge({required this.state, this.compact = false});

  final GtexSurfaceState state;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final Color tone = _toneForSurfaceState(theme, state);
    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: compact ? 7 : 8,
        vertical: compact ? 4 : 5,
      ),
      decoration: BoxDecoration(
        color: tone.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: tone.withValues(alpha: 0.22)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(_iconForSurfaceState(state), color: tone, size: 13),
          if (!compact) ...<Widget>[
            const SizedBox(width: 5),
            Text(
              state.name.toUpperCase(),
              style: theme.textTheme.labelSmall?.copyWith(
                color: tone,
                fontWeight: FontWeight.w900,
                letterSpacing: 0,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

bool _matchesKind(GtexRealtimeEventStreamKind kind, GtexRealtimeEvent event) {
  switch (kind) {
    case GtexRealtimeEventStreamKind.notifications:
      return event.isNotification;
    case GtexRealtimeEventStreamKind.activity:
      return event.isActivity;
  }
}

String _eventTitle(GtexRealtimeEvent event, GtexRealtimeEventStreamKind kind) {
  return _firstPayloadString(event, const <String>[
        'title',
        'headline',
        'subject',
        'summary',
        'label',
        'name',
      ]) ??
      switch (kind) {
        GtexRealtimeEventStreamKind.notifications => 'Notification event',
        GtexRealtimeEventStreamKind.activity => 'Activity event',
      };
}

String _eventDetail(GtexRealtimeEvent event, GtexRealtimeEventStreamKind kind) {
  final String? detail = _firstPayloadString(event, const <String>[
    'message',
    'detail',
    'description',
    'body',
    'summary',
  ]);
  if (detail != null) {
    return detail;
  }
  if (kind == GtexRealtimeEventStreamKind.activity) {
    final String? actor = _firstPayloadString(event, const <String>[
      'actor',
      'user',
      'username',
    ]);
    final String? action = _firstPayloadString(event, const <String>[
      'action',
      'verb',
      'event',
    ]);
    if (actor != null && action != null) {
      return '$actor $action';
    }
  }
  return 'Event payload received from ${event.topic}.';
}

String _eventMeta(GtexRealtimeEvent event) {
  final List<String> parts = <String>[
    event.topic,
    if (_clean(event.id) != null) _clean(event.id)!,
    event.timestamp == null ? 'time pending' : _timeLabel(event.timestamp!),
  ];
  return parts.join(' - ');
}

String? _firstPayloadString(GtexRealtimeEvent event, List<String> keys) {
  for (final String key in keys) {
    final String? value = _clean(event.payload[key]?.toString());
    if (value != null) {
      return value;
    }
  }
  return null;
}

GtexSurfaceState _eventSurfaceState(GtexRealtimeEvent event) {
  final List<Object?> hints = <Object?>[
    event.payload['surface_state'],
    event.payload['state'],
    event.payload['status'],
    event.payload['connection_status'],
    event.statusHint,
  ];
  for (final Object? hint in hints) {
    final GtexSurfaceState? state = _surfaceStateFrom(hint);
    if (state != null) {
      return state;
    }
  }
  return GtexSurfaceState.confirmed;
}

bool _isConfirmedLike(GtexSurfaceState state) {
  return state == GtexSurfaceState.confirmed || state == GtexSurfaceState.data;
}

GtexSurfaceState? _surfaceStateFrom(Object? value) {
  if (value is GtexSurfaceState) {
    return value;
  }
  if (value is GtexRealtimeStatus) {
    return _surfaceStateForStatus(value);
  }
  final String normalized = value?.toString().trim().toLowerCase() ?? '';
  if (normalized.isEmpty) {
    return null;
  }
  final GtexRealtimeStatus? status = gtexRealtimeStatusFrom(normalized);
  if (status != null) {
    return _surfaceStateForStatus(status);
  }
  for (final GtexSurfaceState state in GtexSurfaceState.values) {
    if (state.name == normalized.replaceAll('-', '_')) {
      return state;
    }
  }
  return null;
}

GtexSurfaceState _surfaceStateForStatus(GtexRealtimeStatus status) {
  switch (status) {
    case GtexRealtimeStatus.disconnected:
      return GtexSurfaceState.empty;
    case GtexRealtimeStatus.connecting:
      return GtexSurfaceState.loading;
    case GtexRealtimeStatus.live:
      return GtexSurfaceState.confirmed;
    case GtexRealtimeStatus.syncing:
      return GtexSurfaceState.syncing;
    case GtexRealtimeStatus.reconnecting:
      return GtexSurfaceState.reconnecting;
    case GtexRealtimeStatus.degraded:
      return GtexSurfaceState.degraded;
    case GtexRealtimeStatus.error:
      return GtexSurfaceState.error;
  }
}

GtexRealtimeStatus _statusForSurfaceState(GtexSurfaceState state) {
  switch (state) {
    case GtexSurfaceState.loading:
      return GtexRealtimeStatus.connecting;
    case GtexSurfaceState.empty:
    case GtexSurfaceState.blocked:
      return GtexRealtimeStatus.disconnected;
    case GtexSurfaceState.pending:
    case GtexSurfaceState.syncing:
      return GtexRealtimeStatus.syncing;
    case GtexSurfaceState.reconnecting:
      return GtexRealtimeStatus.reconnecting;
    case GtexSurfaceState.degraded:
      return GtexRealtimeStatus.degraded;
    case GtexSurfaceState.confirmed:
      return GtexRealtimeStatus.live;
    case GtexSurfaceState.error:
      return GtexRealtimeStatus.error;
  }
}

Color _toneForStatus(ThemeData theme, GtexRealtimeStatus status) {
  return _toneForSurfaceState(theme, _surfaceStateForStatus(status));
}

Color _toneForSurfaceState(ThemeData theme, GtexSurfaceState state) {
  switch (state) {
    case GtexSurfaceState.loading:
    case GtexSurfaceState.syncing:
      return theme.colorScheme.primary;
    case GtexSurfaceState.empty:
      return theme.colorScheme.onSurfaceVariant;
    case GtexSurfaceState.pending:
    case GtexSurfaceState.reconnecting:
      return const Color(0xFFFFD75B);
    case GtexSurfaceState.degraded:
      return const Color(0xFFFFB35C);
    case GtexSurfaceState.confirmed:
      return const Color(0xFF69F3A4);
    case GtexSurfaceState.blocked:
    case GtexSurfaceState.error:
      return theme.colorScheme.error;
  }
}

IconData _iconForStatus(GtexRealtimeStatus status) {
  switch (status) {
    case GtexRealtimeStatus.disconnected:
      return Icons.wifi_off_rounded;
    case GtexRealtimeStatus.connecting:
      return Icons.wifi_tethering_rounded;
    case GtexRealtimeStatus.live:
      return Icons.sensors_rounded;
    case GtexRealtimeStatus.syncing:
      return Icons.sync_rounded;
    case GtexRealtimeStatus.reconnecting:
      return Icons.wifi_find_rounded;
    case GtexRealtimeStatus.degraded:
      return Icons.signal_wifi_statusbar_connected_no_internet_4;
    case GtexRealtimeStatus.error:
      return Icons.error_outline_rounded;
  }
}

IconData _iconForSurfaceState(GtexSurfaceState state) {
  switch (state) {
    case GtexSurfaceState.loading:
      return Icons.hourglass_empty_rounded;
    case GtexSurfaceState.empty:
      return Icons.inbox_outlined;
    case GtexSurfaceState.blocked:
      return Icons.lock_outline_rounded;
    case GtexSurfaceState.pending:
      return Icons.pending_actions_outlined;
    case GtexSurfaceState.syncing:
      return Icons.sync_rounded;
    case GtexSurfaceState.reconnecting:
      return Icons.wifi_find_rounded;
    case GtexSurfaceState.degraded:
      return Icons.warning_amber_rounded;
    case GtexSurfaceState.confirmed:
      return Icons.verified_outlined;
    case GtexSurfaceState.error:
      return Icons.error_outline_rounded;
  }
}

IconData _headerIcon(GtexRealtimeEventStreamKind kind) {
  switch (kind) {
    case GtexRealtimeEventStreamKind.notifications:
      return Icons.notifications_none_rounded;
    case GtexRealtimeEventStreamKind.activity:
      return Icons.timeline_rounded;
  }
}

IconData _tileIcon(GtexRealtimeEventStreamKind kind, GtexSurfaceState state) {
  if (state.requiresAttention) {
    return _iconForSurfaceState(state);
  }
  return _headerIcon(kind);
}

IconData _emptyIcon(GtexRealtimeEventStreamKind kind) {
  switch (kind) {
    case GtexRealtimeEventStreamKind.notifications:
      return Icons.notifications_paused_outlined;
    case GtexRealtimeEventStreamKind.activity:
      return Icons.history_toggle_off_rounded;
  }
}

String _streamEyebrow(GtexRealtimeEventStreamKind kind) {
  switch (kind) {
    case GtexRealtimeEventStreamKind.notifications:
      return 'NOTIFICATIONS';
    case GtexRealtimeEventStreamKind.activity:
      return 'ACTIVITY';
  }
}

String _streamTitle(GtexRealtimeEventStreamKind kind) {
  switch (kind) {
    case GtexRealtimeEventStreamKind.notifications:
      return 'Notification stream';
    case GtexRealtimeEventStreamKind.activity:
      return 'Activity events';
  }
}

String _emptyTitle(GtexRealtimeEventStreamKind kind) {
  switch (kind) {
    case GtexRealtimeEventStreamKind.notifications:
      return 'No notifications';
    case GtexRealtimeEventStreamKind.activity:
      return 'No activity events';
  }
}

String _emptyMessage(GtexRealtimeEventStreamKind kind) {
  switch (kind) {
    case GtexRealtimeEventStreamKind.notifications:
      return 'Waiting for backend notification events.';
    case GtexRealtimeEventStreamKind.activity:
      return 'Waiting for backend activity events.';
  }
}

String _stateMessage(GtexSurfaceState state) {
  switch (state) {
    case GtexSurfaceState.loading:
      return 'Realtime state is loading.';
    case GtexSurfaceState.empty:
      return 'No confirmed backend records are available yet.';
    case GtexSurfaceState.blocked:
      return 'This stream is blocked until the session is eligible.';
    case GtexSurfaceState.pending:
      return 'This stream is waiting for the next backend confirmation.';
    case GtexSurfaceState.syncing:
      return 'Realtime state is syncing with the backend.';
    case GtexSurfaceState.reconnecting:
      return 'Realtime transport is reconnecting.';
    case GtexSurfaceState.degraded:
      return 'Confirmed records remain visible while the feed recovers.';
    case GtexSurfaceState.confirmed:
      return 'The backend has confirmed this stream.';
    case GtexSurfaceState.error:
      return 'Realtime state could not be loaded.';
  }
}

String _timeLabel(DateTime value) {
  final Duration delta = DateTime.now().difference(value);
  if (delta.inSeconds < 60) {
    return 'now';
  }
  if (delta.inMinutes < 60) {
    return '${delta.inMinutes}m ago';
  }
  if (delta.inHours < 24) {
    return '${delta.inHours}h ago';
  }
  return '${delta.inDays}d ago';
}

String? _clean(String? value) {
  final String? trimmed = value?.trim();
  if (trimmed == null || trimmed.isEmpty) {
    return null;
  }
  return trimmed;
}
