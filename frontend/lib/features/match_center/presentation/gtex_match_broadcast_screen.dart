import 'package:flutter/material.dart';
import 'package:gte_frontend/features/match_center/controllers/gtex_match_broadcast_controller.dart';
import 'package:gte_frontend/controllers/platform/gtex_platform_experience_controller.dart';
import 'package:gte_frontend/features/compete/domain/competition_models.dart';
import 'package:gte_frontend/features/match_center/models/match/gtex_broadcast_hud_state.dart';
import 'package:gte_frontend/features/match_center/models/match/gtex_match_render_mode.dart';
import 'package:gte_frontend/features/match_center/models/match/gtex_match_view_type.dart';
import 'package:gte_frontend/features/match_center/models/match_timeline_frame.dart';
import 'package:gte_frontend/features/match_center/models/match_view_state.dart';
import 'package:gte_frontend/models/platform/gtex_platform_experience.dart';
import 'package:gte_frontend/features/match_center/services/match_viewer_mapper.dart';
import 'package:gte_frontend/features/match_center/widgets/broadcast/gtex_broadcast_hud_layer.dart';
import 'package:gte_frontend/features/match_center/widgets/broadcast/gtex_match_broadcast_app_bar.dart';
import 'package:gte_frontend/features/match_center/widgets/broadcast/gtex_match_canvas_layer.dart';
import 'package:gte_frontend/features/match_center/widgets/broadcast/gtex_tv_mode_shell.dart';
import 'package:gte_frontend/features/match_center/widgets/broadcast/gtex_web_mode_sidebar.dart';

typedef GtexBroadcastViewStateLoader = Future<MatchViewState> Function();
typedef GtexBroadcastMultiMatchLoader =
    Future<MatchViewState> Function(String matchId);

