import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/features/club/data/club_hq_repository.dart';
import 'package:gte_frontend/features/club/domain/club_hq_models.dart';
import 'package:gte_frontend/features/club/providers/club_hq_providers.dart';
import 'package:gte_frontend/shared/state/gtex_async_surface_state.dart';

void main() {
  test(
    'clubFinanceProvider blocks backend null balance without zero fallback',
    () async {
      final ProviderContainer container = ProviderContainer(
        overrides: [
          clubHqRepositoryProvider.overrideWithValue(
            _FinanceOnlyClubRepository(
              const ClubFinanceDTO(clubId: 'club-1', balance: null),
            ),
          ),
        ],
      );
      addTearDown(container.dispose);

      final GtexSurfaceState<ClubFinanceDTO> state = await container.read(
        clubFinanceProvider(
          const ClubHqRequest(clubId: 'club-1', role: 'club.owner'),
        ).future,
      );

      expect(state, isA<GtexBlocked<ClubFinanceDTO>>());
      expect(
        (state as GtexBlocked<ClubFinanceDTO>).reason,
        'Balance data unavailable - sync in progress.',
      );
    },
  );

  test('clubFinanceProvider renders backend balance when provided', () async {
    final ProviderContainer container = ProviderContainer(
      overrides: [
        clubHqRepositoryProvider.overrideWithValue(
          _FinanceOnlyClubRepository(
            const ClubFinanceDTO(clubId: 'club-1', balance: 1250),
          ),
        ),
      ],
    );
    addTearDown(container.dispose);

    final GtexSurfaceState<ClubFinanceDTO> state = await container.read(
      clubFinanceProvider(
        const ClubHqRequest(clubId: 'club-1', role: 'club.owner'),
      ).future,
    );

    expect(state, isA<GtexData<ClubFinanceDTO>>());
    expect((state as GtexData<ClubFinanceDTO>).data.balance, 1250);
  });
}

class _FinanceOnlyClubRepository implements IClubHqRepository {
  const _FinanceOnlyClubRepository(this.finance);

  final ClubFinanceDTO finance;

  @override
  Future<ClubFinanceDTO> getFinance(String clubId) async => finance;

  @override
  Future<ClubHqSnapshot> fetchClubHq(String clubId) {
    throw UnimplementedError();
  }

  @override
  Future<ClubAcademyDTO> getAcademy(String clubId) {
    throw UnimplementedError();
  }

  @override
  Future<ClubBrandingDTO> getBranding(String clubId) {
    throw UnimplementedError();
  }

  @override
  Future<ClubDashboardDTO> getDashboard(String clubId) {
    throw UnimplementedError();
  }

  @override
  Future<List<ClubRankingDTO>> getRankings(String clubId) {
    throw UnimplementedError();
  }

  @override
  Future<SquadReadinessDTO> getSquadReadiness(String clubId) {
    throw UnimplementedError();
  }

  @override
  Future<List<SponsorshipDTO>> getSponsorships(String clubId) {
    throw UnimplementedError();
  }

  @override
  Future<ClubStaffDTO> getStaff(String clubId) {
    throw UnimplementedError();
  }

  @override
  Future<List<TrophyDTO>> getTrophies(String clubId) {
    throw UnimplementedError();
  }
}
