import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/match_playback_controller.dart';
import 'package:gte_frontend/data/live_match_fixtures.dart';
import 'package:gte_frontend/data/match_gift_api.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/match_event.dart';
import 'package:gte_frontend/models/match_timeline_frame.dart';
import 'package:gte_frontend/models/match_view_state.dart';
import 'package:gte_frontend/models/match_viewer_presentation.dart';
import 'package:gte_frontend/services/match_3d_bridge.dart';
import 'package:gte_frontend/services/match_3d_live_bootstrap_service.dart';
import 'package:gte_frontend/services/match_3d_monetization_service.dart';
import 'package:gte_frontend/services/match_commentary_engine.dart';
import 'package:gte_frontend/services/match_viewer_mapper.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/match/broadcast/gtex_gifting_sheet.dart';
import 'package:gte_frontend/widgets/match/pitch_2d_widget.dart';

typedef MatchViewStateLoader = Future<MatchViewState> Function();
typedef MatchViewContinuationLoader =
    Future<MatchViewState> Function({
      required String matchKey,
      required String continuationToken,
    });

class GtexMatchViewerScreen extends StatefulWidget {
  const GtexMatchViewerScreen({
    super.key,
    required this.competition,
    required this.matchKey,
    this.fallbackSnapshot,
    this.preferFallback = false,
    this.presentationMode = MatchViewerPresentationMode.replay,
    this.renderMode = RenderMode.twoD,
    this.viewStateLoader,
    this.continuationLoader,
    this.entitlement = const Match3dUserEntitlement(),
    this.isSpectator = false,
    this.monetizationService,
    this.giftClient,
    this.titleOverride,
    this.engineBridge,
    this.androidLiveBootstrapProvisioner,
  });

  final CompetitionSummary competition;
  final String matchKey;
  final LiveMatchSnapshot? fallbackSnapshot;
  final bool preferFallback;
  final MatchViewerPresentationMode presentationMode;
  final RenderMode renderMode;
  final MatchViewStateLoader? viewStateLoader;
  final MatchViewContinuationLoader? continuationLoader;
  final Match3dUserEntitlement entitlement;
  final bool isSpectator;
  final Match3dMonetizationService? monetizationService;
  final MatchGiftClient? giftClient;
  final String? titleOverride;
  final Match3DBridge? engineBridge;
  final Match3dAndroidLiveBootstrapProvisioner? androidLiveBootstrapProvisioner;

  @override
  State<GtexMatchViewerScreen> createState() => _GtexMatchViewerScreenState();
}

