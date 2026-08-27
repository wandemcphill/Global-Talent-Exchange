import 'package:flutter/material.dart';

import '../../../ui_gtex/football/gtex_player_card.dart';
import '../../../widgets/gte_shell_theme.dart';
import '../../../widgets/gte_surface_panel.dart';
import '../data/gtex_ui_demo_data.dart';
import 'gtex_ui_primitives.dart';

class GtexStoryCard extends StatelessWidget {
  const GtexStoryCard({super.key, required this.story, this.onTap});

  final GtexStoryCardData story;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return SizedBox(
      width: 220,
      child: GteSurfacePanel(
        accentColor: tokens.accentArena,
        onTap: onTap,
        padding: const EdgeInsets.all(16),
        child: SingleChildScrollView(
          physics: const NeverScrollableScrollPhysics(),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              GtexBadgeIcon(label: story.kicker, color: tokens.accentArena),
              const SizedBox(height: 16),
              Text(story.title, style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 8),
              Text(
                story.subtitle,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class GtexTaskCard extends StatelessWidget {
  const GtexTaskCard({super.key, required this.task, required this.onClaim});

  final GtexTaskData task;
  final VoidCallback onClaim;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return GteSurfacePanel(
      accentColor: tokens.accentCapital,
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Text(
                  task.title,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
              GtexBadgeIcon(
                label: task.rewardLabel,
                color: tokens.accentCapital,
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(task.detail, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 12),
          GtexStatBar(
            label: 'Progress',
            value: '${(task.progress * 100).round()}%',
            progress: task.progress,
            color: tokens.accentCapital,
          ),
          const SizedBox(height: 14),
          Align(
            alignment: Alignment.centerRight,
            child:
                task.isClaimed
                    ? FilledButton.tonal(
                      onPressed: null,
                      child: const Text('Claimed'),
                    )
                    : FilledButton(
                      onPressed: onClaim,
                      child: const Text('Claim'),
                    ),
          ),
        ],
      ),
    );
  }
}

class GtexTransferAlertTile extends StatelessWidget {
  const GtexTransferAlertTile({super.key, required this.alert});

  final GtexTransferAlertData alert;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: tokens.panelStrong.withValues(alpha: 0.72),
        border: Border.all(color: tokens.stroke.withValues(alpha: 0.72)),
      ),
      child: Row(
        children: <Widget>[
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14),
              color: tokens.accentWarm.withValues(alpha: 0.16),
            ),
            child: Icon(
              Icons.notifications_active_outlined,
              color: tokens.accentWarm,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  alert.title,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 4),
                Text(
                  alert.summary,
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          GtexBadgeIcon(label: alert.tag, color: tokens.accentWarm),
        ],
      ),
    );
  }
}

class GtexPlayerTile extends StatelessWidget {
  const GtexPlayerTile({
    super.key,
    required this.player,
    required this.onOpen,
    this.onBid,
  });

  final GtexPlayerCardData player;
  final VoidCallback onOpen;
  final VoidCallback? onBid;

  @override
  Widget build(BuildContext context) {
    return GtexPlayerCard(
      name: player.name,
      position: player.position,
      clubName: player.clubName,
      nationality: player.country,
      priceLabel: gtexCompactCurrency(player.price),
      ratingLabel: '${player.rating}',
      potentialLabel: '${player.potential}',
      ageLabel: '${player.age}',
      gsiLabel: '${player.rating}',
      gsiTierLabel: player.potential >= 90 ? 'S Tier' : 'A Tier',
      gsiTrendLabel: '+2.4%',
      rarityLabel: player.potential >= 92 ? 'Elite' : 'Standard',
      marketHeatLabel: player.liquidityLabel,
      cardVariant: GtexPlayerCardVariant.standard,
      scale: GtexPlayerCardScale.full,
      onTap: onOpen,
      onBuyNow: onBid ?? onOpen,
      buyNowLabel: 'Bid',
      onAddToShortlist: () {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('${player.name} added to Watchlist')),
        );
      },
    );
  }
}

