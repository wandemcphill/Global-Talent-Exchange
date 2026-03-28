import 'package:flutter/material.dart';

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

class GtexPlayerCard extends StatelessWidget {
  const GtexPlayerCard({
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
    return GteSurfacePanel(
      accentColor: accent,
      onTap: onOpen,
      padding: const EdgeInsets.all(16),
      child: SingleChildScrollView(
        physics: const NeverScrollableScrollPhysics(),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                GtexAnimatedAvatar(
                  label: player.name,
                  accent: accent,
                  badges: player.badges,
                  rating: player.rating,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        player.name,
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '${player.position} - ${player.country}',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: player.badges
                            .map(
                              (String badge) =>
                                  GtexBadgeIcon(label: badge, color: accent),
                            )
                            .toList(growable: false),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            Row(
              children: <Widget>[
                Expanded(
                  child: _PlayerMetaTile(
                    label: 'Value',
                    value: gtexCompactCurrency(player.price),
                    accent: accent,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _PlayerMetaTile(
                    label: 'Potential',
                    value: '${player.potential}',
                    accent: tokens.accentCommunity,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              player.bidStatus,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: 6),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: <Widget>[
                Text(
                  player.timerLabel,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: accent,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                GtexBadgeIcon(
                  label: 'Liquidity: ${player.liquidityLabel}',
                  color: tokens.accentCapital,
                ),
              ],
            ),
            const SizedBox(height: 14),
            Row(
              children: <Widget>[
                Expanded(
                  child: OutlinedButton(
                    onPressed: onOpen,
                    child: const Text('Details'),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: FilledButton(
                    onPressed: onBid ?? onOpen,
                    child: const Text('Bid'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
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
    return GteSurfacePanel(
      accentColor: accent,
      onTap: onOpen,
      padding: const EdgeInsets.all(16),
      child: SingleChildScrollView(
        physics: const NeverScrollableScrollPhysics(),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              children: <Widget>[
                Expanded(
                  child: Text(
                    'Regen',
                    style: Theme.of(
                      context,
                    ).textTheme.labelLarge?.copyWith(color: accent),
                  ),
                ),
                Text(
                  '${player.potential} POT',
                  style: Theme.of(
                    context,
                  ).textTheme.titleMedium?.copyWith(color: accent),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Center(
              child: GtexAnimatedAvatar(
                label: player.name,
                size: 72,
                accent: accent,
                badges: player.badges,
                rating: player.rating,
              ),
            ),
            const SizedBox(height: 10),
            Text(player.name, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 4),
            Text(
              '${player.position} - ${player.country}',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: player.badges
                  .map(
                    (String badge) =>
                        GtexBadgeIcon(label: badge, color: accent),
                  )
                  .toList(growable: false),
            ),
          ],
        ),
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

class _PlayerMetaTile extends StatelessWidget {
  const _PlayerMetaTile({
    required this.label,
    required this.value,
    required this.accent,
  });

  final String label;
  final String value;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        color: tokens.surfaceHighlight.withValues(alpha: 0.06),
        border: Border.all(color: tokens.stroke.withValues(alpha: 0.64)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(label, style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 4),
          Text(
            value,
            style: Theme.of(
              context,
            ).textTheme.titleMedium?.copyWith(color: accent),
          ),
        ],
      ),
    );
  }
}