class _GtexMatchViewerScreenState extends State<GtexMatchViewerScreen>
    with SingleTickerProviderStateMixin {
  late Future<MatchViewState> _viewStateFuture;
  MatchPlaybackController? _controller;

  @override
  void initState() {
    super.initState();
    _viewStateFuture = _load();
  }

  @override
  void didUpdateWidget(covariant GtexMatchViewerScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.matchKey != widget.matchKey ||
        oldWidget.viewStateLoader != widget.viewStateLoader ||
        oldWidget.fallbackSnapshot != widget.fallbackSnapshot ||
        oldWidget.preferFallback != widget.preferFallback) {
      _reload();
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  Future<MatchViewState> _load() {
    final MatchViewStateLoader? loader = widget.viewStateLoader;
    if (loader != null) {
      return loader();
    }
    return MatchViewerMapper.load(
      competition: widget.competition,
      matchKey: widget.matchKey,
      fallbackSnapshot: widget.fallbackSnapshot,
      preferFallback: widget.preferFallback,
    );
  }

  void _reload() {
    _controller?.dispose();
    _controller = null;
    setState(() {
      _viewStateFuture = _load();
    });
  }

  Future<void> _openGiftSheet(MatchGiftTarget target) {
    return GtexGiftingSheet.show(
      context,
      unitLabel: _giftUnitLabelForScope(target.sourceScope),
      onSelected: (MatchGiftCatalogItem gift) => _sendGift(target, gift),
    );
  }

  Future<void> _sendGift(
    MatchGiftTarget target,
    MatchGiftCatalogItem gift,
  ) async {
    final MatchGiftClient? client = widget.giftClient;
    if (client == null) {
      return;
    }
    try {
      final MatchGiftReceipt receipt = await client.sendGift(
        target: target,
        gift: gift,
      );
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(receipt.confirmationMessage)));
    } catch (_) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Gift could not be sent.')));
    }
  }

  MatchPlaybackController _ensureController(MatchViewState viewState) {
    final MatchPlaybackController? existing = _controller;
    if (existing != null && existing.viewState.matchId == viewState.matchId) {
      return existing;
    }
    existing?.dispose();
    final MatchPlaybackController created = MatchPlaybackController(
      vsync: this,
      viewState: viewState,
      autoplay: true,
    );
    _controller = created;
    return created;
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        body: FutureBuilder<MatchViewState>(
          future: _viewStateFuture,
          builder: (
            BuildContext context,
            AsyncSnapshot<MatchViewState> snapshot,
          ) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const _MatchViewerLoading();
            }
            if (snapshot.hasError || !snapshot.hasData) {
              return _MatchViewerError(onReload: _reload);
            }
            final MatchViewState viewState = snapshot.data!;
            final MatchGiftTarget? giftTarget = MatchGiftTarget.fromMetadata(
              viewState.monetization.metadata,
            );
            if (viewState.frames.isEmpty) {
              return _MatchViewerError(
                onReload: _reload,
                message:
                    'This match does not yet have a 2D timeline to display.',
              );
            }
            final MatchPlaybackController controller = _ensureController(
              viewState,
            );
            return ListenableBuilder(
              listenable: controller,
              builder: (BuildContext context, Widget? child) {
                final MatchTimelineFrame frame = controller.displayFrame;
                final MatchEvent? activeEvent = controller.activeEvent;
                return SafeArea(
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(14, 10, 14, 12),
                    child: Column(
                      children: <Widget>[
                        _ScoreStrip(
                          timeLabel: _formatPlaybackClock(
                            controller.positionSeconds,
                          ),
                          homeName: viewState.homeTeam.shortName,
                          awayName: viewState.awayTeam.shortName,
                          homeScore: frame.homeScore,
                          awayScore: frame.awayScore,
                          onReload: _reload,
                        ),
                        const SizedBox(height: 10),
                        Expanded(
                          child: _MatchLiveLayout(
                            viewState: viewState,
                            frame: frame,
                            previousFrame: controller.leftFrame,
                            activeEvent: activeEvent,
                            positionSeconds: controller.positionSeconds,
                          ),
                        ),
                        const SizedBox(height: 10),
                        _CommentaryCapsule(
                          text: _commentaryFor(
                            activeEvent: activeEvent,
                            frame: frame,
                          ),
                        ),
                        if (widget.giftClient != null &&
                            giftTarget != null) ...<Widget>[
                          const SizedBox(height: 8),
                          _GiftActionButton(
                            recipientLabel: giftTarget.recipientLabel,
                            onPressed: () => _openGiftSheet(giftTarget),
                          ),
                        ],
                        if (!widget.isSpectator) ...<Widget>[
                          const SizedBox(height: 8),
                          _CompactControlBar(controller: controller),
                        ],
                      ],
                    ),
                  ),
                );
              },
            );
          },
        ),
      ),
    );
  }
}

class _GiftActionButton extends StatelessWidget {
  const _GiftActionButton({
    required this.recipientLabel,
    required this.onPressed,
  });

  final String recipientLabel;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.center,
      child: FilledButton.icon(
        key: const Key('match-2d-gift-button'),
        onPressed: onPressed,
        icon: const Icon(Icons.card_giftcard_outlined),
        label: Text(
          'Gift $recipientLabel',
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        style: FilledButton.styleFrom(
          backgroundColor: const Color(0xFF7DD3FC),
          foregroundColor: const Color(0xFF07111D),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          minimumSize: const Size(0, 40),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        ),
      ),
    );
  }
}

