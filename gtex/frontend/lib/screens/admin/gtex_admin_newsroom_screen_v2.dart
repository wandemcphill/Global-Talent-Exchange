import 'package:flutter/material.dart';

import '../../data/story_feed_api.dart';
import '../../features/engagement_redesign/engagement_models.dart';
import '../../features/engagement_redesign/engagement_widgets.dart';
import '../../models/story_feed_models.dart';
import '../../ui_gtex/ui_gtex.dart';

class GtexAdminNewsroomScreenV2 extends StatefulWidget {
  const GtexAdminNewsroomScreenV2({
    super.key,
    this.api,
    this.queue = const <GtexNewsroomQueueItem>[],
    this.allowFixtureData = false,
    this.embedded = false,
  });

  /// Live story-feed client. When null and [queue] is empty, the desk fails
  /// closed unless fixture data is explicitly allowed.
  final StoryFeedApi? api;
  final List<GtexNewsroomQueueItem> queue;
  final bool allowFixtureData;
  final bool embedded;

  @override
  State<GtexAdminNewsroomScreenV2> createState() =>
      _GtexAdminNewsroomScreenV2State();
}

class _GtexAdminNewsroomScreenV2State extends State<GtexAdminNewsroomScreenV2> {
  late Future<List<_NewsroomStory>> _future;
  _NewsroomStory? _selected;
  final TextEditingController _titleController = TextEditingController();
  final TextEditingController _bodyController = TextEditingController();
  bool _publishing = false;
  String? _publishError;
  String? _publishMessage;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  @override
  void dispose() {
    _titleController.dispose();
    _bodyController.dispose();
    super.dispose();
  }

  Future<List<_NewsroomStory>> _load() async {
    final StoryFeedApi? api = widget.api;
    if (api != null) {
      final List<StoryFeedItem> items = await api.listAdminFeed(limit: 100);
      return items.map(_NewsroomStory.fromFeedItem).toList(growable: false);
    }
    if (widget.queue.isNotEmpty) {
      return widget.queue
          .map(_NewsroomStory.fromQueueItem)
          .toList(growable: false);
    }
    if (widget.allowFixtureData) {
      return StoryFeedApi.fixture().listFeed(limit: 20).then(
        (List<StoryFeedItem> items) =>
            items.map(_NewsroomStory.fromFeedItem).toList(growable: false),
      );
    }
    throw StateError(
      'Live story-feed API is required for Admin Newsroom in production.',
    );
  }

  void _reload() {
    setState(() {
      _publishError = null;
      _publishMessage = null;
      _selected = null;
      _future = _load();
    });
  }

  Future<void> _publishAnnouncement() async {
    final StoryFeedApi? api = widget.api;
    final String title = _titleController.text.trim();
    final String body = _bodyController.text.trim();
    if (api == null) {
      setState(
        () =>
            _publishError =
                'Publishing requires an authenticated admin story-feed client.',
      );
      return;
    }
    if (title.isEmpty || body.isEmpty) {
      setState(
        () =>
            _publishError =
                'Announcement title and body are required before publish.',
      );
      return;
    }
    setState(() {
      _publishing = true;
      _publishError = null;
      _publishMessage = null;
    });
    try {
      final StoryFeedItem published = await api.publishStory(
        storyType: 'announcement',
        title: title,
        body: body,
        audience: 'all',
        featured: true,
      );
      if (!mounted) {
        return;
      }
      _titleController.clear();
      _bodyController.clear();
      setState(() {
        _publishMessage = 'Published “${published.title}”.';
        _selected = _NewsroomStory.fromFeedItem(published);
        _future = _load();
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() => _publishError = error.toString());
    } finally {
      if (mounted) {
        setState(() => _publishing = false);
      }
    }
  }

  Future<void> _scheduleSelected(_NewsroomStory item) async {
    final StoryFeedApi? api = widget.api;
    if (api == null) {
      setState(
        () =>
            _publishError =
                'Scheduling requires an authenticated admin story-feed client.',
      );
      return;
    }
    final DateTime now = DateTime.now();
    final DateTime initial = now.add(const Duration(hours: 1));
    final DateTime? date = await showDatePicker(
      context: context,
      firstDate: now,
      lastDate: now.add(const Duration(days: 365)),
      initialDate: initial,
    );
    if (date == null || !mounted) {
      return;
    }
    final TimeOfDay? time = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(initial),
    );
    if (time == null || !mounted) {
      return;
    }
    final DateTime scheduledFor = DateTime(
      date.year,
      date.month,
      date.day,
      time.hour,
      time.minute,
    );
    setState(() {
      _publishing = true;
      _publishError = null;
      _publishMessage = null;
    });
    try {
      final StoryFeedItem updated = await api.scheduleStory(
        storyId: item.id,
        scheduledFor: scheduledFor,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _publishMessage =
            'Scheduled “${updated.title}” for ${scheduledFor.toLocal()}.';
        _selected = _NewsroomStory.fromFeedItem(updated);
        _future = _load();
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() => _publishError = error.toString());
    } finally {
      if (mounted) {
        setState(() => _publishing = false);
      }
    }
  }

