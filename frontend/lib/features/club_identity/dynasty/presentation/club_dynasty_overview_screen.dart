import 'package:flutter/material.dart';

import '../../../../data/gte_api_repository.dart';
import 'dynasty_leaderboard_screen.dart';
import 'dynasty_screen.dart';
import 'era_history_screen.dart';

class ClubDynastyOverviewScreen extends StatelessWidget {
  const ClubDynastyOverviewScreen({
    super.key,
    required this.clubId,
    this.baseUrl = 'http://127.0.0.1:8000',
    this.backendMode = GteBackendMode.liveThenFixture,
  });

  final String clubId;
  final String baseUrl;
  final GteBackendMode backendMode;

  @override
  Widget build(BuildContext context) {
    return DynastyScreen(
      clubId: clubId,
      baseUrl: baseUrl,
      backendMode: backendMode,
      onOpenTimeline: () {
        Navigator.of(context).push<void>(
          MaterialPageRoute<void>(
            builder: (BuildContext context) => EraHistoryScreen(
              clubId: clubId,
              baseUrl: baseUrl,
              backendMode: backendMode,
            ),
          ),
        );
      },
      onOpenLeaderboard: () {
        Navigator.of(context).push<void>(
          MaterialPageRoute<void>(
            builder: (BuildContext context) => DynastyLeaderboardScreen(
              baseUrl: baseUrl,
              backendMode: backendMode,
            ),
          ),
        );
      },
    );
  }
}
