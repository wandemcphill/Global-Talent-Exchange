import 'gte_api_repository.dart';
import 'gte_authed_api.dart';
import 'gte_http_transport.dart';
import '../models/community_models.dart';

class CommunityApi {
  CommunityApi({
    required this.client,
    required this.fixtures,
  });

  final GteAuthedApi client;
  final _CommunityFixtures fixtures;

  factory CommunityApi.standard({
    required String baseUrl,
    required String? accessToken,
    GteBackendMode mode = GteBackendMode.liveThenFixture,
  }) {
    return CommunityApi(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: mode),
        transport: GteHttpTransport(),
        accessToken: accessToken,
        mode: mode,
      ),
      fixtures: _CommunityFixtures.seed(),
    );
  }

  factory CommunityApi.fixture() {
    return CommunityApi(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.fixture,
        ),
        transport: GteHttpTransport(),
        accessToken: 'fixture-token',
        mode: GteBackendMode.fixture,
      ),
      fixtures: _CommunityFixtures.seed(),
    );
  }

  Future<CommunityDigest> fetchDigest() {
    return client.withFallback<CommunityDigest>(
      () async {
        final Map<String, dynamic> payload =
            await client.getMap('/community/digest');
        return CommunityDigest.fromJson(payload);
      },
      fixtures.digest,
    );
  }

  Future<List<CommunityWatchlistItem>> listWatchlist() {
    return client.withFallback<List<CommunityWatchlistItem>>(
      () async {
        final List<dynamic> payload =
            await client.getList('/community/watchlist');
        return payload
            .map(CommunityWatchlistItem.fromJson)
            .toList(growable: false);
      },
      fixtures.watchlist,
    );
  }

  Future<CommunityWatchlistItem> addWatchlist({
    required String competitionKey,
    required String competitionTitle,
    String competitionType = 'general',
    bool notifyOnStory = true,
    bool notifyOnLaunch = true,
  }) {
    return client.withFallback<CommunityWatchlistItem>(
      () async {
        final Object? payload = await client.request(
          'POST',
          '/community/watchlist',
          body: <String, Object?>{
            'competition_key': competitionKey,
            'competition_title': competitionTitle,
            'competition_type': competitionType,
            'notify_on_story': notifyOnStory,
            'notify_on_launch': notifyOnLaunch,
            'metadata_json': <String, Object?>{},
          },
        );
        return CommunityWatchlistItem.fromJson(payload);
      },
      () async => fixtures.addWatchlist(
        competitionKey: competitionKey,
        competitionTitle: competitionTitle,
      ),
    );
  }

  Future<void> removeWatchlist(String competitionKey) {
    return client.withFallback<void>(
      () async {
        await client.request(
          'DELETE',
          '/community/watchlist/$competitionKey',
        );
      },
      () async => fixtures.removeWatchlist(competitionKey),
    );
  }

  Future<List<LiveThread>> listLiveThreads({String? competitionKey}) {
    return client.withFallback<List<LiveThread>>(
      () async {
        final List<dynamic> payload = await client.getList(
          '/community/live-threads',
          query: <String, Object?>{
            if (competitionKey != null && competitionKey.isNotEmpty)
              'competition_key': competitionKey,
          },
        );
        return payload.map(LiveThread.fromJson).toList(growable: false);
      },
      fixtures.liveThreads,
    );
  }

  Future<LiveThread> createLiveThread({
    required String threadKey,
    required String title,
    String? competitionKey,
  }) {
    return client.withFallback<LiveThread>(
      () async {
        final Object? payload = await client.request(
          'POST',
          '/community/live-threads',
          body: <String, Object?>{
            'thread_key': threadKey,
            'title': title,
            if (competitionKey != null) 'competition_key': competitionKey,
            'pinned': false,
            'metadata_json': <String, Object?>{},
          },
        );
        return LiveThread.fromJson(payload);
      },
      () async => fixtures.createLiveThread(threadKey: threadKey, title: title),
    );
  }

  Future<LiveThread> fetchLiveThread(String threadId) {
    return client.withFallback<LiveThread>(
      () async {
        final Map<String, dynamic> payload =
            await client.getMap('/community/live-threads/$threadId');
        return LiveThread.fromJson(payload);
      },
      () async => fixtures.getLiveThread(threadId),
    );
  }

  Future<List<LiveThreadMessage>> listLiveThreadMessages(String threadId) {
    return client.withFallback<List<LiveThreadMessage>>(
      () async {
        final List<dynamic> payload =
            await client.getList('/community/live-threads/$threadId/messages');
        return payload
            .map(LiveThreadMessage.fromJson)
            .toList(growable: false);
      },
      () async => fixtures.liveThreadMessages(threadId),
    );
  }

  Future<LiveThreadMessage> postLiveThreadMessage({
    required String threadId,
    required String body,
  }) {
    return client.withFallback<LiveThreadMessage>(
      () async {
        final Object? payload = await client.request(
          'POST',
          '/community/live-threads/$threadId/messages',
          body: <String, Object?>{
            'body': body,
            'metadata_json': <String, Object?>{},
          },
        );
        return LiveThreadMessage.fromJson(payload);
      },
      () async => fixtures.postLiveThreadMessage(threadId, body),
    );
  }

  Future<List<PrivateMessageThread>> listPrivateThreads() {
    return client.withFallback<List<PrivateMessageThread>>(
      () async {
        final List<dynamic> payload =
            await client.getList('/community/private-messages/threads');
        return payload
            .map(PrivateMessageThread.fromJson)
            .toList(growable: false);
      },
      fixtures.privateThreads,
    );
  }

  Future<PrivateMessageThread> createPrivateThread({
    required List<String> participantUserIds,
    required String initialMessage,
    String subject = '',
  }) {
    return client.withFallback<PrivateMessageThread>(
      () async {
        final Object? payload = await client.request(
          'POST',
          '/community/private-messages/threads',
          body: <String, Object?>{
            'participant_user_ids': participantUserIds,
            'subject': subject,
            'initial_message': initialMessage,
            'metadata_json': <String, Object?>{},
          },
        );
        return PrivateMessageThread.fromJson(payload);
      },
      () async => fixtures.createPrivateThread(subject: subject),
    );
  }

  Future<PrivateMessageThread> fetchPrivateThread(String threadId) {
    return client.withFallback<PrivateMessageThread>(
      () async {
        final Map<String, dynamic> payload =
            await client.getMap('/community/private-messages/threads/$threadId');
        return PrivateMessageThread.fromJson(payload);
      },
      () async => fixtures.getPrivateThread(threadId),
    );
  }

  Future<List<PrivateMessage>> listPrivateMessages(String threadId) {
    return client.withFallback<List<PrivateMessage>>(
      () async {
        final List<dynamic> payload = await client.getList(
          '/community/private-messages/threads/$threadId/messages',
        );
        return payload.map(PrivateMessage.fromJson).toList(growable: false);
      },
      () async => fixtures.privateMessages(threadId),
    );
  }

  Future<PrivateMessage> postPrivateMessage({
    required String threadId,
    required String body,
  }) {
    return client.withFallback<PrivateMessage>(
      () async {
        final Object? payload = await client.request(
          'POST',
          '/community/private-messages/threads/$threadId/messages',
          body: <String, Object?>{
            'body': body,
            'metadata_json': <String, Object?>{},
          },
        );
        return PrivateMessage.fromJson(payload);
      },
      () async => fixtures.postPrivateMessage(threadId, body),
    );
  }
}

