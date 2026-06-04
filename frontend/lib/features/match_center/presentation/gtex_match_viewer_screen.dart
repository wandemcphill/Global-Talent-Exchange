import 'package:flutter/material.dart';
import 'package:gte_frontend/features/compete/domain/competition_models.dart';
import 'package:gte_frontend/features/match_center/data/match_gift_api.dart';
import 'package:gte_frontend/features/match_center/models/match_view_state.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';

typedef MatchViewStateLoader = Future<MatchViewState> Function();
typedef MatchViewContinuationLoader =
    Future<MatchViewState> Function({
      required String matchKey,
      required String continuationToken,
    });

class GtexMatchViewerScreen extends StatelessWidget {
  const GtexMatchViewerScreen({
    super.key,
    required this.competition,
    required this.matchKey,
    Object? presentationMode,
    Object? renderMode,
    this.viewStateLoader,
    this.continuationLoader,
    Object? entitlement,
    this.isSpectator = false,
    Object? engagementService,
    this.giftClient,
    this.titleOverride,
    Object? engineBridge,
    Object? androidLiveBootstrapProvisioner,
  });

  static const Key quarantinePanelKey = Key('match-viewer-quarantine-panel');
  static const String quarantineTitle = 'Match viewer quarantined';
  static const String quarantineMessage =
      'The legacy local 2D playback viewer is quarantined for launch. '
      'Use the live match center so matchday playback stays backend-routed '
      'and production-authoritative.';

  final CompetitionSummary competition;
  final String matchKey;
  final MatchViewStateLoader? viewStateLoader;
  final MatchViewContinuationLoader? continuationLoader;
  final bool isSpectator;
  final MatchGiftClient? giftClient;
  final String? titleOverride;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: const Scaffold(
        backgroundColor: Colors.transparent,
        body: SafeArea(
          child: Padding(
            padding: EdgeInsets.all(20),
            child: Center(
              child: GteStatePanel(
                key: quarantinePanelKey,
                eyebrow: 'MATCHDAY',
                title: quarantineTitle,
                message: quarantineMessage,
                icon: Icons.block,
                accentColor: GteShellTheme.accentArena,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
