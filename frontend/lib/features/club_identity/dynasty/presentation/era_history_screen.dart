import 'package:flutter/material.dart';

import '../../../../data/gte_api_repository.dart';
import '../../../../widgets/gte_shell_theme.dart';
import '../../../../widgets/gte_state_panel.dart';
import '../../../../widgets/gte_surface_panel.dart';
import '../data/dynasty_api_repository.dart';
import '../data/dynasty_profile_dto.dart';
import '../data/dynasty_repository.dart';
import '../widgets/dynasty_loading_panel.dart';
import '../widgets/era_history_card.dart';
import '../widgets/era_label_chip.dart';
import 'dynasty_controller.dart';

class EraHistoryScreen extends StatefulWidget {
  const EraHistoryScreen({
    super.key,
    required this.clubId,
    this.controller,
    this.repository,
    this.baseUrl = 'http://127.0.0.1:8000',
    this.backendMode = GteBackendMode.liveThenFixture,
  });

  final String clubId;
  final DynastyController? controller;
  final DynastyRepository? repository;
  final String baseUrl;
  final GteBackendMode backendMode;

  @override
  State<EraHistoryScreen> createState() => _EraHistoryScreenState();
}

class _EraHistoryScreenState extends State<EraHistoryScreen> {
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
    _controller.loadHistory(widget.clubId);
  }

  @override
  void didUpdateWidget(covariant EraHistoryScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.clubId != widget.clubId) {
      _controller.loadHistory(widget.clubId);
    }
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
          title: const Text('Era History'),
        ),
        body: AnimatedBuilder(
          animation: _controller,
          builder: (BuildContext context, Widget? child) {
            if (_controller.isLoadingHistory && _controller.history == null) {
              return ListView(
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
                children: const <Widget>[
                  DynastyLoadingPanel(lines: 3, height: 180),
                  SizedBox(height: 20),
                  DynastyLoadingPanel(lines: 4, height: 210),
                  SizedBox(height: 20),
                  DynastyLoadingPanel(lines: 4, height: 210),
                ],
              );
            }

            if (_controller.historyError != null &&
                _controller.eraDetails.isEmpty) {
              return Padding(
                padding: const EdgeInsets.all(20),
                child: GteStatePanel(
                  title: 'Era history unavailable',
                  message: _controller.historyError!,
                  actionLabel: 'Retry',
                  onAction: () {
                    _controller.loadHistory(widget.clubId);
                  },
                  icon: Icons.history_edu_outlined,
                ),
              );
            }

            if (_controller.eraDetails.isEmpty) {
              return Padding(
                padding: const EdgeInsets.all(20),
                child: GteStatePanel(
                  title: 'No era history yet',
                  message:
                      'This club has not crossed the threshold for a named era. The history screen fills in once the badge builds a real stretch of dominance.',
                  actionLabel: 'Retry',
                  onAction: () {
                    _controller.loadHistory(widget.clubId);
                  },
                  icon: Icons.timeline_outlined,
                ),
              );
            }

            return RefreshIndicator(
              onRefresh: () => _controller.loadHistory(widget.clubId),
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
                          'Dynasty timeline',
                          style: Theme.of(context).textTheme.headlineSmall,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'A chronicle of when the club became a power, when it reached myth, and whether that standard held.',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      ],
                    ),
                  ),
                  if (_controller.historyError != null) ...<Widget>[
                    const SizedBox(height: 20),
                    GteSurfacePanel(
                      child: Text(
                        _controller.historyError!,
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ),
                  ],
                  const SizedBox(height: 20),
                  ..._controller.eraDetails.map(
                    (detail) => Padding(
                      padding: const EdgeInsets.only(bottom: 16),
                      child: EraHistoryCard(detail: detail),
                    ),
                  ),
                  const SizedBox(height: 8),
                  _TimelineSection(controller: _controller),
                ],
              ),
            );
          },
        ),
      ),
    );
  }
}

class _TimelineSection extends StatelessWidget {
  const _TimelineSection({
    required this.controller,
  });

  final DynastyController controller;

  @override
  Widget build(BuildContext context) {
    final List<DynastySnapshotDto> timeline = controller.chronologicalTimeline;
    if (timeline.isEmpty) {
      return const SizedBox.shrink();
    }

    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Timeline checkpoints',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 16),
          ...timeline.map(
            (DynastySnapshotDto snapshot) => Padding(
              padding: const EdgeInsets.only(bottom: 14),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Container(
                    width: 14,
                    height: 14,
                    margin: const EdgeInsets.only(top: 4),
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: snapshot.activeDynasty
                          ? GteShellTheme.accentWarm
                          : GteShellTheme.stroke,
                    ),
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
                                snapshot.metrics.windowEndSeasonLabel,
                                style: Theme.of(context).textTheme.titleMedium,
                              ),
                            ),
                            Text(
                              '${snapshot.dynastyScore}',
                              style: Theme.of(context)
                                  .textTheme
                                  .titleMedium
                                  ?.copyWith(color: GteShellTheme.accentWarm),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        EraLabelChip(
                          era: snapshot.eraLabel,
                          active: snapshot.activeDynasty,
                        ),
                        if (snapshot.reasons.isNotEmpty) ...<Widget>[
                          const SizedBox(height: 8),
                          Text(
                            snapshot.reasons.first,
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                        ],
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
