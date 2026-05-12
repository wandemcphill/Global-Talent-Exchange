import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';

import 'club_growth_models.dart';

class GtexClubGrowthApi {
  GtexClubGrowthApi({required this.client, required this.fixtures});

  final GteAuthedApi client;
  final GtexClubGrowthFixtures fixtures;

  factory GtexClubGrowthApi.standard({
    required String baseUrl,
    required String? accessToken,
    GteBackendMode mode = GteBackendMode.live,
  }) {
    final GteBackendMode resolvedMode = gteProductionBackendMode(mode);
    return GtexClubGrowthApi(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: resolvedMode),
        transport: GteHttpTransport(),
        accessToken: accessToken,
        mode: resolvedMode,
      ),
      fixtures: GtexClubGrowthFixtures.seed(),
    );
  }

  factory GtexClubGrowthApi.fixture() {
    return GtexClubGrowthApi(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.fixture,
        ),
        transport: GteHttpTransport(),
        accessToken: 'fixture-token',
        mode: GteBackendMode.fixture,
      ),
      fixtures: GtexClubGrowthFixtures.seed(),
    );
  }

  Future<GtexClubGrowthDashboard> fetchDashboard(String clubId) {
    final String encodedClubId = Uri.encodeComponent(clubId);
    return client.withFallback<GtexClubGrowthDashboard>(() async {
      final Map<String, dynamic> payload = await client.getMap(
        '/api/clubs/$encodedClubId/growth',
      );
      return GtexClubGrowthDashboard.fromJson(payload);
    }, () => fixtures.dashboard(clubId));
  }

  Future<GtexStaffContract> offerStaffContract(String clubId, String staffId) {
    final String encodedClubId = Uri.encodeComponent(clubId);
    final String encodedStaffId = Uri.encodeComponent(staffId);
    return client.withFallback<GtexStaffContract>(() async {
      final Object? payload = await client.post(
        '/api/clubs/$encodedClubId/growth/staff/$encodedStaffId/offer',
        body: const <String, Object?>{
          'duration_days': 120,
          'role_scope': 'club',
          'exclusive': true,
        },
      );
      return GtexStaffContract.fromJson(payload);
    }, () => fixtures.offerStaffContract(clubId, staffId));
  }

  Future<GtexStaffContract> acceptStaffContract(
    String clubId,
    String contractId,
  ) {
    final String encodedClubId = Uri.encodeComponent(clubId);
    final String encodedContractId = Uri.encodeComponent(contractId);
    return client.withFallback<GtexStaffContract>(() async {
      final Object? payload = await client.post(
        '/api/clubs/$encodedClubId/growth/staff-contracts/$encodedContractId/accept',
      );
      return GtexStaffContract.fromJson(payload);
    }, () => fixtures.acceptStaffContract(clubId, contractId));
  }

  Future<List<GtexAcademyProspect>> generateProspects(String clubId) {
    final String encodedClubId = Uri.encodeComponent(clubId);
    return client.withFallback<List<GtexAcademyProspect>>(() async {
      final Object? payload = await client.post(
        '/api/clubs/$encodedClubId/growth/academy/generate-prospects',
        body: const <String, Object?>{'count': 3},
      );
      return _prospectsFromList(payload);
    }, () => fixtures.generateProspects(clubId));
  }

  Future<GtexAcademyContractOffer> offerProspectContract(
    String clubId,
    String prospectId,
  ) {
    final String encodedClubId = Uri.encodeComponent(clubId);
    final String encodedProspectId = Uri.encodeComponent(prospectId);
    return client.withFallback<GtexAcademyContractOffer>(() async {
      final Object? payload = await client.post(
        '/api/clubs/$encodedClubId/growth/academy/prospects/$encodedProspectId/offer-contract',
        body: const <String, Object?>{
          'wage_minor': 1000,
          'duration_months': 24,
        },
      );
      return GtexAcademyContractOffer.fromJson(payload);
    }, () => fixtures.offerProspectContract(clubId, prospectId));
  }

  Future<GtexAcademyContractOffer> acceptProspectContract(
    String clubId,
    String offerId,
  ) {
    final String encodedClubId = Uri.encodeComponent(clubId);
    final String encodedOfferId = Uri.encodeComponent(offerId);
    return client.withFallback<GtexAcademyContractOffer>(() async {
      final Object? payload = await client.post(
        '/api/clubs/$encodedClubId/growth/academy/contracts/$encodedOfferId/respond',
        body: const <String, Object?>{'accepted': true},
      );
      return GtexAcademyContractOffer.fromJson(payload);
    }, () => fixtures.acceptProspectContract(clubId, offerId));
  }

  Future<GtexAcademyProspect> promoteProspect(
    String clubId,
    String prospectId,
  ) {
    final String encodedClubId = Uri.encodeComponent(clubId);
    final String encodedProspectId = Uri.encodeComponent(prospectId);
    return client.withFallback<GtexAcademyProspect>(() async {
      final Object? payload = await client.post(
        '/api/clubs/$encodedClubId/growth/academy/prospects/$encodedProspectId/promote',
      );
      return GtexAcademyProspect.fromJson(payload);
    }, () => fixtures.promoteProspect(clubId, prospectId));
  }
}