class _CommunityFixtures {
  _CommunityFixtures({
    required this._digest,
    required this._watchlist,
    required this._liveThreads,
    required this._threadMessages,
    required this._privateThreads,
    required this._privateMessages,
  });

  CommunityDigest _digest;
  final List<CommunityWatchlistItem> _watchlist;
  final List<LiveThread> _liveThreads;
  final Map<String, List<LiveThreadMessage>> _threadMessages;
  final List<PrivateMessageThread> _privateThreads;
  final Map<String, List<PrivateMessage>> _privateMessages;

  static _CommunityFixtures seed() {
    final List<CommunityWatchlistItem> watchlist = <CommunityWatchlistItem>[
      CommunityWatchlistItem(
        id: 'watch-1',
        competitionKey: 'creator-cup-22',
        competitionTitle: 'Creator Cup Night',
        competitionType: 'creator',
        notifyOnStory: true,
        notifyOnLaunch: true,
        metadata: const <String, Object?>{'lane': 'arena'},
        createdAt: DateTime.parse('2026-03-12T09:00:00Z'),
        updatedAt: DateTime.parse('2026-03-12T09:00:00Z'),
      ),
    ];
    final List<LiveThread> threads = <LiveThread>[
      LiveThread(
        id: 'thread-1',
        threadKey: 'matchday-derby',
        competitionKey: 'creator-cup-22',
        title: 'Matchday derby watch party',
        createdByUserId: 'user-1',
        status: 'open',
        pinned: true,
        lastMessageAt: DateTime.parse('2026-03-13T20:02:00Z'),
        metadata: const <String, Object?>{'tone': 'live'},
        createdAt: DateTime.parse('2026-03-12T18:00:00Z'),
        updatedAt: DateTime.parse('2026-03-13T20:02:00Z'),
      ),
    ];
    final Map<String, List<LiveThreadMessage>> messages =
        <String, List<LiveThreadMessage>>{
      'thread-1': <LiveThreadMessage>[
        LiveThreadMessage(
          id: 'msg-1',
          threadId: 'thread-1',
          authorUserId: 'user-2',
          body: 'Lineups just dropped. Expect a high press.',
          visibility: 'public',
          likeCount: 3,
          replyCount: 0,
          createdAt: DateTime.parse('2026-03-13T19:55:00Z'),
          metadata: const <String, Object?>{},
        ),
      ],
    };
    final List<PrivateMessageThread> privateThreads = <PrivateMessageThread>[
      PrivateMessageThread(
        id: 'pm-1',
        threadKey: 'trade-desk',
        createdByUserId: 'user-1',
        status: 'open',
        subject: 'Transfer room collab',
        lastMessageAt: DateTime.parse('2026-03-13T18:10:00Z'),
        metadata: const <String, Object?>{},
        createdAt: DateTime.parse('2026-03-12T10:00:00Z'),
        updatedAt: DateTime.parse('2026-03-13T18:10:00Z'),
        participants: const <PrivateMessageParticipant>[
          PrivateMessageParticipant(
            id: 'pm-part-1',
            threadId: 'pm-1',
            userId: 'user-1',
            isMuted: false,
            lastReadAt: null,
            joinedAt: DateTime.parse('2026-03-12T10:00:00Z'),
            metadata: <String, Object?>{},
          ),
          PrivateMessageParticipant(
            id: 'pm-part-2',
            threadId: 'pm-1',
            userId: 'user-3',
            isMuted: false,
            lastReadAt: DateTime.parse('2026-03-13T18:10:00Z'),
            joinedAt: DateTime.parse('2026-03-12T10:01:00Z'),
            metadata: <String, Object?>{},
          ),
        ],
      ),
    ];
    final Map<String, List<PrivateMessage>> privateMessages =
        <String, List<PrivateMessage>>{
      'pm-1': <PrivateMessage>[
        PrivateMessage(
          id: 'pm-msg-1',
          threadId: 'pm-1',
          senderUserId: 'user-3',
          body: 'We should align on the next listing window.',
          createdAt: DateTime.parse('2026-03-13T18:10:00Z'),
          metadata: const <String, Object?>{},
        ),
      ],
    };
    final CommunityDigest digest = CommunityDigest(
      watchlistCount: watchlist.length,
      liveThreadCount: threads.length,
      privateThreadCount: privateThreads.length,
      unreadHintCount: 2,
    );
    return _CommunityFixtures(
      _digest: digest,
      _watchlist: watchlist,
      _liveThreads: threads,
      _threadMessages: messages,
      _privateThreads: privateThreads,
      _privateMessages: privateMessages,
    );
  }

