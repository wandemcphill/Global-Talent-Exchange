import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/data/story_feed_api.dart';
import 'package:gte_frontend/features/engagement_redesign/engagement_widgets.dart';
import 'package:gte_frontend/features/home/data/gtex_story_feed_ticker_provider.dart';
import 'package:gte_frontend/features/news_agency/gtex_news_agency_screen_v2.dart';
import 'package:gte_frontend/features/world/football_world_pulse_provider.dart';
import 'package:gte_frontend/features/world/widgets/football_world_pulse_widgets.dart';
import 'package:gte_frontend/models/story_feed_models.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

class _FakeStoryFeedTransport implements GteTransport {
  _FakeStoryFeedTransport(this.payload);

  final List<Map<String, Object?>> payload;

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    return GteTransportResponse(statusCode: 200, body: payload);
  }
}

StoryFeedApi _buildFakeStoryFeedApi(List<Map<String, Object?>> payload) {
  final GteTransport transport = _FakeStoryFeedTransport(payload);
  return StoryFeedApi(
    client: GteAuthedApi(
      config: const GteRepositoryConfig(
        baseUrl: 'http://127.0.0.1:8000',
        mode: GteBackendMode.live,
      ),
      transport: transport,
      accessToken: 'test-token',
      mode: GteBackendMode.live,
    ),
    fixtures: null,
  );
}

StoryFeedItem _makeTickerItem({
  required String id,
  String storyType = 'private_jet_purchase',
  String title = 'Lagos Stars Commissions Sovereign 900X',
  String body = 'Executive jet added to club aviation fleet.',
  bool featured = true,
  DateTime? createdAt,
  String moderationStatus = 'published',
  Map<String, Object?> metadata = const <String, Object?>{},
}) {
  return StoryFeedItem(
    id: id,
    storyType: storyType,
    title: title,
    body: body,
    audience: 'all',
    subjectType: 'club',
    subjectId: 'club-lagos',
    countryCode: 'NG',
    featured: featured,
    createdAt: createdAt ?? DateTime.utc(2026, 10, 21, 12),
    metadata: metadata,
    moderationStatus: moderationStatus,
  );
}

