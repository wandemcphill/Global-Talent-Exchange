import 'package:flutter/material.dart';
import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/features/app_routes/gte_navigation_helpers.dart';
import 'package:gte_frontend/features/app_routes/gte_route_data.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/services/avatar_mapper.dart';
import 'package:gte_frontend/widgets/gte_metric_chip.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';
import 'package:gte_frontend/widgets/match/match_hud_avatar.dart';
import 'package:gte_frontend/widgets/squad/squad_avatar_badge.dart';
import 'package:gte_frontend/widgets/gtex_branding.dart';

import 'gte_halftime_analytics_screen.dart';
import 'gte_match_highlights_screen.dart';
import '../match/gtex_match_viewer_screen.dart';

enum _LiveViewMode {
  commentary,
  keyMoments,
}

class GteLiveMatchCenterScreen extends StatefulWidget {
  const GteLiveMatchCenterScreen({
    super.key,
    required this.competition,
    this.isAuthenticated = false,
    this.onOpenLogin,
    this.navigationDependencies,
  });

  final CompetitionSummary competition;
  final bool isAuthenticated;
  final VoidCallback? onOpenLogin;
  final GteNavigationDependencies? navigationDependencies;

  @override
  State<GteLiveMatchCenterScreen> createState() =>
      _GteLiveMatchCenterScreenState();
}

class _GteLiveMatchCenterScreenState extends State<GteLiveMatchCenterScreen> {
  late Future<LiveMatchSnapshot> _snapshotFuture;
  _LiveViewMode _viewMode = _LiveViewMode.commentary;
  final Map<String, bool> _tacticToggles = <String, bool>{
    'High press': true,
    'Overlap fullbacks': false,
    'Early crosses': false,
    'Compact mid-block': true,
  };

  @override
  void initState() {
    super.initState();
    _snapshotFuture = loadLiveMatchSnapshot(widget.competition);
  }

  void _reload() {
    setState(() {
      _snapshotFuture = loadLiveMatchSnapshot(widget.competition);
    });
  }

  Future<void> _openFeatureRoute(GteAppRouteData route) {
    final GteNavigationDependencies? dependencies =
        widget.navigationDependencies;
    if (dependencies == null) {
      return Future<void>.value();
    }
    return GteNavigationHelpers.pushRoute<void>(
      context,
      route: route,
      dependencies: dependencies,
    );
  }

