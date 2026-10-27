import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/features/owner_console/data/owner_console_api.dart';
import 'package:gte_frontend/features/owner_console/widgets/gtex_owner_inbox_panel.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

class _RecordingTransport implements GteTransport {
  final List<GteTransportRequest> requests = <GteTransportRequest>[];

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    requests.add(request);
    final String path = request.uri.path;

    if (path.endsWith('/owner/control-center')) {
      return const GteTransportResponse(
        statusCode: 200,
        body: <String, Object?>{
          'user': <String, Object?>{
            'id': 'u-owner',
            'username': 'owner',
            'display_name': 'Club Owner',
            'role': 'user',
          },
          'clubs': <Map<String, Object?>>[
            <String, Object?>{
              'club_id': 'c1',
              'club_name': 'First Onboarding FC',
              'stage': 'squad',
              'status': 'activating',
              'value': 1000,
              'value_trend': 0,
            },
            <String, Object?>{
              'club_id': 'c2',
              'club_name': 'Active Lagos FC',
              'stage': 'active',
              'status': 'active',
              'value': 2500,
              'value_trend': 120,
            },
          ],
          'max_clubs': 2,
          'inbox': <Object?>[],
          'decisions': <Object?>[],
          'inbox_open_count': 1,
          'inbox_unread_count': 1,
          'health': <Object?>[],
          'board': <Object?>[],
          'fixtures': <String, Object?>{
            'upcoming': <Object?>[],
            'recent': <Object?>[],
          },
          'economy': <String, Object?>{
            'wallet': <String, Object?>{'withdrawable': 0},
            'club_cash_total': 5000,
            'pending_payouts': 0,
            'earnings_sources': <String, Object?>{},
          },
          'integrity': <String, Object?>{'score': 100},
        },
      );
    }

    if (path.contains('/owner/legacy/') && path.endsWith('/showroom')) {
      return GteTransportResponse(
        statusCode: 200,
        body: <String, Object?>{
          'exhibits': <Map<String, Object?>>[
            <String, Object?>{
              'id': 'exhibit-$path',
              'name': 'Showroom Trophy',
              'category': 'trophy',
              'ownership_label': 'Owned',
              'fallback_label': 'Trophy card',
              'owned': true,
            },
          ],
        },
      );
    }

    if (path.contains('/owner/legacy/') && path.endsWith('/desk')) {
      return const GteTransportResponse(
        statusCode: 200,
        body: <String, Object?>{
          'staff': <Object?>[],
          'policies': <Object?>[],
          'club_valuation': '2500',
          'equity': '100',
          'preseason': <Object?>[],
          'sponsors': <Object?>[],
          'offers': <Object?>[],
          'cases': <Object?>[],
        },
      );
    }

    if (path.endsWith('/owner/inbox')) {
      return const GteTransportResponse(
        statusCode: 200,
        body: <String, Object?>{
          'items': <Map<String, Object?>>[
            <String, Object?>{
              'id': 'item-1',
              'club_id': 'c2',
              'save_context_id': 'club:c2',
              'category': 'requests',
              'kind': 'facility_request',
              'title': 'Upgrade training pitch',
              'what': 'Manager requests level 2 training pitch.',
              'why': 'Improves regen growth rate.',
              'status': 'open',
              'is_decision': true,
              'is_read': false,
              'actions': <Map<String, Object?>>[
                <String, Object?>{
                  'key': 'approve',
                  'label': 'Approve (5,000)',
                  'style': 'primary',
                },
              ],
            },
          ],
          'counts': <String, Object?>{
            'all': 1,
            'requests': 1,
            'deadlines': 0,
            'staff_recommendations': 0,
            'player_issues': 0,
            'scouting_reports': 0,
            'negotiations': 0,
            'scheduling': 0,
            'archive': 0,
            'unread': 1,
            'open': 1,
          },
        },
      );
    }

    if (path.endsWith('/owner/inbox/item-1/read')) {
      return const GteTransportResponse(
        statusCode: 200,
        body: <String, Object?>{
          'id': 'item-1',
          'kind': 'facility_request',
          'title': 'Upgrade training pitch',
          'status': 'open',
          'is_decision': true,
          'is_read': true,
          'read_at': '2026-10-21T12:00:00Z',
        },
      );
    }

