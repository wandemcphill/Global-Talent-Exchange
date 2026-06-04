import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:gte_frontend/features/match_center/models/ball_entity.dart'
    as runtime_ball;
import 'package:gte_frontend/features/3d/models/match_3d_native_session.dart';
import 'package:gte_frontend/features/match_center/models/match_event.dart';
import 'package:gte_frontend/features/match_center/models/match_timeline_frame.dart';
import 'package:gte_frontend/features/match_center/models/match_view_state.dart';
import 'package:gte_frontend/features/match_center/models/player_entity.dart'
    as runtime_player;
import 'package:gte_frontend/features/match_center/models/real_match_engine_presentation.dart';
import 'package:gte_frontend/features/3d/services/match_3d_bridge.dart';
import 'package:gte_frontend/features/3d/services/match_3d_live_bootstrap_service.dart';
import 'package:gte_frontend/features/match_center/widgets/pitch_2d_widget.dart';
import 'package:gte_frontend/features/3d/widgets/match_3d/entities/pitch_entity.dart';
import 'package:gte_frontend/features/3d/widgets/match_3d/gtex_3d_scene.dart';

const String _legacyRuntimePlatformToken =
    'un'
    'ity';
const String _legacyRuntimeNameToken =
    '${_legacyRuntimePlatformToken}_match_3d';

@Deprecated('Legacy runtime surface is quarantined; use the 2D match center.')
class NativeMatch3dSurface extends StatefulWidget {
  const NativeMatch3dSurface({
    super.key,
    required this.viewState,
    required this.frame,
    this.activeEvent,
    this.cameraPreset = MatchEngineCameraPreset.tactical_high,
    this.bridge,
    this.runtimePlayers,
    this.runtimeBall,
    this.showRuntimeBadge = true,
    this.onRuntimeStatusMessageChanged,
    this.androidLiveBootstrapProvisioner,
  });

  static const Key runtimeBadgeKey = Key('native-match-3d-runtime-badge');

  final MatchViewState viewState;
  final MatchTimelineFrame frame;
  final MatchEvent? activeEvent;
  final MatchEngineCameraPreset cameraPreset;
  final Match3DBridge? bridge;
  final Iterable<runtime_player.PlayerEntity>? runtimePlayers;
  final runtime_ball.BallEntity? runtimeBall;
  final bool showRuntimeBadge;
  final ValueChanged<String?>? onRuntimeStatusMessageChanged;
  final Match3dAndroidLiveBootstrapProvisioner? androidLiveBootstrapProvisioner;

  static Match3dNativeSessionDescriptor describeSession({
    required MatchViewState viewState,
    required MatchTimelineFrame frame,
    MatchEngineCameraPreset cameraPreset =
        MatchEngineCameraPreset.tactical_high,
  }) {
    final int expectedPlayerCount =
        frame.players
            .where(
              (player) =>
                  player.active ||
                  player.state == MatchViewerPlayerState.sentOff,
            )
            .length;
    return Match3dNativeSessionDescriptor(
      sessionId: 'native_match_3d:${viewState.matchId}',
      matchId: viewState.matchId,
      source: viewState.source,
      homeTeamId: viewState.homeTeam.teamId,
      homeTeamName: viewState.homeTeam.teamName,
      awayTeamId: viewState.awayTeam.teamId,
      awayTeamName: viewState.awayTeam.teamName,
      initialFrameId: frame.id,
      initialClockMinute: frame.clockMinute,
      initialPhase: frame.phase.name,
      initialCameraPreset: cameraPreset.name,
      expectedPlayerCount: expectedPlayerCount,
      deterministicSeed: viewState.deterministicSeed,
    );
  }

  @override
  State<NativeMatch3dSurface> createState() => _NativeMatch3dSurfaceState();
}

