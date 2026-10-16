import 'package:flutter/material.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

class CompetitionStatusBadge extends StatelessWidget {
  const CompetitionStatusBadge({
    super.key,
    required this.status,
  });

  final CompetitionStatus status;

  @override
  Widget build(BuildContext context) {
    final _StatusPalette palette = _paletteFor(status);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: palette.background,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: palette.stroke),
      ),
      child: Text(
        _labelFor(status),
        style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: palette.foreground,
            ),
      ),
    );
  }

  String _labelFor(CompetitionStatus value) {
    switch (value) {
      case CompetitionStatus.published:
        return 'Published';
      case CompetitionStatus.openForJoin:
        return 'Open for join';
      case CompetitionStatus.filled:
        return 'Filled';
      case CompetitionStatus.locked:
        return 'Locked';
      case CompetitionStatus.inProgress:
        return 'In progress';
      case CompetitionStatus.completed:
        return 'Completed';
      case CompetitionStatus.cancelled:
        return 'Cancelled';
      case CompetitionStatus.refunded:
        return 'Refunded';
      case CompetitionStatus.disputed:
        return 'Disputed';
      case CompetitionStatus.draft:
        return 'Draft';
    }
  }

  _StatusPalette _paletteFor(CompetitionStatus value) {
    switch (value) {
      case CompetitionStatus.openForJoin:
        return const _StatusPalette(
          background: Color(0x1A73F7AF),
          stroke: GteShellTheme.positive,
          foreground: GteShellTheme.positive,
        );
      case CompetitionStatus.filled:
      case CompetitionStatus.locked:
      case CompetitionStatus.inProgress:
        return const _StatusPalette(
          background: Color(0x1AFFC76B),
          stroke: GteShellTheme.accentWarm,
          foreground: GteShellTheme.accentWarm,
        );
      case CompetitionStatus.completed:
        return const _StatusPalette(
          background: Color(0x1A7DE2D1),
          stroke: GteShellTheme.accent,
          foreground: GteShellTheme.accent,
        );
      case CompetitionStatus.cancelled:
      case CompetitionStatus.refunded:
      case CompetitionStatus.disputed:
        return const _StatusPalette(
          background: Color(0x1AFF8B8B),
          stroke: GteShellTheme.negative,
          foreground: GteShellTheme.negative,
        );
      case CompetitionStatus.published:
        return const _StatusPalette(
          background: Color(0x142A3A56),
          stroke: GteShellTheme.stroke,
          foreground: GteShellTheme.textPrimary,
        );
      case CompetitionStatus.draft:
        return const _StatusPalette(
          background: Color(0x142A3A56),
          stroke: GteShellTheme.stroke,
          foreground: GteShellTheme.textMuted,
        );
    }
  }
}

class _StatusPalette {
  const _StatusPalette({
    required this.background,
    required this.stroke,
    required this.foreground,
  });

  final Color background;
  final Color stroke;
  final Color foreground;
}
