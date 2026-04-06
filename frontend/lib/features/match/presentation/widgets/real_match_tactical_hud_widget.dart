import 'package:flutter/material.dart';

import '../../../../models/match_timeline_frame.dart';
import '../../../../models/real_match_engine_presentation.dart';
import '../broadcast_package_models.dart';

class RealMatchTacticalHudWidget extends StatelessWidget {
  const RealMatchTacticalHudWidget({
    super.key,
    required this.package,
    required this.presentation,
  });

  final MatchPresentationPackage package;
  final MatchEnginePresentationState presentation;

  @override
  Widget build(BuildContext context) {
    final String possessionLabel =
        presentation.activeEventContext?.hasPrimaryPlayer == true
            ? 'Possession focus: ${presentation.activeEventContext!.primaryPlayerName}'
            : 'Possession: ${presentation.possessionSide.name.toUpperCase()} · ${presentation.transitionLabel}';
    final String instructionSummary = _combinedInstructionSummary();
    return DecoratedBox(
      key: const Key('real-match-tactical-hud'),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        color: const Color(0xEA091219),
        border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: LayoutBuilder(
          builder: (BuildContext context, BoxConstraints constraints) {
            final bool stackedHeader = constraints.maxWidth < 430;
            final bool stackedCards = constraints.maxWidth < 520;
            final Widget headerPills = Wrap(
              spacing: 8,
              runSpacing: 8,
              alignment:
                  stackedHeader ? WrapAlignment.start : WrapAlignment.end,
              children: <Widget>[
                _HudPill(
                  label: presentation.phaseLabel.toUpperCase(),
                  accent: const Color(0xFFFDB022),
                ),
                _HudPill(
                  label: presentation.pressureLabel.toUpperCase(),
                  accent:
                      presentation.isDangerMoment
                          ? const Color(0xFFF97066)
                          : const Color(0xFF53B1FD),
                ),
              ],
            );

            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                if (stackedHeader) ...<Widget>[
                  Text(
                    'Tactical HUD',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: Colors.white,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 10),
                  headerPills,
                ] else
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Expanded(
                        child: Text(
                          'Tactical HUD',
                          style: Theme.of(
                            context,
                          ).textTheme.titleMedium?.copyWith(
                            color: Colors.white,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Flexible(
                        child: Align(
                          alignment: Alignment.centerRight,
                          child: headerPills,
                        ),
                      ),
                    ],
                  ),
                const SizedBox(height: 12),
                Text(
                  possessionLabel,
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: const Color(0xFF7DD3FC),
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 12),
                if (stackedCards) ...<Widget>[
                  _TeamTacticalCard(
                    team: package.home,
                    shape: presentation.homeShape,
                    eventContext: presentation.activeEventContext,
                    presentation: presentation,
                    accent: _teamAccent(package.home, const Color(0xFF22C55E)),
                  ),
                  const SizedBox(height: 10),
                  _TeamTacticalCard(
                    team: package.away,
                    shape: presentation.awayShape,
                    eventContext: presentation.activeEventContext,
                    presentation: presentation,
                    accent: _teamAccent(package.away, const Color(0xFFF97316)),
                    alignEnd: true,
                  ),
                ] else
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Expanded(
                        child: _TeamTacticalCard(
                          team: package.home,
                          shape: presentation.homeShape,
                          eventContext: presentation.activeEventContext,
                          presentation: presentation,
                          accent: _teamAccent(
                            package.home,
                            const Color(0xFF22C55E),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: _TeamTacticalCard(
                          team: package.away,
                          shape: presentation.awayShape,
                          eventContext: presentation.activeEventContext,
                          presentation: presentation,
                          accent: _teamAccent(
                            package.away,
                            const Color(0xFFF97316),
                          ),
                          alignEnd: true,
                        ),
                      ),
                    ],
                  ),
                if (instructionSummary.isNotEmpty) ...<Widget>[
                  const SizedBox(height: 12),
                  Text(
                    instructionSummary,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Colors.white70,
                      height: 1.35,
                    ),
                  ),
                ],
              ],
            );
          },
        ),
      ),
    );
  }

  String _combinedInstructionSummary() {
    final String homeInstructions = package.home.instructionSummary
        .take(3)
        .join(' | ');
    final String awayInstructions = package.away.instructionSummary
        .take(3)
        .join(' | ');
    final List<String> lines = <String>[
      if (homeInstructions.isNotEmpty)
        '${package.home.teamName}: $homeInstructions',
      if (awayInstructions.isNotEmpty)
        '${package.away.teamName}: $awayInstructions',
    ];
    return lines.join('   ');
  }

  Color _teamAccent(MatchPresentationTeam team, Color fallback) {
    final String? raw = team.accentColorHex;
    if (raw == null || raw.trim().isEmpty) {
      return fallback;
    }
    String normalized = raw.trim().replaceFirst('#', '');
    if (normalized.length == 6) {
      normalized = 'FF$normalized';
    }
    final int? parsed = int.tryParse(normalized, radix: 16);
    return parsed == null ? fallback : Color(parsed);
  }
}

