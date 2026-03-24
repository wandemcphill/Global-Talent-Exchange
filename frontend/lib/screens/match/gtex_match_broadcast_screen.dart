import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'package:gte_frontend/controllers/match/gtex_match_broadcast_controller.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match/gtex_match_render_mode.dart';
import 'package:gte_frontend/models/match/gtex_match_view_type.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/services/match_3d_monetization_service.dart';
import 'package:gte_frontend/services/match_viewer_mapper.dart';
import 'package:gte_frontend/widgets/match/broadcast/gtex_broadcast_hud_layer.dart';
import 'package:gte_frontend/widgets/match/broadcast/gtex_gifting_sheet.dart';
import 'package:gte_frontend/widgets/match/broadcast/gtex_match_broadcast_app_bar.dart';
import 'package:gte_frontend/widgets/match/broadcast/gtex_match_canvas_layer.dart';

typedef GtexBroadcastViewStateLoader = Future<MatchViewState> Function();

class GtexMatchBroadcastScreen extends StatefulWidget {
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

  @override
  State<GtexMatchBroadcastScreen> createState() =>
      _GtexMatchBroadcastScreenState();
}

class _GtexMatchBroadcastScreenState extends State<GtexMatchBroadcastScreen>
    with SingleTickerProviderStateMixin {
  late Future<MatchViewState> _viewStateFuture;
  GtexMatchBroadcastController? _controller;
  Ticker? _ticker;
  Duration? _lastTickElapsed;

  @override
  void initState() {
    super.initState();
    _viewStateFuture = _load();
    _ticker = createTicker(_onTick);
  }

  @override
  void dispose() {
    _ticker?.dispose();
    _controller?.removeListener(_handleControllerChanged);
    _controller?.dispose();
    super.dispose();
  }

  Future<MatchViewState> _load() {
    if (widget.viewStateLoader != null) {
      return widget.viewStateLoader!();
    }
    final CompetitionSummary? competition = widget.competition;
    if (competition == null) {
      return Future<MatchViewState>.error(
        StateError(
          'GtexMatchBroadcastScreen needs either a competition or a viewStateLoader.',
        ),
      );
    }
    return MatchViewerMapper.load(
      competition: competition,
      matchKey: widget.matchId,
      fallbackSnapshot: widget.fallbackSnapshot,
      preferFallback: widget.preferFallback,
    );
  }

  void _onTick(Duration elapsed) {
    final Duration? previous = _lastTickElapsed;
    _lastTickElapsed = elapsed;
    if (previous == null) {
      return;
    }
    _controller?.advanceBy(elapsed - previous);
  }

  void _handleControllerChanged() {
    if (!mounted) {
      return;
    }
    _syncTicker();
    setState(() {});
  }

  void _syncTicker() {
    final GtexMatchBroadcastController? controller = _controller;
    if (controller == null) {
      return;
    }
    final bool shouldTick = !controller.isPaused && !controller.isFullTime;
    if (shouldTick && !(_ticker?.isActive ?? false)) {
      _lastTickElapsed = null;
      _ticker?.start();
    } else if (!shouldTick && (_ticker?.isActive ?? false)) {
      _ticker?.stop();
      _lastTickElapsed = null;
    }
  }

  GtexMatchBroadcastController _ensureController(MatchViewState viewState) {
    final GtexMatchBroadcastController? existing = _controller;
    if (existing != null && existing.viewState.matchId == viewState.matchId) {
      return existing;
    }
    existing?.removeListener(_handleControllerChanged);
    existing?.dispose();
    final GtexMatchBroadcastController created = GtexMatchBroadcastController(
      viewState: viewState,
      initialMode: widget.initialMode,
      initialViewType: widget.viewType,
      isPremiumUser: widget.isPremiumUser,
      spectatorMode: widget.spectatorMode,
      auto3DEnabled: widget.auto3DEnabled,
      competitionId: widget.competitionId ?? widget.competition?.id,
      entitlement: widget.entitlement,
    );
    created.addListener(_handleControllerChanged);
    _controller = created;
    _syncTicker();
    return created;
  }

  void _showGiftSheet() {
    GtexGiftingSheet.show(
      context,
      onSelected: (double amount) {
        if (!mounted) {
          return;
        }
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('${amount.toStringAsFixed(1)} coin gift'),
          ),
        );
      },
    );
  }

  void _toggleViewType(GtexMatchBroadcastController controller) {
    if (!controller.canUsePseudo3D) {
      return;
    }
    controller.setViewType(
      controller.viewType == GtexMatchViewType.pseudo3D
          ? GtexMatchViewType.twoD
          : GtexMatchViewType.pseudo3D,
    );
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<MatchViewState>(
      future: _viewStateFuture,
      builder: (
        BuildContext context,
        AsyncSnapshot<MatchViewState> snapshot,
      ) {
        final bool loading =
            snapshot.connectionState == ConnectionState.waiting;
        if (loading) {
          return const Scaffold(
            backgroundColor: Color(0xFF08111B),
            body: Center(
              child: CircularProgressIndicator(),
            ),
          );
        }
        if (snapshot.hasError || !snapshot.hasData) {
          return Scaffold(
            backgroundColor: const Color(0xFF08111B),
            body: Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    const Icon(
                      Icons.warning_amber_rounded,
                      color: Colors.white70,
                      size: 40,
                    ),
                    const SizedBox(height: 12),
                    Text(
                      'Unable to load the broadcast viewer.',
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                            color: Colors.white,
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                    const SizedBox(height: 12),
                    FilledButton(
                      onPressed: () {
                        setState(() {
                          _viewStateFuture = _load();
                        });
                      },
                      child: const Text('Retry'),
                    ),
                  ],
                ),
              ),
            ),
          );
        }

        final MatchViewState viewState = snapshot.data!;
        final GtexMatchBroadcastController controller =
            _ensureController(viewState);
        final String matchTitle = widget.titleOverride ??
            '${viewState.homeTeam.teamName} vs ${viewState.awayTeam.teamName}';
        final String competitionLabel = widget.competitionLabel ??
            widget.competition?.name ??
            'GTEX Broadcast';

        return GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTap: controller.showControls,
          child: Scaffold(
            backgroundColor: const Color(0xFF07111A),
            appBar: GtexMatchBroadcastAppBar(
              title: matchTitle,
              competitionLabel: competitionLabel,
              mode: controller.mode,
              viewType: controller.viewType,
              canToggleViewType: controller.canUsePseudo3D,
              onModeSelected: controller.setMode,
              onToggleViewType: () => _toggleViewType(controller),
            ),
            body: SafeArea(
              top: false,
              child: Stack(
                fit: StackFit.expand,
                children: <Widget>[
                  Center(
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(10, 12, 10, 16),
                      child: GtexMatchCanvasLayer(
                        viewState: viewState,
                        frame: controller.currentFrame,
                        hudState: controller.hudState,
                        viewType: controller.viewType,
                      ),
                    ),
                  ),
                  GtexBroadcastHudLayer(
                    viewState: viewState,
                    hudState: controller.hudState,
                    matchTitle: matchTitle,
                    competitionLabel: competitionLabel,
                    onTogglePause: controller.togglePause,
                    onCycleSpeed: controller.cycleSpeed,
                    onReplay: controller.replay,
                    onGiftTap: _showGiftSheet,
                    onOpenHighlights: widget.onOpenHighlights,
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}
