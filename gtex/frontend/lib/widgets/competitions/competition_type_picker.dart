import 'package:flutter/material.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class CompetitionTypePicker extends StatelessWidget {
  const CompetitionTypePicker({
    super.key,
    required this.value,
    required this.onChanged,
  });

  final CompetitionFormat value;
  final ValueChanged<CompetitionFormat> onChanged;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: <Widget>[
        Expanded(
          child: _FormatCard(
            icon: Icons.view_list_outlined,
            title: 'Skill league',
            subtitle:
                'Best for longer community competitions with standings and tie-breakers.',
            selected: value == CompetitionFormat.league,
            onTap: () => onChanged(CompetitionFormat.league),
          ),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: _FormatCard(
            icon: Icons.account_tree_outlined,
            title: 'Skill cup',
            subtitle:
                'Best for knockout creator competitions with clean bracket progression.',
            selected: value == CompetitionFormat.cup,
            onTap: () => onChanged(CompetitionFormat.cup),
          ),
        ),
      ],
    );
  }
}

class _FormatCard extends StatelessWidget {
  const _FormatCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.selected,
    required this.onTap,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      emphasized: selected,
      onTap: onTap,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Icon(
                icon,
                color: selected ? GteShellTheme.accent : GteShellTheme.textMuted,
              ),
              const Spacer(),
              if (selected)
                const Icon(
                  Icons.check_circle,
                  color: GteShellTheme.accent,
                ),
            ],
          ),
          const SizedBox(height: 16),
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Text(
            subtitle,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        ],
      ),
    );
  }
}