  Future<void> _openHalftime() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => GteHalftimeAnalyticsScreen(
          competition: widget.competition,
        ),
      ),
    );
  }

  Future<void> _openHighlights() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => GteMatchHighlightsScreen(
          competition: widget.competition,
          isAuthenticated: widget.isAuthenticated,
        ),
      ),
    );
  }

  Future<void> _openViewer(LiveMatchSnapshot match) async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => GtexMatchViewerScreen(
          competition: widget.competition,
          matchKey: match.matchId?.trim().isNotEmpty == true
              ? match.matchId!.trim()
              : widget.competition.id,
          fallbackSnapshot: match,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: const Text('Live match center'),
          actions: <Widget>[
            IconButton(
              tooltip: 'Halftime analytics',
              onPressed: _openHalftime,
              icon: const Icon(Icons.analytics_outlined),
            ),
            IconButton(
              tooltip: 'Highlights',
              onPressed: _openHighlights,
              icon: const Icon(Icons.play_circle_outline),
            ),
          ],
        ),
        body: FutureBuilder<LiveMatchSnapshot>(
          future: _snapshotFuture,
          builder: (BuildContext context,
              AsyncSnapshot<LiveMatchSnapshot> snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Padding(
                padding: EdgeInsets.all(20),
                child: GteStatePanel(
                  eyebrow: 'LIVE MATCH CENTER',
                  title: 'Loading match stream',
                  message:
                      'Warming the arena feed, tactical overlay, and key moments.',
                  icon: Icons.live_tv_outlined,
                  accentColor: GteShellTheme.accentArena,
                  isLoading: true,
                ),
              );
            }
            if (!snapshot.hasData) {
              return Padding(
                padding: const EdgeInsets.all(20),
                child: GteStatePanel(
                  title: 'Live match unavailable',
                  message:
                      'Unable to load the match stream right now. Please retry.',
                  icon: Icons.warning_amber_outlined,
                  actionLabel: 'Retry',
                  onAction: _reload,
                ),
              );
            }

            final LiveMatchSnapshot match = snapshot.data!;
            return ListView(
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
              children: <Widget>[
                _LiveScoreboardCard(match: match),
                if (match.isFinal ||
                    match.highlightsAvailable ||
                    match.keyMomentsAvailable) ...<Widget>[
                  const SizedBox(height: 16),
                  GteSurfacePanel(
                    accentColor: GteShellTheme.accentArena,
                    child: Row(
                      children: <Widget>[
                        const Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Text(
                                '2D replay viewer',
                                style: TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              SizedBox(height: 6),
                              Text(
                                'Open the top-down replay to watch marker movement, event emphasis, and the authoritative scoreboard in one surface.',
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(width: 16),
                        FilledButton.icon(
                          onPressed: () => _openViewer(match),
                          icon: const Icon(Icons.sports_soccer),
                          label: const Text('Open viewer'),
                        ),
                      ],
                    ),
                  ),
                ],
                if (widget.navigationDependencies != null) ...<Widget>[
                  const SizedBox(height: 16),
                  GteSurfacePanel(
                    accentColor: GteShellTheme.accentArena,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          'Match extensions',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Prediction and creator-stadium routes only open from a resolved match id. This live center uses the match snapshot id instead of a placeholder.',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                        const SizedBox(height: 14),
                        Wrap(
                          spacing: 12,
                          runSpacing: 12,
                          children: <Widget>[
                            FilledButton.tonalIcon(
                              onPressed: match.matchId == null ||
                                      match.matchId!.trim().isEmpty
                                  ? null
                                  : () => _openFeatureRoute(
                                        FanPredictionMatchRouteData(
                                          matchId: match.matchId!.trim(),
                                        ),
                                      ),
                              icon: const Icon(Icons.insights_outlined),
                              label: const Text('Fan predictions'),
                            ),
                            FilledButton.tonalIcon(
                              onPressed: match.matchId == null ||
                                      match.matchId!.trim().isEmpty
                                  ? null
                                  : () => _openFeatureRoute(
                                        CreatorStadiumMatchRouteData(
                                          matchId: match.matchId!.trim(),
                                        ),
                                      ),
                              icon: const Icon(Icons.stadium_outlined),
                              label: const Text('Stadium monetization'),
                            ),
                            FilledButton.tonalIcon(
                              onPressed: () => _openFeatureRoute(
                                WorldCompetitionContextRouteData(
                                  competitionId: widget.competition.id,
                                ),
                              ),
                              icon: const Icon(Icons.public_outlined),
                              label: const Text('World context'),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ],
                const SizedBox(height: 16),
                GteSurfacePanel(
                  accentColor: GteShellTheme.accentArena,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Spectator modes',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 10),
                      Text(
                        'Pick the view that fits the moment. The 2D commentary is free. Key-moment video is a paid, premium stream.',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 12),
                      SegmentedButton<_LiveViewMode>(
                        segments: const <ButtonSegment<_LiveViewMode>>[
                          ButtonSegment<_LiveViewMode>(
                            value: _LiveViewMode.commentary,
                            label: Text('2D commentary'),
                            icon: Icon(Icons.toc_outlined),
                          ),
                          ButtonSegment<_LiveViewMode>(
                            value: _LiveViewMode.keyMoments,
                            label: Text('Key-moment video'),
                            icon: Icon(Icons.videocam_outlined),
                          ),
                        ],
                        selected: <_LiveViewMode>{_viewMode},
                        onSelectionChanged: (Set<_LiveViewMode> value) {
                          setState(() => _viewMode = value.first);
                        },
                      ),
                      const SizedBox(height: 14),
                      if (_viewMode == _LiveViewMode.commentary)
                        _CommentaryPanel(match: match)
                      else
                        _KeyMomentPanel(
                          match: match,
                          isAuthenticated: widget.isAuthenticated,
                          onOpenLogin: widget.onOpenLogin,
                        ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                GteSurfacePanel(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Live momentum',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Momentum reads update in real time. Browsing tactics and stats never pauses the match stream.',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 14),
                      _MomentumStrip(values: match.momentum),
                    ],
                  ),
                ),
                const SizedBox(height: 20),
                const GtexSectionHeader(
                  eyebrow: 'TACTICS + STATS',
                  title: 'Stay in the match while managing tactics live.',
                  description:
                      'Spectators can scan tactics, stats, and incidents without pausing the action.',
                  accent: GteShellTheme.accentArena,
                ),
                const SizedBox(height: 14),
                GteSurfacePanel(
                  child: DefaultTabController(
                    length: 4,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        const TabBar(
                          isScrollable: true,
                          tabAlignment: TabAlignment.start,
                          tabs: <Tab>[
                            Tab(text: 'Stats'),
                            Tab(text: 'Tactics'),
                            Tab(text: 'Lineups'),
                            Tab(text: 'Incidents'),
                          ],
                        ),
                        const SizedBox(height: 12),
                        SizedBox(
                          height: 360,
                          child: TabBarView(
                            children: <Widget>[
                              _MatchStatsView(match: match),
                              _TacticsView(
                                toggles: _tacticToggles,
                                onToggle: (String key, bool value) {
                                  setState(() => _tacticToggles[key] = value);
                                },
                                onApply: () {
                                  AppFeedback.showSuccess(
                                    context,
                                    'Tactical changes applied without pausing the match.',
                                  );
                                },
                              ),
                              _LineupsView(match: match),
                              _IncidentView(match: match),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _LiveScoreboardCard extends StatelessWidget {
  const _LiveScoreboardCard({required this.match});

  final LiveMatchSnapshot match;

  @override
  Widget build(BuildContext context) {
    final String status = match.isFinal
        ? 'FINAL'
        : match.isHalftime
            ? 'HALFTIME'
            : match.isLive
                ? 'LIVE ${match.minute}\''
                : 'PRE-MATCH';
    return GteSurfacePanel(
      accentColor: GteShellTheme.accentArena,
      emphasized: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <Widget>[
              _StatusChip(label: status),
              const GteMetricChip(label: 'Spectator', value: 'OPEN'),
              const GteMetricChip(label: 'Video', value: 'KEY MOMENTS'),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: <Widget>[
              Expanded(
                child: _TeamScore(
                  team: match.homeTeam,
                  score: match.homeScore,
                  alignRight: false,
                  featuredPlayer: _featuredPlayer(match.homeLineup),
                  matchId: match.matchId,
                ),
              ),
              const SizedBox(width: 10),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(16),
                  color: Colors.white.withValues(alpha: 0.06),
                  border:
                      Border.all(color: Colors.white.withValues(alpha: 0.14)),
                ),
                child: Text(
                  '${match.homeScore} : ${match.awayScore}',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _TeamScore(
                  team: match.awayTeam,
                  score: match.awayScore,
                  alignRight: true,
                  featuredPlayer: _featuredPlayer(match.awayLineup),
                  matchId: match.matchId,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            'Tactical changes apply instantly, without pausing the match feed.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }

  LiveMatchLineupPlayer? _featuredPlayer(List<LiveMatchLineupPlayer> players) {
    for (final LiveMatchLineupPlayer player in players) {
      if (player.captain) {
        return player;
      }
    }
    if (players.isEmpty) {
      return null;
    }
    return players.first;
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: GteShellTheme.accentArena.withValues(alpha: 0.18),
        border: Border.all(
          color: GteShellTheme.accentArena.withValues(alpha: 0.4),
        ),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: GteShellTheme.accentArena,
              letterSpacing: 1.1,
            ),
      ),
    );
  }
}

class _TeamScore extends StatelessWidget {
  const _TeamScore({
    required this.team,
    required this.score,
    required this.alignRight,
    required this.featuredPlayer,
    required this.matchId,
  });

  final String team;
  final int score;
  final bool alignRight;
  final LiveMatchLineupPlayer? featuredPlayer;
  final String? matchId;

  @override
  Widget build(BuildContext context) {
    final avatar = featuredPlayer == null
        ? null
        : AvatarMapper.fromLiveLineupPlayer(
            featuredPlayer!,
            teamName: team,
            matchId: matchId,
          );
    return Column(
      crossAxisAlignment:
          alignRight ? CrossAxisAlignment.end : CrossAxisAlignment.start,
      children: <Widget>[
        if (avatar != null) ...<Widget>[
          MatchHudAvatar(avatar: avatar),
          const SizedBox(height: 8),
        ],
        Text(
          team,
          style: Theme.of(context).textTheme.titleMedium,
          textAlign: alignRight ? TextAlign.right : TextAlign.left,
        ),
        const SizedBox(height: 6),
        Text(
          'Scoreline focus',
          style: Theme.of(context).textTheme.bodySmall,
          textAlign: alignRight ? TextAlign.right : TextAlign.left,
        ),
      ],
    );
  }
}

class _CommentaryPanel extends StatelessWidget {
  const _CommentaryPanel({required this.match});

  final LiveMatchSnapshot match;

  @override
  Widget build(BuildContext context) {
    final List<LiveMatchEvent> events =
        match.commentary.reversed.take(6).toList();
    if (events.isEmpty) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            '2D commentary feed',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Text(
            'No live commentary yet. Check back after kickoff.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          '2D commentary feed',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 8),
        ...events.map(
          (LiveMatchEvent event) => Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(14),
                color: Colors.white.withValues(alpha: 0.04),
                border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
              ),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    '${event.minute}\'',
                    style: Theme.of(context).textTheme.labelLarge,
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(event.title,
                            style: Theme.of(context).textTheme.titleSmall),
                        const SizedBox(height: 4),
                        Text(event.detail,
                            style: Theme.of(context).textTheme.bodySmall),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _KeyMomentPanel extends StatelessWidget {
  const _KeyMomentPanel({
    required this.match,
    required this.isAuthenticated,
    required this.onOpenLogin,
  });

  final LiveMatchSnapshot match;
  final bool isAuthenticated;
  final VoidCallback? onOpenLogin;

  @override
  Widget build(BuildContext context) {
    if (!isAuthenticated) {
      return Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          color: Colors.white.withValues(alpha: 0.04),
          border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'Key-moment video locked',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 6),
            Text(
              'Sign in and unlock the premium key-moment stream for the current match.',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 10),
            FilledButton(
              onPressed: onOpenLogin,
              child: const Text('Unlock with Arena Pass'),
            ),
          ],
        ),
      );
    }

    if (match.keyMoments.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          color: Colors.white.withValues(alpha: 0.04),
          border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'Key-moment video',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 6),
            Text(
              'No premium key moments yet. The stream will populate as the match progresses.',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          'Key-moment video',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 8),
        ...match.keyMoments.map(
          (LiveMatchHighlightClip clip) => Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(14),
                color: Colors.white.withValues(alpha: 0.04),
                border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
              ),
              child: Row(
                children: <Widget>[
                  const Icon(Icons.videocam_outlined),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(clip.title,
                            style: Theme.of(context).textTheme.titleSmall),
                        const SizedBox(height: 4),
                        Text('${clip.minute}\' • ${clip.durationLabel}',
                            style: Theme.of(context).textTheme.bodySmall),
                      ],
                    ),
                  ),
                  FilledButton.tonal(
                    onPressed: () {},
                    child: const Text('Play'),
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _MomentumStrip extends StatelessWidget {
  const _MomentumStrip({required this.values});

  final List<int> values;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 68,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: values
            .map(
              (int value) => Expanded(
                child: Container(
                  margin: const EdgeInsets.symmetric(horizontal: 3),
                  height: 10 + (value.abs() * 12).toDouble(),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(8),
                    color: value >= 0
                        ? GteShellTheme.accentArena.withValues(alpha: 0.6)
                        : GteShellTheme.accentWarm.withValues(alpha: 0.6),
                  ),
                ),
              ),
            )
            .toList(growable: false),
      ),
    );
  }
}

class _MatchStatsView extends StatelessWidget {
  const _MatchStatsView({required this.match});

  final LiveMatchSnapshot match;

  @override
  Widget build(BuildContext context) {
    final int homeMomentum =
        match.momentum.where((int value) => value > 0).length;
    final int awayMomentum =
        match.momentum.where((int value) => value < 0).length;
    final int total = homeMomentum + awayMomentum + 1;
    final int homePossession = (45 + (homeMomentum / total * 20)).round();
    final int awayPossession = 100 - homePossession;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: <Widget>[
            GteMetricChip(
                label: '${match.homeTeam} Poss', value: '$homePossession%'),
            GteMetricChip(
                label: '${match.awayTeam} Poss', value: '$awayPossession%'),
            GteMetricChip(
                label: 'Shots',
                value: '${3 + match.homeScore + match.awayScore}'),
            GteMetricChip(
                label: 'xG (est)', value: '${1.1 + match.homeScore * 0.4}'),
            GteMetricChip(label: 'Pressing', value: 'Aggressive'),
          ],
        ),
        const SizedBox(height: 16),
        Text(
          'Stats update in real time while the match continues.',
          style: Theme.of(context).textTheme.bodySmall,
        ),
      ],
    );
  }
}

class _TacticsView extends StatelessWidget {
  const _TacticsView({
    required this.toggles,
    required this.onToggle,
    required this.onApply,
  });

  final Map<String, bool> toggles;
  final void Function(String key, bool value) onToggle;
  final VoidCallback onApply;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          'Tactical changes can be applied at any time without pausing the match.',
          style: Theme.of(context).textTheme.bodySmall,
        ),
        const SizedBox(height: 12),
        ...toggles.entries.map(
          (MapEntry<String, bool> entry) => SwitchListTile(
            value: entry.value,
            onChanged: (bool value) => onToggle(entry.key, value),
            title: Text(entry.key),
            dense: true,
            contentPadding: EdgeInsets.zero,
          ),
        ),
        const SizedBox(height: 8),
        FilledButton.icon(
          onPressed: onApply,
          icon: const Icon(Icons.tune_outlined),
          label: const Text('Apply tactical changes'),
        ),
      ],
    );
  }
}

class _LineupsView extends StatelessWidget {
  const _LineupsView({required this.match});

  final LiveMatchSnapshot match;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(match.homeTeam, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 6),
          ...match.homeLineup.map((LiveMatchLineupPlayer player) {
            return _LineupTile(
              player: player,
              teamName: match.homeTeam,
              matchId: match.matchId,
            );
          }),
          const SizedBox(height: 16),
          Text(match.awayTeam, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 6),
          ...match.awayLineup.map((LiveMatchLineupPlayer player) {
            return _LineupTile(
              player: player,
              teamName: match.awayTeam,
              matchId: match.matchId,
            );
          }),
        ],
      ),
    );
  }
}

class _LineupTile extends StatelessWidget {
  const _LineupTile({
    required this.player,
    required this.teamName,
    required this.matchId,
  });

  final LiveMatchLineupPlayer player;
  final String teamName;
  final String? matchId;

  @override
  Widget build(BuildContext context) {
    final avatar = AvatarMapper.fromLiveLineupPlayer(
      player,
      teamName: teamName,
      matchId: matchId,
    );
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: <Widget>[
          SizedBox(
            width: 32,
            child: Text(player.position,
                style: Theme.of(context).textTheme.bodySmall),
          ),
          SquadAvatarBadge(avatar: avatar, size: 32),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              player.captain ? '${player.name} (C)' : player.name,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ),
          Text(player.rating.toStringAsFixed(1),
              style: Theme.of(context).textTheme.bodySmall),
        ],
      ),
    );
  }
}

