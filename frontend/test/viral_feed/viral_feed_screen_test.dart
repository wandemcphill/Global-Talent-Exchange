import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/core/actions/action_pipeline.dart' as feed_actions;
import 'package:gte_frontend/data/gte_api_contracts.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/viral_feed/data/viral_feed_models.dart';
import 'package:gte_frontend/features/viral_feed/data/viral_feed_repository.dart';
import 'package:gte_frontend/features/viral_feed/presentation/viral_feed_screen.dart';
import 'package:gte_frontend/services/reliability/reliable_event_queue.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../support/tolerant_golden_comparator.dart';

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

  testWidgets('viral feed premium surface matches golden', (
    WidgetTester tester,
  ) async {
    // Minor blur and antialiasing differences across local Windows runs and
    // Linux CI should not fail this full-screen golden.
    installTolerantGoldenComparator(
      testFilePath: 'test/viral_feed/viral_feed_screen_test.dart',
      precisionTolerance: 0.005,
    );

    await tester.binding.setSurfaceSize(const Size(430, 932));
    addTearDown(() => tester.binding.setSurfaceSize(null));

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

    await expectLater(
      find.byType(MaterialApp),
      matchesGoldenFile('../goldens/viral_feed_premium_surface.png'),
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
    final feed_actions.ActionInvocation likeInvocation = dispatcher.invocations
        .firstWhere(
          (feed_actions.ActionInvocation item) => item.action == 'like',
        );
    expect(likeInvocation.userId, 'user-feed-1');
    expect(likeInvocation.creatorId, 'creator-1');
    expect(likeInvocation.formatKey, 'match_recap');
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

  testWidgets('feed refresh trigger applies the refresh contract', (
    WidgetTester tester,
  ) async {
    final _CountingViralFeedRepository repository =
        _CountingViralFeedRepository(
          _buildDeck(durationSeconds: 5),
          refresh: ViralFeedDeckRefresh(
            replaceIndices: const <int>[0],
            newItems: <ViralClip>[
              _buildClip(
                clipId: 'match-3::clip-003',
                highlightId: 'clip-003',
                title: 'Clip Three',
                eventType: 'goal',
                minute: 77,
                summaryLine: 'The deck was refreshed in place.',
                creatorId: 'creator-3',
                formatKey: 'refresh',
                durationSeconds: 5,
              ),
            ],
          ),
        );
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

    expect(repository.fetchCount, 1);
    expect(repository.refreshCount, 1);
    expect(find.byKey(const Key('viral-hook-clip-003')), findsOneWidget);
    expect(find.text('The deck was refreshed in place.'), findsOneWidget);
  });

  testWidgets('three successful interactions trigger a for-you refresh', (
    WidgetTester tester,
  ) async {
    final _CountingViralFeedRepository repository =
        _CountingViralFeedRepository(
          _buildDeck(durationSeconds: 5),
          refresh: ViralFeedDeckRefresh(
            replaceIndices: const <int>[1],
            newItems: <ViralClip>[
              _buildClip(
                clipId: 'match-4::clip-004',
                highlightId: 'clip-004',
                title: 'Clip Four',
                eventType: 'assist',
                minute: 64,
                summaryLine: 'The deck reacted after three interactions.',
                creatorId: 'creator-4',
                formatKey: 'reaction',
                durationSeconds: 5,
              ),
            ],
          ),
        );
    final _RecordingActionDispatcher dispatcher = _RecordingActionDispatcher();
    final ReliableEventQueue eventQueue = ReliableEventQueue();
    addTearDown(() async {
      await eventQueue.dispose();
    });

    await tester.pumpWidget(
      _buildHarness(
        repository: repository,
        dispatcher: dispatcher,
        eventQueue: eventQueue,
      ),
    );
    await tester.pumpAndSettle();

    final PageView pageView = tester.widget<PageView>(
      find.byKey(const Key('viral-feed-page-view')),
    );
    pageView.onPageChanged?.call(1);
    await tester.pump();
    pageView.onPageChanged?.call(0);
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('viral-like-clip-001')));
    await tester.pump();
    for (
      int attempt = 0;
      attempt < 20 && repository.refreshCount == 0;
      attempt += 1
    ) {
      await tester.pump(const Duration(milliseconds: 50));
    }

    expect(repository.refreshCount, 1);
    expect(
      dispatcher.invocations
          .map((feed_actions.ActionInvocation item) => item.action)
          .where(
            (String action) =>
                const <String>{'scroll', 'like'}.contains(action),
          ),
      containsAll(<String>['scroll', 'like']),
    );
  });

  testWidgets('for-you refresh waits for the third interaction to finish', (
    WidgetTester tester,
  ) async {
    final _CountingViralFeedRepository repository =
        _CountingViralFeedRepository(_buildDeck(durationSeconds: 5));
    final _ControllableActionDispatcher dispatcher =
        _ControllableActionDispatcher(blockedActions: <String>{'like'});

    await tester.pumpWidget(
      _buildHarness(repository: repository, dispatcher: dispatcher),
    );
    await tester.pumpAndSettle();

    final PageView pageView = tester.widget<PageView>(
      find.byKey(const Key('viral-feed-page-view')),
    );
    pageView.onPageChanged?.call(1);
    await tester.pump();
    pageView.onPageChanged?.call(0);
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('viral-like-clip-001')));
    await tester.pump(const Duration(milliseconds: 50));

    expect(repository.refreshCount, 0);

    dispatcher.completeNext('like');
    await tester.pumpAndSettle();

    expect(repository.refreshCount, 1);
  });

  testWidgets('for-you refresh is guarded while a refresh is in progress', (
    WidgetTester tester,
  ) async {
    final _PendingRefreshViralFeedRepository repository =
        _PendingRefreshViralFeedRepository(
          _buildDeck(durationSeconds: 5),
          refresh: ViralFeedDeckRefresh(
            replaceIndices: const <int>[1],
            newItems: <ViralClip>[
              _buildClip(
                clipId: 'match-5::clip-005',
                highlightId: 'clip-005',
                title: 'Clip Five',
                eventType: 'assist',
                minute: 52,
                summaryLine:
                    'The deck refreshed once after a guarded threshold.',
                creatorId: 'creator-5',
                formatKey: 'guarded',
                durationSeconds: 5,
              ),
            ],
          ),
        );

    await tester.pumpWidget(
      _buildHarness(
        repository: repository,
        dispatcher: _RecordingActionDispatcher(),
      ),
    );
    await tester.pumpAndSettle();

    final PageView pageView = tester.widget<PageView>(
      find.byKey(const Key('viral-feed-page-view')),
    );
    pageView.onPageChanged?.call(1);
    await tester.pump();
    pageView.onPageChanged?.call(0);
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('viral-like-clip-001')));
    await tester.pump();

    expect(repository.refreshCount, 1);

    await tester.tap(find.text('Share to WhatsApp'));
    await tester.pump();
    pageView.onPageChanged?.call(1);
    await tester.pump();
    pageView.onPageChanged?.call(0);
    await tester.pump(const Duration(milliseconds: 50));

    expect(repository.refreshCount, 1);

    repository.completeNextRefresh();
    await tester.pumpAndSettle();

    expect(repository.refreshCount, 1);
  });

  testWidgets('refresh failure keeps the last good deck and shows feedback', (
    WidgetTester tester,
  ) async {
    final _FailingOnRefreshViralFeedRepository repository =
        _FailingOnRefreshViralFeedRepository(_buildDeck(durationSeconds: 5));

    await tester.pumpWidget(
      _buildHarness(
        repository: repository,
        dispatcher: _RecordingActionDispatcher(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('viral-hook-clip-001')), findsOneWidget);

    await tester.tap(find.byKey(const Key('viral-refresh-button')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('viral-hook-clip-001')), findsOneWidget);
    expect(find.text('Contract mismatch during refresh.'), findsOneWidget);
  });
}

