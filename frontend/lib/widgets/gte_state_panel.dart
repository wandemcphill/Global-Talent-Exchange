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
    final Color accent = accentColor ?? GteShellTheme.accent;
    return GteSurfacePanel(
      emphasized: true,
      accentColor: accent,
      child: Column(
        mainAxisSize: MainAxisSize.min,
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
            const SizedBox(height: 10),
          ],
          if (icon != null || isLoading) ...<Widget>[
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(16),
                color: Colors.white.withValues(alpha: 0.05),
                border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
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
            const SizedBox(height: 14),
          ],
          Text(title, style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 8),
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
