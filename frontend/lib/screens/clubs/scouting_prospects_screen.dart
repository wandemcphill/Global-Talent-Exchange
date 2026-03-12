import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_ops_controller.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/models/scouting_models.dart';
import 'package:gte_frontend/screens/clubs/club_ops_screen_host.dart';
import 'package:gte_frontend/screens/clubs/scouting_prospect_detail_screen.dart';
import 'package:gte_frontend/widgets/clubs/prospect_card.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';

class ScoutingProspectsScreen extends StatelessWidget {
  const ScoutingProspectsScreen({
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
      title: 'Youth prospects',
      subtitle: 'Shortlist, trial, and scholarship candidates.',
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
              title: 'Loading prospects',
              message: 'Preparing the youth prospect board.',
              icon: Icons.person_search_outlined,
            ),
          );
        }
        final List<Prospect> prospects =
            controller.scouting?.prospects ?? const <Prospect>[];
        return ListView.separated(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
          itemBuilder: (BuildContext context, int index) {
            final Prospect prospect = prospects[index];
            return ProspectCard(
              prospect: prospect,
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (BuildContext context) => ScoutingProspectDetailScreen(
                    prospectId: prospect.id,
                    controller: controller,
                    clubId: clubId,
                    clubName: clubName,
                  ),
                ),
              ),
            );
          },
          separatorBuilder: (_, __) => const SizedBox(height: 12),
          itemCount: prospects.length,
        );
      },
    );
  }
}
