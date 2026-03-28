import 'dart:math' as math;
import 'dart:ui';

import 'package:flutter/material.dart';

import '../../../core/constants/app_spacing.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/theme/app_motion.dart';
import '../../../core/utils/app_formatters.dart';
import '../../../shared/models/live_match.dart';

class BroadcastTickerEvent {
  const BroadcastTickerEvent({
    required this.minute,
    required this.type,
    required this.team,
    required this.player,
    required this.commentary,
    required this.dramatic,
  });

  final int minute;
  final String type;
  final String team;
  final String player;
  final String commentary;
  final bool dramatic;
}

class BroadcastMoment {
  const BroadcastMoment({
    required this.minute,
    required this.homeScore,
    required this.awayScore,
    required this.headline,
    required this.commentary,
    required this.cameraMode,
    required this.eventLabel,
    required this.possessionHome,
    required this.shotsHome,
    required this.shotsAway,
    required this.passAccuracyHome,
    required this.passAccuracyAway,
    required this.xThreatHome,
    required this.xThreatAway,
    required this.isBigMoment,
    required this.control,
    required this.depth,
    required this.homeWinProbability,
    required this.drawWinProbability,
    required this.awayWinProbability,
    required this.homeOdds,
    required this.drawOdds,
    required this.awayOdds,
    required this.homeShift,
    required this.drawShift,
    required this.awayShift,
    required this.marketLabel,
    required this.playerFocus,
    required this.pushTitle,
    required this.pushBody,
    required this.eventTape,
  });

  final int minute;
  final int homeScore;
  final int awayScore;
  final String headline;
  final String commentary;
  final String cameraMode;
  final String eventLabel;
  final int possessionHome;
  final int shotsHome;
  final int shotsAway;
  final int passAccuracyHome;
  final int passAccuracyAway;
  final double xThreatHome;
  final double xThreatAway;
  final bool isBigMoment;
  final double control;
  final double depth;
  final double homeWinProbability;
  final double drawWinProbability;
  final double awayWinProbability;
  final double homeOdds;
  final double drawOdds;
  final double awayOdds;
  final double homeShift;
  final double drawShift;
  final double awayShift;
  final String marketLabel;
  final String playerFocus;
  final String? pushTitle;
  final String? pushBody;
  final List<BroadcastTickerEvent> eventTape;
}

class _FrameSeed {
  const _FrameSeed({
    required this.minute,
    required this.homeScore,
    required this.awayScore,
    required this.headline,
    required this.commentary,
    required this.cameraMode,
    required this.eventLabel,
    required this.possessionHome,
    required this.shotsHome,
    required this.shotsAway,
    required this.passAccuracyHome,
    required this.passAccuracyAway,
    required this.xThreatHome,
    required this.xThreatAway,
    required this.isBigMoment,
    required this.control,
    required this.depth,
    required this.marketLabel,
    required this.playerFocus,
    required this.pushTitle,
    required this.pushBody,
  });

  final int minute;
  final int homeScore;
  final int awayScore;
  final String headline;
  final String commentary;
  final String cameraMode;
  final String eventLabel;
  final int possessionHome;
  final int shotsHome;
  final int shotsAway;
  final int passAccuracyHome;
  final int passAccuracyAway;
  final double xThreatHome;
  final double xThreatAway;
  final bool isBigMoment;
  final double control;
  final double depth;
  final String marketLabel;
  final String playerFocus;
  final String? pushTitle;
  final String? pushBody;
}

class _ProbabilityTriple {
  const _ProbabilityTriple({
    required this.home,
    required this.draw,
    required this.away,
  });

  final double home;
  final double draw;
  final double away;
}

class _OddsTriple {
  const _OddsTriple({
    required this.home,
    required this.draw,
    required this.away,
  });

  final double home;
  final double draw;
  final double away;
}

