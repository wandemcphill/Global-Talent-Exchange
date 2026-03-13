import 'package:flutter/material.dart';
import '../../../../core/app_feedback.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/trophy_cabinet_dto.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/trophy_cabinet_repository.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/trophy_item_dto.dart';
import 'package:gte_frontend/features/club_identity/trophies/presentation/honors_timeline_screen.dart';
import 'package:gte_frontend/features/club_identity/trophies/presentation/trophy_leaderboard_screen.dart';
import 'package:gte_frontend/features/club_identity/trophies/widgets/featured_trophy_shelf.dart';
import 'package:gte_frontend/features/club_identity/trophies/widgets/major_honor_badge.dart';
import 'package:gte_frontend/features/club_identity/trophies/widgets/trophy_category_section.dart';
import 'package:gte_frontend/features/club_identity/trophies/widgets/trophy_count_card.dart';
import 'package:gte_frontend/features/club_identity/trophies/widgets/trophy_tile.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class TrophyCabinetScreen extends StatefulWidget {
  const TrophyCabinetScreen({
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
  State<TrophyCabinetScreen> createState() => _TrophyCabinetScreenState();
}

class _TrophyCabinetScreenState extends State<TrophyCabinetScreen> {
  late final TrophyCabinetRepository _repository;
  late TrophyScopeFilter _filter;

  TrophyCabinetDto? _cabinet;
  String? _error;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _repository = widget.repository ?? StubTrophyCabinetRepository();
    _filter = widget.initialFilter;
    _loadCabinet();
  }

  Future<void> _loadCabinet() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final TrophyCabinetDto cabinet = await _repository.fetchTrophyCabinet(
        clubId: widget.clubId,
        teamScope: _filter.queryValue,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _cabinet = cabinet;
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
          title: const Text('Trophy Cabinet'),
          actions: <Widget>[
            IconButton(
              onPressed: _loadCabinet,
              icon: const Icon(Icons.refresh),
              tooltip: 'Refresh cabinet',
            ),
          ],
        ),
        body: _buildBody(context),
      ),
    );
  }

  Widget _buildBody(BuildContext context) {
    if (_loading && _cabinet == null) {
      return const _CabinetSkeleton();
    }
    if (_error != null && _cabinet == null) {
      return Padding(
        padding: const EdgeInsets.all(20),
        child: GteStatePanel(
          title: 'Cabinet unavailable',
          message: _error!,
          actionLabel: 'Retry',
          onAction: _loadCabinet,
          icon: Icons.emoji_events_outlined,
        ),
      );
    }

    final TrophyCabinetDto cabinet = _cabinet ??
        TrophyCabinetDto(
          clubId: widget.clubId,
          clubName: widget.clubName ?? 'Expansion XI',
          totalHonorsCount: 0,
          majorHonorsCount: 0,
          eliteHonorsCount: 0,
          seniorHonorsCount: 0,
          academyHonorsCount: 0,
          trophiesByCategory: const <TrophyCategoryDto>[],
          trophiesBySeason: const <TrophySeasonSummaryDto>[],
          recentHonors: const <TrophyItemDto>[],
          historicHonorsTimeline: const <TrophyItemDto>[],
          summaryOutputs: const <String>[],
        );
    final List<TrophyCategoryDto> seniorCategories = cabinet.trophiesByCategory
        .where(
          (TrophyCategoryDto category) =>
              category.teamScope == TrophyTeamScope.senior,
        )
        .toList(growable: false);
    final List<TrophyCategoryDto> academyCategories = cabinet.trophiesByCategory
        .where(
          (TrophyCategoryDto category) =>
              category.teamScope == TrophyTeamScope.academy,
        )
        .toList(growable: false);
    final bool isAcademyFilter = _filter == TrophyScopeFilter.academy;
    final bool isAllFilter = _filter == TrophyScopeFilter.all;

    return RefreshIndicator(
      onRefresh: _loadCabinet,
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
            if (_error != null) ...<Widget>[
              _InlineNotice(message: _error!),
              const SizedBox(height: 18),
            ],
            _HeroPanel(
              cabinet: cabinet,
              onOpenTimeline: _openTimeline,
              onOpenLeaderboard: _openLeaderboard,
            ),
            const SizedBox(height: 20),
            _FilterBar(
              selected: _filter,
              onSelected: (TrophyScopeFilter next) {
                if (next == _filter) {
                  return;
                }
                setState(() {
                  _filter = next;
                });
                _loadCabinet();
              },
            ),
            const SizedBox(height: 20),
            if (cabinet.isEmpty)
              const GteStatePanel(
                title: 'Cabinet waiting for its first trophy',
                message:
                    'New clubs start with an empty museum. The first title will turn this room into a permanent archive.',
                icon: Icons.auto_awesome_outlined,
              )
            else ...<Widget>[
              FeaturedTrophyShelf(trophies: cabinet.featuredHonors()),
              const SizedBox(height: 20),
              if (isAllFilter) ...<Widget>[
                TrophyCategorySection(
                  title: 'Senior cabinet',
                  subtitle:
                      'First-team honors anchor the main gallery of the museum.',
                  categories: seniorCategories,
                  badgeLabel: 'Senior',
                  badgeStyle: MajorHonorBadgeStyle.major,
                  emptyMessage: 'No senior honors yet.',
                ),
                const SizedBox(height: 16),
                TrophyCategorySection(
                  title: 'Academy wing',
                  subtitle:
                      'Youth honors live in a dedicated wing, kept distinct from senior shelves.',
                  categories: academyCategories,
                  badgeLabel: 'Academy',
                  badgeStyle: MajorHonorBadgeStyle.academy,
                  emphasized: true,
                  emptyMessage: 'No academy honors yet.',
                ),
              ] else
                TrophyCategorySection(
                  title: isAcademyFilter ? 'Academy wing' : 'Senior cabinet',
                  subtitle: isAcademyFilter
                      ? 'Youth honors live in a dedicated wing of the museum.'
                      : 'First-team honors anchor the main gallery.',
                  categories: cabinet.trophiesByCategory,
                  badgeLabel: isAcademyFilter ? 'Academy' : 'Senior',
                  badgeStyle: isAcademyFilter
                      ? MajorHonorBadgeStyle.academy
                      : MajorHonorBadgeStyle.major,
                  emphasized: isAcademyFilter,
                  emptyMessage: isAcademyFilter
                      ? 'No academy honors yet.'
                      : 'No senior honors yet.',
                ),
              const SizedBox(height: 20),
              _SeasonSummaryPanel(seasons: cabinet.trophiesBySeason),
              const SizedBox(height: 20),
              _RecentHonorsPanel(honors: cabinet.recentHonors),
            ],
          ],
        ),
      ),
    );
  }

  void _openTimeline() {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => HonorsTimelineScreen(
          clubId: widget.clubId,
          clubName: _cabinet?.clubName ?? widget.clubName,
          repository: _repository,
          initialFilter: _filter,
        ),
      ),
    );
  }

  void _openLeaderboard() {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => TrophyLeaderboardScreen(
          repository: _repository,
          initialFilter: _filter,
        ),
      ),
    );
  }
}

