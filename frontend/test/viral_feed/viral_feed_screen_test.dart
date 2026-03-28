import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/core/actions/action_pipeline.dart' as feed_actions;
import 'package:gte_frontend/core/theme/app_theme.dart';
import 'package:gte_frontend/features/viral_feed/data/viral_feed_models.dart';
import 'package:gte_frontend/features/viral_feed/data/viral_feed_repository.dart';
import 'package:gte_frontend/features/viral_feed/presentation/viral_feed_screen.dart';
import 'package:gte_frontend/services/reliability/reliable_event_queue.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues(<String, Object>{});
  });

  testWidgets('viral feed renders source controls and ranked clip summary', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      _buildHarness(
        repository: _FakeViralFeedRepository(
          _buildDeck(
            durationSeconds: 12,
            firstHook: "89' and the whole match flipped",
            firstSummaryLine:
                'The ranking engine pushed this clip because the pressure swing broke the match open.',
          ),
        ),
        dispatcher: _RecordingActionDispatcher(),
      ),
    );

    await tester.pumpAndSettle();

    expect(find.byKey(const Key('viral-feed-page-view')), findsOneWidget);
    expect(find.text('FOR YOU'), findsWidgets);
    expect(find.text('FOLLOWING'), findsOneWidget);
    expect(find.text("89' and the whole match flipped"), findsOneWidget);
    expect(find.text('Share to WhatsApp'), findsOneWidget);
    expect(
      find.text(
        'The ranking engine pushed this clip because the pressure swing broke the match open.',
      ),
      findsOneWidget,
    );
  });

  testWidgets('like bubble dispatches like action immediately', (
    WidgetTester tester,
  ) async {
    final _RecordingActionDispatcher dispatcher = _RecordingActionDispatcher();

    await tester.pumpWidget(
      _buildHarness(
        repository: _FakeViralFeedRepository(_buildDeck(durationSeconds: 12)),
        dispatcher: dispatcher,
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('viral-like-clip-001')));
    await tester.pump();

    expect(
      dispatcher.invocations.map(
        (feed_actions.ActionInvocation item) => item.action,
      ),
      contains('like'),
    );
    expect(
      dispatcher.invocations
          .where((feed_actions.ActionInvocation item) => item.action == 'like')
          .every(
            (feed_actions.ActionInvocation item) => item.commitImmediately,
          ),
      isTrue,
    );
  });

  testWidgets('page change dispatches scroll action for an incomplete clip', (
    WidgetTester tester,
  ) async {
    final _RecordingActionDispatcher dispatcher = _RecordingActionDispatcher();

    await tester.pumpWidget(
      _buildHarness(
        repository: _FakeViralFeedRepository(_buildDeck(durationSeconds: 5)),
        dispatcher: dispatcher,
      ),
    );
    await tester.pumpAndSettle();

    final PageView pageView = tester.widget<PageView>(
      find.byKey(const Key('viral-feed-page-view')),
    );
    pageView.onPageChanged?.call(1);
    await tester.pump();

    expect(
      dispatcher.invocations.map(
        (feed_actions.ActionInvocation item) => item.action,
      ),
      contains('scroll'),
    );
  });

  testWidgets('active clip dispatches complete after watch window', (
    WidgetTester tester,
  ) async {
    final _RecordingActionDispatcher dispatcher = _RecordingActionDispatcher();

    await tester.pumpWidget(
      _buildHarness(
        repository: _FakeViralFeedRepository(_buildDeck(durationSeconds: 0.02)),
        dispatcher: dispatcher,
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 30));

    expect(
      dispatcher.invocations.map(
        (feed_actions.ActionInvocation item) => item.action,
      ),
      contains('complete'),
    );
  });

  testWidgets('feed refresh trigger reloads the deck', (
    WidgetTester tester,
  ) async {
    final _CountingViralFeedRepository repository =
        _CountingViralFeedRepository(_buildDeck(durationSeconds: 5));
    final ReliableEventQueue eventQueue = ReliableEventQueue();
    addTearDown(() async {
      await eventQueue.dispose();
    });

    await tester.pumpWidget(
      _buildHarness(
        repository: repository,
        dispatcher: _RecordingActionDispatcher(),
        eventQueue: eventQueue,
      ),
    );
    await tester.pumpAndSettle();

    expect(repository.fetchCount, 1);

    await eventQueue.enqueue(
      topic: 'social',
      name: 'profile_follow_toggled',
      feedRefreshTrigger: FeedRefreshTrigger.followAction,
      requiresDelivery: false,
    );

    await tester.pump(const Duration(milliseconds: 350));
    await tester.pumpAndSettle();

    expect(repository.fetchCount, 2);
  });
}

