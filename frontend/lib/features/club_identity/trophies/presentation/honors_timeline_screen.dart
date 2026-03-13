import 'package:flutter/material.dart';
import '../../../../core/app_feedback.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/honors_timeline_dto.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/season_honors_dto.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/trophy_cabinet_repository.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/trophy_item_dto.dart';
import 'package:gte_frontend/features/club_identity/trophies/widgets/honors_timeline_card.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class HonorsTimelineScreen extends StatefulWidget {
  const HonorsTimelineScreen({
    super.key,
    required this.clubId,
    this.clubName,
    this.repository,
    this.initialFilter = TrophyScopeFilter.all,
  });

  final String clubId;
  final String? clubName;
  final TrophyCabinetRepository? repository;
  final TrophyScopeFilter initialFilter;

  @override
  State<HonorsTimelineScreen> createState() => _HonorsTimelineScreenState();
}

class _HonorsTimelineScreenState extends State<HonorsTimelineScreen> {
  late final TrophyCabinetRepository _repository;
  late TrophyScopeFilter _filter;

  HonorsTimelineDto? _timeline;
  SeasonHonorsArchiveDto? _archive;
  String? _error;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _repository = widget.repository ?? StubTrophyCabinetRepository();
    _filter = widget.initialFilter;
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final List<Object> results = await Future.wait<Object>(<Future<Object>>[
        _repository.fetchHonorsTimeline(
          clubId: widget.clubId,
          teamScope: _filter.queryValue,
        ),
        _repository.fetchSeasonHonors(
          clubId: widget.clubId,
          teamScope: _filter.queryValue,
        ),
      ]);
      if (!mounted) {
        return;
      }
      setState(() {
        _timeline = results[0] as HonorsTimelineDto;
        _archive = results[1] as SeasonHonorsArchiveDto;
        _loading = false;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = AppFeedback.messageFor(error);
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: const Text('Honors Timeline'),
          actions: <Widget>[
            IconButton(
              onPressed: _load,
              icon: const Icon(Icons.refresh),
              tooltip: 'Refresh timeline',
            ),
          ],
        ),
        body: _buildBody(context),
      ),
    );
  }

  Widget _buildBody(BuildContext context) {
    if (_loading && _archive == null) {
      return const _TimelineSkeleton();
    }
    if (_error != null && _archive == null) {
      return Padding(
        padding: const EdgeInsets.all(20),
        child: GteStatePanel(
          title: 'Timeline unavailable',
          message: _error!,
          actionLabel: 'Retry',
          onAction: _load,
          icon: Icons.timeline,
        ),
      );
    }

    final HonorsTimelineDto timeline = _timeline ??
        HonorsTimelineDto(
          clubId: widget.clubId,
          clubName: widget.clubName ?? 'Expansion XI',
          honors: const <TrophyItemDto>[],
        );
    final SeasonHonorsArchiveDto archive = _archive ??
        SeasonHonorsArchiveDto(
          clubId: widget.clubId,
          clubName: widget.clubName ?? 'Expansion XI',
          seasonRecords: const <SeasonHonorsRecordDto>[],
        );

    final Map<String, List<SeasonHonorsRecordDto>> grouped =
        <String, List<SeasonHonorsRecordDto>>{};
    for (final SeasonHonorsRecordDto record in archive.seasonRecords) {
      grouped
          .putIfAbsent(record.seasonLabel, () => <SeasonHonorsRecordDto>[])
          .add(record);
    }

    return RefreshIndicator(
      onRefresh: _load,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            if (_loading) ...<Widget>[
              const LinearProgressIndicator(),
              const SizedBox(height: 16),
            ],
            _TimelineHero(
              clubName: archive.clubName,
              totalHonors: timeline.honors.length,
              seasons: grouped.length,
            ),
            const SizedBox(height: 20),
            _TimelineFilterBar(
              selected: _filter,
              onSelected: (TrophyScopeFilter next) {
                if (next == _filter) {
                  return;
                }
                setState(() {
                  _filter = next;
                });
                _load();
              },
            ),
            const SizedBox(height: 20),
            if (_error != null) ...<Widget>[
              _InlineNotice(message: _error!),
              const SizedBox(height: 20),
            ],
            if (archive.isEmpty)
              const GteStatePanel(
                title: 'No archived honors yet',
                message:
                    'When the club wins its first title, season snapshots will start stacking here.',
                icon: Icons.inventory_2_outlined,
              )
            else
              ...grouped.entries
                  .map((MapEntry<String, List<SeasonHonorsRecordDto>> entry) {
                final bool initiallyExpanded = entry.key == grouped.keys.first;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 16),
                  child: HonorsTimelineCard(
                    seasonLabel: entry.key,
                    records: entry.value,
                    initiallyExpanded: initiallyExpanded,
                  ),
                );
              }),
          ],
        ),
      ),
    );
  }
}

