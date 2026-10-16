import 'package:flutter/material.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/trophy_cabinet_dto.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/trophy_item_dto.dart';
import 'package:gte_frontend/features/club_identity/trophies/widgets/major_honor_badge.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class TrophyCategorySection extends StatelessWidget {
  const TrophyCategorySection({
    super.key,
    required this.categories,
    required this.title,
    required this.subtitle,
    this.badgeLabel,
    this.badgeStyle,
    this.emphasized = false,
    this.emptyMessage,
  });

  final List<TrophyCategoryDto> categories;
  final String title;
  final String subtitle;
  final String? badgeLabel;
  final MajorHonorBadgeStyle? badgeStyle;
  final bool emphasized;
  final String? emptyMessage;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      emphasized: emphasized,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Text(title,
                    style: Theme.of(context).textTheme.headlineSmall),
              ),
              if (badgeLabel != null)
                MajorHonorBadge(
                  label: badgeLabel!,
                  style: badgeStyle ?? MajorHonorBadgeStyle.major,
                ),
            ],
          ),
          const SizedBox(height: 8),
          Text(subtitle, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 18),
          if (categories.isEmpty)
            Text(
              emptyMessage ?? 'No honors archived in this wing yet.',
              style: Theme.of(context).textTheme.bodyMedium,
            )
          else
            LayoutBuilder(
              builder: (BuildContext context, BoxConstraints constraints) {
                final double itemWidth = constraints.maxWidth >= 860 ? 232 : 280;
                return Wrap(
                  spacing: 14,
                  runSpacing: 14,
                  children: categories.map((TrophyCategoryDto category) {
                    return SizedBox(
                      width: itemWidth,
                      child: _CategoryCard(category: category),
                    );
                  }).toList(growable: false),
                );
              },
            ),
        ],
      ),
    );
  }
}

class _CategoryCard extends StatelessWidget {
  const _CategoryCard({
    required this.category,
  });

  final TrophyCategoryDto category;

  @override
  Widget build(BuildContext context) {
    final bool isWorld = category.trophyType == 'world_super_cup';
    final Color accent = isWorld
        ? GteShellTheme.accentWarm
        : category.isEliteHonor
            ? GteShellTheme.accentWarm
            : category.isMajorHonor
                ? GteShellTheme.accent
                : category.teamScope.label == 'Academy'
                    ? GteShellTheme.positive
                    : GteShellTheme.textPrimary;
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(22),
        color: isWorld
            ? GteShellTheme.accentWarm.withValues(alpha: 0.08)
            : GteShellTheme.panelStrong.withValues(alpha: 0.8),
        border: Border.all(
          color: isWorld
              ? GteShellTheme.accentWarm.withValues(alpha: 0.6)
              : GteShellTheme.stroke,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Expanded(
                child: Text(
                  category.displayName,
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
              Text(
                '${category.count}x',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      color: accent,
                    ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: <Widget>[
              if (isWorld)
                const MajorHonorBadge(
                  label: 'World Crown',
                  style: MajorHonorBadgeStyle.world,
                )
              else if (category.isEliteHonor)
                const MajorHonorBadge(
                  label: 'Elite',
                  style: MajorHonorBadgeStyle.elite,
                )
              else if (category.isMajorHonor)
                const MajorHonorBadge(label: 'Major'),
              if (category.teamScope.label == 'Academy')
                const MajorHonorBadge(
                  label: 'Academy',
                  style: MajorHonorBadgeStyle.academy,
                ),
            ],
          ),
        ],
      ),
    );
  }
}