void main() {
  group('Phase E2 — Global Ticker (Document I1, I3 & Decision O-09)', () {
    test(
      'deduplicates ticker items by id, caps at 50 items, and excludes reversed/retracted events',
      () {
        final List<StoryFeedItem> input = <StoryFeedItem>[
          _makeTickerItem(
            id: 'dup-1',
            title: 'Initial broadcast headline',
            createdAt: DateTime.utc(2026, 10, 21, 10),
          ),
          _makeTickerItem(
            id: 'dup-1',
            title: 'Updated broadcast headline',
            createdAt: DateTime.utc(2026, 10, 21, 11),
          ),
          _makeTickerItem(
            id: 'rev-meta',
            title: 'Reversed via metadata',
            metadata: const <String, Object?>{'status': 'reversed'},
          ),
          _makeTickerItem(
            id: 'rev-mod',
            title: 'Reversed via moderationStatus',
            moderationStatus: 'reversed',
          ),
          _makeTickerItem(
            id: 'retracted-1',
            title: 'Retracted broadcast',
            metadata: const <String, Object?>{'status': 'retracted'},
          ),
          for (int i = 1; i <= 65; i++)
            _makeTickerItem(
              id: 'item-$i',
              title: 'Broadcast #$i',
              featured: i <= 5,
              createdAt: DateTime.utc(2026, 10, 21, 12, i % 60),
            ),
        ];

        final List<StoryFeedItem> normalized = normalizeStoryFeedTickerItems(
          input,
        );

        expect(normalized.length, equals(kGtexMaxTickerItems));
        expect(kGtexMaxTickerItems, equals(50));

        final Set<String> uniqueIds =
            normalized.map((StoryFeedItem item) => item.id).toSet();
        expect(uniqueIds.length, equals(normalized.length));
        expect(uniqueIds.contains('rev-meta'), isFalse);
        expect(uniqueIds.contains('rev-mod'), isFalse);
        expect(uniqueIds.contains('retracted-1'), isFalse);

        final List<StoryFeedItem> dupOnly = normalizeStoryFeedTickerItems(
          input.take(2),
        );
        expect(dupOnly, hasLength(1));
        expect(dupOnly.single.id, equals('dup-1'));
        expect(dupOnly.single.title, contains('Updated broadcast headline'));
      },
    );

    test(
      'Decision O-09 surfaces verified_price_gtex and owner_display_name across eligible broadcast types with zero owner_user_id leakage',
      () {
        const String leakedUserId = 'usr_private_owner_998877';
        final List<StoryFeedItem> broadcasts = <StoryFeedItem>[
          _makeTickerItem(
            id: 'jet-1',
            storyType: 'private_jet_purchase',
            title: 'Lagos Stars Commissions Sovereign 900X by $leakedUserId',
            body: 'Purchased by $leakedUserId for continental fixtures.',
            metadata: const <String, Object?>{
              'event_type': 'private_jet_purchase',
              'verified_price_gtex': '4800.0000',
              'owner_display_name': 'Chief Ayo',
              'owner_user_id': leakedUserId,
              'club_cash': 999999,
            },
          ),
          _makeTickerItem(
            id: 'facility-1',
            storyType: 'facility_upgrade',
            title: 'Abuja Metro Completes Level 3 Stadium Upgrade',
            body: 'Modernisation of stadium campus.',
            metadata: const <String, Object?>{
              'event_type': 'facility_upgrade',
              'verified_price_gtex': 1250.5,
              'owner_display_name': 'Adaeze Nwosu',
              'owner_user_id': 'usr_secret_facility_42',
            },
          ),
          _makeTickerItem(
            id: 'gift-1',
            storyType: 'player_gift',
            title: 'Luxury Timepiece Gifted to Star Striker',
            body: 'Squad morale boost following derby win.',
            metadata: const <String, Object?>{
              'event_type': 'player_gift',
              'verified_price_gtex': '220',
              'owner_display_name': 'Tunde Bakare',
              'owner_user_id': 'usr_secret_gift_77',
            },
          ),
        ];

        final List<StoryFeedItem> result = normalizeStoryFeedTickerItems(
          broadcasts,
        );

        expect(result, hasLength(3));

        final StoryFeedItem jet = result.firstWhere(
          (StoryFeedItem item) => item.id == 'jet-1',
        );
        expect(jet.title, contains('Chief Ayo'));
        expect(jet.title, contains('4,800 GTX'));
        expect(jet.title, isNot(contains(leakedUserId)));
        expect(jet.body, isNot(contains(leakedUserId)));
        expect(jet.metadata.containsKey('owner_user_id'), isFalse);
        expect(jet.metadata.containsKey('club_cash'), isFalse);
        expect(jet.metadata['owner_display_name'], equals('Chief Ayo'));
        expect(jet.metadata['verified_price_gtex'], equals('4,800 GTX'));

        final StoryFeedItem facility = result.firstWhere(
          (StoryFeedItem item) => item.id == 'facility-1',
        );
        expect(facility.title, contains('Adaeze Nwosu'));
        expect(facility.title, contains('1,250.50 GTX'));
        expect(facility.metadata.containsKey('owner_user_id'), isFalse);

        final StoryFeedItem gift = result.firstWhere(
          (StoryFeedItem item) => item.id == 'gift-1',
        );
        expect(gift.title, contains('Tunde Bakare'));
        expect(gift.title, contains('220 GTX'));
        expect(gift.metadata.containsKey('owner_user_id'), isFalse);
      },
    );

    testWidgets(
      'storyFeedTickerProvider and FootballWorldPulseTicker render O-09 broadcasts and exclude reversed items',
      (WidgetTester tester) async {
        tester.view.physicalSize = const Size(1280, 800);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(() {
          tester.view.resetPhysicalSize();
          tester.view.resetDevicePixelRatio();
        });

        final StoryFeedApi fakeApi = _buildFakeStoryFeedApi(
          <Map<String, Object?>>[
            <String, Object?>{
              'id': 'b-1',
              'story_type': 'private_jet_purchase',
              'title': 'Lagos Stars Commissions Gulfstream G700',
              'body': 'Long-range aviation fleet addition.',
              'audience': 'all',
              'featured': true,
              'created_at': '2026-10-21T12:00:00Z',
              'metadata_json': <String, Object?>{
                'event_type': 'private_jet_purchase',
                'verified_price_gtex': '6200.0000',
                'owner_display_name': 'Chief Ayo',
                'owner_user_id': 'raw_owner_uid_secret_001',
              },
            },
            <String, Object?>{
              'id': 'b-1',
              'story_type': 'private_jet_purchase',
              'title': 'Lagos Stars Commissions Gulfstream G700',
              'body': 'Duplicate payload.',
              'audience': 'all',
              'featured': true,
              'created_at': '2026-10-21T11:55:00Z',
              'metadata_json': <String, Object?>{
                'event_type': 'private_jet_purchase',
                'verified_price_gtex': '6200.0000',
                'owner_display_name': 'Chief Ayo',
              },
            },
            <String, Object?>{
              'id': 'b-reversed',
              'story_type': 'player_gift',
              'title': 'Reversed Hypercar Gift',
              'body': 'Should never appear on ticker.',
              'audience': 'all',
              'featured': true,
              'created_at': '2026-10-21T12:05:00Z',
              'metadata_json': <String, Object?>{
                'status': 'reversed',
                'verified_price_gtex': '850.0000',
                'owner_display_name': 'Hidden Owner',
              },
            },
          ],
        );

        await tester.pumpWidget(
          ProviderScope(
            overrides: [
              storyFeedTickerApiProvider.overrideWithValue(fakeApi),
              footballWorldPulseProvider.overrideWith(
                (Ref ref) async => FootballWorldPulseData.empty,
              ),
            ],
            child: const MaterialApp(
              home: Scaffold(body: FootballWorldPulseTicker()),
            ),
          ),
        );
        await tester.pumpAndSettle();

        expect(
          find.byKey(const Key('football-world-pulse-ticker')),
          findsOneWidget,
        );
        expect(find.textContaining('Chief Ayo'), findsOneWidget);
        expect(find.textContaining('6,200 GTX'), findsWidgets);
        expect(find.textContaining('raw_owner_uid_secret_001'), findsNothing);
        expect(find.textContaining('Reversed Hypercar Gift'), findsNothing);
      },
    );
  });

  group('Phase E2 — Grounded Newsroom (Document I2–I3)', () {
    testWidgets(
      'deduplicates articles by id, renders grounding badge, Established Facts box, and Retracted status chip',
      (WidgetTester tester) async {
        tester.view.physicalSize = const Size(1440, 900);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(() {
          tester.view.resetPhysicalSize();
          tester.view.resetDevicePixelRatio();
        });

        final StoryFeedApi fakeApi = _buildFakeStoryFeedApi(
          <Map<String, Object?>>[
            <String, Object?>{
              'id': 'news-1',
              'story_type': 'fleet_aviation',
              'title': 'Lagos Stars Commissions Executive Aviation',
              'body':
                  'In a major operational investment, Chief Ayo has formally added the Sovereign 900X to Lagos Stars fleet.',
              'audience': 'all',
              'featured': true,
              'created_at': '2026-10-21T12:00:00Z',
              'moderation_status': 'published',
              'metadata_json': <String, Object?>{
                'category': 'fleet_aviation',
                'owner_display_name': 'Chief Ayo',
                'owner_user_id': 'secret_owner_id_555',
                'verified_price_gtex': '4800.0000',
                'established_facts': <String, Object?>{
                  'club_name': 'Lagos Stars',
                  'owner_display_name': 'Chief Ayo',
                  'owner_user_id': 'secret_owner_id_555',
                  'item_name': 'GTEX Sovereign 900X Private Jet',
                  'verified_price_gtex': '4800.0000',
                  'world_day': 14,
                },
              },
            },
            // Duplicate article with same id 'news-1' must be deduplicated
            <String, Object?>{
              'id': 'news-1',
              'story_type': 'fleet_aviation',
              'title': 'Lagos Stars Commissions Executive Aviation',
              'body': 'Duplicate copy of news-1.',
              'audience': 'all',
              'featured': false,
              'created_at': '2026-10-21T11:30:00Z',
              'moderation_status': 'published',
              'metadata_json': const <String, Object?>{},
            },
            // Retracted article
            <String, Object?>{
              'id': 'news-retracted',
              'story_type': 'squad_culture',
              'title': 'Retracted Luxury Watch Presentation',
              'body':
                  'This story was retracted after the underlying ledger event was reversed.',
              'audience': 'all',
              'featured': false,
              'created_at': '2026-10-21T11:00:00Z',
              'moderation_status': 'retracted',
              'metadata_json': <String, Object?>{
                'status': 'retracted',
                'established_facts': <String, Object?>{
                  'club_name': 'Abuja United',
                  'item_name': 'Chronos Tourbillon Piece Unique',
                },
              },
            },
          ],
        );

        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(body: GtexNewsAgencyScreenV2(api: fakeApi)),
          ),
        );
        await tester.pumpAndSettle();

        // Deduplicated by id: 2 left-panel tiles (news-1 and news-retracted), not 3
        expect(find.byType(GtexSectionListTile), findsNWidgets(2));

        // Grounding badge per Document I3
        expect(
          find.byKey(const Key('gtex-newsroom-grounding-label')),
          findsOneWidget,
        );
        expect(
          find.text('Generated from verified match and ledger events'),
          findsOneWidget,
        );

        // Established Facts box per Document I2/I3
        expect(
          find.byKey(const Key('gtex-newsroom-established-facts')),
          findsOneWidget,
        );
        expect(find.text('Established Facts'), findsOneWidget);
        expect(
          find.textContaining('GTEX Sovereign 900X Private Jet'),
          findsOneWidget,
        );
        expect(find.textContaining('4,800 GTX'), findsWidgets);

        // Zero raw owner_user_id leakage
        expect(find.textContaining('secret_owner_id_555'), findsNothing);

        // Retracted status chip is present and selecting the retracted article shows it in detail
        expect(
          find.byKey(const Key('gtex-newsroom-retracted-badge')),
          findsOneWidget,
        );
        expect(find.text('Retracted'), findsOneWidget);

        await tester.tap(find.text('Retracted Luxury Watch Presentation').first);
        await tester.pumpAndSettle();

        final Finder retractedBadge = find.byKey(
          const Key('gtex-newsroom-retracted-badge'),
        );
        expect(retractedBadge, findsOneWidget);
        final GtexStatusChip badgeWidget = tester.widget<GtexStatusChip>(
          retractedBadge,
        );
        expect(badgeWidget.label, equals('Retracted'));
        expect(badgeWidget.outlined, isTrue);
      },
    );
  });
}