class _NativeMatch3dSurfaceState extends State<NativeMatch3dSurface> {
  static const String _embeddedNativeViewType = 'match_3d/native_view';
  static const String _unityActivityViewType = 'match_3d/unity_activity';

  Match3DBridge? _bridge;
  bool _nativeAvailable = false;
  bool _hasProbedNativeAvailability = false;
  String? _sessionId;
  String? _reportedRuntimeStatusMessage;
  StreamSubscription<dynamic>? _runtimeEventsSubscription;
  Match3dNativeRuntimeInfo _runtimeInfo =
      const Match3dNativeRuntimeInfo.unavailable();
  Match3dNativeSessionState? _runtimeSessionState;
  Match3dNativeRuntimeEventType _lastRuntimeEventType =
      Match3dNativeRuntimeEventType.unknown;
  bool _closingSession = false;
  bool _unexpectedSessionClosed = false;
  String? _runtimeStatusOverride;

  @override
  void initState() {
    super.initState();
    _bridge = widget.bridge;
    if (kGtexLegacy3dRuntimeEnabled) {
      unawaited(_probeNativeAvailability());
    }
  }

  @override
  void didUpdateWidget(covariant NativeMatch3dSurface oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!kGtexLegacy3dRuntimeEnabled) {
      return;
    }
    if (!identical(oldWidget.bridge, widget.bridge)) {
      final Match3DBridge? previousBridge = _bridge;
      _bridge = widget.bridge;
      _subscribeToRuntimeEvents();
      unawaited(_reinitializeBridge(previousBridge));
      return;
    }
    if (oldWidget.viewState.matchId != widget.viewState.matchId) {
      unawaited(_reopenNativeSession());
    } else if (_nativeAvailable &&
        (oldWidget.viewState != widget.viewState ||
            oldWidget.frame != widget.frame ||
            oldWidget.activeEvent != widget.activeEvent ||
            oldWidget.cameraPreset != widget.cameraPreset ||
            oldWidget.runtimePlayers != widget.runtimePlayers ||
            oldWidget.runtimeBall != widget.runtimeBall)) {
      unawaited(_syncNativeFrame());
    }
  }

  Future<void> _probeNativeAvailability() async {
    final Match3DBridge? bridge = _bridge;
    if (kIsWeb || defaultTargetPlatform != TargetPlatform.android) {
      unawaited(_runtimeEventsSubscription?.cancel() ?? Future<void>.value());
      _runtimeEventsSubscription = null;
      if (mounted) {
        setState(() {
          _nativeAvailable = false;
          _hasProbedNativeAvailability = true;
          _runtimeInfo = const Match3dNativeRuntimeInfo.unavailable();
          _runtimeSessionState = null;
        });
      }
      _publishRuntimeStatusMessage(null);
      return;
    }
    final Match3dNativeRuntimeInfo runtimeInfo =
        bridge == null
            ? const Match3dNativeRuntimeInfo.unavailable()
            : await bridge.getRuntimeInfo();
    final Match3dNativeSessionState? sessionState =
        runtimeInfo.available && runtimeInfo.supportsSessions && bridge != null
            ? await bridge.getSessionState()
            : null;
    if (runtimeInfo.available && bridge != null) {
      _subscribeToRuntimeEvents();
    } else {
      unawaited(_runtimeEventsSubscription?.cancel() ?? Future<void>.value());
      _runtimeEventsSubscription = null;
    }
    final bool nativeReady =
        runtimeInfo.available &&
        await _ensureAndroidLiveBootstrap(runtimeInfo: runtimeInfo);
    if (!mounted) {
      return;
    }
    setState(() {
      _nativeAvailable = nativeReady;
      _hasProbedNativeAvailability = true;
      _runtimeInfo = runtimeInfo;
      _runtimeSessionState = sessionState;
      _lastRuntimeEventType = Match3dNativeRuntimeEventType.runtimeReady;
      _unexpectedSessionClosed = false;
    });
    _publishRuntimeStatusMessage(_deriveRuntimeStatusMessage());
    if (nativeReady) {
      await _ensureNativeSession();
      await _syncNativeFrame();
    }
  }

  @override
  void dispose() {
    _closingSession = true;
    if (kGtexLegacy3dRuntimeEnabled) {
      unawaited(_runtimeEventsSubscription?.cancel() ?? Future<void>.value());
      _runtimeEventsSubscription = null;
      unawaited(_closeNativeSession(bridge: _bridge));
    }
    super.dispose();
  }

  Future<void> _reinitializeBridge(Match3DBridge? previousBridge) async {
    await _closeNativeSession(bridge: previousBridge);
    if (!mounted) {
      return;
    }
    await _probeNativeAvailability();
  }

  Future<void> _reopenNativeSession() async {
    await _closeNativeSession();
    if (!mounted) {
      return;
    }
    if (!await _ensureAndroidLiveBootstrap()) {
      if (mounted) {
        setState(() {
          _nativeAvailable = false;
          _runtimeSessionState = null;
        });
      }
      _publishRuntimeStatusMessage(_deriveRuntimeStatusMessage());
      return;
    }
    await _ensureNativeSession();
    await _syncNativeFrame();
  }

  Future<String?> _ensureNativeSession() async {
    if (!_nativeAvailable) {
      return null;
    }
    final Match3DBridge? bridge = _bridge;
    if (bridge == null) {
      return null;
    }
    final Match3dNativeSessionDescriptor descriptor =
        NativeMatch3dSurface.describeSession(
          viewState: widget.viewState,
          frame: widget.frame,
          cameraPreset: widget.cameraPreset,
        );
    if (_sessionId == descriptor.sessionId) {
      return _sessionId;
    }
    if (_sessionId != null && _sessionId != descriptor.sessionId) {
      await _closeNativeSession();
    }
    final Match3dNativeSessionState state = await bridge.openSession(
      descriptor,
    );
    _sessionId =
        state.sessionId.isNotEmpty ? state.sessionId : descriptor.sessionId;
    return _sessionId;
  }

  Future<void> _closeNativeSession({Match3DBridge? bridge}) async {
    final Match3DBridge? resolvedBridge = bridge ?? _bridge;
    final String? sessionId = _sessionId;
    _sessionId = null;
    if (resolvedBridge == null || sessionId == null || sessionId.isEmpty) {
      return;
    }
    _closingSession = true;
    await resolvedBridge.closeSession(sessionId: sessionId);
    _closingSession = false;
  }

  Future<void> _syncNativeFrame() async {
    final Match3DBridge? bridge = _bridge;
    if (bridge == null) {
      return;
    }
    final String? sessionId = await _ensureNativeSession();
    final sceneGraph = Gtex3dScene.describeGraph(
      viewState: widget.viewState,
      frame: widget.frame,
      activeEvent: widget.activeEvent,
      cameraPreset: widget.cameraPreset,
      runtimePlayers: widget.runtimePlayers,
      runtimeBall: widget.runtimeBall,
    );
    await bridge.syncFrame(
      sceneGraph: sceneGraph,
      activeEvent: widget.activeEvent,
      sessionId: sessionId,
    );
  }

  Future<bool> _ensureAndroidLiveBootstrap({
    Match3dNativeRuntimeInfo? runtimeInfo,
  }) async {
    if (kIsWeb || defaultTargetPlatform != TargetPlatform.android) {
      return true;
    }
    final Match3dNativeRuntimeInfo resolvedRuntimeInfo =
        runtimeInfo ?? _runtimeInfo;
    final bool requiresLegacyActivityBootstrap =
        resolvedRuntimeInfo.platform == _legacyRuntimePlatformToken ||
        resolvedRuntimeInfo.runtime == _legacyRuntimeNameToken;
    if (!requiresLegacyActivityBootstrap) {
      _runtimeStatusOverride = null;
      return true;
    }
    final Match3dAndroidLiveBootstrapProvisioner? provisioner =
        widget.androidLiveBootstrapProvisioner;
    if (provisioner == null) {
      _runtimeStatusOverride =
          'Legacy match runtime is unavailable; the 2D broadcast remains active.';
      return false;
    }
    final Match3dAndroidLiveBootstrapResult result = await provisioner
        .provision(matchId: widget.viewState.matchId);
    _runtimeStatusOverride =
        result.staged
            ? null
            : (result.message ??
                'Legacy match runtime could not be staged; the 2D broadcast remains active.');
    return result.staged;
  }

  void _subscribeToRuntimeEvents() {
    unawaited(_runtimeEventsSubscription?.cancel() ?? Future<void>.value());
    final Match3DBridge? bridge = _bridge;
    if (bridge == null ||
        kIsWeb ||
        defaultTargetPlatform != TargetPlatform.android) {
      _runtimeEventsSubscription = null;
      return;
    }
    _runtimeEventsSubscription = bridge.events.listen(_handleRuntimeEvent);
  }

  void _handleRuntimeEvent(dynamic event) {
    final Match3dNativeRuntimeEvent runtimeEvent =
        Match3dNativeRuntimeEvent.fromMap(event);
    if (runtimeEvent.type == Match3dNativeRuntimeEventType.unknown ||
        !mounted) {
      return;
    }
    final bool unexpectedSessionClose =
        runtimeEvent.type == Match3dNativeRuntimeEventType.sessionClosed &&
        !_closingSession;
    setState(() {
      _runtimeInfo = runtimeEvent.runtimeInfo;
      _runtimeSessionState = runtimeEvent.sessionState ?? _runtimeSessionState;
      _lastRuntimeEventType = runtimeEvent.type;
      _hasProbedNativeAvailability = true;
      if (runtimeEvent.type == Match3dNativeRuntimeEventType.sessionOpened ||
          runtimeEvent.type == Match3dNativeRuntimeEventType.runtimeReady) {
        _unexpectedSessionClosed = false;
        _runtimeStatusOverride = null;
      }
      if (unexpectedSessionClose) {
        _nativeAvailable = false;
        _unexpectedSessionClosed = true;
      }
    });
    _publishRuntimeStatusMessage(
      unexpectedSessionClose
          ? 'Legacy match runtime closed; the 2D broadcast remains active.'
          : _deriveRuntimeStatusMessage(),
    );
  }

  void _publishRuntimeStatusMessage(String? message) {
    if (_reportedRuntimeStatusMessage == message) {
      return;
    }
    _reportedRuntimeStatusMessage = message;
    widget.onRuntimeStatusMessageChanged?.call(message);
  }

  String? _deriveRuntimeStatusMessage() {
    if (kIsWeb || defaultTargetPlatform != TargetPlatform.android) {
      return null;
    }
    if (_bridge == null || !_hasProbedNativeAvailability) {
      return null;
    }
    if (_unexpectedSessionClosed) {
      return 'Legacy match runtime closed; the 2D broadcast remains active.';
    }
    if (_runtimeStatusOverride != null &&
        _runtimeStatusOverride!.trim().isNotEmpty) {
      return _runtimeStatusOverride;
    }
    if (!_nativeAvailable) {
      return 'Legacy Android runtime unavailable; the 2D broadcast remains active.';
    }
    final Match3dNativeSessionState? sessionState = _runtimeSessionState;
    if (sessionState != null &&
        sessionState.isOpen &&
        !sessionState.platformViewAttached) {
      return 'Legacy match runtime opened; waiting for the Android surface.';
    }
    if (sessionState != null &&
        sessionState.isOpen &&
        sessionState.ackCount == 0) {
      return 'Legacy match runtime opened; waiting for the first frame sync.';
    }
    return null;
  }

  bool get _showRuntimeBadge {
    if (!widget.showRuntimeBadge ||
        kIsWeb ||
        defaultTargetPlatform != TargetPlatform.android ||
        _bridge == null) {
      return false;
    }
    return !_hasProbedNativeAvailability ||
        _nativeAvailable ||
        (_hasProbedNativeAvailability && !_nativeAvailable);
  }

  bool get _usesEmbeddedNativeView =>
      _runtimeInfo.viewType == _embeddedNativeViewType;

  bool get _usesLegacyActivityRuntime =>
      _runtimeInfo.viewType == _unityActivityViewType;

  _RuntimeBadgeStyle get _runtimeBadgeStyle {
    if (!_hasProbedNativeAvailability) {
      return const _RuntimeBadgeStyle(
        label: 'Legacy Runtime Checking',
        backgroundColor: Color(0xCC0F2A3B),
        borderColor: Color(0xFF53B1FD),
      );
    }
    if (!_nativeAvailable) {
      return const _RuntimeBadgeStyle(
        label: '2D Broadcast Active',
        backgroundColor: Color(0xCC7A271A),
        borderColor: Color(0xFFF97066),
      );
    }
    final Match3dNativeSessionState? sessionState = _runtimeSessionState;
    final bool platformViewAttached =
        sessionState?.platformViewAttached ?? _runtimeInfo.platformViewAttached;
    final int ackCount = sessionState?.ackCount ?? _runtimeInfo.ackCount;
    if (sessionState?.lifecycle == Match3dNativeSessionLifecycle.closed) {
      return const _RuntimeBadgeStyle(
        label: 'Legacy Runtime Closed',
        backgroundColor: Color(0xCC7A271A),
        borderColor: Color(0xFFF97066),
      );
    }
    if (ackCount > 0 && platformViewAttached) {
      return const _RuntimeBadgeStyle(
        label: 'Legacy Runtime Live',
        backgroundColor: Color(0xCC134E3A),
        borderColor: Color(0xFF22C55E),
      );
    }
    if (sessionState?.isOpen ?? false) {
      return _RuntimeBadgeStyle(
        label:
            platformViewAttached
                ? 'Legacy Runtime Syncing'
                : 'Legacy Runtime Mounting',
        backgroundColor: const Color(0xCC0F2A3B),
        borderColor:
            platformViewAttached
                ? const Color(0xFFFDB022)
                : const Color(0xFF53B1FD),
      );
    }
    return const _RuntimeBadgeStyle(
      label: 'Legacy Runtime Ready',
      backgroundColor: Color(0xCC0F2A3B),
      borderColor: Color(0xFF53B1FD),
    );
  }

  Widget _buildLegacyActivityShell() {
    final Match3dNativeSessionState? sessionState = _runtimeSessionState;
    final bool playerVisible =
        sessionState?.platformViewAttached ?? _runtimeInfo.platformViewAttached;
    final String headline =
        playerVisible
            ? 'Legacy match runtime live'
            : 'Opening legacy match runtime';
    final String detail =
        playerVisible
            ? 'A quarantined Android player is running this match. Use the system back gesture to return to the GTEX route.'
            : 'GTEX can launch a quarantined Android activity only when the internal legacy runtime flag is enabled.';

    return _buildNativeShell(
      child: DecoratedBox(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: <Color>[Color(0xFF081017), Color(0xFF11202A)],
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Container(
                width: 54,
                height: 54,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(18),
                  color: const Color(0xFF22C55E).withValues(alpha: 0.14),
                  border: Border.all(
                    color: const Color(0xFF22C55E).withValues(alpha: 0.45),
                  ),
                ),
                child: const Icon(
                  Icons.sports_soccer,
                  color: Color(0xFFB6F4C2),
                ),
              ),
              const SizedBox(height: 18),
              Text(
                headline,
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  color: Colors.white,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 10),
              Text(
                detail,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: Colors.white.withValues(alpha: 0.82),
                  height: 1.45,
                ),
              ),
              const Spacer(),
              Text(
                'Match ID: ${widget.viewState.matchId}',
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: Colors.white.withValues(alpha: 0.74),
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.3,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _wrapWithRuntimeBadge(Widget child) {
    if (!_showRuntimeBadge) {
      return child;
    }
    final _RuntimeBadgeStyle badgeStyle = _runtimeBadgeStyle;
    return Stack(
      children: <Widget>[
        child,
        Positioned(
          top: 14,
          right: 14,
          child: _NativeMatch3dRuntimeBadge(
            key: NativeMatch3dSurface.runtimeBadgeKey,
            style: badgeStyle,
          ),
        ),
      ],
    );
  }

  Widget _buildNativeShell({required Widget child}) {
    return AspectRatio(
      aspectRatio: PitchEntity.aspectRatio,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(24),
        child: DecoratedBox(
          decoration: BoxDecoration(
            border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
            gradient: const LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: <Color>[Color(0xFF0D1A22), Color(0xFF09131B)],
            ),
          ),
          child: child,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (!kGtexLegacy3dRuntimeEnabled) {
      return Pitch2dWidget(
        viewState: widget.viewState,
        frame: widget.frame,
        showFormationOverlay: false,
      );
    }
    if (!kIsWeb &&
        defaultTargetPlatform == TargetPlatform.android &&
        _bridge != null &&
        !_hasProbedNativeAvailability) {
      return _wrapWithRuntimeBadge(
        _buildNativeShell(
          child: const Center(
            child: SizedBox(
              width: 28,
              height: 28,
              child: CircularProgressIndicator(strokeWidth: 2.4),
            ),
          ),
        ),
      );
    }
    if (_nativeAvailable &&
        !kIsWeb &&
        defaultTargetPlatform == TargetPlatform.android) {
      if (_usesLegacyActivityRuntime) {
        return _wrapWithRuntimeBadge(_buildLegacyActivityShell());
      }
      if (!_usesEmbeddedNativeView) {
        return _wrapWithRuntimeBadge(
          _buildNativeShell(
            child: const Center(
              child: Text(
                'Legacy match runtime connected without an Android view binding.',
              ),
            ),
          ),
        );
      }
      return _wrapWithRuntimeBadge(
        _buildNativeShell(
          child: Stack(
            children: <Widget>[
              Positioned.fill(
                child: AndroidView(
                  viewType: _embeddedNativeViewType,
                  hitTestBehavior: PlatformViewHitTestBehavior.transparent,
                ),
              ),
            ],
          ),
        ),
      );
    }

    final Match3DBridge? fallbackBridge =
        !kIsWeb && defaultTargetPlatform == TargetPlatform.android
            ? null
            : widget.bridge;
    return _wrapWithRuntimeBadge(
      Gtex3dScene(
        viewState: widget.viewState,
        frame: widget.frame,
        activeEvent: widget.activeEvent,
        cameraPreset: widget.cameraPreset,
        bridge: fallbackBridge,
        runtimePlayers: widget.runtimePlayers,
        runtimeBall: widget.runtimeBall,
      ),
    );
  }
}

class _RuntimeBadgeStyle {
  const _RuntimeBadgeStyle({
    required this.label,
    required this.backgroundColor,
    required this.borderColor,
  });

  final String label;
  final Color backgroundColor;
  final Color borderColor;
}

class _NativeMatch3dRuntimeBadge extends StatelessWidget {
  const _NativeMatch3dRuntimeBadge({super.key, required this.style});

  final _RuntimeBadgeStyle style;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: style.backgroundColor,
        border: Border.all(color: style.borderColor.withValues(alpha: 0.92)),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        child: Text(
          style.label,
          style: Theme.of(context).textTheme.labelMedium?.copyWith(
            color: Colors.white,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
    );
  }
}
