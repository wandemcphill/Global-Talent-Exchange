import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_ops_controller.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/models/academy_models.dart';
import 'package:gte_frontend/screens/clubs/club_ops_screen_host.dart';
import 'package:gte_frontend/widgets/clubs/player_progress_card.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';

class AcademyPlayerDetailScreen extends StatelessWidget {
  const AcademyPlayerDetailScreen({
    super.key,
    required this.playerId,
    this.clubId = 'royal-lagos-fc',
    this.clubName,
    this.baseUrl = 'http://127.0.0.1:8000',
    this.mode = GteBackendMode.liveThenFixture,
    this.api,
    this.controller,
  });

  final String playerId;
  final String clubId;
  final String? clubName;
  final String baseUrl;
  final GteBackendMode mode;
  final ClubOpsApi? api;
  final ClubOpsController? controller;

  @override
  Widget build(BuildContext context) {
    return ClubOpsScreenHost(
      title: 'Player pathway',
      subtitle: 'Development progress and next pathway milestone.',
      clubId: clubId,
      clubName: clubName,
      baseUrl: baseUrl,
      mode: mode,
      api: api,
      controller: controller,
      builder: (BuildContext context, ClubOpsController controller) {
        final AcademyPlayer? player = controller.playerById(playerId);
        if (player == null) {
          return const Padding(
            padding: EdgeInsets.all(20),
            child: GteStatePanel(
              title: 'Academy player not found',
              message: 'This player is not available in the current academy roster.',
              icon: Icons.person_off_outlined,
            ),
          );
        }
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
          children: <Widget>[
            PlayerProgressCard(player: player),
          ],
        );
      },
    );
  }
}
