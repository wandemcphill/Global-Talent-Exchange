import 'package:flutter/material.dart';

import '../data/gtex_match_demo_repository.dart';
import '../data/gtex_match_models.dart';
import '../widgets/gtex_2d_pitch.dart';
import '../widgets/gtex_highlights_panel.dart';
import '../widgets/gtex_match_lineups.dart';
import '../widgets/gtex_match_scoreboard.dart';
import '../widgets/gtex_match_stats_panel.dart';
import '../widgets/gtex_match_timeline.dart';
import '../widgets/gtex_post_match_panel.dart';
import '../widgets/gtex_tactics_panel.dart';
import 'gtex_match_center_controller.dart';

class GtexMatchCenterScreenV2 extends StatefulWidget {
  const GtexMatchCenterScreenV2({
    super.key,
    required this.matchId,
    this.repository,
  });

  final String matchId;
  final GtexMatchRepository? repository;

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
            backgroundColor: Color(0xFF030806),
            body: Center(child: CircularProgressIndicator()),
          );
        }
        if (controller.error != null && controller.state == null) {
          return Scaffold(
            backgroundColor: const Color(0xFF030806),
            body: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(
                    Icons.error_outline,
                    color: Colors.redAccent,
                    size: 42,
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'Could not load match',
                    style: Theme.of(
                      context,
                    ).textTheme.titleLarge?.copyWith(color: Colors.white),
                  ),
                  const SizedBox(height: 8),
                  ElevatedButton(
                    onPressed: controller.load,
                    child: const Text('Retry'),
                  ),
                ],
              ),
            ),
          );
        }
        final match = controller.state!;
        return Scaffold(
          backgroundColor: const Color(0xFF030806),
          body: SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: LayoutBuilder(
                builder: (context, constraints) {
                  final wide = constraints.maxWidth >= 1120;
                  if (!wide) {
                    return _MobileMatchView(
                      match: match,
                      controller: controller,
                    );
                  }
                  return Row(
                    children: [
                      SizedBox(
                        width: 280,
                        child: _MatchSidePanel(
                          match: match,
                          controller: controller,
                        ),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: _MainPitchWorkspace(
                          match: match,
                          controller: controller,
                        ),
                      ),
                      const SizedBox(width: 16),
                      SizedBox(
                        width: 360,
                        child: _RightLivePanel(
                          match: match,
                          controller: controller,
                        ),
                      ),
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
  const _MainPitchWorkspace({required this.match, required this.controller});

  final GtexLiveMatchState match;
  final GtexMatchCenterController controller;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        GtexMatchScoreboard(match: match),
        const SizedBox(height: 16),
        Expanded(
          child: Center(
            child: Gtex2dPitch(
              match: match,
              onPlayerSelected: controller.selectPitchPlayer,
            ),
          ),
        ),
        const SizedBox(height: 16),
        if (match.phase == GtexMatchPhase.fullTime)
          GtexPostMatchPanel(match: match),
      ],
    );
  }
}

class _MatchSidePanel extends StatelessWidget {
  const _MatchSidePanel({required this.match, required this.controller});

  final GtexLiveMatchState match;
  final GtexMatchCenterController controller;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: _panelDecoration(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.all(16),
            child: Text(
              'Match Center',
              style: TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w900,
                fontSize: 18,
              ),
            ),
          ),
          _TabButton(
            label: 'Timeline',
            icon: Icons.timeline,
            selected: controller.selectedTab == 0,
            onTap: () => controller.selectTab(0),
          ),
          _TabButton(
            label: 'Lineups',
            icon: Icons.groups,
            selected: controller.selectedTab == 1,
            onTap: () => controller.selectTab(1),
          ),
          _TabButton(
            label: 'Stats',
            icon: Icons.bar_chart,
            selected: controller.selectedTab == 2,
            onTap: () => controller.selectTab(2),
          ),
          _TabButton(
            label: 'Tactics',
            icon: Icons.tune,
            selected: controller.selectedTab == 3,
            onTap: () => controller.selectTab(3),
          ),
          _TabButton(
            label: 'Highlights',
            icon: Icons.movie,
            selected: controller.selectedTab == 4,
            onTap: () => controller.selectTab(4),
          ),
          const Spacer(),
          Padding(
            padding: const EdgeInsets.all(16),
            child: Text(
              '2D is the primary gameplay view until the 3D engine is production-ready.',
              style: TextStyle(
                color: Colors.white.withOpacity(.52),
                height: 1.3,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _RightLivePanel extends StatelessWidget {
  const _RightLivePanel({required this.match, required this.controller});

  final GtexLiveMatchState match;
  final GtexMatchCenterController controller;

  @override
  Widget build(BuildContext context) {
    Widget child;
    switch (controller.selectedTab) {
      case 1:
        child = GtexMatchLineups(home: match.home, away: match.away);
        break;
      case 2:
        child = GtexMatchStatsPanel(match: match);
        break;
      case 3:
        child = GtexTacticsPanel(
          isSending: controller.isSendingInstruction,
          onSubmit: controller.sendInstruction,
        );
        break;
      case 4:
        child = GtexHighlightsPanel(highlights: match.highlights);
        break;
      case 0:
      default:
        child = GtexMatchTimeline(events: match.timeline);
    }
    return Container(decoration: _panelDecoration(), child: child);
  }
}

class _MobileMatchView extends StatelessWidget {
  const _MobileMatchView({required this.match, required this.controller});

  final GtexLiveMatchState match;
  final GtexMatchCenterController controller;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Row(
          children: [
            const Text(
              'Match Center',
              style: TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w900,
                fontSize: 18,
              ),
            ),
            const Spacer(),
            Text(
              '${match.minute} min',
              style: TextStyle(
                color: Colors.white.withOpacity(.58),
                fontWeight: FontWeight.w800,
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        GtexMatchScoreboard(match: match),
        const SizedBox(height: 10),
        Expanded(
          flex: 5,
          child: Center(
            child: Gtex2dPitch(
              match: match,
              onPlayerSelected: controller.selectPitchPlayer,
            ),
          ),
        ),
        const SizedBox(height: 10),
        const Align(
          alignment: Alignment.centerLeft,
          child: Text(
            'Timeline',
            style: TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w900,
              fontSize: 14,
            ),
          ),
        ),
        const SizedBox(height: 8),
        Expanded(
          flex: 4,
          child: _RightLivePanel(match: match, controller: controller),
        ),
      ],
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
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
          decoration: BoxDecoration(
            color:
                selected
                    ? const Color(0xFF18FF88).withOpacity(.14)
                    : Colors.transparent,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color:
                  selected
                      ? const Color(0xFF18FF88).withOpacity(.24)
                      : Colors.transparent,
            ),
          ),
          child: Row(
            children: [
              Icon(
                icon,
                color:
                    selected
                        ? const Color(0xFF18FF88)
                        : Colors.white.withOpacity(.58),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  label,
                  style: TextStyle(
                    color:
                        selected ? Colors.white : Colors.white.withOpacity(.66),
                    fontWeight: FontWeight.w900,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

BoxDecoration _panelDecoration() {
  return BoxDecoration(
    color: const Color(0xFF07130E),
    borderRadius: BorderRadius.circular(24),
    border: Border.all(color: Colors.white.withOpacity(.08)),
    boxShadow: const [BoxShadow(blurRadius: 24, color: Colors.black38)],
  );
}
