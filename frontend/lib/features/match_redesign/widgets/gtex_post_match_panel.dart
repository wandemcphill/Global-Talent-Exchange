import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../data/gtex_match_models.dart';
import '../../match/widgets/gtex_matchday_ad_slot.dart';
import 'gtex_match_visual_tokens.dart';

class GtexPostMatchPanel extends StatefulWidget {
  const GtexPostMatchPanel({
    super.key,
    required this.match,
    this.onOpenPortfolio,
    this.onOpenMarket,
    this.onOpenNewsroomReport,
    this.onOpenReplay,
    this.onReplayGoal,
  });

  final GtexLiveMatchState match;
  final VoidCallback? onOpenPortfolio;
  final VoidCallback? onOpenMarket;
  final VoidCallback? onOpenNewsroomReport;
  final VoidCallback? onOpenReplay;
  final ValueChanged<int>? onReplayGoal;

  @override
  State<GtexPostMatchPanel> createState() => _GtexPostMatchPanelState();
}

class _GtexPostMatchPanelState extends State<GtexPostMatchPanel> {
  bool _showHomeRatings = true;

  @override
  Widget build(BuildContext context) {
    final bool finalWhistle = widget.match.phase == GtexMatchPhase.fullTime;
    final String resultLabel = widget.match.home.score == widget.match.away.score
        ? 'DRAW · POINTS SHARED'
        : widget.match.home.score > widget.match.away.score
            ? '${widget.match.home.name.toUpperCase()} VICTORIOUS'
            : '${widget.match.away.name.toUpperCase()} VICTORIOUS';

    final post = widget.match.postMatch ??
        GtexPostMatchPackage(
          motm: GtexPlayerOfTheMatch(
            playerName: '',
            teamName: '',
            shirtNumber: 0,
            rating: 0,
            goals: 0,
            assists: 0,
            keyPasses: 0,
            passAcc: 0,
            summary: 'A verified player-of-the-match record is not available for this fixture.',
            available: false,
            ratingAvailable: false,
            assistsAvailable: false,
            keyPassesAvailable: false,
            passAccAvailable: false,
          ),
          shotMap: const [],
          momentum: const [],
          ratings: const [],
          shareSummary: 'Verified match analytics are not available for this fixture.',
        );

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: GtexMatchVisualTokens.panelDecoration(
        background: GtexMatchVisualTokens.surfaceOverlay,
        borderColor: finalWhistle
            ? GtexMatchVisualTokens.live.withOpacity(0.40)
            : GtexMatchVisualTokens.borderStrong,
      ),
      child: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Status Header
            Row(
              children: [
                Icon(
                  finalWhistle ? Icons.verified_rounded : Icons.lock_clock_rounded,
                  color: finalWhistle
                      ? GtexMatchVisualTokens.live
                      : GtexMatchVisualTokens.amber,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    finalWhistle ? 'OFFICIAL MATCH REPORT & ANALYTICS' : 'REPORT LOCKED',
                    style: const TextStyle(
                      color: GtexMatchVisualTokens.textPrimary,
                      fontWeight: FontWeight.w900,
                      fontSize: 13,
                      letterSpacing: .8,
                    ),
                  ),
                ),
                if (finalWhistle)
                  ElevatedButton.icon(
                    onPressed: () {
                      Clipboard.setData(ClipboardData(text: post.shareSummary));
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('Match summary copied to clipboard!'),
                          duration: Duration(seconds: 2),
                          backgroundColor: Color(0xFF0F172A),
                          behavior: SnackBarBehavior.floating,
                        ),
                      );
                    },
                    icon: const Icon(Icons.share_rounded, size: 13),
                    label: const Text('SHARE CARD'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF162332),
                      foregroundColor: GtexMatchVisualTokens.live,
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      textStyle: const TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 0.5,
                      ),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(6),
                        side: const BorderSide(color: GtexMatchVisualTokens.live, width: 0.8),
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 12),

            if (finalWhistle)
              const Padding(
                padding: EdgeInsets.only(bottom: 6),
                child: Text(
                  'FULL-TIME PERFORMANCE REVIEW',
                  style: TextStyle(
                    color: GtexMatchVisualTokens.textSecondary,
                    fontSize: 10,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 1.0,
                  ),
                ),
              ),

            // Big Result Title
            Text(
              finalWhistle ? resultLabel : 'MATCH STILL IN PROGRESS',
              style: const TextStyle(
                color: GtexMatchVisualTokens.textPrimary,
                fontFamily: 'Barlow Condensed',
                fontSize: 26,
                fontWeight: FontWeight.w900,
                letterSpacing: 0,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              finalWhistle
                  ? 'All event ledger transactions, player rating algorithms, and tactical models settled by authoritative match simulation.'
                  : 'The post-match analytics surface unlocks when the persisted match authority declares full time.',
              style: const TextStyle(
                color: GtexMatchVisualTokens.textSecondary,
                fontSize: 12,
                height: 1.35,
              ),
            ),
            const SizedBox(height: 14),

            if (finalWhistle) ...[
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: _MatchTeamReview(
                      team: widget.match.home,
                      alignEnd: false,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: _MatchTeamReview(
                      team: widget.match.away,
                      alignEnd: true,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),

              // Match Statistics Breakdown
              _MatchPerformanceSummary(match: widget.match),
              const SizedBox(height: 14),

              // Goal Replays
              if (widget.onReplayGoal != null &&
                  widget.match.timeline.any((e) => e.type == GtexPitchEventType.goal)) ...[
                _GoalReplaysList(
                  match: widget.match,
                  onReplayGoal: widget.onReplayGoal!,
                ),
                const SizedBox(height: 14),
              ],

              // Only render analytics when supported by source records.
              if (post.motm.available)
                _MotmCelebrationCard(motm: post.motm)
              else
                const GtexMatchEmptyFeed(
                  icon: Icons.emoji_events_outlined,
                  title: 'Player of the match unavailable',
                  message: 'No verified player rating or goal-contribution record was returned.',
                ),
              const SizedBox(height: 14),

              if (post.shotMap.isNotEmpty)
                _XgShotMapCard(shots: post.shotMap, homeTeam: widget.match.home, awayTeam: widget.match.away)
              else
                const GtexMatchEmptyFeed(
                  icon: Icons.gps_off_rounded,
                  title: 'Verified shot map unavailable',
                  message: 'Shot coordinates and xG are shown only when recorded by the match data source.',
                ),
              const SizedBox(height: 14),

              if (post.momentum.isNotEmpty)
                _MatchMomentumCard(momentum: post.momentum, homeTeam: widget.match.home, awayTeam: widget.match.away)
              else
                const GtexMatchEmptyFeed(
                  icon: Icons.show_chart_rounded,
                  title: 'Event-impact timeline unavailable',
                  message: 'No recorded timeline events are available for an event-impact view.',
                ),
              const SizedBox(height: 14),

              if (post.ratings.isNotEmpty)
                _PlayerRatingsSection(
                  ratings: post.ratings,
                  homeTeam: widget.match.home,
                  awayTeam: widget.match.away,
                  showHome: _showHomeRatings,
                  onToggleTeam: (home) => setState(() {
                    _showHomeRatings = home;
                  }),
                )
              else
                const GtexMatchEmptyFeed(
                  icon: Icons.bar_chart_rounded,
                  title: 'Player ratings unavailable',
                  message: 'No verified player ratings were supplied by the match data source.',
                ),
              const SizedBox(height: 14),

              // 5. Post-Match Manager Press Conference
              _ManagerPressConferenceCard(match: widget.match),
              const SizedBox(height: 14),



              // 8. XP & Manager Token Settlement
              _PostMatchSettlementCard(match: widget.match),
              const SizedBox(height: 14),

              // 9. Owner Decision Loop Actions
              const GtexMatchdayAdSlot(
                placement: 'Full-time match report & replay',
                compact: true,
              ),
              const SizedBox(height: 14),
              _OwnerDecisionLoop(
                onOpenPortfolio: widget.onOpenPortfolio,
                onOpenMarket: widget.onOpenMarket,
                onOpenNewsroomReport: widget.onOpenNewsroomReport,
                onOpenReplay: widget.onOpenReplay,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _MotmCelebrationCard extends StatelessWidget {
  const _MotmCelebrationCard({required this.motm});

  final GtexPlayerOfTheMatch motm;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF2E2405), Color(0xFF141A22)],
        ),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFFFFB800), width: 1.2),
        boxShadow: const [
          BoxShadow(
            color: Color(0x33FFB800),
            blurRadius: 16,
            offset: Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                decoration: BoxDecoration(
                  color: const Color(0x33FFB800),
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: const Color(0xFFFFB800)),
                ),
                child: const Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.emoji_events_rounded, size: 12, color: Color(0xFFFFB800)),
                    SizedBox(width: 4),
                    Text(
                      'PLAYER OF THE MATCH',
                      style: TextStyle(
                        color: Color(0xFFFFB800),
                        fontSize: 9.5,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 0.8,
                      ),
                    ),
                  ],
                ),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: const Color(0xFFFFB800),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  motm.ratingAvailable ? '${motm.rating.toStringAsFixed(1)} RATING' : 'RATING N/A',
                  style: const TextStyle(
                    color: Color(0xFF0F172A),
                    fontSize: 11,
                    fontWeight: FontWeight.w900,
                    fontFamily: 'JetBrains Mono',
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Player Headline
          Row(
            children: [
              Container(
                width: 38,
                height: 38,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: const Color(0xFFFFB800),
                  border: Border.all(color: Colors.white, width: 1.5),
                ),
                child: Text(
                  '${motm.shirtNumber}',
                  style: const TextStyle(
                    color: Color(0xFF0F172A),
                    fontSize: 14,
                    fontWeight: FontWeight.w900,
                    fontFamily: 'JetBrains Mono',
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      motm.playerName.toUpperCase(),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: GtexMatchVisualTokens.textPrimary,
                        fontSize: 16,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 0.5,
                      ),
                    ),
                    Text(
                      motm.teamName,
                      style: const TextStyle(
                        color: Color(0xFFFFB800),
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Match Statistics Metrics Strip
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
            decoration: BoxDecoration(
              color: const Color(0x66080E14),
              borderRadius: BorderRadius.circular(6),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _MotmMetricItem(label: 'GOALS', value: '${motm.goals}'),
                _MotmMetricItem(label: 'ASSISTS', value: motm.assistsAvailable ? '${motm.assists}' : 'N/A'),
                _MotmMetricItem(label: 'KEY PASSES', value: motm.keyPassesAvailable ? '${motm.keyPasses}' : 'N/A'),
                _MotmMetricItem(label: 'PASS ACC', value: motm.passAccAvailable ? '${motm.passAcc}%' : 'N/A'),
              ],
            ),
          ),
          const SizedBox(height: 8),
          Text(
            motm.summary,
            style: const TextStyle(
              color: Color(0xFFB0BAC5),
              fontSize: 11,
              fontWeight: FontWeight.w600,
              height: 1.35,
            ),
          ),
        ],
      ),
    );
  }
}

