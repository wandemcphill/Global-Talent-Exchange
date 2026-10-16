import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_controller.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/trophy_item_dto.dart';
import 'package:gte_frontend/widgets/clubs/featured_trophy_card.dart';
import 'package:gte_frontend/widgets/clubs/trophy_grid.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class ClubTrophyCabinetScreen extends StatelessWidget {
  const ClubTrophyCabinetScreen({
    super.key,
    required this.controller,
  });

  final ClubController controller;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (BuildContext context, _) {
        final cabinet = controller.data?.trophyCabinet;
        return Container(
          decoration: gteBackdropDecoration(),
          child: Scaffold(
            backgroundColor: Colors.transparent,
            appBar: AppBar(
              title: const Text('Trophy Cabinet'),
            ),
            body: cabinet == null
                ? Padding(
                    padding: const EdgeInsets.all(20),
                    child: GteStatePanel(
                      title: 'Trophy cabinet unavailable',
                      message: controller.errorMessage ??
                          'Load the club profile before opening this screen.',
                      icon: Icons.emoji_events_outlined,
                    ),
                  )
                : RefreshIndicator(
                    onRefresh: controller.refresh,
                    child: ListView(
                      physics: const AlwaysScrollableScrollPhysics(),
                      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
                      children: <Widget>[
                        if (cabinet.isEmpty)
                          const GteStatePanel(
                            title: 'The cabinet is ready for its first legacy piece',
                            message:
                                'New clubs start with an aspirational cabinet. The first title becomes the anchor for every future milestone.',
                            icon: Icons.auto_awesome_outlined,
                          )
                        else ...<Widget>[
                          FeaturedTrophyCard(
                            trophy: cabinet.featuredHonors().first,
                            onTap: () => _showTrophyDetails(
                              context,
                              cabinet.featuredHonors().first,
                            ),
                          ),
                          const SizedBox(height: 18),
                          GteSurfacePanel(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: <Widget>[
                                Text(
                                  'Cabinet collection',
                                  style: Theme.of(context).textTheme.titleLarge,
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  'Season groups keep the trophy cabinet readable while still highlighting dynasty progression.',
                                  style: Theme.of(context).textTheme.bodyMedium,
                                ),
                                const SizedBox(height: 16),
                                TrophyGrid(
                                  trophies: cabinet.historicHonorsTimeline,
                                  onSelected: (TrophyItemDto trophy) =>
                                      _showTrophyDetails(context, trophy),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: 18),
                          ...cabinet.trophiesBySeason.map((season) {
                            final seasonHonors = cabinet.historicHonorsTimeline
                                .where((TrophyItemDto trophy) =>
                                    trophy.seasonLabel == season.seasonLabel)
                                .toList(growable: false);
                            return Padding(
                              padding: const EdgeInsets.only(bottom: 14),
                              child: GteSurfacePanel(
                                child: ExpansionTile(
                                  tilePadding: EdgeInsets.zero,
                                  childrenPadding: EdgeInsets.zero,
                                  title: Text(
                                    season.seasonLabel,
                                    style:
                                        Theme.of(context).textTheme.titleLarge,
                                  ),
                                  subtitle: Text(
                                    '${season.totalHonorsCount} honors • ${season.majorHonorsCount} major',
                                    style:
                                        Theme.of(context).textTheme.bodyMedium,
                                  ),
                                  children: <Widget>[
                                    const SizedBox(height: 12),
                                    TrophyGrid(
                                      trophies: seasonHonors,
                                      onSelected: (TrophyItemDto trophy) =>
                                          _showTrophyDetails(context, trophy),
                                    ),
                                  ],
                                ),
                              ),
                            );
                          }),
                        ],
                      ],
                    ),
                  ),
          ),
        );
      },
    );
  }

  Future<void> _showTrophyDetails(
    BuildContext context,
    TrophyItemDto trophy,
  ) {
    return showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (BuildContext context) {
        return Padding(
          padding: const EdgeInsets.all(16),
          child: GteSurfacePanel(
            emphasized: true,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  trophy.trophyName,
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: 8),
                Text(
                  '${trophy.seasonLabel} • ${trophy.competitionRegion}',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 12),
                Text(
                  trophy.finalResultSummary,
                  style: Theme.of(context).textTheme.bodyLarge,
                ),
                if (trophy.topPerformerName != null) ...<Widget>[
                  const SizedBox(height: 12),
                  Text(
                    'Top performer: ${trophy.topPerformerName}',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ],
            ),
          ),
        );
      },
    );
  }
}