class _HeroPanel extends StatelessWidget {
  const _HeroPanel({
    required this.cabinet,
    required this.onOpenTimeline,
    required this.onOpenLeaderboard,
  });

  final TrophyCabinetDto cabinet;
  final VoidCallback onOpenTimeline;
  final VoidCallback onOpenLeaderboard;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      emphasized: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(cabinet.clubName,
                        style: Theme.of(context).textTheme.displaySmall),
                    const SizedBox(height: 8),
                    Text(
                      'A museum of silverware, milestones, and season-defining honors.',
                      style: Theme.of(context).textTheme.bodyLarge,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                alignment: WrapAlignment.end,
                children: <Widget>[
                  FilledButton.tonalIcon(
                    onPressed: onOpenTimeline,
                    icon: const Icon(Icons.timeline),
                    label: const Text('Timeline'),
                  ),
                  FilledButton.tonalIcon(
                    onPressed: onOpenLeaderboard,
                    icon: const Icon(Icons.leaderboard),
                    label: const Text('Leaderboard'),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 18),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              TrophyCountCard(
                label: 'Major honors',
                count: cabinet.majorHonorsCount,
                caption: 'League titles, continental crowns, and elite wins.',
                emphasized: true,
              ),
              TrophyCountCard(
                label: 'Total honors',
                count: cabinet.totalHonorsCount,
                caption: 'Every title, special award, and archive marker.',
              ),
              TrophyCountCard(
                label: 'Senior honors',
                count: cabinet.seniorHonorsCount,
                caption: 'First-team silverware kept in the main gallery.',
              ),
              TrophyCountCard(
                label: 'Academy honors',
                count: cabinet.academyHonorsCount,
                caption: 'Youth success kept distinct from the senior shelf.',
              ),
              TrophyCountCard(
                label: 'Elite honors',
                count: cabinet.eliteHonorsCount,
                caption: 'World-level honors marked as cabinet centerpieces.',
                emphasized: true,
              ),
            ],
          ),
          if (cabinet.summaryOutputs.isNotEmpty) ...<Widget>[
            const SizedBox(height: 18),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: cabinet.summaryOutputs.map((String summary) {
                return Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: GteShellTheme.panelStrong.withValues(alpha: 0.92),
                    borderRadius: BorderRadius.circular(999),
                    border: Border.all(color: GteShellTheme.stroke),
                  ),
                  child: Text(summary,
                      style: Theme.of(context).textTheme.labelLarge),
                );
              }).toList(growable: false),
            ),
          ],
        ],
      ),
    );
  }
}