class _MotmMetricItem extends StatelessWidget {
  const _MotmMetricItem({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(
          value,
          style: const TextStyle(
            color: Color(0xFFFFB800),
            fontSize: 13,
            fontWeight: FontWeight.w900,
            fontFamily: 'JetBrains Mono',
          ),
        ),
        Text(
          label,
          style: const TextStyle(
            color: GtexMatchVisualTokens.textSecondary,
            fontSize: 8.5,
            fontWeight: FontWeight.w800,
          ),
        ),
      ],
    );
  }
}

class _XgShotMapCard extends StatelessWidget {
  const _XgShotMapCard({
    required this.shots,
    required this.homeTeam,
    required this.awayTeam,
  });

  final List<GtexShotMapEntry> shots;
  final GtexMatchTeam homeTeam;
  final GtexMatchTeam awayTeam;

  @override
  Widget build(BuildContext context) {
    final double homeXg = shots
        .where((s) => s.isHome)
        .fold(0.0, (acc, s) => acc + s.xg);
    final double awayXg = shots
        .where((s) => !s.isHome)
        .fold(0.0, (acc, s) => acc + s.xg);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF101924),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: GtexMatchVisualTokens.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.gps_fixed_rounded, size: 16, color: GtexMatchVisualTokens.live),
              const SizedBox(width: 6),
              const Text(
                'EXPECTED GOALS (xG) & SHOT MAP',
                style: TextStyle(
                  color: GtexMatchVisualTokens.textPrimary,
                  fontSize: 11,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 1.0,
                ),
              ),
              const Spacer(),
              Text(
                '${homeTeam.shortName} ${homeXg.toStringAsFixed(2)} - ${awayXg.toStringAsFixed(2)} ${awayTeam.shortName}',
                style: const TextStyle(
                  color: GtexMatchVisualTokens.live,
                  fontSize: 10,
                  fontWeight: FontWeight.w900,
                  fontFamily: 'JetBrains Mono',
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Visual Pitch Shot Board
          AspectRatio(
            aspectRatio: 2.2,
            child: Container(
              decoration: BoxDecoration(
                color: const Color(0xFF0D2516),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0x3300E87A)),
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: Stack(
                  children: [
                    // Pitch lines
                    Positioned.fill(child: CustomPaint(painter: _MiniPitchPainter())),

                    // Empty state when no shots recorded
                    if (shots.isEmpty)
                      const Center(
                        child: Text(
                          'No shot events recorded in this match (0.00 xG)',
                          style: TextStyle(
                            color: GtexMatchVisualTokens.textTertiary,
                            fontSize: 11,
                            fontStyle: FontStyle.italic,
                          ),
                        ),
                      ),

                    // Shot markers
                    for (final shot in shots)
                      Positioned(
                        left: (shot.x * 320).clamp(10.0, 310.0),
                        top: (shot.y * 140).clamp(10.0, 130.0),
                        child: _ShotMarker(shot: shot),
                      ),
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(height: 10),

          // Shot Legend
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: const [
              _ShotLegendItem(color: Color(0xFF00E87A), label: 'Goal ⚽'),
              SizedBox(width: 14),
              _ShotLegendItem(color: Color(0xFF00BCD4), label: 'Saved 🧤'),
              SizedBox(width: 14),
              _ShotLegendItem(color: Color(0xFFFFB800), label: 'Missed/Blocked ✖'),
            ],
          ),
        ],
      ),
    );
  }
}

