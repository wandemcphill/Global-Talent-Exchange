import 'package:gte_frontend/app/test_runtime_detector.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';

import 'global_search_models.dart';

class GtexGlobalSearchApi {
  GtexGlobalSearchApi({
    required this.client,
    GtexGlobalSearchFixtures? fixtures,
  }) : _fixtures = fixtures;

  final GteAuthedApi client;
  final GtexGlobalSearchFixtures? _fixtures;

  factory GtexGlobalSearchApi.standard({
    required String baseUrl,
    required String? accessToken,
    GteBackendMode mode = GteBackendMode.live,
  }) {
    final GteBackendMode resolvedMode = gteProductionBackendMode(mode);
    return GtexGlobalSearchApi(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: resolvedMode),
        transport: GteHttpTransport(),
        accessToken: accessToken,
        mode: resolvedMode,
      ),
    );
  }

  factory GtexGlobalSearchApi.fixture() {
    assertFixtureFactoryAllowed('GtexGlobalSearchApi.fixture');
    return GtexGlobalSearchApi(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.fixture,
        ),
        transport: GteHttpTransport(),
        accessToken: 'fixture-token',
        mode: GteBackendMode.fixture,
      ),
      fixtures: GtexGlobalSearchFixtures.seed(),
    );
  }

  Future<List<GtexGlobalSearchResult>> search(
    String query, {
    bool admin = false,
    int limit = 20,
  }) {
    final String path = admin ? '/api/admin/search' : '/api/search';
    return client.withFallback<List<GtexGlobalSearchResult>>(() async {
      final List<dynamic> payload = await client.getList(
        path,
        query: <String, Object?>{'q': query, 'limit': limit},
      );
      return payload
          .map(GtexGlobalSearchResult.fromJson)
          .toList(growable: false);
    }, () => _requireFixtures().search(query, admin: admin, limit: limit));
  }

  GtexGlobalSearchFixtures _requireFixtures() {
    final GtexGlobalSearchFixtures? fixtures = _fixtures;
    if (fixtures == null) {
      throw StateError(
        'Global search fixtures are available only in fixture mode.',
      );
    }
    return fixtures;
  }
}

class GtexGlobalSearchFixtures {
  GtexGlobalSearchFixtures(this._results);

  final List<GtexGlobalSearchResult> _results;