List<BroadcastMoment> buildBroadcastMoments(LiveMatch match) {
  final int earlierHomeScore = math.max(match.homeScore - 1, 0);
  final int earlierAwayScore = match.awayScore;
  final bool homeDominant = match.momentum >= 0.5;
  final int buildMinute = math.max(match.minute - 4, 1);
  final int liveMinute = match.minute;
  final int pressMinute = match.minute + 2;
  final int flashMinute = match.minute + 5;
  final int lateHomeScore =
      homeDominant ? match.homeScore + 1 : match.homeScore;
  final int lateAwayScore =
      homeDominant ? match.awayScore : match.awayScore + 1;

  final List<BroadcastTickerEvent> tape = <BroadcastTickerEvent>[
    BroadcastTickerEvent(
      minute: buildMinute,
      type: 'BUILD',
      team: match.homeClub,
      player: match.homeStarPlayer,
      commentary:
          '${match.homeStarPlayer} drops off the front line and starts the overload through the right half-space.',
      dramatic: false,
    ),
    BroadcastTickerEvent(
      minute: liveMinute,
      type: 'LIVE',
      team: homeDominant ? match.homeClub : match.awayClub,
      player: homeDominant ? match.homeStarPlayer : match.awayStarPlayer,
      commentary:
          homeDominant
              ? '${match.homeStarPlayer} keeps pinning the back line, and every touch nudges the win % upward.'
              : '${match.awayStarPlayer} absorbs the pressure and threatens the release ball behind the press.',
      dramatic: false,
    ),
    BroadcastTickerEvent(
      minute: pressMinute,
      type: 'PRESS',
      team: homeDominant ? match.homeClub : match.awayClub,
      player: homeDominant ? match.homeStarPlayer : match.awayStarPlayer,
      commentary:
          homeDominant
              ? '${match.homeStarPlayer} forces another recovery and the live line starts to run hot.'
              : '${match.awayStarPlayer} breaks the trap, stretching the field and spiking the tension again.',
      dramatic: false,
    ),
    BroadcastTickerEvent(
      minute: flashMinute,
      type: 'FLASH',
      team: homeDominant ? match.homeClub : match.awayClub,
      player: homeDominant ? match.homeStarPlayer : match.awayStarPlayer,
      commentary:
          homeDominant
              ? '${match.homeStarPlayer} tears open the lane and lands the decisive finish.'
              : '${match.awayStarPlayer} detonates the counter and flips the broadcast pulse in one touch.',
      dramatic: true,
    ),
  ];

  final List<_FrameSeed> seeds = <_FrameSeed>[
    _FrameSeed(
      minute: buildMinute,
      homeScore: earlierHomeScore,
      awayScore: earlierAwayScore,
      headline:
          '${match.homeClub} lean into a higher press to destabilize the block.',
      commentary:
          '${match.homeStarPlayer} keeps showing between the lines while ${match.awayClub} compress the center and wait for a mistake.',
      cameraMode: 'Sky Cam',
      eventLabel: 'BUILD',
      possessionHome: 54,
      shotsHome: math.max(match.homeScore + 2, 3),
      shotsAway: math.max(match.awayScore + 1, 2),
      passAccuracyHome: 87,
      passAccuracyAway: 82,
      xThreatHome: 1.4,
      xThreatAway: 0.9,
      isBigMoment: false,
      control: 0.56,
      depth: 0.38,
      marketLabel: 'Range Build',
      playerFocus: match.homeStarPlayer,
      pushTitle: null,
      pushBody: null,
    ),
    _FrameSeed(
      minute: liveMinute,
      homeScore: match.homeScore,
      awayScore: match.awayScore,
      headline: match.headline,
      commentary:
          '${match.homeClub} squeeze the half-space, ${match.awayStarPlayer} keeps glancing over the shoulder, and the crowd volume rises with every forward touch.',
      cameraMode: 'Broadcast',
      eventLabel: 'LIVE',
      possessionHome: (52 + (match.momentum * 20)).round().clamp(40, 69),
      shotsHome: match.homeScore + 5,
      shotsAway: match.awayScore + 3,
      passAccuracyHome: 88,
      passAccuracyAway: 81,
      xThreatHome: 1.8,
      xThreatAway: 1.1,
      isBigMoment: false,
      control: match.momentum.clamp(0.35, 0.85),
      depth: 0.48,
      marketLabel: homeDominant ? 'Home Surge' : 'Away Resistance',
      playerFocus: homeDominant ? match.homeStarPlayer : match.awayStarPlayer,
      pushTitle: null,
      pushBody: null,
    ),
    _FrameSeed(
      minute: pressMinute,
      homeScore: match.homeScore,
      awayScore: match.awayScore,
      headline:
          '${match.awayClub} survive the surge, but territory still belongs to ${match.homeClub}.',
      commentary:
          '${match.awayClub} clear long, yet ${match.homeClub} recover quickly and keep the camera pinned in the attacking third around ${match.homeStarPlayer}.',
      cameraMode: 'Tactical',
      eventLabel: 'PRESS',
      possessionHome: (54 + (match.momentum * 18)).round().clamp(42, 70),
      shotsHome: match.homeScore + 6,
      shotsAway: match.awayScore + 3,
      passAccuracyHome: 89,
      passAccuracyAway: 80,
      xThreatHome: 2.0,
      xThreatAway: 1.0,
      isBigMoment: false,
      control: (match.momentum + 0.08).clamp(0.35, 0.92),
      depth: 0.56,
      marketLabel: homeDominant ? 'Pressure Spike' : 'Counter Thread',
      playerFocus: homeDominant ? match.homeStarPlayer : match.awayStarPlayer,
      pushTitle: null,
      pushBody: null,
    ),
    _FrameSeed(
      minute: flashMinute,
      homeScore: lateHomeScore,
      awayScore: lateAwayScore,
      headline:
          homeDominant
              ? '${match.homeClub} find the extra touch and break the shape open.'
              : '${match.awayClub} counter with precision and stun the momentum swing.',
      commentary:
          homeDominant
              ? '${match.homeStarPlayer} bends away from the marker, meets the diagonal, and buries the finish inside the far post.'
              : '${match.awayStarPlayer} explodes through the gap, and the scoreboard flips before the press can recover its spacing.',
      cameraMode: 'Goal Line',
      eventLabel: 'FLASH',
      possessionHome: homeDominant ? 61 : 47,
      shotsHome: homeDominant ? match.homeScore + 8 : match.homeScore + 6,
      shotsAway: homeDominant ? match.awayScore + 3 : match.awayScore + 5,
      passAccuracyHome: homeDominant ? 90 : 84,
      passAccuracyAway: homeDominant ? 79 : 86,
      xThreatHome: homeDominant ? 2.5 : 1.5,
      xThreatAway: homeDominant ? 1.0 : 2.1,
      isBigMoment: true,
      control: homeDominant ? 0.78 : 0.34,
      depth: homeDominant ? 0.68 : 0.44,
      marketLabel: homeDominant ? 'Breakout' : 'Counter Shock',
      playerFocus: homeDominant ? match.homeStarPlayer : match.awayStarPlayer,
      pushTitle: 'Push Signal',
      pushBody:
          homeDominant
              ? '${match.homeStarPlayer} has just slammed the win % hard toward ${match.homeClub}.'
              : '${match.awayStarPlayer} has flipped the live pulse and shoved the win % toward ${match.awayClub}.',
    ),
  ];

  final List<BroadcastMoment> moments = <BroadcastMoment>[];
  _ProbabilityTriple? previousProbability;

  for (int index = 0; index < seeds.length; index += 1) {
    final _FrameSeed seed = seeds[index];
    final _ProbabilityTriple probability = _buildProbabilityTriple(
      minute: seed.minute,
      homeScore: seed.homeScore,
      awayScore: seed.awayScore,
      control: seed.control,
      isBigMoment: seed.isBigMoment,
    );
    final _OddsTriple odds = _buildOddsTriple(probability);
    final _ProbabilityTriple baseline = previousProbability ?? probability;

    moments.add(
      BroadcastMoment(
        minute: seed.minute,
        homeScore: seed.homeScore,
        awayScore: seed.awayScore,
        headline: seed.headline,
        commentary: seed.commentary,
        cameraMode: seed.cameraMode,
        eventLabel: seed.eventLabel,
        possessionHome: seed.possessionHome,
        shotsHome: seed.shotsHome,
        shotsAway: seed.shotsAway,
        passAccuracyHome: seed.passAccuracyHome,
        passAccuracyAway: seed.passAccuracyAway,
        xThreatHome: seed.xThreatHome,
        xThreatAway: seed.xThreatAway,
        isBigMoment: seed.isBigMoment,
        control: seed.control,
        depth: seed.depth,
        homeWinProbability: probability.home,
        drawWinProbability: probability.draw,
        awayWinProbability: probability.away,
        homeOdds: odds.home,
        drawOdds: odds.draw,
        awayOdds: odds.away,
        homeShift: index == 0 ? 0 : probability.home - baseline.home,
        drawShift: index == 0 ? 0 : probability.draw - baseline.draw,
        awayShift: index == 0 ? 0 : probability.away - baseline.away,
        marketLabel: seed.marketLabel,
        playerFocus: seed.playerFocus,
        pushTitle: seed.pushTitle,
        pushBody: seed.pushBody,
        eventTape: tape
            .take(index + 1)
            .toList()
            .reversed
            .toList(growable: false),
      ),
    );

    previousProbability = probability;
  }

  return moments;
}

