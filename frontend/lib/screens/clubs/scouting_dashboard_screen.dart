import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_ops_controller.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/models/scouting_models.dart';
import 'package:gte_frontend/screens/clubs/club_ops_screen_host.dart';
import 'package:gte_frontend/screens/clubs/scouting_assignments_screen.dart';
import 'package:gte_frontend/screens/clubs/scouting_prospect_detail_screen.dart';
import 'package:gte_frontend/screens/clubs/scouting_prospects_screen.dart';
import 'package:gte_frontend/screens/clubs/youth_pipeline_screen.dart';
import 'package:gte_frontend/widgets/clubs/club_ops_scaffold.dart';
import 'package:gte_frontend/widgets/clubs/prospect_card.dart';
import 'package:gte_frontend/widgets/clubs/prospect_report_card.dart';
import 'package:gte_frontend/widgets/clubs/scout_assignment_card.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class ScoutingDashboardScreen extends StatelessWidget {
  const ScoutingDashboardScreen({
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
      title: 'Scouting pipeline',
      subtitle: 'Assignments, prospects, reports, and youth conversion flow.',
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
              title: 'Loading scouting dashboard',
              message: 'Preparing assignments, prospects, and latest scouting reports.',
              icon: Icons.travel_explore_outlined,
            ),
          );
        }
        final ScoutingDashboard scouting = controller.scouting!;
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
          children: <Widget>[
            GteSurfacePanel(
              emphasized: true,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(scouting.clubName,
                      style: Theme.of(context).textTheme.headlineSmall),
                  const SizedBox(height: 8),
                  Text(
                    '${scouting.openAssignments} live assignments · ${scouting.liveProspects} active prospects · ${scouting.trialsScheduled} trials scheduled',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            ClubOpsSectionHeader(
              title: 'Scouting views',
              subtitle: 'Open the assignments board, prospect list, or youth pipeline summary.',
              action: Wrap(
                spacing: 8,
                children: <Widget>[
                  FilledButton.tonal(
                    onPressed: () => Navigator.of(context).push(
                      MaterialPageRoute<void>(
                        builder: (BuildContext context) => ScoutingAssignmentsScreen(
                          controller: controller,
                          clubId: clubId,
                          clubName: clubName,
                        ),
                      ),
                    ),
                    child: const Text('Assignments'),
                  ),
                  FilledButton.tonal(
                    onPressed: () => Navigator.of(context).push(
                      MaterialPageRoute<void>(
                        builder: (BuildContext context) => ScoutingProspectsScreen(
                          controller: controller,
                          clubId: clubId,
                          clubName: clubName,
                        ),
                      ),
                    ),
                    child: const Text('Prospects'),
                  ),
                  FilledButton.tonal(
                    onPressed: () => Navigator.of(context).push(
                      MaterialPageRoute<void>(
                        builder: (BuildContext context) => YouthPipelineScreen(
                          controller: controller,
                          clubId: clubId,
                          clubName: clubName,
                        ),
                      ),
                    ),
                    child: const Text('Pipeline'),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            if (scouting.assignments.isNotEmpty)
              ScoutAssignmentCard(assignment: scouting.assignments.first),
            const SizedBox(height: 16),
            if (scouting.prospects.isNotEmpty)
              ProspectCard(
                prospect: scouting.prospects.first,
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute<void>(
                    builder: (BuildContext context) => ScoutingProspectDetailScreen(
                      prospectId: scouting.prospects.first.id,
                      controller: controller,
                      clubId: clubId,
                      clubName: clubName,
                    ),
                  ),
                ),
              ),
            const SizedBox(height: 16),
            if (scouting.reports.isNotEmpty)
              ProspectReportCard(report: scouting.reports.first),
          ],
        );
      },
    );
  }
}
