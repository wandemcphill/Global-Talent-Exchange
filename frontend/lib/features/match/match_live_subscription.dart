import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

class MatchSubscriptionRequest {
  const MatchSubscriptionRequest({
    required this.matchId,
    required this.frameCount,
  });

  final String matchId;
  final int frameCount;

  @override
  bool operator ==(Object other) {
    return other is MatchSubscriptionRequest &&
        other.matchId == matchId &&
        other.frameCount == frameCount;
  }

  @override
  int get hashCode => Object.hash(matchId, frameCount);
}

class MatchSubscriptionTick {
  const MatchSubscriptionTick({
    required this.channel,
    required this.frameIndex,
    required this.feedLatencyMs,
    required this.tick,
    required this.connected,
  });

  final String channel;
  final int frameIndex;
  final int feedLatencyMs;
  final int tick;
  final bool connected;
}

abstract interface class MatchLiveSubscriptionService {
  Stream<MatchSubscriptionTick> subscribe({
    required String matchId,
    required int frameCount,
  });
}

class DisconnectedMatchLiveSubscriptionService
    implements MatchLiveSubscriptionService {
  const DisconnectedMatchLiveSubscriptionService();

  @override
  Stream<MatchSubscriptionTick> subscribe({
    required String matchId,
    required int frameCount,
  }) {
    return Stream<MatchSubscriptionTick>.value(
      MatchSubscriptionTick(
        channel: 'match:$matchId',
        frameIndex: 0,
        feedLatencyMs: 0,
        tick: 0,
        connected: false,
      ),
    );
  }
}

class MockMatchLiveSubscriptionService implements MatchLiveSubscriptionService {
  const MockMatchLiveSubscriptionService();

  static const Duration _cadence = Duration(seconds: 3);

  @override
  Stream<MatchSubscriptionTick> subscribe({
    required String matchId,
    required int frameCount,
  }) {
    if (frameCount <= 0) {
      return const Stream<MatchSubscriptionTick>.empty();
    }

    int frameIndex = 0;
    int direction = 1;
    int tick = 0;

    MatchSubscriptionTick buildTick() {
      return MatchSubscriptionTick(
        channel: 'match:$matchId',
        frameIndex: frameIndex,
        feedLatencyMs: _latencyFor(matchId, tick, frameIndex),
        tick: tick,
        connected: true,
      );
    }

    return Stream<MatchSubscriptionTick>.multi((
      MultiStreamController<MatchSubscriptionTick> controller,
    ) {
      controller.add(buildTick());
      final Timer timer = Timer.periodic(_cadence, (Timer value) {
        tick += 1;
        if (frameCount > 1) {
          if (frameIndex == frameCount - 1) {
            direction = -1;
          } else if (frameIndex == 0) {
            direction = 1;
          }
          frameIndex += direction;
        }
        controller.add(buildTick());
      });
      controller.onCancel = timer.cancel;
    });
  }

  int _latencyFor(String matchId, int tick, int frameIndex) {
    final int base = matchId.codeUnits.fold<int>(
      0,
      (int sum, int code) => sum + code,
    );
    return 96 + ((base + (tick * 17) + (frameIndex * 11)) % 84);
  }
}

final Provider<MatchLiveSubscriptionService>
matchLiveSubscriptionServiceProvider = Provider<MatchLiveSubscriptionService>(
  (Ref ref) => const DisconnectedMatchLiveSubscriptionService(),
);

final matchLiveSubscriptionProvider = StreamProvider.autoDispose
    .family<MatchSubscriptionTick, MatchSubscriptionRequest>((
      Ref ref,
      MatchSubscriptionRequest request,
    ) {
      final MatchLiveSubscriptionService service = ref.watch(
        matchLiveSubscriptionServiceProvider,
      );
      return service.subscribe(
        matchId: request.matchId,
        frameCount: request.frameCount,
      );
    });