_ProbabilityTriple _buildProbabilityTriple({
  required int minute,
  required int homeScore,
  required int awayScore,
  required double control,
  required bool isBigMoment,
}) {
  final double timeFactor = (minute.clamp(1, 95) / 95).toDouble();
  final double scoreSwing = (homeScore - awayScore).toDouble();
  final double controlTilt = (control - 0.5) * 2.25;
  final double swingBoost = isBigMoment ? (controlTilt * 0.4) : 0;
  final double scoreWeight = scoreSwing * (1.35 + (timeFactor * 1.05));

  final double homeSignal = scoreWeight + controlTilt + swingBoost;
  final double awaySignal = (-scoreWeight) - controlTilt - swingBoost;
  final double drawSignal =
      0.95 -
      (scoreSwing.abs() * 1.05) -
      (timeFactor * 0.45) -
      (controlTilt.abs() * 0.35);

  final double maxSignal = math.max(
    homeSignal,
    math.max(drawSignal, awaySignal),
  );
  final double homeWeight = math.exp(homeSignal - maxSignal);
  final double drawWeight = math.exp(drawSignal - maxSignal);
  final double awayWeight = math.exp(awaySignal - maxSignal);
  final double total = homeWeight + drawWeight + awayWeight;

  return _ProbabilityTriple(
    home: homeWeight / total,
    draw: drawWeight / total,
    away: awayWeight / total,
  );
}

_OddsTriple _buildOddsTriple(_ProbabilityTriple probability) {
  return _OddsTriple(
    home: _decimalLine(probability.home),
    draw: _decimalLine(probability.draw),
    away: _decimalLine(probability.away),
  );
}

double _decimalLine(double probability) {
  final double safeProbability = probability.clamp(0.08, 0.86);
  return double.parse((1 / safeProbability).toStringAsFixed(2));
}

class BroadcastPitchPlaceholder extends StatelessWidget {
  const BroadcastPitchPlaceholder({
    super.key,
    required this.moment,
    required this.wide,
  });

  final BroadcastMoment moment;
  final bool wide;

  @override
  Widget build(BuildContext context) {
    final double ballX = lerpDouble(-0.52, 0.58, moment.control)!;
    final double ballY = lerpDouble(0.18, 0.72, moment.depth)!;

    return DecoratedBox(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: <Color>[
            Color(0xFF09111D),
            Color(0xFF0E1A2A),
            Color(0xFF060A12),
          ],
        ),
      ),
      child: Stack(
        fit: StackFit.expand,
        children: <Widget>[
          Positioned(
            top: -120,
            left: -80,
            child: _GlowOrb(
              size: 320,
              color: AppColors.primary.withValues(alpha: 0.14),
            ),
          ),
          Positioned(
            right: -120,
            top: -60,
            child: _GlowOrb(
              size: 280,
              color: AppColors.gold.withValues(alpha: 0.12),
            ),
          ),
          Positioned.fill(
            child: CustomPaint(painter: _PitchPainter(moment: moment)),
          ),
          ..._teamMarkers(
            color: AppColors.primary,
            alignments: const <Alignment>[
              Alignment(-0.36, 0.24),
              Alignment(-0.18, 0.10),
              Alignment(-0.06, 0.36),
              Alignment(-0.44, 0.56),
              Alignment(0.04, 0.56),
            ],
            controlShift: moment.control,
          ),
          ..._teamMarkers(
            color: AppColors.gold,
            alignments: const <Alignment>[
              Alignment(0.28, 0.08),
              Alignment(0.18, 0.30),
              Alignment(0.34, 0.44),
              Alignment(0.10, 0.56),
              Alignment(0.44, 0.62),
            ],
            controlShift: 1 - moment.control,
          ),
          AnimatedAlign(
            duration: const Duration(milliseconds: 520),
            curve: Curves.easeOutCubic,
            alignment: Alignment(ballX, ballY),
            child: Container(
              width: 16,
              height: 16,
              decoration: BoxDecoration(
                color: Colors.white,
                shape: BoxShape.circle,
                boxShadow: <BoxShadow>[
                  BoxShadow(
                    color: Colors.white.withValues(alpha: 0.5),
                    blurRadius: 14,
                    spreadRadius: 2,
                  ),
                ],
              ),
            ),
          ),
          Positioned(
            left: spacingLG,
            bottom: spacingLG * 3.5,
            child: Container(
              padding: const EdgeInsets.symmetric(
                horizontal: spacingMD,
                vertical: spacingSM,
              ),
              decoration: BoxDecoration(
                color: AppColors.background.withValues(alpha: 0.72),
                borderRadius: BorderRadius.circular(999),
                border: Border.all(color: AppColors.divider),
              ),
              child: Text(
                '${moment.marketLabel}  |  ${moment.playerFocus}',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: AppColors.textPrimary,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ),
          Positioned(
            right: spacingLG,
            top: wide ? 112 : 96,
            child: _CameraBadge(cameraMode: moment.cameraMode),
          ),
        ],
      ),
    );
  }

  List<Widget> _teamMarkers({
    required Color color,
    required List<Alignment> alignments,
    required double controlShift,
  }) {
    return alignments
        .map(
          (Alignment alignment) => AnimatedAlign(
            duration: const Duration(milliseconds: 520),
            curve: Curves.easeOutCubic,
            alignment: Alignment(
              alignment.x + ((controlShift - 0.5) * 0.18),
              alignment.y,
            ),
            child: _PlayerMarker(color: color),
          ),
        )
        .toList();
  }
}

class ScoreOverlay extends StatelessWidget {
  const ScoreOverlay({
    super.key,
    required this.match,
    required this.moment,
    required this.liveCount,
    required this.feedLatencyMs,
    required this.liveChannel,
    required this.connected,
    required this.wide,
  });

