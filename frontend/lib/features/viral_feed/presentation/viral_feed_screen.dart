import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../../../core/actions/action_pipeline.dart' as feed_actions;
import '../../../core/app_feedback.dart';
import '../../../core/optimistic_ui_handler.dart';
import '../../../core/state_sync_system.dart';
import '../../../shared/models/data_source_status.dart';
import '../../../services/frontend_audit_hooks.dart';
import '../../../services/reliability/reliable_event_queue.dart';
import '../../../widgets/gte_shell_theme.dart';
import '../../../widgets/gte_state_panel.dart';
import '../../../widgets/gte_surface_panel.dart';
import '../data/viral_feed_models.dart';
import '../data/viral_feed_repository.dart';

class ViralFeedScreen extends StatefulWidget {
  const ViralFeedScreen({
    super.key,
    this.currentUserId,
    this.routeStatus = DataSourceStatus.live,
    ViralFeedRepository? repository,
    feed_actions.ClipActionDispatcher? actionDispatcher,
    ReliableEventQueue? eventQueue,
  }) : _repository = repository,
       _actionDispatcher = actionDispatcher,
       _eventQueue = eventQueue;

  final String? currentUserId;
  final DataSourceStatus routeStatus;
  final ViralFeedRepository? _repository;
  final feed_actions.ClipActionDispatcher? _actionDispatcher;
  final ReliableEventQueue? _eventQueue;

  @override
  State<ViralFeedScreen> createState() => _ViralFeedScreenState();
}

class _ViralFeedScreenState extends State<ViralFeedScreen> {
  static const int _feedbackRefreshThreshold = 3;

  late final ViralFeedRepository _repository;
  late final feed_actions.ClipActionDispatcher _actionDispatcher;
  late final FrontendAuditHooks _auditHooks;
  late final ReliableEventQueue _eventQueue;
  late final StateSyncSystem _syncSystem;
  late final OptimisticUiHandler<String, Set<String>> _optimisticUi;
  late final bool _ownsActionDispatcher;

  final PageController _pageController = PageController();
  final Set<String> _likedClipIds = <String>{};
  final Set<String> _sharedClipIds = <String>{};
  final Set<String> _completedClipIds = <String>{};

  StreamSubscription<FeedRefreshTrigger>? _feedRefreshSubscription;
  ViralFeedDeck? _deck;
  Object? _loadError;
  ViralFeedSource _source = ViralFeedSource.forYou;
  int _pageIndex = 0;
  bool _isBootstrapping = true;
  Timer? _completionTimer;
  Timer? _feedRefreshDebounce;
  String? _activeClipId;
  String? _pendingClipActivationId;
  int _successfulFeedbackInteractions = 0;
  Future<void>? _forYouRefreshFuture;

  @override
  void initState() {
    super.initState();
    _repository = widget._repository ?? ViralFeedApiRepository.standard();
    _ownsActionDispatcher = widget._actionDispatcher == null;
    _actionDispatcher =
        widget._actionDispatcher ?? feed_actions.ActionPipeline();
    _auditHooks = FrontendAuditHooks(baseUrl: _frontendAuditBaseUrl);
    _eventQueue = widget._eventQueue ?? gteReliableEventQueue;
    _syncSystem = StateSyncSystem(
      interval: const Duration(seconds: 45),
      onSync: _syncDeck,
      onStateChanged: () {
        if (mounted) {
          setState(() {});
        }
      },
    );
    _optimisticUi = OptimisticUiHandler<String, Set<String>>(
      onStateChanged: () {
        if (mounted) {
          setState(() {});
        }
      },
    );
    _feedRefreshSubscription = _eventQueue.feedRefreshTriggers.listen((_) {
      _scheduleFeedRefresh();
    });
    _syncSystem.attach();
    unawaited(_loadDeck(refresh: true));
  }

