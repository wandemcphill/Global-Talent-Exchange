import 'package:flutter/material.dart';

import '../../../ui_gtex/ui_gtex.dart';

class ModeChipButton extends StatelessWidget {
  const ModeChipButton({
    super.key,
    required this.label,
    required this.icon,
    required this.accent,
    required this.isActive,
    required this.onPressed,
    this.badge,
  });

  final String label;
  final IconData icon;
  final Color accent;
  final bool isActive;
  final VoidCallback onPressed;
  final String? badge;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(GtexSpacing.radiusPill),
        onTap: onPressed,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 140),
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
          decoration: BoxDecoration(
            color: isActive
                ? accent.withValues(alpha: 0.16)
                : GtexColors.surfaceOverlay,
            borderRadius: BorderRadius.circular(GtexSpacing.radiusPill),
            border: Border.all(
              color: isActive ? accent : GtexColors.surfaceBorder,
              width: isActive ? 1.5 : 1,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              Icon(
                icon,
                size: 14,
                color: isActive ? accent : GtexColors.textMuted,
              ),
              const SizedBox(width: 4),
              Text(
                label,
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                      color: isActive ? GtexColors.textPrimary : GtexColors.textMuted,
                      fontWeight: FontWeight.w900,
                      letterSpacing: 0.4,
                      fontSize: 10,
                    ),
              ),
              if (badge != null) ...<Widget>[
                const SizedBox(width: 4),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                  decoration: BoxDecoration(
                    color: isActive
                        ? accent.withValues(alpha: 0.28)
                        : GtexColors.surfaceBase,
                    borderRadius:
                        BorderRadius.circular(GtexSpacing.radiusPill),
                  ),
                  child: Text(
                    badge!,
                    style: TextStyle(
                      color: isActive ? accent : GtexColors.textMuted,
                      fontSize: 9,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