  Future<CommunityDigest> digest() async => _digest;

  Future<List<CommunityWatchlistItem>> watchlist() async =>
      List<CommunityWatchlistItem>.of(_watchlist, growable: false);

  Future<CommunityWatchlistItem> addWatchlist({
    required String competitionKey,
    required String competitionTitle,
  }) async {
    final CommunityWatchlistItem item = CommunityWatchlistItem(
      id: 'watch-${_watchlist.length + 1}',
      competitionKey: competitionKey,
      competitionTitle: competitionTitle,
      competitionType: 'general',
      notifyOnStory: true,
      notifyOnLaunch: true,
      metadata: const <String, Object?>{},
      createdAt: DateTime.now().toUtc(),
      updatedAt: DateTime.now().toUtc(),
    );
    _watchlist.insert(0, item);
    _digest = CommunityDigest(
      watchlistCount: _watchlist.length,
      liveThreadCount: _digest.liveThreadCount,
      privateThreadCount: _digest.privateThreadCount,
      unreadHintCount: _digest.unreadHintCount,
    );
    return item;
  }

  Future<void> removeWatchlist(String competitionKey) async {
    _watchlist.removeWhere(
        (CommunityWatchlistItem item) => item.competitionKey == competitionKey);
    _digest = CommunityDigest(
      watchlistCount: _watchlist.length,
      liveThreadCount: _digest.liveThreadCount,
      privateThreadCount: _digest.privateThreadCount,
      unreadHintCount: _digest.unreadHintCount,
    );
  }

