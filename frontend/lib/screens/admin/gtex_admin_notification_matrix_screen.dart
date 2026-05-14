import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../data/gte_api_repository.dart';
import '../../data/notification_settings_api.dart';
import '../../models/notification_settings_models.dart';
import '../../ui_gtex/ui_gtex.dart';

class GtexAdminNotificationMatrixScreen extends StatefulWidget {
  const GtexAdminNotificationMatrixScreen({
    super.key,
    required this.baseUrl,
    required this.accessToken,
    required this.backendMode,
    this.api,
  });

  final String baseUrl;
  final String accessToken;
  final GteBackendMode backendMode;
  final NotificationSettingsApi? api;

  @override
  State<GtexAdminNotificationMatrixScreen> createState() =>
      _GtexAdminNotificationMatrixScreenState();
}

class _GtexAdminNotificationMatrixScreenState
    extends State<GtexAdminNotificationMatrixScreen> {
  late final NotificationSettingsApi _api;
  late Future<List<NotificationEventMatrixItem>> _future;
  final TextEditingController _searchController = TextEditingController();
  final TextEditingController _targetUserController = TextEditingController(
    text: 'fixture-admin-target',
  );
  final TextEditingController _messageController = TextEditingController();
  String _query = '';
  String? _selectedEventKey;
  bool _sendingTest = false;
  String? _dispatchMessage;

  @override
  void initState() {
    super.initState();
    _api =
        widget.api ??
        NotificationSettingsApi.standard(
          baseUrl: widget.baseUrl,
          accessToken: widget.accessToken,
          mode: widget.backendMode,
        );
    _future = _api.adminListEventMatrix();
  }

  @override
  void dispose() {
    _searchController.dispose();
    _targetUserController.dispose();
    _messageController.dispose();
    super.dispose();
  }

  void _refresh() {
    setState(() {
      _future = _api.adminListEventMatrix();
      _dispatchMessage = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<NotificationEventMatrixItem>>(
      future: _future,
      builder: (
        BuildContext context,
        AsyncSnapshot<List<NotificationEventMatrixItem>> snapshot,
      ) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.hasError) {
          return GtexEmptyState(
            title: 'Notification matrix unavailable',
            message: snapshot.error.toString(),
            icon: Icons.notifications_off_outlined,
            actionLabel: 'Retry',
            onAction: _refresh,
            accent: GtexColors.gold,
          );
        }

        final List<NotificationEventMatrixItem> events =
            snapshot.data ?? const <NotificationEventMatrixItem>[];
        if (events.isEmpty) {
          return GtexEmptyState(
            title: 'No notification events',
            message:
                'The admin event matrix endpoint returned an empty set. Check the notification module registration before launch.',
            icon: Icons.notifications_none_outlined,
            actionLabel: 'Refresh',
            onAction: _refresh,
            accent: GtexColors.gold,
          );
        }

        final List<NotificationEventMatrixItem> filtered = _filterEvents(
          events,
        );
        final NotificationEventMatrixItem selected = _selectedEvent(
          filtered.isEmpty ? events : filtered,
        );
        final Map<String, int> topicCounts = _countsBy(
          events,
          (NotificationEventMatrixItem item) => item.topic,
        );
        final Map<String, int> audienceCounts = _countsBy(
          events,
          (NotificationEventMatrixItem item) => item.audience,
        );

        return GtexMasterDetailScaffold(
          title: 'Admin Notification Matrix',
          subtitle:
              'Event-to-template coverage, deep links, preferences, and admin test dispatch for GTEX notifications.',
          accent: GtexColors.gold,
          mobileLeftTitle: 'Events',
          leftPanelWidth: 350,
          rightPanelWidth: 340,
          actions: <Widget>[
            IconButton.filledTonal(
              tooltip: 'Back to admin command center',
              onPressed: () => context.go('/admin'),
              icon: const Icon(Icons.arrow_back_outlined),
            ),
            IconButton.filledTonal(
              tooltip: 'Refresh notification matrix',
              onPressed: _refresh,
              icon: const Icon(Icons.sync),
            ),
          ],
          leftPanel: _MatrixEventList(
            events: filtered,
            selectedEventKey: selected.eventKey,
            queryController: _searchController,
            onQueryChanged:
                (String value) => setState(() {
                  _query = value;
                }),
            onSelected:
                (String eventKey) => setState(() {
                  _selectedEventKey = eventKey;
                  _dispatchMessage = null;
                }),
          ),
          detail: _MatrixDetailPanel(
            event: selected,
            targetUserController: _targetUserController,
            messageController: _messageController,
            sendingTest: _sendingTest,
            dispatchMessage: _dispatchMessage,
            onSendTest: () => _sendTestEvent(selected),
          ),
          rightPanel: _MatrixSummaryPanel(
            events: events,
            topicCounts: topicCounts,
            audienceCounts: audienceCounts,
          ),
        );
      },
    );
  }

  List<NotificationEventMatrixItem> _filterEvents(
    List<NotificationEventMatrixItem> events,
  ) {
    final String query = _query.trim().toLowerCase();
    if (query.isEmpty) {
      return events;
    }
    return events
        .where(
          (NotificationEventMatrixItem item) =>
              item.eventKey.contains(query) ||
              item.topic.toLowerCase().contains(query) ||
              item.title.toLowerCase().contains(query) ||
              item.deepLinkRoute.toLowerCase().contains(query),
        )
        .toList(growable: false);
  }

  NotificationEventMatrixItem _selectedEvent(
    List<NotificationEventMatrixItem> events,
  ) {
    final String? selectedKey = _selectedEventKey;
    if (selectedKey != null) {
      for (final NotificationEventMatrixItem event in events) {
        if (event.eventKey == selectedKey) {
          return event;
        }
      }
    }
    return events.first;
  }

  Map<String, int> _countsBy(
    List<NotificationEventMatrixItem> events,
    String Function(NotificationEventMatrixItem item) keyFor,
  ) {
    final Map<String, int> counts = <String, int>{};
    for (final NotificationEventMatrixItem event in events) {
      final String key = keyFor(event).trim();
      counts[key] = (counts[key] ?? 0) + 1;
    }
    return counts;
  }

  Future<void> _sendTestEvent(NotificationEventMatrixItem event) async {
    final String targetUserId = _targetUserController.text.trim();
    if (targetUserId.isEmpty) {
      setState(() {
        _dispatchMessage = 'Enter a target user id before sending a test.';
      });
      return;
    }
    setState(() {
      _sendingTest = true;
      _dispatchMessage = null;
    });
    try {
      final NotificationTestEventResult result = await _api
          .adminPublishTestEvent(
            eventKey: event.eventKey,
            targetUserId: targetUserId,
            message: _messageController.text,
          );
      if (!mounted) {
        return;
      }
      setState(() {
        _dispatchMessage =
            'Sent ${result.matrixItem.title} test notification ${result.notificationId}.';
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _dispatchMessage = error.toString();
      });
    } finally {
      if (mounted) {
        setState(() {
          _sendingTest = false;
        });
      }
    }
  }
}

