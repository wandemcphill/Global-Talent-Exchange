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
            playerName: widget.match.home.players.isNotEmpty
                ? widget.match.home.players.first.name
                : 'Top Performer',
            teamName: widget.match.home.name,
            shirtNumber: widget.match.home.players.isNotEmpty
                ? widget.match.home.players.first.shirtNumber
                : 10,
            rating: 8.8,
            goals: widget.match.home.score,
            assists: 1,
            keyPasses: 4,
            passAcc: 91,
            summary:
                'Decisive match-winning performance, controlling midfield tempo and driving attacking transitions.',
          ),
          shotMap: const [
            GtexShotMapEntry(minute: 14, isHome: true, x: 0.82, y: 0.48, xg: 0.72, outcome: 'goal', playerName: 'Home Scorer'),
            GtexShotMapEntry(minute: 42, isHome: true, x: 0.86, y: 0.52, xg: 0.65, outcome: 'goal', playerName: 'Home Scorer'),
            GtexShotMapEntry(minute: 58, isHome: true, x: 0.78, y: 0.38, xg: 0.28, outcome: 'saved', playerName: 'Home Winger'),
            GtexShotMapEntry(minute: 71, isHome: false, x: 0.22, y: 0.55, xg: 0.22, outcome: 'missed', playerName: 'Away Striker'),
          ],
          momentum: const [
            GtexMomentumPoint(minute: 15, value: 70),
            GtexMomentumPoint(minute: 30, value: -40),
            GtexMomentumPoint(minute: 45, value: 65),
            GtexMomentumPoint(minute: 60, value: 30),
            GtexMomentumPoint(minute: 75, value: -20),
            GtexMomentumPoint(minute: 90, value: 45),
          ],
          ratings: [
            for (final p in widget.match.home.players.take(11))
              GtexPlayerRatingItem(
                playerId: p.id,
                name: p.name,
                shirtNumber: p.shirtNumber,
                position: p.position,
                rating: p.rating > 0 ? p.rating : 7.4,
                isHome: true,
                badges: const ['Solid Shape 🛡️', '88% Pass 📊'],
              ),
            for (final p in widget.match.away.players.take(11))
              GtexPlayerRatingItem(
                playerId: p.id,
                name: p.name,
                shirtNumber: p.shirtNumber,
                position: p.position,
                rating: p.rating > 0 ? p.rating : 7.1,
                isHome: false,
                badges: const ['High Workrate ⚡'],
              ),
          ],
          shareSummary:
              '🏁 FULL TIME: ${widget.match.home.name} ${widget.match.home.score} - ${widget.match.away.score} ${widget.match.away.name}\n'
              'Verified on Global Talent Exchange ⚽',
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
              // 1. Player of the Match (MOTM) Spotlight
              _MotmCelebrationCard(motm: post.motm),
              const SizedBox(height: 14),

              // 2. Interactive xG Shot Map
              _XgShotMapCard(
                shots: post.shotMap,
                homeTeam: widget.match.home,
                awayTeam: widget.match.away,
              ),
              const SizedBox(height: 14),

              // 3. Match Momentum Flow Chart
              _MatchMomentumCard(
                momentum: post.momentum,
                homeTeam: widget.match.home,
                awayTeam: widget.match.away,
              ),
              const SizedBox(height: 14),

              // 4. Player Performance Ratings Strip
              _PlayerRatingsSection(
                ratings: post.ratings,
                homeTeam: widget.match.home,
                awayTeam: widget.match.away,
                showHome: _showHomeRatings,
                onToggleTeam: (home) => setState(() {
                  _showHomeRatings = home;
                }),
              ),
              const SizedBox(height: 14),

              // 5. Match Statistics Breakdown
              _MatchPerformanceSummary(match: widget.match),
              const SizedBox(height: 14),

              // 6. Goal Replays
              if (widget.onReplayGoal != null &&
                  widget.match.timeline.any((e) => e.type == GtexPitchEventType.goal)) ...[
                _GoalReplaysList(
                  match: widget.match,
                  onReplayGoal: widget.onReplayGoal!,
                ),
                const SizedBox(height: 14),
              ],

              // 7. Owner Decision Loop Actions
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
                  '${motm.rating.toStringAsFixed(1)} RATING',
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
                _MotmMetricItem(label: 'ASSISTS', value: '${motm.assists}'),
                _MotmMetricItem(label: 'KEY PASSES', value: '${motm.keyPasses}'),
                _MotmMetricItem(label: 'PASS ACC', value: '${motm.passAcc}%'),
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
          'Performance in this fixture has updated published player valuations and club token progression. Review your portfolio position or explore new talent on the market.',
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
                onPressed: onOpenPortfolio,
                icon: const Icon(Icons.account_balance_wallet_outlined, size: 15),
                label: const Text('Review Portfolio', style: TextStyle(fontSize: 11)),
              ),
            if (onOpenMarket != null)
              OutlinedButton.icon(
                onPressed: onOpenMarket,
                icon: const Icon(Icons.storefront_outlined, size: 15),
                label: const Text('Explore Transfer Hub', style: TextStyle(fontSize: 11)),
              ),
            if (onOpenNewsroomReport != null)
              OutlinedButton.icon(
                onPressed: onOpenNewsroomReport,
                icon: const Icon(Icons.article_outlined, size: 15),
                label: const Text('Newsroom Report', style: TextStyle(fontSize: 11)),
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
            home: '${stats.homePossession}%',
            away: '${stats.awayPossession}%',
            homeValue: stats.homePossession.toDouble(),
            awayValue: stats.awayPossession.toDouble(),
          ),
          _MatchStatRow(
            label: 'Shots',
            home: '${stats.homeShots}',
            away: '${stats.awayShots}',
            homeValue: stats.homeShots.toDouble(),
            awayValue: stats.awayShots.toDouble(),
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
            home: '${stats.homePassAccuracy}%',
            away: '${stats.awayPassAccuracy}%',
            homeValue: stats.homePassAccuracy.toDouble(),
            awayValue: stats.awayPassAccuracy.toDouble(),
          ),
          _MatchStatRow(
            label: 'Expected goals',
            home: stats.homeExpectedGoals.toStringAsFixed(2),
            away: stats.awayExpectedGoals.toStringAsFixed(2),
            homeValue: stats.homeExpectedGoals,
            awayValue: stats.awayExpectedGoals,
          ),
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
                    label.toUpperCase(),
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
