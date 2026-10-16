import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_controller.dart';
import 'package:gte_frontend/widgets/admin/club_revenue_summary_card.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';

class ClubAnalyticsScreen extends StatelessWidget {
  const ClubAnalyticsScreen({
    super.key,
    required this.controller,
  });

  final ClubController controller;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (BuildContext context, _) {
        final analytics = controller.adminAnalytics;
        return Container(
          decoration: gteBackdropDecoration(),
          child: Scaffold(
            backgroundColor: Colors.transparent,
            appBar: AppBar(
              title: const Text('Club analytics'),
            ),
            body: analytics == null
                ? const Padding(
                    padding: EdgeInsets.all(20),
                    child: GteStatePanel(
                      title: 'Club analytics unavailable',
                      message:
                          'Open club admin first so the analytics snapshot can be loaded.',
                      icon: Icons.insights_outlined,
                    ),
                  )
                : ListView(
                    padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
                    children: <Widget>[
                      Wrap(
                        spacing: 14,
                        runSpacing: 14,
                        children: analytics.revenueSummaries.map((summary) {
                          return ClubRevenueSummaryCard(summary: summary);
                        }).toList(growable: false),
                      ),
                      const SizedBox(height: 18),
                      Text(
                        'Top clubs',
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      const SizedBox(height: 12),
                      DataTable(
                        columns: const <DataColumn>[
                          DataColumn(label: Text('Rank')),
                          DataColumn(label: Text('Club')),
                          DataColumn(label: Text('Metric')),
                          DataColumn(label: Text('Context')),
                        ],
                        rows: analytics.topClubs.map((entry) {
                          return DataRow(
                            cells: <DataCell>[
                              DataCell(Text('${entry.rank}')),
                              DataCell(Text(entry.clubName)),
                              DataCell(Text(entry.valueLabel)),
                              DataCell(Text(entry.contextLabel)),
                            ],
                          );
                        }).toList(growable: false),
                      ),
                      const SizedBox(height: 18),
                      Text(
                        'Top dynasties',
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      const SizedBox(height: 12),
                      DataTable(
                        columns: const <DataColumn>[
                          DataColumn(label: Text('Rank')),
                          DataColumn(label: Text('Club')),
                          DataColumn(label: Text('Era')),
                          DataColumn(label: Text('Context')),
                        ],
                        rows: analytics.topDynasties.map((entry) {
                          return DataRow(
                            cells: <DataCell>[
                              DataCell(Text('${entry.rank}')),
                              DataCell(Text(entry.clubName)),
                              DataCell(Text(entry.valueLabel)),
                              DataCell(Text(entry.contextLabel)),
                            ],
                          );
                        }).toList(growable: false),
                      ),
                    ],
                  ),
          ),
        );
      },
    );
  }
}
