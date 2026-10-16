import 'package:flutter/material.dart';
import 'package:gte_frontend/models/scouting_models.dart';
import 'package:gte_frontend/widgets/clubs/club_ops_formatters.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class ProspectReportCard extends StatelessWidget {
  const ProspectReportCard({
    super.key,
    required this.report,
  });

  final ProspectReport report;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(report.headline, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 6),
          Text(
            '${report.scoutName} · ${clubOpsFormatDate(report.createdAt)}',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 12),
          Text(report.overallFit, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          Text(report.technicalNote, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 6),
          Text(report.physicalNote, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 6),
          Text(report.characterNote, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 10),
          Text(report.recommendation, style: Theme.of(context).textTheme.titleMedium),
        ],
      ),
    );
  }
}
