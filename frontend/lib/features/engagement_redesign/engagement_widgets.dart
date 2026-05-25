import 'package:flutter/material.dart';

import '../../ui_gtex/ui_gtex.dart';
import 'engagement_models.dart';

Color notificationColor(GtexNotificationKind kind) {
  switch (kind) {
    case GtexNotificationKind.transfers:
      return GtexColors.pitch;
    case GtexNotificationKind.matches:
      return GtexColors.cyan;
    case GtexNotificationKind.market:
      return GtexColors.pitch;
    case GtexNotificationKind.traders:
      return GtexColors.coinGtex;
    case GtexNotificationKind.club:
      return GtexColors.cyan;
    case GtexNotificationKind.competition:
      return GtexColors.gold;
    case GtexNotificationKind.regen:
      return GtexColors.purple;
    case GtexNotificationKind.wallet:
      return GtexColors.mint;
    case GtexNotificationKind.gifts:
      return GtexColors.coinFan;
    case GtexNotificationKind.kyc:
      return GtexColors.cyan;
    case GtexNotificationKind.dispute:
      return GtexColors.red;
    case GtexNotificationKind.jackpot:
      return GtexColors.gold;
    case GtexNotificationKind.system:
      return GtexColors.textSecondary;
  }
}

Color newsCategoryColor(GtexNewsCategory category) {
  switch (category) {
    case GtexNewsCategory.breaking:
      return GtexColors.red;
    case GtexNewsCategory.transfers:
      return GtexColors.pitch;
    case GtexNewsCategory.clubs:
      return GtexColors.cyan;
    case GtexNewsCategory.regens:
      return GtexColors.purple;
    case GtexNewsCategory.awards:
      return GtexColors.gold;
    case GtexNewsCategory.tournaments:
      return GtexColors.orange;
    case GtexNewsCategory.nationalTeams:
      return GtexColors.mint;
    case GtexNewsCategory.jackpot:
      return GtexColors.gold;
    case GtexNewsCategory.market:
      return GtexColors.pitchDeep;
    case GtexNewsCategory.creators:
      return GtexColors.purple;
    case GtexNewsCategory.disputes:
      return GtexColors.red;
  }
}

class GtexSectionListTile extends StatelessWidget {
  const GtexSectionListTile({
    super.key,
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.isSelected,
    required this.onTap,
    this.trailing,
    this.accent = GtexColors.pitch,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final bool isSelected;
  final VoidCallback onTap;
  final Widget? trailing;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      margin: const EdgeInsets.only(bottom: GtexSpacing.sm),
      padding: const EdgeInsets.all(GtexSpacing.sm),
      isSelected: isSelected,
      accent: accent,
      onTap: onTap,
      child: Row(
        children: <Widget>[
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: accent.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
              border: Border.all(color: accent.withValues(alpha: 0.35)),
            ),
            child: Icon(icon, color: accent),
          ),
          const SizedBox(width: GtexSpacing.sm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                    color: GtexColors.text,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  subtitle,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(
                    context,
                  ).textTheme.bodySmall?.copyWith(color: GtexColors.textMuted),
                ),
              ],
            ),
          ),
          if (trailing != null) ...<Widget>[
            const SizedBox(width: GtexSpacing.xs),
            trailing!,
          ],
        ],
      ),
    );
  }
}

class GtexArticleHero extends StatelessWidget {
  const GtexArticleHero({super.key, required this.article});

  final GtexNewsArticle article;

  @override
  Widget build(BuildContext context) {
    final Color accent = newsCategoryColor(article.category);
    return Container(
      padding: const EdgeInsets.all(GtexSpacing.lg),
      decoration: BoxDecoration(
        gradient: GtexColors.panelGlow(accent: accent),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusXl),
        border: Border.all(color: accent.withValues(alpha: 0.38)),
        boxShadow: <BoxShadow>[GtexColors.glow(accent, opacity: 0.16)],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Wrap(
            spacing: GtexSpacing.xs,
            runSpacing: GtexSpacing.xs,
            children: <Widget>[
              GtexStatusChip(
                label: article.categoryLabel,
                color: accent,
                icon: Icons.newspaper_outlined,
              ),
              if (article.isBreaking)
                const GtexStatusChip(
                  label: 'LIVE STORY',
                  color: GtexColors.red,
                  icon: Icons.bolt_outlined,
                ),
              GtexStatusChip(
                label: 'TRUST ${(article.trustScore * 100).round()}%',
                color: GtexColors.cyan,
                icon: Icons.verified_outlined,
              ),
            ],
          ),
          const SizedBox(height: GtexSpacing.lg),
          Text(
            article.title,
            style: Theme.of(context).textTheme.headlineMedium?.copyWith(
              color: GtexColors.text,
              fontWeight: FontWeight.w900,
              height: 1.05,
            ),
          ),
          const SizedBox(height: GtexSpacing.sm),
          Text(
            article.summary,
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              color: GtexColors.textSecondary,
              height: 1.35,
            ),
          ),
          const SizedBox(height: GtexSpacing.lg),
          Text(
            article.body,
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(
              color: GtexColors.textSecondary,
              height: 1.55,
            ),
          ),
          const SizedBox(height: GtexSpacing.lg),
          GtexReactionBar(
            reactionCount: article.reactionCount,
            commentCount: article.commentCount,
            accent: accent,
          ),
        ],
      ),
    );
  }
}

class GtexReactionBar extends StatelessWidget {
  const GtexReactionBar({
    super.key,
    required this.reactionCount,
    required this.commentCount,
    this.accent = GtexColors.pitch,
    this.onReact,
  });

  final int reactionCount;
  final int commentCount;
  final Color accent;
  final VoidCallback? onReact;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: GtexSpacing.xs,
      runSpacing: GtexSpacing.xs,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: <Widget>[
        GtexStatusChip(
          label: '$reactionCount reactions',
          color: accent,
          icon: Icons.sports_soccer_outlined,
        ),
        GtexStatusChip(
          label: '$commentCount comments',
          color: GtexColors.cyan,
          icon: Icons.chat_bubble_outline,
        ),
        if (onReact == null)
          const GtexStatusChip(
            label: 'BACKEND OWNED',
            color: GtexColors.textSecondary,
            icon: Icons.lock_outline,
          )
        else
          TextButton.icon(
            onPressed: onReact,
            icon: const Icon(Icons.add_reaction_outlined),
            label: const Text('React'),
          ),
      ],
    );
  }
}