  Future<void> _rejectSelected(_NewsroomStory item) async {
    final StoryFeedApi? api = widget.api;
    if (api == null) {
      setState(
        () =>
            _publishError =
                'Rejecting requires an authenticated admin story-feed client.',
      );
      return;
    }
    final TextEditingController reasonController = TextEditingController();
    final bool? confirmed = await showDialog<bool>(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          backgroundColor: GtexColors.surfaceRaised,
          title: const Text(
            'Reject story',
            style: TextStyle(color: GtexColors.textPrimary),
          ),
          content: TextField(
            controller: reasonController,
            maxLines: 3,
            style: const TextStyle(color: GtexColors.textPrimary),
            decoration: const InputDecoration(
              hintText: 'Optional rejection reason',
              hintStyle: TextStyle(color: GtexColors.textSecondary),
            ),
          ),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Cancel'),
            ),
            TextButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Reject'),
            ),
          ],
        );
      },
    );
    final String reason = reasonController.text.trim();
    reasonController.dispose();
    if (confirmed != true || !mounted) {
      return;
    }
    setState(() {
      _publishing = true;
      _publishError = null;
      _publishMessage = null;
    });
    try {
      final StoryFeedItem updated = await api.rejectStory(
        storyId: item.id,
        reason: reason.isEmpty ? null : reason,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _publishMessage = 'Rejected “${updated.title}”.';
        _selected = _NewsroomStory.fromFeedItem(updated);
        _future = _load();
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() => _publishError = error.toString());
    } finally {
      if (mounted) {
        setState(() => _publishing = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final Widget body = FutureBuilder<List<_NewsroomStory>>(
      future: _future,
      builder: (
        BuildContext context,
        AsyncSnapshot<List<_NewsroomStory>> snapshot,
      ) {
        if (snapshot.hasError) {
          return Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 560),
              child: GtexPanel(
                title: 'Live newsroom unavailable',
                subtitle: snapshot.error.toString(),
                accent: GtexColors.gold,
                child: GtexActionButton(
                  label: 'Retry newsroom',
                  icon: Icons.refresh,
                  onPressed: _reload,
                  accent: GtexColors.gold,
                  secondary: true,
                ),
              ),
            ),
          );
        }
        if (!snapshot.hasData) {
          return const Center(
            child: CircularProgressIndicator(color: GtexColors.gold),
          );
        }
        final List<_NewsroomStory> queue = snapshot.data!;
        final _NewsroomStory? selected =
            _selected ?? (queue.isEmpty ? null : queue.first);
        if (selected == null) {
          return GtexMasterDetailScaffold(
            title: 'Admin Newsroom',
            subtitle:
                'No live stories yet. Compose a GTEX-wide announcement to publish through /api/admin/story-feed.',
            accent: GtexColors.gold,
            leftPanel: const GtexEmptyState(
              title: 'Story feed empty',
              message:
                  'Published transfer, club, regen and market stories will appear here for review.',
              icon: Icons.newspaper_outlined,
              accent: GtexColors.gold,
            ),
            detail: _AnnouncementComposer(
              titleController: _titleController,
              bodyController: _bodyController,
              publishing: _publishing,
              error: _publishError,
              message: _publishMessage,
              onPublish: widget.api == null ? null : _publishAnnouncement,
            ),
            rightPanel: const GtexPanel(
              title: 'Publish controls',
              subtitle:
                  'Approve & publish posts the announcement composer to the audited admin story-feed endpoint. Select a story to schedule or reject it.',
              accent: GtexColors.gold,
              child: Wrap(
                spacing: GtexSpacing.xs,
                runSpacing: GtexSpacing.xs,
                children: <Widget>[
                  GtexStatusChip(label: 'PUBLISH LIVE', color: GtexColors.pitch),
                  GtexStatusChip(
                    label: 'SCHEDULE LIVE',
                    color: GtexColors.cyan,
                  ),
                  GtexStatusChip(
                    label: 'REJECT LIVE',
                    color: GtexColors.red,
                  ),
                ],
              ),
            ),
          );
        }
        return GtexMasterDetailScaffold(
          title: 'Admin Newsroom',
          subtitle:
              'Review live story-feed items and publish GTEX-wide announcements.',
          accent: GtexColors.gold,
          mobileLeftTitle: 'News queue',
          leftPanel: _AdminNewsQueue(
            queue: queue,
            selected: selected,
            onSelected: (_NewsroomStory item) => setState(() => _selected = item),
          ),
          detail: Column(
            children: <Widget>[
              Expanded(child: _AdminNewsPreview(item: selected)),
              Expanded(
                child: _AnnouncementComposer(
                  titleController: _titleController,
                  bodyController: _bodyController,
                  publishing: _publishing,
                  error: _publishError,
                  message: _publishMessage,
                  onPublish: widget.api == null ? null : _publishAnnouncement,
                ),
              ),
            ],
          ),
          rightPanel: _AdminPublishControls(
            item: selected,
            publishing: _publishing,
            canModerate: widget.api != null,
            message: _publishMessage,
            error: _publishError,
            onPublishAnnouncement: widget.api == null ? null : _publishAnnouncement,
            onSchedule: widget.api == null
                ? null
                : () => _scheduleSelected(selected),
            onReject: widget.api == null
                ? null
                : () => _rejectSelected(selected),
            onRefresh: _reload,
          ),
        );
      },
    );
    if (widget.embedded) {
      return body;
    }
    return Scaffold(
      backgroundColor: GtexColors.stadiumBlack,
      body: SafeArea(child: body),
    );
  }
}