class _MiniPitchPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final linePaint = Paint()
      ..color = Colors.white.withOpacity(0.25)
      ..strokeWidth = 1.0
      ..style = PaintingStyle.stroke;

    // Pitch perimeter
    canvas.drawRect(Rect.fromLTWH(8, 8, size.width - 16, size.height - 16), linePaint);
    // Halfway line
    canvas.drawLine(Offset(size.width / 2, 8), Offset(size.width / 2, size.height - 8), linePaint);
    // Center circle
    canvas.drawCircle(Offset(size.width / 2, size.height / 2), size.height * 0.16, linePaint);

    // Left & Right penalty boxes
    canvas.drawRect(Rect.fromLTWH(8, size.height * 0.28, size.width * 0.15, size.height * 0.44), linePaint);
    canvas.drawRect(Rect.fromLTWH(size.width - 8 - size.width * 0.15, size.height * 0.28, size.width * 0.15, size.height * 0.44), linePaint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _ShotMarker extends StatelessWidget {
  const _ShotMarker({required this.shot});

  final GtexShotMapEntry shot;

  @override
  Widget build(BuildContext context) {
    final double size = (12.0 + shot.xg * 16.0).clamp(12.0, 24.0);
    Color color;
    if (shot.isGoal) {
      color = const Color(0xFF00E87A);
    } else if (shot.outcome == 'saved') {
      color = const Color(0xFF00BCD4);
    } else {
      color = const Color(0xFFFFB800);
    }

    return Tooltip(
      message: "${shot.minute}' · ${shot.playerName} (${shot.outcome.toUpperCase()} · ${shot.xg.toStringAsFixed(2)} xG)",
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: color.withOpacity(0.85),
          border: Border.all(color: Colors.white, width: 1.2),
          boxShadow: [
            if (shot.isGoal)
              BoxShadow(
                color: color.withOpacity(0.65),
                blurRadius: 10,
                spreadRadius: 2,
              ),
          ],
        ),
        child: Center(
          child: Text(
            shot.isGoal ? '★' : '',
            style: const TextStyle(fontSize: 9, color: Color(0xFF0F172A), fontWeight: FontWeight.w900),
          ),
        ),
      ),
    );
  }
}

class _ShotLegendItem extends StatelessWidget {
  const _ShotLegendItem({required this.color, required this.label});

  final Color color;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: color,
          ),
        ),
        const SizedBox(width: 4),
        Text(
          label,
          style: const TextStyle(
            color: GtexMatchVisualTokens.textSecondary,
            fontSize: 9.5,
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    );
  }
}

class _MatchMomentumCard extends StatelessWidget {
  const _MatchMomentumCard({
    required this.momentum,
    required this.homeTeam,
    required this.awayTeam,
  });