class GtexClubGrowthFixtures {
  GtexClubGrowthFixtures(this._dashboard, this._pendingOffers);

  GtexClubGrowthDashboard _dashboard;
  final Map<String, String> _pendingOffers;

  static GtexClubGrowthFixtures seed() {
    final DateTime now = DateTime.parse('2026-05-11T12:00:00Z');
    final GtexStaffProfile agent = GtexStaffProfile(
      id: 'staff-agent',
      displayName: 'Launch Negotiation Agent',
      staffType: 'agent',
      rarity: 'standard',
      skills: const <String>['negotiation', 'contract handling'],
      salaryMinor: 24000,
      commissionBps: 350,
      rating: 62,
      active: true,
      metadata: const <String, Object?>{},
    );
    final GtexStaffProfile scout = GtexStaffProfile(
      id: 'staff-scout',
      displayName: 'Regional Academy Scout',
      staffType: 'scout',
      rarity: 'standard',
      skills: const <String>['scouting', 'academy growth'],
      salaryMinor: 18000,
      commissionBps: 100,
      rating: 58,
      active: true,
      metadata: const <String, Object?>{},
    );
    return GtexClubGrowthFixtures(
      GtexClubGrowthDashboard(
        clubId: 'fixture-club',
        staffMarket: <GtexStaffProfile>[agent, scout],
        staffContracts: const <GtexStaffContract>[],
        staffEffects: const <String, int>{
          'scout_quality': 0,
          'training_bonus': 0,
          'negotiation_bonus': 0,
        },
        academyProfile: GtexAcademyProfile(
          id: 'academy-fixture',
          clubId: 'fixture-club',
          level: 1,
          investmentMinor: 0,
          generationCooldownUntil: null,
          metadata: const <String, Object?>{},
          updatedAt: now,
        ),
        academyProspects: const <GtexAcademyProspect>[],
        sponsorship: const GtexSponsorshipClubSummary(
          activeContracts: 1,
          pendingContracts: 0,
          settledPayoutMinor: 25000,
          outstandingPayoutMinor: 75000,
          openLeads: 1,
        ),
        updatedAt: now,
      ),
      <String, String>{},
    );
  }

  Future<GtexClubGrowthDashboard> dashboard(String clubId) async => _dashboard;

  Future<GtexStaffContract> offerStaffContract(
    String clubId,
    String staffId,
  ) async {
    final GtexStaffProfile staff = _dashboard.staffMarket.firstWhere(
      (GtexStaffProfile item) => item.id == staffId,
      orElse: () => _dashboard.staffMarket.first,
    );
    final GtexStaffContract contract = GtexStaffContract(
      id: 'contract-${staff.id}',
      clubId: clubId,
      staffProfile: staff,
      status: 'offered',
      salaryMinor: staff.salaryMinor,
      commissionBps: staff.commissionBps,
      durationDays: 120,
      roleScope: 'club',
      exclusive: true,
      startedAt: null,
      endsAt: null,
      acceptedAt: null,
      terminatedAt: null,
      updatedAt: DateTime.now().toUtc(),
    );
    _dashboard = _replaceContracts(<GtexStaffContract>[
      ..._dashboard.staffContracts,
      contract,
    ]);
    return contract;
  }

  Future<GtexStaffContract> acceptStaffContract(
    String clubId,
    String contractId,
  ) async {
    final DateTime now = DateTime.now().toUtc();
    final List<GtexStaffContract> next = _dashboard.staffContracts
        .map((GtexStaffContract item) {
          if (item.id != contractId) {
            return item;
          }
          return GtexStaffContract(
            id: item.id,
            clubId: item.clubId,
            staffProfile: item.staffProfile,
            status: 'active',
            salaryMinor: item.salaryMinor,
            commissionBps: item.commissionBps,
            durationDays: item.durationDays,
            roleScope: item.roleScope,
            exclusive: item.exclusive,
            startedAt: now,
            endsAt: now.add(Duration(days: item.durationDays)),
            acceptedAt: now,
            terminatedAt: item.terminatedAt,
            updatedAt: now,
          );
        })
        .toList(growable: false);
    _dashboard = _replaceContracts(next);
    return next.firstWhere((GtexStaffContract item) => item.id == contractId);
  }

