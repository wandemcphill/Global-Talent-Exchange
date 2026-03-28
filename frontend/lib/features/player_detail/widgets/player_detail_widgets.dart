import 'package:flutter/material.dart';

import '../../../core/constants/app_breakpoints.dart';
import '../../../core/constants/app_spacing.dart';
import '../../../core/theme/app_colors.dart';
import '../../../core/utils/app_formatters.dart';
import '../../../core/widgets/gtex_surface_card.dart';
import '../../../shared/models/player.dart';
import '../../../shared/widgets/metric_pill.dart';

String playerDetailHeroTag(Player player) => 'player-detail-${player.id}';

bool isElitePlayer(Player player) {
  return player.rating >= 88 || player.potential >= 92;
}

class PlayerStoryBeat {
  const PlayerStoryBeat({
    required this.phase,
    required this.title,
    required this.description,
    required this.icon,
    this.highlight = false,
  });

  final String phase;
  final String title;
  final String description;
  final IconData icon;
  final bool highlight;
}

class PlayerCareerEntry {
  const PlayerCareerEntry({
    required this.period,
    required this.club,
    required this.summary,
    required this.statLine,
    this.current = false,
  });

  final String period;
  final String club;
  final String summary;
  final String statLine;
  final bool current;
}

enum PlayerOfferStatus { leading, active, watching, expiring }

extension PlayerOfferStatusPresentation on PlayerOfferStatus {
  String get label {
    return switch (this) {
      PlayerOfferStatus.leading => 'Leading offer',
      PlayerOfferStatus.active => 'Active',
      PlayerOfferStatus.watching => 'Watching',
      PlayerOfferStatus.expiring => 'Expiring',
    };
  }

  Color get color {
    return switch (this) {
      PlayerOfferStatus.leading => AppColors.primary,
      PlayerOfferStatus.active => AppColors.gold,
      PlayerOfferStatus.watching => AppColors.textSecondary,
      PlayerOfferStatus.expiring => AppColors.danger,
    };
  }

  IconData get icon {
    return switch (this) {
      PlayerOfferStatus.leading => Icons.workspace_premium_rounded,
      PlayerOfferStatus.active => Icons.gavel_rounded,
      PlayerOfferStatus.watching => Icons.visibility_rounded,
      PlayerOfferStatus.expiring => Icons.timer_off_rounded,
    };
  }
}

class PlayerMarketOffer {
  const PlayerMarketOffer({
    required this.club,
    required this.amountInMillions,
    required this.structure,
    required this.deadlineLabel,
    required this.status,
  });

  final String club;
  final double amountInMillions;
  final String structure;
  final String deadlineLabel;
  final PlayerOfferStatus status;
}

class PlayerAttribute {
  const PlayerAttribute({
    required this.label,
    required this.value,
    required this.caption,
  });

  final String label;
  final double value;
  final String caption;
}

class PlayerDetailHeader extends StatelessWidget {
  const PlayerDetailHeader({
    super.key,
    required this.player,
    required this.heroTag,
    required this.badges,
  });

  final Player player;
  final String heroTag;
  final List<String> badges;