  final List<GtexMomentumPoint> momentum;
  final GtexMatchTeam homeTeam;
  final GtexMatchTeam awayTeam;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF101924),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: GtexMatchVisualTokens.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.waves_rounded, size: 16, color: GtexMatchVisualTokens.amber),
              const SizedBox(width: 6),
              const Text(
                'MATCH MOMENTUM FLOW (90 MIN)',
                style: TextStyle(
                  color: GtexMatchVisualTokens.textPrimary,
                  fontSize: 11,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 1.0,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Momentum Bar Chart
          SizedBox(
            height: 70,
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                for (final point in momentum)
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 1.5),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          // Positive (Home) bar
                          Expanded(
                            child: Align(
                              alignment: Alignment.bottomCenter,
                              child: Container(
                                height: point.value > 0
                                    ? (point.value / 100.0) * 32.0
                                    : 0,
                                decoration: BoxDecoration(
                                  color: GtexMatchVisualTokens.live,
                                  borderRadius: const BorderRadius.vertical(top: Radius.circular(2)),
                                ),
                              ),
                            ),
                          ),
                          // Baseline
                          Container(height: 1, color: Colors.white24),
                          // Negative (Away) bar
                          Expanded(
                            child: Align(
                              alignment: Alignment.topCenter,
                              child: Container(
                                height: point.value < 0
                                    ? (point.value.abs() / 100.0) * 32.0
                                    : 0,
                                decoration: BoxDecoration(
                                  color: GtexMatchVisualTokens.amber,
                                  borderRadius: const BorderRadius.vertical(bottom: Radius.circular(2)),
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(height: 6),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                '▲ ${homeTeam.shortName} PRESSURE',
                style: const TextStyle(
                  color: GtexMatchVisualTokens.live,
                  fontSize: 9,
                  fontWeight: FontWeight.w900,
                  fontFamily: 'JetBrains Mono',
                ),
              ),
              const Text(
                '45\' HT',
                style: TextStyle(
                  color: GtexMatchVisualTokens.textSecondary,
                  fontSize: 9,
                  fontFamily: 'JetBrains Mono',
                ),
              ),
              Text(
                '▼ ${awayTeam.shortName} PRESSURE',
                style: const TextStyle(
                  color: GtexMatchVisualTokens.amber,
                  fontSize: 9,
                  fontWeight: FontWeight.w900,
                  fontFamily: 'JetBrains Mono',
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _PlayerRatingsSection extends StatelessWidget {
  const _PlayerRatingsSection({
    required this.ratings,
    required this.homeTeam,
    required this.awayTeam,
    required this.showHome,
    required this.onToggleTeam,
  });

  final List<GtexPlayerRatingItem> ratings;
  final GtexMatchTeam homeTeam;
  final GtexMatchTeam awayTeam;
  final bool showHome;
  final ValueChanged<bool> onToggleTeam;

  @override
  Widget build(BuildContext context) {
    final filtered = ratings.where((r) => r.isHome == showHome).toList()
      ..sort((a, b) => b.rating.compareTo(a.rating));

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF101924),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: GtexMatchVisualTokens.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.star_rate_rounded, size: 16, color: Color(0xFFFFB800)),
              const SizedBox(width: 6),
              const Text(
                'PLAYER RATINGS & PERFORMANCE',
                style: TextStyle(
                  color: GtexMatchVisualTokens.textPrimary,
                  fontSize: 11,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 1.0,
                ),
              ),
              const Spacer(),

              // Team Selector Buttons
              InkWell(
                onTap: () => onToggleTeam(true),
                borderRadius: BorderRadius.circular(4),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                  decoration: BoxDecoration(
                    color: showHome ? const Color(0x3300E87A) : Colors.transparent,
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(
                      color: showHome ? GtexMatchVisualTokens.live : Colors.white24,
                    ),
                  ),
                  child: Text(
                    homeTeam.shortName,
                    style: TextStyle(
                      color: showHome ? GtexMatchVisualTokens.live : Colors.white60,
                      fontSize: 9.5,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 4),
              InkWell(
                onTap: () => onToggleTeam(false),
                borderRadius: BorderRadius.circular(4),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                  decoration: BoxDecoration(
                    color: !showHome ? const Color(0x33FFB800) : Colors.transparent,
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(
                      color: !showHome ? GtexMatchVisualTokens.amber : Colors.white24,
                    ),
                  ),
                  child: Text(
                    awayTeam.shortName,
                    style: TextStyle(
                      color: !showHome ? GtexMatchVisualTokens.amber : Colors.white60,
                      fontSize: 9.5,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          for (final item in filtered)
            _PlayerRatingRow(item: item),
        ],
      ),
    );
  }
}

class _PlayerRatingRow extends StatelessWidget {
  const _PlayerRatingRow({required this.item});

  final GtexPlayerRatingItem item;

  @override
  Widget build(BuildContext context) {
    Color badgeColor;
    if (item.rating >= 8.5) {
      badgeColor = const Color(0xFFFFB800);
    } else if (item.rating >= 7.5) {
      badgeColor = const Color(0xFF00E87A);
    } else {
      badgeColor = const Color(0xFF94A3B8);
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      decoration: BoxDecoration(
        color: const Color(0xFF162332),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: Colors.white.withOpacity(0.06)),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(
              color: badgeColor.withOpacity(0.18),
              borderRadius: BorderRadius.circular(4),
              border: Border.all(color: badgeColor, width: 0.8),
            ),
            child: Text(
              item.rating.toStringAsFixed(1),
              style: TextStyle(
                color: badgeColor,
                fontSize: 10,
                fontWeight: FontWeight.w900,
                fontFamily: 'JetBrains Mono',
              ),
            ),
          ),
          const SizedBox(width: 8),
          Text(
            '#${item.shirtNumber}',
            style: const TextStyle(
              color: GtexMatchVisualTokens.textSecondary,
              fontSize: 10,
              fontFamily: 'JetBrains Mono',
            ),
          ),
          const SizedBox(width: 6),
          Expanded(
            child: Text(
              item.name,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: GtexMatchVisualTokens.textPrimary,
                fontSize: 11,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          for (final badge in item.badges.take(2))
            Container(
              margin: const EdgeInsets.only(left: 4),
              padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
              decoration: BoxDecoration(
                color: const Color(0xFF0B121A),
                borderRadius: BorderRadius.circular(3),
                border: Border.all(color: Colors.white12),
              ),
              child: Text(
                badge,
                style: const TextStyle(
                  color: Colors.white70,
                  fontSize: 8.5,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _GoalReplaysList extends StatelessWidget {
  const _GoalReplaysList({
    required this.match,
    required this.onReplayGoal,
  });

  final GtexLiveMatchState match;
  final ValueChanged<int> onReplayGoal;

  @override
  Widget build(BuildContext context) {
    final goalEvents = match.timeline.where((e) => e.type == GtexPitchEventType.goal).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'GOAL REPLAYS & HIGHLIGHT MOMENTS',
          style: TextStyle(
            color: GtexMatchVisualTokens.amber,
            fontSize: 11,
            fontWeight: FontWeight.w900,
            letterSpacing: 1.1,
          ),
        ),
        const SizedBox(height: 8),
        for (final event in goalEvents)
          Container(
            margin: const EdgeInsets.only(bottom: 7),
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 9),
            decoration: BoxDecoration(
              color: GtexMatchVisualTokens.surfaceRaised,
              borderRadius: BorderRadius.circular(7),
              border: Border.all(color: GtexMatchVisualTokens.border),
            ),
            child: Row(
              children: [
                Container(
                  width: 32,
                  height: 32,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: GtexMatchVisualTokens.amber.withOpacity(.12),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(color: GtexMatchVisualTokens.amber.withOpacity(.35)),
                  ),
                  child: const Icon(Icons.sports_soccer_rounded, color: GtexMatchVisualTokens.amber, size: 17),
                ),
                const SizedBox(width: 9),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        "${event.minute}' · ${event.playerName?.trim().isNotEmpty == true ? event.playerName!.trim() : event.title}",
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: GtexMatchVisualTokens.textPrimary,
                          fontWeight: FontWeight.w900,
                          fontSize: 12,
                        ),
                      ),
                      if (event.description.trim().isNotEmpty)
                        Text(
                          event.description,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            color: GtexMatchVisualTokens.textSecondary,
                            fontSize: 10,
                          ),
                        ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                TextButton.icon(
                  key: Key('gtex-post-match-goal-replay-${event.minute}'),
                  onPressed: () => onReplayGoal(event.minute),
                  icon: const Icon(Icons.replay_rounded, size: 14),
                  label: const Text('Replay', style: TextStyle(fontSize: 11)),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class _OwnerDecisionLoop extends StatelessWidget {
  const _OwnerDecisionLoop({
    this.onOpenPortfolio,
    this.onOpenMarket,
    this.onOpenNewsroomReport,
    this.onOpenReplay,
  });

  final VoidCallback? onOpenPortfolio;
  final VoidCallback? onOpenMarket;
  final VoidCallback? onOpenNewsroomReport;
  final VoidCallback? onOpenReplay;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'MATCHDAY → OWNER DECISION LOOP',
          style: TextStyle(
            color: GtexMatchVisualTokens.live,
            fontSize: 12,
            fontWeight: FontWeight.w900,
            letterSpacing: 1.0,
          ),
        ),
        const SizedBox(height: 6),
        const Text(
          'Review your portfolio position, explore new talent, or open the match report. Financial and valuation effects are shown only when confirmed by their owning services.',
          style: TextStyle(
            color: GtexMatchVisualTokens.textSecondary,
            fontSize: 11.5,
            height: 1.35,
          ),
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: [
            if (onOpenPortfolio != null)
              FilledButton.icon(
                key: const Key('gtex-post-match-portfolio-btn'),
                onPressed: onOpenPortfolio,
                icon: const Icon(Icons.account_balance_wallet_outlined, size: 15),
                label: const Text('Review Portfolio', style: TextStyle(fontSize: 11)),
              ),
            if (onOpenMarket != null)
              OutlinedButton.icon(
                key: const Key('gtex-post-match-market-btn'),
                onPressed: onOpenMarket,
                icon: const Icon(Icons.storefront_outlined, size: 15),
                label: const Text('Explore Transfer Hub', style: TextStyle(fontSize: 11)),
              ),
            if (onOpenNewsroomReport != null)
              OutlinedButton.icon(
                key: const Key('gtex-post-match-newsroom-btn'),
                onPressed: onOpenNewsroomReport,
                icon: const Icon(Icons.article_outlined, size: 15),
                label: const Text('Open Newsroom Match Report', style: TextStyle(fontSize: 11)),
              ),
            if (onOpenReplay != null)
              TextButton.icon(
                onPressed: onOpenReplay,
                icon: const Icon(Icons.replay_circle_filled_outlined, size: 15),
                label: const Text('Open 2D Replay', style: TextStyle(fontSize: 11)),
              ),
          ],
        ),
      ],
    );
  }
}

class _MatchPerformanceSummary extends StatelessWidget {
  const _MatchPerformanceSummary({required this.match});

  final GtexLiveMatchState match;

  @override
  Widget build(BuildContext context) {
    final GtexMatchStats stats = match.stats;

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: GtexMatchVisualTokens.surfaceRaised,
        borderRadius: BorderRadius.circular(9),
        border: Border.all(color: GtexMatchVisualTokens.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text(
            'MATCH PERFORMANCE STATISTICS',
            style: TextStyle(
              color: GtexMatchVisualTokens.textPrimary,
              fontSize: 11,
              fontWeight: FontWeight.w900,
              letterSpacing: .8,
            ),
          ),
          const SizedBox(height: 12),
          _MatchStatRow(
            label: 'Possession',
            home: stats.possessionAvailable ? '${stats.homePossession}%' : 'N/A',
            away: stats.possessionAvailable ? '${stats.awayPossession}%' : 'N/A',
            homeValue: stats.possessionAvailable ? stats.homePossession.toDouble() : 0,
            awayValue: stats.possessionAvailable ? stats.awayPossession.toDouble() : 0,
          ),
          _MatchStatRow(
            label: 'Shots',
            home: stats.shotsAvailable ? '${stats.homeShots}' : 'N/A',
            away: stats.shotsAvailable ? '${stats.awayShots}' : 'N/A',
            homeValue: stats.shotsAvailable ? stats.homeShots.toDouble() : 0,
            awayValue: stats.shotsAvailable ? stats.awayShots.toDouble() : 0,
          ),
          _MatchStatRow(
            label: 'Shots on target',
            home: '${stats.homeShotsOnTarget}',
            away: '${stats.awayShotsOnTarget}',
            homeValue: stats.homeShotsOnTarget.toDouble(),
            awayValue: stats.awayShotsOnTarget.toDouble(),
          ),
          _MatchStatRow(
            label: 'Pass accuracy',
            home: stats.passingAvailable ? '${stats.homePassAccuracy}%' : 'N/A',
            away: stats.passingAvailable ? '${stats.awayPassAccuracy}%' : 'N/A',
            homeValue: stats.passingAvailable ? stats.homePassAccuracy.toDouble() : 0,
            awayValue: stats.passingAvailable ? stats.awayPassAccuracy.toDouble() : 0,
          ),
          _MatchStatRow(
            label: 'Expected goals',
            home: stats.expectedGoalsAvailable ? stats.homeExpectedGoals.toStringAsFixed(2) : 'N/A',
            away: stats.expectedGoalsAvailable ? stats.awayExpectedGoals.toStringAsFixed(2) : 'N/A',
            homeValue: stats.expectedGoalsAvailable ? stats.homeExpectedGoals : 0,
            awayValue: stats.expectedGoalsAvailable ? stats.awayExpectedGoals : 0,
          ),
          if (match.timeline.any((e) => e.type == GtexPitchEventType.substitution)) ...[
            const SizedBox(height: 12),
            const Text(
              'TACTICAL SUBSTITUTIONS',
              style: TextStyle(
                color: GtexMatchVisualTokens.textSecondary,
                fontSize: 10,
                fontWeight: FontWeight.w900,
                letterSpacing: .8,
              ),
            ),
            const SizedBox(height: 7),
            for (final GtexMatchTimelineEvent event in match.timeline.where((e) => e.type == GtexPitchEventType.substitution))
              Container(
                margin: const EdgeInsets.only(bottom: 6),
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                decoration: BoxDecoration(
                  color: GtexMatchVisualTokens.surfaceOverlay,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: GtexMatchVisualTokens.border),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.sync_alt_rounded, color: GtexMatchVisualTokens.amber, size: 16),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        '${event.minute}\' ${event.title}',
                        style: const TextStyle(
                          color: GtexMatchVisualTokens.textPrimary,
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
          ],
        ],
      ),
    );
  }
}

class _MatchStatRow extends StatelessWidget {
  const _MatchStatRow({
    required this.label,
    required this.home,
    required this.away,
    required this.homeValue,
    required this.awayValue,
  });

  final String label;
  final String home;
  final String away;
  final double homeValue;
  final double awayValue;

  @override
  Widget build(BuildContext context) {
    final double total = homeValue.abs() + awayValue.abs();
    final double homeShare = total <= 0 ? .5 : homeValue.abs() / total;
    final double awayShare = total <= 0 ? .5 : awayValue.abs() / total;

    return Padding(
      padding: const EdgeInsets.only(bottom: 9),
      child: Column(
        children: [
          Row(
            children: [
              SizedBox(
                width: 48,
                child: Text(
                  home,
                  style: const TextStyle(
                    color: GtexMatchVisualTokens.live,
                    fontWeight: FontWeight.w900,
                    fontFamily: 'JetBrains Mono',
                    fontSize: 11,
                  ),
                ),
              ),
              Expanded(
                child: Center(
                  child: Text(
                    label,
                    style: const TextStyle(
                      color: GtexMatchVisualTokens.textSecondary,
                      fontSize: 9.5,
                      fontWeight: FontWeight.w800,
                      letterSpacing: .5,
                    ),
                  ),
                ),
              ),
              SizedBox(
                width: 48,
                child: Text(
                  away,
                  textAlign: TextAlign.right,
                  style: const TextStyle(
                    color: GtexMatchVisualTokens.amber,
                    fontWeight: FontWeight.w900,
                    fontFamily: 'JetBrains Mono',
                    fontSize: 11,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          ClipRRect(
            borderRadius: BorderRadius.circular(3),
            child: SizedBox(
              height: 5,
              child: Row(
                children: [
                  Expanded(
                    flex: (homeShare * 100).toInt(),
                    child: Container(color: GtexMatchVisualTokens.live),
                  ),
                  const SizedBox(width: 2),
                  Expanded(
                    flex: (awayShare * 100).toInt(),
                    child: Container(color: GtexMatchVisualTokens.amber),
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

class _PressQuestionData {
  const _PressQuestionData({
    required this.outlet,
    required this.journalist,
    required this.avatarColor,
    required this.question,
    required this.options,
  });

  final String outlet;
  final String journalist;
  final Color avatarColor;
  final String question;
  final List<_PressOptionData> options;
}

class _PressOptionData {
  const _PressOptionData({
    required this.text,
    required this.impactLabel,
    required this.impactColor,
  });

  final String text;
  final String impactLabel;
  final Color impactColor;
}

class _ManagerPressConferenceCard extends StatefulWidget {
  const _ManagerPressConferenceCard({required this.match});

  final GtexLiveMatchState match;

  @override
  State<_ManagerPressConferenceCard> createState() => _ManagerPressConferenceCardState();
}

class _ManagerPressConferenceCardState extends State<_ManagerPressConferenceCard> {
  final Map<int, int> _selectedAnswers = {};

  List<_PressQuestionData> _buildQuestions() {
    final int homeScore = widget.match.home.score;
    final int awayScore = widget.match.away.score;
    final bool won = homeScore > awayScore;
    final bool drew = homeScore == awayScore;

    return [
      _PressQuestionData(
        outlet: 'THE ATHLETIC · TACTICAL DESK',
        journalist: 'Samir Croft, Senior Analyst',
        avatarColor: const Color(0xFF60A5FA),
        question: won
            ? 'Manager, your team adapted fluidly across tactical phases today. What was your key tactical directive?'
            : drew
                ? 'Manager, both sides cancelled each other out in the middle third. How did you assess the tactical battle?'
                : 'Manager, your side struggled against their defensive transition. Where did the plan fall short?',
        options: won
            ? const [
                _PressOptionData(
                  text: '"We pressed high and dominated the central half-spaces to dictate tempo."',
                  impactLabel: '+18 TACTICAL DISCIPLINE · +12 BOARD CONFIDENCE',
                  impactColor: Color(0xFF00E87A),
                ),
                _PressOptionData(
                  text: '"Our positional flexibility allowed the wingers to overload wide areas."',
                  impactLabel: '+15 TEAM CHEMISTRY · +10 ADAPTABILITY',
                  impactColor: Color(0xFF60A5FA),
                ),
                _PressOptionData(
                  text: '"Credit to the squad. They executed instructions with elite maturity."',
                  impactLabel: '+20 SQUAD MORALE · +10 REPUTATION',
                  impactColor: Color(0xFFFFB800),
                ),
              ]
            : const [
                _PressOptionData(
                  text: '"We held solid defensive compactness, but lacked the final killer pass."',
                  impactLabel: '+12 PRAGMATISM · +8 STABILITY',
                  impactColor: Color(0xFF60A5FA),
                ),
                _PressOptionData(
                  text: '"The workrate was there. We will refine attacking rotations in training."',
                  impactLabel: '+15 WORK ETHIC · +10 FOCUS',
                  impactColor: Color(0xFF00E87A),
                ),
                _PressOptionData(
                  text: '"We set high standards here. A point is not enough for our ambition."',
                  impactLabel: '+18 AMBITION · -5 STRESS RISK',
                  impactColor: Color(0xFFFF5722),
                ),
              ],
      ),
      _PressQuestionData(
        outlet: 'SKY SPORTS FOOTBALL',
        journalist: 'Laura Evans, Pitchside Anchor',
        avatarColor: const Color(0xFFFF5722),
        question: won
            ? 'The fans were roaring all 90 minutes. How special was the connection between pitch and stadium?'
            : 'How do you maintain momentum going into the next fixture after today’s intense 90 minutes?',
        options: won
            ? const [
                _PressOptionData(
                  text: '"This win belongs to the fans. Their energy gave us an unstoppable second wind."',
                  impactLabel: '+25 FAN APPROVAL · +20 STADIUM PASSION',
                  impactColor: Color(0xFF00E87A),
                ),
                _PressOptionData(
                  text: '"Professional execution. We celebrate tonight and refocus tomorrow morning."',
                  impactLabel: '+15 PROFESSIONALISM · +10 COMPOSURE',
                  impactColor: Color(0xFF60A5FA),
                ),
                _PressOptionData(
                  text: '"This is the benchmark. Every match must be contested with this intensity."',
                  impactLabel: '+18 SQUAD DETERMINATION · +12 REPUTATION',
                  impactColor: Color(0xFFFFB800),
                ),
              ]
            : const [
                _PressOptionData(
                  text: '"We stay united. Difficult phases build champions; we rise together."',
                  impactLabel: '+20 SQUAD RESOLVE · +15 FAN LOYALTY',
                  impactColor: Color(0xFF00E87A),
                ),
                _PressOptionData(
                  text: '"We review video analytics tomorrow, adjust key metrics, and bounce back."',
                  impactLabel: '+15 ANALYTICAL FOCUS · +10 CONFIDENCE',
                  impactColor: Color(0xFF60A5FA),
                ),
                _PressOptionData(
                  text: '"Every player knows what is required. Accountability is paramount."',
                  impactLabel: '+18 STANDARDS · +10 LEADERSHIP',
                  impactColor: Color(0xFFFF5722),
                ),
              ],
      ),
      _PressQuestionData(
        outlet: 'GTEX FAN VOICE',
        journalist: 'Dave Wilson, Supporters Forum',
        avatarColor: const Color(0xFFFFB800),
        question:
            'Looking ahead to the transfer window and player progression, how confident are you in this squad’s ceiling?',
        options: const [
          _PressOptionData(
            text: '"We have extraordinary emerging talent. The long-term trajectory is world-class."',
            impactLabel: '+25 BOARD VISION · +20 TALENT CONFIDENCE',
            impactColor: Color(0xFF00E87A),
          ),
          _PressOptionData(
            text: '"Our scouting network is actively identifying high-value tactical profiles."',
            impactLabel: '+18 MARKET REPUTATION · +15 SCOUT ACCURACY',
            impactColor: Color(0xFF60A5FA),
          ),
          _PressOptionData(
            text: '"I believe in our current roster. We develop from within and reward hard work."',
            impactLabel: '+22 ACADEMY PRIDE · +18 SQUAD LOYALTY',
            impactColor: Color(0xFFFFB800),
          ),
        ],
      ),
    ];
  }

  @override
  Widget build(BuildContext context) {
    final questions = _buildQuestions();
    final int answeredCount = _selectedAnswers.length;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF111827),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: answeredCount == questions.length
              ? const Color(0xFF00E87A)
              : const Color(0x663B82F6),
          width: 1.2,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: const Color(0x333B82F6),
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: const Color(0xFF3B82F6)),
                ),
                child: const Icon(
                  Icons.record_voice_over_rounded,
                  size: 15,
                  color: Color(0xFF60A5FA),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'SIMULATED MEDIA REACTION (PRESS ROOM BRIEFING)',
                      style: TextStyle(
                        color: Color(0xFF60A5FA),
                        fontSize: 10,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 0.8,
                      ),
                    ),
                    Text(
                      '3 ACCREDITED MEDIA QUESTIONS · $answeredCount/3 ANSWERED',
                      style: const TextStyle(
                        color: GtexMatchVisualTokens.textSecondary,
                        fontSize: 9.5,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
              if (answeredCount == questions.length)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    color: const Color(0x3300E87A),
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(color: const Color(0xFF00E87A)),
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.check_circle_rounded, size: 12, color: Color(0xFF00E87A)),
                      SizedBox(width: 4),
                      Text(
                        'PRESS CONCLUDED',
                        style: TextStyle(
                          color: Color(0xFF00E87A),
                          fontSize: 9,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ),
          const SizedBox(height: 14),

          // Questions List
          for (int qIdx = 0; qIdx < questions.length; qIdx++) ...[
            _buildQuestionTile(questions[qIdx], qIdx),
            if (qIdx < questions.length - 1) const SizedBox(height: 12),
          ],
        ],
      ),
    );
  }

  Widget _buildQuestionTile(_PressQuestionData q, int qIdx) {
    final int? selectedOpt = _selectedAnswers[qIdx];

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: selectedOpt != null
              ? const Color(0x6600E87A)
              : Colors.white12,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Outlet & Journalist
          Row(
            children: [
              Container(
                width: 6,
                height: 6,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: q.avatarColor,
                ),
              ),
              const SizedBox(width: 6),
              Text(
                q.outlet,
                style: TextStyle(
                  color: q.avatarColor,
                  fontSize: 9,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 0.6,
                ),
              ),
              const Spacer(),
              Text(
                q.journalist,
                style: const TextStyle(
                  color: GtexMatchVisualTokens.textTertiary,
                  fontSize: 9,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),

          // Question Text
          Text(
            q.question,
            style: const TextStyle(
              color: GtexMatchVisualTokens.textPrimary,
              fontSize: 11,
              fontStyle: FontStyle.italic,
              fontWeight: FontWeight.w600,
              height: 1.3,
            ),
          ),
          const SizedBox(height: 8),

          // Response Options
          for (int optIdx = 0; optIdx < q.options.length; optIdx++) ...[
            _buildOptionButton(q.options[optIdx], qIdx, optIdx, selectedOpt == optIdx),
            if (optIdx < q.options.length - 1) const SizedBox(height: 6),
          ],

          // Effect indicator if selected
          if (selectedOpt != null) ...[
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: q.options[selectedOpt].impactColor.withAlpha(30),
                borderRadius: BorderRadius.circular(4),
                border: Border.all(
                  color: q.options[selectedOpt].impactColor,
                  width: 0.8,
                ),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.trending_up_rounded,
                    size: 11,
                    color: q.options[selectedOpt].impactColor,
                  ),
                  const SizedBox(width: 5),
                  Text(
                    q.options[selectedOpt].impactLabel,
                    style: TextStyle(
                      color: q.options[selectedOpt].impactColor,
                      fontSize: 8.5,
                      fontWeight: FontWeight.w900,
                      fontFamily: 'JetBrains Mono',
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildOptionButton(
    _PressOptionData opt,
    int qIdx,
    int optIdx,
    bool isSelected,
  ) {
    return InkWell(
      onTap: () => setState(() {
        _selectedAnswers[qIdx] = optIdx;
      }),
      borderRadius: BorderRadius.circular(6),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
        decoration: BoxDecoration(
          color: isSelected ? const Color(0x3300E87A) : const Color(0x661E293B),
          borderRadius: BorderRadius.circular(6),
          border: Border.all(
            color: isSelected ? const Color(0xFF00E87A) : Colors.white10,
            width: isSelected ? 1.2 : 0.8,
          ),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(
              isSelected
                  ? Icons.radio_button_checked_rounded
                  : Icons.radio_button_off_rounded,
              size: 13,
              color: isSelected ? const Color(0xFF00E87A) : Colors.white38,
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                opt.text,
                style: TextStyle(
                  color: isSelected ? Colors.white : GtexMatchVisualTokens.textSecondary,
                  fontSize: 10,
                  fontWeight: isSelected ? FontWeight.w700 : FontWeight.w500,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PostMatchSettlementCard extends StatefulWidget {
  const _PostMatchSettlementCard({required this.match});

  final GtexLiveMatchState match;

  @override
  State<_PostMatchSettlementCard> createState() => _PostMatchSettlementCardState();
}

class _PostMatchSettlementCardState extends State<_PostMatchSettlementCard> {
  bool _claimed = false;

  @override
  Widget build(BuildContext context) {
    final int homeScore = widget.match.home.score;
    final int awayScore = widget.match.away.score;
    final bool won = homeScore > awayScore;
    final bool drew = homeScore == awayScore;

    final int resultXp = won ? 200 : (drew ? 100 : 50);
    const int participationXp = 250;
    const int tacticalXp = 100;
    final int totalXp = participationXp + resultXp + tacticalXp;

    final int tokenReward = won ? 25 : (drew ? 15 : 10);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF1E293B), Color(0xFF0F172A)],
        ),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: _claimed ? const Color(0xFF00E87A) : const Color(0xFFFFB800),
          width: 1.2,
        ),
        boxShadow: const [
          BoxShadow(
            color: Color(0x22FFB800),
            blurRadius: 12,
            offset: Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(6),
                decoration: const BoxDecoration(
                  color: Color(0x33FFB800),
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.military_tech_rounded,
                  size: 16,
                  color: Color(0xFFFFB800),
                ),
              ),
              const SizedBox(width: 8),
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'MATCH REWARD SETTLEMENT',
                      style: TextStyle(
                        color: Color(0xFFFFB800),
                        fontSize: 10,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 0.8,
                      ),
                    ),
                    Text(
                      'MANAGER LEVEL 14 · SEASON TACTICAL CYCLE',
                      style: TextStyle(
                        color: GtexMatchVisualTokens.textSecondary,
                        fontSize: 9.5,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: const Color(0x33FFB800),
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: const Color(0xFFFFB800)),
                ),
                child: Text(
                  '+$totalXp XP',
                  style: const TextStyle(
                    color: Color(0xFFFFB800),
                    fontSize: 11,
                    fontWeight: FontWeight.w900,
                    fontFamily: 'JetBrains Mono',
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Settlement Breakdown Rows
          _buildSettlementRow(
            icon: Icons.sports_soccer_rounded,
            label: 'Matchday Completion',
            value: '+$participationXp XP',
            color: Colors.white70,
          ),
          const SizedBox(height: 6),
          _buildSettlementRow(
            icon: Icons.emoji_events_rounded,
            label: won ? 'Victory Bounty' : (drew ? 'Draw Result Share' : 'Match Resilience'),
            value: '+$resultXp XP',
            color: won ? const Color(0xFF00E87A) : (drew ? const Color(0xFFFFB800) : Colors.white60),
          ),
          const SizedBox(height: 6),
          _buildSettlementRow(
            icon: Icons.tune_rounded,
            label: 'Tactical Alignment Masterclass',
            value: '+$tacticalXp XP',
            color: const Color(0xFF60A5FA),
          ),
          const SizedBox(height: 6),
          _buildSettlementRow(
            icon: Icons.monetization_on_rounded,
            label: 'GTEX Manager Token Pool',
            value: '+$tokenReward \$TALENT',
            color: const Color(0xFFFFB800),
            isBold: true,
          ),
          const SizedBox(height: 14),

          // Level Progression Bar
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Row(
                children: [
                  Text(
                    'LEVEL 14 PROGRESSION',
                    style: TextStyle(
                      color: GtexMatchVisualTokens.textTertiary,
                      fontSize: 8.5,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 0.5,
                    ),
                  ),
                  Spacer(),
                  Text(
                    '8,450 / 10,000 XP (84.5%)',
                    style: TextStyle(
                      color: Color(0xFFFFB800),
                      fontSize: 8.5,
                      fontWeight: FontWeight.w800,
                      fontFamily: 'JetBrains Mono',
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 5),
              ClipRRect(
                borderRadius: BorderRadius.circular(3),
                child: LinearProgressIndicator(
                  value: _claimed ? 0.90 : 0.845,
                  minHeight: 6,
                  backgroundColor: const Color(0xFF334155),
                  valueColor: AlwaysStoppedAnimation<Color>(
                    _claimed ? const Color(0xFF00E87A) : const Color(0xFFFFB800),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),

          // Claim Button
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _claimed
                  ? null
                  : () {
                      setState(() => _claimed = true);
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(
                            'Settled: +$totalXp XP and +$tokenReward \$TALENT credited to Manager Account',
                          ),
                          backgroundColor: const Color(0xFF0F172A),
                          behavior: SnackBarBehavior.floating,
                        ),
                      );
                    },
              style: ElevatedButton.styleFrom(
                backgroundColor: _claimed
                    ? const Color(0x3300E87A)
                    : const Color(0xFFFFB800),
                foregroundColor: _claimed
                    ? const Color(0xFF00E87A)
                    : const Color(0xFF0F172A),
                padding: const EdgeInsets.symmetric(vertical: 12),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(6),
                  side: _claimed
                      ? const BorderSide(color: Color(0xFF00E87A))
                      : BorderSide.none,
                ),
              ),
              icon: Icon(
                _claimed ? Icons.check_circle_rounded : Icons.lock_open_rounded,
                size: 16,
              ),
              label: Text(
                _claimed
                    ? 'REWARDS DEPOSITED TO WALLET'
                    : 'CLAIM +$totalXp XP & +$tokenReward \$TALENT',
                style: const TextStyle(
                  fontSize: 10.5,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 0.6,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSettlementRow({
    required IconData icon,
    required String label,
    required String value,
    required Color color,
    bool isBold = false,
  }) {
    return Row(
      children: [
        Icon(icon, size: 12, color: color),
        const SizedBox(width: 7),
        Text(
          label,
          style: TextStyle(
            color: GtexMatchVisualTokens.textSecondary,
            fontSize: 10,
            fontWeight: isBold ? FontWeight.w700 : FontWeight.w500,
          ),
        ),
        const Spacer(),
        Text(
          value,
          style: TextStyle(
            color: color,
            fontSize: 10.5,
            fontWeight: FontWeight.w900,
            fontFamily: 'JetBrains Mono',
          ),
        ),
      ],
    );
  }
}

class _MatchTeamReview extends StatelessWidget {
  const _MatchTeamReview({
    required this.team,
    required this.alignEnd,
  });

  final GtexMatchTeam team;
  final bool alignEnd;

  @override
  Widget build(BuildContext context) {
    final Color accent = _tryColor(team.primaryColorHex);
    final CrossAxisAlignment alignment =
        alignEnd ? CrossAxisAlignment.end : CrossAxisAlignment.start;
    return Container(
      padding: const EdgeInsets.all(11),
      decoration: BoxDecoration(
        color: GtexMatchVisualTokens.surfaceRaised,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: accent.withValues(alpha: .40)),
      ),
      child: Column(
        crossAxisAlignment: alignment,
        children: <Widget>[
          Text(
            team.name,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            textAlign: alignEnd ? TextAlign.right : TextAlign.left,
            style: const TextStyle(
              color: GtexMatchVisualTokens.textPrimary,
              fontWeight: FontWeight.w900,
              fontSize: 13,
            ),
          ),
          const SizedBox(height: 5),
          Text(
            team.formation,
            style: TextStyle(
              color: accent,
              fontSize: 19,
              fontWeight: FontWeight.w900,
            ),
          ),
          if (team.managerName?.trim().isNotEmpty == true) ...<Widget>[
            const SizedBox(height: 4),
            Text(
              team.managerName!.trim(),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              textAlign: alignEnd ? TextAlign.right : TextAlign.left,
              style: const TextStyle(
                color: GtexMatchVisualTokens.textSecondary,
                fontSize: 10,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
          if (team.recentFormPercent != null) ...<Widget>[
            const SizedBox(height: 4),
            Text(
              'Form ${team.recentFormPercent}%',
              style: const TextStyle(
                color: GtexMatchVisualTokens.textSecondary,
                fontSize: 10,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Color _tryColor(String? raw) {
    if (raw == null) return GtexMatchVisualTokens.live;
    final String value = raw.trim().replaceFirst('#', '');
    if (value.length != 6) return GtexMatchVisualTokens.live;
    final int? parsed = int.tryParse(value, radix: 16);
    return parsed == null ? GtexMatchVisualTokens.live : Color(0xFF000000 | parsed);
  }
}