    if (path.endsWith('/owner/inbox/item-1/archive')) {
      return const GteTransportResponse(
        statusCode: 200,
        body: <String, Object?>{
          'id': 'item-1',
          'kind': 'facility_request',
          'title': 'Upgrade training pitch',
          'status': 'archived',
          'is_decision': true,
          'is_read': true,
          'archived_at': '2026-10-21T12:05:00Z',
        },
      );
    }

    if (path.endsWith('/owner/inbox/item-1/decide')) {
      return const GteTransportResponse(
        statusCode: 200,
        body: <String, Object?>{
          'id': 'item-1',
          'kind': 'facility_request',
          'title': 'Upgrade training pitch',
          'status': 'resolved',
          'resolution': 'approve',
          'outcome': 'Training upgraded to level 2.',
          'is_decision': true,
          'is_read': true,
        },
      );
    }

    return const GteTransportResponse(statusCode: 404, body: <String, Object?>{});
  }
}

class _FakeOwnerInboxServer implements GtexOwnerInboxDataSource {
  _FakeOwnerInboxServer({
    required List<OwnerInboxEntry> seedItems,
    this.throwConflictOnDecide = false,
    this.decideDelay = Duration.zero,
  }) : _items = List<OwnerInboxEntry>.from(seedItems);

  final List<OwnerInboxEntry> _items;
  final bool throwConflictOnDecide;
  final Duration decideDelay;

  int decideCallCount = 0;
  String? lastIdempotencyKey;

  GtexOwnerInboxCounts _computeCounts({String? clubId}) {
    int all = 0;
    int requests = 0;
    int deadlines = 0;
    int staff = 0;
    int archive = 0;
    int unread = 0;
    int open = 0;

    for (final OwnerInboxEntry item in _items) {
      if (clubId != null && item.clubId != clubId) {
        continue;
      }
      if (item.isArchived) {
        archive += 1;
        continue;
      }
      all += 1;
      if (item.category == 'requests') {
        requests += 1;
      } else if (item.category == 'deadlines') {
        deadlines += 1;
      } else if (item.category == 'staff_recommendations') {
        staff += 1;
      }
      if (!item.isRead) {
        unread += 1;
      }
      if (item.isOpen) {
        open += 1;
      }
    }

    return GtexOwnerInboxCounts(
      all: all,
      requests: requests,
      deadlines: deadlines,
      staffRecommendations: staff,
      archive: archive,
      unread: unread,
      open: open,
    );
  }

  @override
  Future<GtexOwnerInboxFeed> fetchInbox({
    String? status,
    String? category,
    String? clubId,
    String? saveContextId,
    bool unreadOnly = false,
  }) async {
    final String effectiveStatus = status ?? 'open';
    final String effectiveCategory = category ?? 'all';
    final List<OwnerInboxEntry> filtered = <OwnerInboxEntry>[];

    for (final OwnerInboxEntry item in _items) {
      if (clubId != null && item.clubId != clubId) {
        continue;
      }
      if (saveContextId != null && item.saveContextId != saveContextId) {
        continue;
      }
      if (effectiveStatus == 'archived' || effectiveCategory == 'archive') {
        if (!item.isArchived) {
          continue;
        }
      } else {
        if (item.isArchived && effectiveStatus != 'all') {
          continue;
        }
        if (effectiveStatus == 'open' && !item.isOpen) {
          continue;
        }
        if (effectiveStatus == 'resolved' && !item.isResolved) {
          continue;
        }
        if (effectiveCategory != 'all' && item.category != effectiveCategory) {
          continue;
        }
      }
      if (unreadOnly && item.isRead) {
        continue;
      }
      filtered.add(item);
    }

    return GtexOwnerInboxFeed(
      items: filtered,
      counts: _computeCounts(clubId: clubId),
    );
  }

  @override
  Future<OwnerInboxEntry> markInboxItemRead(String itemId) async {
    final int index = _items.indexWhere(
      (OwnerInboxEntry entry) => entry.id == itemId,
    );
    final OwnerInboxEntry updated = _items[index].copyWith(
      isRead: true,
      readAt: DateTime.utc(2026, 10, 21, 12),
    );
    _items[index] = updated;
    return updated;
  }

