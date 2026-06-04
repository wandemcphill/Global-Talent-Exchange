import 'package:flutter/material.dart';

import '../../../shared/models/player.dart';
import 'live_competitions_hub_screen.dart';

class Competition {
  const Competition({
    required this.name,
    required this.region,
    required this.stage,
    required this.nextFixture,
    required this.spotlight,
  });

  final String name;
  final String region;
  final String stage;
  final String nextFixture;
  final String spotlight;
}

class TournamentsScreen extends StatelessWidget {
  const TournamentsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const LiveCompetitionsHubScreen();
  }
}

class TournamentIntroScreen extends StatelessWidget {
  const TournamentIntroScreen({
    super.key,
    required this.competition,
    this.videoAssetPath,
    this.fixtures,
    this.standings,
    this.squad,
    this.onEnterTournament,
  });

  final Competition competition;
  final String? videoAssetPath;
  final Object? fixtures;
  final Object? standings;
  final List<Player>? squad;
  final VoidCallback? onEnterTournament;

  @override
  Widget build(BuildContext context) {
    return const LiveCompetitionsHubScreen();
  }
}

class TournamentScreen extends StatelessWidget {
  const TournamentScreen({
    super.key,
    required this.competition,
    this.fixtures,
    this.standings,
    this.squad,
  });

  final Competition competition;
  final Object? fixtures;
  final Object? standings;
  final List<Player>? squad;

  @override
  Widget build(BuildContext context) {
    return const LiveCompetitionsHubScreen();
  }
}