class _TimelineHero extends StatelessWidget {
  const _TimelineHero({
    required this.clubName,
    required this.totalHonors,
    required this.seasons,
  });

  final String clubName;
  final int totalHonors;
  final int seasons;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      emphasized: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(clubName, style: Theme.of(context).textTheme.displaySmall),
          const SizedBox(height: 8),
          Text(
            'Season-by-season honors history, preserved as an archive even when the live club state changes.',
            style: Theme.of(context).textTheme.bodyLarge,
          ),
          const SizedBox(height: 18),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              _StatPill(label: 'Honors', value: '$totalHonors'),
              _StatPill(label: 'Seasons archived', value: '$seasons'),
            ],
          ),
        ],
      ),
    );
  }
}

class _TimelineFilterBar extends StatelessWidget {
  const _TimelineFilterBar({
    required this.selected,
    required this.onSelected,
  });

  final TrophyScopeFilter selected;
  final ValueChanged<TrophyScopeFilter> onSelected;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      padding: const EdgeInsets.all(14),
      child: Row(
        children: <Widget>[
          Expanded(
              child: Text('Archive view',
                  style: Theme.of(context).textTheme.titleLarge)),
          SegmentedButton<TrophyScopeFilter>(
            segments: TrophyScopeFilter.values.map((TrophyScopeFilter filter) {
              return ButtonSegment<TrophyScopeFilter>(
                value: filter,
                label: Text(filter.label),
              );
            }).toList(growable: false),
            selected: <TrophyScopeFilter>{selected},
            onSelectionChanged: (Set<TrophyScopeFilter> selection) {
              onSelected(selection.first);
            },
          ),
        ],
      ),
    );
  }
}

class _StatPill extends StatelessWidget {
  const _StatPill({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: GteShellTheme.panelStrong,
        border: Border.all(color: GteShellTheme.stroke),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(label, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 4),
          Text(value, style: Theme.of(context).textTheme.titleLarge),
        ],
      ),
    );
  }
}

class _InlineNotice extends StatelessWidget {
  const _InlineNotice({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: GteShellTheme.accentWarm.withValues(alpha: 0.12),
        border:
            Border.all(color: GteShellTheme.accentWarm.withValues(alpha: 0.4)),
      ),
      child: Text(
        message,
        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: GteShellTheme.textPrimary,
            ),
      ),
    );
  }
}

class _TimelineSkeleton extends StatelessWidget {
  const _TimelineSkeleton();

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
      children: const <Widget>[
        _SkeletonBlock(height: 180),
        SizedBox(height: 20),
        _SkeletonBlock(height: 72),
        SizedBox(height: 20),
        _SkeletonBlock(height: 140),
        SizedBox(height: 16),
        _SkeletonBlock(height: 140),
        SizedBox(height: 16),
        _SkeletonBlock(height: 140),
      ],
    );
  }
}

class _SkeletonBlock extends StatelessWidget {
  const _SkeletonBlock({required this.height});

  final double height;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(child: SizedBox(height: height));
  }
}