  @override
  Widget build(BuildContext context) {
    final bool elite = isElitePlayer(player);

    return GtexSurfaceCard(
      glowColor: elite ? AppColors.gold : AppColors.primary,
      padding: const EdgeInsets.all(spacingLG),
      child: LayoutBuilder(
        builder: (BuildContext context, BoxConstraints constraints) {
          final bool wide = constraints.maxWidth >= AppBreakpoints.medium;
          final Widget avatar = _HeroAvatar(
            player: player,
            heroTag: heroTag,
            elite: elite,
          );

          final Widget identity = Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Wrap(
                spacing: spacingSM,
                runSpacing: spacingSM,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: <Widget>[
                  Text(
                    player.name,
                    style: Theme.of(context).textTheme.headlineMedium,
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: spacingSM,
                      vertical: spacingXS,
                    ),
                    decoration: BoxDecoration(
                      color:
                          elite
                              ? AppColors.gold.withValues(alpha: 0.14)
                              : AppColors.primary.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(999),
                      border: Border.all(
                        color: elite ? AppColors.gold : AppColors.primary,
                      ),
                    ),
                    child: Text(
                      'OVR ${player.rating}',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: elite ? AppColors.gold : AppColors.primary,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: spacingSM),
              Text(
                '${player.position} | ${player.country} | Age ${player.age}',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
              const SizedBox(height: spacingMD),
              Wrap(
                spacing: spacingSM,
                runSpacing: spacingSM,
                children:
                    badges
                        .map(
                          (String badge) => _BadgeChip(
                            label: badge,
                            highlighted:
                                elite &&
                                (badge == 'Elite' || badge == 'Wonderkid'),
                          ),
                        )
                        .toList(),
              ),
            ],
          );

          final Widget metrics = Wrap(
            spacing: spacingSM,
            runSpacing: spacingSM,
            children: <Widget>[
              MetricPill(
                label: 'Value',
                value: AppFormatters.money(player.valueInMillions),
                highlight: true,
              ),
              MetricPill(label: 'Potential', value: '${player.potential}'),
              MetricPill(
                label: 'Style',
                value: player.isHot ? 'Explosive' : 'Balanced',
              ),
            ],
          );

          if (wide) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: <Widget>[
                    avatar,
                    const SizedBox(width: spacingLG),
                    Expanded(child: identity),
                    const SizedBox(width: spacingLG),
                    SizedBox(width: 240, child: metrics),
                  ],
                ),
                const SizedBox(height: spacingLG),
                _HeaderSignalStrip(player: player, elite: elite),
              ],
            );
          }

          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Center(child: avatar),
              const SizedBox(height: spacingLG),
              identity,
              const SizedBox(height: spacingMD),
              metrics,
              const SizedBox(height: spacingLG),
              _HeaderSignalStrip(player: player, elite: elite),
            ],
          );
        },
      ),
    );
  }
}

class PlayerDetailTabBar extends StatelessWidget {
  const PlayerDetailTabBar({super.key, required this.controller});

  final TabController controller;

  @override
  Widget build(BuildContext context) {
    final bool isScrollable =
        MediaQuery.sizeOf(context).width < AppBreakpoints.compact;

    return Container(
      padding: const EdgeInsets.all(spacingSM),
      decoration: BoxDecoration(
        color: AppColors.card.withValues(alpha: 0.94),
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: AppColors.divider),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.18),
            blurRadius: 20,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: TabBar(
        controller: controller,
        isScrollable: isScrollable,
        tabAlignment: isScrollable ? TabAlignment.start : TabAlignment.fill,
        dividerColor: Colors.transparent,
        overlayColor: const WidgetStatePropertyAll(Colors.transparent),
        indicator: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          gradient: LinearGradient(
            colors: <Color>[
              AppColors.primary.withValues(alpha: 0.18),
              AppColors.gold.withValues(alpha: 0.12),
            ],
          ),
          border: Border.all(color: AppColors.primary.withValues(alpha: 0.26)),
        ),
        labelColor: AppColors.textPrimary,
        unselectedLabelColor: AppColors.textSecondary,
        tabs: const <Tab>[
          Tab(key: Key('player-detail-tab-stats'), text: 'Stats'),
          Tab(key: Key('player-detail-tab-story'), text: 'Story'),
          Tab(key: Key('player-detail-tab-career'), text: 'Career'),
          Tab(key: Key('player-detail-tab-offers'), text: 'Offers'),
        ],
      ),
    );
  }
}

class PlayerStatsTab extends StatelessWidget {
  const PlayerStatsTab({
    super.key,
    required this.attributes,
    required this.bottomPadding,
  });