class _FilterBar extends StatelessWidget {
  const _FilterBar({
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
              child: Text('Cabinet view',
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

class _SeasonSummaryPanel extends StatelessWidget {
  const _SeasonSummaryPanel({required this.seasons});

  final List<TrophySeasonSummaryDto> seasons;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Season archive markers',
              style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 8),
          Text(
            'A fast season-by-season scan of how the museum was built.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),
          if (seasons.isEmpty)
            Text(
              'No season snapshots archived yet.',
              style: Theme.of(context).textTheme.bodyMedium,
            )
          else
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: seasons.map((TrophySeasonSummaryDto season) {
                return SizedBox(
                  width: 208,
                  child: Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(20),
                      color: GteShellTheme.panelStrong.withValues(alpha: 0.76),
                      border: Border.all(color: GteShellTheme.stroke),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(season.seasonLabel,
                            style: Theme.of(context).textTheme.titleLarge),
                        const SizedBox(height: 8),
                        Text(
                          '${season.totalHonorsCount} honors | ${season.majorHonorsCount} major',
                          style: Theme.of(context).textTheme.bodyLarge,
                        ),
                        const SizedBox(height: 6),
                        Text(
                          'Senior ${season.seniorHonorsCount} | Academy ${season.academyHonorsCount}',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      ],
                    ),
                  ),
                );
              }).toList(growable: false),
            ),
        ],
      ),
    );
  }
}

class _RecentHonorsPanel extends StatelessWidget {
  const _RecentHonorsPanel({required this.honors});

  final List<TrophyItemDto> honors;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Recent honors',
              style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 8),
          Text(
            'The freshest additions to the museum floor.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),
          if (honors.isEmpty)
            Text(
              'No recent honors yet. The next trophy will appear here first.',
              style: Theme.of(context).textTheme.bodyMedium,
            )
          else
            LayoutBuilder(
              builder: (BuildContext context, BoxConstraints constraints) {
                final bool narrow = constraints.maxWidth < 760;
                return Wrap(
                  spacing: 14,
                  runSpacing: 14,
                  children: honors.map((TrophyItemDto honor) {
                    return SizedBox(
                      width: narrow ? constraints.maxWidth : 280,
                      child: TrophyTile(trophy: honor),
                    );
                  }).toList(growable: false),
                );
              },
            ),
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
      child: Row(
        children: <Widget>[
          const Icon(Icons.info_outline, color: GteShellTheme.accentWarm),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              message,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: GteShellTheme.textPrimary,
                  ),
            ),
          ),
        ],
      ),
    );
  }
}

class _CabinetSkeleton extends StatelessWidget {
  const _CabinetSkeleton();

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
      children: const <Widget>[
        _SkeletonPanel(height: 250),
        SizedBox(height: 20),
        _SkeletonPanel(height: 72),
        SizedBox(height: 20),
        _SkeletonPanel(height: 300),
        SizedBox(height: 20),
        _SkeletonPanel(height: 260),
      ],
    );
  }
}

class _SkeletonPanel extends StatelessWidget {
  const _SkeletonPanel({required this.height});

  final double height;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(child: SizedBox(height: height));
  }
}
