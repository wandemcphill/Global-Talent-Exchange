import 'package:flutter/material.dart';

import '../models/gtex_competition_models.dart';

/// Horizontal progress rail across a competition's life:
/// upcoming → registration → live → completed → settled.
///
/// Renders the signed-in club's own outcome (eliminated / winner) next to the
/// rail when the payload carries it, so a user can tell at a glance whether
/// they are still in it.
class GtexCompetitionLifecycleRail extends StatelessWidget {
  const GtexCompetitionLifecycleRail({
    super.key,
    required this.summary,
    this.compact = false,
  });

  final GtexCompetitionSummary summary;
  final bool compact;

  static const List<GtexCompetitionLifecycleStage> _stages =
      <GtexCompetitionLifecycleStage>[
        GtexCompetitionLifecycleStage.upcoming,
        GtexCompetitionLifecycleStage.registration,
        GtexCompetitionLifecycleStage.live,
        GtexCompetitionLifecycleStage.completed,
        GtexCompetitionLifecycleStage.settlement,
      ];

  @override
  Widget build(BuildContext context) {
    final GtexCompetitionLifecycleStage current = summary.lifecycleStage;
    return Semantics(
      label:
          'Competition lifecycle. Current stage: ${current.label}.'
          '${summary.viewerOutcomeLabel == null ? '' : ' Your status: ${summary.viewerOutcomeLabel}.'}',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Row(
            children: <Widget>[
              for (int index = 0; index < _stages.length; index += 1) ...<Widget>[
                if (index > 0)
                  Expanded(
                    child: Container(
                      height: 2,
                      margin: const EdgeInsets.symmetric(horizontal: 4),
                      color:
                          _stages[index].rank <= current.rank
                              ? _accentFor(current)
                              : const Color(0xFF2A3440),
                    ),
                  ),
                _StageDot(
                  stage: _stages[index],
                  reached: _stages[index].rank <= current.rank,
                  isCurrent: _stages[index] == current,
                  accent: _accentFor(current),
                ),
              ],
            ],
          ),
          const SizedBox(height: 8),
          Wrap(
            crossAxisAlignment: WrapCrossAlignment.center,
            spacing: 8,
            runSpacing: 6,
            children: <Widget>[
              _Pill(
                label: current.label,
                accent: _accentFor(current),
                icon: _iconFor(current),
              ),
              if (summary.isAwaitingSettlement)
                const _Pill(
                  label: 'Prize settlement pending',
                  accent: Color(0xFFFFB800),
                  icon: Icons.hourglass_bottom_outlined,
                ),
              if (summary.winnerClubName != null &&
                  summary.winnerClubName!.trim().isNotEmpty)
                _Pill(
                  label: 'Winner: ${summary.winnerClubName!.trim()}',
                  accent: const Color(0xFFFFD66B),
                  icon: Icons.emoji_events_outlined,
                ),
              if (summary.viewerOutcomeLabel != null)
                _Pill(
                  label: summary.viewerOutcomeLabel!,
                  accent: _outcomeAccent(summary.viewerOutcome),
                  icon: _outcomeIcon(summary.viewerOutcome),
                ),
            ],
          ),
        ],
      ),
    );
  }

  static Color _accentFor(GtexCompetitionLifecycleStage stage) {
    switch (stage) {
      case GtexCompetitionLifecycleStage.upcoming:
        return const Color(0xFF8A97A8);
      case GtexCompetitionLifecycleStage.registration:
        return const Color(0xFF2F80ED);
      case GtexCompetitionLifecycleStage.live:
        return const Color(0xFF00E87A);
      case GtexCompetitionLifecycleStage.completed:
        return const Color(0xFFB26DFF);
      case GtexCompetitionLifecycleStage.settlement:
        return const Color(0xFFFFD66B);
    }
  }

  static IconData _iconFor(GtexCompetitionLifecycleStage stage) {
    switch (stage) {
      case GtexCompetitionLifecycleStage.upcoming:
        return Icons.event_outlined;
      case GtexCompetitionLifecycleStage.registration:
        return Icons.how_to_reg_outlined;
      case GtexCompetitionLifecycleStage.live:
        return Icons.sensors_outlined;
      case GtexCompetitionLifecycleStage.completed:
        return Icons.flag_outlined;
      case GtexCompetitionLifecycleStage.settlement:
        return Icons.payments_outlined;
    }
  }

  static Color _outcomeAccent(GtexCompetitionViewerOutcome outcome) {
    switch (outcome) {
      case GtexCompetitionViewerOutcome.winner:
        return const Color(0xFFFFD66B);
      case GtexCompetitionViewerOutcome.eliminated:
        return const Color(0xFFFF3D3D);
      case GtexCompetitionViewerOutcome.active:
        return const Color(0xFF00E87A);
      case GtexCompetitionViewerOutcome.registered:
        return const Color(0xFF2F80ED);
      case GtexCompetitionViewerOutcome.notEntered:
      case GtexCompetitionViewerOutcome.unknown:
        return const Color(0xFF8A97A8);
    }
  }

  static IconData _outcomeIcon(GtexCompetitionViewerOutcome outcome) {
    switch (outcome) {
      case GtexCompetitionViewerOutcome.winner:
        return Icons.workspace_premium_outlined;
      case GtexCompetitionViewerOutcome.eliminated:
        return Icons.do_not_disturb_on_outlined;
      case GtexCompetitionViewerOutcome.active:
        return Icons.bolt_outlined;
      case GtexCompetitionViewerOutcome.registered:
        return Icons.check_circle_outline;
      case GtexCompetitionViewerOutcome.notEntered:
      case GtexCompetitionViewerOutcome.unknown:
        return Icons.remove_circle_outline;
    }
  }
}

class _StageDot extends StatelessWidget {
  const _StageDot({
    required this.stage,
    required this.reached,
    required this.isCurrent,
    required this.accent,
  });

  final GtexCompetitionLifecycleStage stage;
  final bool reached;
  final bool isCurrent;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final double size = isCurrent ? 14 : 10;
    return Tooltip(
      message: stage.label,
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: reached ? accent : const Color(0xFF2A3440),
          border: Border.all(
            color: reached ? accent : const Color(0xFF3A4654),
            width: isCurrent ? 2 : 1,
          ),
        ),
      ),
    );
  }
}

class _Pill extends StatelessWidget {
  const _Pill({required this.label, required this.accent, required this.icon});

  final String label;
  final Color accent;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: .12),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: accent.withValues(alpha: .38)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(icon, size: 13, color: accent),
          const SizedBox(width: 6),
          Text(
            label,
            style: TextStyle(
              color: accent,
              fontWeight: FontWeight.w900,
              fontSize: 11,
            ),
          ),
        ],
      ),
    );
  }
}
