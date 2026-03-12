import 'package:flutter/material.dart';

import '../../../../data/gte_api_repository.dart';
import '../../../../widgets/gte_shell_theme.dart';
import '../../../../widgets/gte_state_panel.dart';
import '../../../../widgets/gte_surface_panel.dart';
import '../data/dynasty_api_repository.dart';
import '../data/dynasty_profile_dto.dart';
import '../data/dynasty_repository.dart';
import '../widgets/dynasty_loading_panel.dart';
import '../widgets/dynasty_reason_list.dart';
import '../widgets/dynasty_score_card.dart';
import '../widgets/dynasty_status_banner.dart';
import '../widgets/streak_indicator_row.dart';
import 'dynasty_controller.dart';

class DynastyScreen extends StatefulWidget {
  const DynastyScreen({
    super.key,
    required this.clubId,
    this.controller,
    this.repository,
    this.baseUrl = 'http://127.0.0.1:8000',
    this.backendMode = GteBackendMode.liveThenFixture,
    this.onOpenTimeline,
    this.onOpenLeaderboard,
  });

  final String clubId;
  final DynastyController? controller;
  final DynastyRepository? repository;
  final String baseUrl;
  final GteBackendMode backendMode;
  final VoidCallback? onOpenTimeline;
  final VoidCallback? onOpenLeaderboard;

  @override
  State<DynastyScreen> createState() => _DynastyScreenState();
}

class _DynastyScreenState extends State<DynastyScreen> {
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
    _controller.loadOverview(widget.clubId);
  }

  @override
  void didUpdateWidget(covariant DynastyScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.clubId != widget.clubId) {
      _controller.loadOverview(widget.clubId);
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
          title: const Text('Dynasty Overview'),
        ),
        body: AnimatedBuilder(
          animation: _controller,
          builder: (BuildContext context, Widget? child) {
            final bool isInitialLoad =
                _controller.isLoadingOverview && _controller.profile == null;
            if (isInitialLoad) {
              return const _DynastyOverviewLoadingState();
            }
            if (_controller.overviewError != null &&
                _controller.profile == null) {
              return Padding(
                padding: const EdgeInsets.all(20),
                child: GteStatePanel(
                  title: 'Dynasty feed unavailable',
                  message: _controller.overviewError!,
                  actionLabel: 'Retry',
                  onAction: () {
                    _controller.loadOverview(widget.clubId);
                  },
                  icon: Icons.shield_outlined,
                ),
              );
            }

            final DynastyProfileDto? profile = _controller.profile;
            if (profile == null) {
              return const SizedBox.shrink();
            }

            return RefreshIndicator(
              onRefresh: () => _controller.loadOverview(widget.clubId),
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
                children: <Widget>[
                  DynastyStatusBanner(
                    profile: profile,
                    onOpenTimeline: widget.onOpenTimeline,
                    onOpenLeaderboard: widget.onOpenLeaderboard,
                  ),
                  if (_controller.overviewError != null) ...<Widget>[
                    const SizedBox(height: 20),
                    _InlineNotice(message: _controller.overviewError!),
                  ],
                  const SizedBox(height: 20),
                  LayoutBuilder(
                    builder:
                        (BuildContext context, BoxConstraints constraints) {
                      final bool stacked = constraints.maxWidth < 720;
                      final double cardWidth = stacked
                          ? constraints.maxWidth
                          : (constraints.maxWidth - 16) / 2;
                      return Wrap(
                        spacing: 16,
                        runSpacing: 16,
                        children: <Widget>[
                          SizedBox(
                            width: cardWidth,
                            child: DynastyScoreCard(profile: profile),
                          ),
                          SizedBox(
                            width: cardWidth,
                            child: _LastFourSummaryCard(profile: profile),
                          ),
                        ],
                      );
                    },
                  ),
                  const SizedBox(height: 20),
                  Text(
                    'Active streaks',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'Runs that keep the badge in the dynasty conversation.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 12),
                  StreakIndicatorRow(streaks: profile.activeStreaks),
                  const SizedBox(height: 20),
                  DynastyReasonList(
                    title: profile.hasRecognizedDynasty
                        ? 'Dynasty trigger reasons'
                        : 'What still separates them',
                    reasons: profile.reasons,
                    emptyTitle: profile.isRisingClub
                        ? 'No dynasty case yet'
                        : 'Still building a case file',
                    emptyMessage: profile.isRisingClub
                        ? 'The club is rising, but the detector is still waiting for a decisive cycle.'
                        : 'This club has not yet produced the repeated elite finishes needed for an era label.',
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

class _LastFourSummaryCard extends StatelessWidget {
  const _LastFourSummaryCard({
    required this.profile,
  });

  final DynastyProfileDto profile;

  @override
  Widget build(BuildContext context) {
    final List<DynastySeasonSummaryDto> seasons = profile.lastFourSeasonSummary;
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Last four seasons',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Text(
            profile.hasRecognizedDynasty
                ? 'The stretch that built the current era label.'
                : 'The run is promising, but it still sits below dynasty standard.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),
          if (seasons.isEmpty)
            Text(
              'Recent season summaries will appear once four full campaigns are logged.',
              style: Theme.of(context).textTheme.bodyMedium,
            )
          else
            Column(
              children: seasons
                  .map(
                    (DynastySeasonSummaryDto season) => Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Container(
                            width: 10,
                            height: 10,
                            margin: const EdgeInsets.only(top: 5),
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: _isHotSeason(season)
                                  ? GteShellTheme.accentWarm
                                  : GteShellTheme.stroke,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: <Widget>[
                                Text(
                                  season.seasonLabel,
                                  style:
                                      Theme.of(context).textTheme.titleMedium,
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  _seasonSummary(season),
                                  style: Theme.of(context).textTheme.bodyMedium,
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  )
                  .toList(growable: false),
            ),
        ],
      ),
    );
  }

  bool _isHotSeason(DynastySeasonSummaryDto season) {
    return season.leagueTitle ||
        season.championsLeagueTitle ||
        season.worldSuperCupWinner;
  }

  String _seasonSummary(DynastySeasonSummaryDto season) {
    final List<String> parts = <String>[
      if (season.leagueFinish != null) 'League finish ${season.leagueFinish}',
      if (season.leagueTitle) 'league title',
      if (season.championsLeagueTitle) 'Champions League',
      if (season.worldSuperCupWinner) 'World Super Cup',
      if (season.worldSuperCupQualified && !season.worldSuperCupWinner)
        'world qualification',
      '${season.trophyCount} trophies',
      'rep ${season.reputationGain >= 0 ? '+' : ''}${season.reputationGain}',
    ];
    return parts.join(' | ');
  }
}

class _DynastyOverviewLoadingState extends StatelessWidget {
  const _DynastyOverviewLoadingState();

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
      children: const <Widget>[
        DynastyLoadingPanel(lines: 4, height: 210),
        SizedBox(height: 20),
        DynastyLoadingPanel(lines: 4, height: 180),
        SizedBox(height: 20),
        DynastyLoadingPanel(lines: 3, height: 140),
      ],
    );
  }
}

class _InlineNotice extends StatelessWidget {
  const _InlineNotice({
    required this.message,
  });

  final String message;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const Icon(Icons.info_outline, color: GteShellTheme.accentWarm),
          const SizedBox(width: 12),
          Expanded(
            child: Text(message, style: Theme.of(context).textTheme.bodyMedium),
          ),
        ],
      ),
    );
  }
}
