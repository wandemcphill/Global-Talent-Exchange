import 'package:flutter/material.dart';
import '../../../../core/app_feedback.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/trophy_cabinet_repository.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/trophy_item_dto.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/trophy_leaderboard_entry_dto.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class TrophyLeaderboardScreen extends StatefulWidget {
  const TrophyLeaderboardScreen({
    super.key,
    this.repository,
    this.initialFilter = TrophyScopeFilter.all,
  });

  final TrophyCabinetRepository? repository;
  final TrophyScopeFilter initialFilter;

  @override
  State<TrophyLeaderboardScreen> createState() =>
      _TrophyLeaderboardScreenState();
}

class _TrophyLeaderboardScreenState extends State<TrophyLeaderboardScreen> {
  late final TrophyCabinetRepository _repository;
  late TrophyScopeFilter _filter;

  TrophyLeaderboardDto? _leaderboard;
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
      final TrophyLeaderboardDto leaderboard =
          await _repository.fetchTrophyLeaderboard(
        teamScope: _filter.queryValue,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _leaderboard = leaderboard;
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
          title: const Text('Trophy Leaderboard'),
          actions: <Widget>[
            IconButton(
              onPressed: _load,
              icon: const Icon(Icons.refresh),
              tooltip: 'Refresh leaderboard',
            ),
          ],
        ),
        body: _buildBody(context),
      ),
    );
  }

  Widget _buildBody(BuildContext context) {
    if (_loading && _leaderboard == null) {
      return const _LeaderboardSkeleton();
    }
    if (_error != null && _leaderboard == null) {
      return Padding(
        padding: const EdgeInsets.all(20),
        child: GteStatePanel(
          title: 'Leaderboard unavailable',
          message: _error!,
          actionLabel: 'Retry',
          onAction: _load,
          icon: Icons.leaderboard_outlined,
        ),
      );
    }

    final TrophyLeaderboardDto leaderboard = _leaderboard ??
        const TrophyLeaderboardDto(entries: <TrophyLeaderboardEntryDto>[]);

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
            _LeaderboardHero(totalClubs: leaderboard.entries.length),
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
                _load();
              },
            ),
            const SizedBox(height: 20),
            if (_error != null) ...<Widget>[
              _InlineNotice(message: _error!),
              const SizedBox(height: 20),
            ],
            if (leaderboard.isEmpty)
              const GteStatePanel(
                title: 'No leaderboard entries yet',
                message:
                    'As clubs start collecting honors, the museum rankings will populate here.',
                icon: Icons.shield_outlined,
              )
            else ...<Widget>[
              _LeaderboardSection(
                title: 'Most trophies',
                subtitle: 'Pure cabinet volume across all archived honors.',
                entries: leaderboard.topByTotal(),
                selector: (TrophyLeaderboardEntryDto item) =>
                    item.totalHonorsCount,
              ),
              const SizedBox(height: 20),
              _LeaderboardSection(
                title: 'Most major honors',
                subtitle:
                    'League titles, continental crowns, and elite trophies.',
                entries: leaderboard.topByMajor(),
                selector: (TrophyLeaderboardEntryDto item) =>
                    item.majorHonorsCount,
              ),
              const SizedBox(height: 20),
              _LeaderboardSection(
                title: 'Most continental titles',
                subtitle: 'Senior and academy continental wins combined.',
                entries: leaderboard.topByContinental(),
                selector: (TrophyLeaderboardEntryDto item) =>
                    item.continentalTitlesCount,
              ),
              const SizedBox(height: 20),
              _LeaderboardSection(
                title: 'Most world titles',
                subtitle: 'World Super Cup wins carry the rarest weight.',
                entries: leaderboard.topByWorld(),
                selector: (TrophyLeaderboardEntryDto item) =>
                    item.worldTitlesCount,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _LeaderboardHero extends StatelessWidget {
  const _LeaderboardHero({
    required this.totalClubs,
  });

  final int totalClubs;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      emphasized: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Museum rankings',
              style: Theme.of(context).textTheme.displaySmall),
          const SizedBox(height: 8),
          Text(
            'A premium overview of who owns the most decorated cabinet in the exchange.',
            style: Theme.of(context).textTheme.bodyLarge,
          ),
          const SizedBox(height: 16),
          Text(
            '$totalClubs clubs ranked',
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  color: GteShellTheme.accentWarm,
                ),
          ),
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
              child: Text('Leaderboard scope',
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

class _LeaderboardSection extends StatelessWidget {
  const _LeaderboardSection({
    required this.title,
    required this.subtitle,
    required this.entries,
    required this.selector,
  });

  final String title;
  final String subtitle;
  final List<TrophyLeaderboardEntryDto> entries;
  final int Function(TrophyLeaderboardEntryDto entry) selector;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(title, style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 8),
          Text(subtitle, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 16),
          ...entries
              .asMap()
              .entries
              .map((MapEntry<int, TrophyLeaderboardEntryDto> entry) {
            return Padding(
              padding: EdgeInsets.only(
                  bottom: entry.key == entries.length - 1 ? 0 : 12),
              child: _LeaderboardRow(
                rank: entry.key + 1,
                entry: entry.value,
                value: selector(entry.value),
              ),
            );
          }),
        ],
      ),
    );
  }
}

class _LeaderboardRow extends StatelessWidget {
  const _LeaderboardRow({
    required this.rank,
    required this.entry,
    required this.value,
  });

  final int rank;
  final TrophyLeaderboardEntryDto entry;
  final int value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        color: GteShellTheme.panelStrong.withValues(alpha: 0.78),
        border: Border.all(color: GteShellTheme.stroke),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Container(
            width: 42,
            height: 42,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: rank == 1
                  ? GteShellTheme.accentWarm.withValues(alpha: 0.18)
                  : GteShellTheme.panel.withValues(alpha: 0.9),
              border: Border.all(
                color:
                    rank == 1 ? GteShellTheme.accentWarm : GteShellTheme.stroke,
              ),
            ),
            child: Text(
              '$rank',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    color: rank == 1 ? GteShellTheme.accentWarm : null,
                  ),
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(
                  children: <Widget>[
                    Expanded(
                      child: Text(
                        entry.clubName,
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                    ),
                    Text(
                      '$value',
                      style:
                          Theme.of(context).textTheme.headlineSmall?.copyWith(
                                color: GteShellTheme.accent,
                              ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  entry.summaryOutputs.isEmpty
                      ? 'No archived summaries yet.'
                      : entry.summaryOutputs.first,
                  style: Theme.of(context).textTheme.bodyLarge,
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: <Widget>[
                    _TinyPill(label: 'Major ${entry.majorHonorsCount}'),
                    _TinyPill(label: 'Total ${entry.totalHonorsCount}'),
                    if (entry.worldTitlesCount > 0)
                      _TinyPill(label: 'World ${entry.worldTitlesCount}'),
                    if (entry.continentalTitlesCount > 0)
                      _TinyPill(
                          label: 'Continental ${entry.continentalTitlesCount}'),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _TinyPill extends StatelessWidget {
  const _TinyPill({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: GteShellTheme.panel,
        border: Border.all(color: GteShellTheme.stroke),
      ),
      child: Text(label, style: Theme.of(context).textTheme.bodyMedium),
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

class _LeaderboardSkeleton extends StatelessWidget {
  const _LeaderboardSkeleton();

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
      children: const <Widget>[
        _SkeletonBlock(height: 180),
        SizedBox(height: 20),
        _SkeletonBlock(height: 72),
        SizedBox(height: 20),
        _SkeletonBlock(height: 240),
        SizedBox(height: 20),
        _SkeletonBlock(height: 240),
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
