import 'package:flutter/material.dart';
import 'package:gte_frontend/models/scouting_models.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class ProspectCard extends StatelessWidget {
  const ProspectCard({
    super.key,
    required this.prospect,
    this.onTap,
  });

  final Prospect prospect;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      onTap: onTap,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Text(prospect.name,
                    style: Theme.of(context).textTheme.titleLarge),
              ),
              Chip(label: Text(_stageLabel(prospect.stage))),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            '${prospect.position} · ${prospect.age} · ${prospect.region}',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 10),
          Text(prospect.developmentProjection,
              style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 10),
          Text(prospect.nextAction, style: Theme.of(context).textTheme.titleMedium),
        ],
      ),
    );
  }

  String _stageLabel(ProspectStage stage) {
    switch (stage) {
      case ProspectStage.monitored:
        return 'Monitored';
      case ProspectStage.shortlisted:
        return 'Shortlisted';
      case ProspectStage.trial:
        return 'Trial';
      case ProspectStage.scholarship:
        return 'Scholarship';
      case ProspectStage.promoted:
        return 'Promoted';
    }
  }
}
