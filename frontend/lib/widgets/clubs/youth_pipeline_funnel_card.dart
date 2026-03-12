import 'package:flutter/material.dart';
import 'package:gte_frontend/models/scouting_models.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class YouthPipelineFunnelCard extends StatelessWidget {
  const YouthPipelineFunnelCard({
    super.key,
    required this.title,
    required this.stages,
    this.subtitle,
  });

  final String title;
  final String? subtitle;
  final List<YouthPipelineStage> stages;

  @override
  Widget build(BuildContext context) {
    final int maxCount =
        stages.isEmpty ? 1 : stages.map((YouthPipelineStage item) => item.count).reduce((int a, int b) => a > b ? a : b);
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          if (subtitle != null) ...<Widget>[
            const SizedBox(height: 8),
            Text(subtitle!, style: Theme.of(context).textTheme.bodyMedium),
          ],
          const SizedBox(height: 18),
          for (final YouthPipelineStage stage in stages) ...<Widget>[
            Align(
              alignment: Alignment.centerLeft,
              child: FractionallySizedBox(
                widthFactor: (stage.count / maxCount).clamp(0.18, 1),
                child: Container(
                  margin: const EdgeInsets.only(bottom: 10),
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(20),
                    color: Colors.white.withValues(alpha: 0.05),
                    border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
                  ),
                  child: Row(
                    children: <Widget>[
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Text(stage.label,
                                style: Theme.of(context).textTheme.titleMedium),
                            const SizedBox(height: 4),
                            Text(stage.description,
                                style: Theme.of(context).textTheme.bodyMedium),
                          ],
                        ),
                      ),
                      const SizedBox(width: 12),
                      Text('${stage.count}',
                          style: Theme.of(context).textTheme.titleLarge),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
