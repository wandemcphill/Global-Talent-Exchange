import 'package:flutter/material.dart';

import 'gtex_action_button.dart';
import '../theme/gtex_colors.dart';

enum GtexButtonVariant { primary, secondary, ghost }

class GtexButton extends StatelessWidget {
  const GtexButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.icon,
    this.variant = GtexButtonVariant.primary,
    this.compact = false,
  });

  final String label;
  final VoidCallback? onPressed;
  final IconData? icon;
  final GtexButtonVariant variant;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return GtexActionButton(
      label: label,
      icon: icon,
      onPressed: onPressed,
      compact: compact,
      secondary: variant != GtexButtonVariant.primary,
      accent: switch (variant) {
        GtexButtonVariant.primary => GtexColors.pitch,
        GtexButtonVariant.secondary => GtexColors.cyan,
        GtexButtonVariant.ghost => GtexColors.textMuted,
      },
    );
  }
}
