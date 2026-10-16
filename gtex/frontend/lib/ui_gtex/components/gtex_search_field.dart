import 'package:flutter/material.dart';

import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';

class GtexSearchField extends StatelessWidget {
  const GtexSearchField({
    super.key,
    this.controller,
    this.hintText = 'Search GTEX',
    this.onChanged,
    this.onSubmitted,
    this.autofocus = false,
  });

  final TextEditingController? controller;
  final String hintText;
  final ValueChanged<String>? onChanged;
  final ValueChanged<String>? onSubmitted;
  final bool autofocus;

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      autofocus: autofocus,
      onChanged: onChanged,
      onSubmitted: onSubmitted,
      style: const TextStyle(
        color: GtexColors.text,
        fontWeight: FontWeight.w700,
      ),
      decoration: InputDecoration(
        hintText: hintText,
        prefixIcon: const Icon(Icons.search),
        filled: true,
        fillColor: GtexColors.panelStrong.withValues(alpha: 0.76),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: GtexSpacing.md,
          vertical: GtexSpacing.sm,
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(GtexSpacing.radiusPill),
          borderSide: const BorderSide(color: GtexColors.line),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(GtexSpacing.radiusPill),
          borderSide: BorderSide(
            color: GtexColors.line.withValues(alpha: 0.78),
          ),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(GtexSpacing.radiusPill),
          borderSide: const BorderSide(color: GtexColors.pitch, width: 1.4),
        ),
      ),
    );
  }
}