class _TeamTacticalCard extends StatelessWidget {
  const _TeamTacticalCard({
    required this.team,
    required this.shape,
    required this.eventContext,
    required this.presentation,
    required this.accent,
    this.alignEnd = false,
  });

  final MatchPresentationTeam team;
  final MatchEngineTeamShape shape;
  final MatchEngineEventContext? eventContext;
  final MatchEnginePresentationState presentation;
  final Color accent;
  final bool alignEnd;

  @override
  Widget build(BuildContext context) {
    final String? press = _findInstruction(team.instructionSummary, 'press');
    final String? tempo = _findInstruction(team.instructionSummary, 'tempo');
    final String? width = _findInstruction(team.instructionSummary, 'width');
    final ({String label, String value}) focus = _focusCopy();
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: Colors.white.withValues(alpha: 0.04),
        border: Border.all(color: accent.withValues(alpha: 0.20)),
      ),
      child: Column(
        crossAxisAlignment:
            alignEnd ? CrossAxisAlignment.end : CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            team.shortName,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w900,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            '${shape.formation} | ${team.mentality ?? 'Style hidden'}',
            textAlign: alignEnd ? TextAlign.right : TextAlign.left,
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: Colors.white70),
          ),
          const SizedBox(height: 10),
          Wrap(
            alignment: alignEnd ? WrapAlignment.end : WrapAlignment.start,
            spacing: 8,
            runSpacing: 8,
            children: <Widget>[
              _HudMetricChip(label: 'Width', value: width ?? shape.widthLabel),
              _HudMetricChip(label: 'Line', value: _lineHeightLabel(shape)),
              _HudMetricChip(label: 'Compact', value: shape.compactnessLabel),
              _HudMetricChip(label: 'Press', value: press ?? 'Hidden'),
              _HudMetricChip(label: 'Tempo', value: tempo ?? 'Hidden'),
            ],
          ),
          const SizedBox(height: 10),
          _ShapeLaneSummary(shape: shape, accent: accent, alignEnd: alignEnd),
          const SizedBox(height: 10),
          Text(
            '${focus.label}: ${focus.value}',
            textAlign: alignEnd ? TextAlign.right : TextAlign.left,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: accent,
              fontWeight: FontWeight.w700,
              height: 1.3,
            ),
          ),
        ],
      ),
    );
  }

  ({String label, String value}) _focusCopy() {
    if (eventContext?.teamId == team.teamId &&
        eventContext?.bannerText != null) {
      return (label: 'Attack focus', value: eventContext!.bannerText!);
    }
    if (presentation.isSetPieceMoment) {
      return (label: 'Restart shape', value: presentation.transitionLabel);
    }
    if (presentation.transitionState?.isBreak == true) {
      return (
        label: shape.inPossession ? 'Break support' : 'Recovery run',
        value:
            shape.inPossession
                ? presentation.dangerLabel
                : 'Collapse space and recover central lanes',
      );
    }
    if (presentation.isDangerMoment && shape.inPossession) {
      return (label: 'Chance state', value: presentation.dangerLabel);
    }
    return (
      label: shape.inPossession ? 'Support shape' : 'Defensive block',
      value:
          shape.inPossession
              ? 'Maintain support lanes'
              : 'Hold compact distances',
    );
  }
}

