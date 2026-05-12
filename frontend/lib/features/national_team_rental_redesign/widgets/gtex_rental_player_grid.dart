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
    required this.selectedCountryName,
    required this.selectedTeamName,
    required this.onSelectPlayer,
    required this.onToggleBasket,
    required this.onRefresh,
  });

  final List<GtexRentalPlayerView> players;
  final String? selectedPlayerId;
  final GtexRentalBasketState basketState;
  final bool isLoading;
  final String? error;
  final String? selectedCountryName;
  final String? selectedTeamName;
  final ValueChanged<GtexRentalPlayerView> onSelectPlayer;
  final ValueChanged<GtexRentalPlayerView> onToggleBasket;
  final VoidCallback onRefresh;

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (error != null && error!.trim().isNotEmpty) {
      return Padding(
        padding: const EdgeInsets.all(GtexSpacing.lg),
        child: GtexEmptyState(
          title: 'Rental pool could not load',
          message: error!,
          icon: Icons.cloud_off_outlined,
          actionLabel: 'Retry',
          onAction: onRefresh,
        ),
      );
    }
    if (players.isEmpty) {
      return const Padding(
        padding: EdgeInsets.all(GtexSpacing.lg),
        child: GtexEmptyState(
          title: 'No eligible rental players yet',
          message:
              'Choose a competition and country to load the live rental pool.',
          icon: Icons.flag_outlined,
        ),
      );
    }

    return Column(
      children: <Widget>[
        Padding(
          padding: const EdgeInsets.all(GtexSpacing.md),
          child: LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final bool wide = constraints.maxWidth > 820;
              final List<Widget> metrics = <Widget>[
                GtexMetricTile(
                  label: 'Eligible players',
                  value: players.length.toString(),
                  icon: Icons.groups_2_outlined,
                ),
                GtexMetricTile(
                  label: 'Selected squad',
                  value: basketState.squadCount.toString(),
                  icon: Icons.shopping_basket_outlined,
                  accent: GtexColors.gold,
                ),
                GtexMetricTile(
                  label: 'Country',
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
          child: RefreshIndicator(
            onRefresh: () async => onRefresh(),
            child: GridView.builder(
              padding: const EdgeInsets.fromLTRB(
                GtexSpacing.md,
                0,
                GtexSpacing.md,
                GtexSpacing.md,
              ),
              gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: MediaQuery.sizeOf(context).width > 1350 ? 3 : 2,
                childAspectRatio: 1.82,
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
                  gsiLabel: player.gsiLabel,
                  gsiTierLabel: player.gsiTierLabel,
                  ageLabel: player.ageLabel,
                  isSelected: selectedPlayerId == player.playerId,
                  onTap: () => onSelectPlayer(player),
                  onAddToShortlist: () => onToggleBasket(player),
                  onBuyNow: () => onToggleBasket(player),
                );
              },
            ),
          ),
        ),
      ],
    );
  }
}
