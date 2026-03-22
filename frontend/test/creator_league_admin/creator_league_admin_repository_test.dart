import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/features/creator_league_admin/data/creator_league_admin_models.dart';
import 'package:gte_frontend/features/creator_league_admin/data/creator_league_admin_repository.dart';

void main() {
  test('creator league admin repository targets the canonical competitions prefix',
      () async {
    final _RecordingTransport transport = _RecordingTransport(
      <GteTransportResponse>[
        GteTransportResponse(statusCode: 200, body: _configPayload()),
        GteTransportResponse(
          statusCode: 200,
          body: _financialReportPayload(),
        ),
        GteTransportResponse(
          statusCode: 200,
          body: <Object?>[_settlementPayload()],
        ),
      ],
    );
    final CreatorLeagueAdminApiRepository repository =
        CreatorLeagueAdminApiRepository(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.live,
        ),
        transport: transport,
        accessToken: 'token-123',
      ),
    );

    final CreatorLeagueConfig overview = await repository.fetchOverview();
    final CreatorLeagueFinancialReport report =
        await repository.fetchFinancialReport(
      const CreatorLeagueFinancialReportQuery(seasonId: 'creator-season-1'),
    );
    final List<CreatorLeagueSettlement> settlements =
        await repository.listSettlements(
      const CreatorLeagueFinancialSettlementsQuery(
        seasonId: 'creator-season-1',
      ),
    );

    expect(overview.leagueKey, 'creator_league');
    expect(report.config.leagueKey, 'creator_league');
    expect(settlements.single.seasonId, 'creator-season-1');
    expect(
      transport.requests.map((GteTransportRequest request) => request.uri.path),
      <String>[
        '/api/competitions/creator-league',
        '/api/competitions/creator-league/financial-report',
        '/api/competitions/creator-league/financial-settlements',
      ],
    );
    expect(
      transport.requests[1].uri.queryParameters['season_id'],
      'creator-season-1',
    );
    expect(
      transport.requests[2].uri.queryParameters['season_id'],
      'creator-season-1',
    );
  });
}

Map<String, Object?> _configPayload() {
  return <String, Object?>{
    'id': 'creator-league-config-1',
    'league_key': 'creator_league',
    'enabled': true,
    'seasons_paused': false,
    'league_format': 'double_round_robin',
    'default_club_count': 20,
    'division_count': 3,
    'match_frequency_days': 7,
    'season_duration_days': 266,
    'broadcast_purchases_enabled': true,
    'season_pass_sales_enabled': true,
    'match_gifting_enabled': true,
    'settlement_review_enabled': true,
    'settlement_review_total_revenue_coin': 1000,
    'settlement_review_creator_share_coin': 100,
    'settlement_review_platform_share_coin': 100,
    'settlement_review_shareholder_distribution_coin': 100,
    'tiers': const <Object?>[],
    'movement_rules': const <Object?>[],
  };
}

Map<String, Object?> _financialReportPayload() {
  return <String, Object?>{
    'config': _configPayload(),
    'share_market_control': const <String, Object?>{},
    'stadium_control': const <String, Object?>{},
    'creator_match_gift_controls': const <String, Object?>{},
    'settlements_requiring_review': const <Object?>[],
    'recent_audit_events': const <Object?>[],
  };
}

Map<String, Object?> _settlementPayload() {
  return <String, Object?>{
    'id': 'settlement-1',
    'season_id': 'creator-season-1',
    'competition_id': 'creator-league-competition-1',
    'match_id': 'match-1',
    'home_club_id': 'royal-lagos-fc',
    'away_club_id': 'atlas-fc',
    'total_revenue_coin': 500,
    'total_creator_share_coin': 100,
    'total_platform_share_coin': 400,
    'shareholder_total_distribution_coin': 50,
    'review_status': 'review_required',
    'review_reason_codes_json': const <String>[],
    'policy_snapshot_json': const <String, Object?>{},
    'metadata_json': const <String, Object?>{},
  };
}

class _RecordingTransport implements GteTransport {
  _RecordingTransport(this._responses);

  final List<GteTransportResponse> _responses;
  final List<GteTransportRequest> requests = <GteTransportRequest>[];

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    requests.add(request);
    return _responses.removeAt(0);
  }
}