class _NewsroomStory {
  const _NewsroomStory({
    required this.id,
    required this.title,
    required this.body,
    required this.status,
    required this.category,
    required this.updatedAt,
    required this.audience,
    this.riskLabel,
  });

  final String id;
  final String title;
  final String body;
  final String status;
  final GtexNewsCategory category;
  final DateTime updatedAt;
  final String audience;
  final String? riskLabel;

  factory _NewsroomStory.fromFeedItem(StoryFeedItem item) {
    final String status = switch (item.moderationStatus.toLowerCase()) {
      'scheduled' => item.scheduledFor == null
          ? 'Scheduled'
          : 'Scheduled ${item.scheduledFor!.toLocal()}',
      'rejected' => 'Rejected',
      _ => item.featured ? 'Featured' : 'Published',
    };
    return _NewsroomStory(
      id: item.id,
      title: item.title,
      body: item.body,
      status: status,
      category: _categoryFromStoryType(item.storyType),
      updatedAt: item.createdAt,
      audience: item.audience,
      riskLabel: item.metadata['risk_label']?.toString(),
    );
  }

  factory _NewsroomStory.fromQueueItem(GtexNewsroomQueueItem item) {
    return _NewsroomStory(
      id: item.id,
      title: item.title,
      body: 'Queue item supplied without full story body.',
      status: item.status,
      category: item.category,
      updatedAt: item.updatedAt,
      audience: item.audience,
      riskLabel: item.riskLabel,
    );
  }
}

