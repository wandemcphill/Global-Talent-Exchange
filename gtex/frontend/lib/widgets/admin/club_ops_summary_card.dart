import 'package:flutter/material.dart';
import 'package:gte_frontend/models/club_finance_models.dart';
import 'package:gte_frontend/widgets/clubs/club_ops_formatters.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class ClubOpsSummaryCard extends StatelessWidget {
  const ClubOpsSummaryCard({
    super.key,
    required this.summary,
  });

  final ClubOpsAdminSnapshot summary;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      emphasized: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Club operations', style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 12),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              _AdminMetric(label: 'Clubs monitored', value: '${summary.clubsMonitored}'),
              _AdminMetric(
                label: 'Operating budget',
                value: clubOpsFormatCurrency(summary.totalOperatingBudget),
              ),
              _AdminMetric(label: 'Active contracts', value: '${summary.activeContracts}'),
              _AdminMetric(label: 'Active assignments', value: '${summary.activeAssignments}'),
            ],
          ),
        ],
      ),
    );
  }
}

class _AdminMetric extends StatelessWidget {
  const _AdminMetric({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 180,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(value, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 4),
          Text(label, style: Theme.of(context).textTheme.bodyMedium),
        ],
      ),
    );
  }
}
