import '../../../data/gte_api_repository.dart';
import '../../../data/gte_authed_api.dart';
import '../../../data/gte_http_transport.dart';
import '../../../data/gte_models.dart';

typedef JsonMap = Map<String, Object?>;

final _FeatureFixtureTransport _fixtureFeatureTransport =
    _FeatureFixtureTransport.seed();

GteTransport createModeAwareTransport(GteBackendMode mode) {
  return mode == GteBackendMode.fixture
      ? _fixtureFeatureTransport
      : GteHttpTransport();
}

GteAuthedApi createFeatureApi({
  required String baseUrl,
  required GteBackendMode mode,
  required String? accessToken,
}) {
  return GteAuthedApi(
    config: GteRepositoryConfig(baseUrl: baseUrl, mode: mode),
    transport: createModeAwareTransport(mode),
    accessToken: accessToken,
    mode: mode,
  );
}

JsonMap jsonMap(
  Object? value, {
  String label = 'payload',
  JsonMap fallback = const <String, Object?>{},
}) {
  return GteJson.map(value, label: label, fallback: fallback);
}

JsonMap? jsonMapOrNull(Object? value) {
  if (value == null) {
    return null;
  }
  return GteJson.map(value);
}

List<Object?> jsonList(Object? value, {String label = 'payload'}) {
  return GteJson.list(value, label: label);
}

List<T> parseList<T>(
  Object? value,
  T Function(Object? value) parser, {
  String label = 'payload',
}) {
  return jsonList(value, label: label).map(parser).toList(growable: false);
}

List<JsonMap> jsonMapList(Object? value, {String label = 'payload'}) {
  return jsonList(
    value,
    label: label,
  ).map((Object? item) => jsonMap(item, label: label)).toList(growable: false);
}

String? stringOrNullValue(Object? value) {
  if (value == null) {
    return null;
  }
  final String parsed = value.toString().trim();
  return parsed.isEmpty ? null : parsed;
}

String stringValue(Object? value, {String fallback = ''}) {
  return stringOrNullValue(value) ?? fallback;
}

double numberValue(Object? value, {double fallback = 0}) {
  if (value == null) {
    return fallback;
  }
  if (value is num) {
    return value.toDouble();
  }
  return double.tryParse(value.toString()) ?? fallback;
}

int intValue(Object? value, {int fallback = 0}) {
  if (value == null) {
    return fallback;
  }
  if (value is int) {
    return value;
  }
  if (value is num) {
    return value.toInt();
  }
  return int.tryParse(value.toString()) ?? fallback;
}

bool boolValue(Object? value, {bool fallback = false}) {
  if (value == null) {
    return fallback;
  }
  if (value is bool) {
    return value;
  }
  final String normalized = value.toString().trim().toLowerCase();
  if (<String>{'1', 'true', 'yes', 'on'}.contains(normalized)) {
    return true;
  }
  if (<String>{'0', 'false', 'no', 'off'}.contains(normalized)) {
    return false;
  }
  return fallback;
}

DateTime? dateTimeValue(Object? value) {
  if (value == null) {
    return null;
  }
  if (value is DateTime) {
    return value.toUtc();
  }
  return DateTime.tryParse(value.toString())?.toUtc();
}

String? dateQueryValue(DateTime? value) {
  if (value == null) {
    return null;
  }
  return value.toUtc().toIso8601String().split('T').first;
}

List<String> stringListValue(Object? value) {
  return jsonList(value)
      .map(stringValue)
      .where((String item) => item.isNotEmpty)
      .toList(growable: false);
}

Map<String, Object?> compactQuery(Map<String, Object?> input) {
  final Map<String, Object?> query = <String, Object?>{};
  for (final MapEntry<String, Object?> entry in input.entries) {
    final Object? value = entry.value;
    if (value == null) {
      continue;
    }
    if (value is String && value.trim().isEmpty) {
      continue;
    }
    if (value is Iterable<Object?> && value.isEmpty) {
      continue;
    }
    query[entry.key] = value;
  }
  return query;
}