  @override
  void dispose() {
    _completionTimer?.cancel();
    _feedRefreshDebounce?.cancel();
    _feedRefreshSubscription?.cancel();
    _syncSystem.detach();
    _pageController.dispose();
    if (_ownsActionDispatcher) {
      _actionDispatcher.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final ViralFeedDeck? deck = _deck;
    final Color background = Theme.of(context).scaffoldBackgroundColor;
    if (_isBootstrapping) {
      return _buildScaffold(
        backgroundColor: background,
        body: const _LoadingState(),
      );
    }
    if (_loadError != null && deck == null) {
      return _buildScaffold(
        backgroundColor: background,
        body: _ErrorState(
          message: AppFeedback.messageFor(_loadError!),
          onRetry: _handleRetry,
        ),
      );
    }
    if (deck == null || deck.clips.isEmpty) {
      return _buildScaffold(
        backgroundColor: background,
        body: _EmptyState(onRetry: _handleRetry),
      );
    }

    return _buildScaffold(
      backgroundColor: background,
      body: PageView.builder(
        key: const Key('viral-feed-page-view'),
        controller: _pageController,
        scrollDirection: Axis.vertical,
        itemCount: deck.clips.length,
        onPageChanged: (int index) => _handlePageChanged(deck, index),
        itemBuilder: (BuildContext context, int index) {
          final ViralClip clip = deck.clips[index];
          return _ViralClipPage(
            clip: clip,
            deck: deck,
            index: index,
            total: deck.clips.length,
            source: _source,
            isSyncing: _syncSystem.isSyncing,
            isLiked: _likedClipIds.contains(clip.clipId),
            isShared: _sharedClipIds.contains(clip.clipId),
            likePending: _optimisticUi.isPending('like:${clip.clipId}'),
            sharePending: _optimisticUi.isPending('share:${clip.clipId}'),
            onBack: () => _handleBack(clip),
            onRefresh: _handleManualRefresh,
            onSelectSource: _changeSource,
            onLike: () => _handleLike(clip),
            onShare: () => _handleShare(clip),
          );
        },
      ),
    );
  }

  Scaffold _buildScaffold({
    required Color backgroundColor,
    required Widget body,
  }) {
    if (!kDebugMode) {
      return Scaffold(
        backgroundColor: backgroundColor,
        body: Container(decoration: gteBackdropDecoration(), child: body),
      );
    }
    return Scaffold(
      backgroundColor: backgroundColor,
      body: Stack(
        children: <Widget>[
          Container(decoration: gteBackdropDecoration(), child: body),
          Positioned(
            top: MediaQuery.paddingOf(context).top + 76,
            right: 12,
            child: _RouteStatusBadge(status: widget.routeStatus),
          ),
        ],
      ),
    );
  }

  Future<void> _loadDeck({
    required bool refresh,
    bool resetPosition = false,
    bool showErrorFeedback = false,
  }) async {
    final bool clearExistingDeck = resetPosition || _deck == null;
    if (mounted) {
      setState(() {
        _isBootstrapping = clearExistingDeck;
        if (clearExistingDeck) {
          _deck = null;
          _loadError = null;
          _pageIndex = 0;
        }
      });
    }

    try {
      final ViralFeedDeck nextDeck = await _repository.fetchDeck(
        source: _source,
        refresh: refresh,
      );
      if (!mounted) {
        return;
      }
      final int nextIndex =
          nextDeck.clips.isEmpty
              ? 0
              : (resetPosition
                  ? 0
                  : _pageIndex.clamp(0, nextDeck.clips.length - 1));
      setState(() {
        _deck = nextDeck;
        _loadError = null;
        _isBootstrapping = false;
        _pageIndex = nextIndex;
      });
      if (nextDeck.clips.isNotEmpty) {
        _jumpToPage(nextIndex);
        _scheduleActiveClip(nextDeck.clips[nextIndex]);
      }
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _isBootstrapping = false;
        if (clearExistingDeck) {
          _loadError = error;
        }
      });
      if (showErrorFeedback && !clearExistingDeck) {
        AppFeedback.showError(context, error);
      }
    }
  }

  Future<void> _syncDeck() {
    final ViralFeedDeck? deck = _deck;
    if (_source == ViralFeedSource.forYou &&
        deck != null &&
        deck.clips.isNotEmpty) {
      return _refreshForYou(showErrorFeedback: true);
    }
    return _loadDeck(refresh: true, showErrorFeedback: _deck != null);
  }

  Future<void> _refreshForYou({required bool showErrorFeedback}) async {
    final Future<void>? inFlightRefresh = _forYouRefreshFuture;
    if (inFlightRefresh != null) {
      return inFlightRefresh;
    }
    late final Future<void> trackedRefresh;
    trackedRefresh = _runForYouRefresh(
      showErrorFeedback: showErrorFeedback,
    ).whenComplete(() {
      if (identical(_forYouRefreshFuture, trackedRefresh)) {
        _forYouRefreshFuture = null;
      }
    });
    _forYouRefreshFuture = trackedRefresh;
    return trackedRefresh;
  }

  Future<void> _runForYouRefresh({required bool showErrorFeedback}) async {
    final ViralFeedDeck? currentDeck = _deck;
    if (currentDeck == null || currentDeck.clips.isEmpty) {
      await _loadDeck(refresh: true, showErrorFeedback: showErrorFeedback);
      return;
    }
    try {
      final ViralFeedDeckRefresh refresh = await _repository.refreshForYou(
        cursor: _pageIndex,
        limit: currentDeck.clips.length,
      );
      if (!mounted) {
        return;
      }
      final ViralFeedDeck nextDeck = _applyRefresh(currentDeck, refresh);
      final int nextIndex =
          nextDeck.clips.isEmpty
              ? 0
              : _pageIndex.clamp(0, nextDeck.clips.length - 1);
      setState(() {
        _deck = nextDeck;
        _loadError = null;
        _isBootstrapping = false;
        _pageIndex = nextIndex;
        _successfulFeedbackInteractions = 0;
      });
      if (nextDeck.clips.isNotEmpty) {
        _jumpToPage(nextIndex);
        _scheduleActiveClip(nextDeck.clips[nextIndex]);
      }
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _isBootstrapping = false;
      });
      if (showErrorFeedback) {
        AppFeedback.showError(context, error);
      }
    }
  }

  ViralFeedDeck _applyRefresh(
    ViralFeedDeck currentDeck,
    ViralFeedDeckRefresh refresh,
  ) {
    if (refresh.replaceIndices.isEmpty || refresh.newItems.isEmpty) {
      return currentDeck;
    }
    final List<ViralClip> updatedClips = List<ViralClip>.from(
      currentDeck.clips,
    );
    final int replaceCount = math.min(
      refresh.replaceIndices.length,
      refresh.newItems.length,
    );
    for (int index = 0; index < replaceCount; index += 1) {
      final int targetIndex = refresh.replaceIndices[index];
      if (targetIndex < 0 || targetIndex >= updatedClips.length) {
        continue;
      }
      updatedClips[targetIndex] = refresh.newItems[index];
    }
    return ViralFeedDeck(
      source: currentDeck.source,
      feedKey: currentDeck.feedKey,
      generatedAt: DateTime.now().toUtc(),
      cacheHit: false,
      clips: updatedClips,
      debatesByMatch: currentDeck.debatesByMatch,
    );
  }

  Future<void> _recordSuccessfulInteraction(String action) async {
    if (_source != ViralFeedSource.forYou) {
      return;
    }
    if (!const <String>{
      'scroll',
      'complete',
      'like',
      'share',
    }.contains(action)) {
      return;
    }
    _successfulFeedbackInteractions += 1;
    if (_successfulFeedbackInteractions < _feedbackRefreshThreshold ||
        _forYouRefreshFuture != null) {
      return;
    }
    _successfulFeedbackInteractions = 0;
    await _refreshForYou(showErrorFeedback: false);
  }

  Future<void> _dispatchPassiveInteraction(
    String action,
    ViralClip clip,
  ) async {
    try {
      await _dispatchAction(action, clip);
      await _recordSuccessfulInteraction(action);
    } catch (error, stackTrace) {
      debugPrint('Passive feed interaction failed: $error\n$stackTrace');
    }
  }

  void _handleRetry() {
    unawaited(
      _auditHooks.trackButtonClick(
        screen: 'viral_feed',
        flow: 'feed_load',
        target: 'retry_button',
      ),
    );
    unawaited(_loadDeck(refresh: true, resetPosition: true));
  }

  void _handleManualRefresh() {
    unawaited(
      _auditHooks.trackButtonClick(
        screen: 'viral_feed',
        flow: 'feed_load',
        target: 'refresh_button',
        metadata: <String, Object?>{'feed_source': _source.feedSource},
      ),
    );
    unawaited(_syncSystem.sync());
  }

  void _changeSource(ViralFeedSource source) {
    if (_source == source) {
      return;
    }
    _completionTimer?.cancel();
    _activeClipId = null;
    _pendingClipActivationId = null;
    setState(() {
      _source = source;
      _pageIndex = 0;
      _deck = null;
      _loadError = null;
      _isBootstrapping = true;
      _successfulFeedbackInteractions = 0;
    });
    unawaited(
      _auditHooks.trackButtonClick(
        screen: 'viral_feed',
        flow: 'feed_source',
        target: source.feedSource,
      ),
    );
    unawaited(_loadDeck(refresh: true, resetPosition: true));
  }

  void _handleBack(ViralClip clip) {
    unawaited(
      _auditHooks.trackButtonClick(
        screen: 'viral_feed',
        flow: 'feed_navigation',
        target: 'back_button',
        metadata: <String, Object?>{
          'clip_id': clip.clipId,
          'page_index': _pageIndex,
        },
      ),
    );
    unawaited(
      _auditHooks.trackDropOff(
        screen: 'viral_feed',
        flow: 'feed_navigation',
        stage: 'back_navigation',
        target: 'back_button',
        metadata: <String, Object?>{
          'clip_id': clip.clipId,
          'page_index': _pageIndex,
        },
      ),
    );
    Navigator.of(context).maybePop();
  }

  void _scheduleFeedRefresh() {
    _feedRefreshDebounce?.cancel();
    _feedRefreshDebounce = Timer(const Duration(milliseconds: 300), () {
      unawaited(_syncSystem.syncAfterCriticalAction());
    });
  }

  void _handlePageChanged(ViralFeedDeck deck, int index) {
    if (_pageIndex >= 0 && _pageIndex < deck.clips.length) {
      final ViralClip previousClip = deck.clips[_pageIndex];
      if (!_completedClipIds.contains(previousClip.clipId)) {
        unawaited(_dispatchPassiveInteraction('scroll', previousClip));
      }
    }
    setState(() {
      _pageIndex = index;
    });
    _scheduleActiveClip(deck.clips[index]);
  }

  void _scheduleActiveClip(ViralClip clip) {
    if (_activeClipId == clip.clipId ||
        _pendingClipActivationId == clip.clipId) {
      return;
    }
    _pendingClipActivationId = clip.clipId;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) {
        return;
      }
      _pendingClipActivationId = null;
      _activateClip(clip);
    });
  }

  void _activateClip(ViralClip clip) {
    if (_activeClipId == clip.clipId) {
      return;
    }
    _completionTimer?.cancel();
    _activeClipId = clip.clipId;
    if (_completedClipIds.contains(clip.clipId)) {
      return;
    }
    _completionTimer = Timer(_completionDelay(clip), () {
      if (!mounted || _activeClipId != clip.clipId) {
        return;
      }
      _completedClipIds.add(clip.clipId);
      unawaited(_dispatchPassiveInteraction('complete', clip));
    });
  }

  Duration _completionDelay(ViralClip clip) {
    final int durationMs = clip.videoLengthMs ?? 12000;
    return Duration(milliseconds: math.max(durationMs, 1));
  }

  Future<void> _handleLike(ViralClip clip) async {
    if (_likedClipIds.contains(clip.clipId) ||
        _optimisticUi.isPending('like:${clip.clipId}')) {
      return;
    }
    unawaited(
      _auditHooks.trackButtonClick(
        screen: 'viral_feed',
        flow: 'feed_engagement',
        target: 'like_button',
        metadata: <String, Object?>{
          'clip_id': clip.clipId,
          'highlight_id': clip.highlightId,
          'match_id': clip.matchId,
        },
      ),
    );
    await _runOptimisticSetMutation(
      key: 'like:${clip.clipId}',
      currentState: _likedClipIds,
      apply: (Set<String> nextState) {
        _likedClipIds
          ..clear()
          ..addAll(nextState);
      },
      clipId: clip.clipId,
      commit: () async {
        await _eventQueue.enqueue(
          topic: 'viral_feed',
          name: 'major_interaction',
          payload: <String, Object?>{
            'action': 'like_clip',
            'clip_id': clip.clipId,
            'match_id': clip.matchId,
            'highlight_id': clip.highlightId,
          },
          dedupeKey: 'viral-like:${clip.clipId}',
        );
        await _dispatchAction('like', clip, commitImmediately: true);
        await _recordSuccessfulInteraction('like');
      },
    );
  }

  Future<void> _handleShare(ViralClip clip) async {
    if (_sharedClipIds.contains(clip.clipId) ||
        _optimisticUi.isPending('share:${clip.clipId}')) {
      return;
    }
    unawaited(
      _auditHooks.trackButtonClick(
        screen: 'viral_feed',
        flow: 'feed_engagement',
        target: 'share_button',
        metadata: <String, Object?>{
          'clip_id': clip.clipId,
          'highlight_id': clip.highlightId,
          'match_id': clip.matchId,
          'channel': clip.shareChannel,
        },
      ),
    );
    await _runOptimisticSetMutation(
      key: 'share:${clip.clipId}',
      currentState: _sharedClipIds,
      apply: (Set<String> nextState) {
        _sharedClipIds
          ..clear()
          ..addAll(nextState);
      },
      clipId: clip.clipId,
      commit: () async {
        await _eventQueue.enqueue(
          topic: 'viral_feed',
          name: 'major_interaction',
          payload: <String, Object?>{
            'action': 'share_clip',
            'clip_id': clip.clipId,
            'match_id': clip.matchId,
            'highlight_id': clip.highlightId,
            'channel': clip.shareChannel,
          },
          dedupeKey: 'viral-share:${clip.clipId}',
        );
        await _dispatchAction('share', clip, commitImmediately: true);
        await _recordSuccessfulInteraction('share');
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                'Share handoff queued for ${clip.shareChannel.toUpperCase()}.',
              ),
            ),
          );
        }
      },
    );
  }

  Future<void> _runOptimisticSetMutation({
    required String key,
    required Set<String> currentState,
    required void Function(Set<String> nextState) apply,
    required String clipId,
    required Future<void> Function() commit,
  }) async {
    try {
      await _optimisticUi.run(
        key: key,
        currentState: Set<String>.from(currentState),
        optimisticState:
            (Set<String> existing) => <String>{...existing, clipId},
        apply: (Set<String> nextState) {
          if (!mounted) {
            return;
          }
          setState(() {
            apply(nextState);
          });
        },
        commit: commit,
      );
    } catch (error) {
      if (!mounted) {
        return;
      }
      AppFeedback.showError(context, error);
    }
  }

  Future<void> _dispatchAction(
    String action,
    ViralClip clip, {
    bool commitImmediately = false,
  }) {
    return _actionDispatcher.dispatch(
      feed_actions.ActionInvocation(
        action: action,
        clipId: clip.clipId,
        userId: widget.currentUserId,
        videoLengthMs: clip.videoLengthMs,
        referrer: 'viral_feed',
        creatorId: clip.creatorId,
        formatKey: clip.formatKey,
        clipEventType: clip.eventType,
        teamName: clip.teamName,
        tags: clip.tags,
        commitImmediately: commitImmediately,
      ),
    );
  }

  void _jumpToPage(int pageIndex) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !_pageController.hasClients) {
        return;
      }
      _pageController.jumpToPage(pageIndex);
    });
  }
}