class GtexRegenCard extends StatelessWidget {
  const GtexRegenCard({super.key, required this.player, required this.onOpen});

  final GtexPlayerCardData player;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    return GtexPlayerCard(
      name: player.name,
      position: player.position,
      clubName: player.clubName,
      nationality: player.country,
      priceLabel: gtexCompactCurrency(player.price),
      ratingLabel: '${player.rating}',
      potentialLabel: '${player.potential}',
      ageLabel: '${player.age}',
      gsiLabel: '${player.potential}',
      gsiTierLabel: player.potential >= 90 ? 'GEN-1 ELITE' : 'GEN-1 PROSPECT',
      gsiTrendLabel: '↑ Rising',
      rarityLabel: player.potential >= 90 ? 'LEGENDARY REGEN' : 'REGEN PROSPECT',
      marketHeatLabel: 'HIGH POTENTIAL',
      cardVariant: GtexPlayerCardVariant.holographic,
      scale: GtexPlayerCardScale.full,
      onTap: onOpen,
      onBuyNow: onOpen,
      buyNowLabel: 'Inspect',
    );
  }
}

class GtexTournamentCard extends StatelessWidget {
  const GtexTournamentCard({
    super.key,
    required this.tournament,
    required this.onJoin,
  });

  final GtexTournamentCardData tournament;
  final VoidCallback onJoin;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return GteSurfacePanel(
      accentColor: tokens.accentArena,
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Container(
            height: 110,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(22),
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: <Color>[
                  tokens.accentArena.withValues(alpha: 0.82),
                  tokens.accent.withValues(alpha: 0.78),
                  tokens.panelElevated,
                ],
              ),
            ),
            child: Stack(
              children: <Widget>[
                Positioned.fill(
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(22),
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: <Color>[
                          Colors.transparent,
                          Colors.black.withValues(alpha: 0.22),
                        ],
                      ),
                    ),
                  ),
                ),
                Positioned(
                  left: 16,
                  bottom: 16,
                  child: Text(
                    tournament.themeLabel,
                    style: Theme.of(
                      context,
                    ).textTheme.titleLarge?.copyWith(color: tokens.textInverse),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Text(tournament.name, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Text(
            tournament.rewardLabel,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 12),
          Row(
            children: <Widget>[
              Expanded(
                child: GtexBadgeIcon(
                  label: tournament.status,
                  color: tokens.accentArena,
                ),
              ),
              FilledButton(onPressed: onJoin, child: const Text('Join')),
            ],
          ),
        ],
      ),
    );
  }
}

class GtexFederationCard extends StatelessWidget {
  const GtexFederationCard({
    super.key,
    required this.federation,
    required this.onJoin,
  });

  final GtexFederationCardData federation;
  final VoidCallback onJoin;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return GteSurfacePanel(
      accentColor: tokens.accentCommunity,
      padding: const EdgeInsets.all(18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(federation.name, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Text(
            '${federation.memberCount} members',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: tokens.accentCommunity,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 10),
          Text(
            federation.rulesSummary,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 14),
          Align(
            alignment: Alignment.centerRight,
            child: FilledButton.tonal(
              onPressed: onJoin,
              child: const Text('Join'),
            ),
          ),
        ],
      ),
    );
  }
}

class GtexRecordCard extends StatelessWidget {
  const GtexRecordCard({super.key, required this.record});

  final GtexHistoryRecordData record;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: tokens.panelStrong.withValues(alpha: 0.72),
        border: Border.all(color: tokens.stroke.withValues(alpha: 0.72)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(record.title, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 6),
          Text(
            record.holder,
            style: Theme.of(
              context,
            ).textTheme.bodyMedium?.copyWith(color: tokens.accentWarm),
          ),
          const SizedBox(height: 6),
          Text(record.context, style: Theme.of(context).textTheme.bodySmall),
        ],
      ),
    );
  }
}
