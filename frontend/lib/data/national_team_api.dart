import 'gte_api_repository.dart';
import 'gte_authed_api.dart';
import 'gte_http_transport.dart';
import '../models/national_team_models.dart';

class NationalTeamApi {
  NationalTeamApi({required this.client, required this.fixtures});

  final GteAuthedApi client;
  final _NationalTeamFixtures fixtures;

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
      fixtures: _NationalTeamFixtures.seed(),
    );
  }

  factory NationalTeamApi.fixture() {
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
        '/api/national-team-engine/competitions',
        auth: false,
      );
      return payload
          .map(NationalTeamCompetition.fromJson)
          .toList(growable: false);
    }, fixtures.listCompetitions);
  }

  Future<NationalTeamRentalPlayerCollection> listRentalPool(
    String competitionId, {
    int limit = 200,
    int offset = 0,
    String? countryCode,
    String? position,
  }) {
    return client.withFallback<NationalTeamRentalPlayerCollection>(() async {
      final Map<String, Object?> query = <String, Object?>{
        'limit': limit,
        'offset': offset,
        if (countryCode != null && countryCode.trim().isNotEmpty)
          'country_code': countryCode.trim(),
        if (position != null && position.trim().isNotEmpty)
          'position': position.trim(),
      };
      final Map<String, dynamic> payload = await client.getMap(
        '/api/national-team-engine/competitions/$competitionId/rental-pool',
        query: query,
        auth: false,
      );
      return NationalTeamRentalPlayerCollection.fromJson(payload);
    }, () => fixtures.rentalPool(competitionId, countryCode: countryCode));
  }

  Future<NationalTeamEntry> createRentalEntry(
    String competitionId, {
    required String countryCode,
    required String countryName,
  }) {
    return client.withFallback<NationalTeamEntry>(
      () async {
        final Object? payload = await client.post(
          '/api/national-team-engine/competitions/$competitionId/rental-entry',
          body: <String, Object?>{
            'country_code': countryCode,
            'country_name': countryName,
            'metadata_json': <String, Object?>{'source': 'gtex_frontend_v2'},
          },
        );
        return NationalTeamEntry.fromJson(payload);
      },
      () => fixtures.createRentalEntry(
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
        '/api/national-team-engine/entries/$entryId/rentals',
        body: <String, Object?>{
          'player_id': playerId,
          if (shirtNumber != null) 'shirt_number': shirtNumber,
        },
      );
      return NationalTeamEntryDetail.fromJson(payload);
    }, () => fixtures.entryDetail(entryId));
  }

  Future<NationalTeamEntryDetail> fetchEntryDetail(String entryId) {
    return client.withFallback<NationalTeamEntryDetail>(() async {
      final Map<String, dynamic> payload = await client.getMap(
        '/api/national-team-engine/entries/$entryId',
        auth: false,
      );
      return NationalTeamEntryDetail.fromJson(payload);
    }, () async => fixtures.entryDetail(entryId));
  }

  Future<NationalTeamUserHistory> fetchUserHistory() {
    return client.withFallback<NationalTeamUserHistory>(() async {
      final Map<String, dynamic> payload = await client.getMap(
        '/api/national-team-engine/me/history',
      );
      return NationalTeamUserHistory.fromJson(payload);
    }, fixtures.userHistory);
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
