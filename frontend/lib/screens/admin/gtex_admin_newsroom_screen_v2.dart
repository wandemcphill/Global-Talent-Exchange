import 'package:flutter/material.dart';

import '../../features/engagement_redesign/engagement_models.dart';
import '../../features/engagement_redesign/engagement_widgets.dart';
import '../../ui_gtex/ui_gtex.dart';

class GtexAdminNewsroomScreenV2 extends StatefulWidget {
  const GtexAdminNewsroomScreenV2({super.key, this.queue = const []});

  final List<GtexNewsroomQueueItem> queue;

  @override
  State<GtexAdminNewsroomScreenV2> createState() =>
      _GtexAdminNewsroomScreenV2State();
}

class _GtexAdminNewsroomScreenV2State extends State<GtexAdminNewsroomScreenV2> {
  GtexNewsroomQueueItem? _selected;

  @override
  void initState() {
    super.initState();
    if (widget.queue.isNotEmpty) {
      _selected = widget.queue.first;
    }
  }

  @override
  Widget build(BuildContext context) {
    final GtexNewsroomQueueItem? selected = _selected;
    if (selected == null || widget.queue.isEmpty) {
      return Scaffold(
        backgroundColor: GtexColors.stadiumBlack,
        body: SafeArea(
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 560),
              child: GtexPanel(
                title: 'Live newsroom unavailable',
                subtitle:
                    'Admin Newsroom V2 requires the audited live newsroom queue API. Demo newsroom queues are not mounted in strict-live production.',
                accent: GtexColors.gold,
                child: Text(
                  'No live newsroom queue was supplied by backend authority.',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: GtexColors.textMuted,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ),
          ),
        ),
      );
    }
    return GtexMasterDetailScaffold(
      title: 'Admin Newsroom',
      subtitle:
          'Review AI stories, publish announcements, moderate risk, and control GTEX-wide football news.',
      accent: GtexColors.gold,
      mobileLeftTitle: 'News queue',
      leftPanel: _AdminNewsQueue(
        queue: widget.queue,
        selected: selected,
        onSelected:
            (GtexNewsroomQueueItem item) => setState(() => _selected = item),
      ),
      detail: _AdminNewsPreview(item: selected),
      rightPanel: _AdminPublishControls(item: selected),
    );
  }
}

class _AdminNewsQueue extends StatelessWidget {
  const _AdminNewsQueue({
    required this.queue,
    required this.selected,
    required this.onSelected,
  });

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
          trailing: GtexStatusChip(
            label: item.category.name.toUpperCase(),
            color: newsCategoryColor(item.category),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Generated story body, editorial notes, linked objects, and moderation history appear here when the newsroom queue item includes them.',
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
        const SizedBox(height: GtexSpacing.md),
        const GtexPanel(
          title: 'Announcement composer',
          subtitle:
              'Use this area for manual GTEX-wide announcements: tournaments, jackpot, KYC deadlines, maintenance, or market events.',
          child: TextField(
            minLines: 5,
            maxLines: 8,
            decoration: InputDecoration(
              hintText: 'Write announcement or editor note...',
            ),
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
          subtitle:
              'Publishing stays locked until audited admin newsroom endpoints are mounted.',
          accent: newsCategoryColor(item.category),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              GtexActionButton(
                label: 'Approve & publish',
                icon: Icons.publish_outlined,
                onPressed:
                    () => _showNewsroomHandoff(
                      context,
                      'Publishing requires the audited admin story-feed endpoint before this queue item can go live.',
                    ),
                accent: GtexColors.pitch,
              ),
              const SizedBox(height: GtexSpacing.sm),
              GtexActionButton(
                label: 'Schedule',
                icon: Icons.schedule_outlined,
                onPressed:
                    () => _showNewsroomHandoff(
                      context,
                      'Scheduling is handed off to the admin notification calendar once this story has a live id.',
                    ),
                accent: GtexColors.cyan,
                secondary: true,
              ),
              const SizedBox(height: GtexSpacing.sm),
              GtexActionButton(
                label: 'Send as notification',
                icon: Icons.notifications_active_outlined,
                onPressed:
                    () => _showNewsroomHandoff(
                      context,
                      'Open Admin Notifications to send platform announcements from mounted notification endpoints.',
                    ),
                accent: GtexColors.gold,
                secondary: true,
              ),
              const SizedBox(height: GtexSpacing.sm),
              GtexActionButton(
                label: 'Reject story',
                icon: Icons.block_outlined,
                onPressed:
                    () => _showNewsroomHandoff(
                      context,
                      'Story rejection needs the audited moderation endpoint; no silent client-only rejection is allowed.',
                    ),
                accent: GtexColors.red,
                secondary: true,
              ),
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

void _showNewsroomHandoff(BuildContext context, String message) {
  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
}