class _RouteStatusBadge extends StatelessWidget {
  const _RouteStatusBadge({required this.status});

  final DataSourceStatus status;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final Color color = switch (status) {
      DataSourceStatus.live => tokens.positive,
      DataSourceStatus.blocked => tokens.negative,
      DataSourceStatus.demo => tokens.warning,
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: Color.alphaBlend(
          tokens.panelStrong.withValues(alpha: 0.92),
          tokens.background,
        ),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: color.withValues(alpha: 0.44)),
        boxShadow: <BoxShadow>[
          BoxShadow(
            color: color.withValues(alpha: 0.12),
            blurRadius: 18,
            spreadRadius: 1,
          ),
        ],
      ),
      child: Text(
        status.label,
        style: Theme.of(context).textTheme.labelLarge?.copyWith(
          color: color,
          fontWeight: FontWeight.w800,
          letterSpacing: 0.8,
        ),
      ),
    );
  }
}

class _ViralClipPage extends StatelessWidget {
  const _ViralClipPage({
    required this.clip,
    required this.deck,
    required this.index,
    required this.total,
    required this.source,
    required this.isSyncing,
    required this.isLiked,
    required this.isShared,
    required this.likePending,
    required this.sharePending,
    required this.onBack,
    required this.onRefresh,
    required this.onSelectSource,
    required this.onLike,
    required this.onShare,
  });

