import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/app_feedback.dart';
import '../../core/constants/app_spacing.dart';
import '../../models/regen_creation_models.dart';
import '../../models/regen_universe_models.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/providers/auth_provider.dart';
import '../../shared/providers/regen_provider.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';
import '../../shared/widgets/gtex_premium_panels.dart';
import '../../widgets/football_player_card.dart';
import '../../widgets/gte_state_panel.dart';

class RegensScreen extends ConsumerWidget {
  const RegensScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<RegenUniverseHubData> value = ref.watch(
      regenUniverseHubProvider,
    );
    final bool authenticated = ref.watch(isAuthenticatedProvider);
    return AppPageLayout(
      title: 'Scout Prospects',
      subtitle:
          'Scout rising prospects, national-pool depth, GSI, potential, and club-building stories.',
      trailing: DataSourceBadge(
        status:
            value.hasError ? DataSourceStatus.blocked : DataSourceStatus.live,
      ),
      children: <Widget>[
        value.when(
          data:
              (RegenUniverseHubData data) => Column(
                children: <Widget>[
                  _Hero(data: data, authenticated: authenticated),
                  const SizedBox(height: spacingMD),
                  _AwardsPanel(awards: data.awards),
                  const SizedBox(height: spacingMD),
                  _NationalPoolPanel(nationalRegens: data.nationalRegens),
                  const SizedBox(height: spacingMD),
                  _RisingStarsPanel(stars: data.risingStars),
                  const SizedBox(height: spacingMD),
                  _RequestedSonsPanel(
                    authenticated: authenticated,
                    orders: data.requestedSonOrders,
                  ),
                  const SizedBox(height: spacingMD),
                  _ScoutingFeedPanel(items: data.scoutingFeed),
                  const SizedBox(height: spacingMD),
                  _TrackingPanel(tracking: data.tracking),
                ],
              ),
          loading:
              () => const GteStatePanel(
                eyebrow: 'SCOUT',
                title: 'Loading prospects',
                message:
                    'Syncing rising stars, awards, national-pool depth, and request-son orders.',
                icon: Icons.auto_awesome_rounded,
                isLoading: true,
              ),
          error:
              (Object error, StackTrace stackTrace) => GteStatePanel(
                eyebrow: 'SCOUT',
                title: 'Prospect scouting is blocked',
                message: AppFeedback.messageFor(
                  error,
                  fallback: 'Live prospect scouting is unavailable right now.',
                ),
                icon: Icons.warning_amber_rounded,
              ),
        ),
      ],
    );
  }
}

class _Hero extends StatelessWidget {
  const _Hero({required this.data, required this.authenticated});

  final RegenUniverseHubData data;
  final bool authenticated;

  @override
  Widget build(BuildContext context) {
    return GtexHeroPanel(
      eyebrow: 'LIVE TALENT MAP',
      title: 'Scout the next wave of football talent.',
      description:
          'Review GSI, form, potential, national-pool depth, and request-son prospects with clean football card visuals.',
      metrics: <Widget>[
        _MetricChip(
          label: 'Awards',
          value: '${data.awards.length}',
          tone: GtexSurfaceTone.warning,
        ),
        _MetricChip(
          label: 'National pool',
          value: '${data.nationalRegens.length}',
          tone: GtexSurfaceTone.info,
        ),
        _MetricChip(
          label: 'Rising stars',
          value: '${data.risingStars.length}',
          tone: GtexSurfaceTone.live,
        ),
        _MetricChip(
          label: 'Requested sons',
          value:
              authenticated
                  ? '${data.generatedRequestedSons.length}'
                  : 'Sign in',
          tone: GtexSurfaceTone.success,
        ),
      ],
    );
  }
}

class _AwardsPanel extends StatelessWidget {
  const _AwardsPanel({required this.awards});

  final List<RegenAwardResult> awards;

  @override
  Widget build(BuildContext context) {
    return GtexSectionPanel(
      title: 'Awards',
      subtitle:
          'Prospect awards and form stories. National-pool players can win here without becoming tradable.',
      child:
          awards.isEmpty
              ? const _EmptyState(
                message: 'No live award winners have been published yet.',
              )
              : Column(
                children: awards
                    .map(
                      (RegenAwardResult result) => Padding(
                        padding: const EdgeInsets.only(bottom: spacingSM),
                        child: _AwardTile(result: result),
                      ),
                    )
                    .toList(growable: false),
              ),
    );
  }
}

class _AwardTile extends StatelessWidget {
  const _AwardTile({required this.result});

  final RegenAwardResult result;