class _ShapeLaneSummary extends StatelessWidget {
  const _ShapeLaneSummary({
    required this.shape,
    required this.accent,
    required this.alignEnd,
  });

  final MatchEngineTeamShape shape;
  final Color accent;
  final bool alignEnd;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment:
          alignEnd ? CrossAxisAlignment.end : CrossAxisAlignment.start,
      children: shape.lanes
          .where((MatchEngineShapeLane lane) => lane.activeCount > 0)
          .map(
            (MatchEngineShapeLane lane) => Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                mainAxisAlignment:
                    alignEnd ? MainAxisAlignment.end : MainAxisAlignment.start,
                children: <Widget>[
                  if (!alignEnd)
                    _LaneLabel(label: _laneLabel(lane.line), accent: accent),
                  if (!alignEnd) const SizedBox(width: 8),
                  Flexible(
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(999),
                      child: Align(
                        alignment:
                            alignEnd
                                ? Alignment.centerRight
                                : Alignment.centerLeft,
                        child: Container(
                          height: 8,
                          width: (lane.width * 2.4).clamp(26, 108).toDouble(),
                          color: accent.withValues(alpha: 0.42),
                        ),
                      ),
                    ),
                  ),
                  if (alignEnd) const SizedBox(width: 8),
                  if (alignEnd)
                    _LaneLabel(label: _laneLabel(lane.line), accent: accent),
                ],
              ),
            ),
          )
          .toList(growable: false),
    );
  }

  String _laneLabel(MatchEngineShapeLine line) {
    return switch (line) {
      MatchEngineShapeLine.goalkeeper => 'GK',
      MatchEngineShapeLine.defense => 'DEF',
      MatchEngineShapeLine.midfield => 'MID',
      MatchEngineShapeLine.attack => 'ATT',
    };
  }
}

class _LaneLabel extends StatelessWidget {
  const _LaneLabel({required this.label, required this.accent});

  final String label;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Text(
      label,
      style: Theme.of(context).textTheme.labelMedium?.copyWith(
        color: accent,
        fontWeight: FontWeight.w800,
      ),
    );
  }
}

class _HudMetricChip extends StatelessWidget {
  const _HudMetricChip({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        color: Colors.white.withValues(alpha: 0.04),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            label.toUpperCase(),
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: Colors.white54,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            value,
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }
}

class _HudPill extends StatelessWidget {
  const _HudPill({required this.label, required this.accent});

  final String label;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: accent.withValues(alpha: 0.15),
        border: Border.all(color: accent.withValues(alpha: 0.32)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(
          color: Colors.white,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}

String? _findInstruction(List<String> instructions, String keyword) {
  for (final String item in instructions) {
    if (item.toLowerCase().contains(keyword.toLowerCase())) {
      return item;
    }
  }
  return null;
}

String _lineHeightLabel(MatchEngineTeamShape shape) {
  final MatchEngineShapeLane defenseLane = shape.lanes.firstWhere(
    (MatchEngineShapeLane lane) => lane.line == MatchEngineShapeLine.defense,
    orElse:
        () => const MatchEngineShapeLane(
          line: MatchEngineShapeLine.defense,
          averageX: 0,
          averageY: 0,
          width: 0,
          activeCount: 0,
        ),
  );
  final double lineHeight = defenseLane.averageX;
  if (shape.side == MatchViewerSide.home) {
    if (lineHeight >= 34) {
      return 'High';
    }
    if (lineHeight >= 24) {
      return 'Mid';
    }
    return 'Deep';
  }
  if (lineHeight <= 66 && lineHeight > 0) {
    return 'High';
  }
  if (lineHeight <= 76 && lineHeight > 0) {
    return 'Mid';
  }
  return 'Deep';
}
