import 'package:flutter/material.dart';

import '../../features/engagement_redesign/engagement_controller.dart';
import '../../features/engagement_redesign/engagement_models.dart';
import '../../features/engagement_redesign/engagement_widgets.dart';
import '../../ui_gtex/ui_gtex.dart';

class GtexAdminNewsroomScreenV2 extends StatefulWidget {
  const GtexAdminNewsroomScreenV2({super.key, this.controller});

  final GtexEngagementController? controller;

  @override
  State<GtexAdminNewsroomScreenV2> createState() => _GtexAdminNewsroomScreenV2State();
}

class _GtexAdminNewsroomScreenV2State extends State<GtexAdminNewsroomScreenV2> {
  late final GtexEngagementController _controller;
  late final List<GtexNewsroomQueueItem> _queue;
  late GtexNewsroomQueueItem _selected;

  @override
  void initState() {
    super.initState();
    _controller = widget.controller ?? GtexEngagementController();
    _queue = _controller.loadDemoNewsroomQueue();
    _selected = _queue.first;
  }

  @override
  Widget build(BuildContext context) {
    return GtexMasterDetailScaffold(
      title: 'Admin Newsroom',
      subtitle: 'Review AI stories, publish announcements, moderate risk, and control GTEX-wide football news.',
      accent: GtexColors.gold,
      mobileLeftTitle: 'News queue',
      leftPanel: _AdminNewsQueue(
        queue: _queue,
        selected: _selected,
        onSelected: (GtexNewsroomQueueItem item) => setState(() => _selected = item),
      ),
      detail: _AdminNewsPreview(item: _selected),
      rightPanel: _AdminPublishControls(item: _selected),
    );
  }
}

class _AdminNewsQueue extends StatelessWidget {
  const _AdminNewsQueue({required this.queue, required this.selected, required this.onSelected});

  final List<GtexNewsroomQueueItem> queue;
  final GtexNewsroomQueueItem selected;
  final ValueChanged<GtexNewsroomQueueItem> onSelected;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: <Widget>[
        const GtexSearchField(hintText: 'Search stories, announcements'),
        const SizedBox(height: GtexSpacing.md),
        Wrap(
          spacing: GtexSpacing.xs,
          runSpacing: GtexSpacing.xs,
          children: const <Widget>[
            GtexStatusChip(label: 'DRAFTS', color: GtexColors.textSecondary),
            GtexStatusChip(label: 'REVIEW', color: GtexColors.gold),
            GtexStatusChip(label: 'SCHEDULED', color: GtexColors.cyan),
          ],
        ),
        const SizedBox(height: GtexSpacing.md),
        Expanded(
          child: ListView(
            children: <Widget>[
              for (final GtexNewsroomQueueItem item in queue)
                GtexSectionListTile(
                  title: item.title,
                  subtitle: '${item.status} • ${item.audience}',
                  icon: Icons.newspaper_outlined,
                  accent: newsCategoryColor(item.category),
                  isSelected: item.id == selected.id,
                  onTap: () => onSelected(item),
                  trailing: item.riskLabel != null ? const Icon(Icons.warning_amber_outlined, color: GtexColors.red) : null,
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

  final GtexNewsroomQueueItem item;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(GtexSpacing.lg),
      children: <Widget>[
        GtexPanel(
          title: item.title,
          subtitle: 'Status: ${item.status} • Audience: ${item.audience}',
          accent: newsCategoryColor(item.category),
          trailing: GtexStatusChip(label: item.category.name.toUpperCase(), color: newsCategoryColor(item.category)),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'This is the admin preview surface. Codex should replace this placeholder with the generated AI story body, editorial notes, linked objects, and moderation history from the backend.',
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(color: GtexColors.textSecondary, height: 1.5),
              ),
              if (item.riskLabel != null) ...<Widget>[
                const SizedBox(height: GtexSpacing.md),
                GtexStatusChip(label: item.riskLabel!, color: GtexColors.red, icon: Icons.warning_amber_outlined),
              ],
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        const GtexPanel(
          title: 'Announcement composer',
          subtitle: 'Use this area for manual GTEX-wide announcements: tournaments, jackpot, KYC deadlines, maintenance, or market events.',
          child: TextField(
            minLines: 5,
            maxLines: 8,
            decoration: InputDecoration(hintText: 'Write announcement or editor note...'),
          ),
        ),
      ],
    );
  }
}

class _AdminPublishControls extends StatelessWidget {
  const _AdminPublishControls({required this.item});

  final GtexNewsroomQueueItem item;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(GtexSpacing.md),
      children: <Widget>[
        GtexPanel(
          title: 'Publish controls',
          subtitle: 'All actions should hit audited admin endpoints.',
          accent: newsCategoryColor(item.category),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              GtexActionButton(label: 'Approve & publish', icon: Icons.publish_outlined, onPressed: () {}, accent: GtexColors.pitch),
              const SizedBox(height: GtexSpacing.sm),
              GtexActionButton(label: 'Schedule', icon: Icons.schedule_outlined, onPressed: () {}, accent: GtexColors.cyan, secondary: true),
              const SizedBox(height: GtexSpacing.sm),
              GtexActionButton(label: 'Send as notification', icon: Icons.notifications_active_outlined, onPressed: () {}, accent: GtexColors.gold, secondary: true),
              const SizedBox(height: GtexSpacing.sm),
              GtexActionButton(label: 'Reject story', icon: Icons.block_outlined, onPressed: () {}, accent: GtexColors.red, secondary: true),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Risk checks',
          subtitle: item.riskLabel ?? 'No unresolved risk flags.',
          accent: item.riskLabel == null ? GtexColors.pitch : GtexColors.red,
          child: Wrap(
            spacing: GtexSpacing.xs,
            runSpacing: GtexSpacing.xs,
            children: const <Widget>[
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
