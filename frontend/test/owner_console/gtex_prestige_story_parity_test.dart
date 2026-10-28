import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart' show GteApiErrorType, GteApiException;
import 'package:gte_frontend/features/owner_console/data/owner_console_api.dart';
import 'package:gte_frontend/features/owner_console/widgets/club_legacy_showroom.dart';

class _FakeAuthedApi implements GteAuthedApi {
  _FakeAuthedApi({
    this.legacyShowroomThrows = false,
    this.canonicalCatalog,
    this.ownedAssets,
    this.squadPayload,
    this.storyPayload,
    this.postHandler,
  });

  final bool legacyShowroomThrows;
  final List<Map<String, dynamic>>? canonicalCatalog;
  final List<Map<String, dynamic>>? ownedAssets;
  final Map<String, dynamic>? squadPayload;
  final Map<String, dynamic>? storyPayload;
  final Future<Object?> Function(String path, Object? body)? postHandler;

  final List<String> requestedPaths = <String>[];
  final List<Map<String, dynamic>> recordedPosts = <Map<String, dynamic>>[];

  @override
  Future<Map<String, dynamic>> getMap(
    String path, {
    Map<String, Object?> query = const <String, Object?>{},
    bool auth = true,
    bool opportunisticAuth = false,
  }) async {
    requestedPaths.add(path);

    if (path.startsWith('/owner/control-center')) {
      return <String, dynamic>{
        'clubs': <Map<String, dynamic>>[
          <String, dynamic>{
            'club_id': 'club-test-1',
            'club_name': 'Lagos City FC',
            'is_active': true,
            'stage': 'active',
          },
        ],
      };
    }

    if (path.contains('/owner/legacy/') && path.endsWith('/showroom')) {
      if (legacyShowroomThrows) {
        throw StateError('Legacy showroom disabled');
      }
      return <String, dynamic>{
        'exhibits': <Map<String, dynamic>>[
          <String, dynamic>{
            'id': 'legacy-watch-1',
            'name': 'Legacy Tourbillon',
            'category': 'watch',
            'price': '450.00',
            'owned': true,
          },
        ],
      };
    }

    if (path.contains('/owner/clubs/') && path.endsWith('/showroom')) {
      return <String, dynamic>{
        'catalog': canonicalCatalog ??
            <Map<String, dynamic>>[
              <String, dynamic>{
                'catalog_key': 'falcon_7x_private_jet',
                'name': 'Dassault Falcon 7X',
                'category': 'jet',
                'price_gtex': '4800.00',
                'can_gift_to_player': false,
              },
              <String, dynamic>{
                'catalog_key': 'chronos_tourbillon_watch',
                'name': 'Chronos Tourbillon',
                'category': 'watch',
                'price_gtex': '250.00',
                'can_gift_to_player': true,
              },
            ],
        'owned_assets': ownedAssets ??
            <Map<String, dynamic>>[
              <String, dynamic>{
                'catalog_key': 'falcon_7x_private_jet',
                'id': 'owned-asset-1',
                'custom_name': 'Skyline One',
              },
            ],
      };
    }

    if (path.contains('/owner/clubs/') && path.endsWith('/story')) {
      return storyPayload ??
          <String, dynamic>{
            'club': <String, dynamic>{
              'club_id': 'club-test-1',
              'club_name': 'Lagos City FC',
              'world_day': 14,
            },
            'relationships': <String, dynamic>{
              'manager': <String, dynamic>{'name': 'Coach Ade'},
              'players': <Map<String, dynamic>>[
                <String, dynamic>{
                  'id': 'regen-1',
                  'name': 'Chidi Nnamdi',
                  'position': 'FWD',
                  'rating': 74,
                  'morale': 80,
                  'is_regen': true,
                },
              ],
            },
            'club_news': <Map<String, dynamic>>[
              <String, dynamic>{
                'id': 'news-1',
                'headline': 'Lagos City FC Commissions Falcon 7X',
              },
            ],
          };
    }

    if (path.contains('/owner/clubs/')) {
      return squadPayload ??
          <String, dynamic>{
            'club_id': 'club-test-1',
            'club_name': 'Lagos City FC',
            'squad': <Map<String, dynamic>>[
              <String, dynamic>{
                'id': 'regen-1',
                'name': 'Chidi Nnamdi',
                'position': 'FWD',
                'rating': 74,
                'morale': 80,
                'is_regen': true,
              },
              <String, dynamic>{
                'id': 'senior-2',
                'name': 'Ahmed Musa',
                'position': 'MID',
                'rating': 82,
                'morale': 70,
                'is_regen': false,
              },
            ],
          };
    }

    return <String, dynamic>{};
  }

