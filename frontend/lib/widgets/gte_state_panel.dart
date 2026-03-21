import 'package:flutter/material.dart';

import 'gte_shell_theme.dart';
import 'gte_surface_panel.dart';

class GteStatePanel extends StatelessWidget {
  const GteStatePanel({
    super.key,
    required this.title,
    required this.message,
    this.actionLabel,
    this.onAction,
    this.icon,
    this.eyebrow,
    this.accentColor,
    this.isLoading = false,
  });

  final String title;
  final String message;
  final String? actionLabel;
  final VoidCallback? onAction;
  final IconData? icon;
  final String? eyebrow;
  final Color? accentColor;
  final bool isLoading;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final Color accent = accentColor ?? tokens.accent;

    return GteSurfacePanel(
      emphasized: true,
      accentColor: accent,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              if (icon != null || isLoading) ...<Widget>[
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(tokens.radiusSmall),
                    color: accent.withValues(alpha: 0.14),
                    border: Border.all(color: accent.withValues(alpha: 0.24)),
                  ),
                  child: isLoading
                      ? SizedBox(
                          width: 28,
                          height: 28,
                          child: CircularProgressIndicator(
                            strokeWidth: 2.6,
                            valueColor: AlwaysStoppedAnimation<Color>(accent),
                          ),
                        )
                      : Icon(icon, size: 28, color: accent),
                ),
                const SizedBox(width: 14),
              ],
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    if (eyebrow != null) ...<Widget>[
                      Text(
                        eyebrow!,
                        style: Theme.of(context).textTheme.labelLarge?.copyWith(
                              color: accent,
                              letterSpacing: 1.1,
                            ),
                      ),
                      const SizedBox(height: 8),
                    ],
                    Text(
                      title,
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(message, style: Theme.of(context).textTheme.bodyMedium),
          if (actionLabel != null && onAction != null) ...<Widget>[
            const SizedBox(height: 18),
            FilledButton.icon(
              onPressed: onAction,
              icon: Icon(isLoading ? Icons.refresh : Icons.arrow_forward),
              label: Text(actionLabel!),
            ),
          ],
        ],
      ),
    );
  }
}
