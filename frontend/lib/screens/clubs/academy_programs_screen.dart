import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_ops_controller.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/models/academy_models.dart';
import 'package:gte_frontend/screens/clubs/club_ops_screen_host.dart';
import 'package:gte_frontend/widgets/clubs/academy_program_card.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';

class AcademyProgramsScreen extends StatelessWidget {
  const AcademyProgramsScreen({
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
      title: 'Academy programs',
      subtitle: 'Current pathway blocks by age band and training focus.',
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
              title: 'Loading academy programs',
              message: 'Preparing pathway blocks and cohort outcomes.',
              icon: Icons.list_alt_outlined,
            ),
          );
        }
        final List<AcademyProgram> programs =
            controller.academy?.programs ?? const <AcademyProgram>[];
        return ListView.separated(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
          itemBuilder: (BuildContext context, int index) =>
              AcademyProgramCard(program: programs[index]),
          separatorBuilder: (_, __) => const SizedBox(height: 12),
          itemCount: programs.length,
        );
      },
    );
  }
}