GtexNewsCategory _categoryFromStoryType(String storyType) {
  final String normalized = storyType.toLowerCase();
  if (normalized.contains('transfer')) return GtexNewsCategory.transfers;
  if (normalized.contains('club')) return GtexNewsCategory.clubs;
  if (normalized.contains('regen')) return GtexNewsCategory.regens;
  if (normalized.contains('award')) return GtexNewsCategory.awards;
  if (normalized.contains('tournament') || normalized.contains('competition')) {
    return GtexNewsCategory.tournaments;
  }
  if (normalized.contains('jackpot')) return GtexNewsCategory.jackpot;
  if (normalized.contains('market')) return GtexNewsCategory.market;
  if (normalized.contains('creator')) return GtexNewsCategory.creators;
  if (normalized.contains('dispute')) return GtexNewsCategory.disputes;
  if (normalized.contains('break')) return GtexNewsCategory.breaking;
  return GtexNewsCategory.market;
}

class _AdminNewsQueue extends StatelessWidget {
  const _AdminNewsQueue({
    required this.queue,
    required this.selected,
    required this.onSelected,
  });

  final List<_NewsroomStory> queue;
  final _NewsroomStory selected;
  final ValueChanged<_NewsroomStory> onSelected;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: <Widget>[
        const Wrap(
          spacing: GtexSpacing.xs,
          runSpacing: GtexSpacing.xs,
          children: <Widget>[
            GtexStatusChip(label: 'LIVE FEED', color: GtexColors.pitch),
            GtexStatusChip(label: 'FEATURED', color: GtexColors.gold),
            GtexStatusChip(label: 'PUBLISHED', color: GtexColors.cyan),
          ],
        ),
        const SizedBox(height: GtexSpacing.md),
        Expanded(
          child: ListView(
            children: <Widget>[
              for (final _NewsroomStory item in queue)
                GtexSectionListTile(
                  title: item.title,
                  subtitle: '${item.status} • ${item.audience}',
                  icon: Icons.newspaper_outlined,
                  accent: newsCategoryColor(item.category),
                  isSelected: item.id == selected.id,
                  onTap: () => onSelected(item),
                  trailing:
                      item.riskLabel != null
                          ? const Icon(
                            Icons.warning_amber_outlined,
                            color: GtexColors.red,
                          )
                          : null,
                ),
            ],
          ),
        ),
      ],
    );
  }
}

class _AdminNewsPreview extends StatelessWidget {
  const _AdminNewsPreview({required this.item});

  final _NewsroomStory item;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(GtexSpacing.lg),
      children: <Widget>[
        GtexPanel(
          title: item.title,
          subtitle: 'Status: ${item.status} • Audience: ${item.audience}',
          accent: newsCategoryColor(item.category),
          trailing: GtexStatusChip(
            label: item.category.name.toUpperCase(),
            color: newsCategoryColor(item.category),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                item.body,
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                  color: GtexColors.textSecondary,
                  height: 1.5,
                ),
              ),
              if (item.riskLabel != null) ...<Widget>[
                const SizedBox(height: GtexSpacing.md),
                GtexStatusChip(
                  label: item.riskLabel!,
                  color: GtexColors.red,
                  icon: Icons.warning_amber_outlined,
                ),
              ],
            ],
          ),
        ),
      ],
    );
  }
}

class _AnnouncementComposer extends StatelessWidget {
  const _AnnouncementComposer({
    required this.titleController,
    required this.bodyController,
    required this.publishing,
    required this.error,
    required this.message,
    required this.onPublish,
  });