class _MatchLiveLayout extends StatelessWidget {
  const _MatchLiveLayout({
    required this.viewState,
    required this.frame,
    required this.previousFrame,
    required this.activeEvent,
    required this.positionSeconds,
  });

  final MatchViewState viewState;
  final MatchTimelineFrame frame;
  final MatchTimelineFrame previousFrame;
  final MatchEvent? activeEvent;
  final double positionSeconds;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool wide = constraints.maxWidth >= 980;
        final Widget pitch = _PitchStage(
          viewState: viewState,
          frame: frame,
          previousFrame: previousFrame,
          activeEvent: activeEvent,
        );
        final Widget insightPanel = _MatchInsightPanel(
          viewState: viewState,
          frame: frame,
          activeEvent: activeEvent,
          positionSeconds: positionSeconds,
          compact: !wide,
        );

        if (wide) {
          return Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              Expanded(flex: 7, child: pitch),
              const SizedBox(width: 10),
              SizedBox(width: 330, child: insightPanel),
            ],
          );
        }

        final double panelHeight =
            math
                .min(190, math.max(72, constraints.maxHeight * 0.34))
                .toDouble();
        return Column(
          children: <Widget>[
            Expanded(child: pitch),
            const SizedBox(height: 8),
            SizedBox(height: panelHeight, child: insightPanel),
          ],
        );
      },
    );
  }
}

class _PitchStage extends StatelessWidget {
  const _PitchStage({
    required this.viewState,
    required this.frame,
    required this.previousFrame,
    required this.activeEvent,
  });

  final MatchViewState viewState;
  final MatchTimelineFrame frame;
  final MatchTimelineFrame previousFrame;
  final MatchEvent? activeEvent;

  @override
  Widget build(BuildContext context) {
    return Container(
      key: const Key('match-2d-pitch-stage'),
      decoration: BoxDecoration(
        color: const Color(0x66111827),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      clipBehavior: Clip.antiAlias,
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(6),
          child: MatchPitch2D(
            viewState: viewState,
            frame: frame,
            previousFrame: previousFrame,
            activeEvent: activeEvent,
          ),
        ),
      ),
    );
  }
}

class _MatchInsightPanel extends StatelessWidget {
  const _MatchInsightPanel({
    required this.viewState,
    required this.frame,
    required this.activeEvent,
    required this.positionSeconds,
    required this.compact,
  });

  final MatchViewState viewState;
  final MatchTimelineFrame frame;
  final MatchEvent? activeEvent;
  final double positionSeconds;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final Widget body =
        compact
            ? SingleChildScrollView(
              padding: const EdgeInsets.all(8),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  _TacticalSummary(viewState: viewState, frame: frame),
                  const SizedBox(height: 8),
                  _PlayerPanels(
                    viewState: viewState,
                    frame: frame,
                    activeEvent: activeEvent,
                    compact: true,
                  ),
                  const SizedBox(height: 8),
                  _EventFeed(
                    events: _feedEventsForPosition(
                      events: viewState.events,
                      positionSeconds: positionSeconds,
                    ),
                    activeEvent: activeEvent,
                    compact: true,
                  ),
                ],
              ),
            )
            : Padding(
              padding: const EdgeInsets.all(8),
              child: Column(
                children: <Widget>[
                  _TacticalSummary(viewState: viewState, frame: frame),
                  const SizedBox(height: 8),
                  _PlayerPanels(
                    viewState: viewState,
                    frame: frame,
                    activeEvent: activeEvent,
                    compact: false,
                  ),
                  const SizedBox(height: 8),
                  Expanded(
                    child: _EventFeed(
                      events: _feedEventsForPosition(
                        events: viewState.events,
                        positionSeconds: positionSeconds,
                      ),
                      activeEvent: activeEvent,
                      compact: false,
                    ),
                  ),
                ],
              ),
            );

    return Container(
      key: const Key('match-2d-live-panel'),
      decoration: BoxDecoration(
        color: const Color(0xD90B1220),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
      ),
      clipBehavior: Clip.antiAlias,
      child: body,
    );
  }
}

