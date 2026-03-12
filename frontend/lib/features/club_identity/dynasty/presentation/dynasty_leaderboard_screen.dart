import 'package:flutter/material.dart';

import '../../../../data/gte_api_repository.dart';
import '../../../../widgets/gte_shell_theme.dart';
import '../../../../widgets/gte_state_panel.dart';
import '../../../../widgets/gte_surface_panel.dart';
import '../data/dynasty_api_repository.dart';
import '../data/dynasty_leaderboard_entry_dto.dart';
import '../data/dynasty_repository.dart';
import '../data/dynasty_types.dart';
import '../widgets/dynasty_leaderboard_tile.dart';
import '../widgets/dynasty_loading_panel.dart';
import 'dynasty_controller.dart';

class DynastyLeaderboardScreen extends StatefulWidget {
  const DynastyLeaderboardScreen({
    super.key,
    this.controller,
    this.repository,
    this.baseUrl = 'http://127.0.0.1:8000',
    this.backendMode = GteBackendMode.liveThenFixture,
    this.onOpenClub,
  });

  final DynastyController? controller;
  final DynastyRepository? repository;
  final String baseUrl;
  final GteBackendMode backendMode;
  final ValueChanged<String>? onOpenClub;

  @override
  State<DynastyLeaderboardScreen> createState() =>
      _DynastyLeaderboardScreenState();
}

class _DynastyLeaderboardScreenState extends State<DynastyLeaderboardScreen> {
  late final DynastyController _controller;
  late final bool _ownsController;

  @override
  void initState() {
    super.initState();
    _ownsController = widget.controller == null;
    _controller = widget.controller ??
        DynastyController(
          repository: widget.repository ??
              DynastyApiRepository.standard(
                baseUrl: widget.baseUrl,
                mode: widget.backendMode,
              ),
        );
    _controller.loadLeaderboard();
  }

  @override
  void dispose() {
    if (_ownsController) {
      _controller.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: const Text('Dynasty leaderboard'),
        ),
        body: AnimatedBuilder(
          animation: _controller,
          builder: (BuildContext context, Widget? child) {
            if (_controller.isLoadingLeaderboard &&
                _controller.leaderboard.isEmpty) {
              return ListView(
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
                children: const <Widget>[
                  DynastyLoadingPanel(lines: 3, height: 140),
                  SizedBox(height: 20),
                  DynastyLoadingPanel(lines: 3, height: 140),
                  SizedBox(height: 20),
                  DynastyLoadingPanel(lines: 3, height: 140),
                ],
              );
            }

            if (_controller.leaderboardError != null &&
                _controller.leaderboard.isEmpty) {
              return Padding(
                padding: const EdgeInsets.all(20),
                child: GteStatePanel(
                  title: 'Leaderboard unavailable',
                  message: _controller.leaderboardError!,
                  actionLabel: 'Retry',
                  onAction: () {
                    _controller.loadLeaderboard();
                  },
                  icon: Icons.leaderboard_outlined,
                ),
              );
            }

            final List<DynastyLeaderboardEntryDto> filtered =
                _controller.filteredLeaderboard;
            return RefreshIndicator(
              onRefresh: () => _controller.loadLeaderboard(),
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
                children: <Widget>[
                  GteSurfacePanel(
                    emphasized: true,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          'Global dynasty table',
                          style: Theme.of(context).textTheme.headlineSmall,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Filter the current feed between live powers, all-time names, and clubs still climbing toward the threshold.',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                        const SizedBox(height: 18),
                        SegmentedButton<DynastyLeaderboardFilter>(
                          showSelectedIcon: false,
                          segments: DynastyLeaderboardFilter.values
                              .map(
                                (DynastyLeaderboardFilter filter) =>
                                    ButtonSegment<DynastyLeaderboardFilter>(
                                  value: filter,
                                  label: Text(filter.label),
                                ),
                              )
                              .toList(growable: false),
                          selected: <DynastyLeaderboardFilter>{
                            _controller.leaderboardFilter
                          },
                          onSelectionChanged:
                              (Set<DynastyLeaderboardFilter> selection) {
                            final DynastyLeaderboardFilter? filter =
                                selection.isEmpty ? null : selection.first;
                            if (filter != null) {
                              _controller.setLeaderboardFilter(filter);
                            }
                          },
                        ),
                      ],
                    ),
                  ),
                  if (_controller.leaderboardError != null) ...<Widget>[
                    const SizedBox(height: 20),
                    GteSurfacePanel(
                      child: Text(
                        _controller.leaderboardError!,
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ),
                  ],
                  const SizedBox(height: 20),
                  if (filtered.isEmpty)
                    GteStatePanel(
                      title: _controller.leaderboardFilter.emptyTitle,
                      message: _controller.leaderboardFilter.emptyMessage,
                      icon: Icons.flag_outlined,
                    )
                  else
                    ...filtered.asMap().entries.map(
                          (MapEntry<int, DynastyLeaderboardEntryDto> entry) =>
                              Padding(
                            padding: const EdgeInsets.only(bottom: 14),
                            child: DynastyLeaderboardTile(
                              rank: entry.key + 1,
                              entry: entry.value,
                              onTap: widget.onOpenClub == null
                                  ? null
                                  : () {
                                      widget.onOpenClub!(entry.value.clubId);
                                    },
                            ),
                          ),
                        ),
                ],
              ),
            );
          },
        ),
      ),
    );
  }
}