Map<String, dynamic> dynamicMap(JsonMap value) {
  return Map<String, dynamic>.from(value);
}

bool isNotFoundError(Object error) {
  return error is GteApiException && error.type == GteApiErrorType.notFound;
}

bool isUnauthorizedError(Object error) {
  return error is GteApiException && error.type == GteApiErrorType.unauthorized;
}

class _FeatureFixtureTransport implements GteTransport {
  _FeatureFixtureTransport.seed()
    : _giftCatalog = <JsonMap>[
        <String, Object?>{
          'id': 'gift-catalog-legacy-1',
          'key': 'legacy_spotlight',
          'display_name': 'Legacy Spotlight',
          'tier': 'legacy',
          'fancoin_price': 0,
          'description': 'Legacy admin-only gift economy record.',
          'active': false,
          'updated_at': '2026-04-01T08:00:00Z',
        },
      ],
      _revenueRules = <JsonMap>[
        <String, Object?>{
          'id': 'rev-rule-gtex-1',
          'rule_key': 'gtex_coin_primary',
          'scope': 'platform',
          'title': 'GTEX Coin primary economy',
          'description':
              'Live spend settles in GTEX Coin while gift controls remain legacy-only.',
          'platform_share_bps': 0,
          'creator_share_bps': 0,
          'recipient_share_bps': 0,
          'burn_bps': 0,
          'priority': 1,
          'active': true,
          'updated_at': '2026-04-01T08:00:00Z',
        },
      ],
      _comboRules = <JsonMap>[
        <String, Object?>{
          'id': 'combo-rule-legacy-1',
          'rule_key': 'legacy_combo',
          'title': 'Legacy combo disabled',
          'description':
              'Gift combo amplification is disabled in the live GTEX Coin runtime.',
          'min_combo_count': 2,
          'window_seconds': 120,
          'bonus_bps': 0,
          'priority': 1,
          'active': false,
          'updated_at': '2026-04-01T08:00:00Z',
        },
      ],
      _burnEvents = <JsonMap>[
        <String, Object?>{
          'id': 'burn-legacy-1',
          'source_type': 'legacy_gift_retirement',
          'amount': 0,
          'unit': 'coin',
          'reason': 'Gift economy retired from the live shell.',
          'metadata_json': <String, Object?>{'mode': 'fixture'},
          'created_at': '2026-04-01T08:00:00Z',
        },
      ],
      _cultures = <JsonMap>[
        <String, Object?>{
          'id': 'culture-ng-lagos',
          'culture_key': 'lagos_press',
          'display_name': 'Lagos High Press',
          'scope_type': 'club_region',
          'country_code': 'NG',
          'region_name': 'Lagos',
          'city_name': 'Lagos',
          'play_style_summary':
              'Fast vertical build-up, crowd pressure, and aggressive wide recoveries.',
          'supporter_traits_json': <String>['loud', 'relentless', 'mercurial'],
          'rivalry_themes_json': <String>['regional_supremacy'],
          'talent_archetypes_json': <String>['wingers', 'pressing_eights'],
          'climate_notes': 'Humid coastlines reward depth and rotation.',
          'active': true,
          'metadata_json': <String, Object?>{'focus': 'club_identity'},
        },
        <String, Object?>{
          'id': 'culture-br-rio',
          'culture_key': 'rio_front_foot',
          'display_name': 'Rio Front Foot',
          'scope_type': 'national',
          'country_code': 'BR',
          'region_name': 'Rio de Janeiro',
          'city_name': 'Rio',
          'play_style_summary':
              'Technical combinations, brave rest-defense, and elastic final-third rotations.',
          'supporter_traits_json': <String>['expressive', 'demanding'],
          'rivalry_themes_json': <String>['heritage', 'continental_ambition'],
          'talent_archetypes_json': <String>[
            'playmakers',
            'press-resistant_fullbacks',
          ],
          'climate_notes':
              'Fast pitches and warm conditions favor daring possession.',
          'active': true,
          'metadata_json': <String, Object?>{'focus': 'regen_universe'},
        },
      ],
      _clubContexts = <String, JsonMap>{},
      _competitionContexts = <String, JsonMap>{},
      _narratives = <JsonMap>[
        <String, Object?>{
          'id': 'narrative-ibadan-rise',
          'slug': 'ibadan-rise',
          'scope_type': 'club',
          'club_id': 'ibadan-lions',
          'arc_type': 'club_identity',
          'status': 'active',
          'visibility': 'public',
          'headline': 'Ibadan Lions are shaping a new badge-era identity',
          'summary':
              'The canonical football-world simulation is tracking a new club culture, academy pulse, and transfer posture around Ibadan.',
          'importance_score': 78,
          'simulation_horizon': 'seasonal',
          'tags_json': <String>['club_identity', 'academy'],
          'impact_vectors_json': <String>['reputation', 'regen_interest'],
          'metadata_json': <String, Object?>{'tone': 'ambitious'},
        },
        <String, Object?>{
          'id': 'narrative-transfer-window',
          'slug': 'transfer-window-heat',
          'scope_type': 'global',
          'arc_type': 'transfer_market',
          'status': 'active',
          'visibility': 'public',
          'headline': 'GTEX transfer windows are feeding live pricing tension',
          'summary':
              'Pricing, scouting, and club narratives are all sourced from the same active football-world runtime.',
          'importance_score': 81,
          'simulation_horizon': 'monthly',
          'tags_json': <String>['market', 'pricing'],
          'impact_vectors_json': <String>['orders', 'club_reputation'],
          'metadata_json': <String, Object?>{'tone': 'volatile'},
        },
      ],
      _federations = <JsonMap>[
        <String, Object?>{
          'id': 'federation-west-africa',
          'name': 'West Africa Federation',
          'ranking_score': 84.2,
          'reputation_score': 79.5,
          'audience_size': 820000,
          'treasury_balance': 4200,
          'is_public': true,
          'structure_json': <String, Object?>{
            'divisions': 3,
            'continental_slots': 4,
          },
          'rules_json': <String, Object?>{'region_label': 'West Africa'},
          'metadata_json': <String, Object?>{'region_label': 'West Africa'},
          'competitions_json': <Object?>[
            <String, Object?>{
              'competition_id': 'competition-west-africa-cup',
              'name': 'West Africa Cup',
            },
          ],
          'members_json': <Object?>[],
        },
        <String, Object?>{
          'id': 'federation-global-elite',
          'name': 'Global Elite Federation',
          'ranking_score': 92.1,
          'reputation_score': 90.4,
          'audience_size': 1800000,
          'treasury_balance': 9400,
          'is_public': true,
          'structure_json': <String, Object?>{
            'divisions': 1,
            'continental_slots': 8,
          },
          'rules_json': <String, Object?>{'region_label': 'Global'},
          'metadata_json': <String, Object?>{'region_label': 'Global'},
          'competitions_json': <Object?>[
            <String, Object?>{
              'competition_id': 'competition-global-champions',
              'name': 'Global Champions Series',
            },
          ],
          'members_json': <Object?>[],
        },
      ];