Widget _buildHarness({
  required ViralFeedRepository repository,
  required feed_actions.ClipActionDispatcher dispatcher,
  ReliableEventQueue? eventQueue,
}) {
  return MaterialApp(
    theme: AppTheme.dark(),
    home: ViralFeedScreen(
      repository: repository,
      actionDispatcher: dispatcher,
      eventQueue: eventQueue,
    ),
  );
}

ViralFeedDeck _buildDeck({
  required double durationSeconds,
  String firstHook = 'Clip one hook',
  String firstSummaryLine = 'Clip one ranking summary',
}) {
  return ViralFeedDeck(
    source: ViralFeedSource.forYou,
    feedKey: 'feed-key',
    generatedAt: DateTime.utc(2026, 3, 28),
    cacheHit: false,
    clips: <ViralClip>[
      ViralClip(
        clipId: 'match-1::clip-001',
        matchId: 'match-1',
        highlightId: 'clip-001',
        title: 'Clip One',
        eventType: 'goal',
        minute: 18,
        viralScore: 88,
        rankingScore: 79.4,
        caption: ViralCaption(
          hook: firstHook,
          caption: 'Clip one caption',
          cta: 'Share to WhatsApp',
          hashtags: const <String>['#GTEX'],
        ),
        tags: const <String>['goal'],
        rank: 1,
        score: 98.2,
        feedSource: 'ranking_engine',
        metadata: <String, Object?>{
          'summary_line': firstSummaryLine,
          'creator_id': 'creator-1',
        },
        teamName: 'Royal Lagos FC',
        durationSeconds: durationSeconds,
      ),
      ViralClip(
        clipId: 'match-2::clip-002',
        matchId: 'match-2',
        highlightId: 'clip-002',
        title: 'Clip Two',
        eventType: 'assist',
        minute: 42,
        viralScore: 74,
        rankingScore: 68.2,
        caption: ViralCaption(
          hook: 'Clip two hook',
          caption: 'Clip two caption',
          cta: 'Share to WhatsApp',
          hashtags: <String>['#GTEX'],
        ),
        tags: <String>['assist'],
        rank: 2,
        score: 76.4,
        feedSource: 'ranking_engine',
        metadata: <String, Object?>{
          'summary_line': 'Second clip is held in the live deck.',
        },
        teamName: 'Harbor City',
        durationSeconds: durationSeconds,
      ),
    ],
  );
}

class _FakeViralFeedRepository implements ViralFeedRepository {
  _FakeViralFeedRepository(this._deck);

  final ViralFeedDeck _deck;

  @override
  Future<ViralFeedDeck> fetchDeck({
    ViralFeedSource source = ViralFeedSource.forYou,
    int limit = 10,
    bool refresh = true,
  }) async {
    return _deck;
  }
}

class _CountingViralFeedRepository extends _FakeViralFeedRepository {
  _CountingViralFeedRepository(super.deck);

  int fetchCount = 0;

  @override
  Future<ViralFeedDeck> fetchDeck({
    ViralFeedSource source = ViralFeedSource.forYou,
    int limit = 10,
    bool refresh = true,
  }) async {
    fetchCount += 1;
    return super.fetchDeck(source: source, limit: limit, refresh: refresh);
  }
}

class _RecordingActionDispatcher implements feed_actions.ClipActionDispatcher {
  final List<feed_actions.ActionInvocation> invocations =
      <feed_actions.ActionInvocation>[];

  @override
  Future<void> dispatch(feed_actions.ActionInvocation invocation) async {
    invocations.add(invocation);
  }

  @override
  void dispose() {}
}
