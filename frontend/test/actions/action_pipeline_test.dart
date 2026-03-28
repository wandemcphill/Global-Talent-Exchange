import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/core/actions/action_pipeline.dart';
import 'package:gte_frontend/core/actions/action_registry.dart';
import 'package:gte_frontend/core/actions/event_service.dart';

void main() {
  test('action registry exposes required clip actions', () {
    final ActionRegistry registry = ActionRegistry();

    expect(registry.resolve('like').toJson(), <String, String>{
      'api': 'POST /events/clip',
      'event_type': 'like',
    });
    expect(registry.resolve('scroll').toJson(), <String, String>{
      'api': 'POST /events/clip',
      'event_type': 'scroll',
    });
    expect(registry.resolve('complete').toJson(), <String, String>{
      'api': 'POST /events/clip',
      'event_type': 'complete',
    });
  });

  test('missing action registry entry throws', () {
    final ActionRegistry registry = ActionRegistry();

    expect(() => registry.resolve('bookmark'), throwsStateError);
  });

  test('action pipeline maps invocation to tracked event metadata', () async {
    final _RecordingEventService service = _RecordingEventService();
    final ActionPipeline pipeline = ActionPipeline(eventService: service);

    await pipeline.dispatch(
      const ActionInvocation(
        action: 'like',
        clipId: 'clip-101',
        videoLengthMs: 12000,
        referrer: 'viral_feed',
        clipEventType: 'goal',
        teamName: 'Royal Lagos FC',
        tags: <String>['goal', 'winner'],
      ),
    );

    expect(service.requests, hasLength(1));
    final TrackEventRequest request = service.requests.single;
    expect(request.clipId, 'clip-101');
    expect(request.eventType, 'like');
    expect(request.videoLengthMs, 12000);
    expect(request.referrer, 'viral_feed');
    expect(request.clipEventType, 'goal');
    expect(request.teamName, 'Royal Lagos FC');
    expect(request.tags, <String>['goal', 'winner']);
  });
}

class _RecordingEventService extends EventService {
  _RecordingEventService()
    : super(transport: _NoopTransport(), store: _MemoryStore());

  final List<TrackEventRequest> requests = <TrackEventRequest>[];

  @override
  Future<void> trackEvent(TrackEventRequest request) async {
    requests.add(request);
  }
}

class _NoopTransport implements EventTransport {
  @override
  Future<void> postEvents(List<QueuedEvent> events) async {}
}

class _MemoryStore implements EventQueueStore {
  String? _sessionId;

  @override
  Future<List<QueuedEvent>> readQueue() async => const <QueuedEvent>[];

  @override
  Future<String?> readSessionId() async => _sessionId;

  @override
  Future<void> writeQueue(List<QueuedEvent> events) async {}

  @override
  Future<void> writeSessionId(String sessionId) async {
    _sessionId = sessionId;
  }
}
