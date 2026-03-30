import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/platform/gtex_platform_experience_controller.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match/gtex_match_render_mode.dart';
import 'package:gte_frontend/models/match/gtex_match_view_type.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/models/platform/gtex_platform_experience.dart';
import 'package:gte_frontend/services/match_3d_monetization_service.dart';
import 'package:gte_frontend/widgets/gte_route_integrity_screen.dart';

typedef GtexBroadcastViewStateLoader = Future<MatchViewState> Function();
typedef GtexBroadcastMultiMatchLoader =
    Future<MatchViewState> Function(String matchId);

class GtexMatchBroadcastScreen extends StatelessWidget {
  const GtexMatchBroadcastScreen({
    super.key,
    required this.matchId,
    required this.initialMode,
    required this.viewType,
    required this.isPremiumUser,
    required this.spectatorMode,
    required this.auto3DEnabled,
    this.competition,
    this.competitionId,
    this.fallbackSnapshot,
    this.preferFallback = false,
    this.viewStateLoader,
    this.entitlement,
    this.titleOverride,
    this.competitionLabel,
    this.onOpenHighlights,
    this.platformMode = GtexPlatformMode.mobile,
    this.platformController,
    this.multiMatchViewStateLoader,
    this.onChannelSelected,
  });

  final String matchId;
  final GtexMatchRenderMode initialMode;
  final GtexMatchViewType viewType;
  final bool isPremiumUser;
  final bool spectatorMode;
  final bool auto3DEnabled;
  final CompetitionSummary? competition;
  final String? competitionId;
  final LiveMatchSnapshot? fallbackSnapshot;
  final bool preferFallback;
  final GtexBroadcastViewStateLoader? viewStateLoader;
  final Match3dUserEntitlement? entitlement;
  final String? titleOverride;
  final String? competitionLabel;
  final VoidCallback? onOpenHighlights;
  final GtexPlatformMode platformMode;
  final GtexPlatformExperienceController? platformController;
  final GtexBroadcastMultiMatchLoader? multiMatchViewStateLoader;
  final ValueChanged<GtexTvChannel>? onChannelSelected;

  @override
  Widget build(BuildContext context) {
    return const GteRouteIntegrityScreen.blocked(
      title: 'Match broadcast unavailable',
      message:
          'Broadcast routes are blocked until live broadcast sessions can be served without fallback snapshots or fabricated event streams.',
      icon: Icons.podcasts_outlined,
    );
  }
}