class _TacticalSummary extends StatelessWidget {
  const _TacticalSummary({required this.viewState, required this.frame});

  final MatchViewState viewState;
  final MatchTimelineFrame frame;

  @override
  Widget build(BuildContext context) {
    final String possession =
        frame.possessionSide == MatchViewerSide.home
            ? viewState.homeTeam.shortName
            : viewState.awayTeam.shortName;
    final String shape =
        '${viewState.homeTeam.formation} / ${viewState.awayTeam.formation}';
    final String pressure = '${(_pressureIndex(frame) * 100).round()}%';

    return _PanelBlock(
      key: const Key('match-2d-tactical-summary'),
      title: 'Tactical Overlay',
      child: Wrap(
        spacing: 6,
        runSpacing: 6,
        children: <Widget>[
          _InfoChip(label: 'Shape', value: shape),
          _InfoChip(label: 'Heat', value: _heatZoneLabel(frame)),
          _InfoChip(label: 'Press', value: pressure),
          _InfoChip(label: 'Ball', value: possession),
        ],
      ),
    );
  }
}

class _PlayerPanels extends StatelessWidget {
  const _PlayerPanels({
    required this.viewState,
    required this.frame,
    required this.activeEvent,
    required this.compact,
  });

  final MatchViewState viewState;
  final MatchTimelineFrame frame;
  final MatchEvent? activeEvent;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final Widget home = _TeamPlayerPanel(
      team: viewState.homeTeam,
      players: _focusPlayers(
        frame: frame,
        side: MatchViewerSide.home,
        limit: compact ? 2 : 3,
      ),
      activeEvent: activeEvent,
    );
    final Widget away = _TeamPlayerPanel(
      team: viewState.awayTeam,
      players: _focusPlayers(
        frame: frame,
        side: MatchViewerSide.away,
        limit: compact ? 2 : 3,
      ),
      activeEvent: activeEvent,
    );

    return _PanelBlock(
      key: const Key('match-2d-player-panels'),
      title: 'Player Panels',
      child:
          compact
              ? Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Expanded(child: home),
                  const SizedBox(width: 8),
                  Expanded(child: away),
                ],
              )
              : Column(
                children: <Widget>[home, const SizedBox(height: 8), away],
              ),
    );
  }
}

class _TeamPlayerPanel extends StatelessWidget {
  const _TeamPlayerPanel({
    required this.team,
    required this.players,
    required this.activeEvent,
  });

  final MatchViewerTeam team;
  final List<MatchViewerPlayerFrame> players;
  final MatchEvent? activeEvent;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              _TeamDot(color: _parseHexColor(team.primaryColorHex)),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  '${team.shortName} ${team.formation}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 0,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 7),
          for (final MatchViewerPlayerFrame player in players)
            _PlayerFocusRow(
              player: player,
              teamColor: _parseHexColor(team.primaryColorHex),
              label: _playerDisplayLabel(player, activeEvent),
            ),
        ],
      ),
    );
  }
}

class _PlayerFocusRow extends StatelessWidget {
  const _PlayerFocusRow({
    required this.player,
    required this.teamColor,
    required this.label,
  });