class _IncidentView extends StatelessWidget {
  const _IncidentView({required this.match});

  final LiveMatchSnapshot match;

  @override
  Widget build(BuildContext context) {
    if (match.cards.isEmpty && match.substitutions.isEmpty) {
      return Text(
        'No incidents logged yet.',
        style: Theme.of(context).textTheme.bodySmall,
      );
    }
    return SingleChildScrollView(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          if (match.cards.isNotEmpty) ...<Widget>[
            Text('Cards', style: Theme.of(context).textTheme.titleSmall),
            const SizedBox(height: 6),
            ...match.cards
                .map((LiveMatchEvent event) => _IncidentTile(event: event)),
            const SizedBox(height: 12),
          ],
          if (match.substitutions.isNotEmpty) ...<Widget>[
            Text('Substitutions',
                style: Theme.of(context).textTheme.titleSmall),
            const SizedBox(height: 6),
            ...match.substitutions
                .map((LiveMatchEvent event) => _IncidentTile(event: event)),
          ],
        ],
      ),
    );
  }
}

class _IncidentTile extends StatelessWidget {
  const _IncidentTile({required this.event});

  final LiveMatchEvent event;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: <Widget>[
          Text('${event.minute}\'',
              style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(event.title,
                    style: Theme.of(context).textTheme.bodyMedium),
                Text(event.detail,
                    style: Theme.of(context).textTheme.bodySmall),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