  Future<List<LiveThread>> liveThreads() async =>
      List<LiveThread>.of(_liveThreads, growable: false);

  Future<LiveThread> createLiveThread({
    required String threadKey,
    required String title,
  }) async {
    final LiveThread thread = LiveThread(
      id: 'thread-${_liveThreads.length + 1}',
      threadKey: threadKey,
      competitionKey: null,
      title: title,
      createdByUserId: 'user-1',
      status: 'open',
      pinned: false,
      lastMessageAt: null,
      metadata: const <String, Object?>{},
      createdAt: DateTime.now().toUtc(),
      updatedAt: DateTime.now().toUtc(),
    );
    _liveThreads.insert(0, thread);
    return thread;
  }

  Future<LiveThread> getLiveThread(String threadId) async =>
      _liveThreads.firstWhere((LiveThread item) => item.id == threadId);

  Future<List<LiveThreadMessage>> liveThreadMessages(String threadId) async =>
      List<LiveThreadMessage>.of(_threadMessages[threadId] ?? const <LiveThreadMessage>[], growable: false);

  Future<LiveThreadMessage> postLiveThreadMessage(
      String threadId, String body) async {
    final LiveThreadMessage message = LiveThreadMessage(
      id: 'msg-${DateTime.now().millisecondsSinceEpoch}',
      threadId: threadId,
      authorUserId: 'user-1',
      body: body,
      visibility: 'public',
      likeCount: 0,
      replyCount: 0,
      createdAt: DateTime.now().toUtc(),
      metadata: const <String, Object?>{},
    );
    _threadMessages.putIfAbsent(threadId, () => <LiveThreadMessage>[]).add(message);
    return message;
  }

  Future<List<PrivateMessageThread>> privateThreads() async =>
      List<PrivateMessageThread>.of(_privateThreads, growable: false);

  Future<PrivateMessageThread> createPrivateThread({required String subject}) async {
    final PrivateMessageThread thread = PrivateMessageThread(
      id: 'pm-${_privateThreads.length + 1}',
      threadKey: 'pm-${_privateThreads.length + 1}',
      createdByUserId: 'user-1',
      status: 'open',
      subject: subject,
      lastMessageAt: DateTime.now().toUtc(),
      metadata: const <String, Object?>{},
      createdAt: DateTime.now().toUtc(),
      updatedAt: DateTime.now().toUtc(),
      participants: const <PrivateMessageParticipant>[],
    );
    _privateThreads.insert(0, thread);
    return thread;
  }

  Future<PrivateMessageThread> getPrivateThread(String threadId) async =>
      _privateThreads.firstWhere((PrivateMessageThread item) => item.id == threadId);

  Future<List<PrivateMessage>> privateMessages(String threadId) async =>
      List<PrivateMessage>.of(_privateMessages[threadId] ?? const <PrivateMessage>[], growable: false);

  Future<PrivateMessage> postPrivateMessage(String threadId, String body) async {
    final PrivateMessage message = PrivateMessage(
      id: 'pm-msg-${DateTime.now().millisecondsSinceEpoch}',
      threadId: threadId,
      senderUserId: 'user-1',
      body: body,
      createdAt: DateTime.now().toUtc(),
      metadata: const <String, Object?>{},
    );
    _privateMessages.putIfAbsent(threadId, () => <PrivateMessage>[]).add(message);
    return message;
  }
}
