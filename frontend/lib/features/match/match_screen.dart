import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/constants/app_breakpoints.dart';
import '../../core/constants/app_spacing.dart';
import '../../core/theme/app_motion.dart';
import '../../shared/models/live_match.dart';
import '../../shared/providers/match_provider.dart';
import 'match_live_subscription.dart';
import 'widgets/match_screen_widgets.dart';

class MatchScreen extends ConsumerStatefulWidget {
  const MatchScreen({super.key});

  @override
  ConsumerState<MatchScreen> createState() => _MatchScreenState();
}

class _MatchScreenState extends ConsumerState<MatchScreen> {
  double _sheetExtent = 0;

  @override
  Widget build(BuildContext context) {
    final List<LiveMatch> matches = ref.watch(matchProvider);
    final LiveMatch featuredMatch = matches.first;
    final List<BroadcastMoment> moments = buildBroadcastMoments(featuredMatch);
    final MatchSubscriptionRequest request = MatchSubscriptionRequest(
      matchId: featuredMatch.id,
      frameCount: moments.length,
    );
    final AsyncValue<MatchSubscriptionTick> subscriptionValue = ref.watch(
      matchLiveSubscriptionProvider(request),
    );
    final MatchSubscriptionTick? subscription = subscriptionValue.maybeWhen(
      data: (MatchSubscriptionTick value) => value,
      orElse: () => null,
    );
    final int activeIndex =
        (subscription?.frameIndex ?? 0).clamp(0, moments.length - 1).toInt();
    final BroadcastMoment activeMoment = moments[activeIndex];
    final int feedLatencyMs = subscription?.feedLatencyMs ?? 128;
    final String liveChannel =
        subscription?.channel ?? 'match:${featuredMatch.id}';
    final bool connected = subscription?.connected ?? true;

    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool wide = constraints.maxWidth >= AppBreakpoints.medium;
        final double sheetMin = wide ? 0.18 : 0.24;
        final double sheetMax = wide ? 0.56 : 0.72;
        final double sceneHeight = constraints.maxHeight - (spacingMD * 2);
        final double activeSheetExtent =
            _sheetExtent == 0
                ? sheetMin
                : _sheetExtent.clamp(sheetMin, sheetMax);

        return Padding(
          padding: const EdgeInsets.all(spacingMD),
          child: NotificationListener<DraggableScrollableNotification>(
            onNotification: (DraggableScrollableNotification notification) {
              if ((notification.extent - _sheetExtent).abs() > 0.002) {
                setState(() {
                  _sheetExtent = notification.extent;
                });
              }
              return false;
            },
            child: ClipRRect(
              borderRadius: BorderRadius.circular(28),
              child: Stack(
                fit: StackFit.expand,
                children: <Widget>[
                  RepaintBoundary(
                    child: BroadcastPitchPlaceholder(
                      key: const Key('match-broadcast-placeholder'),
                      moment: activeMoment,
                      wide: wide,
                    ),
                  ),
                  ScoreOverlay(
                    key: const Key('match-score-overlay'),
                    match: featuredMatch,
                    moment: activeMoment,
                    liveCount: matches.length,
                    feedLatencyMs: feedLatencyMs,
                    liveChannel: liveChannel,
                    connected: connected,
                    wide: wide,
                  ),
                  PushSignalOverlay(
                    key: const Key('match-push-overlay'),
                    moment: activeMoment,
                    wide: wide,
                  ),
                  AnimatedPositioned(
                    duration: AppMotion.medium,
                    curve: AppMotion.easeInOut,
                    left: spacingMD,
                    right: spacingMD,
                    bottom: (sceneHeight * activeSheetExtent) + spacingMD,
                    child: CommentaryBar(
                      key: const Key('match-commentary-bar'),
                      moment: activeMoment,
                      wide: wide,
                    ),
                  ),
                  RepaintBoundary(
                    child: StatsPanel(
                      key: const Key('match-stats-panel'),
                      initialSize: sheetMin,
                      minSize: sheetMin,
                      maxSize: sheetMax,
                      moment: activeMoment,
                      liveChannel: liveChannel,
                      feedLatencyMs: feedLatencyMs,
                      matches: matches,
                      wide: wide,
                    ),
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
