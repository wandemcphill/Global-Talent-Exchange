import 'package:gte_frontend/app/test_runtime_detector.dart';

import 'gte_api_repository.dart';
import 'gte_authed_api.dart';
import 'gte_http_transport.dart';
import '../models/national_team_models.dart';

class NationalTeamApi {
  NationalTeamApi({required this.client, this.fixtures});

  final GteAuthedApi client;
  final _NationalTeamFixtures? fixtures;

  bool get hasRegisteredFixtures => fixtures != null;

  String _nationalAlias(String path) {
    final Uri baseUri = Uri.parse(
      client.config.baseUrl.endsWith('/')
          ? client.config.baseUrl
          : '${client.config.baseUrl}/',
    );
    return baseUri
        .resolve(path.startsWith('/') ? path.substring(1) : path)
        .toString();
  }

  factory NationalTeamApi.standard({
    required String baseUrl,
    required String? accessToken,
    GteBackendMode mode = GteBackendMode.live,
    GteTransport? transport,
  }) {
    final GteBackendMode resolvedMode = gteProductionBackendMode(mode);
    final GteTransport resolvedTransport = transport ?? GteHttpTransport();
    return NationalTeamApi(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: resolvedMode),
        transport: resolvedTransport,
        accessToken: accessToken,
        mode: resolvedMode,
      ),
    );
  }

  factory NationalTeamApi.fixture() {
    assertFixtureFactoryAllowed('NationalTeamApi.fixture');
    return NationalTeamApi(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.fixture,
        ),
        transport: GteHttpTransport(),
        accessToken: 'fixture-token',
        mode: GteBackendMode.fixture,
      ),
      fixtures: _NationalTeamFixtures.seed(),
    );
  }

  Future<List<NationalTeamCompetition>> listCompetitions() {
    return client.withFallback<List<NationalTeamCompetition>>(() async {
      final List<dynamic> payload = await client.getList(
        _nationalAlias('/api/national/competitions'),
        auth: false,
      );
      return payload
          .map(NationalTeamCompetition.fromJson)
          .toList(growable: false);
    }, () => _requireFixtures().listCompetitions());
  }

  Future<List<Map<String, dynamic>>> listCountries({
    String? competitionId,
  }) async {
    final Object? payload = await client.request(
      'GET',
      _nationalAlias('/api/national/countries'),
      query: <String, Object?>{
        if (competitionId != null && competitionId.trim().isNotEmpty)
          'competition_id': competitionId.trim(),
      },
      auth: false,
    );
    return _mapListPayload(
      payload,
      listKeys: const <String>['countries', 'items', 'results'],
      label: 'national countries',
    );
  }

  Future<List<Map<String, dynamic>>> listTeams({
    String? competitionId,
    String? countryCode,
  }) async {
    final Object? payload = await client.request(
      'GET',
      _nationalAlias('/api/national/teams'),
      query: <String, Object?>{
        if (competitionId != null && competitionId.trim().isNotEmpty)
          'competition_id': competitionId.trim(),
        if (countryCode != null && countryCode.trim().isNotEmpty)
          'country_code': countryCode.trim().toUpperCase(),
      },
      auth: false,
    );
    return _mapListPayload(
      payload,
      listKeys: const <String>['teams', 'items', 'results'],
      label: 'national teams',
    );
  }

  Future<NationalTeamRentalPlayerCollection> listRentalPool(
    String competitionId, {
    int limit = 200,
    int offset = 0,
    String? countryCode,
    String? position,
    String? entryId,
    bool auth = false,
  }) {
    return client.withFallback<NationalTeamRentalPlayerCollection>(
      () async {
        final Map<String, Object?> query = <String, Object?>{
          'limit': limit,
          'offset': offset,
          if (countryCode != null && countryCode.trim().isNotEmpty)
            'country_code': countryCode.trim(),
          if (position != null && position.trim().isNotEmpty)
            'position': position.trim(),
          if (entryId != null && entryId.trim().isNotEmpty)
            'entry_id': entryId.trim(),
        };
        final Map<String, dynamic> payload = await client.getMap(
          _nationalAlias(
            '/api/national/competitions/$competitionId/rental-pool',
          ),
          query: query,
          auth: auth,
        );
        return NationalTeamRentalPlayerCollection.fromJson(payload);
      },
      () => _requireFixtures().rentalPool(
        competitionId,
        countryCode: countryCode,
      ),
    );
  }

  Future<NationalTeamEntry> createRentalEntry(
    String competitionId, {
    required String countryCode,
    required String countryName,
  }) {
    return client.withFallback<NationalTeamEntry>(
      () async {
        final Object? payload = await client.post(
          _nationalAlias(
            '/api/national/competitions/$competitionId/rental-entry',
          ),
          body: <String, Object?>{
            'country_code': countryCode,
            'country_name': countryName,
            'metadata_json': <String, Object?>{'source': 'gtex_frontend_v2'},
          },
        );
        return NationalTeamEntry.fromJson(payload);
      },
      () => _requireFixtures().createRentalEntry(
        competitionId,
        countryCode: countryCode,
        countryName: countryName,
      ),
    );
  }

  Future<NationalTeamEntryDetail> rentPlayer({
    required String entryId,
    required String playerId,
    int? shirtNumber,
  }) {
    return client.withFallback<NationalTeamEntryDetail>(() async {
      final Object? payload = await client.post(
        _nationalAlias('/api/national/entries/$entryId/rentals'),
        body: <String, Object?>{
          'player_id': playerId,
          if (shirtNumber != null) 'shirt_number': shirtNumber,
        },
      );
      return NationalTeamEntryDetail.fromJson(payload);
    }, () => _requireFixtures().entryDetail(entryId));
  }

  Future<NationalTeamEntryDetail> fetchEntryDetail(String entryId) {
    return client.withFallback<NationalTeamEntryDetail>(() async {
      final Map<String, dynamic> payload = await client.getMap(
        _nationalAlias('/api/national/entries/$entryId'),
        auth: false,
      );
      return NationalTeamEntryDetail.fromJson(payload);
    }, () async => _requireFixtures().entryDetail(entryId));
  }

  Future<NationalTeamUserHistory> fetchUserHistory() {
    return client.withFallback<NationalTeamUserHistory>(() async {
      final Map<String, dynamic> payload = await client.getMap(
        _nationalAlias('/api/national/me/history'),
      );
      return NationalTeamUserHistory.fromJson(payload);
    }, () => _requireFixtures().userHistory());
  }

  _NationalTeamFixtures _requireFixtures() {
    final _NationalTeamFixtures? resolvedFixtures = fixtures;
    if (resolvedFixtures == null) {
      throw StateError(
        'National-team fixture data is not registered in strict-live runtime.',
      );
    }
    return resolvedFixtures;
  }

  List<Map<String, dynamic>> _mapListPayload(
    Object? payload, {
    required List<String> listKeys,
    required String label,
  }) {
    Object? resolved = payload;
    if (payload is Map) {
      for (final String key in listKeys) {
        final Object? candidate = payload[key];
        if (candidate is List) {
          resolved = candidate;
          break;
        }
      }
    }
    if (resolved is! List) {
      throw GteApiException(
        type: GteApiErrorType.parsing,
        message: 'Unexpected $label response shape.',
      );
    }
    return resolved
        .whereType<Map>()
        .map((Map<dynamic, dynamic> item) => Map<String, dynamic>.from(item))
        .toList(growable: false);
  }
}

