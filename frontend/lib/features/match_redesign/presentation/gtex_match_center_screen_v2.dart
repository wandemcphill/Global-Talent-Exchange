import 'package:flutter/material.dart';

import '../data/gtex_match_feed.dart';
import '../data/gtex_match_models.dart';
import '../data/gtex_match_repository.dart';
import '../widgets/gtex_2d_pitch.dart';
import '../widgets/gtex_highlights_panel.dart';
import '../widgets/gtex_match_connection_banner.dart';
import '../widgets/gtex_match_lineups.dart';
import '../widgets/gtex_match_scoreboard.dart';
import '../widgets/gtex_match_stats_panel.dart';
import '../widgets/gtex_match_timeline.dart';
import '../widgets/gtex_post_match_panel.dart';
import '../widgets/gtex_tactics_panel.dart';
import 'gtex_match_center_controller.dart';

class _GtexMatchColors {
  static const Color shell = Color(0xFF0A0C0F);
  static const Color panel = Color(0xFF111418);
  static const Color overlay = Color(0xFF181C22);
  static const Color border = Color(0xFF252D38);
  static const Color text = Color(0xFFE8EDF4);
  static const Color muted = Color(0xFF8A97A8);
  static const Color primary = Color(0xFF00E87A);
  static const Color amber = Color(0xFFFFB800);
  static const Color red = Color(0xFFFF3D3D);
  static const Color blue = Color(0xFF2F80ED);
}

class GtexMatchCenterScreenV2 extends StatefulWidget {
  const GtexMatchCenterScreenV2({
    super.key,
    required this.matchId,
    this.repository,
    this.onOpenReplay,
    this.onExit,
  });

  final String matchId;
  final GtexMatchRepository? repository;

  /// Opens the replay archive for this fixture. When null the replay CTA is
  /// hidden rather than rendered as a dead end.
  final ValueChanged<String>? onOpenReplay;

  /// Navigates away from the match centre. When null the back affordance is
  /// hidden so the screen never shows a button that does nothing.
  final VoidCallback? onExit;

  @override
  State<GtexMatchCenterScreenV2> createState() =>
      _GtexMatchCenterScreenV2State();
}

class _GtexMatchCenterScreenV2State extends State<GtexMatchCenterScreenV2> {
  late final GtexMatchCenterController controller;

  @override
  void initState() {
    super.initState();
    controller = GtexMatchCenterController(
      matchId: widget.matchId,
      repository: widget.repository,
    )..load();
  }

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (context, _) {
        if (controller.isLoading && controller.state == null) {
          return const Scaffold(
            backgroundColor: _GtexMatchColors.shell,
            body: _MatchLoadingState(),
          );
        }
        if (controller.error != null && controller.state == null) {
          return Scaffold(
            backgroundColor: _GtexMatchColors.shell,
            body: Center(
              child: _MatchErrorState(
                message: controller.error.toString(),
                onRetry: controller.retry,
                onExit: widget.onExit,
              ),
            ),
          );
        }
        final GtexLiveMatchState? match = controller.state;
        if (match == null) {
          // Feed resolved without a payload. Explicit empty beats a blank
          // scaffold with nothing in it.
          return Scaffold(
            backgroundColor: _GtexMatchColors.shell,
            body: Center(
              child: _MatchEmptyState(
                matchId: widget.matchId,
                onRetry: controller.retry,
                onExit: widget.onExit,
              ),
            ),
          );
        }
        return Scaffold(
          backgroundColor: _GtexMatchColors.shell,
          body: SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: LayoutBuilder(
                builder: (context, constraints) {
                  final wide = constraints.maxWidth >= 1080;
                  final Widget banner = GtexMatchConnectionBanner(
                    status: controller.connection,
                    onRetry: controller.retry,
                    compact: !wide,
                  );
                  final Widget body =
                      !wide
                          ? _MobileMatchView(
                            match: match,
                            controller: controller,
                            onOpenReplay: widget.onOpenReplay,
                          )
                          : Row(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              Expanded(
                                flex: 7,
                                child: _MainPitchWorkspace(
                                  match: match,
                                  controller: controller,
                                  onOpenReplay: widget.onOpenReplay,
                                ),
                              ),
                              const SizedBox(width: 16),
                              SizedBox(
                                width: 392,
                                child: _RightLivePanel(
                                  match: match,
                                  controller: controller,
                                ),
                              ),
                            ],
                          );
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: <Widget>[
                      if (controller.connection !=
                              GtexMatchConnectionStatus.live &&
                          controller.connection !=
                              GtexMatchConnectionStatus.idle) ...<Widget>[
                        banner,
                        const SizedBox(height: 12),
                      ],
                      Expanded(child: body),
                    ],
                  );
                },
              ),
            ),
          ),
        );
      },
    );
  }
}