class _MatrixEventList extends StatelessWidget {
  const _MatrixEventList({
    required this.events,
    required this.selectedEventKey,
    required this.queryController,
    required this.onQueryChanged,
    required this.onSelected,
  });

  final List<NotificationEventMatrixItem> events;
  final String selectedEventKey;
  final TextEditingController queryController;
  final ValueChanged<String> onQueryChanged;
  final ValueChanged<String> onSelected;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: <Widget>[
        GtexSearchField(
          controller: queryController,
          hintText: 'Search notification events',
          onChanged: onQueryChanged,
        ),
        const SizedBox(height: GtexSpacing.md),
        Expanded(
          child:
              events.isEmpty
                  ? const GtexEmptyState(
                    title: 'No matches',
                    message: 'Try another event key, topic, route, or title.',
                    icon: Icons.search_off_outlined,
                    accent: GtexColors.gold,
                  )
                  : ListView.separated(
                    itemCount: events.length,
                    separatorBuilder:
                        (BuildContext context, int index) =>
                            const SizedBox(height: GtexSpacing.sm),
                    itemBuilder: (BuildContext context, int index) {
                      final NotificationEventMatrixItem event = events[index];
                      return GtexPanel(
                        title: event.title,
                        subtitle: event.defaultMessage,
                        accent: GtexColors.gold,
                        isSelected: event.eventKey == selectedEventKey,
                        onTap: () => onSelected(event.eventKey),
                        child: Wrap(
                          spacing: GtexSpacing.xs,
                          runSpacing: GtexSpacing.xs,
                          children: <Widget>[
                            GtexStatusChip(
                              label: event.topic,
                              tone: GtexStatusTone.premium,
                              compact: true,
                            ),
                            GtexStatusChip(
                              label: event.audience,
                              tone: GtexStatusTone.neutral,
                              compact: true,
                            ),
                          ],
                        ),
                      );
                    },
                  ),
        ),
      ],
    );
  }
}

class _MatrixDetailPanel extends StatelessWidget {
  const _MatrixDetailPanel({
    required this.event,
    required this.targetUserController,
    required this.messageController,
    required this.sendingTest,
    required this.dispatchMessage,
    required this.onSendTest,
  });

