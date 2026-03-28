import 'action_registry.dart';
import 'event_service.dart';

class ActionInvocation {
  const ActionInvocation({
    required this.action,
    required this.clipId,
    this.commitImmediately = false,
    this.userId,
    this.watchTimeMs,
    this.videoLengthMs,
    this.device,
    this.country,
    this.referrer,
    this.contentType = 'clip',
    this.formatKey,
    this.clipEventType,
    this.teamName,
    this.tags = const <String>[],
  });

  final String action;
  final String clipId;
  final bool commitImmediately;
  final String? userId;
  final int? watchTimeMs;
  final int? videoLengthMs;
  final String? device;
  final String? country;
  final String? referrer;
  final String? contentType;
  final String? formatKey;
  final String? clipEventType;
  final String? teamName;
  final List<String> tags;
}

abstract class ClipActionDispatcher {
  Future<void> dispatch(ActionInvocation invocation);

  void dispose() {}
}

class ActionPipeline implements ClipActionDispatcher {
  ActionPipeline({ActionRegistry? registry, EventService? eventService})
    : _registry = registry ?? ActionRegistry(),
      _eventService = eventService ?? EventService.standard(),
      _ownsEventService = eventService == null;

  final ActionRegistry _registry;
  final EventService _eventService;
  final bool _ownsEventService;

  @override
  Future<void> dispatch(ActionInvocation invocation) async {
    final ActionRegistration registration = _registry.resolve(
      invocation.action,
    );
    if (registration.api != ActionRegistry.clipEventsApi) {
      final StateError error = StateError(
        'Action "${invocation.action}" is bound to unsupported API '
        '"${registration.api}".',
      );
      assert(() {
        throw error;
      }());
      throw error;
    }
    await _eventService.trackEvent(
      TrackEventRequest(
        clipId: invocation.clipId,
        eventType: registration.eventType,
        userId: invocation.userId,
        watchTimeMs: invocation.watchTimeMs,
        videoLengthMs: invocation.videoLengthMs,
        device: invocation.device,
        country: invocation.country,
        referrer: invocation.referrer,
        contentType: invocation.contentType,
        formatKey: invocation.formatKey,
        clipEventType: invocation.clipEventType,
        teamName: invocation.teamName,
        tags: invocation.tags,
      ),
    );
    if (invocation.commitImmediately) {
      await _eventService.flush(propagateError: true);
    }
  }

  @override
  void dispose() {
    if (_ownsEventService) {
      _eventService.dispose();
    }
  }
}