class _MainPitchWorkspace extends StatelessWidget {
  const _MainPitchWorkspace({
    required this.match,
    required this.controller,
    this.onOpenReplay,
  });

  final GtexLiveMatchState match;
  final GtexMatchCenterController controller;
  final ValueChanged<String>? onOpenReplay;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        GtexMatchScoreboard(match: match),
        const SizedBox(height: 12),
        Expanded(
          child: _BroadcastPanel(
            title: 'TACTICAL CAM',
            trailing: '${match.home.formation} / ${match.away.formation}',
            child: Center(
              child: Gtex2dPitch(
                match: match,
                onPlayerSelected: controller.selectPitchPlayer,
              ),
            ),
          ),
        ),
        const SizedBox(height: 12),
        _HorizontalTimelineScrub(match: match),
        const SizedBox(height: 12),
        _LineupStrip(home: match.home, away: match.away),
        if (match.phase == GtexMatchPhase.fullTime) ...<Widget>[
          GtexPostMatchPanel(match: match),
          _ReplayEntryBar(matchId: match.matchId, onOpenReplay: onOpenReplay),
        ],
      ],
    );
  }
}

/// Post-match handoff into the replay archive.
///
/// Hidden entirely when the host did not supply a destination, so full time
/// never leaves the viewer staring at an inert button.
class _ReplayEntryBar extends StatelessWidget {
  const _ReplayEntryBar({required this.matchId, this.onOpenReplay});

  final String matchId;
  final ValueChanged<String>? onOpenReplay;

  @override
  Widget build(BuildContext context) {
    final ValueChanged<String>? open = onOpenReplay;
    if (open == null) {
      return const SizedBox.shrink();
    }
    return Padding(
      padding: const EdgeInsets.only(top: 12),
      child: SizedBox(
        width: double.infinity,
        child: FilledButton.icon(
          onPressed: () => open(matchId),
          style: FilledButton.styleFrom(
            minimumSize: const Size.fromHeight(48),
          ),
          icon: const Icon(Icons.replay_circle_filled_outlined),
          label: const Text('Watch replay'),
        ),
      ),
    );
  }
}

class _RightLivePanel extends StatelessWidget {
  const _RightLivePanel({
    required this.match,
    required this.controller,
    this.compact = false,
  });

  final GtexLiveMatchState match;
  final GtexMatchCenterController controller;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    if (compact) {
      return ListView(
        padding: EdgeInsets.zero,
        children: [
          _AnalysisTabs(controller: controller, compact: true),
          const SizedBox(height: 10),
          SizedBox(
            height: 240,
            child: _BroadcastPanel(
              title: _tabTitle(controller.selectedTab),
              child: _tabChild(context),
            ),
          ),
          const SizedBox(height: 10),
          _MomentumPanel(match: match),
          const SizedBox(height: 10),
          _EconomyImpactPanel(match: match),
        ],
      );
    }
    return Column(
      children: [
        _AnalysisTabs(controller: controller),
        const SizedBox(height: 12),
        Expanded(
          flex: 3,
          child: _BroadcastPanel(
            title: _tabTitle(controller.selectedTab),
            child: _tabChild(context),
          ),
        ),
        const SizedBox(height: 12),
        _MomentumPanel(match: match),
        const SizedBox(height: 12),
        _EconomyImpactPanel(match: match),
      ],
    );
  }

  Widget _tabChild(BuildContext context) {
    switch (controller.selectedTab) {
      case 1:
        return GtexMatchStatsPanel(match: match);
      case 2:
        return GtexMatchLineups(home: match.home, away: match.away);
      case 3:
        return GtexTacticsPanel(
          isSending: controller.isSendingInstruction,
          onSubmit: controller.sendInstruction,
        );
      case 4:
        return GtexHighlightsPanel(highlights: match.highlights);
      case 0:
      default:
        return GtexMatchTimeline(events: match.timeline);
    }
  }

  String _tabTitle(int index) {
    switch (index) {
      case 1:
        return 'MATCH STATS';
      case 2:
        return 'LINEUPS';
      case 3:
        return 'TACTICS';
      case 4:
        return 'HIGHLIGHTS';
      case 0:
      default:
        return 'LIVE TIMELINE';
    }
  }
}