  @override
  Future<Object?> post(
    String path, {
    Map<String, Object?> query = const <String, Object?>{},
    Object? body,
    bool auth = true,
  }) async {
    recordedPosts.add(<String, dynamic>{'path': path, 'body': body});
    if (postHandler != null) {
      return postHandler!(path, body);
    }
    return <String, dynamic>{'status': 'ok'};
  }

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  group('Owner Showroom & Prestige Story Parity (B5 Scoped)', () {
    test('H9 & H3 broadcast label classification identifies jets, facilities and private assets', () {
      const ShowroomExhibit jet = ShowroomExhibit(
        id: 'falcon_7x_private_jet',
        name: 'Falcon 7X',
        category: 'jet',
        ownershipLabel: 'Available',
        fallbackLabel: 'Falcon 7X',
        sku: 'falcon_7x_private_jet',
        price: '4800',
      );
      const ShowroomExhibit facility = ShowroomExhibit(
        id: 'facility:medical',
        name: 'Medical Centre L3',
        category: 'facility',
        ownershipLabel: 'Available',
        fallbackLabel: 'Medical Centre',
      );
      const ShowroomExhibit watch = ShowroomExhibit(
        id: 'chronos_tourbillon_watch',
        name: 'Chronos Tourbillon',
        category: 'watch',
        ownershipLabel: 'Available',
        fallbackLabel: 'Watch',
      );

      expect(
        ClubLegacyShowroom.visibilityBadgeLabel(jet),
        'Public Broadcast · Fleet Aviation',
      );
      expect(
        ClubLegacyShowroom.visibilityBadgeLabel(facility),
        'Club Facility · Infrastructure Broadcast',
      );
      expect(
        ClubLegacyShowroom.visibilityBadgeLabel(watch),
        'Private Collection · No Global Broadcast',
      );

      expect(
        ClubLegacyShowroom.publicBroadcastNoticeFor(jet),
        contains('Private jet purchases broadcast globally'),
      );
      expect(
        ClubLegacyShowroom.publicBroadcastNoticeFor(facility),
        contains('Facility upgrades debit the club ledger and publish a global infrastructure broadcast'),
      );
      expect(
        ClubLegacyShowroom.publicBroadcastNoticeFor(watch),
        isNull,
      );
    });

    test('fetchShowroom falls back to canonical /owner/clubs/{id}/showroom when legacy showroom fails', () async {
      final _FakeAuthedApi fakeApi = _FakeAuthedApi(legacyShowroomThrows: true);
      final OwnerConsoleApi api = OwnerConsoleApi(client: fakeApi, activeClubId: 'club-test-1');

      final List<ShowroomExhibit> exhibits = await api.fetchShowroom();

      expect(exhibits, hasLength(2));
      final ShowroomExhibit jet = exhibits.firstWhere((ShowroomExhibit e) => e.id == 'falcon_7x_private_jet');
      expect(jet.name, 'Dassault Falcon 7X');
      expect(jet.category, 'jet');
      expect(jet.price, '4800.00');
      expect(jet.owned, isTrue);
      expect(jet.ownershipLabel, 'Owned Asset');

      final ShowroomExhibit watch = exhibits.firstWhere((ShowroomExhibit e) => e.id == 'chronos_tourbillon_watch');
      expect(watch.name, 'Chronos Tourbillon');
      expect(watch.owned, isFalse);
      expect(watch.ownershipLabel, 'Available');
    });

    test('fetchGiftRecipients strictly filters only academy regens', () async {
      final _FakeAuthedApi fakeApi = _FakeAuthedApi();
      final OwnerConsoleApi api = OwnerConsoleApi(client: fakeApi, activeClubId: 'club-test-1');

      final List<OwnerGiftRecipient> recipients = await api.fetchGiftRecipients();

      expect(recipients, hasLength(1));
      expect(recipients.first.id, 'regen-1');
      expect(recipients.first.name, 'Chidi Nnamdi');
      expect(recipients.first.isRegen, isTrue);
    });

    test('giftOwnedAssetToPlayer falls back to canonical /owner/clubs/{id}/showroom/gift when desk fails', () async {
      final _FakeAuthedApi fakeApi = _FakeAuthedApi(
        postHandler: (String path, Object? body) async {
          if (path.contains('/owner/legacy/')) {
            throw const GteApiException(
              type: GteApiErrorType.notFound,
              message: 'Legacy desk not supported',
              statusCode: 404,
            );
          }
          return <String, dynamic>{
            'status': 'confirmed',
            'morale_delta': 15,
          };
        },
      );
      final OwnerConsoleApi api = OwnerConsoleApi(client: fakeApi, activeClubId: 'club-test-1');

      await api.giftOwnedAssetToPlayer(assetId: 'asset-45', playerId: 'regen-1');
      // Simulate retry after a lost response: the same gift intent reuses its
      // idempotency key, so the server can return the original gift receipt.
      await api.giftOwnedAssetToPlayer(assetId: 'asset-45', playerId: 'regen-1');

      final List<Map<String, dynamic>> canonicalGiftPosts = fakeApi.recordedPosts
          .where((Map<String, dynamic> p) =>
              p['path'] == '/owner/clubs/club-test-1/showroom/gift')
          .toList(growable: false);
      expect(canonicalGiftPosts, hasLength(2));
      expect(
        canonicalGiftPosts.map(
          (Map<String, dynamic> p) =>
              (p['body'] as Map<String, Object?>)['idempotency_key'],
        ).toSet(),
        <String>{'owner-gift-club-test-1-asset-45-regen-1'},
      );
      expect(
        canonicalGiftPosts.every(
          (Map<String, dynamic> p) =>
              (p['body'] as Map<String, Object?>)['player_id'] == 'regen-1',
        ),
        isTrue,
      );
    });

    test('gift acceptance failure never falls back to a second canonical gift', () async {
      final _FakeAuthedApi fakeApi = _FakeAuthedApi(
        postHandler: (String path, Object? body) async {
          final Map<String, dynamic> payload = Map<String, dynamic>.from(body as Map);
          if (path == '/owner/legacy/club-test-1/desk' &&
              payload['action'] == 'gift') {
            return <String, dynamic>{'id': 'gift-created-1'};
          }
          if (path == '/owner/legacy/club-test-1/desk' &&
              payload['action'] == 'accept_gift') {
            throw StateError('accept response timed out');
          }
          return <String, dynamic>{'status': 'unexpected'};
        },
      );
      final OwnerConsoleApi api = OwnerConsoleApi(
        client: fakeApi,
        activeClubId: 'club-test-1',
      );

      await expectLater(
        api.giftOwnedAssetToPlayer(assetId: 'asset-45', playerId: 'regen-1'),
        throwsA(isA<StateError>()),
      );

      expect(
        fakeApi.recordedPosts.any(
          (Map<String, dynamic> post) =>
              post['path'] == '/owner/clubs/club-test-1/showroom/gift',
        ),
        isFalse,
        reason: 'An existing gift offer must not trigger a second gift fallback.',
      );
    });

    testWidgets('ClubLegacyShowroom renders luxury asset card and handles gift button for regens', (WidgetTester tester) async {
      final List<ShowroomExhibit> exhibits = <ShowroomExhibit>[
        const ShowroomExhibit(
          id: 'chronos_tourbillon_watch',
          name: 'Chronos Tourbillon Watch',
          category: 'watch',
          ownershipLabel: 'Owned Asset',
          fallbackLabel: 'Luxury Watch',
          sku: 'chronos_tourbillon_watch',
          price: '250.00',
          owned: true,
        ),
      ];

      await tester.pumpWidget(
        MaterialApp(
          theme: ThemeData.dark(),
          home: Scaffold(
            body: ClubLegacyShowroom(
              exhibits: exhibits,
              forceStatic: true,
              loadGiftRecipients: () async => <OwnerGiftRecipient>[
                const OwnerGiftRecipient(
                  id: 'regen-1',
                  name: 'Chidi Nnamdi',
                  position: 'FWD',
                  rating: 74,
                  morale: 75,
                  isRegen: true,
                ),
              ],
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Chronos Tourbillon Watch'), findsWidgets);
      expect(find.text('Private Collection · No Global Broadcast'), findsOneWidget);
    });
  });
}
