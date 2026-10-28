import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/features/owner_console/models/gtex_owner_inbox_models.dart';
import 'package:gte_frontend/features/owner_console/presentation/owner_inbox_screen.dart';
import 'package:gte_frontend/features/owner_console/widgets/gtex_owner_inbox_panel.dart';

class _FakeInboxDataSource implements GtexOwnerInboxDataSource {
  _FakeInboxDataSource({
    this.feed,
    this.shouldThrow = false,
  });

  GtexOwnerInboxFeed? feed;
  bool shouldThrow;
  final List<String> calls = <String>[];

  @override
  Future<GtexOwnerInboxFeed> fetchInbox({
    String? status,
    String? category,
    String? clubId,
    String? saveContextId,
    bool unreadOnly = false,
  }) async {
    calls.add('fetchInbox:status=$status:category=$category:clubId=$clubId:unreadOnly=$unreadOnly');
    if (shouldThrow) {
      throw Exception('Failed to load owner decision inbox');
    }
    return feed ??
        GtexOwnerInboxFeed(
          items: <OwnerInboxEntry>[
            const OwnerInboxEntry(
              id: 'item-101',
              kind: 'facility_request',
              title: 'Upgrade Medical Bay',
              isDecision: true,
              category: 'staff_recommendations',
              priority: 'high',
              clubId: 'c1',
              status: 'open',
              what: 'Invest 8,000 GTX into medical wing to reduce injury time.',
              why: 'Two key regens suffered recurrence.',
              sender: 'Head Physio Danladi',
              actions: <OwnerDecisionAction>[
                OwnerDecisionAction(key: 'approve', label: 'Approve 8,000 GTX', style: 'primary'),
                OwnerDecisionAction(key: 'reject', label: 'Reject', style: 'ghost'),
              ],
            ),
            const OwnerInboxEntry(
              id: 'item-102',
              kind: 'scouting_report',
              title: 'WAFU B U-17 Scouting Report',
              isDecision: false,
              category: 'scouting_reports',
              priority: 'normal',
              clubId: 'c1',
              status: 'open',
              what: 'Found 3 potential regens in Ghana / Ivory Coast.',
              sender: 'Chief Scout Mensah',
            ),
          ],
          counts: GtexOwnerInboxCounts(
            all: 2,
            requests: 0,
            deadlines: 0,
            staffRecommendations: 1,
            playerIssues: 0,
            scoutingReports: 1,
            negotiations: 0,
            scheduling: 0,
            archive: 0,
            unread: 1,
            open: 2,
            raw: const <String, int>{'open': 2, 'unread': 1},
          ),
        );
  }

  @override
  Future<OwnerInboxEntry> markInboxItemRead(String itemId) async {
    calls.add('markRead:$itemId');
    return OwnerInboxEntry(
      id: itemId,
      kind: 'scouting_report',
      title: 'WAFU B U-17 Scouting Report',
      isDecision: false,
      isRead: true,
    );
  }

  @override
  Future<OwnerInboxEntry> archiveInboxItem(String itemId) async {
    calls.add('archive:$itemId');
    return OwnerInboxEntry(
      id: itemId,
      kind: 'scouting_report',
      title: 'WAFU B U-17 Scouting Report',
      isDecision: false,
      status: 'archived',
    );
  }

  @override
  Future<OwnerInboxEntry> decideInboxItem(
    String itemId, {
    required String action,
    String? idempotencyKey,
  }) async {
    calls.add('decide:$itemId:$action:$idempotencyKey');
    return OwnerInboxEntry(
      id: itemId,
      kind: 'facility_request',
      title: 'Upgrade Medical Bay',
      isDecision: true,
      status: 'resolved',
      outcome: 'Medical Bay upgrade queued for 8,000 GTX.',
    );
  }
}