  final MatchViewerPlayerFrame player;
  final Color teamColor;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 5),
      child: Row(
        children: <Widget>[
          CircleAvatar(
            radius: 13,
            backgroundColor: teamColor,
            child: Text(
              _avatarLabel(player),
              style: Theme.of(context).textTheme.labelSmall?.copyWith(
                color: _textColorFor(teamColor),
                fontWeight: FontWeight.w900,
                letterSpacing: 0,
              ),
            ),
          ),
          const SizedBox(width: 7),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0,
                  ),
                ),
                Text(
                  '${player.animationState.label} - ${player.staminaPct.clamp(0, 100)}%',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: Colors.white.withValues(alpha: 0.62),
                    letterSpacing: 0,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _EventFeed extends StatelessWidget {
  const _EventFeed({
    required this.events,
    required this.activeEvent,
    required this.compact,
  });

  final List<MatchEvent> events;
  final MatchEvent? activeEvent;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final List<Widget> tiles = events
        .map(
          (MatchEvent event) =>
              _EventFeedTile(event: event, active: activeEvent?.id == event.id),
        )
        .toList(growable: false);

    return _PanelBlock(
      key: const Key('match-2d-event-feed'),
      title: 'Event Feed',
      expandChild: !compact,
      child:
          compact
              ? Column(children: tiles.take(4).toList(growable: false))
              : ListView(padding: EdgeInsets.zero, children: tiles),
    );
  }
}

class _EventFeedTile extends StatelessWidget {
  const _EventFeedTile({required this.event, required this.active});

  final MatchEvent event;
  final bool active;

  @override
  Widget build(BuildContext context) {
    final Color accent =
        active ? const Color(0xFF7DD3FC) : Colors.white.withValues(alpha: 0.42);
    return Container(
      margin: const EdgeInsets.only(top: 6),
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color:
            active
                ? const Color(0x1F7DD3FC)
                : Colors.white.withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: accent.withValues(alpha: active ? 0.55 : 1)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(event.icon, color: accent, size: 17),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  "${event.minute}'  ${event.bannerText}",
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  MatchCommentaryEngine.lineForEvent(event),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: Colors.white.withValues(alpha: 0.66),
                    letterSpacing: 0,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _PanelBlock extends StatelessWidget {
  const _PanelBlock({
    super.key,
    required this.title,
    required this.child,
    this.expandChild = false,
  });

  final String title;
  final Widget child;
  final bool expandChild;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.16),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white.withValues(alpha: 0.07)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: expandChild ? MainAxisSize.max : MainAxisSize.min,
        children: <Widget>[
          Text(
            title,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: Colors.white.withValues(alpha: 0.86),
              fontWeight: FontWeight.w900,
              letterSpacing: 0,
            ),
          ),
          const SizedBox(height: 6),
          if (expandChild) Expanded(child: child) else child,
        ],
      ),
    );
  }
}

class _InfoChip extends StatelessWidget {
  const _InfoChip({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minHeight: 26),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Text(
        '$label $value',
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
          color: Colors.white.withValues(alpha: 0.82),
          fontWeight: FontWeight.w800,
          letterSpacing: 0,
        ),
      ),
    );
  }
}

class _TeamDot extends StatelessWidget {
  const _TeamDot({required this.color});

  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 10,
      height: 10,
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
        border: Border.all(color: Colors.white.withValues(alpha: 0.65)),
      ),
    );
  }
}

class _ScoreStrip extends StatelessWidget {
  const _ScoreStrip({
    required this.timeLabel,
    required this.homeName,
    required this.awayName,
    required this.homeScore,
    required this.awayScore,
    required this.onReload,
  });

  final String timeLabel;
  final String homeName;
  final String awayName;
  final int homeScore;
  final int awayScore;
  final VoidCallback onReload;

