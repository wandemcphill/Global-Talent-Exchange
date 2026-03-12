import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_ops_controller.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/models/academy_models.dart';
import 'package:gte_frontend/screens/clubs/club_ops_screen_host.dart';
import 'package:gte_frontend/widgets/admin/academy_conversion_card.dart';
import 'package:gte_frontend/widgets/clubs/academy_program_card.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';

class AcademyAnalyticsScreen extends StatelessWidget {
  const AcademyAnalyticsScreen({
    super.key,
    this.baseUrl = 'http://127.0.0.1:8000',
    this.mode = GteBackendMode.liveThenFixture,
    this.api,
    this.controller,
  });

  final String baseUrl;
  final GteBackendMode mode;
  final ClubOpsApi? api;
  final ClubOpsController? controller;

  @override
  Widget build(BuildContext context) {
    return ClubOpsScreenHost(
      title: 'Academy analytics',
      subtitle: 'Conversion, readiness, and program mix.',
      baseUrl: baseUrl,
      mode: mode,
      api: api,
      controller: controller,
      adminData: true,
      builder: (BuildContext context, ClubOpsController controller) {
        if (controller.isLoadingAdminData && !controller.hasAdminData) {
          return const Padding(
            padding: EdgeInsets.all(20),
            child: GteStatePanel(
              title: 'Loading academy analytics',
              message: 'Preparing pathway conversion and program coverage metrics.',
              icon: Icons.analytics_outlined,
            ),
          );
        }
        final analytics = controller.academyAnalytics!;
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
          children: <Widget>[
            AcademyConversionCard(analytics: analytics),
            const SizedBox(height: 16),
            for (final AcademyProgram program in analytics.programMix) ...<Widget>[
              AcademyProgramCard(program: program),
              if (program != analytics.programMix.last) const SizedBox(height: 12),
            ],
          ],
        );
      },
    );
  }
}
