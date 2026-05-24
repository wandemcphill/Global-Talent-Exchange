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
    'national rental V2 derives countries from the live eligibility pool',
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
      expect(nationalApi.listRentalPoolCalls, 1);
      expect(nationalApi.lastRentalPoolCountryCode, isNull);
      expect(find.text('Nigeria'), findsWidgets);
      expect(find.text('Live Pool Forward'), findsOneWidget);
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
