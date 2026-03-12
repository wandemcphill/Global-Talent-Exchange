import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_ops_controller.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/models/academy_models.dart';
import 'package:gte_frontend/screens/clubs/academy_player_detail_screen.dart';
import 'package:gte_frontend/screens/clubs/club_ops_screen_host.dart';
import 'package:gte_frontend/widgets/clubs/academy_player_row.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';

class AcademyPlayersScreen extends StatelessWidget {
  const AcademyPlayersScreen({
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
      title: 'Academy players',
      subtitle: 'Roster and pathway readiness across the academy.',
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
              title: 'Loading academy players',
              message: 'Preparing the current academy roster.',
              icon: Icons.groups_outlined,
            ),
          );
        }
        final List<AcademyPlayer> players =
            controller.academy?.players ?? const <AcademyPlayer>[];
        return ListView.separated(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
          itemBuilder: (BuildContext context, int index) {
            final AcademyPlayer player = players[index];
            return AcademyPlayerRow(
              player: player,
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (BuildContext context) => AcademyPlayerDetailScreen(
                    playerId: player.id,
                    controller: controller,
                    clubId: clubId,
                    clubName: clubName,
                  ),
                ),
              ),
            );
          },
          separatorBuilder: (_, __) => const SizedBox(height: 12),
          itemCount: players.length,
        );
      },
    );
  }
}