Widget _buildHarness({
  required ViralFeedRepository repository,
  required feed_actions.ClipActionDispatcher dispatcher,
  ReliableEventQueue? eventQueue,
}) {
  return MaterialApp(
    theme: GteShellTheme.build(),
    home: ViralFeedScreen(
      currentUserId: 'user-feed-1',
      repository: repository,
      actionDispatcher: dispatcher,
      eventQueue: eventQueue ?? ReliableEventQueue(),
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
      _buildClip(
        clipId: 'match-1::clip-001',
        highlightId: 'clip-001',
        title: 'Clip One',
        eventType: 'goal',
        minute: 18,
        summaryLine: firstSummaryLine,
        creatorId: 'creator-1',
        formatKey: 'match_recap',
        durationSeconds: durationSeconds,
        hook: firstHook,
      ),
      _buildClip(
        clipId: 'match-2::clip-002',
        highlightId: 'clip-002',
        title: 'Clip Two',
        eventType: 'assist',
        minute: 42,
        summaryLine: 'Second clip is held in the live deck.',
        creatorId: 'creator-2',
        formatKey: 'quick_cut',
        durationSeconds: durationSeconds,
        teamName: 'Harbor City',
        feedSource: FeedSource.following,
        hook: 'Clip two hook',
      ),
    ],
  );
}

ViralClip _buildClip({
  required String clipId,
  required String highlightId,
  required String title,
  required String eventType,
  required int minute,
  required String summaryLine,
  required String creatorId,
  required String formatKey,
  required double durationSeconds,
  String teamName = 'Royal Lagos FC',
  String hook = 'Clip hook',
  String feedSource = FeedSource.forYou,
}) {
  return ViralClip(
    clipId: clipId,
    matchId: clipId.split('::').first,
    highlightId: highlightId,
    title: title,
    eventType: eventType,
    minute: minute,
    viralScore: 88,
    rankingScore: 79.4,
    caption: ViralCaption(
      hook: hook,
      caption: '$title caption',
      cta: 'Share to WhatsApp',
      hashtags: const <String>['#GTEX'],
    ),
    tags: <String>[eventType],
    rank: 1,
    score: 98.2,
    feedSource: feedSource,
    metadata: <String, Object?>{
      'summary_line': summaryLine,
      'creator_id': creatorId,
      'format_key': formatKey,
    },
    teamName: teamName,
    durationSeconds: durationSeconds,
  );
}

