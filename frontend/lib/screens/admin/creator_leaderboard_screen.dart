import 'package:flutter/material.dart';

import '../../data/creator_api.dart';
import '../../models/creator_models.dart';
import '../../widgets/admin/creator_leaderboard_table.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';
import '../../widgets/gtex_branding.dart';

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
      appBar: AppBar(title: const Text('Creator leaderboard desk')),
      body: FutureBuilder<CreatorLeaderboardSnapshot>(
        future: _future,
        builder: (BuildContext context, AsyncSnapshot<CreatorLeaderboardSnapshot> snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Padding(
              padding: EdgeInsets.all(20),
              child: GteStatePanel(
                eyebrow: 'CREATOR LEADERBOARD',
                title: 'Loading creator leaderboard desk',
                message: 'Ranking top creators, strongest creator competitions, and qualified participation.',
                icon: Icons.leaderboard_outlined,
                accentColor: Color(0xFF9C6BFF),
              ),
            );
          }
          if (snapshot.hasError || !snapshot.hasData) {
            return Padding(
              padding: const EdgeInsets.all(20),
              child: GteStatePanel(
                eyebrow: 'CREATOR LEADERBOARD',
                title: 'Creator leaderboard desk unavailable',
                message: '${snapshot.error ?? 'Unknown error'}',
                icon: Icons.error_outline,
                accentColor: Color(0xFF9C6BFF),
                actionLabel: 'Retry',
                onAction: () => setState(() { _future = widget.api.fetchCreatorLeaderboard(); }),
              ),
            );
          }

          final CreatorLeaderboardSnapshot leaderboard = snapshot.data!;
          return SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                GtexHeroBanner(
                  eyebrow: 'CREATOR LEADERBOARD DESK',
                  title: 'Review who is converting attention into matchday participation, retention, and reward quality.',
                  description: 'This admin lane is tuned for promotion quality, creator reliability, and competition momentum. It should feel like an executive signal board, not a raw export.',
                  accent: const Color(0xFF9C6BFF),
                  chips: <Widget>[
                    Chip(label: Text('Creators ${leaderboard.entries.length}')),
                    Chip(label: Text(leaderboard.topCreatorLabel)),
                  ],
                ),
                const SizedBox(height: 16),
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
                if (leaderboard.entries.isEmpty)
                  const GteStatePanel(
                    eyebrow: 'CREATOR SIGNALS',
                    title: 'No creator ranking signal yet',
                    message: 'Once creator competitions and participation volume mature, the ranking table will appear here with growth and quality context.',
                    icon: Icons.insights_outlined,
                    accentColor: Color(0xFF9C6BFF),
                  )
                else
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
