import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/constants/app_spacing.dart';
import '../../core/theme/app_colors.dart';
import '../../core/widgets/gtex_surface_card.dart';
import '../../shared/models/competition.dart';
import '../../shared/models/player.dart';
import '../../shared/providers/regen_provider.dart';
import '../../shared/widgets/metric_pill.dart';
import '../../shared/widgets/section_heading.dart';
import 'tournament_intro_screen.dart';
import 'tournament_models.dart';

class TournamentsScreen extends ConsumerWidget {
  const TournamentsScreen({super.key, this.allowFixtureData = false});

  final bool allowFixtureData;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final List<Competition> competitions = ref.watch(competitionsProvider);
    final List<Player> regens = ref.watch(regenProvider);
    if (!allowFixtureData) {
      return const _TournamentsBlockedView();
    }
    final Competition featured =
        competitions.isNotEmpty
            ? competitions.first
            : const Competition(
              name: 'GTEX World Cup',
              region: 'Global',
              stage: 'Opening Night',
              nextFixture: 'Lagos Atlas FC vs Rio Norte',
              spotlight: 'Cinematic tournament package loading',
            );

    return ListView(
      padding: const EdgeInsets.all(spacingMD),
      children: <Widget>[
        const SectionHeading(
          title: 'Tournaments',
          subtitle: 'Fullscreen intros, live brackets, and squad staging.',
          trailing: MetricPill(
            label: 'Status',
            value: 'Broadcast Ready',
            highlight: true,
          ),
        ),
        const SizedBox(height: spacingLG),
        GtexSurfaceCard(
          glowColor: AppColors.primary,
          padding: EdgeInsets.zero,
          child: ClipRRect(
            borderRadius: BorderRadius.circular(cardRadius),
            child: Container(
              padding: const EdgeInsets.all(spacingLG),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: <Color>[
                    AppColors.primary.withValues(alpha: 0.2),
                    AppColors.gold.withValues(alpha: 0.14),
                    AppColors.surfaceMuted,
                  ],
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Wrap(
                    spacing: spacingSM,
                    runSpacing: spacingSM,
                    children: <Widget>[
                      MetricPill(
                        label: 'Region',
                        value: featured.region,
                        highlight: true,
                      ),
                      MetricPill(label: 'Stage', value: featured.stage),
                    ],
                  ),
                  const SizedBox(height: spacingLG),
                  Text(
                    featured.name,
                    style: Theme.of(context).textTheme.headlineMedium,
                  ),
                  const SizedBox(height: spacingSM),
                  Text(
                    featured.spotlight,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                  const SizedBox(height: spacingLG),
                  FilledButton.icon(
                    key: const Key('tournament-launch-open-intro'),
                    onPressed: () {
                      Navigator.of(context).push(
                        MaterialPageRoute<void>(
                          builder: (BuildContext context) {
                            return TournamentIntroScreen(
                              competition: featured,
                              fixtures: buildTournamentFixtures(featured),
                              standings: buildTournamentStandings(featured),
                              squad: buildTournamentSquad(regens),
                              allowFixtureData: allowFixtureData,
                            );
                          },
                        ),
                      );
                    },
                    icon: const Icon(Icons.play_circle_fill_rounded),
                    label: const Text('Open Intro'),
                  ),
                ],
              ),
            ),
          ),
        ),
        const SizedBox(height: spacingLG),
        ...competitions.asMap().entries.map(
          (MapEntry<int, Competition> entry) => Padding(
            padding: const EdgeInsets.only(bottom: spacingMD),
            child: GtexSurfaceCard(
              glowColor: entry.key == 0 ? AppColors.gold : null,
              child: ListTile(
                contentPadding: EdgeInsets.zero,
                title: Text(entry.value.name),
                subtitle: Text(
                  '${entry.value.region} | ${entry.value.stage}\n${entry.value.nextFixture}',
                ),
                trailing: const Icon(Icons.chevron_right_rounded),
                onTap: () {
                  Navigator.of(context).push(
                    MaterialPageRoute<void>(
                      builder: (BuildContext context) {
                        return TournamentIntroScreen(
                          competition: entry.value,
                          fixtures: buildTournamentFixtures(entry.value),
                          standings: buildTournamentStandings(entry.value),
                          squad: buildTournamentSquad(regens),
                          allowFixtureData: allowFixtureData,
                        );
                      },
                    ),
                  );
                },
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _TournamentsBlockedView extends StatelessWidget {
  const _TournamentsBlockedView();

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(spacingMD),
      children: <Widget>[
        const SectionHeading(
          title: 'Tournaments',
          subtitle:
              'Competition OS fixtures and standings load only from the live backend authority.',
          trailing: MetricPill(label: 'Status', value: 'Blocked'),
        ),
        const SizedBox(height: spacingLG),
        GtexSurfaceCard(
          glowColor: AppColors.gold,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Live tournaments unavailable',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: spacingSM),
              Text(
                'This legacy tournament shell is blocked until persisted Competition OS fixtures, standings, and squad data are injected.',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
