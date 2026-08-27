import 'package:flutter/material.dart';

import '../../../core/widgets/player_card.dart';
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
    final tokens = GteShellTheme.tokensOf(context);
    final Color accent =
        player.potential >= 92
            ? tokens.accentArena
            : player.rating >= 84
            ? tokens.accentClub
            : tokens.accent;
    return PlayerCard(
      name: player.name,
      rating: player.rating,
      image: '',
      position: player.position,
      subtitle: '${player.clubName} | ${player.country}',
      accentColor: accent,
      avatarSize: 64,
      layout: PlayerCardLayout.horizontal,
      onTap: onOpen,
      badgeLabels: <String>[
        player.position,
        player.country,
        ...player.badges.take(2),
      ],
      metrics: <PlayerCardMetric>[
        PlayerCardMetric(
          label: 'Value',
          value: gtexCompactCurrency(player.price),
        ),
        PlayerCardMetric(label: 'Potential', value: '${player.potential}'),
        PlayerCardMetric(label: 'Age', value: '${player.age}'),
        PlayerCardMetric(label: 'Liquidity', value: player.liquidityLabel),
      ],
      footer: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(player.bidStatus, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 6),
          Text(
            player.timerLabel,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: accent,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
      actions: <Widget>[
        OutlinedButton(onPressed: onOpen, child: const Text('Details')),
        FilledButton(onPressed: onBid ?? onOpen, child: const Text('Bid')),
      ],
    );
  }
}

class GtexRegenCard extends StatelessWidget {
  const GtexRegenCard({
    super.key,
    required this.player,
    required this.onOpen,
    this.generation = 'Gen-1',
    this.trajectory,
  });

  final GtexPlayerCardData player;
  final VoidCallback onOpen;
  final String generation;
  final String? trajectory;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final Color accent =
        player.potential >= 90 ? tokens.accentArena : tokens.accentCommunity;
    return PlayerCard(
      name: player.name,
      rating: player.rating,
      image: '',
      position: player.position,
      subtitle: '${player.country} | ${player.clubName} • $generation',
      accentColor: accent,
      avatarSize: 72,
      onTap: onOpen,
      badgeLabels: <String>[
        player.position,
        'POT ${player.potential}',
        generation,
        ...player.badges.take(2),
      ],
      metrics: <PlayerCardMetric>[
        PlayerCardMetric(label: 'Trajectory', value: trajectory ?? '${player.rating} → ${player.potential}'),
        PlayerCardMetric(label: 'Age', value: '${player.age}'),
        PlayerCardMetric(
          label: 'Value',
          value: gtexCompactCurrency(player.price),
        ),
      ],
      footer: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: <Widget>[
          Expanded(
            child: Text(
              player.bidStatus,
              style: Theme.of(context).textTheme.bodyMedium,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          GtexBadgeIcon(
            label: 'REGEN PROSPECT',
            color: accent,
          ),
        ],
      ),
      actions: <Widget>[
        OutlinedButton(onPressed: onOpen, child: const Text('Scout')),
        FilledButton(onPressed: onOpen, child: const Text('Develop')),
      ],
    );
  }
}

class GtexClubAssetCard extends StatelessWidget {
  const GtexClubAssetCard({
    super.key,
    required this.clubName,
    required this.leagueName,
    required this.squadRating,
    required this.squadValue,
    required this.clubValuation,
    required this.sharePrice,
    required this.shareMovement,
    this.onTap,
    this.onTradeShares,
  });

  final String clubName;
  final String leagueName;
  final int squadRating;
  final double squadValue;
  final double clubValuation;
  final double sharePrice;
  final double shareMovement;
  final VoidCallback? onTap;
  final VoidCallback? onTradeShares;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final bool isUp = shareMovement >= 0;
    final Color trendColor = isUp ? tokens.accent : tokens.accentWarm;

    return GteSurfacePanel(
      accentColor: tokens.accentClub,
      padding: const EdgeInsets.all(18),
      onTap: onTap,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(14),
                  gradient: LinearGradient(
                    colors: <Color>[tokens.accentClub, tokens.panelElevated],
                  ),
                ),
                child: Icon(Icons.shield_outlined, color: tokens.textInverse),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(clubName, style: Theme.of(context).textTheme.titleLarge),
                    Text(leagueName, style: Theme.of(context).textTheme.bodySmall),
                  ],
                ),
              ),
              GtexBadgeIcon(
                label: 'OVR $squadRating',
                color: tokens.accentClub,
              ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: <Widget>[
              GtexMetricPill(
                label: 'Club Value',
                value: '₦${gtexCompactCurrency(clubValuation)}',
                icon: Icons.account_balance_outlined,
                color: tokens.accentClub,
              ),
              GtexMetricPill(
                label: 'Share Price',
                value: '₦${sharePrice.toStringAsFixed(2)}',
                icon: Icons.show_chart_rounded,
                color: trendColor,
              ),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            children: <Widget>[
              Icon(
                isUp ? Icons.arrow_upward_rounded : Icons.arrow_downward_rounded,
                size: 16,
                color: trendColor,
              ),
              const SizedBox(width: 4),
              Text(
                '${isUp ? '+' : ''}${shareMovement.toStringAsFixed(1)}% 24h',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: trendColor,
                      fontWeight: FontWeight.w700,
                    ),
              ),
              const Spacer(),
              if (onTradeShares != null)
                FilledButton.tonal(
                  onPressed: onTradeShares,
                  child: const Text('Trade Shares'),
                ),
            ],
          ),
        ],
      ),
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
