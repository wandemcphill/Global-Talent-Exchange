import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_exchange_api_client.dart';
import 'package:gte_frontend/data/national_team_api.dart';
import 'package:gte_frontend/models/national_team_models.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/screens/gtex_national_team_rental_screen_v2.dart';

void main() {
  testWidgets(
    'national rental V2 loads country and team authority before the pool',
    (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1400, 1000);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final _FakeNationalTeamApi nationalApi = _FakeNationalTeamApi();
      final GteExchangeController controller = GteExchangeController(
        api: GteExchangeApiClient.standard(baseUrl: 'https://api.gtex.test'),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: GtexNationalTeamRentalScreenV2(
            controller: controller,
            apiBaseUrl: 'https://api.gtex.test',
            nationalTeamApi: nationalApi,
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(nationalApi.listCompetitionsCalls, 1);
      expect(nationalApi.listCountriesCalls, 1);
      expect(nationalApi.lastCountriesCompetitionId, 'comp-1');
      expect(nationalApi.listTeamsCalls, 2);
      expect(nationalApi.lastTeamsCompetitionId, 'comp-1');
      expect(nationalApi.lastTeamsCountryCode, 'NG');
      expect(nationalApi.listRentalPoolCalls, 1);
      expect(nationalApi.lastRentalPoolCountryCode, 'NG');
      expect(find.text('Nigeria'), findsWidgets);
      expect(find.text('Live Pool Forward'), findsWidgets);
    },
  );
}

class _FakeNationalTeamApi extends NationalTeamApi {
  _FakeNationalTeamApi()
    : super(
        client: GteAuthedApi(
          config: const GteRepositoryConfig(baseUrl: 'https://api.gtex.test'),
          transport: _NoopTransport(),
          accessToken: 'token',
        ),
      );

  int listCompetitionsCalls = 0;
  int listCountriesCalls = 0;
  int listTeamsCalls = 0;
  String? lastCountriesCompetitionId;
  String? lastTeamsCompetitionId;
  String? lastTeamsCountryCode;
  int listRentalPoolCalls = 0;
  String? lastRentalPoolCountryCode;

  @override
  Future<List<NationalTeamCompetition>> listCompetitions() async {
    listCompetitionsCalls += 1;
    return <NationalTeamCompetition>[
      NationalTeamCompetition(
        id: 'comp-1',
        key: 'nations-cup',
        title: 'Nations Cup',
        seasonLabel: 'Spring 2026',
        regionType: 'global',
        ageBand: 'senior',
        formatType: 'cup',
        status: 'open',
        notes: 'Live rental competition.',
        active: true,
        createdAt: DateTime.parse('2026-03-01T00:00:00Z'),
        updatedAt: DateTime.parse('2026-03-12T00:00:00Z'),
      ),
    ];
  }

  @override
  Future<List<Map<String, dynamic>>> listCountries({
    String? competitionId,
  }) async {
    listCountriesCalls += 1;
    lastCountriesCompetitionId = competitionId;
    return <Map<String, dynamic>>[
      <String, dynamic>{
        'country_code': 'NG',
        'country_name': 'Nigeria',
        'confederation': 'CAF',
        'eligible_players': 1,
        'rental_budget_label': 'Backend authority',
      },
    ];
  }

  @override
  Future<List<Map<String, dynamic>>> listTeams({
    String? competitionId,
    String? countryCode,
  }) async {
    listTeamsCalls += 1;
    lastTeamsCompetitionId = competitionId;
    lastTeamsCountryCode = countryCode;
    return <Map<String, dynamic>>[
      <String, dynamic>{
        'id': 'team-ng',
        'country_code': 'NG',
        'name': 'Nigeria Senior',
        'age_band': 'senior',
        'competition_id': competitionId,
        'eligible_players': 1,
        'min_squad_size': 16,
        'max_squad_size': 26,
      },
    ];
  }

  @override
  Future<NationalTeamRentalPlayerCollection> listRentalPool(
    String competitionId, {
    int limit = 200,
    int offset = 0,
    String? countryCode,
    String? position,
    String? entryId,
    bool auth = false,
  }) async {
    listRentalPoolCalls += 1;
    lastRentalPoolCountryCode = countryCode;
    return NationalTeamRentalPlayerCollection(
      total: 1,
      items: <NationalTeamRentalPlayer>[
        NationalTeamRentalPlayer(
          playerId: 'player-ng-1',
          playerName: 'Live Pool Forward',
          overallRating: 78,
          primaryPosition: 'ST',
          currentClubName: 'Backend FC',
          currentLeagueName: 'Authority League',
          nationality: 'Nigeria',
          countryCode: 'NG',
          age: 22,
          gsi: 74,
          baseValueCoin: 1200,
          loanPriceCoin: 240,
          tierLabel: 'Gold',
          sourceBucket: 'real_player',
          isRegen: false,
          isPreseededNationalRegen: false,
          marketEligible: true,
          eligibility: const NationalTeamRentalEligibility(
            eligible: true,
            reasons: <String>[],
            checks: <String, bool>{'nationality': true},
            message: 'Eligible from backend.',
          ),
        ),
      ],
    );
  }
}

class _NoopTransport implements GteTransport {
  @override
  Future<GteTransportResponse> send(GteTransportRequest request) {
    throw StateError('Unexpected transport call in national rental test.');
  }
}
