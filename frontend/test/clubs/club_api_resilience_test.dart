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
  test('fetchDashboard degrades optional dynasty and trophy data', () async {
    final ClubApi api = ClubApi(
      config: const GteRepositoryConfig(
        baseUrl: 'http://127.0.0.1:8000',
        mode: GteBackendMode.fixture,
      ),
      transport: _UnexpectedTransport(),
      reputationRepository: FixtureReputationRepository(
        latency: Duration.zero,
      ),
      dynastyRepository: _FailingDynastyRepository(),
      trophyRepository: StubTrophyCabinetRepository(
        scenario: TrophyRepositoryScenario.error,
        latency: Duration.zero,
      ),
      identityRepository: MockClubIdentityRepository(
        latency: Duration.zero,
      ),
    );

    final ClubDashboardData data = await api.fetchDashboard(
      clubId: 'royal-lagos-fc',
    );

    expect(data.clubId, 'royal-lagos-fc');
    expect(data.identity.clubName, isNotEmpty);
    expect(data.reputation.profile.currentScore, greaterThan(0));
    expect(data.dynastyProfile.dynastyScore, 0);
    expect(data.dynastyProfile.hasRecognizedDynasty, isFalse);
    expect(data.trophyCabinet.totalHonorsCount, 0);
    expect(data.trophyCabinet.isEmpty, isTrue);
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

class _UnexpectedTransport implements GteTransport {
  @override
  Future<GteTransportResponse> send(GteTransportRequest request) {
    throw UnsupportedError('transport should not be used in this test');
  }
}
