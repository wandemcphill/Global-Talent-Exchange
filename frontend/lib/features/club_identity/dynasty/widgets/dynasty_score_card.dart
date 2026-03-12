import 'package:flutter/material.dart';

import '../../../../widgets/gte_shell_theme.dart';
import '../../../../widgets/gte_surface_panel.dart';
import '../data/dynasty_profile_dto.dart';

class DynastyScoreCard extends StatelessWidget {
  const DynastyScoreCard({
    super.key,
    required this.profile,
  });

  final DynastyProfileDto profile;

  @override
  Widget build(BuildContext context) {
    final double progress = (profile.dynastyScore / 100).clamp(0, 1);
    final _TierStep currentTier = _currentTier(profile.dynastyScore);
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Dynasty score',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 8),
          Text(
            '${profile.dynastyScore}',
            style: Theme.of(context).textTheme.displaySmall?.copyWith(
                  color: GteShellTheme.accentWarm,
                ),
          ),
          const SizedBox(height: 6),
          Text(
            'Tier: ${currentTier.label}',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: GteShellTheme.textPrimary.withValues(alpha: 0.78),
                ),
          ),
          const SizedBox(height: 12),
          ClipRRect(
            borderRadius: BorderRadius.circular(999),
            child: LinearProgressIndicator(
              minHeight: 10,
              value: progress,
              backgroundColor: GteShellTheme.stroke,
              valueColor: AlwaysStoppedAnimation<Color>(
                progress >= 0.8
                    ? GteShellTheme.accentWarm
                    : GteShellTheme.accent,
              ),
            ),
          ),
          const SizedBox(height: 12),
          _TierMeter(
            score: profile.dynastyScore,
            currentTier: currentTier,
          ),
          const SizedBox(height: 12),
          Text(
            _scoreMessage(profile.dynastyScore),
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        ],
      ),
    );
  }

  String _scoreMessage(int score) {
    if (score >= 90) {
      return 'Rare air. This is the kind of score that changes how a club is remembered.';
    }
    if (score >= 70) {
      return 'A heavy reputation with the numbers to back up the feeling.';
    }
    if (score >= 45) {
      return 'The club is forcing its way into the conversation, but the case still needs more seasons.';
    }
    return 'The foundation is visible, but dynasty status remains protected by a high bar.';
  }
}

class _TierStep {
  const _TierStep({
    required this.tier,
    required this.label,
    required this.threshold,
  });

  final _DynastyTier tier;
  final String label;
  final int threshold;
}

enum _DynastyTier {
  goodClub,
  bigClub,
  dynasty,
}

const List<_TierStep> _tierSteps = <_TierStep>[
  _TierStep(tier: _DynastyTier.goodClub, label: 'Good club', threshold: 0),
  _TierStep(tier: _DynastyTier.bigClub, label: 'Big club', threshold: 45),
  _TierStep(tier: _DynastyTier.dynasty, label: 'Dynasty', threshold: 70),
];

_TierStep _currentTier(int score) {
  return _tierSteps.lastWhere(
    (_TierStep step) => score >= step.threshold,
    orElse: () => _tierSteps.first,
  );
}

class _TierMeter extends StatelessWidget {
  const _TierMeter({
    required this.score,
    required this.currentTier,
  });

  final int score;
  final _TierStep currentTier;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: _tierSteps.map((_TierStep step) {
        final bool reached = score >= step.threshold;
        final bool isCurrent = step.tier == currentTier.tier;
        final Color tone = isCurrent
            ? GteShellTheme.accentWarm
            : reached
                ? GteShellTheme.accent
                : GteShellTheme.stroke;
        return _TierPill(
          label: step.label,
          tone: tone,
          emphasized: isCurrent,
        );
      }).toList(growable: false),
    );
  }
}

class _TierPill extends StatelessWidget {
  const _TierPill({
    required this.label,
    required this.tone,
    this.emphasized = false,
  });

  final String label;
  final Color tone;
  final bool emphasized;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: tone.withValues(alpha: emphasized ? 0.2 : 0.12),
        border: Border.all(
          color: tone.withValues(alpha: emphasized ? 0.55 : 0.3),
        ),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: emphasized ? tone : GteShellTheme.textMuted,
            ),
      ),
    );
  }
}
