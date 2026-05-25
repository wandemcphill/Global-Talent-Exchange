import 'package:flutter/material.dart';

import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';
import '../theme/gtex_typography.dart';

class GtexErrorBanner extends StatelessWidget {
  const GtexErrorBanner({
    super.key,
    this.title = 'Something went wrong',
    required this.message,
    this.onRetry,
    this.retryLabel = 'Try again',
    this.icon = Icons.warning_amber_rounded,
  });

  final String title;
  final String message;
  final VoidCallback? onRetry;
  final String retryLabel;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens colors = GtexColors.of(context);
    return Container(
      decoration: BoxDecoration(
        color: colors.brandAlert.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(GtexRadius.lg),
        border: Border.all(color: colors.brandAlert.withValues(alpha: 0.28)),
      ),
      child: IntrinsicHeight(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            Container(
              width: 3,
              decoration: BoxDecoration(
                color: colors.brandAlert,
                borderRadius: const BorderRadius.horizontal(
                  left: Radius.circular(GtexRadius.lg),
                ),
              ),
            ),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(GtexSpacing.md),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Icon(icon, color: colors.brandAlert, size: 20),
                    const SizedBox(width: GtexSpacing.sm),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: <Widget>[
                          Text(
                            title,
                            style: GtexText.labelMD.copyWith(
                              color: colors.textPrimary,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                          const SizedBox(height: GtexSpacing.xxs),
                          Text(
                            message,
                            style: GtexText.bodySM.copyWith(
                              color: colors.textSecondary,
                            ),
                          ),
                          if (onRetry != null) ...<Widget>[
                            const SizedBox(height: GtexSpacing.xs),
                            TextButton(
                              onPressed: onRetry,
                              style: TextButton.styleFrom(
                                foregroundColor: colors.brandPitch,
                                padding: EdgeInsets.zero,
                                minimumSize: const Size(0, 32),
                                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                              ),
                              child: Text(retryLabel),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