  @override
  Widget build(BuildContext context) {
    final TextStyle? teamStyle = Theme.of(context).textTheme.labelLarge
        ?.copyWith(color: Colors.white, fontWeight: FontWeight.w800);
    return Container(
      key: const Key('match-2d-score-strip'),
      constraints: const BoxConstraints(minHeight: 44),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: const Color(0xEE111827),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
      ),
      child: Row(
        children: <Widget>[
          _TimePill(label: timeLabel),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              homeName.toUpperCase(),
              textAlign: TextAlign.right,
              overflow: TextOverflow.ellipsis,
              style: teamStyle,
            ),
          ),
          const SizedBox(width: 12),
          Text(
            '$homeScore - $awayScore',
            key: const Key('match-2d-scoreline'),
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              color: Colors.white,
              fontWeight: FontWeight.w900,
              letterSpacing: 0,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              awayName.toUpperCase(),
              overflow: TextOverflow.ellipsis,
              style: teamStyle,
            ),
          ),
          const SizedBox(width: 8),
          Tooltip(
            message: 'Reload match',
            child: IconButton(
              onPressed: onReload,
              icon: const Icon(Icons.refresh, size: 18),
              color: Colors.white,
              style: IconButton.styleFrom(
                backgroundColor: Colors.white.withValues(alpha: 0.08),
                fixedSize: const Size.square(32),
                minimumSize: const Size.square(32),
                padding: EdgeInsets.zero,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _TimePill extends StatelessWidget {
  const _TimePill({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      key: const Key('match-2d-clock'),
      width: 64,
      alignment: Alignment.center,
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 7),
      decoration: BoxDecoration(
        color: const Color(0xFF0B5CAD),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelLarge?.copyWith(
          color: Colors.white,
          fontWeight: FontWeight.w900,
          letterSpacing: 0,
        ),
      ),
    );
  }
}

class _CommentaryCapsule extends StatelessWidget {
  const _CommentaryCapsule({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.center,
      child: Container(
        key: const Key('match-2d-commentary-bar'),
        constraints: const BoxConstraints(maxWidth: 620, minHeight: 30),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: const Color(0xEA0B1220),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: const Color(0xFFEE7CCC), width: 1.2),
          boxShadow: <BoxShadow>[
            BoxShadow(
              color: const Color(0xFFEE7CCC).withValues(alpha: 0.24),
              blurRadius: 12,
              spreadRadius: 0.5,
            ),
          ],
        ),
        child: Text(
          text,
          textAlign: TextAlign.center,
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          style: Theme.of(context).textTheme.labelMedium?.copyWith(
            color: Colors.white,
            fontWeight: FontWeight.w700,
            letterSpacing: 0,
          ),
        ),
      ),
    );
  }
}

class _CompactControlBar extends StatelessWidget {
  const _CompactControlBar({required this.controller});

  final MatchPlaybackController controller;