  final List<PlayerAttribute> attributes;
  final double bottomPadding;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      key: const Key('player-detail-stats-view'),
      padding: EdgeInsets.only(bottom: bottomPadding),
      physics: const BouncingScrollPhysics(
        parent: AlwaysScrollableScrollPhysics(),
      ),
      itemCount: attributes.length + 1,
      separatorBuilder: (_, _) => const SizedBox(height: spacingMD),
      itemBuilder: (BuildContext context, int index) {
        if (index == 0) {
          return GtexSurfaceCard(
            glowColor: AppColors.primary,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'Attribute Profile',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: spacingSM),
                Text(
                  'Core traits are animated into a match-readiness profile for quick scanning.',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          );
        }

        final PlayerAttribute attribute = attributes[index - 1];
        return GtexSurfaceCard(
          child: _AnimatedAttributeRow(attribute: attribute),
        );
      },
    );
  }
}

class PlayerStoryTab extends StatelessWidget {
  const PlayerStoryTab({
    super.key,
    required this.storyBeats,
    required this.bottomPadding,
  });

  final List<PlayerStoryBeat> storyBeats;
  final double bottomPadding;

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      key: const Key('player-detail-story-view'),
      padding: EdgeInsets.only(bottom: bottomPadding),
      physics: const BouncingScrollPhysics(
        parent: AlwaysScrollableScrollPhysics(),
      ),
      itemCount: storyBeats.length,
      itemBuilder: (BuildContext context, int index) {
        final PlayerStoryBeat beat = storyBeats[index];
        final bool isLast = index == storyBeats.length - 1;

        return Padding(
          padding: const EdgeInsets.only(bottom: spacingMD),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              SizedBox(
                width: 44,
                child: Column(
                  children: <Widget>[
                    Container(
                      width: 36,
                      height: 36,
                      decoration: BoxDecoration(
                        color:
                            beat.highlight
                                ? AppColors.primary.withValues(alpha: 0.14)
                                : AppColors.surfaceMuted,
                        shape: BoxShape.circle,
                        border: Border.all(
                          color:
                              beat.highlight
                                  ? AppColors.primary
                                  : AppColors.divider,
                        ),
                      ),
                      child: Icon(
                        beat.icon,
                        color:
                            beat.highlight ? AppColors.primary : AppColors.gold,
                        size: 18,
                      ),
                    ),
                    if (!isLast)
                      Container(width: 2, height: 92, color: AppColors.divider),
                  ],
                ),
              ),
              const SizedBox(width: spacingMD),
              Expanded(
                child: GtexSurfaceCard(
                  glowColor: beat.highlight ? AppColors.primary : null,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      MetricPill(
                        label: 'Phase',
                        value: beat.phase,
                        highlight: beat.highlight,
                      ),
                      const SizedBox(height: spacingMD),
                      Text(
                        beat.title,
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: spacingSM),
                      Text(
                        beat.description,
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class PlayerCareerTab extends StatelessWidget {
  const PlayerCareerTab({
    super.key,
    required this.careerEntries,
    required this.bottomPadding,
  });

  final List<PlayerCareerEntry> careerEntries;
  final double bottomPadding;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      key: const Key('player-detail-career-view'),
      padding: EdgeInsets.only(bottom: bottomPadding),
      physics: const BouncingScrollPhysics(
        parent: AlwaysScrollableScrollPhysics(),
      ),
      itemCount: careerEntries.length,
      separatorBuilder: (_, _) => const SizedBox(height: spacingMD),
      itemBuilder: (BuildContext context, int index) {
        final PlayerCareerEntry entry = careerEntries[index];

        return GtexSurfaceCard(
          glowColor: entry.current ? AppColors.primary : null,
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Container(
                width: 78,
                padding: const EdgeInsets.all(spacingSM),
                decoration: BoxDecoration(
                  color:
                      entry.current
                          ? AppColors.primary.withValues(alpha: 0.14)
                          : AppColors.surfaceMuted.withValues(alpha: 0.82),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                    color:
                        entry.current ? AppColors.primary : AppColors.divider,
                  ),
                ),
                child: Column(
                  children: <Widget>[
                    const Icon(Icons.shield_rounded, color: AppColors.gold),
                    const SizedBox(height: spacingSM),
                    Text(
                      entry.period,
                      textAlign: TextAlign.center,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: spacingMD),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Wrap(
                      spacing: spacingSM,
                      runSpacing: spacingSM,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: <Widget>[
                        Text(
                          entry.club,
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        if (entry.current)
                          const MetricPill(
                            label: 'Status',
                            value: 'Current',
                            highlight: true,
                          ),
                      ],
                    ),
                    const SizedBox(height: spacingSM),
                    Text(
                      entry.summary,
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    const SizedBox(height: spacingMD),
                    Text(
                      entry.statLine,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: AppColors.gold,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class PlayerOffersTab extends StatelessWidget {
  const PlayerOffersTab({
    super.key,
    required this.offers,
    required this.bottomPadding,
  });

  final List<PlayerMarketOffer> offers;
  final double bottomPadding;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      key: const Key('player-detail-offers-view'),
      padding: EdgeInsets.only(bottom: bottomPadding),
      physics: const BouncingScrollPhysics(
        parent: AlwaysScrollableScrollPhysics(),
      ),
      itemCount: offers.length,
      separatorBuilder: (_, _) => const SizedBox(height: spacingMD),
      itemBuilder: (BuildContext context, int index) {
        final PlayerMarketOffer offer = offers[index];

        return GtexSurfaceCard(
          key: Key('player-detail-offer-$index'),
          glowColor:
              offer.status == PlayerOfferStatus.leading
                  ? AppColors.primary
                  : offer.status.color,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          offer.club,
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(height: spacingXS),
                        Text(
                          offer.structure,
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: spacingMD),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: spacingSM,
                      vertical: spacingXS,
                    ),
                    decoration: BoxDecoration(
                      color: offer.status.color.withValues(alpha: 0.14),
                      borderRadius: BorderRadius.circular(999),
                      border: Border.all(color: offer.status.color),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: <Widget>[
                        Icon(
                          offer.status.icon,
                          size: 14,
                          color: offer.status.color,
                        ),
                        const SizedBox(width: spacingXS),
                        Text(
                          offer.status.label,
                          style: Theme.of(
                            context,
                          ).textTheme.bodySmall?.copyWith(
                            color: offer.status.color,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: spacingMD),
              Text(
                AppFormatters.money(offer.amountInMillions),
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  color:
                      offer.status == PlayerOfferStatus.leading
                          ? AppColors.primary
                          : AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: spacingSM),
              Text(
                offer.deadlineLabel,
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _HeroAvatar extends StatelessWidget {
  const _HeroAvatar({
    required this.player,
    required this.heroTag,
    required this.elite,
  });

  final Player player;
  final String heroTag;
  final bool elite;

  @override
  Widget build(BuildContext context) {
    final ImageProvider<Object>? imageProvider = _resolveImage(player.image);
    final Widget avatar = AnimatedContainer(
      duration: const Duration(milliseconds: 280),
      width: 128,
      height: 128,
      padding: const EdgeInsets.all(spacingMD),
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[
            elite
                ? AppColors.gold.withValues(alpha: 0.2)
                : AppColors.primary.withValues(alpha: 0.18),
            AppColors.surfaceMuted,
            AppColors.card,
          ],
        ),
        border: Border.all(
          color: elite ? AppColors.gold : AppColors.primary,
          width: 1.4,
        ),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color:
                elite
                    ? AppColors.gold.withValues(alpha: 0.16)
                    : AppColors.primary.withValues(alpha: 0.14),
            blurRadius: 36,
            spreadRadius: 2,
          ),
        ],
      ),
      child: ClipOval(
        child:
            imageProvider == null
                ? Container(
                  color: AppColors.background,
                  alignment: Alignment.center,
                  child: Text(
                    player.name
                        .split(' ')
                        .where((String part) => part.isNotEmpty)
                        .take(2)
                        .map((String part) => part.substring(0, 1))
                        .join(),
                    style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      color: elite ? AppColors.gold : AppColors.primary,
                    ),
                  ),
                )
                : Image(image: imageProvider, fit: BoxFit.cover),
      ),
    );

    return Hero(tag: heroTag, child: avatar);
  }
}

class _HeaderSignalStrip extends StatelessWidget {
  const _HeaderSignalStrip({required this.player, required this.elite});

  final Player player;
  final bool elite;

  @override
  Widget build(BuildContext context) {
    final List<({String label, String value, Color color})> items =
        <({String label, String value, Color color})>[
          (
            label: 'Pace Pulse',
            value: '${(player.pace * 100).round()}',
            color: AppColors.primary,
          ),
          (
            label: 'Technique',
            value: '${(player.technique * 100).round()}',
            color: AppColors.gold,
          ),
          (
            label: 'Mentality',
            value: '${(player.mentality * 100).round()}',
            color: elite ? AppColors.gold : AppColors.primary,
          ),
        ];

    return Wrap(
      spacing: spacingMD,
      runSpacing: spacingMD,
      children:
          items
              .map(
                (({String label, String value, Color color}) item) => SizedBox(
                  width: 184,
                  child: Container(
                    padding: const EdgeInsets.all(spacingMD),
                    decoration: BoxDecoration(
                      color: item.color.withValues(alpha: 0.08),
                      borderRadius: BorderRadius.circular(cardRadius),
                      border: Border.all(
                        color: item.color.withValues(alpha: 0.24),
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          item.label,
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                        const SizedBox(height: spacingSM),
                        Text(
                          item.value,
                          style: Theme.of(context).textTheme.headlineSmall
                              ?.copyWith(color: item.color),
                        ),
                      ],
                    ),
                  ),
                ),
              )
              .toList(),
    );
  }
}

class _BadgeChip extends StatelessWidget {
  const _BadgeChip({required this.label, required this.highlighted});

  final String label;
  final bool highlighted;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: spacingSM,
        vertical: spacingXS,
      ),
      decoration: BoxDecoration(
        color:
            highlighted
                ? AppColors.gold.withValues(alpha: 0.14)
                : AppColors.surfaceMuted.withValues(alpha: 0.92),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(
          color: highlighted ? AppColors.gold : AppColors.divider,
        ),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.bodySmall?.copyWith(
          color: highlighted ? AppColors.gold : AppColors.textPrimary,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _AnimatedAttributeRow extends StatelessWidget {
  const _AnimatedAttributeRow({required this.attribute});

  final PlayerAttribute attribute;

  @override
  Widget build(BuildContext context) {
    final Color accent =
        attribute.value >= 0.85
            ? AppColors.gold
            : attribute.value >= 0.72
            ? AppColors.primary
            : AppColors.textSecondary;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: <Widget>[
            Expanded(
              child: Text(
                attribute.label,
                style: Theme.of(context).textTheme.titleLarge,
              ),
            ),
            const SizedBox(width: spacingSM),
            Text(
              '${(attribute.value * 100).round()}',
              style: Theme.of(
                context,
              ).textTheme.titleLarge?.copyWith(color: accent),
            ),
          ],
        ),
        const SizedBox(height: spacingSM),
        TweenAnimationBuilder<double>(
          tween: Tween<double>(begin: 0, end: attribute.value),
          duration: const Duration(milliseconds: 700),
          curve: Curves.easeOutCubic,
          builder: (BuildContext context, double value, Widget? child) {
            return ClipRRect(
              borderRadius: BorderRadius.circular(999),
              child: LinearProgressIndicator(
                value: value,
                minHeight: 10,
                backgroundColor: AppColors.surfaceMuted,
                valueColor: AlwaysStoppedAnimation<Color>(accent),
              ),
            );
          },
        ),
        const SizedBox(height: spacingSM),
        Text(
          attribute.caption,
          style: Theme.of(
            context,
          ).textTheme.bodySmall?.copyWith(color: AppColors.textSecondary),
        ),
      ],
    );
  }
}

ImageProvider<Object>? _resolveImage(String source) {
  if (source.startsWith('http')) {
    return NetworkImage(source);
  }
  if (source.isNotEmpty) {
    return AssetImage(source);
  }
  return null;
}
