import 'package:gte_frontend/app/test_runtime_detector.dart';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';

import 'matchday_economy_models.dart';

class GtexMatchdayEconomyApi {
  GtexMatchdayEconomyApi({
    required this.client,
    GtexMatchdayEconomyFixtures? fixtures,
  }) : _fixtures = fixtures;

  final GteAuthedApi client;
  final GtexMatchdayEconomyFixtures? _fixtures;

  factory GtexMatchdayEconomyApi.standard({
    required String baseUrl,
    required String? accessToken,
    GteBackendMode mode = GteBackendMode.live,
  }) {
    final GteBackendMode resolvedMode = gteProductionBackendMode(mode);
    return GtexMatchdayEconomyApi(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: resolvedMode),
        transport: GteHttpTransport(),
        accessToken: accessToken,
        mode: resolvedMode,
      ),
    );
  }

  factory GtexMatchdayEconomyApi.fixture() {
    assertFixtureFactoryAllowed('GtexMatchdayEconomyApi.fixture');
    return GtexMatchdayEconomyApi(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.fixture,
        ),
        transport: GteHttpTransport(),
        accessToken: 'fixture-token',
        mode: GteBackendMode.fixture,
      ),
      fixtures: GtexMatchdayEconomyFixtures.seed(),
    );
  }

  Future<GtexMatchdayEconomyOverview> fetchOverview({bool admin = false}) {
    return client.withFallback<GtexMatchdayEconomyOverview>(() async {
      final Map<String, dynamic> payload = await client.getMap(
        admin
            ? '/api/admin/matchday-economy/overview'
            : '/api/matchday-economy/overview',
        auth: admin,
      );
      return GtexMatchdayEconomyOverview.fromJson(payload);
    }, _requireFixtures().overview);
  }

  Future<GtexMatchdayEconomyAction> resolveFederationSanction({
    required String sanctionId,
    String? note,
    Map<String, Object?> metadata = const <String, Object?>{},
  }) {
    final String encodedSanctionId = Uri.encodeComponent(sanctionId);
    return client.withFallback<GtexMatchdayEconomyAction>(
      () async {
        final Object? payload = await client.post(
          '/api/admin/matchday-economy/federation-sanctions/$encodedSanctionId/resolve',
          body: <String, Object?>{'note': note, 'metadata_json': metadata},
        );
        return GtexMatchdayEconomyAction.fromJson(payload);
      },
      () =>
          _requireFixtures().action('resolve_federation_sanction', sanctionId),
    );
  }

  Future<GtexMatchdayEconomyAction> settlePredictionRewards({
    required String fixtureId,
    String fancoinAmount = '25.0000',
    int maxWinners = 3,
    String? note,
    Map<String, Object?> metadata = const <String, Object?>{},
  }) {
    final String encodedFixtureId = Uri.encodeComponent(fixtureId);
    return client.withFallback<GtexMatchdayEconomyAction>(() async {
      final Object? payload = await client.post(
        '/api/admin/matchday-economy/predictions/$encodedFixtureId/settle-rewards',
        body: <String, Object?>{
          'fancoin_amount': fancoinAmount,
          'max_winners': maxWinners,
          'note': note,
          'metadata_json': metadata,
        },
      );
      return GtexMatchdayEconomyAction.fromJson(payload);
    }, () => _requireFixtures().action('settle_prediction_rewards', fixtureId));
  }

  Future<GtexMatchdayEconomyAction> checkInTicket({
    required String ticketId,
    int loyaltyPoints = 25,
    int xpAwarded = 10,
    String? reactionType,
    Map<String, Object?> metadata = const <String, Object?>{},
  }) {
    final String encodedTicketId = Uri.encodeComponent(ticketId);
    return client.withFallback<GtexMatchdayEconomyAction>(() async {
      final Object? payload = await client.post(
        '/api/admin/matchday-economy/tickets/$encodedTicketId/check-in',
        body: <String, Object?>{
          'loyalty_points': loyaltyPoints,
          'xp_awarded': xpAwarded,
          'reaction_type': reactionType,
          'metadata_json': metadata,
        },
      );
      return GtexMatchdayEconomyAction.fromJson(payload);
    }, () => _requireFixtures().action('check_in_ticket', ticketId));
  }

  Future<GtexMatchdayEconomyAction> settleCardListing({
    required String listingId,
    required String buyerUserId,
    int quantity = 1,
    int feeBps = 400,
    String? settlementReference,
    Map<String, Object?> metadata = const <String, Object?>{},
  }) {
    final String encodedListingId = Uri.encodeComponent(listingId);
    return client.withFallback<GtexMatchdayEconomyAction>(() async {
      final Object? payload = await client.post(
        '/api/admin/matchday-economy/card-listings/$encodedListingId/settle',
        body: <String, Object?>{
          'buyer_user_id': buyerUserId,
          'quantity': quantity,
          'fee_bps': feeBps,
          'settlement_reference': settlementReference,
          'metadata_json': metadata,
        },
      );
      return GtexMatchdayEconomyAction.fromJson(payload);
    }, () => _requireFixtures().action('settle_card_listing', listingId));
  }

  GtexMatchdayEconomyFixtures _requireFixtures() {
    final GtexMatchdayEconomyFixtures? fixtures = _fixtures;
    if (fixtures == null) {
      throw StateError(
        'Matchday economy fixtures are available only in fixture mode.',
      );
    }
    return fixtures;
  }
}

class GtexMatchdayEconomyFixtures {
  const GtexMatchdayEconomyFixtures(this._overview);

