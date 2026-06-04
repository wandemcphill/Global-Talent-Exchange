import 'package:flutter/material.dart';

class GtexHiddenControlsOverlay extends StatelessWidget {
  const GtexHiddenControlsOverlay({
    super.key,
    required this.visible,
    required this.onSyncFrame,
    required this.onOpenHighlights,
  });

  static const Key overlayKey = Key('gtex_hidden_controls_overlay');

  final bool visible;
  final VoidCallback onSyncFrame;
  final VoidCallback? onOpenHighlights;

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      ignoring: !visible,
      child: AnimatedOpacity(
        key: overlayKey,
        opacity: visible ? 1 : 0,
        duration: const Duration(milliseconds: 180),
        child: Align(
          alignment: Alignment.bottomCenter,
          child: Padding(
            padding: const EdgeInsets.only(bottom: 22),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              decoration: BoxDecoration(
                color: const Color(0xDD08121C),
                borderRadius: BorderRadius.circular(999),
                border: Border.all(color: Colors.white.withValues(alpha: 0.14)),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  const _StatusPill(
                    icon: Icons.sensors_rounded,
                    label: 'Frame live',
                  ),
                  const SizedBox(width: 10),
                  _ControlChip(
                    icon: Icons.sync_rounded,
                    label: 'Sync',
                    onTap: onSyncFrame,
                  ),
                  if (onOpenHighlights != null) ...<Widget>[
                    const SizedBox(width: 10),
                    _ControlChip(
                      icon: Icons.video_library_rounded,
                      label: 'Highlights',
                      onTap: onOpenHighlights!,
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _StatusPill extends StatelessWidget {
  const _StatusPill({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Icon(icon, color: const Color(0xFF22C55E), size: 20),
            const SizedBox(width: 6),
            Text(
              label,
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ControlChip extends StatelessWidget {
  const _ControlChip({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(999),
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Icon(icon, color: Colors.white, size: 20),
            const SizedBox(width: 6),
            Text(
              label,
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
