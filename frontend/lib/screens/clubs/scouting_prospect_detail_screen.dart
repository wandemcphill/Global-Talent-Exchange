import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_ops_controller.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/models/scouting_models.dart';
import 'package:gte_frontend/screens/clubs/club_ops_screen_host.dart';
import 'package:gte_frontend/widgets/clubs/prospect_report_card.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class ScoutingProspectDetailScreen extends StatelessWidget {
  const ScoutingProspectDetailScreen({
    super.key,
    required this.prospectId,
    this.clubId = 'royal-lagos-fc',
    this.clubName,
    this.baseUrl = 'http://127.0.0.1:8000',
    this.mode = GteBackendMode.liveThenFixture,
    this.api,
    this.controller,
  });

  final String prospectId;
  final String clubId;
  final String? clubName;
  final String baseUrl;
  final GteBackendMode mode;
  final ClubOpsApi? api;
  final ClubOpsController? controller;

  @override
  Widget build(BuildContext context) {
    return ClubOpsScreenHost(
      title: 'Prospect detail',
      subtitle: 'Pathway fit, live recommendation, and latest scouting report.',
      clubId: clubId,
      clubName: clubName,
      baseUrl: baseUrl,
      mode: mode,
      api: api,
      controller: controller,
      builder: (BuildContext context, ClubOpsController controller) {
        final Prospect? prospect = controller.prospectById(prospectId);
        final ProspectReport? report = controller.reportForProspect(prospectId);
        if (prospect == null) {
          return const Padding(
            padding: EdgeInsets.all(20),
            child: GteStatePanel(
              title: 'Prospect not found',
              message: 'This prospect is not available in the current scouting board.',
              icon: Icons.person_off_outlined,
            ),
          );
        }
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
          children: <Widget>[
            GteSurfacePanel(
              emphasized: true,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(prospect.name,
                      style: Theme.of(context).textTheme.headlineSmall),
                  const SizedBox(height: 8),
                  Text(
                    '${prospect.position} · ${prospect.age} · ${prospect.region} · ${prospect.currentClub}',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 12),
                  Text(prospect.developmentProjection,
                      style: Theme.of(context).textTheme.bodyMedium),
                  const SizedBox(height: 12),
                  Text(prospect.nextAction,
                      style: Theme.of(context).textTheme.titleMedium),
                ],
              ),
            ),
            const SizedBox(height: 16),
            if (report != null) ProspectReportCard(report: report),
          ],
        );
      },
    );
  }
}