  final NotificationEventMatrixItem event;
  final TextEditingController targetUserController;
  final TextEditingController messageController;
  final bool sendingTest;
  final String? dispatchMessage;
  final VoidCallback onSendTest;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: EdgeInsets.zero,
      children: <Widget>[
        GtexPanel(
          title: event.title,
          subtitle: event.eventKey,
          accent: GtexColors.gold,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Wrap(
                spacing: GtexSpacing.sm,
                runSpacing: GtexSpacing.sm,
                children: <Widget>[
                  GtexMetricTile(
                    label: 'Topic',
                    value: event.topic,
                    icon: Icons.topic_outlined,
                    accent: GtexColors.gold,
                  ),
                  GtexMetricTile(
                    label: 'Audience',
                    value: event.audience,
                    icon: Icons.groups_outlined,
                    accent: GtexColors.cyan,
                  ),
                  GtexMetricTile(
                    label: 'Preference',
                    value: event.preferenceKey ?? 'admin enforced',
                    icon: Icons.tune_outlined,
                    accent: GtexColors.mint,
                  ),
                ],
              ),
              const SizedBox(height: GtexSpacing.lg),
              _DetailLine(label: 'Template', value: event.templateKey),
              _DetailLine(label: 'Deep link', value: event.deepLinkRoute),
              _DetailLine(label: 'Default', value: event.defaultMessage),
              if (event.metadata.isNotEmpty) ...<Widget>[
                const SizedBox(height: GtexSpacing.md),
                Wrap(
                  spacing: GtexSpacing.xs,
                  runSpacing: GtexSpacing.xs,
                  children: event.metadata.entries
                      .map(
                        (MapEntry<String, Object?> entry) => GtexStatusChip(
                          label: '${entry.key}: ${entry.value}',
                          tone: GtexStatusTone.neutral,
                          compact: true,
                        ),
                      )
                      .toList(growable: false),
                ),
              ],
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Test dispatch',
          subtitle:
              'Send one admin-triggered test notification through the live notification event matrix.',
          accent: GtexColors.cyan,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              TextField(
                controller: targetUserController,
                decoration: const InputDecoration(
                  labelText: 'Target user id',
                  prefixIcon: Icon(Icons.person_search_outlined),
                ),
              ),
              const SizedBox(height: GtexSpacing.sm),
              TextField(
                controller: messageController,
                minLines: 2,
                maxLines: 4,
                decoration: InputDecoration(
                  labelText: 'Message override',
                  hintText: event.defaultMessage,
                  prefixIcon: const Icon(Icons.edit_note_outlined),
                ),
              ),
              const SizedBox(height: GtexSpacing.md),
              GtexActionButton(
                label: sendingTest ? 'Sending test' : 'Send test event',
                icon: Icons.notifications_active_outlined,
                accent: GtexColors.cyan,
                onPressed: sendingTest ? null : onSendTest,
              ),
              if (dispatchMessage != null) ...<Widget>[
                const SizedBox(height: GtexSpacing.md),
                Text(
                  dispatchMessage!,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: GtexColors.textSecondary,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }
}

class _MatrixSummaryPanel extends StatelessWidget {
  const _MatrixSummaryPanel({
    required this.events,
    required this.topicCounts,
    required this.audienceCounts,
  });

  final List<NotificationEventMatrixItem> events;
  final Map<String, int> topicCounts;
  final Map<String, int> audienceCounts;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: EdgeInsets.zero,
      children: <Widget>[
        GtexMetricTile(
          label: 'Mapped events',
          value: events.length.toString(),
          helper: 'Backend event keys exposed to admin.',
          icon: Icons.notifications_active_outlined,
          accent: GtexColors.gold,
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Topics',
          subtitle: 'Coverage by notification channel.',
          accent: GtexColors.gold,
          child: _CountList(counts: topicCounts),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Audiences',
          subtitle: 'Who can receive matrix events.',
          accent: GtexColors.cyan,
          child: _CountList(counts: audienceCounts),
        ),
      ],
    );
  }
}

class _CountList extends StatelessWidget {
  const _CountList({required this.counts});

  final Map<String, int> counts;

  @override
  Widget build(BuildContext context) {
    final List<MapEntry<String, int>> entries =
        counts.entries.toList()
          ..sort((MapEntry<String, int> a, MapEntry<String, int> b) {
            final int byCount = b.value.compareTo(a.value);
            if (byCount != 0) {
              return byCount;
            }
            return a.key.compareTo(b.key);
          });
    return Column(
      children: entries
          .map(
            (MapEntry<String, int> entry) => Padding(
              padding: const EdgeInsets.only(bottom: GtexSpacing.xs),
              child: Row(
                children: <Widget>[
                  Expanded(
                    child: Text(
                      entry.key,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: GtexColors.text,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                  GtexStatusChip(
                    label: entry.value.toString(),
                    tone: GtexStatusTone.premium,
                    compact: true,
                  ),
                ],
              ),
            ),
          )
          .toList(growable: false),
    );
  }
}

class _DetailLine extends StatelessWidget {
  const _DetailLine({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            label.toUpperCase(),
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: GtexColors.textMuted,
              fontWeight: FontWeight.w900,
              letterSpacing: 0.6,
            ),
          ),
          const SizedBox(height: GtexSpacing.xxs),
          Text(
            value,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: GtexColors.text,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}
