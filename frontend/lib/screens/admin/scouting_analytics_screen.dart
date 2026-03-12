import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_ops_controller.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/models/scouting_models.dart';
import 'package:gte_frontend/screens/clubs/club_ops_screen_host.dart';
import 'package:gte_frontend/widgets/clubs/scout_assignment_card.dart';
import 'package:gte_frontend/widgets/clubs/youth_pipeline_funnel_card.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class ScoutingAnalyticsScreen extends StatelessWidget {
  const ScoutingAnalyticsScreen({
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
      title: 'Scouting analytics',
      subtitle: 'Assignment completion, regional coverage, and funnel conversion.',
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
              title: 'Loading scouting analytics',
              message: 'Preparing funnel metrics and assignment load.',
              icon: Icons.area_chart_outlined,
            ),
          );
        }
        final ScoutingAnalyticsSnapshot analytics = controller.scoutingAnalytics!;
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
          children: <Widget>[
            GteSurfacePanel(
              emphasized: true,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    '${analytics.assignmentCompletionPercent.toStringAsFixed(0)}% assignments completed',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    '${analytics.regionalCoveragePercent.toStringAsFixed(0)}% regional coverage · ${analytics.youthConversionPercent.toStringAsFixed(1)}% youth conversion',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            YouthPipelineFunnelCard(
              title: 'Scouting funnel',
              stages: analytics.funnel,
            ),
            const SizedBox(height: 16),
            for (final ScoutAssignment assignment in analytics.assignmentLoad) ...<Widget>[
              ScoutAssignmentCard(assignment: assignment),
              if (assignment != analytics.assignmentLoad.last)
                const SizedBox(height: 12),
            ],
          ],
        );
      },
    );
  }
}