  static GtexGlobalSearchFixtures seed() {
    return GtexGlobalSearchFixtures(const <GtexGlobalSearchResult>[
      GtexGlobalSearchResult(
        type: 'player',
        id: 'player-jude',
        title: 'Jude Bellingham',
        subtitle: 'CM - Real Madrid - La Liga',
        imageUrl: null,
        route: '/app/market?player=player-jude',
        score: 20,
        permissionRequired: null,
        metadata: <String, Object?>{'is_real_player': true},
      ),
      GtexGlobalSearchResult(
        type: 'club',
        id: 'club-arsenal',
        title: 'Arsenal Lagos',
        subtitle: 'NG, Lagos',
        imageUrl: null,
        route: '/app/club?club=club-arsenal',
        score: 14,
        permissionRequired: null,
        metadata: <String, Object?>{'slug': 'arsenal-lagos'},
      ),
      GtexGlobalSearchResult(
        type: 'regen',
        id: 'prospect-kelechi',
        title: 'Kelechi Okoro',
        subtitle: 'ST - NG - contract_offered',
        imageUrl: 'newgen/ng/kelechi-okoro.png',
        route: '/world/regens',
        score: 13,
        permissionRequired: null,
        metadata: <String, Object?>{'club_id': 'club-arsenal'},
      ),
      GtexGlobalSearchResult(
        type: 'staff',
        id: 'staff-agent-lagos',
        title: 'Adaeze Nwosu',
        subtitle: 'agent - rating 88',
        imageUrl: null,
        route: '/app/club',
        score: 12,
        permissionRequired: null,
        metadata: <String, Object?>{'rarity': 'elite'},
      ),
      GtexGlobalSearchResult(
        type: 'sponsor_package',
        id: 'sponsor-front-shirt',
        title: 'Front Shirt Sponsor',
        subtitle: 'Primary shirt package for verified GTEX clubs.',
        imageUrl: null,
        route: '/app/club',
        score: 12,
        permissionRequired: null,
        metadata: <String, Object?>{'asset_type': 'jersey_front'},
      ),
      GtexGlobalSearchResult(
        type: 'transfer_listing',
        id: 'transfer-jude',
        title: 'Jude Bellingham Transfer',
        subtitle: 'Arsenal Lagos - open - 7500.00 credits',
        imageUrl: null,
        route: '/app/market?transferListing=transfer-jude',
        score: 13,
        permissionRequired: null,
        metadata: <String, Object?>{
          'player_id': 'player-jude',
          'listing_type': 'transfer',
        },
      ),
      GtexGlobalSearchResult(
        type: 'coin_trader',
        id: 'trader-lagos',
        title: 'Lagos Liquidity Desk',
        subtitle: 'gold trader - NG - rating 4.8',
        imageUrl: null,
        route: '/app/coin-traders?trader=trader-lagos',
        score: 12,
        permissionRequired: null,
        metadata: <String, Object?>{'tier': 'gold'},
      ),
      GtexGlobalSearchResult(
        type: 'federation',
        id: 'federation-africa',
        title: 'Africa GTEX Federation',
        subtitle: 'hybrid federation - ranking 88.0 - audience 120000',
        imageUrl: null,
        route: '/app/play?federation=federation-africa',
        score: 12,
        permissionRequired: null,
        metadata: <String, Object?>{'audience_size': 120000},
      ),
      GtexGlobalSearchResult(
        type: 'fan_prediction',
        id: 'prediction-lagos-final',
        title: 'Lagos final prediction card',
        subtitle: 'open - costs 2 token(s)',
        imageUrl: null,
        route: '/fan-predictions/matches/match-lagos-final',
        score: 11,
        permissionRequired: null,
        metadata: <String, Object?>{'match_id': 'match-lagos-final'},
      ),
      GtexGlobalSearchResult(
        type: 'fan_war',
        id: 'fan-war-lagos',
        title: 'Lagos Fan War',
        subtitle: 'club - Nigeria - 250 prestige',
        imageUrl: null,
        route: '/app/community?fanWar=lagos-fan-war',
        score: 11,
        permissionRequired: null,
        metadata: <String, Object?>{'slug': 'lagos-fan-war'},
      ),
      GtexGlobalSearchResult(
        type: 'broadcast_auction',
        id: 'broadcast-auction-lagos',
        title: 'Lagos Continental Cup broadcast auction',
        subtitle: 'auction_live - reserve 500.0000 credits',
        imageUrl: null,
        route: '/broadcast/live?competition=competition-lagos-final',
        score: 10,
        permissionRequired: null,
        metadata: <String, Object?>{
          'competition_id': 'competition-lagos-final',
        },
      ),
      GtexGlobalSearchResult(
        type: 'broadcast_right',
        id: 'broadcast-right-lagos',
        title: 'Lagos Continental Cup broadcast right',
        subtitle: 'exclusive - share 15.00%',
        imageUrl: null,
        route: '/broadcast/live?competition=competition-lagos-final',
        score: 10,
        permissionRequired: null,
        metadata: <String, Object?>{'owner_id': 'user-owner'},
      ),
      GtexGlobalSearchResult(
        type: 'viral_clip',
        id: 'clip-lagos-goal-vertical',
        title: 'clip-lagos-goal vertical',
        subtitle: 'trending - score 91.0 - 2000 views',
        imageUrl: null,
        route: '/news?clip=clip-lagos-goal',
        score: 10,
        permissionRequired: null,
        metadata: <String, Object?>{'format_type': 'vertical'},
      ),
      GtexGlobalSearchResult(
        type: 'sponsored_clip',
        id: 'sponsored-clip-lagos',
        title: 'Sponsored clip clip-lagos-goal',
        subtitle: 'budget 250.0000 credits - 900 impressions',
        imageUrl: null,
        route: '/news?clip=clip-lagos-goal',
        score: 10,
        permissionRequired: null,
        metadata: <String, Object?>{'advertiser_id': 'advertiser-lagos'},
      ),
      GtexGlobalSearchResult(
        type: 'ticket_event',
        id: 'event-lagos-final',
        title: 'Lagos Derby Final',
        subtitle: 'GTEX Arena - on_sale - 25000/50000 sold',
        imageUrl: null,
        route: '/creator-stadium/matches/match-lagos-final',
        score: 11,
        permissionRequired: null,
        metadata: <String, Object?>{'match_id': 'match-lagos-final'},
      ),
      GtexGlobalSearchResult(
        type: 'ticket_resale',
        id: 'ticket-resale-vip',
        title: 'Lagos Derby Final resale ticket',
        subtitle: 'Vip VIP-10 - 125.0000 credits',
        imageUrl: null,
        route: '/creator-stadium/matches/match-lagos-final',
        score: 10,
        permissionRequired: null,
        metadata: <String, Object?>{'seat_tier': 'vip'},
      ),
      GtexGlobalSearchResult(
        type: 'player_card_listing',
        id: 'card-listing-jude-gold',
        title: 'Jude Bellingham Gold',
        subtitle: 'Gold - founders - 3 listed at 88.0000 credits',
        imageUrl: null,
        route: '/player-cards/players/player-jude',
        score: 10,
        permissionRequired: null,
        metadata: <String, Object?>{'tier': 'gold'},
      ),
      GtexGlobalSearchResult(
        type: 'admin_user',
        id: 'user-owner',
        title: 'owner@example.com',
        subtitle: 'owner - user - KYC fully_verified',
        imageUrl: null,
        route: '/admin?user=user-owner',
        score: 12,
        permissionRequired: 'admin',
        metadata: <String, Object?>{'role': 'user'},
      ),
      GtexGlobalSearchResult(
        type: 'admin_coin_order',
        id: 'coin-order-1',
        title: 'User Buys - accepted',
        subtitle: 'buyer@example.com via Lagos Liquidity Desk - 50 coin',
        imageUrl: null,
        route: '/admin?coinOrder=coin-order-1',
        score: 10,
        permissionRequired: 'admin',
        metadata: <String, Object?>{'status': 'accepted'},
      ),
      GtexGlobalSearchResult(
        type: 'admin_command_route',
        id: 'academy_regens',
        title: 'Academy Regens',
        subtitle:
            'Academy generation, training plans, portrait assignment, contracts, and senior promotion.',
        imageUrl: null,
        route: '/world/regens',
        score: 10,
        permissionRequired: 'admin',
        metadata: <String, Object?>{'feature_key': 'academy_regens'},
      ),
    ]);
  }

  Future<List<GtexGlobalSearchResult>> search(
    String query, {
    required bool admin,
    required int limit,
  }) async {
    final String normalized = query.trim().toLowerCase();
    final Iterable<GtexGlobalSearchResult> scoped =
        admin
            ? _results
            : _results.where((GtexGlobalSearchResult item) => !item.adminOnly);
    return scoped
        .where(
          (GtexGlobalSearchResult item) => <String>[
            item.title,
            item.subtitle,
            item.type,
          ].join(' ').toLowerCase().contains(normalized),
        )
        .take(limit)
        .toList(growable: false);
  }
}