  @override
  Future<OwnerInboxEntry> archiveInboxItem(String itemId) async {
    final int index = _items.indexWhere(
      (OwnerInboxEntry entry) => entry.id == itemId,
    );
    final OwnerInboxEntry updated = _items[index].copyWith(
      status: 'archived',
      archivedAt: DateTime.utc(2026, 10, 21, 12, 10),
    );
    _items[index] = updated;
    return updated;
  }

  @override
  Future<OwnerInboxEntry> decideInboxItem(
    String itemId, {
    required String action,
    String? idempotencyKey,
  }) async {
    decideCallCount += 1;
    lastIdempotencyKey = idempotencyKey;
    if (decideDelay > Duration.zero) {
      await Future<void>.delayed(decideDelay);
    }
    final int index = _items.indexWhere(
      (OwnerInboxEntry entry) => entry.id == itemId,
    );
    if (throwConflictOnDecide) {
      _items[index] = _items[index].copyWith(
        status: 'resolved',
        resolution: action,
        isRead: true,
        outcome: 'Already approved in another session.',
      );
      throw const GteApiException(
        type: GteApiErrorType.unknown,
        statusCode: 409,
        message: 'inbox_item_already_resolved',
      );
    }
    final OwnerInboxEntry updated = _items[index].copyWith(
      status: 'resolved',
      resolution: action,
      isRead: true,
      outcome: 'Training facility upgraded to level 2.',
    );
    _items[index] = updated;
    return updated;
  }
}

Widget _wrapPanel(Widget child) {
  return MaterialApp(
    theme: ThemeData.dark(),
    home: Scaffold(
      backgroundColor: GtexColors.navy.bgBase,
      body: SingleChildScrollView(child: child),
    ),
  );
}