  @override
  Widget build(BuildContext context) {
    final RegenAwardWinner? winner =
        result.winners.isEmpty ? null : result.winners.first;
    return GtexListTile(
      title: result.award.name,
      subtitle:
          winner == null
              ? 'Season ${result.season.seasonNumber} | Winner pending'
              : 'Season ${result.season.seasonNumber} | ${winner.playerName} | Score ${winner.rankingScore.toStringAsFixed(1)}',
      leadingIcon: Icons.emoji_events_rounded,
      tone: GtexSurfaceTone.warning,
      trailing:
          winner == null
              ? null
              : SizedBox(
                width: 220,
                child: _BadgeWrap(labels: winner.badgeLabels),
              ),
    );
  }
}

class _NationalPoolPanel extends StatelessWidget {
  const _NationalPoolPanel({required this.nationalRegens});

  final List<NationalRegenSeed> nationalRegens;

  @override
  Widget build(BuildContext context) {
    return GtexSectionPanel(
      title: 'National Pool',
      subtitle: 'National-pool prospects are rental-only squad depth.',
      child:
          nationalRegens.isEmpty
              ? const _EmptyState(
                message: 'No national-pool regens are published yet.',
              )
              : Column(
                children: nationalRegens
                    .map(
                      (NationalRegenSeed seed) => Padding(
                        padding: const EdgeInsets.only(bottom: spacingSM),
                        child: FootballPlayerCard(
                          playerName: seed.displayName,
                          tierLabel: seed.rarityTier,
                          avatar: null,
                          imageUrl: seed.imageUrl,
                          position: seed.primaryPosition,
                          nationalityCode: seed.countryCode,
                          rating: seed.resolvedGsi,
                          ratingLabel: 'GSI',
                          ageLabel: '${seed.age ?? '--'}',
                          potentialLabel: '${seed.potentialRating}',
                          attributes: <String>[
                            seed.countryName,
                            seed.ageBand.toUpperCase(),
                            ...seed.badgeLabels.take(2),
                          ],
                        ),
                      ),
                    )
                    .toList(growable: false),
              ),
    );
  }
}

class _RisingStarsPanel extends StatelessWidget {
  const _RisingStarsPanel({required this.stars});

  final List<RegenRisingStar> stars;

  @override
  Widget build(BuildContext context) {
    return GtexSectionPanel(
      title: 'Rising Stars',
      subtitle: 'Scouted rising prospects with form and potential.',
      child:
          stars.isEmpty
              ? const _EmptyState(
                message: 'No rising stars have been published yet.',
              )
              : Column(
                children: stars
                    .map(
                      (RegenRisingStar star) => Padding(
                        padding: const EdgeInsets.only(bottom: spacingSM),
                        child: FootballPlayerCard(
                          playerName: star.player.name,
                          tierLabel: star.player.sourceType,
                          avatar: null,
                          imageUrl: star.player.imageUrl,
                          position: star.player.position,
                          nationalityCode: star.player.nationalityCode,
                          rating: star.player.resolvedGsi,
                          ratingLabel: 'GSI',
                          ageLabel: '${star.player.age}',
                          potentialLabel: '${star.player.potential}',
                          attributes: <String>[
                            star.player.nationality,
                            star.momentumLabel,
                            ...star.displayBadges.take(2),
                          ],
                        ),
                      ),
                    )
                    .toList(growable: false),
              ),
    );
  }
}

class _RequestedSonsPanel extends StatelessWidget {
  const _RequestedSonsPanel({
    required this.authenticated,
    required this.orders,
  });

  final bool authenticated;
  final List<RegenCreationOrder> orders;

  @override
  Widget build(BuildContext context) {
    final List<RegenCreationOrder> generated = orders
        .where((RegenCreationOrder order) => order.generatedPlayer != null)
        .toList(growable: false);
    return GtexSectionPanel(
      title: 'Requested Sons',
      subtitle: 'Authenticated order feed for paid request-son prospects.',
      child:
          !authenticated
              ? const _EmptyState(
                message: 'Sign in to load your live request-son orders.',
              )
              : generated.isEmpty
              ? const _EmptyState(
                message: 'No generated request-son players are visible yet.',
              )
              : Column(
                children: generated
                    .map(
                      (RegenCreationOrder order) => Padding(
                        padding: const EdgeInsets.only(bottom: spacingSM),
                        child: FootballPlayerCard(
                          playerName:
                              order.generatedPlayer?.fullName ??
                              'Requested son',
                          tierLabel: 'Requested Son',
                          avatar: null,
                          imageUrl: order.generatedPlayer?.imageUrl,
                          position: order.generatedPlayer?.position,
                          nationalityCode: order.generatedPlayer?.countryCode,
                          rating: order.generatedPlayer?.resolvedGsi,
                          ratingLabel: 'GSI',
                          ageLabel: '${order.generatedPlayer?.age ?? '--'}',
                          potentialLabel:
                              '${order.generatedPlayer?.potentialRating ?? '--'}',
                          attributes: <String>[order.status, 'Bloodline Regen'],
                        ),
                      ),
                    )
                    .toList(growable: false),
              ),
    );
  }
}

class _ScoutingFeedPanel extends StatelessWidget {
  const _ScoutingFeedPanel({required this.items});