class _FakeViralFeedRepository implements ViralFeedRepository {
  _FakeViralFeedRepository(this._deck, {ViralFeedDeckRefresh? refresh})
    : _refresh =
          refresh ??
          const ViralFeedDeckRefresh(
            replaceIndices: <int>[],
            newItems: <ViralClip>[],
          );

  final ViralFeedDeck _deck;
  final ViralFeedDeckRefresh _refresh;

  @override
  Future<ViralFeedDeck> fetchDeck({
    ViralFeedSource source = ViralFeedSource.forYou,
    int limit = 10,
    bool refresh = true,
  }) async {
    return _deck;
  }

  @override
  Future<ViralFeedDeckRefresh> refreshForYou({
    required int cursor,
    int limit = 10,
  }) async {
    return _refresh;
  }
}

class _CountingViralFeedRepository extends _FakeViralFeedRepository {
  _CountingViralFeedRepository(super.deck, {super.refresh});

  int fetchCount = 0;
  int refreshCount = 0;

  @override
  Future<ViralFeedDeck> fetchDeck({
    ViralFeedSource source = ViralFeedSource.forYou,
    int limit = 10,
    bool refresh = true,
  }) async {
    fetchCount += 1;
    return super.fetchDeck(source: source, limit: limit, refresh: refresh);
  }

  @override
  Future<ViralFeedDeckRefresh> refreshForYou({
    required int cursor,
    int limit = 10,
  }) async {
    refreshCount += 1;
    return super.refreshForYou(cursor: cursor, limit: limit);
  }
}

class _PendingRefreshViralFeedRepository implements ViralFeedRepository {
  _PendingRefreshViralFeedRepository(
    this._deck, {
    required ViralFeedDeckRefresh refresh,
  }) : _refresh = refresh;

  final ViralFeedDeck _deck;
  final ViralFeedDeckRefresh _refresh;
  final List<Completer<ViralFeedDeckRefresh>> _pendingRefreshes =
      <Completer<ViralFeedDeckRefresh>>[];

  int fetchCount = 0;
  int refreshCount = 0;

  @override
  Future<ViralFeedDeck> fetchDeck({
    ViralFeedSource source = ViralFeedSource.forYou,
    int limit = 10,
    bool refresh = true,
  }) async {
    fetchCount += 1;
    return _deck;
  }

  @override
  Future<ViralFeedDeckRefresh> refreshForYou({
    required int cursor,
    int limit = 10,
  }) {
    refreshCount += 1;
    final Completer<ViralFeedDeckRefresh> completer =
        Completer<ViralFeedDeckRefresh>();
    _pendingRefreshes.add(completer);
    return completer.future;
  }

  void completeNextRefresh() {
    if (_pendingRefreshes.isEmpty) {
      return;
    }
    _pendingRefreshes.removeAt(0).complete(_refresh);
  }
}

class _FailingOnRefreshViralFeedRepository extends _FakeViralFeedRepository {
  _FailingOnRefreshViralFeedRepository(super.deck);

  @override
  Future<ViralFeedDeckRefresh> refreshForYou({
    required int cursor,
    int limit = 10,
  }) async {
    throw const GteApiException(
      type: GteApiErrorType.validation,
      message: 'Contract mismatch during refresh.',
    );
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

class _ControllableActionDispatcher
    implements feed_actions.ClipActionDispatcher {
  _ControllableActionDispatcher({Set<String> blockedActions = const <String>{}})
    : _blockedActions = Set<String>.from(blockedActions);

  final Set<String> _blockedActions;
  final List<feed_actions.ActionInvocation> invocations =
      <feed_actions.ActionInvocation>[];
  final Map<String, List<Completer<void>>> _pendingByAction =
      <String, List<Completer<void>>>{};

  @override
  Future<void> dispatch(feed_actions.ActionInvocation invocation) {
    invocations.add(invocation);
    if (!_blockedActions.contains(invocation.action)) {
      return Future<void>.value();
    }
    final Completer<void> completer = Completer<void>();
    _pendingByAction
        .putIfAbsent(invocation.action, () => <Completer<void>>[])
        .add(completer);
    return completer.future;
  }

  void completeNext(String action) {
    final List<Completer<void>>? pending = _pendingByAction[action];
    if (pending == null || pending.isEmpty) {
      return;
    }
    pending.removeAt(0).complete();
    if (pending.isEmpty) {
      _pendingByAction.remove(action);
    }
  }

  @override
  void dispose() {}
}
