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
    final String resolvedEyebrow =
        eyebrow ?? (isLoading ? 'LIVE SYNC' : 'MATCHDAY STATUS');

    return GteSurfacePanel(
      emphasized: true,
      accentColor: accent,
      padding: const EdgeInsets.all(22),
      child: LayoutBuilder(
        builder: (BuildContext context, BoxConstraints constraints) {
          final bool stackHeader = constraints.maxWidth < 320;
          final bool showStatusVisual = icon != null || isLoading;
          final Widget eyebrowChip = Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: accent.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(tokens.radiusPill),
              border: Border.all(color: accent.withValues(alpha: 0.24)),
            ),
            child: Wrap(
              spacing: 8,
              runSpacing: 4,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: <Widget>[
                Container(
                  width: 8,
                  height: 8,
                  margin: const EdgeInsets.symmetric(vertical: 4),
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: accent,
                  ),
                ),
                Text(
                  resolvedEyebrow,
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: accent,
                    letterSpacing: 1.1,
                  ),
                ),
              ],
            ),
          );
          final Widget headerCopy = Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              eyebrowChip,
              const SizedBox(height: 14),
              Text(title, style: Theme.of(context).textTheme.headlineSmall),
              const SizedBox(height: 10),
              Text(
                message,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: tokens.textMuted,
                  height: 1.45,
                ),
              ),
            ],
          );
          final Widget? statusVisual =
              !showStatusVisual
                  ? null
                  : Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(tokens.radiusMedium),
                      color: accent.withValues(alpha: 0.14),
                      border: Border.all(color: accent.withValues(alpha: 0.24)),
                      boxShadow: <BoxShadow>[
                        BoxShadow(
                          color: accent.withValues(alpha: 0.12),
                          blurRadius: 18,
                          spreadRadius: 1,
                        ),
                      ],
                    ),
                    child:
                        isLoading
                            ? SizedBox(
                              width: 28,
                              height: 28,
                              child: CircularProgressIndicator(
                                strokeWidth: 2.6,
                                valueColor: AlwaysStoppedAnimation<Color>(
                                  accent,
                                ),
                              ),
                            )
                            : Icon(icon, size: 28, color: accent),
                  );

          return Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              if (stackHeader)
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    headerCopy,
                    if (statusVisual != null) ...<Widget>[
                      const SizedBox(height: 18),
                      statusVisual,
                    ],
                  ],
                )
              else
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Expanded(child: headerCopy),
                    if (statusVisual != null) ...<Widget>[
                      const SizedBox(width: 18),
                      statusVisual,
                    ],
                  ],
                ),
              if (actionLabel != null && onAction != null) ...<Widget>[
                const SizedBox(height: 18),
                FilledButton.icon(
                  onPressed: onAction,
                  icon: Icon(isLoading ? Icons.refresh : Icons.arrow_forward),
                  label: Text(actionLabel!),
                ),
              ],
            ],
          );
        },
      ),
    );
  }
}