class _MobileMatchView extends StatelessWidget {
  const _MobileMatchView({
    required this.match,
    required this.controller,
    this.onOpenReplay,
  });

  final GtexLiveMatchState match;
  final GtexMatchCenterController controller;
  final ValueChanged<String>? onOpenReplay;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Row(
          children: [
            const Text(
              'MATCH CENTER',
              style: TextStyle(
                color: _GtexMatchColors.text,
                fontWeight: FontWeight.w900,
                fontSize: 18,
                letterSpacing: .8,
              ),
            ),
            const Spacer(),
            Text(
              '${match.minute} min',
              style: const TextStyle(
                color: _GtexMatchColors.muted,
                fontWeight: FontWeight.w800,
                fontFamily: 'JetBrains Mono',
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        GtexMatchScoreboard(match: match),
        const SizedBox(height: 10),
        Expanded(
          flex: 5,
          child: _BroadcastPanel(
            title: 'TACTICAL CAM',
            child: Center(
              child: Gtex2dPitch(
                match: match,
                onPlayerSelected: controller.selectPitchPlayer,
              ),
            ),
          ),
        ),
        const SizedBox(height: 10),
        _AnalysisTabs(controller: controller, compact: true),
        const SizedBox(height: 10),
        Expanded(
          flex: 4,
          child: _RightLivePanel(
            match: match,
            controller: controller,
            compact: true,
          ),
        ),
        if (match.phase == GtexMatchPhase.fullTime)
          _ReplayEntryBar(matchId: match.matchId, onOpenReplay: onOpenReplay),
      ],
    );
  }
}

class _AnalysisTabs extends StatelessWidget {
  const _AnalysisTabs({required this.controller, this.compact = false});

  final GtexMatchCenterController controller;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final tabs = [
      (0, 'Timeline', Icons.timeline),
      (1, 'Stats', Icons.bar_chart),
      (2, 'Lineups', Icons.groups),
      (3, 'Tactics', Icons.tune),
      (4, 'Clips', Icons.movie),
    ];
    return SizedBox(
      height: 48,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: tabs.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (context, index) {
          final tab = tabs[index];
          final selected = controller.selectedTab == tab.$1;
          return _TabButton(
            label: compact ? tab.$2.toUpperCase() : tab.$2,
            icon: tab.$3,
            selected: selected,
            onTap: () => controller.selectTab(tab.$1),
          );
        },
      ),
    );
  }
}