  @override
  Widget build(BuildContext context) {
    return Container(
      key: const Key('match-2d-controls'),
      constraints: const BoxConstraints(maxWidth: 620),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.24),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Row(
        children: <Widget>[
          _ControlIconButton(
            tooltip: controller.isPlaying ? 'Pause' : 'Play',
            icon: controller.isPlaying ? Icons.pause : Icons.play_arrow,
            onPressed: controller.togglePlayPause,
          ),
          _ControlIconButton(
            tooltip: 'Restart',
            icon: Icons.replay,
            onPressed: controller.restart,
          ),
          _ControlIconButton(
            tooltip: 'Speed ${controller.speed.toStringAsFixed(0)}x',
            icon: Icons.speed,
            onPressed: controller.cycleSpeed,
          ),
          _ControlIconButton(
            tooltip: 'Next event',
            icon: Icons.skip_next,
            onPressed: controller.jumpToNextEvent,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: LinearProgressIndicator(
              value: controller.progress.clamp(0, 1),
              minHeight: 5,
              borderRadius: BorderRadius.circular(999),
              backgroundColor: Colors.white.withValues(alpha: 0.10),
              valueColor: const AlwaysStoppedAnimation<Color>(
                Color(0xFF7DD3FC),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ControlIconButton extends StatelessWidget {
  const _ControlIconButton({
    required this.tooltip,
    required this.icon,
    required this.onPressed,
  });

  final String tooltip;
  final IconData icon;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: tooltip,
      child: IconButton(
        onPressed: onPressed,
        icon: Icon(icon, size: 18),
        color: Colors.white,
        style: IconButton.styleFrom(
          backgroundColor: Colors.white.withValues(alpha: 0.08),
          fixedSize: const Size.square(34),
          minimumSize: const Size.square(34),
          padding: EdgeInsets.zero,
        ),
      ),
    );
  }
}

class _MatchViewerLoading extends StatelessWidget {
  const _MatchViewerLoading();

  @override
  Widget build(BuildContext context) {
    return const SafeArea(
      child: Padding(
        padding: EdgeInsets.all(20),
        child: GteStatePanel(
          eyebrow: 'MATCHDAY',
          title: 'Loading 2D match',
          message: 'Preparing the pitch, squads, ball, and commentary.',
          icon: Icons.sports_soccer,
          accentColor: GteShellTheme.accentArena,
          isLoading: true,
        ),
      ),
    );
  }
}

class _MatchViewerError extends StatelessWidget {
  const _MatchViewerError({
    required this.onReload,
    this.message = 'Unable to load the 2D match timeline right now.',
  });

  final VoidCallback onReload;
  final String message;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: GteStatePanel(
          title: 'Match unavailable',
          message: message,
          icon: Icons.warning_amber_outlined,
          actionLabel: 'Retry',
          onAction: onReload,
        ),
      ),
    );
  }
}

String _formatPlaybackClock(double seconds) {
  final int totalSeconds = math.max(0, seconds.floor());
  final int minutes = totalSeconds ~/ 60;
  final int remainder = totalSeconds % 60;
  return '${minutes.toString().padLeft(2, '0')}:${remainder.toString().padLeft(2, '0')}';
}

String _commentaryFor({
  required MatchEvent? activeEvent,
  required MatchTimelineFrame frame,
}) {
  if (activeEvent != null) {
    return MatchCommentaryEngine.lineForEvent(activeEvent, frame: frame);
  }
  final String? banner = frame.eventBanner?.trim();
  if (banner != null && banner.isNotEmpty) {
    return banner;
  }
  return MatchCommentaryEngine.fallbackForFrame(frame);
}

List<MatchEvent> _feedEventsForPosition({
  required List<MatchEvent> events,
  required double positionSeconds,
}) {
  final List<MatchEvent> visible = events
      .where((MatchEvent event) => event.timeSeconds <= positionSeconds + 12)
      .toList(growable: true);
  if (visible.isEmpty) {
    return events.take(4).toList(growable: false);
  }
  visible.sort(
    (MatchEvent left, MatchEvent right) =>
        right.timeSeconds.compareTo(left.timeSeconds),
  );
  return visible.take(6).toList(growable: false);
}

List<MatchViewerPlayerFrame> _focusPlayers({
  required MatchTimelineFrame frame,
  required MatchViewerSide side,
  required int limit,
}) {
  final List<MatchViewerPlayerFrame> players = frame.players
      .where((MatchViewerPlayerFrame player) => player.side == side)
      .where((MatchViewerPlayerFrame player) => player.active)
      .toList(growable: true);
  players.sort((MatchViewerPlayerFrame left, MatchViewerPlayerFrame right) {
    return _playerFocusScore(
      frame,
      right,
    ).compareTo(_playerFocusScore(frame, left));
  });
  return players.take(limit).toList(growable: false);
}

int _playerFocusScore(MatchTimelineFrame frame, MatchViewerPlayerFrame player) {
  int score = 0;
  if (frame.ball.ownerPlayerId == player.playerId) {
    score += 100;
  }
  if (player.highlighted) {
    score += 60;
  }
  if (player.state == MatchViewerPlayerState.attacking ||
      player.state == MatchViewerPlayerState.pressing ||
      player.state == MatchViewerPlayerState.moving) {
    score += 18;
  }
  if (player.line == MatchPlayerLine.attack) {
    score += 8;
  }
  if (player.line == MatchPlayerLine.midfield) {
    score += 4;
  }
  return score;
}

String _playerDisplayLabel(
  MatchViewerPlayerFrame player,
  MatchEvent? activeEvent,
) {
  if (activeEvent?.primaryPlayerId == player.playerId &&
      (activeEvent?.primaryPlayerName ?? '').trim().isNotEmpty) {
    return activeEvent!.primaryPlayerName!.trim();
  }
  if (activeEvent?.secondaryPlayerId == player.playerId &&
      (activeEvent?.secondaryPlayerName ?? '').trim().isNotEmpty) {
    return activeEvent!.secondaryPlayerName!.trim();
  }
  final String label = player.label.trim();
  if (label.isNotEmpty && int.tryParse(label) == null) {
    return label;
  }
  final int? shirtNumber = player.shirtNumber;
  return shirtNumber == null ? 'Player $label' : 'Player $shirtNumber';
}

String _avatarLabel(MatchViewerPlayerFrame player) {
  final int? shirtNumber = player.shirtNumber;
  if (shirtNumber != null) {
    return shirtNumber.toString();
  }
  final String label = player.label.trim();
  if (label.isEmpty) {
    return '?';
  }
  return label.length <= 2 ? label : label.substring(0, 2);
}

String _heatZoneLabel(MatchTimelineFrame frame) {
  final String? explicit = frame.dangerZone?.trim();
  if (explicit != null && explicit.isNotEmpty) {
    return explicit.replaceAll('_', ' ');
  }
  switch (frame.possessionPhase) {
    case MatchPossessionPhase.boxAttack:
      return 'box';
    case MatchPossessionPhase.finalThird:
      return 'final third';
    case MatchPossessionPhase.transition:
      return 'transition';
    case MatchPossessionPhase.setPiece:
    case MatchPossessionPhase.restart:
      return 'set piece';
    case MatchPossessionPhase.buildUp:
      return 'build up';
    case MatchPossessionPhase.attack:
      return 'attack';
    case MatchPossessionPhase.recovery:
      return 'recovery';
    case MatchPossessionPhase.stoppage:
    case MatchPossessionPhase.deadBall:
      return 'stoppage';
    case MatchPossessionPhase.control:
    case null:
      return 'middle';
  }
}

double _pressureIndex(MatchTimelineFrame frame) {
  final double? explicit = frame.pressureIndex;
  if (explicit != null) {
    return explicit.clamp(0.08, 1.0).toDouble();
  }
  return switch (frame.possessionPhase) {
    MatchPossessionPhase.boxAttack => 0.82,
    MatchPossessionPhase.finalThird => 0.68,
    MatchPossessionPhase.attack => 0.54,
    MatchPossessionPhase.transition => 0.58,
    MatchPossessionPhase.setPiece => 0.62,
    MatchPossessionPhase.restart => 0.44,
    MatchPossessionPhase.buildUp => 0.42,
    MatchPossessionPhase.recovery => 0.30,
    MatchPossessionPhase.stoppage || MatchPossessionPhase.deadBall => 0.22,
    MatchPossessionPhase.control || null => 0.34,
  };
}

Color _parseHexColor(String value) {
  final String normalized = value.replaceAll('#', '').trim();
  final String hex = normalized.length == 6 ? 'FF$normalized' : normalized;
  return Color(int.tryParse(hex, radix: 16) ?? 0xFF2563EB);
}

Color _textColorFor(Color fill) {
  return fill.computeLuminance() > 0.45
      ? const Color(0xFF111827)
      : Colors.white;
}

String _giftUnitLabelForScope(String sourceScope) {
  final String normalized = sourceScope.trim().toLowerCase();
  if (normalized == 'gtex' ||
      normalized == 'gtex_platform' ||
      normalized == 'gtex_competition') {
    return 'GTEX Coin';
  }
  return 'Fan Coin';
}
