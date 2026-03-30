import 'package:flutter/material.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/widgets/gte_route_integrity_screen.dart';

typedef GteLiveCommentaryStreamLoader =
    Stream<List<LiveMatchEvent>> Function(LiveMatchSnapshot match);

class GteLiveMatchCenterScreen extends StatelessWidget {
  const GteLiveMatchCenterScreen({
    super.key,
    required this.competition,
    this.isAuthenticated = false,
    this.onOpenLogin,
    this.navigationDependencies,
    this.snapshotLoader,
    this.commentaryStreamLoader,
  });

  final CompetitionSummary competition;
  final bool isAuthenticated;
  final VoidCallback? onOpenLogin;
  final GteNavigationDependencies? navigationDependencies;
  final Future<LiveMatchSnapshot> Function(CompetitionSummary competition)?
  snapshotLoader;
  final GteLiveCommentaryStreamLoader? commentaryStreamLoader;

  @override
  Widget build(BuildContext context) {
    return const GteRouteIntegrityScreen.blocked(
      title: 'Live match center unavailable',
      message:
          'Live match center routes are blocked until snapshots, commentary, and watch surfaces are served from the real backend without fabricated fallback data.',
      icon: Icons.stadium_outlined,
    );
  }
}
