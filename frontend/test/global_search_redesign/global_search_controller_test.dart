import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/features/global_search_redesign/global_search_redesign.dart';

void main() {
  test('global search model parses Batch 33 result JSON', () {
    final GtexGlobalSearchResult result = GtexGlobalSearchResult.fromJson(
      <String, Object?>{
        'type': 'player',
        'id': 'player-1',
        'title': 'Jude Bellingham',
        'subtitle': 'CM - Real Madrid',
        'image_url': null,
        'route': '/app/market?player=player-1',
        'score': 20.5,
        'permission_required': null,
        'metadata': <String, Object?>{'is_real_player': true},
      },
    );

    expect(result.type, 'player');
    expect(result.title, 'Jude Bellingham');
    expect(result.adminOnly, isFalse);
    expect(result.metadata['is_real_player'], isTrue);
  });

  test('controller filters admin-only results for normal search', () async {
    final GtexGlobalSearchController userController =
        GtexGlobalSearchController(api: GtexGlobalSearchApi.fixture());

    await userController.search('owner');

    expect(userController.results, isEmpty);

    final GtexGlobalSearchController adminController =
        GtexGlobalSearchController(
          api: GtexGlobalSearchApi.fixture(),
          admin: true,
        );

    await adminController.search('owner');

    expect(adminController.results.single.type, 'admin_user');
  });

  test('canonical search routes preserve deep links and admin safety', () {
    expect(
      gtexCanonicalGlobalSearchRoute(
        '/broadcast?competition=final',
        isAdmin: false,
      ),
      '/broadcast/live?competition=final',
    );
    expect(
      gtexCanonicalGlobalSearchRoute('/admin/ops', isAdmin: true),
      '/admin/trust-ops',
    );
    expect(
      gtexCanonicalGlobalSearchRoute(
        '/admin/launch-control?feature=broadcast',
        isAdmin: true,
      ),
      '/admin/launch-control?feature=broadcast',
    );
    expect(
      gtexCanonicalGlobalSearchRoute('/admin/launch-control', isAdmin: false),
      '/app/home',
    );
    expect(
      gtexCanonicalGlobalSearchRoute(
        'https://example.test/broadcast?competition=final',
        isAdmin: false,
      ),
      '/broadcast/live?competition=final',
    );
    expect(
      gtexCanonicalGlobalSearchRoute(
        '/app/market?player=player-jude',
        isAdmin: false,
      ),
      '/app/market?player=player-jude',
    );
  });

  test('fixture covers Batch 28-33 product-loop result families', () async {
    final GtexGlobalSearchController userController =
        GtexGlobalSearchController(api: GtexGlobalSearchApi.fixture());

    await userController.search('Lagos');

    final Set<String> userTypes =
        userController.results
            .map((GtexGlobalSearchResult result) => result.type)
            .toSet();
    expect(userTypes, contains('coin_trader'));
    expect(userTypes, contains('fan_prediction'));
    expect(userTypes, contains('fan_war'));
    expect(userTypes, isNot(contains('broadcast_auction')));
    expect(userTypes, isNot(contains('broadcast_right')));
    expect(userTypes, contains('ticket_event'));
    expect(userTypes, contains('ticket_resale'));

    await userController.search('Kelechi');
    expect(userController.results.single.type, 'regen');

    await userController.search('Adaeze');
    expect(userController.results.single.type, 'staff');

    await userController.search('Front Shirt');
    expect(userController.results.single.type, 'sponsor_package');

    await userController.search('Africa');
    expect(userController.results.single.type, 'federation');

    await userController.search('vertical');
    expect(
      userController.results.map(
        (GtexGlobalSearchResult result) => result.type,
      ),
      contains('viral_clip'),
    );

    await userController.search('Sponsored');
    expect(userController.results.single.type, 'sponsored_clip');

    await userController.search('founders');
    expect(userController.results.single.type, 'player_card_listing');

    final GtexGlobalSearchController adminController =
        GtexGlobalSearchController(
          api: GtexGlobalSearchApi.fixture(),
          admin: true,
        );
    await adminController.search('accepted');

    expect(adminController.results.single.type, 'admin_coin_order');
    expect(adminController.results.single.adminOnly, isTrue);

    await adminController.search('Lagos');
    final Set<String> adminLagosTypes =
        adminController.results
            .map((GtexGlobalSearchResult result) => result.type)
            .toSet();
    expect(adminLagosTypes, contains('broadcast_auction'));
    expect(adminLagosTypes, contains('broadcast_right'));

    await adminController.search('Academy');
    expect(adminController.results.single.type, 'admin_command_route');
    expect(adminController.results.single.adminOnly, isTrue);
  });
}
