import 'gte_api_repository.dart';
import 'gte_authed_api.dart';
import 'gte_http_transport.dart';
import '../models/sponsorship_admin_models.dart';

class SponsorshipAdminApi {
  SponsorshipAdminApi({
    required this.client,
    required this.fixtures,
  });

  final GteAuthedApi client;
  final _SponsorshipFixtures fixtures;

  factory SponsorshipAdminApi.standard({
    required String baseUrl,
    required String? accessToken,
    GteBackendMode mode = GteBackendMode.liveThenFixture,
  }) {
    return SponsorshipAdminApi(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: mode),
        transport: GteHttpTransport(),
        accessToken: accessToken,
        mode: mode,
      ),
      fixtures: _SponsorshipFixtures.seed(),
    );
  }

  factory SponsorshipAdminApi.fixture() {
    return SponsorshipAdminApi(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.fixture,
        ),
        transport: GteHttpTransport(),
        accessToken: 'fixture-token',
        mode: GteBackendMode.fixture,
      ),
      fixtures: _SponsorshipFixtures.seed(),
    );
  }

  Future<List<SponsorshipPackageView>> listPackages() {
    return client.withFallback<List<SponsorshipPackageView>>(
      () async {
        final List<dynamic> payload =
            await client.getList('/admin/sponsorship/packages');
        return payload
            .map(SponsorshipPackageView.fromJson)
            .toList(growable: false);
      },
      fixtures.packages,
    );
  }

  Future<List<SponsorshipContractView>> listClubContracts(String clubId) {
    return client.withFallback<List<SponsorshipContractView>>(
      () async {
        final List<dynamic> payload = await client.getList(
          '/sponsorship/clubs/$clubId/contracts',
          auth: false,
        );
        return payload
            .map(SponsorshipContractView.fromJson)
            .toList(growable: false);
      },
      () async => fixtures.contractsForClub(clubId),
    );
  }

  Future<SponsorshipContractView> reviewContract({
    required String contractId,
    required String action,
    String? resolutionNote,
  }) {
    return client.withFallback<SponsorshipContractView>(
      () async {
        final Object? payload = await client.request(
          'POST',
          '/admin/sponsorship/contracts/$contractId/review',
          body: <String, Object?>{
            'action': action,
            'resolution_note': resolutionNote ?? '',
          },
        );
        return SponsorshipContractView.fromJson(payload);
      },
      () async => fixtures.reviewContract(contractId, action),
    );
  }
}

class _SponsorshipFixtures {
  _SponsorshipFixtures(this._packages, this._contracts);

  final List<SponsorshipPackageView> _packages;
  final List<SponsorshipContractView> _contracts;

  static _SponsorshipFixtures seed() {
    return _SponsorshipFixtures(
      <SponsorshipPackageView>[
        SponsorshipPackageView(
          id: 'pkg-1',
          code: 'gold',
          name: 'Gold visibility package',
          assetType: 'stadium',
          baseAmountMinor: 2500000,
          currency: 'USD',
          defaultDurationMonths: 12,
          payoutSchedule: 'quarterly',
          description: 'High visibility inventory rights.',
          isActive: true,
        ),
      ],
      <SponsorshipContractView>[
        SponsorshipContractView(
          id: 'contract-1',
          clubId: 'club-1',
          packageId: 'pkg-1',
          assetType: 'stadium',
          sponsorName: 'Prime Sportswear',
          status: 'pending',
          contractAmountMinor: 2500000,
          currency: 'USD',
          durationMonths: 12,
          payoutSchedule: 'quarterly',
          startAt: DateTime.parse('2026-04-01T00:00:00Z'),
          endAt: DateTime.parse('2027-03-31T00:00:00Z'),
          moderationRequired: true,
          moderationStatus: 'pending',
          customCopy: null,
          customLogoUrl: null,
          performanceBonusMinor: 0,
          settledAmountMinor: 0,
          outstandingAmountMinor: 2500000,
          createdAt: DateTime.parse('2026-03-12T00:00:00Z'),
          updatedAt: DateTime.parse('2026-03-12T00:00:00Z'),
        ),
      ],
    );
  }

  Future<List<SponsorshipPackageView>> packages() async =>
      List<SponsorshipPackageView>.of(_packages, growable: false);

  Future<List<SponsorshipContractView>> contractsForClub(String clubId) async =>
      List<SponsorshipContractView>.of(_contracts, growable: false);

  Future<SponsorshipContractView> reviewContract(
      String contractId, String action) async {
    final int index = _contracts
        .indexWhere((SponsorshipContractView item) => item.id == contractId);
    if (index == -1) {
      return _contracts.first;
    }
    final SponsorshipContractView updated = SponsorshipContractView(
      id: _contracts[index].id,
      clubId: _contracts[index].clubId,
      packageId: _contracts[index].packageId,
      assetType: _contracts[index].assetType,
      sponsorName: _contracts[index].sponsorName,
      status: action == 'approve' ? 'active' : 'rejected',
      contractAmountMinor: _contracts[index].contractAmountMinor,
      currency: _contracts[index].currency,
      durationMonths: _contracts[index].durationMonths,
      payoutSchedule: _contracts[index].payoutSchedule,
      startAt: _contracts[index].startAt,
      endAt: _contracts[index].endAt,
      moderationRequired: _contracts[index].moderationRequired,
      moderationStatus: action,
      customCopy: _contracts[index].customCopy,
      customLogoUrl: _contracts[index].customLogoUrl,
      performanceBonusMinor: _contracts[index].performanceBonusMinor,
      settledAmountMinor: _contracts[index].settledAmountMinor,
      outstandingAmountMinor: _contracts[index].outstandingAmountMinor,
      createdAt: _contracts[index].createdAt,
      updatedAt: DateTime.now().toUtc(),
    );
    _contracts[index] = updated;
    return updated;
  }
}
