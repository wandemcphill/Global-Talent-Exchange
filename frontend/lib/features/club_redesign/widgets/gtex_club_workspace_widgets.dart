import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

import '../models/gtex_club_redesign_models.dart';
import '../presentation/gtex_club_workspace_controller.dart';

class GtexClubHero extends StatelessWidget {
  const GtexClubHero({
    super.key,
    required this.snapshot,
    required this.ownerFacing,
    this.isFollowing = false,
    this.onFollow,
    this.onBuyShares,
  });

  final GtexClubWorkspaceSnapshot snapshot;
  final bool ownerFacing;
  final bool isFollowing;
  final VoidCallback? onFollow;
  final VoidCallback? onBuyShares;

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      accent: GtexColors.pitch,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                _ClubBadge(shortCode: snapshot.shortCode),
                const SizedBox(width: GtexSpacing.md),
                Flexible(
                  fit: FlexFit.loose,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        snapshot.clubName,
                        style: Theme.of(
                          context,
                        ).textTheme.headlineSmall?.copyWith(
                          color: GtexColors.text,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      const SizedBox(height: GtexSpacing.xxs),
                      Text(
                        '${snapshot.country} - ${snapshot.division}',
                        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: GtexColors.textMuted,
                        ),
                      ),
                      const SizedBox(height: GtexSpacing.sm),
                      Wrap(
                        spacing: GtexSpacing.xs,
                        runSpacing: GtexSpacing.xs,
                        children: snapshot.identityTags
                            .map(
                              (String tag) => GtexStatusChip(
                                label: tag,
                                color: GtexColors.pitch,
                              ),
                            )
                            .toList(growable: false),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: GtexSpacing.lg),
          Wrap(
            spacing: GtexSpacing.sm,
            runSpacing: GtexSpacing.sm,
            children: <Widget>[
              SizedBox(
                width: 210,
                child: GtexMetricTile(
                  label: 'Club value',
                  value: gtexFormatCredits(snapshot.totalClubValueCredits),
                  icon: Icons.account_balance_wallet_outlined,
                  accent: GtexColors.pitch,
                ),
              ),
              SizedBox(
                width: 190,
                child: GtexMetricTile(
                  label: 'Followers',
                  value: '${snapshot.followers}',
                  icon: Icons.groups_2_outlined,
                  accent: GtexColors.pitch,
                ),
              ),
              SizedBox(
                width: 190,
                child: GtexMetricTile(
                  label: 'Shareholders',
                  value: '${snapshot.shareholders}',
                  icon: Icons.stacked_line_chart,
                  accent: GtexColors.gold,
                ),
              ),
            ],
          ),
          if (!ownerFacing) ...<Widget>[
            const SizedBox(height: GtexSpacing.lg),
            Wrap(
              spacing: GtexSpacing.sm,
              runSpacing: GtexSpacing.sm,
              children: <Widget>[
                GtexActionButton(
                  label: isFollowing ? 'Following' : 'Follow club',
                  icon:
                      isFollowing
                          ? Icons.notifications_active
                          : Icons.add_alert_outlined,
                  onPressed: onFollow,
                  accent: GtexColors.pitch,
                ),
                GtexActionButton(
                  label: 'Buy shares',
                  icon: Icons.ssid_chart_outlined,
                  onPressed: onBuyShares,
                  accent: GtexColors.gold,
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class GtexClubSectionList<T> extends StatelessWidget {
  const GtexClubSectionList({
    super.key,
    required this.items,
    required this.selected,
    required this.labelBuilder,
    required this.descriptionBuilder,
    required this.onSelected,
  });

  final List<T> items;
  final T selected;
  final String Function(T item) labelBuilder;
  final String Function(T item) descriptionBuilder;
  final ValueChanged<T> onSelected;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      itemCount: items.length,
      separatorBuilder: (_, __) => const SizedBox(height: GtexSpacing.xs),
      itemBuilder: (BuildContext context, int index) {
        final T item = items[index];
        return GtexPanel(
          isSelected: item == selected,
          accent: GtexColors.pitch,
          padding: const EdgeInsets.all(GtexSpacing.sm),
          onTap: () => onSelected(item),
          child: Row(
            children: <Widget>[
              Container(
                width: 34,
                height: 34,
                decoration: BoxDecoration(
                  color: GtexColors.pitch.withValues(
                    alpha: item == selected ? 0.2 : 0.08,
                  ),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  _iconFor(labelBuilder(item)),
                  color:
                      item == selected
                          ? GtexColors.pitch
                          : GtexColors.textMuted,
                  size: 18,
                ),
              ),
              const SizedBox(width: GtexSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      labelBuilder(item),
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        color: GtexColors.text,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    Text(
                      descriptionBuilder(item),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: GtexColors.textMuted,
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

  IconData _iconFor(String label) {
    final String normalized = label.toLowerCase();
    if (normalized.contains('squad')) return Icons.groups_2_outlined;
    if (normalized.contains('transfer')) return Icons.swap_horiz_outlined;
    if (normalized.contains('finance') || normalized.contains('share')) {
      return Icons.account_balance_wallet_outlined;
    }
    if (normalized.contains('competition')) return Icons.emoji_events_outlined;
    if (normalized.contains('identity')) return Icons.shield_outlined;
    if (normalized.contains('troph')) return Icons.workspace_premium_outlined;
    if (normalized.contains('news')) return Icons.newspaper_outlined;
    if (normalized.contains('order')) return Icons.receipt_long_outlined;
    if (normalized.contains('community')) return Icons.forum_outlined;
    return Icons.dashboard_customize_outlined;
  }
}

class GtexClubSquadList extends StatelessWidget {
  const GtexClubSquadList({super.key, required this.squad});

  final List<GtexClubMember> squad;

  @override
  Widget build(BuildContext context) {
    if (squad.isEmpty) {
      return const GtexEmptyState(
        title: 'No squad players loaded',
        message:
            'Owned players will appear here when the live club squad endpoint returns them.',
        icon: Icons.groups_2_outlined,
      );
    }
    return Column(
      children: squad
          .map(
            (GtexClubMember member) => Padding(
              padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
              child: GtexPanel(
                padding: const EdgeInsets.all(GtexSpacing.sm),
                accent: member.isRegen ? GtexColors.gold : GtexColors.pitch,
                child: Row(
                  children: <Widget>[
                    CircleAvatar(
                      radius: 22,
                      backgroundColor: (member.isRegen
                              ? GtexColors.gold
                              : GtexColors.pitch)
                          .withValues(alpha: 0.16),
                      backgroundImage:
                          member.imageUrl == null
                              ? null
                              : NetworkImage(member.imageUrl!),
                      child:
                          member.imageUrl == null
                              ? Text(
                                member.name.substring(0, 1).toUpperCase(),
                                style: const TextStyle(
                                  fontWeight: FontWeight.w900,
                                ),
                              )
                              : null,
                    ),
                    const SizedBox(width: GtexSpacing.sm),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(
                            member.name,
                            style: Theme.of(
                              context,
                            ).textTheme.titleSmall?.copyWith(
                              color: GtexColors.text,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                          Text(
                            '${member.position} - ${member.nationality}',
                            style: Theme.of(context).textTheme.bodySmall
                                ?.copyWith(color: GtexColors.textMuted),
                          ),
                        ],
                      ),
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: <Widget>[
                        Text(
                          member.rating.toStringAsFixed(1),
                          style: Theme.of(
                            context,
                          ).textTheme.titleMedium?.copyWith(
                            color: GtexColors.text,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                        Text(
                          gtexFormatCredits(member.valueCredits),
                          style: Theme.of(context).textTheme.bodySmall
                              ?.copyWith(color: GtexColors.textMuted),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          )
          .toList(growable: false),
    );
  }
}

class GtexClubNewsList extends StatelessWidget {
  const GtexClubNewsList({super.key, required this.news});

  final List<GtexClubNewsItem> news;

  @override
  Widget build(BuildContext context) {
    if (news.isEmpty) {
      return const GtexEmptyState(
        title: 'No club news yet',
        message:
            'AI newsroom mentions will appear here when live club stories are available.',
        icon: Icons.newspaper_outlined,
      );
    }
    return Column(
      children: news
          .map(
            (GtexClubNewsItem item) => Padding(
              padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
              child: GtexPanel(
                accent: GtexColors.pitch,
                title: item.headline,
                subtitle: '${item.category} - ${item.timestampLabel}',
                child: Text(
                  item.summary,
                  style: Theme.of(
                    context,
                  ).textTheme.bodyMedium?.copyWith(color: GtexColors.textMuted),
                ),
              ),
            ),
          )
          .toList(growable: false),
    );
  }
}

class GtexClubTrophyGrid extends StatelessWidget {
  const GtexClubTrophyGrid({super.key, required this.trophies});

  final List<GtexClubTrophy> trophies;

  @override
  Widget build(BuildContext context) {
    if (trophies.isEmpty) {
      return const GtexEmptyState(
        title: 'No trophies recorded',
        message:
            'The trophy cabinet will populate from the live club honors endpoint.',
        icon: Icons.emoji_events_outlined,
      );
    }
    return Wrap(
      spacing: GtexSpacing.sm,
      runSpacing: GtexSpacing.sm,
      children: trophies
          .map(
            (GtexClubTrophy trophy) => SizedBox(
              width: 220,
              child: GtexPanel(
                accent: GtexColors.gold,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    const Icon(
                      Icons.emoji_events_outlined,
                      color: GtexColors.gold,
                      size: 34,
                    ),
                    const SizedBox(height: GtexSpacing.sm),
                    Text(
                      trophy.title,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: GtexColors.text,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    Text(
                      '${trophy.season} - ${trophy.tier}',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: GtexColors.textMuted,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          )
          .toList(growable: false),
    );
  }
}

class GtexClubRightRail extends StatelessWidget {
  const GtexClubRightRail({
    super.key,
    required this.snapshot,
    this.ownerFacing = true,
    this.onBuyShares,
  });

  final GtexClubWorkspaceSnapshot snapshot;
  final bool ownerFacing;
  final VoidCallback? onBuyShares;

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: <Widget>[
        GtexPanel(
          title: ownerFacing ? 'Owner actions' : 'Club investment',
          subtitle:
              ownerFacing
                  ? 'Fast routes for running this club.'
                  : 'Follow the club and buy into its growth.',
          accent: GtexColors.pitch,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              GtexActionButton(
                label:
                    ownerFacing ? 'Open player market' : 'Follow club updates',
                icon:
                    ownerFacing
                        ? Icons.shopping_basket_outlined
                        : Icons.notifications_active_outlined,
                onPressed: () {},
                accent: GtexColors.pitch,
              ),
              const SizedBox(height: GtexSpacing.sm),
              GtexActionButton(
                label: ownerFacing ? 'Review orders' : 'Buy shares',
                icon:
                    ownerFacing
                        ? Icons.receipt_long_outlined
                        : Icons.ssid_chart_outlined,
                onPressed: onBuyShares,
                accent: GtexColors.gold,
              ),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Latest activity',
          accent: GtexColors.pitch,
          child: Column(
            children: snapshot.activity
                .map(
                  (String item) => Padding(
                    padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
                    child: Row(
                      children: <Widget>[
                        const Icon(
                          Icons.bolt_outlined,
                          color: GtexColors.pitch,
                          size: 18,
                        ),
                        const SizedBox(width: GtexSpacing.xs),
                        Expanded(
                          child: Text(
                            item,
                            style: Theme.of(context).textTheme.bodySmall
                                ?.copyWith(color: GtexColors.textMuted),
                          ),
                        ),
                      ],
                    ),
                  ),
                )
                .toList(growable: false),
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Open orders',
          accent: GtexColors.gold,
          child: Column(
            children: snapshot.orders
                .map(
                  (GtexClubOrderItem order) => Padding(
                    padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
                    child: Row(
                      children: <Widget>[
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Text(
                                order.title,
                                style: const TextStyle(
                                  color: GtexColors.text,
                                  fontWeight: FontWeight.w800,
                                ),
                              ),
                              Text(
                                order.status,
                                style: const TextStyle(
                                  color: GtexColors.textMuted,
                                ),
                              ),
                            ],
                          ),
                        ),
                        Text(
                          gtexFormatCredits(order.amountCredits),
                          style: const TextStyle(
                            color: GtexColors.gold,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                      ],
                    ),
                  ),
                )
                .toList(growable: false),
          ),
        ),
      ],
    );
  }
}

class _ClubBadge extends StatelessWidget {
  const _ClubBadge({required this.shortCode});

  final String shortCode;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 84,
      height: 96,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[
            GtexColors.pitch.withValues(alpha: 0.95),
            GtexColors.panelStrong,
            GtexColors.gold.withValues(alpha: 0.82),
          ],
        ),
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(30),
          topRight: Radius.circular(30),
          bottomLeft: Radius.circular(40),
          bottomRight: Radius.circular(40),
        ),
        border: Border.all(color: GtexColors.text.withValues(alpha: 0.12)),
        boxShadow: <BoxShadow>[
          GtexColors.glow(GtexColors.pitch, opacity: 0.24),
        ],
      ),
      child: Center(
        child: Text(
          shortCode,
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
            color: Colors.black,
            fontWeight: FontWeight.w900,
            letterSpacing: 1.2,
          ),
        ),
      ),
    );
  }
}