  final LiveMatch match;
  final BroadcastMoment moment;
  final int liveCount;
  final int feedLatencyMs;
  final String liveChannel;
  final bool connected;
  final bool wide;

  @override
  Widget build(BuildContext context) {
    return Positioned(
      top: spacingMD,
      left: spacingMD,
      right: spacingMD,
      child: Align(
        alignment: Alignment.topCenter,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1120),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(24),
            child: BackdropFilter(
              filter: ImageFilter.blur(sigmaX: 14, sigmaY: 14),
              child: Container(
                padding: const EdgeInsets.all(spacingMD),
                decoration: BoxDecoration(
                  color: AppColors.background.withValues(alpha: 0.72),
                  border: Border.all(color: AppColors.divider),
                  borderRadius: BorderRadius.circular(24),
                ),
                child:
                    wide
                        ? Row(
                          children: <Widget>[
                            Expanded(child: _liveBug(context)),
                            Expanded(flex: 2, child: _scoreCore(context)),
                            Expanded(
                              child: Align(
                                alignment: Alignment.centerRight,
                                child: _detailColumn(context),
                              ),
                            ),
                          ],
                        )
                        : Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            _liveBug(context),
                            const SizedBox(height: spacingMD),
                            _scoreCore(context),
                            const SizedBox(height: spacingMD),
                            _detailColumn(context),
                          ],
                        ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _liveBug(BuildContext context) {
    return Wrap(
      spacing: spacingSM,
      runSpacing: spacingSM,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: <Widget>[
        Container(
          padding: const EdgeInsets.symmetric(
            horizontal: spacingSM,
            vertical: spacingXS,
          ),
          decoration: BoxDecoration(
            color: AppColors.danger.withValues(alpha: 0.18),
            borderRadius: BorderRadius.circular(999),
            border: Border.all(color: AppColors.danger.withValues(alpha: 0.5)),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Container(
                width: 8,
                height: 8,
                decoration: const BoxDecoration(
                  color: AppColors.danger,
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: spacingXS),
              Text(
                'LIVE',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: AppColors.textPrimary,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
        ),
        _TopChip(label: 'Venue', value: match.venue),
        _TopChip(label: 'Windows', value: '$liveCount'),
        _TopChip(label: 'Lag', value: '${feedLatencyMs}ms'),
      ],
    );
  }

  Widget _scoreCore(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: <Widget>[
        Text(
          moment.headline,
          textAlign: TextAlign.center,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          style: Theme.of(
            context,
          ).textTheme.bodyMedium?.copyWith(color: AppColors.textSecondary),
        ),
        const SizedBox(height: spacingMD),
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: <Widget>[
            Expanded(
              child: Text(
                match.homeClub,
                textAlign: TextAlign.end,
                style: Theme.of(
                  context,
                ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700),
              ),
            ),
            const SizedBox(width: spacingMD),
            _AnimatedScore(score: moment.homeScore),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: spacingSM),
              child: Text(
                '-',
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ),
            _AnimatedScore(score: moment.awayScore),
            const SizedBox(width: spacingMD),
            Expanded(
              child: Text(
                match.awayClub,
                style: Theme.of(
                  context,
                ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700),
              ),
            ),
          ],
        ),
        const SizedBox(height: spacingMD),
        _LiveWinStrip(moment: moment, match: match),
      ],
    );
  }

  Widget _detailColumn(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.end,
      children: <Widget>[
        Text(
          moment.eventLabel,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: AppColors.gold,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: spacingXS),
        AnimatedSwitcher(
          duration: const Duration(milliseconds: 320),
          transitionBuilder: (Widget child, Animation<double> animation) {
            return FadeTransition(
              opacity: animation,
              child: SlideTransition(
                position: Tween<Offset>(
                  begin: const Offset(0, 0.2),
                  end: Offset.zero,
                ).animate(animation),
                child: child,
              ),
            );
          },
          child: Text(
            key: ValueKey<int>(moment.minute),
            '${moment.minute}\'',
            style: Theme.of(
              context,
            ).textTheme.headlineMedium?.copyWith(color: AppColors.textPrimary),
          ),
        ),
        const SizedBox(height: spacingXS),
        Text(
          'Crowd ${AppFormatters.compact(match.crowd)}',
          style: Theme.of(context).textTheme.bodySmall,
        ),
        const SizedBox(height: spacingXS),
        Text(
          connected ? moment.marketLabel : 'Reconnecting',
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: AppColors.gold,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: spacingXS),
        Text(
          liveChannel,
          textAlign: TextAlign.end,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: Theme.of(
            context,
          ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
        ),
      ],
    );
  }
}

class PushSignalOverlay extends StatelessWidget {
  const PushSignalOverlay({
    super.key,
    required this.moment,
    required this.wide,
  });

  final BroadcastMoment moment;
  final bool wide;

  @override
  Widget build(BuildContext context) {
    final bool active = moment.pushTitle != null && moment.pushBody != null;

    return Positioned(
      top: wide ? 116 : 164,
      right: spacingMD,
      child: IgnorePointer(
        ignoring: !active,
        child: AnimatedOpacity(
          duration: AppMotion.medium,
          opacity: active ? 1 : 0,
          child: AnimatedSlide(
            duration: AppMotion.medium,
            curve: AppMotion.easeOut,
            offset: active ? Offset.zero : const Offset(0.15, 0),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 320),
              child: Container(
                padding: const EdgeInsets.all(spacingMD),
                decoration: BoxDecoration(
                  color: AppColors.background.withValues(alpha: 0.88),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: AppColors.gold.withValues(alpha: 0.65),
                  ),
                  boxShadow: <BoxShadow>[
                    BoxShadow(
                      color: AppColors.gold.withValues(alpha: 0.18),
                      blurRadius: 24,
                      spreadRadius: 2,
                    ),
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: <Widget>[
                        Container(
                          width: 10,
                          height: 10,
                          decoration: const BoxDecoration(
                            color: AppColors.gold,
                            shape: BoxShape.circle,
                          ),
                        ),
                        const SizedBox(width: spacingXS),
                        Text(
                          moment.pushTitle ?? '',
                          style: Theme.of(
                            context,
                          ).textTheme.bodySmall?.copyWith(
                            color: AppColors.gold,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: spacingSM),
                    Text(
                      moment.pushBody ?? '',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: AppColors.textPrimary,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class CommentaryBar extends StatelessWidget {
  const CommentaryBar({super.key, required this.moment, required this.wide});

  final BroadcastMoment moment;
  final bool wide;

  @override
  Widget build(BuildContext context) {
    return _AnimatedCommentaryBar(moment: moment, wide: wide);
  }
}

class _AnimatedCommentaryBar extends StatefulWidget {
  const _AnimatedCommentaryBar({required this.moment, required this.wide});

  final BroadcastMoment moment;
  final bool wide;

  @override
  State<_AnimatedCommentaryBar> createState() => _AnimatedCommentaryBarState();
}

class _AnimatedCommentaryBarState extends State<_AnimatedCommentaryBar>
    with SingleTickerProviderStateMixin {
  late final AnimationController _typingController = AnimationController(
    vsync: this,
    duration: AppMotion.slow,
  );

  @override
  void initState() {
    super.initState();
    _restartTyping();
  }

  @override
  void didUpdateWidget(covariant _AnimatedCommentaryBar oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.moment.minute != widget.moment.minute ||
        oldWidget.moment.commentary != widget.moment.commentary) {
      _restartTyping();
    }
  }

  @override
  void dispose() {
    _typingController.dispose();
    super.dispose();
  }

  void _restartTyping() {
    _typingController
      ..value = 0
      ..forward();
  }

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.bottomCenter,
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxWidth: widget.wide ? 860 : double.infinity,
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(22),
          child: BackdropFilter(
            filter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
            child: Container(
              padding: const EdgeInsets.symmetric(
                horizontal: spacingMD,
                vertical: spacingSM,
              ),
              decoration: BoxDecoration(
                color: AppColors.background.withValues(alpha: 0.78),
                borderRadius: BorderRadius.circular(22),
                border: Border.all(
                  color:
                      widget.moment.isBigMoment
                          ? AppColors.gold.withValues(alpha: 0.42)
                          : AppColors.divider,
                ),
              ),
              child: SizedBox(
                height: widget.wide ? 82 : 96,
                child: AnimatedBuilder(
                  animation: _typingController,
                  builder: (BuildContext context, Widget? child) {
                    final double progress = _typingController.value;
                    final int visibleCount = (widget.moment.commentary.length *
                            progress)
                        .ceil()
                        .clamp(0, widget.moment.commentary.length);
                    final double shake =
                        widget.moment.isBigMoment
                            ? math.sin(progress * math.pi * 9) *
                                6 *
                                (1 - progress)
                            : 0;
                    final String visibleText = widget.moment.commentary
                        .substring(0, visibleCount);

                    return Opacity(
                      opacity: 0.7 + (progress * 0.3),
                      child: Transform.translate(
                        offset: Offset(shake, 0),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Container(
                              margin: const EdgeInsets.only(top: 6),
                              padding: const EdgeInsets.symmetric(
                                horizontal: spacingSM,
                                vertical: spacingXS,
                              ),
                              decoration: BoxDecoration(
                                color: AppColors.gold.withValues(alpha: 0.16),
                                borderRadius: BorderRadius.circular(999),
                              ),
                              child: Text(
                                '${widget.moment.minute}\'',
                                style: Theme.of(
                                  context,
                                ).textTheme.bodySmall?.copyWith(
                                  color: AppColors.gold,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ),
                            const SizedBox(width: spacingMD),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: <Widget>[
                                  Text(
                                    widget.moment.isBigMoment
                                        ? 'Big Moment'
                                        : 'Commentary',
                                    style: Theme.of(
                                      context,
                                    ).textTheme.bodySmall?.copyWith(
                                      color: AppColors.textSecondary,
                                    ),
                                  ),
                                  const SizedBox(height: spacingXS),
                                  Text(
                                    progress < 1
                                        ? '$visibleText|'
                                        : visibleText,
                                    maxLines: widget.wide ? 2 : 3,
                                    overflow: TextOverflow.ellipsis,
                                    style: Theme.of(
                                      context,
                                    ).textTheme.bodyMedium?.copyWith(
                                      color: AppColors.textPrimary,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class StatsPanel extends StatelessWidget {
  const StatsPanel({
    super.key,
    required this.initialSize,
    required this.minSize,
    required this.maxSize,
    required this.moment,
    required this.liveChannel,
    required this.feedLatencyMs,
    required this.matches,
    required this.wide,
  });

  final double initialSize;
  final double minSize;
  final double maxSize;
  final BroadcastMoment moment;
  final String liveChannel;
  final int feedLatencyMs;
  final List<LiveMatch> matches;
  final bool wide;

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      initialChildSize: initialSize,
      minChildSize: minSize,
      maxChildSize: maxSize,
      snap: true,
      snapSizes: <double>[initialSize, (initialSize + maxSize) / 2, maxSize],
      builder: (BuildContext context, ScrollController scrollController) {
        final List<LiveMatch> otherMatches = matches.skip(1).toList();

        return Align(
          alignment: Alignment.bottomCenter,
          child: ConstrainedBox(
            constraints: BoxConstraints(maxWidth: wide ? 760 : double.infinity),
            child: ClipRRect(
              borderRadius: const BorderRadius.vertical(
                top: Radius.circular(28),
              ),
              child: BackdropFilter(
                filter: ImageFilter.blur(sigmaX: 18, sigmaY: 18),
                child: Container(
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: <Color>[
                        AppColors.card.withValues(alpha: 0.92),
                        AppColors.background.withValues(alpha: 0.96),
                      ],
                    ),
                    border: Border.all(color: AppColors.divider),
                  ),
                  child: CustomScrollView(
                    controller: scrollController,
                    physics: const ClampingScrollPhysics(),
                    slivers: <Widget>[
                      SliverToBoxAdapter(
                        child: SafeArea(
                          top: false,
                          child: Padding(
                            padding: const EdgeInsets.fromLTRB(
                              spacingLG,
                              spacingSM,
                              spacingLG,
                              spacingLG,
                            ),
                            child: LayoutBuilder(
                              builder: (
                                BuildContext context,
                                BoxConstraints constraints,
                              ) {
                                final bool panelWide =
                                    constraints.maxWidth >= 680;

                                return Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: <Widget>[
                                    Center(
                                      child: Container(
                                        key: const Key('match-stats-handle'),
                                        width: 56,
                                        height: 6,
                                        decoration: BoxDecoration(
                                          color: AppColors.divider,
                                          borderRadius: BorderRadius.circular(
                                            999,
                                          ),
                                        ),
                                      ),
                                    ),
                                    const SizedBox(height: spacingMD),
                                    Row(
                                      children: <Widget>[
                                        Expanded(
                                          child: Column(
                                            crossAxisAlignment:
                                                CrossAxisAlignment.start,
                                            children: <Widget>[
                                              Text(
                                                'Match Stats',
                                                style:
                                                    Theme.of(
                                                      context,
                                                    ).textTheme.headlineSmall,
                                              ),
                                              const SizedBox(height: spacingXS),
                                              Text(
                                                'Drag upward for deeper analysis, event tape, and live market pulse.',
                                                style:
                                                    Theme.of(
                                                      context,
                                                    ).textTheme.bodySmall,
                                              ),
                                            ],
                                          ),
                                        ),
                                        Column(
                                          crossAxisAlignment:
                                              CrossAxisAlignment.end,
                                          children: <Widget>[
                                            _TopChip(
                                              label: 'Camera',
                                              value: moment.cameraMode,
                                            ),
                                            const SizedBox(height: spacingSM),
                                            _TopChip(
                                              label: 'Feed',
                                              value: '${feedLatencyMs}ms',
                                            ),
                                          ],
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: spacingLG),
                                    if (panelWide)
                                      Row(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: <Widget>[
                                          Expanded(
                                            child: _statsColumn(context),
                                          ),
                                          const SizedBox(width: spacingLG),
                                          SizedBox(
                                            width: 240,
                                            child: _otherWindows(
                                              context,
                                              otherMatches,
                                            ),
                                          ),
                                        ],
                                      )
                                    else ...<Widget>[
                                      _statsColumn(context),
                                      const SizedBox(height: spacingLG),
                                      _otherWindows(context, otherMatches),
                                    ],
                                  ],
                                );
                              },
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _statsColumn(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        _StatCompareRow(
          label: 'Possession',
          homeValue: '${moment.possessionHome}%',
          awayValue: '${100 - moment.possessionHome}%',
          homeShare: moment.possessionHome / 100,
        ),
        const SizedBox(height: spacingMD),
        _StatCompareRow(
          label: 'Shots',
          homeValue: '${moment.shotsHome}',
          awayValue: '${moment.shotsAway}',
          homeShare: moment.shotsHome / (moment.shotsHome + moment.shotsAway),
        ),
        const SizedBox(height: spacingMD),
        _StatCompareRow(
          label: 'Pass Accuracy',
          homeValue: '${moment.passAccuracyHome}%',
          awayValue: '${moment.passAccuracyAway}%',
          homeShare:
              moment.passAccuracyHome /
              (moment.passAccuracyHome + moment.passAccuracyAway),
        ),
        const SizedBox(height: spacingMD),
        _StatCompareRow(
          label: 'xThreat',
          homeValue: moment.xThreatHome.toStringAsFixed(1),
          awayValue: moment.xThreatAway.toStringAsFixed(1),
          homeShare:
              moment.xThreatHome / (moment.xThreatHome + moment.xThreatAway),
        ),
        const SizedBox(height: spacingLG),
        Text('Market Pulse', style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: spacingSM),
        _MarketPulseBoard(moment: moment),
        const SizedBox(height: spacingLG),
        Text('Event Tape', style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: spacingSM),
        ...moment.eventTape.map(
          (BroadcastTickerEvent item) => _EventTapeTile(item: item),
        ),
        const SizedBox(height: spacingLG),
        Text('Push Signal', style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: spacingSM),
        _PushSignalCard(moment: moment),
        const SizedBox(height: spacingLG),
        Wrap(
          spacing: spacingSM,
          runSpacing: spacingSM,
          children: <Widget>[
            _PanelTag(label: moment.eventLabel),
            _PanelTag(label: moment.cameraMode),
            _PanelTag(label: 'Intensity ${(moment.control * 100).round()}'),
            _PanelTag(label: liveChannel),
          ],
        ),
      ],
    );
  }

  Widget _otherWindows(BuildContext context, List<LiveMatch> otherMatches) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          'Other Live Windows',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        const SizedBox(height: spacingSM),
        ...otherMatches.map(
          (LiveMatch match) => Container(
            margin: const EdgeInsets.only(bottom: spacingSM),
            padding: const EdgeInsets.all(spacingMD),
            decoration: BoxDecoration(
              color: AppColors.background.withValues(alpha: 0.54),
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: AppColors.divider),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  '${match.homeClub} vs ${match.awayClub}',
                  style: Theme.of(
                    context,
                  ).textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: spacingXS),
                Text(
                  '${match.homeScore}-${match.awayScore}  |  ${match.minute}\'',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: AppColors.gold,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: spacingXS),
                Text(
                  'Focus ${match.homeStarPlayer}',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: AppColors.primary,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: spacingXS),
                Text(
                  match.headline,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _LiveWinStrip extends StatelessWidget {
  const _LiveWinStrip({required this.moment, required this.match});

  final BroadcastMoment moment;
  final LiveMatch match;

  @override
  Widget build(BuildContext context) {
    final int homeFlex = (moment.homeWinProbability * 1000).round().clamp(
      1,
      998,
    );
    final int drawFlex = (moment.drawWinProbability * 1000).round().clamp(
      1,
      998,
    );
    final int awayFlex = (moment.awayWinProbability * 1000).round().clamp(
      1,
      998,
    );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        Text(
          'Live Win %',
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: AppColors.textSecondary,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: spacingSM),
        Row(
          children: <Widget>[
            Expanded(
              child: _ProbabilityPill(
                label: match.homeClub,
                probability: moment.homeWinProbability,
                line: moment.homeOdds,
                shift: moment.homeShift,
                color: AppColors.primary,
              ),
            ),
            const SizedBox(width: spacingSM),
            Expanded(
              child: _ProbabilityPill(
                label: 'Draw',
                probability: moment.drawWinProbability,
                line: moment.drawOdds,
                shift: moment.drawShift,
                color: AppColors.textSecondary,
              ),
            ),
            const SizedBox(width: spacingSM),
            Expanded(
              child: _ProbabilityPill(
                label: match.awayClub,
                probability: moment.awayWinProbability,
                line: moment.awayOdds,
                shift: moment.awayShift,
                color: AppColors.gold,
              ),
            ),
          ],
        ),
        const SizedBox(height: spacingSM),
        ClipRRect(
          borderRadius: BorderRadius.circular(999),
          child: SizedBox(
            height: 10,
            child: Row(
              children: <Widget>[
                Expanded(
                  flex: homeFlex,
                  child: Container(color: AppColors.primary),
                ),
                Expanded(
                  flex: drawFlex,
                  child: Container(
                    color: AppColors.textSecondary.withValues(alpha: 0.65),
                  ),
                ),
                Expanded(
                  flex: awayFlex,
                  child: Container(
                    color: AppColors.gold.withValues(alpha: 0.8),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _ProbabilityPill extends StatelessWidget {
  const _ProbabilityPill({
    required this.label,
    required this.probability,
    required this.line,
    required this.shift,
    required this.color,
  });

  final String label;
  final double probability;
  final double line;
  final double shift;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(spacingSM),
      decoration: BoxDecoration(
        color: AppColors.card.withValues(alpha: 0.78),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withValues(alpha: 0.26)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
          ),
          const SizedBox(height: spacingXS),
          Text(
            '${(probability * 100).round()}%',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              color: color,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: spacingXS),
          Text(
            'Line ${line.toStringAsFixed(2)}x',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: AppColors.textPrimary,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: spacingXS),
          Text(
            AppFormatters.percent(shift * 100),
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: shift >= 0 ? AppColors.success : AppColors.danger,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class _MarketPulseBoard extends StatelessWidget {
  const _MarketPulseBoard({required this.moment});

  final BroadcastMoment moment;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(spacingMD),
      decoration: BoxDecoration(
        color: AppColors.background.withValues(alpha: 0.58),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppColors.divider),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            moment.marketLabel,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              color: AppColors.textPrimary,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: spacingXS),
          Text(
            'Live lines and win % react to score state, momentum, and late-match pressure.',
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
          ),
          const SizedBox(height: spacingMD),
          Row(
            children: <Widget>[
              Expanded(
                child: _MarketLineTile(
                  label: 'Home',
                  line: moment.homeOdds,
                  shift: moment.homeShift,
                  color: AppColors.primary,
                ),
              ),
              const SizedBox(width: spacingSM),
              Expanded(
                child: _MarketLineTile(
                  label: 'Draw',
                  line: moment.drawOdds,
                  shift: moment.drawShift,
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(width: spacingSM),
              Expanded(
                child: _MarketLineTile(
                  label: 'Away',
                  line: moment.awayOdds,
                  shift: moment.awayShift,
                  color: AppColors.gold,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _MarketLineTile extends StatelessWidget {
  const _MarketLineTile({
    required this.label,
    required this.line,
    required this.shift,
    required this.color,
  });

  final String label;
  final double line;
  final double shift;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(spacingSM),
      decoration: BoxDecoration(
        color: AppColors.card.withValues(alpha: 0.72),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withValues(alpha: 0.24)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            label,
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
          ),
          const SizedBox(height: spacingXS),
          Text(
            '${line.toStringAsFixed(2)}x',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              color: color,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: spacingXS),
          Text(
            AppFormatters.percent(shift * 100),
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: shift >= 0 ? AppColors.success : AppColors.danger,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class _EventTapeTile extends StatelessWidget {
  const _EventTapeTile({required this.item});

  final BroadcastTickerEvent item;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: spacingSM),
      padding: const EdgeInsets.all(spacingMD),
      decoration: BoxDecoration(
        color: AppColors.background.withValues(alpha: 0.52),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color:
              item.dramatic
                  ? AppColors.gold.withValues(alpha: 0.42)
                  : AppColors.divider,
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: spacingSM,
              vertical: spacingXS,
            ),
            decoration: BoxDecoration(
              color:
                  item.dramatic
                      ? AppColors.gold.withValues(alpha: 0.16)
                      : AppColors.card.withValues(alpha: 0.8),
              borderRadius: BorderRadius.circular(999),
            ),
            child: Text(
              item.type,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: item.dramatic ? AppColors.gold : AppColors.textPrimary,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          const SizedBox(width: spacingMD),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  '${item.minute}\'  ${item.player}',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: AppColors.textPrimary,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: spacingXS),
                Text(
                  item.commentary,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: AppColors.textSecondary,
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

class _PushSignalCard extends StatelessWidget {
  const _PushSignalCard({required this.moment});

  final BroadcastMoment moment;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(spacingMD),
      decoration: BoxDecoration(
        color: AppColors.background.withValues(alpha: 0.58),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color:
              moment.isBigMoment
                  ? AppColors.gold.withValues(alpha: 0.42)
                  : AppColors.divider,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            moment.pushTitle ?? 'Stand By',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              color:
                  moment.isBigMoment ? AppColors.gold : AppColors.textPrimary,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: spacingXS),
          Text(
            moment.pushBody ??
                'No dramatic event is active. The system stays armed for goals, red cards, and sudden momentum breaks.',
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
          ),
        ],
      ),
    );
  }
}

class _AnimatedScore extends StatelessWidget {
  const _AnimatedScore({required this.score});

  final int score;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 78,
      padding: const EdgeInsets.symmetric(vertical: spacingSM),
      decoration: BoxDecoration(
        color: AppColors.background.withValues(alpha: 0.64),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppColors.primary.withValues(alpha: 0.32)),
      ),
      alignment: Alignment.center,
      child: AnimatedSwitcher(
        duration: AppMotion.slow,
        transitionBuilder: (Widget child, Animation<double> animation) {
          final Animation<double> scale = Tween<double>(
            begin: 0.82,
            end: 1,
          ).animate(
            CurvedAnimation(parent: animation, curve: AppMotion.elasticOut),
          );
          return FadeTransition(
            opacity: animation,
            child: ScaleTransition(scale: scale, child: child),
          );
        },
        child: Text(
          '$score',
          key: ValueKey<int>(score),
          style: Theme.of(context).textTheme.headlineLarge?.copyWith(
            color: AppColors.gold,
            fontSize: 42,
            fontWeight: FontWeight.w800,
          ),
        ),
      ),
    );
  }
}

class _StatCompareRow extends StatelessWidget {
  const _StatCompareRow({
    required this.label,
    required this.homeValue,
    required this.awayValue,
    required this.homeShare,
  });

  final String label;
  final String homeValue;
  final String awayValue;
  final double homeShare;

  @override
  Widget build(BuildContext context) {
    final double share = homeShare.clamp(0.0, 1.0);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: <Widget>[
            SizedBox(
              width: 54,
              child: Text(
                homeValue,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppColors.primary,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            Expanded(
              child: Text(
                label,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ),
            SizedBox(
              width: 54,
              child: Text(
                awayValue,
                textAlign: TextAlign.end,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppColors.gold,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: spacingSM),
        ClipRRect(
          borderRadius: BorderRadius.circular(999),
          child: SizedBox(
            height: 10,
            child: Row(
              children: <Widget>[
                Expanded(
                  flex: (share * 1000).round().clamp(1, 999),
                  child: Container(color: AppColors.primary),
                ),
                Expanded(
                  flex: ((1 - share) * 1000).round().clamp(1, 999),
                  child: Container(
                    color: AppColors.gold.withValues(alpha: 0.75),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _TopChip extends StatelessWidget {
  const _TopChip({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: spacingSM,
        vertical: spacingXS,
      ),
      decoration: BoxDecoration(
        color: AppColors.card.withValues(alpha: 0.82),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: AppColors.divider),
      ),
      child: RichText(
        text: TextSpan(
          children: <InlineSpan>[
            TextSpan(
              text: '$label ',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            TextSpan(
              text: value,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: AppColors.textPrimary,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PanelTag extends StatelessWidget {
  const _PanelTag({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: spacingSM,
        vertical: spacingXS,
      ),
      decoration: BoxDecoration(
        color: AppColors.background.withValues(alpha: 0.58),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: AppColors.divider),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.bodySmall?.copyWith(
          color: AppColors.textPrimary,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _PlayerMarker extends StatelessWidget {
  const _PlayerMarker({required this.color});

  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 18,
      height: 18,
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: color.withValues(alpha: 0.35),
            blurRadius: 16,
            spreadRadius: 2,
          ),
        ],
      ),
    );
  }
}

class _GlowOrb extends StatelessWidget {
  const _GlowOrb({required this.size, required this.color});

  final double size;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: RadialGradient(
          colors: <Color>[color, color.withValues(alpha: 0)],
        ),
      ),
    );
  }
}

class _CameraBadge extends StatelessWidget {
  const _CameraBadge({required this.cameraMode});

  final String cameraMode;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: spacingMD,
        vertical: spacingSM,
      ),
      decoration: BoxDecoration(
        color: AppColors.background.withValues(alpha: 0.7),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: AppColors.divider),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Camera', style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: spacingXS),
          Text(
            cameraMode,
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(fontWeight: FontWeight.w700),
          ),
        ],
      ),
    );
  }
}

class _PitchPainter extends CustomPainter {
  const _PitchPainter({required this.moment});

  final BroadcastMoment moment;

  @override
  void paint(Canvas canvas, Size size) {
    final double horizonY = size.height * 0.18;
    final double bottomY = size.height * 0.94;
    final double leftTop = size.width * 0.21;
    final double rightTop = size.width * 0.79;
    final double leftBottom = size.width * 0.04;
    final double rightBottom = size.width * 0.96;

    final Path pitch =
        Path()
          ..moveTo(leftTop, horizonY)
          ..lineTo(rightTop, horizonY)
          ..lineTo(rightBottom, bottomY)
          ..lineTo(leftBottom, bottomY)
          ..close();

    final Rect pitchBounds = Rect.fromLTRB(
      leftBottom,
      horizonY,
      rightBottom,
      bottomY,
    );

    canvas.drawPath(
      pitch,
      Paint()
        ..shader = const LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: <Color>[
            Color(0xFF2A8C59),
            Color(0xFF145234),
            Color(0xFF0B361F),
          ],
        ).createShader(pitchBounds),
    );

    final Paint linePaint =
        Paint()
          ..color = Colors.white.withValues(alpha: 0.52)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2;

    canvas.drawPath(pitch, linePaint);

    final Path midLine =
        Path()
          ..moveTo((leftTop + rightTop) / 2, horizonY)
          ..lineTo((leftBottom + rightBottom) / 2, bottomY);
    canvas.drawPath(midLine, linePaint);

    final Rect centerEllipse = Rect.fromCenter(
      center: Offset(size.width / 2, lerpDouble(horizonY, bottomY, 0.52)!),
      width: size.width * 0.24,
      height: size.height * 0.14,
    );
    canvas.drawOval(centerEllipse, linePaint);

    final double depthShift = lerpDouble(0, size.width * 0.03, moment.control)!;
    canvas.drawPath(
      _penaltyBoxPath(
        leftTop: leftTop,
        leftBottom: leftBottom + depthShift,
        horizonY: horizonY,
        bottomY: bottomY,
        side: _PitchSide.left,
      ),
      linePaint,
    );
    canvas.drawPath(
      _penaltyBoxPath(
        leftTop: rightTop,
        leftBottom: rightBottom - depthShift,
        horizonY: horizonY,
        bottomY: bottomY,
        side: _PitchSide.right,
      ),
      linePaint,
    );

    final Paint hudPaint =
        Paint()
          ..color = AppColors.primary.withValues(alpha: 0.08)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1;

    for (int i = 0; i < 6; i++) {
      final double y = lerpDouble(horizonY, bottomY, i / 5)!;
      canvas.drawLine(
        Offset(lerpDouble(leftTop, leftBottom, i / 5)!, y),
        Offset(lerpDouble(rightTop, rightBottom, i / 5)!, y),
        hudPaint,
      );
    }
  }

  Path _penaltyBoxPath({
    required double leftTop,
    required double leftBottom,
    required double horizonY,
    required double bottomY,
    required _PitchSide side,
  }) {
    final double topInset = 0.12;
    final double bottomInset = 0.24;
    final double innerTop =
        side == _PitchSide.left ? leftTop + 48 : leftTop - 48;
    final double innerBottom =
        side == _PitchSide.left ? leftBottom + 96 : leftBottom - 96;

    return Path()
      ..moveTo(leftTop, lerpDouble(horizonY, bottomY, topInset)!)
      ..lineTo(innerTop, lerpDouble(horizonY, bottomY, topInset)!)
      ..lineTo(innerBottom, lerpDouble(horizonY, bottomY, bottomInset)!)
      ..lineTo(leftBottom, lerpDouble(horizonY, bottomY, bottomInset)!)
      ..close();
  }

  @override
  bool shouldRepaint(covariant _PitchPainter oldDelegate) {
    return oldDelegate.moment != moment;
  }
}

enum _PitchSide { left, right }