  Future<List<GtexAcademyProspect>> generateProspects(String clubId) async {
    final int offset = _dashboard.academyProspects.length;
    final DateTime now = DateTime.now().toUtc();
    final List<GtexAcademyProspect>
    generated = List<GtexAcademyProspect>.generate(
      3,
      (int index) => GtexAcademyProspect(
        id: 'prospect-${offset + index + 1}',
        clubId: clubId,
        displayName:
            'Academy Regen ${(offset + index + 1).toString().padLeft(3, '0')}',
        nationality: 'NG',
        position: const <String>['GK', 'CB', 'CM', 'ST'][index % 4],
        age: 16,
        personality: const <String, Object?>{
          'temperament': 'focused',
          'training_style': 'methodical',
        },
        currentAbility: 38 + index,
        potential: 72 + index,
        portraitAssetRef: null,
        status: 'discovered',
        metadata: const <String, Object?>{
          'portrait_policy': 'newgen_bank_only',
        },
        updatedAt: now,
      ),
    );
    _dashboard = _replaceProspects(<GtexAcademyProspect>[
      ...generated,
      ..._dashboard.academyProspects,
    ]);
    return generated;
  }

  Future<GtexAcademyContractOffer> offerProspectContract(
    String clubId,
    String prospectId,
  ) async {
    final String offerId = 'offer-$prospectId';
    _pendingOffers[offerId] = prospectId;
    _dashboard = _replaceProspectStatus(prospectId, 'contract_offered');
    return GtexAcademyContractOffer(
      id: offerId,
      clubId: clubId,
      prospectId: prospectId,
      status: 'offered',
      wageMinor: 1000,
      durationMonths: 24,
      responseReason: null,
      updatedAt: DateTime.now().toUtc(),
    );
  }

  Future<GtexAcademyContractOffer> acceptProspectContract(
    String clubId,
    String offerId,
  ) async {
    final String prospectId =
        _pendingOffers[offerId] ?? offerId.replaceFirst('offer-', '');
    _dashboard = _replaceProspectStatus(prospectId, 'youth_signed');
    return GtexAcademyContractOffer(
      id: offerId,
      clubId: clubId,
      prospectId: prospectId,
      status: 'accepted',
      wageMinor: 1000,
      durationMonths: 24,
      responseReason: null,
      updatedAt: DateTime.now().toUtc(),
    );
  }

  Future<GtexAcademyProspect> promoteProspect(
    String clubId,
    String prospectId,
  ) async {
    _dashboard = _replaceProspectStatus(prospectId, 'promoted_to_senior');
    return _dashboard.academyProspects.firstWhere(
      (GtexAcademyProspect item) => item.id == prospectId,
    );
  }

  GtexClubGrowthDashboard _replaceContracts(List<GtexStaffContract> contracts) {
    return GtexClubGrowthDashboard(
      clubId: _dashboard.clubId,
      staffMarket: _dashboard.staffMarket,
      staffContracts: contracts,
      staffEffects: <String, int>{
        'scout_quality': contracts
            .where(
              (GtexStaffContract item) =>
                  item.active && item.staffProfile.staffType == 'scout',
            )
            .fold<int>(
              0,
              (int total, GtexStaffContract item) =>
                  total + item.staffProfile.rating,
            ),
        'training_bonus': 0,
        'negotiation_bonus': contracts
            .where(
              (GtexStaffContract item) =>
                  item.active && item.staffProfile.staffType == 'agent',
            )
            .fold<int>(
              0,
              (int total, GtexStaffContract item) =>
                  total + item.staffProfile.rating,
            ),
      },
      academyProfile: _dashboard.academyProfile,
      academyProspects: _dashboard.academyProspects,
      sponsorship: _dashboard.sponsorship,
      updatedAt: DateTime.now().toUtc(),
    );
  }

  GtexClubGrowthDashboard _replaceProspects(
    List<GtexAcademyProspect> prospects,
  ) {
    return GtexClubGrowthDashboard(
      clubId: _dashboard.clubId,
      staffMarket: _dashboard.staffMarket,
      staffContracts: _dashboard.staffContracts,
      staffEffects: _dashboard.staffEffects,
      academyProfile: _dashboard.academyProfile,
      academyProspects: prospects,
      sponsorship: _dashboard.sponsorship,
      updatedAt: DateTime.now().toUtc(),
    );
  }

  GtexClubGrowthDashboard _replaceProspectStatus(
    String prospectId,
    String status,
  ) {
    return _replaceProspects(
      _dashboard.academyProspects
          .map((GtexAcademyProspect item) {
            if (item.id != prospectId) {
              return item;
            }
            return GtexAcademyProspect(
              id: item.id,
              clubId: item.clubId,
              displayName: item.displayName,
              nationality: item.nationality,
              position: item.position,
              age: item.age,
              personality: item.personality,
              currentAbility: item.currentAbility,
              potential: item.potential,
              portraitAssetRef: item.portraitAssetRef,
              status: status,
              metadata: item.metadata,
              updatedAt: DateTime.now().toUtc(),
            );
          })
          .toList(growable: false),
    );
  }
}

List<GtexAcademyProspect> _prospectsFromList(Object? payload) {
  if (payload is! List) {
    return const <GtexAcademyProspect>[];
  }
  return payload.map(GtexAcademyProspect.fromJson).toList(growable: false);
}
