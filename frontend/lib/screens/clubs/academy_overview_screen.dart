import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_ops_controller.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/models/academy_models.dart';
import 'package:gte_frontend/screens/clubs/academy_players_screen.dart';
import 'package:gte_frontend/screens/clubs/academy_programs_screen.dart';
import 'package:gte_frontend/screens/clubs/academy_training_screen.dart';
import 'package:gte_frontend/screens/clubs/club_ops_screen_host.dart';
import 'package:gte_frontend/widgets/clubs/academy_program_card.dart';
import 'package:gte_frontend/widgets/clubs/club_ops_formatters.dart';
import 'package:gte_frontend/widgets/clubs/club_ops_scaffold.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class AcademyOverviewScreen extends StatelessWidget {
  const AcademyOverviewScreen({
    super.key,
    this.clubId = 'royal-lagos-fc',
    this.clubName,
    this.baseUrl = 'http://127.0.0.1:8000',
    this.mode = GteBackendMode.liveThenFixture,
    this.api,
    this.controller,
  });

  final String clubId;
  final String? clubName;
  final String baseUrl;
  final GteBackendMode mode;
  final ClubOpsApi? api;
  final ClubOpsController? controller;

  @override
  Widget build(BuildContext context) {
    return ClubOpsScreenHost(
      title: 'Academy pathway',
      subtitle: 'Programs, player progression, and training cycle planning.',
      clubId: clubId,
      clubName: clubName,
      baseUrl: baseUrl,
      mode: mode,
      api: api,
      controller: controller,
      builder: (BuildContext context, ClubOpsController controller) {
        if (controller.isLoadingClubData && !controller.hasClubData) {
          return const Padding(
            padding: EdgeInsets.all(20),
            child: GteStatePanel(
              title: 'Loading academy overview',
              message: 'Preparing pathway summary, programs, and player progression.',
              icon: Icons.school_outlined,
            ),
          );
        }
        final AcademyDashboard academy = controller.academy!;
        final AcademyPathwaySummary summary = academy.pathwaySummary;
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
          children: <Widget>[
            GteSurfacePanel(
              emphasized: true,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(academy.clubName,
                      style: Theme.of(context).textTheme.headlineSmall),
                  const SizedBox(height: 8),
                  Text(
                    '${academy.players.length} players in pathway · ${summary.promotionsThisSeason} promotions this season · budget ${clubOpsFormatCurrency(summary.developmentBudget)}',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 12),
                  Text(summary.staffCoverageLabel,
                      style: Theme.of(context).textTheme.bodyMedium),
                  Text(summary.facilityLabel,
                      style: Theme.of(context).textTheme.bodyMedium),
                ],
              ),
            ),
            const SizedBox(height: 16),
            ClubOpsSectionHeader(
              title: 'Academy surfaces',
              subtitle: 'Open the programs list, player roster, or training cycles.',
              action: Wrap(
                spacing: 8,
                children: <Widget>[
                  FilledButton.tonal(
                    onPressed: () => Navigator.of(context).push(
                      MaterialPageRoute<void>(
                        builder: (BuildContext context) => AcademyProgramsScreen(
                          controller: controller,
                          clubId: clubId,
                          clubName: clubName,
                        ),
                      ),
                    ),
                    child: const Text('Programs'),
                  ),
                  FilledButton.tonal(
                    onPressed: () => Navigator.of(context).push(
                      MaterialPageRoute<void>(
                        builder: (BuildContext context) => AcademyPlayersScreen(
                          controller: controller,
                          clubId: clubId,
                          clubName: clubName,
                        ),
                      ),
                    ),
                    child: const Text('Players'),
                  ),
                  FilledButton.tonal(
                    onPressed: () => Navigator.of(context).push(
                      MaterialPageRoute<void>(
                        builder: (BuildContext context) => AcademyTrainingScreen(
                          controller: controller,
                          clubId: clubId,
                          clubName: clubName,
                        ),
                      ),
                    ),
                    child: const Text('Training'),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            for (final AcademyProgram program in academy.programs.take(2)) ...<Widget>[
              AcademyProgramCard(program: program),
              if (program != academy.programs.take(2).last)
                const SizedBox(height: 12),
            ],
            const SizedBox(height: 16),
            GteSurfacePanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('Recent promotions',
                      style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 12),
                  for (final AcademyPromotion promotion in academy.promotions) ...<Widget>[
                    Text(
                      '${promotion.playerName} · ${promotion.destination}',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${clubOpsFormatDate(promotion.occurredAt)} · ${promotion.note}',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    if (promotion != academy.promotions.last)
                      const SizedBox(height: 12),
                  ],
                ],
              ),
            ),
          ],
        );
      },
    );
  }
}