class _NationalTeamFixtures {
  _NationalTeamFixtures(this._competitions, this._entries);

  final List<NationalTeamCompetition> _competitions;
  final List<NationalTeamEntry> _entries;

  static _NationalTeamFixtures seed() {
    final List<NationalTeamCompetition> competitions =
        <NationalTeamCompetition>[
          NationalTeamCompetition(
            id: 'nt-1',
            key: 'world-scout-qualifier',
            title: 'World Scout Qualifier',
            seasonLabel: 'Spring 2026',
            regionType: 'global',
            ageBand: 'senior',
            formatType: 'cup',
            status: 'open',
            notes: 'Regional qualifiers open now.',
            active: true,
            createdAt: DateTime.parse('2026-03-01T00:00:00Z'),
            updatedAt: DateTime.parse('2026-03-12T00:00:00Z'),
          ),
        ];
    final List<NationalTeamEntry> entries = <NationalTeamEntry>[
      NationalTeamEntry(
        id: 'entry-1',
        competitionId: 'nt-1',
        countryCode: 'NG',
        countryName: 'Nigeria',
        managerUserId: 'user-1',
        squadSize: 5,
        metadata: const <String, Object?>{'seed': 1},
        createdAt: DateTime.parse('2026-03-05T00:00:00Z'),
        updatedAt: DateTime.parse('2026-03-12T00:00:00Z'),
      ),
    ];
    return _NationalTeamFixtures(competitions, entries);
  }

