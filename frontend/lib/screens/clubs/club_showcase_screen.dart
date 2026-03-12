import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_controller.dart';
import 'package:gte_frontend/features/club_identity/jerseys/widgets/identity_color_utils.dart';
import 'package:gte_frontend/models/club_catalog_models.dart';
import 'package:gte_frontend/models/club_models.dart';
import 'package:gte_frontend/widgets/clubs/dynasty_milestone_card.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class ClubShowcaseScreen extends StatelessWidget {
  const ClubShowcaseScreen({
    super.key,
    required this.controller,
  });

  final ClubController controller;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (BuildContext context, _) {
        final data = controller.data;
        return Container(
          decoration: gteBackdropDecoration(),
          child: Scaffold(
            backgroundColor: Colors.transparent,
            appBar: AppBar(
              title: const Text('Club showcase'),
            ),
            body: data == null
                ? Padding(
                    padding: const EdgeInsets.all(20),
                    child: GteStatePanel(
                      title: 'Club showcase unavailable',
                      message: controller.errorMessage ??
                          'Load the club profile before opening this screen.',
                      icon: Icons.slideshow_outlined,
                    ),
                  )
                : RefreshIndicator(
                    onRefresh: controller.refresh,
                    child: ListView(
                      physics: const AlwaysScrollableScrollPhysics(),
                      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
                      children: <Widget>[
                        _ShowcaseHero(data: data),
                        const SizedBox(height: 18),
                        Text(
                          'Showcase panels',
                          style: Theme.of(context).textTheme.headlineSmall,
                        ),
                        const SizedBox(height: 12),
                        Wrap(
                          spacing: 14,
                          runSpacing: 14,
                          children: data.showcasePanels.map((ClubShowcasePanel panel) {
                            return SizedBox(
                              width: 240,
                              child: GteSurfacePanel(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: <Widget>[
                                    Text(
                                      panel.title,
                                      style: Theme.of(context).textTheme.titleLarge,
                                    ),
                                    const SizedBox(height: 8),
                                    Text(
                                      panel.value,
                                      style:
                                          Theme.of(context).textTheme.headlineSmall,
                                    ),
                                    const SizedBox(height: 8),
                                    Text(
                                      panel.caption,
                                      style: Theme.of(context).textTheme.bodyMedium,
                                    ),
                                  ],
                                ),
                              ),
                            );
                          }).toList(growable: false),
                        ),
                        const SizedBox(height: 18),
                        Text(
                          'Equipped cosmetics',
                          style: Theme.of(context).textTheme.headlineSmall,
                        ),
                        const SizedBox(height: 12),
                        Wrap(
                          spacing: 12,
                          runSpacing: 12,
                          children: data.catalog
                              .where((ClubCatalogItem item) =>
                                  item.ownershipStatus ==
                                  CatalogOwnershipStatus.equipped)
                              .map(
                                (ClubCatalogItem item) => Chip(
                                  label: Text(item.title),
                                ),
                              )
                              .toList(growable: false),
                        ),
                        const SizedBox(height: 18),
                        Text(
                          'Legacy milestones',
                          style: Theme.of(context).textTheme.headlineSmall,
                        ),
                        const SizedBox(height: 12),
                        Wrap(
                          spacing: 14,
                          runSpacing: 14,
                          children: data.legacyMilestones.map((milestone) {
                            return SizedBox(
                              width: 280,
                              child: DynastyMilestoneCard(milestone: milestone),
                            );
                          }).toList(growable: false),
                        ),
                      ],
                    ),
                  ),
          ),
        );
      },
    );
  }
}

class _ShowcaseHero extends StatelessWidget {
  const _ShowcaseHero({
    required this.data,
  });

  final ClubDashboardData data;

  @override
  Widget build(BuildContext context) {
    final backdrop = data.branding.selectedBackdrop;
    return GteSurfacePanel(
      emphasized: true,
      padding: EdgeInsets.zero,
      child: Container(
        padding: const EdgeInsets.all(22),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(28),
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: backdrop.gradientColors
                .map(identityColorFromHex)
                .toList(growable: false),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              data.clubName,
              style: Theme.of(context).textTheme.displaySmall,
            ),
            const SizedBox(height: 8),
            Text(
              data.branding.motto,
              style: Theme.of(context).textTheme.bodyLarge,
            ),
            const SizedBox(height: 12),
            Text(
              '${data.branding.selectedTheme.name} • ${backdrop.name}',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: GteShellTheme.textPrimary.withValues(alpha: 0.8),
                  ),
            ),
          ],
        ),
      ),
    );
  }
}