void main() {
  group('Phase E1 — OwnerConsoleApi clubId resolution & inbox endpoints (H2)', () {
    test(
      'resolves explicit clubId and active club instead of blindly picking clubs.first',
      () async {
        final _RecordingTransport transport = _RecordingTransport();
        final GteAuthedApi client = GteAuthedApi(
          config: const GteRepositoryConfig(baseUrl: 'https://gtex.test'),
          transport: transport,
          accessToken: 'test-token',
        );
        final OwnerConsoleApi api = OwnerConsoleApi(client: client);

        // 1. Explicit clubId ('c1') overrides active club ('c2')
        await api.fetchShowroom(clubId: 'c1');
        expect(
          transport.requests.last.uri.path,
          '/api/v2/owner/legacy/c1/showroom',
        );

        // 2. Explicit clubId ('c2') does not pick clubs.first ('c1')
        await api.fetchDesk(clubId: 'c2');
        expect(
          transport.requests.last.uri.path,
          '/api/v2/owner/legacy/c2/desk',
        );

        await api.performDesk('hire', const <String, Object?>{}, 'c2');
        expect(
          transport.requests.last.uri.path,
          '/api/v2/owner/legacy/c2/desk',
        );

        // 3. Omitting clubId resolves the active club ('c2', stage == 'active')
        // rather than blindly picking clubs.first ('c1', stage == 'squad')
        await api.fetchShowroom();
        expect(
          transport.requests.last.uri.path,
          '/api/v2/owner/legacy/c2/showroom',
        );
      },
    );

    test(
      'calls canonical /owner/inbox lifecycle endpoints with filters and idempotency key',
      () async {
        final _RecordingTransport transport = _RecordingTransport();
        final GteAuthedApi client = GteAuthedApi(
          config: const GteRepositoryConfig(baseUrl: 'https://gtex.test'),
          transport: transport,
          accessToken: 'test-token',
        );
        final OwnerConsoleApi api = OwnerConsoleApi(client: client);

        final GtexOwnerInboxFeed feed = await api.fetchInbox(
          status: 'open',
          category: 'requests',
          clubId: 'c2',
          saveContextId: 'club:c2',
          unreadOnly: true,
        );
        expect(feed.items, hasLength(1));
        expect(feed.counts.open, 1);
        expect(feed.counts.unread, 1);

        final GteTransportRequest fetchReq = transport.requests.last;
        expect(fetchReq.uri.path, '/api/v2/owner/inbox');
        expect(fetchReq.uri.queryParameters['status'], 'open');
        expect(fetchReq.uri.queryParameters['category'], 'requests');
        expect(fetchReq.uri.queryParameters['club_id'], 'c2');
        expect(fetchReq.uri.queryParameters['save_context_id'], 'club:c2');
        expect(fetchReq.uri.queryParameters['unread_only'], 'true');

        final OwnerInboxEntry readEntry = await api.markInboxItemRead('item-1');
        expect(readEntry.isRead, isTrue);
        expect(
          transport.requests.last.uri.path,
          '/api/v2/owner/inbox/item-1/read',
        );

        final OwnerInboxEntry decidedEntry = await api.decideInboxItem(
          'item-1',
          action: 'approve',
          idempotencyKey: 'idem-key-123',
        );
        expect(decidedEntry.isResolved, isTrue);
        expect(
          transport.requests.last.uri.path,
          '/api/v2/owner/inbox/item-1/decide',
        );
        expect(
          (transport.requests.last.body as Map<String, Object?>)['idempotency_key'],
          'idem-key-123',
        );

        final OwnerInboxEntry archivedEntry = await api.archiveInboxItem(
          'item-1',
        );
        expect(archivedEntry.isArchived, isTrue);
        expect(
          transport.requests.last.uri.path,
          '/api/v2/owner/inbox/item-1/archive',
        );
      },
    );
  });

  group('Phase E1 — GtexOwnerInboxPanel lifecycle & 409 recovery (H2)', () {
    testWidgets(
      'executes open -> read -> decide (updates server attention count) -> archive (hidden from default list)',
      (WidgetTester tester) async {
        final _FakeOwnerInboxServer server = _FakeOwnerInboxServer(
          seedItems: <OwnerInboxEntry>[
            const OwnerInboxEntry(
              id: 'item-1',
              clubId: 'c2',
              category: 'staff_recommendations',
              kind: 'facility_request',
              title: 'Manager demands training upgrade',
              what: 'Upgrade training facility to level 2 for 5,000 GTX.',
              why: 'Current level limits academy progression.',
              sender: 'Coach Tunde',
              status: 'open',
              isDecision: true,
              isRead: false,
              payload: <String, dynamic>{'cost': 5000, 'facility': 'training'},
              actions: <OwnerDecisionAction>[
                OwnerDecisionAction(
                  key: 'approve',
                  label: 'Approve spend (5,000)',
                  style: 'primary',
                ),
                OwnerDecisionAction(
                  key: 'reject',
                  label: 'Reject',
                  style: 'ghost',
                ),
              ],
            ),
            OwnerInboxEntry(
              id: 'item-archived-seed',
              clubId: 'c2',
              category: 'requests',
              kind: 'sponsor_opportunity',
              title: 'Archived sponsor proposal',
              what: 'Old shirt sponsor offer.',
              status: 'archived',
              isDecision: false,
              isRead: true,
              archivedAt: DateTime.utc(2026, 10, 20),
            ),
          ],
        );

        await tester.pumpWidget(
          _wrapPanel(GtexOwnerInboxPanel(api: server, clubId: 'c2')),
        );
        await tester.pumpAndSettle();

        // 1. Default 'open' list hides archived items and shows server counts
        expect(
          find.byKey(const Key('gtex-owner-inbox-counts-badge')),
          findsOneWidget,
        );
        expect(find.text('1 Open · 1 Unread'), findsOneWidget);
        expect(
          find.byKey(const Key('gtex-owner-inbox-item-item-1')),
          findsOneWidget,
        );
        expect(
          find.byKey(const Key('gtex-owner-inbox-item-item-archived-seed')),
          findsNothing,
        );
        expect(
          find.byKey(const Key('gtex-attention-unread-dot')),
          findsOneWidget,
        );

        // 2. Mark item read: open -> read
        await tester.tap(find.byKey(const Key('gtex-owner-inbox-read-item-1')));
        await tester.pumpAndSettle();

        expect(find.text('1 Open · 0 Unread'), findsOneWidget);
        expect(
          find.byKey(const Key('gtex-attention-unread-dot')),
          findsNothing,
        );

        // 3. Decide item via GtexConfirmSheet: read -> decide (updates server attention count)
        await tester.tap(
          find.byKey(const Key('gtex-owner-inbox-decide-item-1-approve')),
        );
        await tester.pumpAndSettle();

        expect(
          find.byKey(const Key('gtex-confirm-financial-box')),
          findsOneWidget,
        );
        expect(
          find.text('Ref: inbox-decide-item-1-approve'),
          findsOneWidget,
        );

        await tester.tap(find.byKey(const Key('gtex-confirm-submit-button')));
        await tester.pumpAndSettle();

        expect(server.decideCallCount, 1);
        expect(server.lastIdempotencyKey, 'inbox-decide-item-1-approve');
        expect(find.text('0 Open · 0 Unread'), findsOneWidget);
        expect(
          find.byKey(const Key('gtex-owner-inbox-outcome-item-1')),
          findsOneWidget,
        );
        expect(
          find.text('Training facility upgraded to level 2.'),
          findsOneWidget,
        );

        // 4. Archive item: decide -> archive (hidden from default open list)
        await tester.tap(
          find.byKey(const Key('gtex-owner-inbox-archive-item-1')),
        );
        await tester.pumpAndSettle();

        expect(
          find.byKey(const Key('gtex-owner-inbox-item-item-1')),
          findsNothing,
        );
        expect(
          find.byKey(const Key('gtex-owner-inbox-empty-state')),
          findsOneWidget,
        );

        // 5. Selecting the 'archived' filter reveals archived items
        await tester.tap(
          find.byKey(const Key('gtex-owner-inbox-status-archived')),
        );
        await tester.pumpAndSettle();

        expect(
          find.byKey(const Key('gtex-owner-inbox-item-item-1')),
          findsOneWidget,
        );
        expect(
          find.byKey(const Key('gtex-owner-inbox-item-item-archived-seed')),
          findsOneWidget,
        );
      },
    );

    testWidgets(
      'recovers gracefully from 409 already-decided response and prevents double-tap duplicate submissions',
      (WidgetTester tester) async {
        final _FakeOwnerInboxServer server = _FakeOwnerInboxServer(
          throwConflictOnDecide: true,
          decideDelay: const Duration(milliseconds: 60),
          seedItems: const <OwnerInboxEntry>[
            OwnerInboxEntry(
              id: 'item-conflict',
              clubId: 'c2',
              category: 'negotiations',
              kind: 'transfer_bid',
              title: 'Kano Pillars bid 12,000 for Ade Bello',
              what: 'Formal transfer offer of 12,000 GTX.',
              status: 'open',
              isDecision: true,
              isRead: false,
              payload: <String, dynamic>{'bid': 12000},
              actions: <OwnerDecisionAction>[
                OwnerDecisionAction(
                  key: 'accept',
                  label: 'Accept bid',
                  style: 'primary',
                ),
              ],
            ),
          ],
        );

        await tester.pumpWidget(
          _wrapPanel(GtexOwnerInboxPanel(api: server, clubId: 'c2')),
        );
        await tester.pumpAndSettle();

        expect(find.text('1 Open · 1 Unread'), findsOneWidget);

        await tester.tap(
          find.byKey(const Key('gtex-owner-inbox-decide-item-conflict-accept')),
        );
        await tester.pumpAndSettle();

        final Finder submitFinder = find.byKey(
          const Key('gtex-confirm-submit-button'),
        );
        // Rapid double-tap while request is in flight
        await tester.tap(submitFinder);
        await tester.pump();
        await tester.tap(submitFinder);
        await tester.pumpAndSettle();

        // Double-tap lock ensures only 1 backend request was sent
        expect(server.decideCallCount, 1);

        // 409 recovery refreshes item and displays resolved state + conflict notice
        expect(
          find.byKey(const Key('gtex-owner-inbox-conflict-banner')),
          findsOneWidget,
        );
        expect(find.text('0 Open · 0 Unread'), findsOneWidget);
        expect(
          find.byKey(const Key('gtex-owner-inbox-outcome-item-conflict')),
          findsOneWidget,
        );
        expect(
          find.text('Already approved in another session.'),
          findsOneWidget,
        );
      },
    );
  });
}
