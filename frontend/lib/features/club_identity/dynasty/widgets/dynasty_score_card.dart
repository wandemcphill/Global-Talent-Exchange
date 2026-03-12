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
