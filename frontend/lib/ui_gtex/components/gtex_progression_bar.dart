import 'package:flutter/material.dart';

import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';

/// Standardized progress bar for reputation, academy levels, dynasty streaks, or facility upgrades.
class GtexProgressionBar extends StatelessWidget {
  const GtexProgressionBar({
    super.key,
    required this.label,
    this.currentStep,
    this.totalSteps,
    this.progressValue,
    this.tierLabel,
    this.helperText,
    this.accentColor = GtexColors.gold,
  });

  final String label;
  final int? currentStep;
  final int? totalSteps;
  final double? progressValue;
  final String? tierLabel;
  final String? helperText;
  final Color accentColor;

  double get _normalizedProgress {
    if (progressValue != null) {
      return progressValue!.clamp(0.0, 1.0);
    }
    if (currentStep != null && totalSteps != null && totalSteps! > 0) {
      return (currentStep! / totalSteps!).clamp(0.0, 1.0);
    }
    return 0.0;
  }

  @override
  Widget build(BuildContext context) {
    final double pct = _normalizedProgress;
    final String pctText = '${(pct * 100).toInt()}%';

    return Container(
      padding: const EdgeInsets.all(GtexSpacing.sm),
      decoration: BoxDecoration(
        color: GtexColors.surfaceBase.withValues(alpha: 0.85),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
        border: Border.all(color: GtexColors.line),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: <Widget>[
              Expanded(
                child: Wrap(
                  crossAxisAlignment: WrapCrossAlignment.center,
                  spacing: GtexSpacing.xs,
                  children: <Widget>[
                    Text(
                      label.toUpperCase(),
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                            color: GtexColors.textSecondary,
                            fontWeight: FontWeight.w900,
                            letterSpacing: 0.6,
                          ),
                    ),
                    if (tierLabel != null && tierLabel!.isNotEmpty)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                        decoration: BoxDecoration(
                          color: accentColor.withValues(alpha: 0.2),
                          borderRadius: BorderRadius.circular(4),
                          border: Border.all(color: accentColor.withValues(alpha: 0.5)),
                        ),
                        child: Text(
                          tierLabel!,
                          style: Theme.of(context).textTheme.labelSmall?.copyWith(
                                color: accentColor,
                                fontWeight: FontWeight.w800,
                                fontSize: 10,
                              ),
                        ),
                      ),
                  ],
                ),
              ),
              Text(
                currentStep != null && totalSteps != null
                    ? '$currentStep / $totalSteps ($pctText)'
                    : pctText,
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      color: accentColor,
                      fontWeight: FontWeight.w900,
                    ),
              ),
            ],
          ),
          const SizedBox(height: GtexSpacing.xs),
          ClipRRect(
            borderRadius: BorderRadius.circular(GtexSpacing.radiusSm),
            child: Stack(
              children: <Widget>[
                Container(
                  height: 10,
                  width: double.infinity,
                  color: GtexColors.panel,
                ),
                FractionallySizedBox(
                  widthFactor: pct,
                  child: Container(
                    height: 10,
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: <Color>[
                          accentColor.withValues(alpha: 0.7),
                          accentColor,
                        ],
                      ),
                      boxShadow: <BoxShadow>[
                        BoxShadow(
                          color: accentColor.withValues(alpha: 0.6),
                          blurRadius: 6,
                          spreadRadius: 1,
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
          if (helperText != null && helperText!.isNotEmpty) ...<Widget>[
            const SizedBox(height: 6),
            Text(
              helperText!,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: GtexColors.textMuted,
                    fontWeight: FontWeight.w600,
                  ),
            ),
          ],
        ],
      ),
    );
  }
}