void main() {
  testWidgets('shows unauthenticated card when user is not authenticated', (WidgetTester tester) async {
    bool loginRequested = false;
    final deps = GteNavigationDependencies(
      apiBaseUrl: 'http://localhost:8000',
      isAuthenticated: false,
    );

    await tester.pumpWidget(
      MaterialApp(
        home: GtexOwnerInboxScreen(
          dependencies: deps,
          onOpenLogin: () {
            loginRequested = true;
          },
        ),
      ),
    );

    expect(find.byKey(const Key('owner-inbox-unauth-card')), findsOneWidget);
    expect(find.text('Sign in required'), findsOneWidget);
    expect(find.text('Owner decision inbox requires an authenticated session.'), findsOneWidget);

    // Tap sign in
    await tester.tap(find.text('Sign in'));
    await tester.pumpAndSettle();
    expect(loginRequested, isTrue);
  });

  testWidgets('renders owner decision inbox header, active club badge, and items when authenticated', (WidgetTester tester) async {
    final fakeApi = _FakeInboxDataSource();
    final deps = GteNavigationDependencies(
      apiBaseUrl: 'http://localhost:8000',
      isAuthenticated: true,
      currentClubId: 'c1',
      currentClubName: 'Lagos City FC',
    );

    await tester.pumpWidget(
      MaterialApp(
        home: GtexOwnerInboxScreen(
          dependencies: deps,
          api: fakeApi,
        ),
      ),
    );
    await tester.pumpAndSettle();

    // Verify header and club badge
    expect(find.text('Owner Decision Inbox'), findsOneWidget);
    expect(find.byKey(const Key('owner-inbox-club-badge')), findsOneWidget);
    expect(find.text('Club: Lagos City FC'), findsOneWidget);
    expect(find.byKey(const Key('owner-inbox-back-button')), findsOneWidget);
    expect(find.byKey(const Key('owner-inbox-refresh-button')), findsOneWidget);

    // Verify inbox panel and real items
    expect(find.byType(GtexOwnerInboxPanel), findsOneWidget);
    expect(find.byKey(const Key('gtex-owner-inbox-item-item-101')), findsOneWidget);
    expect(find.byKey(const Key('gtex-owner-inbox-item-item-102')), findsOneWidget);
    expect(find.text('Upgrade Medical Bay'), findsOneWidget);
    expect(find.text('WAFU B U-17 Scouting Report'), findsOneWidget);
  });

  testWidgets('forwards deep link query parameters to inbox panel and api call', (WidgetTester tester) async {
    final fakeApi = _FakeInboxDataSource();
    final deps = GteNavigationDependencies(
      apiBaseUrl: 'http://localhost:8000',
      isAuthenticated: true,
      currentClubId: 'c1',
      currentClubName: 'Lagos City FC',
    );

    await tester.pumpWidget(
      MaterialApp(
        home: GtexOwnerInboxScreen(
          dependencies: deps,
          api: fakeApi,
          clubId: 'c2',
          initialStatus: 'resolved',
          initialCategory: 'deadlines',
          initialUnreadOnly: true,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      fakeApi.calls.any((call) =>
          call.contains('status=resolved') &&
          call.contains('category=deadlines') &&
          call.contains('clubId=c2') &&
          call.contains('unreadOnly=true')),
      isTrue,
    );
  });

  testWidgets('displays honest empty state when server returns no items', (WidgetTester tester) async {
    final emptyFeed = GtexOwnerInboxFeed(
      items: const <OwnerInboxEntry>[],
      counts: GtexOwnerInboxCounts(
        all: 0,
        requests: 0,
        deadlines: 0,
        staffRecommendations: 0,
        playerIssues: 0,
        scoutingReports: 0,
        negotiations: 0,
        scheduling: 0,
        archive: 0,
        unread: 0,
        open: 0,
        raw: const <String, int>{},
      ),
    );
    final fakeApi = _FakeInboxDataSource(feed: emptyFeed);
    final deps = GteNavigationDependencies(
      apiBaseUrl: 'http://localhost:8000',
      isAuthenticated: true,
      currentClubId: 'c1',
      currentClubName: 'Lagos City FC',
    );

    await tester.pumpWidget(
      MaterialApp(
        home: GtexOwnerInboxScreen(
          dependencies: deps,
          api: fakeApi,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('gtex-owner-inbox-empty-state')), findsOneWidget);
    expect(find.text('Inbox is clear for this filter'), findsOneWidget);
  });

  testWidgets('displays honest error state when server returns error and allows retry', (WidgetTester tester) async {
    final fakeApi = _FakeInboxDataSource(shouldThrow: true);
    final deps = GteNavigationDependencies(
      apiBaseUrl: 'http://localhost:8000',
      isAuthenticated: true,
      currentClubId: 'c1',
      currentClubName: 'Lagos City FC',
    );

    await tester.pumpWidget(
      MaterialApp(
        home: GtexOwnerInboxScreen(
          dependencies: deps,
          api: fakeApi,
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('gtex-owner-inbox-error-banner')), findsOneWidget);

    // Recover by fixing error and retrying
    fakeApi.shouldThrow = false;
    await tester.tap(find.text('Try again'));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('gtex-owner-inbox-error-banner')), findsNothing);
    expect(find.byKey(const Key('gtex-owner-inbox-item-item-101')), findsOneWidget);
  });
}
