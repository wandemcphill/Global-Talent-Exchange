import 'package:flutter/material.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

enum MajorHonorBadgeStyle {
  major,
  elite,
  academy,
  world,
}

class MajorHonorBadge extends StatelessWidget {
  const MajorHonorBadge({
    super.key,
    required this.label,
    this.style = MajorHonorBadgeStyle.major,
  });

  final String label;
  final MajorHonorBadgeStyle style;

  @override
  Widget build(BuildContext context) {
    final _BadgePalette palette = _paletteFor(style);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        gradient: LinearGradient(
          colors: <Color>[
            palette.start,
            palette.end,
          ],
        ),
        border: Border.all(color: palette.stroke),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(palette.icon, size: 14, color: palette.foreground),
          const SizedBox(width: 6),
          Text(
            label,
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: palette.foreground,
                  fontSize: 11,
                ),
          ),
        ],
      ),
    );
  }

  _BadgePalette _paletteFor(MajorHonorBadgeStyle style) {
    switch (style) {
      case MajorHonorBadgeStyle.major:
        return const _BadgePalette(
          start: Color(0x1F7DE2D1),
          end: Color(0x1A7DE2D1),
          stroke: Color(0x557DE2D1),
          foreground: GteShellTheme.accent,
          icon: Icons.workspace_premium,
        );
      case MajorHonorBadgeStyle.elite:
        return const _BadgePalette(
          start: Color(0x33FFC76B),
          end: Color(0x14F4F7FB),
          stroke: Color(0x88FFC76B),
          foreground: GteShellTheme.accentWarm,
          icon: Icons.emoji_events,
        );
      case MajorHonorBadgeStyle.academy:
        return const _BadgePalette(
          start: Color(0x1F73F7AF),
          end: Color(0x146DE7B1),
          stroke: Color(0x6673F7AF),
          foreground: GteShellTheme.positive,
          icon: Icons.school,
        );
      case MajorHonorBadgeStyle.world:
        return const _BadgePalette(
          start: Color(0x4DFFD27F),
          end: Color(0x1AFEF7E0),
          stroke: Color(0x99FFD27F),
          foreground: GteShellTheme.accentWarm,
          icon: Icons.public,
        );
    }
  }
}

class _BadgePalette {
  const _BadgePalette({
    required this.start,
    required this.end,
    required this.stroke,
    required this.foreground,
    required this.icon,
  });

  final Color start;
  final Color end;
  final Color stroke;
  final Color foreground;
  final IconData icon;
}