  final List<JsonMap> _giftCatalog;
  final List<JsonMap> _revenueRules;
  final List<JsonMap> _comboRules;
  final List<JsonMap> _burnEvents;
  final List<JsonMap> _cultures;
  final Map<String, JsonMap> _clubContexts;
  final Map<String, JsonMap> _competitionContexts;
  final List<JsonMap> _narratives;
  final List<JsonMap> _federations;

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    final String method = request.method.toUpperCase();
    final String path = _normalizePath(request.uri.path);

    if (method == 'GET' && path == '/api/economy/gift-catalog') {
      return _ok(_giftCatalog);
    }
    if (method == 'POST' && path == '/api/admin/economy/gift-catalog') {
      return _ok(_upsertByKey(_giftCatalog, _requestMap(request.body), 'key'));
    }
    if (method == 'GET' && path == '/api/admin/economy/revenue-share-rules') {
      return _ok(_filterActive(_revenueRules, request.uri, fallback: true));
    }
    if (method == 'POST' && path == '/api/admin/economy/revenue-share-rules') {
      return _ok(
        _upsertByKey(_revenueRules, _requestMap(request.body), 'rule_key'),
      );
    }
    if (method == 'GET' && path == '/api/admin/economy/gift-combo-rules') {
      return _ok(_filterActive(_comboRules, request.uri, fallback: true));
    }
    if (method == 'POST' && path == '/api/admin/economy/gift-combo-rules') {
      return _ok(
        _upsertByKey(_comboRules, _requestMap(request.body), 'rule_key'),
      );
    }
    if (method == 'GET' && path == '/api/admin/economy/burn-events') {
      return _ok(_limitList(_burnEvents, request.uri));
    }
    if (method == 'GET' && path == '/api/world/cultures') {
      return _ok(
        _limitList(_filterActive(_cultures, request.uri), request.uri),
      );
    }
    if (method == 'PUT' && path.startsWith('/api/admin/world/cultures/')) {
      final String cultureKey = path.substring(
        '/api/admin/world/cultures/'.length,
      );
      return _ok(
        _upsertByKey(_cultures, <String, Object?>{
          ..._requestMap(request.body),
          'culture_key': cultureKey,
          'id': 'culture-$cultureKey',
        }, 'culture_key'),
      );
    }
    if (method == 'GET' && path == '/api/federations') {
      return _ok(_federations);
    }
    if (method == 'GET' && path == '/api/federations/rankings') {
      return _ok(_federationRankings());
    }
    if (method == 'GET' && path == '/api/federations/regional-tournaments') {
      return _ok(_regionalTournaments());
    }
    if (method == 'GET' &&
        path.startsWith('/api/federations/national-associations/')) {
      final String countryCode =
          path
              .substring('/api/federations/national-associations/'.length)
              .split('/')
              .first
              .toUpperCase();
      return _ok(_nationalAssociation(countryCode));
    }
    if (method == 'GET' &&
        path.startsWith('/api/federations/') &&
        path.endsWith('/governance')) {
      return _ok(const <String, Object?>{
        'proposals': <Object?>[],
        'votes': <Object?>[],
        'sanctions': <Object?>[],
      });
    }
    if (method == 'GET' &&
        path.startsWith('/api/federations/') &&
        path.endsWith('/narratives')) {
      return _ok(_narratives);
    }
    if (method == 'GET' && path.startsWith('/api/federations/')) {
      return _ok(const <String, Object?>{
        'leagues': <Object?>[],
        'rules': <String, Object?>{},
        'members': <Object?>[],
        'reputation': <String, Object?>{
          'score': 80,
          'ranking_score': 84,
          'audience_size': 820000,
          'treasury_balance': 4200,
        },
      });
    }
    if (method == 'GET' &&
        (path == '/feed/for-you' || path == '/feed/following')) {
      return _ok(_viralFeedPayload(path.endsWith('following')));
    }
    if (method == 'GET' && path == '/feed/for-you/refresh') {
      return _ok(const <String, Object?>{
        'replace_indices': <int>[0],
        'new_items': <Object?>[],
      });
    }
    if (method == 'GET' && path == '/player-cards/packs') {
      return _ok(const <Object?>[
        <String, Object?>{
          'pack_key': 'starter-draft',
          'title': 'Starter Draft Pack',
          'description':
              'A fixture pack that mirrors the live collectible card contract.',
          'price_credits': 0,
          'cards_per_pack': 3,
          'drop_odds_json': <String, Object?>{
            'bronze': 70,
            'silver': 20,
            'gold': 8,
            'elite': 2,
          },
          'is_active': true,
        },
      ]);
    }
    if (method == 'POST' &&
        path.startsWith('/player-cards/packs/') &&
        path.endsWith('/open')) {
      return _ok(<String, Object?>{
        'opening_id': 'fixture-pack-opening',
        'pack_key': 'starter-draft',
        'user_id': 'fixture-user',
        'status': 'opened',
        'price_credits': 0,
        'created_at': DateTime.utc(2026, 5, 11, 9, 5).toIso8601String(),
        'opened_cards': const <Object?>[
          <String, Object?>{
            'player_card_id': 'fixture-card-1',
            'player_id': 'fixture-player-1',
            'display_name': 'Ayo Striker Base',
            'tier_code': 'gold',
            'tier_name': 'Gold',
            'rarity_rank': 3,
            'edition_code': 'base',
          },
        ],
      });
    }
    if (method == 'POST' &&
        (path == '/player-cards/cards/burn' ||
            path == '/player-cards/cards/upgrade')) {
      final bool isBurn = path == '/player-cards/cards/burn';
      return _ok(<String, Object?>{
        if (isBurn)
          'burn_event_id': 'fixture-collectible-action'
        else
          'upgrade_event_id': 'fixture-collectible-action',
        'status': 'completed',
      });
    }
    if (method == 'POST' &&
        path.startsWith('/api/federations/') &&
        path.endsWith('/memberships')) {
      return _ok(_joinFederation(path, _requestMap(request.body)));
    }
    if (method == 'GET' &&
        path.startsWith('/api/world/clubs/') &&
        path.endsWith('/context')) {
      return _ok(
        _clubContextFor(
          _extractScopedId(path, '/api/world/clubs/', '/context'),
        ),
      );
    }
    if (method == 'PUT' &&
        path.startsWith('/api/admin/world/clubs/') &&
        path.endsWith('/context')) {
      final String clubId = _extractScopedId(
        path,
        '/api/admin/world/clubs/',
        '/context',
      );
      final JsonMap context = <String, Object?>{
        ..._clubContextFor(clubId),
        'world_profile': <String, Object?>{
          ...jsonMap(
            _clubContextFor(clubId)['world_profile'],
            fallback: const <String, Object?>{},
          ),
          ..._requestMap(request.body),
        },
      };
      _clubContexts[clubId] = context;
      return _ok(context);
    }
    if (method == 'GET' &&
        path.startsWith('/api/world/competitions/') &&
        path.endsWith('/context')) {
      return _ok(
        _competitionContextFor(
          _extractScopedId(path, '/api/world/competitions/', '/context'),
        ),
      );
    }
    if (method == 'GET' && path == '/api/world/narratives') {
      return _ok(_limitList(_filterNarratives(request.uri), request.uri));
    }
    if (method == 'GET' && path == '/api/broadcast/home') {
      return _ok(_broadcastHomePayload());
    }
    if (method == 'PUT' && path.startsWith('/api/admin/world/narratives/')) {
      final String slug = path.substring('/api/admin/world/narratives/'.length);
      final JsonMap requestBody = _requestMap(request.body);
      return _ok(
        _upsertByKey(_narratives, <String, Object?>{
          ...requestBody,
          'id': 'narrative-$slug',
          'slug': slug,
          'scope_type':
              stringValue(requestBody['club_id']).isNotEmpty
                  ? 'club'
                  : stringValue(requestBody['competition_id']).isNotEmpty
                  ? 'competition'
                  : 'global',
        }, 'slug'),
      );
    }

