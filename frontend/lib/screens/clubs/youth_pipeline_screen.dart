import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_ops_controller.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/models/scouting_models.dart';
import 'package:gte_frontend/screens/clubs/club_ops_screen_host.dart';
import 'package:gte_frontend/widgets/clubs/youth_pipeline_funnel_card.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class YouthPipelineScreen extends StatelessWidget {
  const YouthPipelineScreen({
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
      title: 'Youth pipeline',
      subtitle: 'Conversion stages from tracked prospects to promoted players.',
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
              title: 'Loading youth pipeline',
              message: 'Preparing funnel stages and conversion notes.',
              icon: Icons.filter_alt_outlined,
            ),
          );
        }
        final YouthPipelineSnapshot pipeline = controller.youthPipeline!;
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
          children: <Widget>[
            YouthPipelineFunnelCard(
              title: 'Pipeline summary',
              subtitle:
                  '${pipeline.conversionPercent.toStringAsFixed(1)}% conversion from tracked prospects to promoted players.',
              stages: pipeline.stages,
            ),
            const SizedBox(height: 16),
            GteSurfacePanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('Pipeline notes',
                      style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 12),
                  for (final String note in pipeline.notes) ...<Widget>[
                    Text(note, style: Theme.of(context).textTheme.bodyMedium),
                    if (note != pipeline.notes.last) const SizedBox(height: 8),
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