  final ViralClip clip;
  final ViralFeedDeck deck;
  final int index;
  final int total;
  final ViralFeedSource source;
  final bool isSyncing;
  final bool isLiked;
  final bool isShared;
  final bool likePending;
  final bool sharePending;
  final VoidCallback onBack;
  final VoidCallback onRefresh;
  final ValueChanged<ViralFeedSource> onSelectSource;
  final VoidCallback onLike;
  final VoidCallback onShare;

  @override
  Widget build(BuildContext context) {
    final List<Color> palette = _paletteFor(clip.eventType);
    final Color accent = palette.last;
    final tokens = GteShellTheme.tokensOf(context);
    final definition = GteShellTheme.definitionOf(context);
    final ThemeData theme = Theme.of(context);
    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[
            Color.alphaBlend(
              palette.first.withValues(alpha: 0.78),
              tokens.background,
            ),
            Color.alphaBlend(
              palette[1].withValues(alpha: 0.62),
              tokens.backgroundSoft,
            ),
            Color.alphaBlend(
              accent.withValues(alpha: 0.18),
              tokens.panelElevated,
            ),
          ],
        ),
      ),
      child: Stack(
        fit: StackFit.expand,
        children: <Widget>[
          _BackdropTexture(palette: palette),
          SafeArea(
            child: LayoutBuilder(
              builder: (BuildContext context, BoxConstraints constraints) {
                return SingleChildScrollView(
                  padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
                  child: ConstrainedBox(
                    constraints: BoxConstraints(
                      minHeight: constraints.maxHeight,
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: tokens.panelStrong.withValues(alpha: 0.56),
                            borderRadius: BorderRadius.circular(24),
                            border: Border.all(
                              color: tokens.stroke.withValues(alpha: 0.92),
                            ),
                            boxShadow: <BoxShadow>[
                              BoxShadow(
                                color: accent.withValues(alpha: 0.12),
                                blurRadius: 20,
                                spreadRadius: 1,
                              ),
                            ],
                          ),
                          child: Row(
                            children: <Widget>[
                              Container(
                                decoration: BoxDecoration(
                                  shape: BoxShape.circle,
                                  color: tokens.panelStrong.withValues(
                                    alpha: 0.72,
                                  ),
                                  border: Border.all(
                                    color: tokens.stroke.withValues(alpha: 0.9),
                                  ),
                                ),
                                child: IconButton(
                                  key: const Key('viral-back-button'),
                                  onPressed: onBack,
                                  icon: const Icon(
                                    Icons.arrow_back_ios_new_rounded,
                                  ),
                                  color: tokens.textPrimary,
                                ),
                              ),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Wrap(
                                  spacing: 8,
                                  runSpacing: 8,
                                  children: ViralFeedSource.values
                                      .map<Widget>(
                                        (ViralFeedSource value) =>
                                            _FeedSourceChip(
                                              label: value.label,
                                              isSelected: value == source,
                                              onTap:
                                                  () => onSelectSource(value),
                                            ),
                                      )
                                      .toList(growable: false),
                                ),
                              ),
                              const SizedBox(width: 10),
                              Container(
                                decoration: BoxDecoration(
                                  shape: BoxShape.circle,
                                  color: tokens.panelStrong.withValues(
                                    alpha: 0.72,
                                  ),
                                  border: Border.all(
                                    color: tokens.stroke.withValues(alpha: 0.9),
                                  ),
                                ),
                                child: IconButton(
                                  key: const Key('viral-refresh-button'),
                                  onPressed: onRefresh,
                                  icon:
                                      isSyncing
                                          ? SizedBox(
                                            width: 18,
                                            height: 18,
                                            child: CircularProgressIndicator(
                                              strokeWidth: 2,
                                              color: definition.primaryColor,
                                            ),
                                          )
                                          : const Icon(Icons.refresh_rounded),
                                  color: tokens.textPrimary,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 12),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: <Widget>[
                            _MetaChip(
                              label: isSyncing ? 'SYNCING LIVE' : 'LIVE LOCKED',
                              accent: definition.primaryColor,
                            ),
                            _MetaChip(
                              label: 'RANK #${clip.rank}',
                              accent: definition.accentColor,
                            ),
                            _MetaChip(
                              label: 'ENGINE',
                              accent: definition.secondaryColor,
                            ),
                            _MetaChip(label: "${clip.minute}'", accent: accent),
                            if (clip.teamName != null)
                              _MetaChip(
                                label: clip.teamName!.toUpperCase(),
                                accent: definition.secondaryColor,
                              ),
                            if (clip.scorelineLabel != null)
                              _MetaChip(
                                label: clip.scorelineLabel!,
                                accent: definition.accentColor,
                              ),
                            _MetaChip(
                              label: '${index + 1}/$total',
                              accent: tokens.textMuted,
                            ),
                          ],
                        ),
                        const SizedBox(height: 24),
                        Text(
                          clip.caption.hook,
                          key: Key('viral-hook-${clip.highlightId}'),
                          style: theme.textTheme.headlineLarge?.copyWith(
                            fontSize: 34,
                            fontWeight: FontWeight.w900,
                            height: 0.98,
                          ),
                        ),
                        const SizedBox(height: 12),
                        Text(
                          clip.title,
                          style: theme.textTheme.titleLarge?.copyWith(
                            color: tokens.textPrimary.withValues(alpha: 0.9),
                          ),
                        ),
                        const SizedBox(height: 24),
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: <Widget>[
                                  _StageCard(
                                    clip: clip,
                                    deck: deck,
                                    accent: accent,
                                  ),
                                  const SizedBox(height: 18),
                                  Text(
                                    clip.caption.caption,
                                    style: theme.textTheme.bodyLarge,
                                  ),
                                  const SizedBox(height: 10),
                                  Wrap(
                                    spacing: 8,
                                    runSpacing: 8,
                                    children: clip.caption.hashtags
                                        .map(
                                          (String hashtag) => Text(
                                            hashtag,
                                            style: theme.textTheme.bodySmall
                                                ?.copyWith(
                                                  color:
                                                      definition.primaryColor,
                                                  fontWeight: FontWeight.w700,
                                                ),
                                          ),
                                        )
                                        .toList(growable: false),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(width: 18),
                            _ActionRail(
                              clip: clip,
                              isLiked: isLiked,
                              isShared: isShared,
                              likePending: likePending,
                              sharePending: sharePending,
                              onLike: onLike,
                              onShare: onShare,
                              accent: accent,
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _StageCard extends StatelessWidget {
  const _StageCard({
    required this.clip,
    required this.deck,
    required this.accent,
  });

  final ViralClip clip;
  final ViralFeedDeck deck;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final tokens = GteShellTheme.tokensOf(context);
    return ConstrainedBox(
      constraints: const BoxConstraints(minHeight: 320),
      child: GteSurfacePanel(
        emphasized: true,
        accentColor: accent,
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              children: <Widget>[
                Container(
                  width: 54,
                  height: 54,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: accent.withValues(alpha: 0.18),
                  ),
                  child: Icon(_iconFor(clip.eventType), color: accent),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'CLIP STAGE',
                        style: theme.textTheme.labelLarge?.copyWith(
                          color: accent,
                          fontWeight: FontWeight.w800,
                          letterSpacing: 0.9,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        clip.playerName == null
                            ? clip.title
                            : '${clip.playerName} | ${clip.title}',
                        style: theme.textTheme.titleLarge,
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 20),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: <Widget>[
                _StageMetricPill(
                  label: 'Feed source',
                  value: clip.feedSource,
                  accent: accent,
                ),
                _StageMetricPill(
                  label: 'Deck',
                  value: deck.source.label,
                  accent: accent,
                ),
                _StageMetricPill(
                  label: 'Score',
                  value: clip.score.toStringAsFixed(1),
                  accent: accent,
                ),
                if (clip.creatorId != null)
                  _StageMetricPill(
                    label: 'Creator',
                    value: clip.creatorId!,
                    accent: accent,
                  ),
              ],
            ),
            const SizedBox(height: 20),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
              decoration: BoxDecoration(
                color: tokens.surfaceHighlight.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: tokens.stroke.withValues(alpha: 0.7)),
              ),
              child: Text(
                clip.summaryLine ??
                    'Ranking engine supplied this highlight with no local reordering, cache replay, or mock fallback.',
                style: theme.textTheme.bodyMedium,
              ),
            ),
            const SizedBox(height: 18),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              decoration: BoxDecoration(
                color: accent.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: accent.withValues(alpha: 0.24)),
              ),
              child: Row(
                children: <Widget>[
                  Icon(Icons.play_circle_fill_rounded, size: 20, color: accent),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      clip.videoUrl == null
                          ? 'Playback source attaches when the ranked clip asset is available.'
                          : 'Playback source connected for this ranked clip.',
                      style: theme.textTheme.bodyMedium,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _StageMetricPill extends StatelessWidget {
  const _StageMetricPill({
    required this.label,
    required this.value,
    required this.accent,
  });

  final String label;
  final String value;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return Container(
      constraints: const BoxConstraints(minWidth: 128),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: accent.withValues(alpha: 0.24)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            label.toUpperCase(),
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: accent,
              fontWeight: FontWeight.w800,
              letterSpacing: 0.8,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            value,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: tokens.textPrimary,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class _ActionRail extends StatelessWidget {
  const _ActionRail({
    required this.clip,
    required this.isLiked,
    required this.isShared,
    required this.likePending,
    required this.sharePending,
    required this.onLike,
    required this.onShare,
    required this.accent,
  });

  final ViralClip clip;
  final bool isLiked;
  final bool isShared;
  final bool likePending;
  final bool sharePending;
  final VoidCallback onLike;
  final VoidCallback onShare;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final tokens = GteShellTheme.tokensOf(context);
    return SizedBox(
      width: 108,
      child: GteSurfacePanel(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 14),
        accentColor: accent,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.end,
          children: <Widget>[
            Text(
              'ACTION RAIL',
              style: theme.textTheme.labelMedium?.copyWith(
                color: accent,
                fontWeight: FontWeight.w800,
                letterSpacing: 0.9,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 14),
            _ActionBubble(
              icon: Icons.local_fire_department_rounded,
              label: 'Hot',
              active: true,
              accent: accent,
            ),
            const SizedBox(height: 16),
            _ActionBubble(
              key: Key('viral-like-${clip.highlightId}'),
              icon:
                  isLiked
                      ? Icons.favorite_rounded
                      : Icons.favorite_border_rounded,
              label: likePending ? 'Saving' : (isLiked ? 'Liked' : 'Like'),
              active: isLiked || likePending,
              busy: likePending,
              onTap: likePending ? null : onLike,
              accent: accent,
            ),
            const SizedBox(height: 16),
            _ActionBubble(
              icon: isShared ? Icons.check_circle_rounded : Icons.share_rounded,
              label:
                  sharePending
                      ? 'Sending'
                      : (isShared ? 'Shared' : clip.caption.cta),
              active: isShared || sharePending,
              busy: sharePending,
              onTap: sharePending ? null : onShare,
              accent: tokens.accentWarm,
            ),
            const SizedBox(height: 16),
            _ActionBubble(
              icon: Icons.leaderboard_rounded,
              label: 'Rank ${clip.rank}',
              active: false,
              accent: tokens.textMuted,
            ),
            const SizedBox(height: 20),
            Text(
              clip.shareChannel.toUpperCase(),
              style: theme.textTheme.bodySmall?.copyWith(
                color: tokens.textPrimary,
                fontWeight: FontWeight.w800,
                letterSpacing: 1.0,
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

class _ActionBubble extends StatelessWidget {
  const _ActionBubble({
    super.key,
    required this.icon,
    required this.label,
    required this.active,
    required this.accent,
    this.busy = false,
    this.onTap,
  });

  final IconData icon;
  final String label;
  final bool active;
  final Color accent;
  final bool busy;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final ThemeData theme = Theme.of(context);
    final tokens = GteShellTheme.tokensOf(context);
    final Widget bubble = Column(
      children: <Widget>[
        AnimatedContainer(
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOutCubic,
          width: 60,
          height: 60,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color:
                active
                    ? accent.withValues(alpha: 0.2)
                    : tokens.surfaceHighlight.withValues(alpha: 0.08),
            border: Border.all(
              color:
                  active
                      ? accent.withValues(alpha: 0.34)
                      : tokens.stroke.withValues(alpha: 0.75),
            ),
            boxShadow:
                active
                    ? <BoxShadow>[
                      BoxShadow(
                        color: accent.withValues(alpha: 0.18),
                        blurRadius: 16,
                        spreadRadius: 1,
                      ),
                    ]
                    : const <BoxShadow>[],
          ),
          child: Center(
            child:
                busy
                    ? SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: accent,
                      ),
                    )
                    : Icon(icon, color: active ? accent : tokens.textPrimary),
          ),
        ),
        const SizedBox(height: 8),
        Text(
          label,
          style: theme.textTheme.bodySmall?.copyWith(
            color: tokens.textPrimary,
            fontWeight: FontWeight.w700,
          ),
          textAlign: TextAlign.center,
        ),
      ],
    );
    if (onTap == null) {
      return bubble;
    }
    return InkWell(
      borderRadius: BorderRadius.circular(999),
      onTap: onTap,
      child: bubble,
    );
  }
}

class _FeedSourceChip extends StatelessWidget {
  const _FeedSourceChip({
    required this.label,
    required this.isSelected,
    required this.onTap,
  });

  final String label;
  final bool isSelected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    final accent = GteShellTheme.definitionOf(context).primaryColor;
    return InkWell(
      borderRadius: BorderRadius.circular(999),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color:
              isSelected
                  ? accent.withValues(alpha: 0.12)
                  : tokens.panelStrong.withValues(alpha: 0.55),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(
            color:
                isSelected
                    ? accent.withValues(alpha: 0.36)
                    : tokens.stroke.withValues(alpha: 0.82),
          ),
        ),
        child: Text(
          label,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(
            color: isSelected ? accent : tokens.textPrimary,
            fontWeight: FontWeight.w800,
            letterSpacing: 1.2,
          ),
        ),
      ),
    );
  }
}

class _MetaChip extends StatelessWidget {
  const _MetaChip({required this.label, required this.accent});

  final String label;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: Color.alphaBlend(
          accent.withValues(alpha: 0.12),
          tokens.panelStrong.withValues(alpha: 0.88),
        ),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: accent.withValues(alpha: 0.28)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.bodySmall?.copyWith(
          color: tokens.textPrimary,
          fontWeight: FontWeight.w800,
          letterSpacing: 0.8,
        ),
      ),
    );
  }
}

class _BackdropTexture extends StatelessWidget {
  const _BackdropTexture({required this.palette});

  final List<Color> palette;

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: CustomPaint(painter: _BackdropPainter(palette: palette)),
    );
  }
}

class _BackdropPainter extends CustomPainter {
  const _BackdropPainter({required this.palette});

  final List<Color> palette;

  @override
  void paint(Canvas canvas, Size size) {
    final Paint glowPaint = Paint()..style = PaintingStyle.fill;
    final List<Offset> centers = <Offset>[
      Offset(size.width * 0.18, size.height * 0.22),
      Offset(size.width * 0.84, size.height * 0.34),
      Offset(size.width * 0.42, size.height * 0.82),
    ];
    final List<Color> colors = <Color>[
      palette.first.withValues(alpha: 0.08),
      palette[1].withValues(alpha: 0.08),
      Colors.white.withValues(alpha: 0.04),
    ];
    for (int i = 0; i < centers.length; i += 1) {
      glowPaint.color = colors[i];
      canvas.drawCircle(
        centers[i],
        size.shortestSide * (0.22 + (i * 0.03)),
        glowPaint,
      );
    }

    final Paint linePaint =
        Paint()
          ..color = Colors.white.withValues(alpha: 0.04)
          ..strokeWidth = 1;
    for (double y = 0; y < size.height; y += 56) {
      final Path path = Path()..moveTo(0, y);
      for (double x = 0; x <= size.width; x += 28) {
        path.lineTo(x, y + math.sin((x + y) / 80) * 4);
      }
      canvas.drawPath(path, linePaint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

const String _frontendAuditBaseUrl = String.fromEnvironment(
  'GTE_API_BASE_URL',
  defaultValue: 'http://127.0.0.1:8000',
);

class _LoadingState extends StatelessWidget {
  const _LoadingState();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Padding(
        padding: EdgeInsets.all(24),
        child: GteStatePanel(
          eyebrow: 'CLIPS',
          title: 'Loading live feed',
          message:
              'Preparing the ranked clip deck, interaction lane, and source controls for the active feed.',
          icon: Icons.video_collection_rounded,
          isLoading: true,
        ),
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: GteStatePanel(
          eyebrow: 'CLIPS',
          title: 'No clips ready yet',
          message:
              'The ranking engine will surface clips here as soon as the live feed endpoints return ranked payloads.',
          icon: Icons.video_collection_outlined,
          actionLabel: 'Retry',
          onAction: onRetry,
        ),
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: GteStatePanel(
          eyebrow: 'CLIPS',
          title: 'Feed validation failed',
          message: message,
          icon: Icons.error_outline_rounded,
          actionLabel: 'Retry',
          onAction: onRetry,
        ),
      ),
    );
  }
}

List<Color> _paletteFor(String eventType) {
  switch (eventType.toLowerCase()) {
    case 'goal':
    case 'penalty_scored':
      return const <Color>[
        Color(0xFF170C1F),
        Color(0xFF5C162E),
        Color(0xFFF59E0B),
      ];
    case 'double_save':
    case 'goalkeeper_save':
      return const <Color>[
        Color(0xFF071A22),
        Color(0xFF0A495B),
        Color(0xFF2DD4BF),
      ];
    default:
      return const <Color>[
        Color(0xFF0B1020),
        Color(0xFF1B2440),
        Color(0xFF5B6CB8),
      ];
  }
}

IconData _iconFor(String eventType) {
  switch (eventType.toLowerCase()) {
    case 'goal':
    case 'penalty_scored':
      return Icons.sports_soccer_rounded;
    case 'double_save':
    case 'goalkeeper_save':
      return Icons.pan_tool_alt_rounded;
    default:
      return Icons.bolt_rounded;
  }
}
