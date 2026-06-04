import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/core/theme/app_theme.dart';
import 'package:gte_frontend/features/club/club_screen.dart';
import 'package:gte_frontend/features/club/data/club_hq_repository.dart';
import 'package:gte_frontend/features/club/domain/club_hq_models.dart';
import 'package:gte_frontend/features/club/providers/club_hq_providers.dart';

void main() {
  testWidgets('renders production Club HQ sections from backend data', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1280, 2800);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          clubHqRepositoryProvider.overrideWithValue(
            _FakeClubHqRepository(_clubSnapshot(balance: 4200000)),
          ),
        ],
        child: MaterialApp(
          theme: AppTheme.dark(),
          home: const Scaffold(
            body: ClubScreen(clubId: 'club-1', role: 'club.owner'),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Club HQ'), findsOneWidget);
    expect(find.text('Atlas Borough FC'), findsWidgets);
    expect(find.text('Public Profile'), findsOneWidget);
    expect(find.text('Finance'), findsOneWidget);
    expect(find.text('Squad Readiness'), findsOneWidget);
    expect(find.text('Academy'), findsOneWidget);
    expect(find.text('Staff'), findsOneWidget);
    expect(find.text('Sponsorships'), findsOneWidget);
    expect(find.text('Branding'), findsOneWidget);

    await tester.drag(
      find.byKey(const Key('club-hq-dashboard')),
      const Offset(0, -1200),
    );
    await tester.pumpAndSettle();

    expect(find.text('Trophies'), findsOneWidget);
    expect(find.text('Rankings'), findsOneWidget);
  });

  testWidgets('renders blocked finance balance when backend balance is null', (
    WidgetTester tester,
  ) async {
    tester.view.physicalSize = const Size(1280, 2200);
    tester.view.devicePixelRatio = 1;
    addTearDown(() {
      tester.view.resetPhysicalSize();
      tester.view.resetDevicePixelRatio();
    });

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          clubHqRepositoryProvider.overrideWithValue(
            _FakeClubHqRepository(_clubSnapshot()),
          ),
        ],
        child: MaterialApp(
          theme: AppTheme.dark(),
          home: const Scaffold(
            body: ClubScreen(clubId: 'club-1', role: 'club.owner'),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.text('Balance data unavailable - sync in progress.'),
      findsOneWidget,
    );
    expect(
      find.byKey(const Key('club-finance-balance-blocked')),
      findsOneWidget,
    );
    expect(find.textContaining(r'$0'), findsNothing);
  });
}

class _FakeClubHqRepository implements IClubHqRepository {
  const _FakeClubHqRepository(this.snapshot);

  final ClubHqSnapshot snapshot;

  @override
  Future<ClubHqSnapshot> fetchClubHq(String clubId) async => snapshot;

  @override
  Future<ClubAcademyDTO> getAcademy(String clubId) async => snapshot.academy;

  @override
  Future<ClubBrandingDTO> getBranding(String clubId) async => snapshot.branding;

  @override
  Future<ClubDashboardDTO> getDashboard(String clubId) async =>
      snapshot.dashboard;

  @override
  Future<ClubFinanceDTO> getFinance(String clubId) async => snapshot.finance;

  @override
  Future<List<ClubRankingDTO>> getRankings(String clubId) async =>
      snapshot.rankings;

  @override
  Future<SquadReadinessDTO> getSquadReadiness(String clubId) async =>
      snapshot.readiness;

  @override
  Future<List<SponsorshipDTO>> getSponsorships(String clubId) async =>
      snapshot.sponsorships;

  @override
  Future<ClubStaffDTO> getStaff(String clubId) async => snapshot.staff;

  @override
  Future<List<TrophyDTO>> getTrophies(String clubId) async => snapshot.trophies;
}

ClubHqSnapshot _clubSnapshot({double? balance}) {
  return ClubHqSnapshot(
    dashboard: const ClubDashboardDTO(
      clubId: 'club-1',
      name: 'Atlas Borough FC',
      league: 'GTEX Premier',
      division: 'Division One',
      foundedYear: 2026,
      totalSquadValue: 18500000,
      activeCompetitions: 3,
      alerts: <String>['License review synced'],
    ),
    finance: ClubFinanceDTO(
      clubId: 'club-1',
      balance: balance,
      revenue: 800000,
      expenses: 520000,
      transferBudget: 2100000,
      wages: 360000,
      lastSyncedAt: DateTime.utc(2026, 6, 1),
    ),
    readiness: const SquadReadinessDTO(
      eligibleCount: 19,
      injuredCount: 2,
      suspendedCount: 1,
      availableForNextFixture: 18,
      readinessScore: 86,
    ),
    academy: const ClubAcademyDTO(
      facilitiesRating: 88,
      players: <AcademyPlayerDTO>[
        AcademyPlayerDTO(
          id: 'a-1',
          name: 'Musa Bello',
          position: 'CM',
          age: 17,
          status: 'Promotion watch',
        ),
      ],
    ),
    staff: ClubStaffDTO(
      members: <StaffMemberDTO>[
        StaffMemberDTO(
          role: 'Head Coach',
          name: 'Ada Nwosu',
          contractEnd: DateTime.utc(2027, 6, 30),
          status: 'Active',
        ),
      ],
    ),
    sponsorships: <SponsorshipDTO>[
      SponsorshipDTO(
        id: 'sp-1',
        sponsor: 'Northline Bank',
        value: 900000,
        endDate: DateTime.utc(2027, 5, 1),
        status: 'active',
      ),
    ],
    branding: const ClubBrandingDTO(
      badge: 'https://cdn.example/atlas.png',
      colors: <String>['green', 'gold'],
      kit: 'Home 2026',
      assets: <String>['badge', 'kit'],
    ),
    trophies: const <TrophyDTO>[
      TrophyDTO(
        id: 't-1',
        name: 'City Shield',
        competition: 'Regional Cup',
        season: '2025',
        type: 'cup',
      ),
    ],
    rankings: const <ClubRankingDTO>[
      ClubRankingDTO(
        rank: 4,
        previousRank: 6,
        points: 74,
        division: 'Division One',
      ),
    ],
  );
}