  Future<List<NationalTeamCompetition>> listCompetitions() async =>
      List<NationalTeamCompetition>.of(_competitions, growable: false);

  Future<NationalTeamRentalPlayerCollection> rentalPool(
    String competitionId, {
    String? countryCode,
  }) async {
    final List<NationalTeamRentalPlayer> items = <NationalTeamRentalPlayer>[
      NationalTeamRentalPlayer(
        playerId: 'fixture-ng-9',
        playerName: 'T. Adebayo',
        overallRating: 78.4,
        primaryPosition: 'ST',
        currentClubName: 'Lagos Meteors',
        currentLeagueName: 'GTEX National Pool',
        nationality: 'Nigeria',
        countryCode: 'NG',
        age: 19,
        gsi: 81,
        baseValueCoin: 1200000,
        loanPriceCoin: 240000,
        tierLabel: 'Gold',
        sourceBucket: 'SportMonks',
        isRegen: false,
        isPreseededNationalRegen: false,
        marketEligible: true,
        eligibility: const NationalTeamRentalEligibility(
          eligible: true,
          reasons: <String>[],
          checks: <String, bool>{'fixture': true},
        ),
      ),
      NationalTeamRentalPlayer(
        playerId: 'fixture-ng-10',
        playerName: 'M. Okoro',
        overallRating: 74.8,
        primaryPosition: 'CM',
        currentClubName: 'GTEX National Seed',
        currentLeagueName: 'National Seed Pool',
        nationality: 'Nigeria',
        countryCode: 'NG',
        age: 18,
        gsi: 77,
        baseValueCoin: 475000,
        loanPriceCoin: 95000,
        tierLabel: 'Seed',
        sourceBucket: 'national_seed',
        isRegen: true,
        isPreseededNationalRegen: true,
        marketEligible: true,
        eligibility: const NationalTeamRentalEligibility(
          eligible: true,
          reasons: <String>[],
          checks: <String, bool>{'fixture': true},
        ),
      ),
    ];
    final List<NationalTeamRentalPlayer> filtered =
        countryCode == null || countryCode.trim().isEmpty
            ? items
            : items
                .where(
                  (NationalTeamRentalPlayer player) =>
                      player.countryCode == countryCode,
                )
                .toList(growable: false);
    return NationalTeamRentalPlayerCollection(
      total: filtered.length,
      items: filtered,
    );
  }

  Future<NationalTeamEntry> createRentalEntry(
    String competitionId, {
    required String countryCode,
    required String countryName,
  }) async {
    return NationalTeamEntry(
      id: 'fixture-entry-$countryCode',
      competitionId: competitionId,
      countryCode: countryCode,
      countryName: countryName,
      managerUserId: 'fixture-user',
      squadSize: 0,
      metadata: const <String, Object?>{'source': 'fixture'},
      createdAt: DateTime.now().toUtc(),
      updatedAt: DateTime.now().toUtc(),
    );
  }

  Future<NationalTeamEntryDetail> entryDetail(String entryId) async {
    final NationalTeamEntry entry = _entries.firstWhere(
      (NationalTeamEntry item) => item.id == entryId,
      orElse: () => _entries.first,
    );
    return NationalTeamEntryDetail(
      entry: entry,
      squadMembers: <NationalTeamSquadMember>[
        NationalTeamSquadMember(
          id: 'member-1',
          entryId: entry.id,
          userId: 'user-22',
          playerName: 'K. Midfield',
          shirtNumber: 8,
          roleLabel: 'Captain',
          status: 'selected',
          createdAt: DateTime.now().toUtc(),
          updatedAt: DateTime.now().toUtc(),
        ),
      ],
      managerHistory: <NationalTeamManagerHistory>[
        NationalTeamManagerHistory(
          id: 'hist-1',
          entryId: entry.id,
          userId: 'user-1',
          actionType: 'assigned',
          note: 'Assigned national team manager.',
          createdAt: DateTime.now().toUtc(),
          updatedAt: DateTime.now().toUtc(),
        ),
      ],
    );
  }

  Future<NationalTeamUserHistory> userHistory() async {
    return NationalTeamUserHistory(
      managedEntries: _entries,
      squadMemberships: const <NationalTeamSquadMember>[],
    );
  }
}
