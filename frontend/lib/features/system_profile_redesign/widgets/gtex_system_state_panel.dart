import 'package:flutter/material.dart';

import '../models/gtex_profile_models.dart';

class GtexSystemStatePanel extends StatelessWidget {
  const GtexSystemStatePanel({
    super.key,
    required this.spec,
    this.onPrimary,
    this.onSecondary,
  });

  final GtexSystemStateSpec spec;
  final VoidCallback? onPrimary;
  final VoidCallback? onSecondary;

  static const Color _bg = Color(0xFF07120D);
  static const Color _panel = Color(0xFF0D1C14);
  static const Color _line = Color(0xFF214232);
  static const Color _green = Color(0xFF39FF88);
  static const Color _gold = Color(0xFFFFC857);

  IconData get _icon => switch (spec.kind) {
        GtexSystemStateKind.loading => Icons.sync,
        GtexSystemStateKind.empty => Icons.inventory_2_outlined,
        GtexSystemStateKind.error => Icons.warning_amber_rounded,
        GtexSystemStateKind.offline => Icons.wifi_off_rounded,
        GtexSystemStateKind.accessDenied => Icons.lock_outline_rounded,
        GtexSystemStateKind.maintenance => Icons.construction_rounded,
        GtexSystemStateKind.success => Icons.check_circle_outline_rounded,
      };

  Color get _accent => switch (spec.kind) {
        GtexSystemStateKind.error => Colors.redAccent,
        GtexSystemStateKind.accessDenied => _gold,
        GtexSystemStateKind.maintenance => _gold,
        GtexSystemStateKind.success => _green,
        _ => _green,
      };

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: _bg,
        borderRadius: BorderRadius.circular(28),
        border: Border.all(color: _line),
      ),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 56,
              height: 56,
              decoration: BoxDecoration(
                color: _panel,
                shape: BoxShape.circle,
                border: Border.all(color: _accent.withOpacity(.7)),
              ),
              child: Icon(_icon, color: _accent, size: 28),
            ),
            const SizedBox(height: 20),
            Text(
              spec.title,
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: 8),
            Text(
              spec.message,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.white70,
                    height: 1.4,
                  ),
            ),
            const SizedBox(height: 22),
            Wrap(
              spacing: 12,
              children: [
                FilledButton(
                  style: FilledButton.styleFrom(
                    backgroundColor: _green,
                    foregroundColor: Colors.black,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                  ),
                  onPressed: onPrimary,
                  child: Text(spec.primaryActionLabel),
                ),
                if (spec.secondaryActionLabel != null)
                  OutlinedButton(
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.white,
                      side: const BorderSide(color: _line),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                    ),
                    onPressed: onSecondary,
                    child: Text(spec.secondaryActionLabel!),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