class _MatchLoadingState extends StatelessWidget {
  const _MatchLoadingState();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 360),
        child: Container(
          padding: const EdgeInsets.all(20),
          decoration: _panelDecoration(),
          child: const Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              SizedBox(
                width: 28,
                height: 28,
                child: CircularProgressIndicator(
                  strokeWidth: 2.4,
                  color: _GtexMatchColors.primary,
                ),
              ),
              SizedBox(height: 14),
              Text(
                'Loading live match authority',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: _GtexMatchColors.text,
                  fontWeight: FontWeight.w900,
                ),
              ),
              SizedBox(height: 6),
              Text(
                'Waiting for persisted match state from the backend.',
                textAlign: TextAlign.center,
                style: TextStyle(color: _GtexMatchColors.muted, height: 1.35),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Shown when the feed resolved but carried no match payload.
class _MatchEmptyState extends StatelessWidget {
  const _MatchEmptyState({
    required this.matchId,
    required this.onRetry,
    this.onExit,
  });

  final String matchId;
  final VoidCallback onRetry;
  final VoidCallback? onExit;

  @override
  Widget build(BuildContext context) {
    return ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 460),
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: _panelDecoration(),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            const Row(
              children: <Widget>[
                Icon(
                  Icons.sports_soccer_outlined,
                  color: _GtexMatchColors.muted,
                ),
                SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'No match state yet',
                    style: TextStyle(
                      color: _GtexMatchColors.text,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              'The match authority has not published a state for "$matchId" yet. '
              'This usually means kickoff has not happened.',
              style: const TextStyle(
                color: _GtexMatchColors.muted,
                height: 1.4,
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: <Widget>[
                FilledButton.icon(
                  onPressed: onRetry,
                  style: FilledButton.styleFrom(
                    minimumSize: const Size(88, 48),
                  ),
                  icon: const Icon(Icons.refresh),
                  label: const Text('Check again'),
                ),
                if (onExit != null) ...<Widget>[
                  const SizedBox(width: 10),
                  TextButton(
                    onPressed: onExit,
                    style: TextButton.styleFrom(
                      minimumSize: const Size(88, 48),
                    ),
                    child: const Text('Back'),
                  ),
                ],
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _MatchErrorState extends StatelessWidget {
  const _MatchErrorState({
    required this.message,
    required this.onRetry,
    this.onExit,
  });

  final String message;
  final VoidCallback onRetry;
  final VoidCallback? onExit;

  @override
  Widget build(BuildContext context) {
    return ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 460),
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: _panelDecoration(),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.error_outline, color: _GtexMatchColors.red),
                SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'Live match unavailable',
                    style: TextStyle(
                      color: _GtexMatchColors.text,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              message,
              style: const TextStyle(
                color: _GtexMatchColors.muted,
                height: 1.4,
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: <Widget>[
                FilledButton.icon(
                  onPressed: onRetry,
                  style: FilledButton.styleFrom(
                    minimumSize: const Size(88, 48),
                  ),
                  icon: const Icon(Icons.refresh),
                  label: const Text('Retry live feed'),
                ),
                if (onExit != null) ...<Widget>[
                  const SizedBox(width: 10),
                  TextButton(
                    onPressed: onExit,
                    style: TextButton.styleFrom(
                      minimumSize: const Size(88, 48),
                    ),
                    child: const Text('Back'),
                  ),
                ],
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _BroadcastPanel extends StatelessWidget {
  const _BroadcastPanel({
    required this.title,
    required this.child,
    this.trailing,
  });

  final String title;
  final String? trailing;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      clipBehavior: Clip.antiAlias,
      decoration: _panelDecoration(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            height: 44,
            padding: const EdgeInsets.symmetric(horizontal: 14),
            decoration: const BoxDecoration(
              color: _GtexMatchColors.overlay,
              border: Border(
                bottom: BorderSide(color: _GtexMatchColors.border),
              ),
            ),
            child: Row(
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: _GtexMatchColors.text,
                    fontWeight: FontWeight.w900,
                    fontSize: 12,
                    letterSpacing: .6,
                  ),
                ),
                const Spacer(),
                if (trailing != null)
                  Text(
                    trailing!,
                    style: const TextStyle(
                      color: _GtexMatchColors.muted,
                      fontFamily: 'JetBrains Mono',
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
              ],
            ),
          ),
          Expanded(
            child: Padding(padding: const EdgeInsets.all(12), child: child),
          ),
        ],
      ),
    );
  }
}

class _HorizontalTimelineScrub extends StatelessWidget {
  const _HorizontalTimelineScrub({required this.match});

  final GtexLiveMatchState match;

  @override
  Widget build(BuildContext context) {
    final List<GtexMatchTimelineEvent> events = match.timeline.reversed
        .take(8)
        .toList(growable: false);
    return SizedBox(
      height: 82,
      child: DecoratedBox(
        decoration: _panelDecoration(),
        child:
            events.isEmpty
                ? const Center(
                  child: Text(
                    'No live timeline events returned yet.',
                    style: TextStyle(color: _GtexMatchColors.muted),
                  ),
                )
                : ListView.separated(
                  padding: const EdgeInsets.all(10),
                  scrollDirection: Axis.horizontal,
                  itemBuilder: (BuildContext context, int index) {
                    final GtexMatchTimelineEvent event = events[index];
                    return Container(
                      width: 210,
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: _GtexMatchColors.overlay,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: _GtexMatchColors.border),
                      ),
                      child: Row(
                        children: [
                          _EventGlyph(type: event.type),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Text(
                                  "${event.minute}'  ${event.title}",
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(
                                    color: _GtexMatchColors.text,
                                    fontWeight: FontWeight.w900,
                                    fontSize: 12,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  event.playerName ?? event.description,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(
                                    color: _GtexMatchColors.muted,
                                    fontSize: 11,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                  separatorBuilder: (_, __) => const SizedBox(width: 8),
                  itemCount: events.length,
                ),
      ),
    );
  }
}

class _LineupStrip extends StatelessWidget {
  const _LineupStrip({required this.home, required this.away});

  final GtexMatchTeam home;
  final GtexMatchTeam away;

  @override
  Widget build(BuildContext context) {
    final List<({GtexLineupPlayer player, Color color, String team})> players =
        [
          for (final GtexLineupPlayer player in home.players.take(5))
            (
              player: player,
              color: _teamColor(home, _GtexMatchColors.primary),
              team: home.shortName,
            ),
          for (final GtexLineupPlayer player in away.players.take(5))
            (
              player: player,
              color: _teamColor(away, _GtexMatchColors.amber),
              team: away.shortName,
            ),
        ];
    return SizedBox(
      height: 74,
      child: DecoratedBox(
        decoration: _panelDecoration(),
        child:
            players.isEmpty
                ? const Center(
                  child: Text(
                    'Lineup feed unavailable for this match.',
                    style: TextStyle(color: _GtexMatchColors.muted),
                  ),
                )
                : ListView.separated(
                  padding: const EdgeInsets.all(10),
                  scrollDirection: Axis.horizontal,
                  itemBuilder: (BuildContext context, int index) {
                    final item = players[index];
                    return _LineupChip(
                      player: item.player,
                      color: item.color,
                      team: item.team,
                    );
                  },
                  separatorBuilder: (_, __) => const SizedBox(width: 8),
                  itemCount: players.length,
                ),
      ),
    );
  }
}

class _LineupChip extends StatelessWidget {
  const _LineupChip({
    required this.player,
    required this.color,
    required this.team,
  });

  final GtexLineupPlayer player;
  final Color color;
  final String team;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 172,
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: _GtexMatchColors.overlay,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: .42)),
      ),
      child: Row(
        children: [
          Container(
            width: 32,
            height: 32,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: color.withValues(alpha: .16),
              borderRadius: BorderRadius.circular(6),
            ),
            child: Text(
              '${player.shirtNumber}',
              style: TextStyle(
                color: color,
                fontFamily: 'JetBrains Mono',
                fontWeight: FontWeight.w900,
                fontSize: 12,
              ),
            ),
          ),
          const SizedBox(width: 9),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  player.name,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: _GtexMatchColors.text,
                    fontWeight: FontWeight.w900,
                    fontSize: 12,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  '$team / ${player.position} / ${player.rating.toStringAsFixed(1)}',
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: _GtexMatchColors.muted,
                    fontSize: 10,
                    fontFamily: 'JetBrains Mono',
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _MomentumPanel extends StatelessWidget {
  const _MomentumPanel({required this.match});

  final GtexLiveMatchState match;

  @override
  Widget build(BuildContext context) {
    final int homeMomentum =
        (match.homeMomentumPercent ?? match.stats.homePossession).clamp(0, 100);
    final int awayMomentum = 100 - homeMomentum;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: _panelDecoration(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'LIVE MOMENTUM',
            style: TextStyle(
              color: _GtexMatchColors.text,
              fontWeight: FontWeight.w900,
              fontSize: 12,
              letterSpacing: .6,
            ),
          ),
          const SizedBox(height: 10),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: Row(
              children: [
                Expanded(
                  flex: homeMomentum == 0 ? 1 : homeMomentum,
                  child: Container(height: 9, color: _GtexMatchColors.primary),
                ),
                Expanded(
                  flex: awayMomentum == 0 ? 1 : awayMomentum,
                  child: Container(height: 9, color: _GtexMatchColors.amber),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: Text(
                  '${match.home.shortName} $homeMomentum%',
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: _GtexMatchColors.primary,
                    fontFamily: 'JetBrains Mono',
                    fontWeight: FontWeight.w800,
                    fontSize: 11,
                  ),
                ),
              ),
              Text(
                '$awayMomentum% ${match.away.shortName}',
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: _GtexMatchColors.amber,
                  fontFamily: 'JetBrains Mono',
                  fontWeight: FontWeight.w800,
                  fontSize: 11,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _EconomyImpactPanel extends StatelessWidget {
  const _EconomyImpactPanel({required this.match});

  final GtexLiveMatchState match;

  @override
  Widget build(BuildContext context) {
    final List<GtexMatchEconomyImpact> impacts = match.economyImpacts
        .take(3)
        .toList(growable: false);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: _panelDecoration(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'ECONOMY IMPACT',
            style: TextStyle(
              color: _GtexMatchColors.text,
              fontWeight: FontWeight.w900,
              fontSize: 12,
              letterSpacing: .6,
            ),
          ),
          const SizedBox(height: 10),
          if (impacts.isEmpty)
            const Text(
              'No live valuation movement returned for this match.',
              style: TextStyle(color: _GtexMatchColors.muted, height: 1.35),
            )
          else
            for (final GtexMatchEconomyImpact impact in impacts) ...[
              _EconomyImpactRow(impact: impact),
              if (impact != impacts.last) const SizedBox(height: 8),
            ],
        ],
      ),
    );
  }
}

class _EconomyImpactRow extends StatelessWidget {
  const _EconomyImpactRow({required this.impact});

  final GtexMatchEconomyImpact impact;

  @override
  Widget build(BuildContext context) {
    final double delta = impact.deltaPercent ?? 0;
    final Color tone =
        delta < 0 ? _GtexMatchColors.red : _GtexMatchColors.primary;
    return Row(
      children: [
        Expanded(
          child: Text(
            impact.playerName,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: _GtexMatchColors.text,
              fontWeight: FontWeight.w800,
              fontSize: 12,
            ),
          ),
        ),
        const SizedBox(width: 10),
        Text(
          impact.currentValueLabel ?? 'LIVE',
          style: const TextStyle(
            color: _GtexMatchColors.muted,
            fontFamily: 'JetBrains Mono',
            fontSize: 11,
          ),
        ),
        const SizedBox(width: 8),
        Text(
          impact.deltaLabel ??
              '${delta >= 0 ? '+' : ''}${delta.toStringAsFixed(1)}%',
          style: TextStyle(
            color: tone,
            fontFamily: 'JetBrains Mono',
            fontWeight: FontWeight.w900,
            fontSize: 11,
          ),
        ),
      ],
    );
  }
}

class _EventGlyph extends StatelessWidget {
  const _EventGlyph({required this.type});

  final GtexPitchEventType type;

  @override
  Widget build(BuildContext context) {
    final (IconData icon, Color color) = switch (type) {
      GtexPitchEventType.goal => (
        Icons.sports_soccer,
        _GtexMatchColors.primary,
      ),
      GtexPitchEventType.shot => (Icons.adjust, _GtexMatchColors.amber),
      GtexPitchEventType.save => (Icons.back_hand, _GtexMatchColors.blue),
      GtexPitchEventType.yellowCard => (
        Icons.crop_portrait,
        _GtexMatchColors.amber,
      ),
      GtexPitchEventType.redCard => (Icons.crop_portrait, _GtexMatchColors.red),
      GtexPitchEventType.substitution => (
        Icons.swap_horiz,
        _GtexMatchColors.blue,
      ),
      GtexPitchEventType.tacticalChange => (
        Icons.tune,
        _GtexMatchColors.primary,
      ),
      _ => (Icons.timeline, _GtexMatchColors.muted),
    };
    return Container(
      width: 34,
      height: 34,
      decoration: BoxDecoration(
        color: color.withValues(alpha: .14),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: .36)),
      ),
      child: Icon(icon, color: color, size: 18),
    );
  }
}

class _TabButton extends StatelessWidget {
  const _TabButton({
    required this.label,
    required this.icon,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final IconData icon;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      selected: selected,
      label: label,
      child: InkWell(
        borderRadius: BorderRadius.circular(6),
        onTap: onTap,
        child: Container(
          // 48dp minimum keeps the tab strip within the accessibility floor.
          constraints: const BoxConstraints(minHeight: 48, minWidth: 48),
          alignment: Alignment.center,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
            color:
                selected
                    ? const Color(0xFF00E87A).withOpacity(.14)
                    : const Color(0xFF101713),
            borderRadius: BorderRadius.circular(6),
            border: Border.all(
              color:
                  selected
                      ? const Color(0xFF00E87A).withOpacity(.48)
                      : const Color(0xFF2A3A31),
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                icon,
                size: 18,
                color:
                    selected ? const Color(0xFF00E87A) : _GtexMatchColors.muted,
              ),
              const SizedBox(width: 10),
              Text(
                label,
                style: TextStyle(
                  color:
                      selected ? _GtexMatchColors.text : _GtexMatchColors.muted,
                  fontWeight: FontWeight.w900,
                  fontSize: 12,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

Color _teamColor(GtexMatchTeam team, Color fallback) {
  final String? raw = team.primaryColorHex?.trim();
  if (raw == null || raw.isEmpty) {
    return fallback;
  }
  final String normalized = raw.replaceFirst('#', '');
  final int? value = int.tryParse(
    normalized.length == 6 ? 'FF$normalized' : normalized,
    radix: 16,
  );
  if (value == null) {
    return fallback;
  }
  return Color(value);
}

BoxDecoration _panelDecoration() {
  return BoxDecoration(
    color: _GtexMatchColors.panel,
    borderRadius: BorderRadius.circular(8),
    border: Border.all(color: _GtexMatchColors.border),
  );
}