class GtexMatchBroadcastScreen extends StatefulWidget {
  const GtexMatchBroadcastScreen({
    super.key,
    required this.matchId,
    required this.initialMode,
    required this.viewType,
    required this.isPremiumUser,
    required this.spectatorMode,
    this.competition,
    this.competitionId,
    this.viewStateLoader,
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
  final CompetitionSummary? competition;
  final String? competitionId;
  final GtexBroadcastViewStateLoader? viewStateLoader;
  final String? titleOverride;
  final String? competitionLabel;
  final VoidCallback? onOpenHighlights;
  final GtexPlatformMode platformMode;
  final GtexPlatformExperienceController? platformController;
  final GtexBroadcastMultiMatchLoader? multiMatchViewStateLoader;
  final ValueChanged<GtexTvChannel>? onChannelSelected;

  @override
  State<GtexMatchBroadcastScreen> createState() =>
      _GtexMatchBroadcastScreenState();
}

class _GtexMatchBroadcastScreenState extends State<GtexMatchBroadcastScreen> {
  late Future<MatchViewState> _viewStateFuture;
  GtexMatchBroadcastController? _controller;
  GtexPlatformExperienceController? _platformController;
  bool _ownsPlatformController = false;
  late String _activeMatchId;
  bool _tvFullTimeHandled = false;

  @override
  void initState() {
    super.initState();
    _activeMatchId = widget.matchId;
    _configurePlatformController();
    _viewStateFuture = _load();
  }

  @override
  void didUpdateWidget(covariant GtexMatchBroadcastScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (_sourceConfigChanged(oldWidget)) {
      _activeMatchId = widget.matchId;
      _reloadViewState();
      return;
    }
    if (_controllerConfigChanged(oldWidget)) {
      _disposeController();
      setState(() {});
    }
    if (oldWidget.platformController != widget.platformController ||
        oldWidget.platformMode != widget.platformMode) {
      _disposePlatformController();
      _configurePlatformController();
      setState(() {});
    }
  }

  @override
  void dispose() {
    _disposeController();
    _disposePlatformController();
    super.dispose();
  }

  Future<MatchViewState> _load() {
    if (widget.multiMatchViewStateLoader != null) {
      return widget.multiMatchViewStateLoader!(_activeMatchId);
    }
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
      matchKey: _activeMatchId,
    );
  }

  void _handleControllerChanged() {
    final GtexMatchBroadcastController? controller = _controller;
    if (widget.platformMode == GtexPlatformMode.tv && controller != null) {
      if (controller.isFullTime) {
        if (!_tvFullTimeHandled) {
          _tvFullTimeHandled = true;
          final GtexTvChannel? nextChannel =
              _platformController?.handleMatchFinished();
          if (nextChannel != null) {
            _handleChannelSelected(nextChannel);
          }
        }
      } else {
        _tvFullTimeHandled = false;
      }
    }
    if (!mounted) {
      return;
    }
    setState(() {});
  }

  GtexMatchBroadcastController _ensureController(MatchViewState viewState) {
    final GtexMatchBroadcastController? existing = _controller;
    if (existing != null &&
        _canReuseController(existing.viewState, viewState)) {
      return existing;
    }
    _disposeController();
    final GtexMatchBroadcastController created = GtexMatchBroadcastController(
      viewState: viewState,
      initialMode: widget.initialMode,
      initialViewType: widget.viewType,
      isPremiumUser: widget.isPremiumUser,
      spectatorMode: widget.spectatorMode,
      competitionId: widget.competitionId ?? widget.competition?.id,
    );
    created.addListener(_handleControllerChanged);
    _controller = created;
    return created;
  }

  void _disposeController() {
    _controller?.removeListener(_handleControllerChanged);
    _controller?.dispose();
    _controller = null;
  }

  void _reloadViewState() {
    _disposeController();
    setState(() {
      _viewStateFuture = _load();
    });
  }

  void _switchToMatch(String matchId) {
    if (_activeMatchId == matchId) {
      return;
    }
    _activeMatchId = matchId;
    _reloadViewState();
  }

  void _handleChannelSelected(GtexTvChannel channel) {
    widget.onChannelSelected?.call(channel);
    if (channel.matchId != null) {
      _switchToMatch(channel.matchId!);
    }
  }

  void _configurePlatformController() {
    if (widget.platformController != null) {
      _platformController = widget.platformController;
      _ownsPlatformController = false;
    } else {
      _platformController = GtexPlatformExperienceController(
        mode: widget.platformMode,
      );
      _ownsPlatformController = true;
    }
    _platformController?.switchMode(widget.platformMode);
  }

  void _disposePlatformController() {
    if (_ownsPlatformController) {
      _platformController?.dispose();
    }
    _platformController = null;
    _ownsPlatformController = false;
  }

  bool _sourceConfigChanged(GtexMatchBroadcastScreen oldWidget) {
    return oldWidget.matchId != widget.matchId ||
        oldWidget.competition != widget.competition ||
        oldWidget.competitionId != widget.competitionId ||
        oldWidget.viewStateLoader != widget.viewStateLoader ||
        oldWidget.multiMatchViewStateLoader != widget.multiMatchViewStateLoader;
  }

  bool _controllerConfigChanged(GtexMatchBroadcastScreen oldWidget) {
    return oldWidget.initialMode != widget.initialMode ||
        oldWidget.viewType != widget.viewType ||
        oldWidget.isPremiumUser != widget.isPremiumUser ||
        oldWidget.spectatorMode != widget.spectatorMode;
  }

  bool _canReuseController(MatchViewState current, MatchViewState next) {
    if (current.matchId != next.matchId ||
        current.durationSeconds != next.durationSeconds ||
        current.frames.length != next.frames.length ||
        current.events.length != next.events.length ||
        current.segmentEndSeconds != next.segmentEndSeconds ||
        current.nextSegmentToken != next.nextSegmentToken) {
      return false;
    }
    if (current.frames.isEmpty || next.frames.isEmpty) {
      return false;
    }
    return current.lastFrame.id == next.lastFrame.id &&
        current.lastFrame.timeSeconds == next.lastFrame.timeSeconds;
  }

  double _backendDisplaySeconds(MatchViewState viewState) {
    if (viewState.frames.isEmpty) {
      return 0;
    }
    final double lastFrameSeconds = viewState.lastFrame.timeSeconds;
    final int segmentEndSeconds = viewState.segmentEndSeconds;
    if (segmentEndSeconds > 0) {
      final double authoredSegmentEnd = segmentEndSeconds.toDouble();
      return authoredSegmentEnd > lastFrameSeconds
          ? lastFrameSeconds
          : authoredSegmentEnd;
    }
    return lastFrameSeconds;
  }

  GtexBroadcastHudState _buildBackendHudState({
    required GtexMatchBroadcastController controller,
    required MatchTimelineFrame frame,
    required double displaySeconds,
  }) {
    final MatchViewState viewState = controller.viewState;
    final bool isFullTime =
        frame.phase == MatchViewerPhase.fulltime ||
        (viewState.durationSeconds > 0 &&
            displaySeconds >= viewState.durationSeconds - 0.05);
    return controller.overlayController.buildHudState(
      viewState: viewState,
      mode: controller.mode,
      viewType: controller.viewType,
      frame: frame,
      viewerSeconds: displaySeconds,
      isPaused: false,
      speedLabel: controller.speedLabel,
      scoreMasked: viewState.scoreRevealLocked,
      homeScore: viewState.scoreRevealLocked ? null : frame.homeScore,
      awayScore: viewState.scoreRevealLocked ? null : frame.awayScore,
      spectatorMode: widget.spectatorMode,
      isFullTime: isFullTime,
    );
  }

  void _showBackendFrameControls(
    GtexMatchBroadcastController controller,
    double displaySeconds,
  ) {
    controller.overlayController.showControls(displaySeconds);
    if (mounted) {
      setState(() {});
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<MatchViewState>(
      future: _viewStateFuture,
      builder: (BuildContext context, AsyncSnapshot<MatchViewState> snapshot) {
        final bool loading =
            snapshot.connectionState == ConnectionState.waiting;
        if (loading) {
          return const Scaffold(
            backgroundColor: Color(0xFF08111B),
            body: Center(child: CircularProgressIndicator()),
          );
        }
        if (snapshot.hasError || !snapshot.hasData) {
          return _buildFailureScaffold(
            context,
            title: 'Unable to load the broadcast viewer.',
          );
        }

        final MatchViewState viewState = snapshot.data!;
        if (viewState.frames.isEmpty) {
          return _buildFailureScaffold(
            context,
            title: 'Broadcast timeline incomplete.',
            message: 'The signed spectator feed did not include any frames.',
          );
        }
        final GtexMatchBroadcastController controller = _ensureController(
          viewState,
        );
        final double displaySeconds = _backendDisplaySeconds(viewState);
        final MatchTimelineFrame displayFrame = controller
            .frameAtAuthoritativeSeconds(displaySeconds);
        final GtexBroadcastHudState displayHudState = _buildBackendHudState(
          controller: controller,
          frame: displayFrame,
          displaySeconds: displaySeconds,
        );
        final String matchTitle =
            widget.titleOverride ??
            '${viewState.homeTeam.teamName} vs ${viewState.awayTeam.teamName}';
        final String competitionLabel =
            widget.competitionLabel ??
            widget.competition?.name ??
            'GTEX Broadcast';
        final GtexPlatformExperienceController? platformController =
            _platformController;

        Widget broadcastViewport = Stack(
          fit: StackFit.expand,
          children: <Widget>[
            Center(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(10, 12, 10, 16),
                child: GtexMatchCanvasLayer(
                  viewState: viewState,
                  frame: displayFrame,
                  hudState: displayHudState,
                  viewType: controller.viewType,
                ),
              ),
            ),
            GtexBroadcastHudLayer(
              viewState: viewState,
              hudState: displayHudState,
              platformMode: widget.platformMode,
              matchTitle: matchTitle,
              competitionLabel: competitionLabel,
              onSyncFrame: _reloadViewState,
              onGiftTap: () {},
              onOpenHighlights: widget.onOpenHighlights,
            ),
          ],
        );

        if (widget.platformMode == GtexPlatformMode.web &&
            platformController != null) {
          broadcastViewport = Row(
            children: <Widget>[
              Expanded(child: broadcastViewport),
              SizedBox(
                width: 300,
                child: GtexWebModeSidebar(
                  controller: platformController,
                  matchTitle: matchTitle,
                ),
              ),
            ],
          );
        }

        if (widget.platformMode == GtexPlatformMode.tv &&
            platformController != null) {
          broadcastViewport = Stack(
            fit: StackFit.expand,
            children: <Widget>[
              broadcastViewport,
              GtexTvModeShell(
                controller: platformController,
                matchTitle: matchTitle,
                onChannelSelected: _handleChannelSelected,
              ),
            ],
          );
        }

        return GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTap: () => _showBackendFrameControls(controller, displaySeconds),
          child: Scaffold(
            backgroundColor: const Color(0xFF07111A),
            appBar:
                widget.platformMode == GtexPlatformMode.tv
                    ? null
                    : GtexMatchBroadcastAppBar(
                      title: matchTitle,
                      competitionLabel: competitionLabel,
                      mode: controller.mode,
                      onModeSelected: controller.setMode,
                    ),
            body: SafeArea(
              top: widget.platformMode == GtexPlatformMode.tv,
              child: broadcastViewport,
            ),
          ),
        );
      },
    );
  }

  Widget _buildFailureScaffold(
    BuildContext context, {
    required String title,
    String? message,
  }) {
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
                title,
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w700,
                ),
              ),
              if (message != null) ...<Widget>[
                const SizedBox(height: 12),
                Text(
                  message,
                  textAlign: TextAlign.center,
                  style: Theme.of(
                    context,
                  ).textTheme.bodyMedium?.copyWith(color: Colors.white70),
                ),
              ],
              const SizedBox(height: 12),
              FilledButton(
                onPressed: _reloadViewState,
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
