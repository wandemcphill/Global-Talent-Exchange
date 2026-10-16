import 'package:flutter_test/flutter_test.dart';
import 'package:gte_frontend/data/club_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_era_dto.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_leaderboard_entry_dto.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_profile_dto.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_repository.dart';
import 'package:gte_frontend/features/club_identity/jerseys/data/club_identity_repository.dart';
import 'package:gte_frontend/features/club_identity/reputation/data/reputation_repository.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/trophy_cabinet_repository.dart';
import 'package:gte_frontend/models/club_models.dart';

void main() {
  test(
    'fetchDashboard uses the registered fixture factory in fixture mode',
    () async {
      final ClubApi api = ClubApi.fixture();

      final ClubDashboardData data = await api.fetchDashboard(
        clubId: 'royal-lagos-fc',
      );

      expect(data.clubId, 'royal-lagos-fc');
      expect(data.identity.clubName, isNotEmpty);
      expect(data.reputation.profile.currentScore, greaterThan(0));
      expect(data.dynastyProfile.clubId, 'royal-lagos-fc');
      expect(data.trophyCabinet.clubId, 'royal-lagos-fc');
    },
  );

  test('fetchV2WorkspaceSnapshot maps the canonical live aggregate', () async {
    final _SnapshotTransport transport = _SnapshotTransport();
    final ClubApi api = ClubApi(
      config: const GteRepositoryConfig(
        baseUrl: 'http://127.0.0.1:8000',
        mode: GteBackendMode.live,
      ),
      transport: transport,
      accessToken: 'token-live',
      reputationRepository: FixtureReputationRepository(latency: Duration.zero),
      dynastyRepository: _FailingDynastyRepository(),
      trophyRepository: StubTrophyCabinetRepository(latency: Duration.zero),
      identityRepository: MockClubIdentityRepository(latency: Duration.zero),
    );

    final snapshot = await api.fetchV2WorkspaceSnapshot(clubId: 'club-live');

    expect(
      transport.lastRequest.uri.path,
      '/api/v2/clubs/club-live/v2-snapshot',
    );
    expect(transport.lastRequest.headers['Authorization'], 'Bearer token-live');
    expect(snapshot.clubId, 'club-live');
    expect(snapshot.clubName, 'Lagos Legacy');
    expect(snapshot.shortCode, 'LL');
    expect(snapshot.finances.walletCredits, 123456);
    expect(snapshot.finances.squadValueCredits, 75000);
    expect(snapshot.squad.single.name, 'Adaeze Okoro');
    expect(snapshot.squad.single.isRegen, isFalse);
    expect(snapshot.orders.single.title, 'Listing: Adaeze Okoro');
    expect(snapshot.identityTags, contains('1 registered players'));
    expect(
      snapshot.activity.first,
      'Loaded from /api/clubs/{club_id}/v2-snapshot',
    );
  });
}

class _FailingDynastyRepository implements DynastyRepository {
  @override
  Future<DynastyProfileDto> fetchDynastyProfile(String clubId) async {
    throw StateError('dynasty unavailable');
  }

  @override
  Future<DynastyHistoryDto> fetchDynastyHistory(String clubId) async {
    return const DynastyHistoryDto(
      clubId: 'unknown-club',
      clubName: 'Unknown club',
      dynastyTimeline: <DynastySnapshotDto>[],
      eras: <DynastyEraDto>[],
      events: <DynastyEventDto>[],
    );
  }

  @override
  Future<List<DynastyEraDto>> fetchEras(String clubId) async {
    return const <DynastyEraDto>[];
  }

  @override
  Future<List<DynastyLeaderboardEntryDto>> fetchDynastyLeaderboard({
    int limit = 25,
  }) async {
    return const <DynastyLeaderboardEntryDto>[];
  }
}

class _SnapshotTransport implements GteTransport {
  late GteTransportRequest lastRequest;

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    lastRequest = request;
    return const GteTransportResponse(
      statusCode: 200,
      body: <String, Object?>{
        'success': true,
        'data': <String, Object?>{
          'live': true,
          'fixture': false,
          'demo': false,
          'source': 'live',
          'club_id': 'club-live',
          'club': <String, Object?>{
            'club_name': 'Lagos Legacy',
            'short_name': 'LL',
            'country_code': 'NG',
            'owner_display_name': 'Owner One',
          },
          'squad': <String, Object?>{
            'player_count': 1,
            'squad_value_credits': 75000,
            'players': <Object?>[
              <String, Object?>{
                'player_id': 'player-live-1',
                'name': 'Adaeze Okoro',
                'position': 'ST',
                'nationality': 'Nigeria',
                'market_value_credits': 75000,
                'rating': 82.5,
                'is_regen': false,
              },
            ],
          },
          'wallet': <String, Object?>{'wallet_credits': 123456},
          'ranking': <String, Object?>{
            'reputation_score': 41,
            'prestige_tier': 'Local',
          },
          'facilities': <String, Object?>{
            'supporter_token': <String, Object?>{'holder_count': 9},
            'projected_matchday_revenue_coin': 500,
          },
          'competitions': <String, Object?>{'active_count': 1},
          'transfers': <String, Object?>{
            'outgoing_listing_count': 1,
            'incoming_bid_count': 0,
            'outgoing_offer_count': 0,
            'incoming_offer_count': 0,
            'transfer_request_count': 0,
            'activity': <Object?>[
              <String, Object?>{
                'id': 'listing-live',
                'kind': 'listing',
                'status': 'open',
                'player_id': 'player-live-1',
                'player_name': 'Adaeze Okoro',
                'amount_credits': 85000,
              },
            ],
          },
        },
      },
    );
  }
}
