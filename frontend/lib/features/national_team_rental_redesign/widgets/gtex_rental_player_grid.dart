import 'package:flutter/material.dart';

import '../../../ui_gtex/ui_gtex.dart';
import '../models/gtex_national_team_rental_models.dart';

class GtexRentalPlayerGrid extends StatelessWidget {
  const GtexRentalPlayerGrid({
    super.key,
    required this.players,
    required this.selectedPlayerId,
    required this.basketState,
    required this.isLoading,
    required this.error,
    required this.warning,
    required this.diagnostics,
    required this.selectedCountryName,
    required this.selectedTeamName,
    required this.onSelectPlayer,
    required this.onToggleBasket,
    this.onRefresh,
  });

  final List<GtexRentalPlayerView> players;
  final String? selectedPlayerId;
  final GtexRentalBasketState basketState;
  final bool isLoading;
  final String? error;
  final String? warning;
  final List<String> diagnostics;
  final String? selectedCountryName;
  final String? selectedTeamName;
  final ValueChanged<GtexRentalPlayerView> onSelectPlayer;
  final ValueChanged<GtexRentalPlayerView> onToggleBasket;
  final VoidCallback? onRefresh;

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return const _RentalPoolSkeletonBoard();
    }
    if (error != null && error!.trim().isNotEmpty) {
      return Padding(
        padding: const EdgeInsets.all(GtexSpacing.lg),
        child: GtexBlockedState(
          title: 'Live rental pool unavailable',
          reason: error!,
          severity: GtexBlockedSeverity.error,
          resolution:
              'The national rental screen cannot render fallback countries or players.',
          icon: Icons.cloud_off_outlined,
          ctaLabel: onRefresh == null ? null : 'Retry live pool',
          ctaAction: onRefresh,
        ),
      );
    }
    if (players.isEmpty) {
      return Padding(
        padding: const EdgeInsets.all(GtexSpacing.lg),
        child: GtexBlockedState(
          title: 'No backend-eligible players returned',
          reason:
              'The live national-team rental endpoint returned no players for the selected filters.',
          severity: GtexBlockedSeverity.info,
          resolution:
              'Change the competition, country, or team filter, or retry the live pool.',
          icon: Icons.flag_outlined,
          ctaLabel: onRefresh == null ? null : 'Retry live pool',
          ctaAction: onRefresh,
        ),
      );
    }

    return Column(
      children: <Widget>[
        if (warning != null && warning!.trim().isNotEmpty)
          _RentalPoolWarningBanner(warning: warning!, diagnostics: diagnostics),
        Padding(
          padding: const EdgeInsets.all(GtexSpacing.md),
          child: LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final bool wide = constraints.maxWidth > 820;
              final int eligibleCount =
                  players
                      .where(
                        (GtexRentalPlayerView player) => player.rentalEligible,
                      )
                      .length;
              final int unavailableCount = players.length - eligibleCount;
              final List<Widget> metrics = <Widget>[
                GtexMetricTile(
                  label: 'Backend eligible',
                  value: eligibleCount.toString(),
                  icon: Icons.groups_2_outlined,
                ),
                GtexMetricTile(
                  label: 'Selected squad',
                  value: basketState.squadCount.toString(),
                  icon: Icons.shopping_basket_outlined,
                  accent: GtexColors.gold,
                ),
                GtexMetricTile(
                  label: 'Unavailable',
                  value: unavailableCount.toString(),
                  icon: Icons.lock_outline,
                  accent:
                      unavailableCount == 0
                          ? GtexColors.textMuted
                          : GtexColors.gold,
                ),
                GtexMetricTile(
                  label: 'Country pool',
                  value: selectedCountryName ?? 'All',
                  icon: Icons.public_outlined,
                  accent: GtexColors.cyan,
                ),
                GtexMetricTile(
                  label: 'Team',
                  value: selectedTeamName ?? 'Any team',
                  icon: Icons.flag_circle_outlined,
                  accent: GtexColors.mint,
                ),
              ];
              if (wide) {
                return Row(
                  children: metrics
                      .map(
                        (Widget item) => Expanded(
                          child: Padding(
                            padding: const EdgeInsets.only(
                              right: GtexSpacing.sm,
                            ),
                            child: item,
                          ),
                        ),
                      )
                      .toList(growable: false),
                );
              }
              return Column(
                children: metrics
                    .map(
                      (Widget item) => Padding(
                        padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
                        child: item,
                      ),
                    )
                    .toList(growable: false),
              );
            },
          ),
        ),
        Expanded(
          child: LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final int crossAxisCount = _rentalGridCrossAxisCount(
                constraints.maxWidth,
              );
              final double childAspectRatio = _rentalGridAspectRatio(
                crossAxisCount,
              );

              final Widget grid = GridView.builder(
                padding: const EdgeInsets.fromLTRB(
                  GtexSpacing.md,
                  0,
                  GtexSpacing.md,
                  GtexSpacing.md,
                ),
                gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: crossAxisCount,
                  childAspectRatio: childAspectRatio,
                  mainAxisSpacing: GtexSpacing.md,
                  crossAxisSpacing: GtexSpacing.md,
                ),
                itemCount: players.length,
                itemBuilder: (BuildContext context, int index) {
                  final GtexRentalPlayerView player = players[index];
                  return GtexPlayerCard(
                    name: player.name,
                    position: player.position,
                    clubName: player.clubName,
                    nationality: player.nationality,
                    priceLabel: player.priceLabel,
                    imageUrl: player.imageUrl,
                    countryCode: player.countryCode,
                    rarityLabel: player.rarityLabel,
                    marketHeatLabel: player.marketHeatLabel,
                    gsiTrendLabel: player.transferTrendLabel,
                    demandLabel: player.demandLabel,
                    chemistryLinks: <String>[
                      player.availabilityLabel,
                      player.sourceLabel,
                      if (player.portraitStatus != null) player.portraitStatus!,
                    ],
                    cardVariant:
                        player.isPreseededRegen
                            ? GtexPlayerCardVariant.nationalSeed
                            : GtexPlayerCardVariant.standard,
                    portraitStatus: player.portraitStatus,
                    portraitMissingReason: player.portraitMissingReason,
                    gsiLabel: player.gsiLabel,
                    gsiTierLabel: player.gsiTierLabel,
                    ageLabel: player.ageLabel,
                    isSelected: selectedPlayerId == player.playerId,
                    onTap: () => onSelectPlayer(player),
                    onAddToShortlist:
                        player.rentalEligible
                            ? () => onToggleBasket(player)
                            : null,
                    onBuyNow:
                        player.rentalEligible
                            ? () => onToggleBasket(player)
                            : null,
                  );
                },
              );

              if (onRefresh == null) return grid;
              return RefreshIndicator(
                onRefresh: () async => onRefresh!.call(),
                child: grid,
              );
            },
          ),
        ),
      ],
    );
  }
}

