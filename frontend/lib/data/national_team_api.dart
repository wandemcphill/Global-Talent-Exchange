import 'gte_api_repository.dart';
import 'gte_authed_api.dart';
import 'gte_http_transport.dart';
import '../models/national_team_models.dart';

class NationalTeamApi {
  NationalTeamApi({
    required this.client,
    required this.fixtures,
  });

  final GteAuthedApi client;
  final _NationalTeamFixtures fixtures;

  factory NationalTeamApi.standard({
    required String baseUrl,
    required String? accessToken,
    GteBackendMode mode = GteBackendMode.liveThenFixture,
  }) {
    return NationalTeamApi(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: mode),
        transport: GteHttpTransport(),
        accessToken: accessToken,
        mode: mode,
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
    return client.withFallback<List<NationalTeamCompetition>>(
      () async {
        final List<dynamic> payload =
            await client.getList('/national-team-engine/competitions', auth: false);
        return payload
            .map(NationalTeamCompetition.fromJson)
            .toList(growable: false);
      },
      fixtures.listCompetitions,
    );
  }

  Future<NationalTeamEntryDetail> fetchEntryDetail(String entryId) {
    return client.withFallback<NationalTeamEntryDetail>(
      () async {
        final Map<String, dynamic> payload =
            await client.getMap('/national-team-engine/entries/$entryId', auth: false);
        return NationalTeamEntryDetail.fromJson(payload);
      },
      () async => fixtures.entryDetail(entryId),
    );
  }

  Future<NationalTeamUserHistory> fetchUserHistory() {
    return client.withFallback<NationalTeamUserHistory>(
      () async {
        final Map<String, dynamic> payload =
            await client.getMap('/national-team-engine/me/history');
        return NationalTeamUserHistory.fromJson(payload);
      },
      fixtures.userHistory,
    );
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

  Future<NationalTeamEntryDetail> entryDetail(String entryId) async {
    final NationalTeamEntry entry =
        _entries.firstWhere((NationalTeamEntry item) => item.id == entryId, orElse: () => _entries.first);
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