    return const GteTransportResponse(
      statusCode: 404,
      body: <String, Object?>{
        'detail': 'Fixture feature route not implemented.',
      },
    );
  }

  GteTransportResponse _ok(Object body) {
    return GteTransportResponse(statusCode: 200, body: body);
  }

  String _normalizePath(String path) {
    if (path == '/api/v2') {
      return '/api';
    }
    if (path.startsWith('/api/v2/')) {
      return '/api${path.substring('/api/v2'.length)}';
    }
    return path;
  }

  JsonMap _requestMap(Object? body) {
    return jsonMap(body, fallback: const <String, Object?>{});
  }

  List<JsonMap> _limitList(List<JsonMap> items, Uri uri) {
    final int? limit = int.tryParse(uri.queryParameters['limit']?.trim() ?? '');
    if (limit == null || limit <= 0 || limit >= items.length) {
      return List<JsonMap>.from(items, growable: false);
    }
    return items.take(limit).toList(growable: false);
  }

  List<JsonMap> _filterActive(
    List<JsonMap> items,
    Uri uri, {
    bool fallback = false,
  }) {
    final String? activeOnly = uri.queryParameters['active_only'];
    final bool requireActive =
        activeOnly == null
            ? fallback
            : !<String>{
              '0',
              'false',
              'no',
            }.contains(activeOnly.trim().toLowerCase());
    if (!requireActive) {
      return List<JsonMap>.from(items, growable: false);
    }
    return items
        .where((JsonMap item) => boolValue(item['active'], fallback: true))
        .map((JsonMap item) => Map<String, Object?>.from(item))
        .toList(growable: false);
  }

  List<JsonMap> _filterNarratives(Uri uri) {
    final String clubId = (uri.queryParameters['club_id'] ?? '').trim();
    final String competitionId =
        (uri.queryParameters['competition_id'] ?? '').trim();
    return _narratives
        .where((JsonMap item) {
          if (clubId.isNotEmpty && stringValue(item['club_id']) != clubId) {
            return false;
          }
          if (competitionId.isNotEmpty &&
              stringValue(item['competition_id']) != competitionId) {
            return false;
          }
          return true;
        })
        .map((JsonMap item) => Map<String, Object?>.from(item))
        .toList(growable: false);
  }

  JsonMap _upsertByKey(List<JsonMap> items, JsonMap request, String keyField) {
    final String key = stringValue(request[keyField]);
    final JsonMap normalized = <String, Object?>{
      'id':
          stringOrNullValue(request['id']) ??
          '${keyField.replaceAll('_', '-')}-${key.isEmpty ? items.length + 1 : key}',
      ...request,
      if (!request.containsKey('updated_at'))
        'updated_at': DateTime.utc(2026, 4, 4, 12).toIso8601String(),
    };
    final int existingIndex = items.indexWhere(
      (JsonMap item) => stringValue(item[keyField]) == key,
    );
    if (existingIndex >= 0) {
      items[existingIndex] = normalized;
    } else {
      items.insert(0, normalized);
    }
    return Map<String, Object?>.from(normalized);
  }

  JsonMap _clubContextFor(String clubId) {
    return _clubContexts.putIfAbsent(
      clubId,
      () => <String, Object?>{
        'club_id': clubId,
        'club_name': _displayClubName(clubId),
        'short_name': _displayClubName(clubId).split(' ').take(2).join(' '),
        'country_code': 'NG',
        'region_name': 'South West',
        'city_name': 'Ibadan',
        'reputation_score': 74,
        'prestige_tier': 'ascending',
        'culture': _cultures.first,
        'world_profile': <String, Object?>{
          'supporter_mood': 'charged',
          'narrative_phase': 'identity_building',
          'identity_keywords_json': <String>['academy', 'pressing', 'regional'],
        },
        'active_narratives': _narratives
            .where((JsonMap item) => stringValue(item['club_id']) == clubId)
            .toList(growable: false),
        'simulation_hooks': <Object?>[
          <String, Object?>{
            'hook': 'pricing_feedback',
            'detail':
                'Player pricing, regen attraction, and club reputation share one runtime.',
          },
          <String, Object?>{
            'hook': 'academy_growth',
            'detail':
                'Youth development feeds directly into the regen universe desk.',
          },
        ],
      },
    );
  }

  JsonMap _competitionContextFor(String competitionId) {
    return _competitionContexts.putIfAbsent(
      competitionId,
      () => <String, Object?>{
        'competition_id': competitionId,
        'name': 'GTEX Elite Cup',
        'status': 'in_progress',
        'format': 'cup',
        'stage': 'quarterfinal',
        'participant_count': 8,
        'active_narratives': <Object?>[_narratives.last],
        'simulation_hooks': <Object?>[
          <String, Object?>{
            'hook': 'fixture_pressure',
            'detail': 'Match load influences club momentum and player pricing.',
          },
        ],
      },
    );
  }

  JsonMap _joinFederation(String path, JsonMap body) {
    final String federationId = _extractScopedId(
      path,
      '/api/federations/',
      '/memberships',
    );
    final String clubId = stringValue(body['club_id']);
    final JsonMap membership = <String, Object?>{
      'id': 'membership-$federationId-$clubId',
      'federation_id': federationId,
      'club_id': clubId,
      'role': 'member_club',
      'status': 'active',
      'metadata_json': body['metadata_json'] ?? const <String, Object?>{},
    };
    final int federationIndex = _federations.indexWhere(
      (JsonMap federation) => stringValue(federation['id']) == federationId,
    );
    if (federationIndex >= 0) {
      final List<JsonMap> members = jsonMapList(
        _federations[federationIndex]['members_json'],
        label: 'federation members',
      );
      final int existingIndex = members.indexWhere(
        (JsonMap item) => stringValue(item['club_id']) == clubId,
      );
      if (existingIndex >= 0) {
        members[existingIndex] = membership;
      } else {
        members.add(membership);
      }
      _federations[federationIndex] = <String, Object?>{
        ..._federations[federationIndex],
        'members_json': members,
      };
    }
    return membership;
  }

  List<JsonMap> _federationRankings() {
    return _federations
        .map(
          (JsonMap item) => <String, Object?>{
            'federation_id': item['id'],
            'name': item['name'],
            'ranking_score': item['ranking_score'],
            'reputation_score': item['reputation_score'],
            'audience_size': item['audience_size'],
            'activity_score': 76,
            'competitiveness_score': 81,
          },
        )
        .toList(growable: false);
  }

  List<JsonMap> _regionalTournaments() {
    return const <JsonMap>[
      <String, Object?>{
        'region_code': 'west_africa',
        'region_label': 'West Africa',
        'federation_count': 1,
        'active_league_count': 3,
        'total_member_clubs': 18,
      },
      <String, Object?>{
        'region_code': 'global',
        'region_label': 'Global',
        'federation_count': 1,
        'active_league_count': 2,
        'total_member_clubs': 24,
      },
    ];
  }

  JsonMap _nationalAssociation(String countryCode) {
    return <String, Object?>{
      'country_code': countryCode,
      'country_name': countryCode == 'NG' ? 'Nigeria' : countryCode,
      'confederation_code': 'CAF',
      'market_region': 'West Africa',
      'federation_count': 1,
      'active_league_count': 3,
      'member_club_count': 18,
      'sanction_count': 0,
      'ranking_score': 84.2,
      'top_federations': <Object?>[
        <String, Object?>{
          'federation_id': 'federation-west-africa',
          'name': 'West Africa Federation',
          'ranking_score': 84.2,
          'reputation_score': 79.5,
          'active_league_count': 3,
          'active_member_count': 18,
          'rules': <String, Object?>{},
        },
      ],
      'national_team_oversight': <String, Object?>{
        'country_codes': <String>[countryCode],
        'eligibility_policy': 'country_code_match',
      },
    };
  }

  JsonMap _viralFeedPayload(bool following) {
    final String feedSource = following ? 'following' : 'for_you';
    return <String, Object?>{
      'feed_key': 'fixture-$feedSource',
      'feed_source': feedSource,
      'generated_at': DateTime.utc(2026, 5, 11, 9).toIso8601String(),
      'cache_hit': false,
      'items': <Object?>[
        <String, Object?>{
          'clip_id': 'fixture-match::clip-001',
          'match_id': 'fixture-match',
          'highlight_id': 'clip-001',
          'title': 'Late winner lights up GTEX',
          'event_type': 'goal',
          'minute': 89,
          'viral_score': 92,
          'ranking_score': 0.92,
          'rank': 1,
          'score': 0.92,
          'feed_source': feedSource,
          'team_name': 'Ibadan Lions',
          'player_name': 'Ayo Striker',
          'scoreline_label': '2-1',
          'duration_seconds': 12,
          'share_channel': 'whatsapp',
          'tags': <String>['goal', 'late_drama'],
          'caption': <String, Object?>{
            'hook': "89' and the whole match flipped",
            'caption': 'GTEX pressure, one loose ball, and the crowd erupts.',
            'cta': 'Share to WhatsApp',
            'hashtags': <String>['GTEX', 'Football'],
          },
          'metadata': <String, Object?>{
            'summary_line':
                'The fixture feed is wired through the same viral feed contract.',
            'creator_id': 'fixture-creator',
            'format_key': 'match_recap',
          },
        },
      ],
    };
  }

  String _extractScopedId(String path, String prefix, String suffix) {
    final String trimmed = path.substring(prefix.length);
    return trimmed.substring(0, trimmed.length - suffix.length);
  }

  String _displayClubName(String clubId) {
    final List<String> parts = clubId
        .split(RegExp(r'[-_\s]+'))
        .where((String part) => part.trim().isNotEmpty)
        .map(
          (String part) =>
              '${part[0].toUpperCase()}${part.substring(1).toLowerCase()}',
        )
        .toList(growable: false);
    if (parts.isEmpty) {
      return 'Club Workspace';
    }
    if (parts.last.toLowerCase() == 'fc') {
      return parts.join(' ');
    }
    return '${parts.join(' ')} FC';
  }

  JsonMap _broadcastHomePayload() {
    const String featuredMatchKey = 'fixture-matchday-ibadan';
    return <String, Object?>{
      'generated_at': '2026-04-04T12:00:00Z',
      'featured_channel': <String, Object?>{
        'channel_id': 'fixture-featured',
        'name': 'GTEX Matchday Desk',
        'is_live': true,
        'current_program': <String, Object?>{
          'match_id': featuredMatchKey,
          'title': 'Ibadan Lions FC vs Atlas City',
          'subtitle':
              'Live football runtime with tactical 2D, broadcast package, and Flutter 3D lanes armed.',
          'watch_route': '/matches/viewer/$featuredMatchKey',
          'replay_route': '/matches/3d/$featuredMatchKey',
          'is_live': true,
          'metadata': <String, Object?>{
            'focus_reason':
                'The rich shell is mounted to real matchday lanes instead of replay previews.',
          },
        },
      },
      'channels': <Object?>[
        <String, Object?>{
          'channel_id': 'fixture-featured',
          'name': 'GTEX Matchday Desk',
          'is_live': true,
          'current_program': <String, Object?>{
            'match_id': featuredMatchKey,
            'title': 'Ibadan Lions FC vs Atlas City',
            'subtitle':
                'Open the live match hub, then step into the 2D viewer, broadcast package, or Flutter 3D lane.',
            'watch_route': '/matches/viewer/$featuredMatchKey',
            'replay_route': '/matches/3d/$featuredMatchKey',
            'is_live': true,
          },
        },
        <String, Object?>{
          'channel_id': 'fixture-next',
          'name': 'Transfer Window Cam',
          'is_live': true,
          'current_program': <String, Object?>{
            'match_id': 'fixture-transfer-window',
            'title': 'Lagos Rail FC vs Meridian SC',
            'subtitle':
                'Secondary matchday lane keeping pricing, scouting, and regen pull in sync.',
            'watch_route': '/matches/viewer/fixture-transfer-window',
            'replay_route': '/matches/3d/fixture-transfer-window',
            'is_live': true,
          },
        },
      ],
      'match_of_the_moment': <String, Object?>{
        'match_id': featuredMatchKey,
        'title': 'Ibadan Lions FC vs Atlas City',
        'subtitle': 'Featured live football lane',
        'watch_route': '/matches/viewer/$featuredMatchKey',
        'replay_route': '/matches/3d/$featuredMatchKey',
        'is_live': true,
      },
    };
  }
}