int _rentalGridCrossAxisCount(double maxWidth) {
  if (maxWidth >= 1120) return 3;
  if (maxWidth >= 680) return 2;
  return 1;
}

double _rentalGridAspectRatio(int crossAxisCount) {
  return crossAxisCount == 1 ? 1.85 : 1.72;
}

class _RentalPoolWarningBanner extends StatelessWidget {
  const _RentalPoolWarningBanner({
    required this.warning,
    required this.diagnostics,
  });

  final String warning;
  final List<String> diagnostics;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        GtexSpacing.md,
        GtexSpacing.md,
        GtexSpacing.md,
        0,
      ),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(GtexSpacing.md),
        decoration: BoxDecoration(
          color: GtexColors.gold.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
          border: Border.all(color: GtexColors.gold.withValues(alpha: 0.35)),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            const Icon(Icons.warning_amber_rounded, color: GtexColors.gold),
            const SizedBox(width: GtexSpacing.sm),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    warning,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: GtexColors.text,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  if (diagnostics.isNotEmpty) ...<Widget>[
                    const SizedBox(height: GtexSpacing.xs),
                    Text(
                      diagnostics.take(2).join('  |  '),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: GtexColors.textSecondary,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _RentalPoolSkeletonBoard extends StatelessWidget {
  const _RentalPoolSkeletonBoard();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(GtexSpacing.md),
      child: Column(
        children: <Widget>[
          Row(
            children: List<Widget>.generate(
              3,
              (int index) => const Expanded(
                child: Padding(
                  padding: EdgeInsets.only(right: GtexSpacing.sm),
                  child: _RentalSkeletonTile(height: 76),
                ),
              ),
            ),
          ),
          const SizedBox(height: GtexSpacing.md),
          Expanded(
            child: LayoutBuilder(
              builder: (BuildContext context, BoxConstraints constraints) {
                final int crossAxisCount = _rentalGridCrossAxisCount(
                  constraints.maxWidth,
                );
                return GridView.builder(
                  itemCount: 6,
                  gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: crossAxisCount,
                    childAspectRatio: _rentalGridAspectRatio(crossAxisCount),
                    mainAxisSpacing: GtexSpacing.md,
                    crossAxisSpacing: GtexSpacing.md,
                  ),
                  itemBuilder:
                      (BuildContext context, int index) =>
                          const _RentalSkeletonTile(height: 168),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _RentalSkeletonTile extends StatelessWidget {
  const _RentalSkeletonTile({required this.height});

  final double height;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: height,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(GtexSpacing.radiusLg),
        border: Border.all(color: GtexColors.line.withValues(alpha: 0.45)),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[
            GtexColors.pitch.withValues(alpha: 0.12),
            GtexColors.panelStrong,
            GtexColors.cyan.withValues(alpha: 0.08),
          ],
        ),
      ),
    );
  }
}
