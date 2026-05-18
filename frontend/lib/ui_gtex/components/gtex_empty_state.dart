import 'package:flutter/material.dart';

import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';
import 'gtex_action_button.dart';

class GtexEmptyState extends StatelessWidget {
  const GtexEmptyState({
    super.key,
    required this.title,
    required this.message,
    this.icon = Icons.sports_soccer_outlined,
    this.actionLabel,
    this.onAction,
    this.accent = GtexColors.pitch,
    this.recommendations = const <String>[],
  });

  final String title;
  final String message;
  final IconData icon;
  final String? actionLabel;
  final VoidCallback? onAction;
  final Color accent;
  final List<String> recommendations;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool compact =
            constraints.hasBoundedHeight && constraints.maxHeight < 260;
        final double iconShellSize = compact ? 48 : 72;
        final double iconSize = compact ? 24 : 34;
        final TextTheme textTheme = Theme.of(context).textTheme;
        final Widget content = Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 440),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                Container(
                  width: iconShellSize,
                  height: iconShellSize,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: accent.withValues(alpha: 0.12),
                    border: Border.all(color: accent.withValues(alpha: 0.35)),
                  ),
                  child: Icon(icon, color: accent, size: iconSize),
                ),
                SizedBox(height: compact ? GtexSpacing.sm : GtexSpacing.lg),
                Text(
                  title,
                  textAlign: TextAlign.center,
                  style: (compact
                          ? textTheme.titleMedium
                          : textTheme.headlineSmall)
                      ?.copyWith(
                        color: GtexColors.text,
                        fontWeight: FontWeight.w900,
                      ),
                ),
                SizedBox(height: compact ? GtexSpacing.xs : GtexSpacing.sm),
                Text(
                  message,
                  textAlign: TextAlign.center,
                  style: (compact ? textTheme.bodySmall : textTheme.bodyMedium)
                      ?.copyWith(
                        color: GtexColors.textSecondary,
                        height: compact ? 1.3 : 1.45,
                      ),
                ),
                if (recommendations.isNotEmpty) ...<Widget>[
                  SizedBox(height: compact ? GtexSpacing.sm : GtexSpacing.md),
                  Wrap(
                    alignment: WrapAlignment.center,
                    spacing: GtexSpacing.xs,
                    runSpacing: GtexSpacing.xs,
                    children: recommendations
                        .take(4)
                        .map(
                          (String item) => Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: GtexSpacing.sm,
                              vertical: 6,
                            ),
                            decoration: BoxDecoration(
                              color: accent.withValues(alpha: 0.1),
                              borderRadius: BorderRadius.circular(
                                GtexSpacing.radiusPill,
                              ),
                              border: Border.all(
                                color: accent.withValues(alpha: 0.26),
                              ),
                            ),
                            child: Text(
                              item,
                              style: textTheme.labelSmall?.copyWith(
                                color: GtexColors.textSecondary,
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                          ),
                        )
                        .toList(growable: false),
                  ),
                ],
                if (actionLabel != null && onAction != null) ...<Widget>[
                  SizedBox(height: compact ? GtexSpacing.sm : GtexSpacing.lg),
                  GtexActionButton(
                    label: actionLabel!,
                    onPressed: onAction,
                    accent: accent,
                  ),
                ],
              ],
            ),
          ),
        );

        if (!constraints.hasBoundedHeight) {
          return content;
        }
        return SingleChildScrollView(
          child: ConstrainedBox(
            constraints: BoxConstraints(minHeight: constraints.maxHeight),
            child: content,
          ),
        );
      },
    );
  }
}
