import 'package:flutter/material.dart';

import '../../core/constants/app_spacing.dart';
import '../../data/live_match_fixtures.dart';
import '../../data/match/match_simulation_engine.dart';
import '../../data/match/match_simulation_models.dart';
import '../../models/competition_models.dart';
import '../../models/match_type.dart';
import '../../screens/match/gtex_match_simulation_screen.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';

class MatchSimulateScreen extends StatefulWidget {
  const MatchSimulateScreen({super.key});

  @override
  State<MatchSimulateScreen> createState() => _MatchSimulateScreenState();
}

class _MatchSimulateScreenState extends State<MatchSimulateScreen> {
  final TextEditingController _homeController = TextEditingController(
    text: 'GTEX Academy',
  );
  final TextEditingController _awayController = TextEditingController(
    text: 'Regens United',
  );

  @override
  void dispose() {
    _homeController.dispose();
    _awayController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AppPageLayout(
      title: 'Simulate',
      subtitle:
          'Fixture-mode simulation stays separate from live spectating. This route launches the local simulation engine without pretending it is a backend feed.',
      trailing: const DataSourceBadge(status: DataSourceStatus.demo),
      children: <Widget>[
        Card(
          child: Padding(
            padding: const EdgeInsets.all(spacingLG),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                const Text(
                  'Simulation is available only in explicit fixture mode. It stays honest, labeled, and separate from the live spectate path.',
                ),
                const SizedBox(height: spacingMD),
                TextField(
                  controller: _homeController,
                  decoration: const InputDecoration(labelText: 'Home team'),
                ),
                const SizedBox(height: spacingMD),
                TextField(
                  controller: _awayController,
                  decoration: const InputDecoration(labelText: 'Away team'),
                ),
                const SizedBox(height: spacingMD),
                FilledButton(
                  onPressed: _launchSimulation,
                  child: const Text('Launch simulation'),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Future<void> _launchSimulation() async {
    final String home =
        _homeController.text.trim().isEmpty
            ? 'GTEX Academy'
            : _homeController.text.trim();
    final String away =
        _awayController.text.trim().isEmpty
            ? 'Regens United'
            : _awayController.text.trim();
    final DateTime now = DateTime.now().toUtc();
    final CompetitionSummary seedCompetition = CompetitionSummary(
      id: '$home-v-$away'.toLowerCase().replaceAll(RegExp(r'[^a-z0-9]+'), '-'),
      name: '$home vs $away',
      format: CompetitionFormat.cup,
      visibility: CompetitionVisibility.public,
      status: CompetitionStatus.published,
      creatorId: 'simulation',
      creatorName: 'Fixture Simulation',
      participantCount: 2,
      capacity: 2,
      currency: 'coin',
      entryFee: 0,
      platformFeePct: 0,
      hostFeePct: 0,
      platformFeeAmount: 0,
      hostFeeAmount: 0,
      prizePool: 0,
      payoutStructure: const <CompetitionPayoutBreakdown>[],
      rulesSummary: 'Fixture-mode local simulation route',
      matchType: MatchType.fastMatch,
      joinEligibility: const CompetitionJoinEligibility(
        eligible: false,
        reason: 'simulation_only',
      ),
      beginnerFriendly: true,
      createdAt: now,
      updatedAt: now,
    );
    final LiveMatchSnapshot base = LiveMatchFixtures.buildSnapshot(
      seedCompetition,
    );
    final LiveMatchSnapshot snapshot = LiveMatchSnapshot(
      matchId: seedCompetition.id,
      homeTeam: home,
      awayTeam: away,
      homeScore: 0,
      awayScore: 0,
      minute: 0,
      phase: LiveMatchPhase.preMatch,
      momentum: const <int>[50, 50, 50, 50, 50],
      commentary: const <LiveMatchEvent>[],
      homeLineup: base.homeLineup,
      awayLineup: base.awayLineup,
      substitutions: const <LiveMatchEvent>[],
      cards: const <LiveMatchEvent>[],
      tacticalSuggestions: const <LiveMatchTacticalSuggestion>[],
      keyMoments: const <LiveMatchHighlightClip>[],
      highlights: const <LiveMatchHighlightClip>[],
      standardHighlightExpiresAt: now.add(const Duration(minutes: 10)),
      premiumHighlightExpiresAt: now.add(const Duration(hours: 1)),
    );
    final MatchSimulationRequest request =
        MatchSimulationRequestFactory.fromLiveSnapshot(
          snapshot,
          importance: MatchSimulationImportance.quickMatch,
        );
    final MatchSimulationResult result = const MatchSimulationEngine().simulate(
      request,
    );
    if (!mounted) {
      return;
    }
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder:
            (BuildContext context) => GtexMatchSimulationScreen(
              result: result,
              title: '$home vs $away',
              competitionLabel: 'Simulation',
            ),
      ),
    );
  }
}