  final List<RegenScoutingFeedItem> items;

  @override
  Widget build(BuildContext context) {
    return GtexSectionPanel(
      title: 'Scouting Feed',
      subtitle: 'Live `/regen-universe/scouting-feed` discovery stories.',
      child:
          items.isEmpty
              ? const _EmptyState(
                message: 'No live scouting feed items are visible yet.',
              )
              : Column(
                children: items
                    .map(
                      (RegenScoutingFeedItem item) => Padding(
                        padding: const EdgeInsets.only(bottom: spacingSM),
                        child: GtexListTile(
                          title: item.title,
                          subtitle:
                              '${item.summary}\n${item.player?.name ?? 'Unknown prospect'} | ${item.feedType}',
                          leadingIcon: Icons.travel_explore_rounded,
                          tone: GtexSurfaceTone.info,
                          trailing: SizedBox(
                            width: 220,
                            child: _BadgeWrap(labels: item.displayBadges),
                          ),
                        ),
                      ),
                    )
                    .toList(growable: false),
              ),
    );
  }
}

class _TrackingPanel extends StatelessWidget {
  const _TrackingPanel({required this.tracking});

  final RegenGenerationTracking tracking;

  @override
  Widget build(BuildContext context) {
    final RegenGenerationTrackingEntry? leadingCountry =
        tracking.countryDistribution.isEmpty
            ? null
            : tracking.countryDistribution.first;
    return GtexSectionPanel(
      title: 'Tracking',
      subtitle:
          'Live generation totals and country distribution from `/regen-universe/tracking`.',
      child: Wrap(
        spacing: spacingSM,
        runSpacing: spacingSM,
        children: <Widget>[
          _MetricChip(
            label: 'Total tracked',
            value: '${tracking.totalSeededPlayers}',
            tone: GtexSurfaceTone.live,
          ),
          _MetricChip(
            label: 'Peak GSI',
            value: '${tracking.globalPeakRating}',
            tone: GtexSurfaceTone.warning,
          ),
          if (leadingCountry != null)
            _MetricChip(
              label: 'Leading country',
              value: '${leadingCountry.bucket} (${leadingCountry.count})',
              tone: GtexSurfaceTone.info,
            ),
        ],
      ),
    );
  }
}

class _MetricChip extends StatelessWidget {
  const _MetricChip({
    required this.label,
    required this.value,
    required this.tone,
  });

  final String label;
  final String value;
  final GtexSurfaceTone tone;

  @override
  Widget build(BuildContext context) {
    return GtexStatTile(label: label, value: value, tone: tone);
  }
}

class _BadgeWrap extends StatelessWidget {
  const _BadgeWrap({required this.labels});

  final List<String> labels;

  @override
  Widget build(BuildContext context) {
    if (labels.isEmpty) {
      return const SizedBox.shrink();
    }
    return Wrap(
      alignment: WrapAlignment.end,
      spacing: spacingXS,
      runSpacing: spacingXS,
      children: labels
          .map(
            (String label) =>
                _BadgeChip(label: label, tone: _toneForBadge(label)),
          )
          .toList(growable: false),
    );
  }

  GtexSurfaceTone _toneForBadge(String label) {
    switch (label) {
      case 'National Pool':
        return GtexSurfaceTone.info;
      case 'Rental Only':
        return GtexSurfaceTone.warning;
      case 'Not Tradable':
        return GtexSurfaceTone.danger;
      case 'Requested Son':
        return GtexSurfaceTone.success;
      case 'Bloodline Regen':
        return GtexSurfaceTone.warning;
      case 'Club Regen':
        return GtexSurfaceTone.live;
      default:
        return GtexSurfaceTone.neutral;
    }
  }
}

class _BadgeChip extends StatelessWidget {
  const _BadgeChip({required this.label, required this.tone});

  final String label;
  final GtexSurfaceTone tone;

  @override
  Widget build(BuildContext context) {
    final Color toneColor = switch (tone) {
      GtexSurfaceTone.live => Theme.of(context).colorScheme.primary,
      GtexSurfaceTone.info => Theme.of(context).colorScheme.secondary,
      GtexSurfaceTone.success => Colors.greenAccent.shade400,
      GtexSurfaceTone.warning => Colors.amber.shade400,
      GtexSurfaceTone.danger => Theme.of(context).colorScheme.error,
      GtexSurfaceTone.neutral => Colors.white70,
    };
    return ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 140),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
        decoration: BoxDecoration(
          color: toneColor.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: toneColor.withValues(alpha: 0.3)),
        ),
        child: Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: Theme.of(context).textTheme.labelSmall?.copyWith(
            color: toneColor,
            fontWeight: FontWeight.w800,
          ),
        ),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return GtexListTile(
      title: 'Nothing live yet',
      subtitle: message,
      leadingIcon: Icons.hourglass_empty_rounded,
      tone: GtexSurfaceTone.neutral,
    );
  }
}
