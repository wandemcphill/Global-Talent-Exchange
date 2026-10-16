import 'package:flutter/material.dart';

import '../../models/creator_models.dart';
import '../gte_surface_panel.dart';

class CreatorLeaderboardTable extends StatelessWidget {
  const CreatorLeaderboardTable({
    super.key,
    required this.entries,
  });

  final List<CreatorLeaderboardEntry> entries;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Creator leaderboard',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 16),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: DataTable(
              columns: const <DataColumn>[
                DataColumn(label: Text('Rank')),
                DataColumn(label: Text('Creator')),
                DataColumn(label: Text('Share code')),
                DataColumn(label: Text('Qualified participation')),
                DataColumn(label: Text('Creator competitions')),
                DataColumn(label: Text('Community reward')),
              ],
              rows: entries
                  .map(
                    (CreatorLeaderboardEntry entry) => DataRow(
                      cells: <DataCell>[
                        DataCell(Text('${entry.rank}')),
                        DataCell(
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: <Widget>[
                              Text(entry.displayName),
                              Text('@${entry.handle}'),
                            ],
                          ),
                        ),
                        DataCell(Text(entry.shareCode)),
                        DataCell(Text('${entry.qualifiedParticipation}')),
                        DataCell(Text('${entry.creatorCompetitions}')),
                        DataCell(Text(entry.communityRewardLabel)),
                      ],
                    ),
                  )
                  .toList(growable: false),
            ),
          ),
        ],
      ),
    );
  }
}
