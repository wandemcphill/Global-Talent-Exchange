import 'package:flutter/material.dart';

import '../../data/creator_api.dart';
import '../../models/creator_models.dart';
import '../../widgets/admin/creator_leaderboard_table.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';

class CreatorLeaderboardScreen extends StatefulWidget {
  const CreatorLeaderboardScreen({
    super.key,
    required this.api,
  });

  final CreatorApi api;

  @override
  State<CreatorLeaderboardScreen> createState() => _CreatorLeaderboardScreenState();
}

class _CreatorLeaderboardScreenState extends State<CreatorLeaderboardScreen> {
  late Future<CreatorLeaderboardSnapshot> _future;

  @override
  void initState() {
    super.initState();
    _future = widget.api.fetchCreatorLeaderboard();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Creator leaderboard')),
      body: FutureBuilder<CreatorLeaderboardSnapshot>(
        future: _future,
        builder: (BuildContext context, AsyncSnapshot<CreatorLeaderboardSnapshot> snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Padding(
              padding: EdgeInsets.all(20),
              child: GteStatePanel(
                title: 'Loading creator leaderboard',
                message: 'Ranking top creators, strongest creator competitions, and qualified participation.',
                icon: Icons.leaderboard_outlined,
              ),
            );
          }
          if (snapshot.hasError || !snapshot.hasData) {
            return Padding(
              padding: const EdgeInsets.all(20),
              child: GteStatePanel(
                title: 'Creator leaderboard unavailable',
                message: '${snapshot.error ?? 'Unknown error'}',
                icon: Icons.error_outline,
              ),
            );
          }

          final CreatorLeaderboardSnapshot leaderboard = snapshot.data!;
          return SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                GteSurfacePanel(
                  emphasized: true,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        leaderboard.growthHeadline,
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        leaderboard.growthDetail,
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: <Widget>[
                    _SummaryCard(label: 'Top creator', value: leaderboard.topCreatorLabel),
                    _SummaryCard(
                      label: 'Strongest creator competition',
                      value: leaderboard.strongestCompetitionLabel,
                    ),
                    _SummaryCard(
                      label: 'Highest qualified participation',
                      value: leaderboard.highestQualifiedParticipationLabel,
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                CreatorLeaderboardTable(entries: leaderboard.entries),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _SummaryCard extends StatelessWidget {
  const _SummaryCard({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 240,
      child: GteSurfacePanel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              label,
              style: Theme.of(context).textTheme.labelLarge,
            ),
            const SizedBox(height: 8),
            Text(
              value,
              style: Theme.of(context).textTheme.titleMedium,
            ),
          ],
        ),
      ),
    );
  }
}