  final TextEditingController titleController;
  final TextEditingController bodyController;
  final bool publishing;
  final String? error;
  final String? message;
  final VoidCallback? onPublish;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(GtexSpacing.lg),
      children: <Widget>[
        GtexPanel(
          title: 'Announcement composer',
          subtitle:
              'Manual GTEX-wide announcements publish through POST /api/admin/story-feed.',
          accent: GtexColors.gold,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              TextField(
                controller: titleController,
                decoration: const InputDecoration(
                  hintText: 'Announcement title',
                ),
              ),
              const SizedBox(height: GtexSpacing.sm),
              TextField(
                controller: bodyController,
                minLines: 5,
                maxLines: 8,
                decoration: const InputDecoration(
                  hintText: 'Write announcement body...',
                ),
              ),
              if (error != null) ...<Widget>[
                const SizedBox(height: GtexSpacing.sm),
                Text(
                  error!,
                  style: const TextStyle(color: GtexColors.red, height: 1.4),
                ),
              ],
              if (message != null) ...<Widget>[
                const SizedBox(height: GtexSpacing.sm),
                Text(
                  message!,
                  style: const TextStyle(color: GtexColors.pitch, height: 1.4),
                ),
              ],
              const SizedBox(height: GtexSpacing.md),
              GtexActionButton(
                label: publishing ? 'Publishing…' : 'Approve & publish',
                icon: Icons.publish_outlined,
                onPressed: publishing ? null : onPublish,
                accent: GtexColors.pitch,
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _AdminPublishControls extends StatelessWidget {
  const _AdminPublishControls({
    required this.item,
    required this.publishing,
    required this.canModerate,
    required this.onPublishAnnouncement,
    required this.onSchedule,
    required this.onReject,
    required this.onRefresh,
    this.message,
    this.error,
  });

  final _NewsroomStory item;
  final bool publishing;
  final bool canModerate;
  final VoidCallback? onPublishAnnouncement;
  final VoidCallback? onSchedule;
  final VoidCallback? onReject;
  final VoidCallback onRefresh;
  final String? message;
  final String? error;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(GtexSpacing.md),
      children: <Widget>[
        GtexPanel(
          title: 'Publish controls',
          subtitle:
              canModerate
                  ? 'Compose an announcement, or schedule / reject the selected story through the admin story-feed moderation endpoints.'
                  : 'Publishing stays locked until an authenticated admin story-feed client is supplied.',
          accent: newsCategoryColor(item.category),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              if (message != null) ...<Widget>[
                Text(
                  message!,
                  style: const TextStyle(color: GtexColors.pitch, height: 1.4),
                ),
                const SizedBox(height: GtexSpacing.sm),
              ],
              if (error != null) ...<Widget>[
                Text(
                  error!,
                  style: const TextStyle(color: GtexColors.red, height: 1.4),
                ),
                const SizedBox(height: GtexSpacing.sm),
              ],
              GtexActionButton(
                label: publishing ? 'Working…' : 'Approve & publish',
                icon: Icons.publish_outlined,
                onPressed: publishing ? null : onPublishAnnouncement,
                accent: GtexColors.pitch,
              ),
              const SizedBox(height: GtexSpacing.sm),
              GtexActionButton(
                label: 'Schedule',
                icon: Icons.schedule_outlined,
                onPressed: publishing ? null : onSchedule,
                accent: GtexColors.cyan,
                secondary: true,
              ),
              const SizedBox(height: GtexSpacing.sm),
              GtexActionButton(
                label: 'Reject story',
                icon: Icons.block_outlined,
                onPressed: publishing ? null : onReject,
                accent: GtexColors.red,
                secondary: true,
              ),
              const SizedBox(height: GtexSpacing.sm),
              GtexActionButton(
                label: 'Refresh feed',
                icon: Icons.refresh,
                onPressed: publishing ? null : onRefresh,
                accent: GtexColors.gold,
                secondary: true,
              ),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Risk checks',
          subtitle: item.riskLabel ?? 'No unresolved risk flags on this story.',
          accent: item.riskLabel == null ? GtexColors.pitch : GtexColors.red,
          child: const Wrap(
            spacing: GtexSpacing.xs,
            runSpacing: GtexSpacing.xs,
            children: <Widget>[
              GtexStatusChip(label: 'AUDIT LOG', color: GtexColors.cyan),
              GtexStatusChip(label: 'ENTITY LINKS', color: GtexColors.pitch),
              GtexStatusChip(label: 'NO SECRETS', color: GtexColors.gold),
            ],
          ),
        ),
      ],
    );
  }
}
