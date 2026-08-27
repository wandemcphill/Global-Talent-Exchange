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

class GtexClubAssetCard extends StatelessWidget {
  const GtexClubAssetCard({
    super.key,
    required this.clubName,
    required this.league,
    required this.squadRating,
    required this.valuation,
    required this.sharePrice,
    required this.changePct,
    this.onTap,
    this.onTradeShares,
  });

  final String clubName;
  final String league;
  final int squadRating;
  final double valuation;
  final double sharePrice;
  final double changePct;
  final VoidCallback? onTap;
  final VoidCallback? onTradeShares;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final bool isPositive = changePct >= 0;
    final Color trendColor = isPositive ? tokens.accentArena : tokens.accentWarm;

    return GteSurfacePanel(
      accentColor: tokens.accentClub,
      onTap: onTap,
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              GtexAnimatedAvatar(
                label: clubName,
                size: 48,
                accent: tokens.accentClub,
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      clubName,
                      style: Theme.of(context).textTheme.titleMedium,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 2),
                    Text(
                      league,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
              GtexBadgeIcon(
                label: 'OVR $squadRating',
                color: tokens.accentClub,
              ),
            ],
          ),
          const SizedBox(height: 14),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: <Widget>[
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('Club Value', style: Theme.of(context).textTheme.bodySmall),
                  const SizedBox(height: 2),
                  Text(
                    '₦${gtexCompactCurrency(valuation)}',
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                  ),
                ],
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: <Widget>[
                  Text('Share Price', style: Theme.of(context).textTheme.bodySmall),
                  const SizedBox(height: 2),
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: <Widget>[
                      Text(
                        '₦${sharePrice.toStringAsFixed(2)}',
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                              fontWeight: FontWeight.w700,
                              color: tokens.accentCapital,
                            ),
                      ),
                      const SizedBox(width: 4),
                      Text(
                        '${isPositive ? "+" : ""}${changePct.toStringAsFixed(1)}%',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: trendColor,
                              fontWeight: FontWeight.w700,
                            ),
                      ),
                    ],
                  ),
                ],
              ),
            ],
          ),
          if (onTradeShares != null) ...<Widget>[
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: FilledButton.tonal(
                onPressed: onTradeShares,
                child: const Text('Trade Club Shares'),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class GtexClubShareCard extends StatelessWidget {
  const GtexClubShareCard({
    super.key,
    required this.symbol,
    required this.clubName,
    required this.price,
    required this.change24h,
    required this.volume,
    this.onBuy,
    this.onSell,
  });

  final String symbol;
  final String clubName;
  final double price;
  final double change24h;
  final double volume;
  final VoidCallback? onBuy;
  final VoidCallback? onSell;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final bool isUp = change24h >= 0;
    final Color trendColor = isUp ? tokens.accentArena : tokens.accentWarm;

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: tokens.panelStrong.withValues(alpha: 0.78),
        border: Border.all(color: tokens.stroke.withValues(alpha: 0.65)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(10),
                  color: tokens.accentCapital.withValues(alpha: 0.16),
                ),
                child: Text(
                  symbol,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        color: tokens.accentCapital,
                        fontWeight: FontWeight.w800,
                      ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  clubName,
                  style: Theme.of(context).textTheme.titleMedium,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              Text(
                '${isUp ? "▲" : "▼"} ${change24h.abs().toStringAsFixed(2)}%',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: trendColor,
                      fontWeight: FontWeight.w700,
                    ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: <Widget>[
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('Price', style: Theme.of(context).textTheme.bodySmall),
                  Text(
                    '₦${price.toStringAsFixed(2)}',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                  ),
                ],
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: <Widget>[
                  Text('24h Vol', style: Theme.of(context).textTheme.bodySmall),
                  Text(
                    '₦${gtexCompactCurrency(volume)}',
                    style: Theme.of(context).textTheme.titleSmall,
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: <Widget>[
              Expanded(
                child: OutlinedButton(
                  onPressed: onSell,
                  child: const Text('Sell'),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: FilledButton(
                  onPressed: onBuy,
                  child: const Text('Buy Shares'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class GtexPortfolioAssetCard extends StatelessWidget {
  const GtexPortfolioAssetCard({
    super.key,
    required this.title,
    required this.subtitle,
    required this.assetType,
    required this.currentValue,
    required this.profitLoss,
    required this.profitLossPct,
    this.onTap,
  });

  final String title;
  final String subtitle;
  final String assetType;
  final double currentValue;
  final double profitLoss;
  final double profitLossPct;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final bool isGain = profitLoss >= 0;
    final Color statusColor = isGain ? tokens.accentArena : tokens.accentWarm;

    return GteSurfacePanel(
      accentColor: statusColor,
      onTap: onTap,
      padding: const EdgeInsets.all(14),
      child: Row(
        children: <Widget>[
          Container(
            width: 44,
            height: 44,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(12),
              color: tokens.panelElevated,
              border: Border.all(color: tokens.stroke.withValues(alpha: 0.5)),
            ),
            child: Icon(
              assetType == 'PLAYER'
                  ? Icons.person_outline
                  : assetType == 'CLUB_SHARE'
                      ? Icons.show_chart
                      : Icons.account_balance_wallet_outlined,
              color: tokens.accent,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  title,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                const SizedBox(height: 2),
                Text(
                  subtitle,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: <Widget>[
              Text(
                '₦${gtexCompactCurrency(currentValue)}',
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
              const SizedBox(height: 2),
              Text(
                '${isGain ? "+" : ""}₦${gtexCompactCurrency(profitLoss.abs())} (${isGain ? "+" : ""}${profitLossPct.toStringAsFixed(1)}%)',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: statusColor,
                      fontWeight: FontWeight.w700,
                    ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class GtexMarketCard extends StatelessWidget {
  const GtexMarketCard({
    super.key,
    required this.title,
    required this.subtitle,
    required this.price,
    required this.trendLabel,
    required this.isRising,
    this.onTap,
  });

  final String title;
  final String subtitle;
  final double price;
  final String trendLabel;
  final bool isRising;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final Color trendColor = isRising ? tokens.accentArena : tokens.accentWarm;

    return GteSurfacePanel(
      accentColor: trendColor,
      onTap: onTap,
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: <Widget>[
              Expanded(
                child: Text(
                  title,
                  style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              GtexBadgeIcon(
                label: trendLabel,
                color: trendColor,
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(subtitle, style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: <Widget>[
              Text('Current Price', style: Theme.of(context).textTheme.bodySmall),
              Text(
                '₦${gtexCompactCurrency(price)}',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: tokens.accentCapital,
                      fontWeight: FontWeight.w800,
                    ),
              ),
            ],
          ),
        ],
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
  const GtexRegenCard({super.key, required this.player, required this.onOpen});

  final GtexPlayerCardData player;
  final VoidCallback onOpen;

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
      subtitle: '${player.country} | ${player.clubName}',
      accentColor: accent,
      avatarSize: 72,
      onTap: onOpen,
      badgeLabels: <String>[
        player.position,
        '${player.potential} POT',
        ...player.badges.take(2),
      ],
      metrics: <PlayerCardMetric>[
        PlayerCardMetric(label: 'Potential', value: '${player.potential}'),
        PlayerCardMetric(label: 'Age', value: '${player.age}'),
        PlayerCardMetric(
          label: 'Value',
          value: gtexCompactCurrency(player.price),
        ),
      ],
      footer: Text(
        player.bidStatus,
        style: Theme.of(context).textTheme.bodyMedium,
      ),
      actions: <Widget>[
        FilledButton.tonal(onPressed: onOpen, child: const Text('Open')),
      ],
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