  final GtexMatchdayEconomyOverview _overview;

  static GtexMatchdayEconomyFixtures seed() {
    final DateTime now = DateTime.parse('2026-05-11T10:00:00Z');
    return GtexMatchdayEconomyFixtures(
      GtexMatchdayEconomyOverview(
        generatedAt: now,
        audience: 'fixture',
        totals: const <String, Object?>{
          'sections': 5,
          'metrics': 22,
          'alerts': 2,
        },
        sections: const <GtexMatchdayEconomySection>[
          GtexMatchdayEconomySection(
            key: 'federation_governance',
            title: 'Federation Governance',
            description:
                'National associations, rules, rankings, sanctions, and votes.',
            featureKey: 'federations',
            route: '/app/play',
            launchState: 'public',
            enabled: true,
            healthStatus: 'online',
            alerts: <String>[],
            metrics: <GtexMatchdayEconomyMetric>[
              GtexMatchdayEconomyMetric(
                key: 'federations',
                label: 'Federations',
                value: 4,
                displayValue: '4',
                unit: null,
                status: 'ok',
                route: '/app/play',
                metadata: <String, Object?>{},
              ),
              GtexMatchdayEconomyMetric(
                key: 'proposals',
                label: 'Open proposals',
                value: 2,
                displayValue: '2',
                unit: null,
                status: 'attention',
                route: null,
                metadata: <String, Object?>{},
              ),
            ],
          ),
          GtexMatchdayEconomySection(
            key: 'fan_economy',
            title: 'Fan Economy',
            description:
                'Predictions, fan wars, reward grants, and supporter points.',
            featureKey: 'fan_coin',
            route: '/app/community',
            launchState: 'public',
            enabled: true,
            healthStatus: 'online',
            alerts: <String>[],
            metrics: <GtexMatchdayEconomyMetric>[
              GtexMatchdayEconomyMetric(
                key: 'prediction_fixtures',
                label: 'Prediction fixtures',
                value: 8,
                displayValue: '8',
                unit: null,
                status: 'live',
                route: '/app/community',
                metadata: <String, Object?>{},
              ),
              GtexMatchdayEconomyMetric(
                key: 'fan_points',
                label: 'Fan war point events',
                value: 128,
                displayValue: '128',
                unit: null,
                status: 'ok',
                route: null,
                metadata: <String, Object?>{},
              ),
            ],
          ),
          GtexMatchdayEconomySection(
            key: 'viral_broadcast',
            title: 'Viral Clips And Broadcast',
            description:
                'Highlight variants, rights, views, and creator clip revenue.',
            featureKey: 'broadcast',
            route: '/broadcast/live',
            launchState: 'maintenance',
            enabled: false,
            healthStatus: 'maintenance',
            alerts: <String>['Rights worker paused for moderation review.'],
            metrics: <GtexMatchdayEconomyMetric>[
              GtexMatchdayEconomyMetric(
                key: 'clip_variants',
                label: 'Clip variants',
                value: 21,
                displayValue: '21',
                unit: null,
                status: 'ok',
                route: '/app/community',
                metadata: <String, Object?>{},
              ),
            ],
          ),
          GtexMatchdayEconomySection(
            key: 'ticketing_stadium',
            title: 'Ticketing And Stadium',
            description:
                'Stadium events, tickets, resale, crowd reactions, and revenue.',
            featureKey: 'ticketing',
            route: '/app/play',
            launchState: 'beta',
            enabled: true,
            healthStatus: 'gated',
            alerts: <String>[],
            metrics: <GtexMatchdayEconomyMetric>[
              GtexMatchdayEconomyMetric(
                key: 'stadium_events',
                label: 'Stadium events',
                value: 3,
                displayValue: '3',
                unit: null,
                status: 'live',
                route: '/app/play',
                metadata: <String, Object?>{},
              ),
              GtexMatchdayEconomyMetric(
                key: 'gross_revenue',
                label: 'Gross revenue',
                value: 54000,
                displayValue: '54,000',
                unit: 'credits',
                status: 'ok',
                route: null,
                metadata: <String, Object?>{},
              ),
            ],
          ),
          GtexMatchdayEconomySection(
            key: 'player_card_collectibles',
            title: 'Player Card Collectibles',
            description:
                'Card supply, holdings, listings, and settled sale depth.',
            featureKey: 'player_card_marketplace',
            route: '/player-cards',
            launchState: 'internal',
            enabled: true,
            healthStatus: 'gated',
            alerts: <String>['Pack opening stays behind launch control.'],
            metrics: <GtexMatchdayEconomyMetric>[
              GtexMatchdayEconomyMetric(
                key: 'cards',
                label: 'Card templates',
                value: 560,
                displayValue: '560',
                unit: null,
                status: 'ok',
                route: '/player-cards',
                metadata: <String, Object?>{},
              ),
              GtexMatchdayEconomyMetric(
                key: 'open_listings',
                label: 'Open listings',
                value: 42,
                displayValue: '42',
                unit: null,
                status: 'live',
                route: null,
                metadata: <String, Object?>{},
              ),
            ],
          ),
        ],
      ),
    );
  }

  Future<GtexMatchdayEconomyOverview> overview() async => _overview;

  Future<GtexMatchdayEconomyAction> action(String action, String id) async {
    return GtexMatchdayEconomyAction(
      action: action,
      status: 'ok',
      resourceId: id,
      message: 'Fixture $action completed.',
      metrics: const <String, double>{'records_updated': 1},
      metadata: const <String, Object?>{'source': 'fixture'},
    );
  }
}
