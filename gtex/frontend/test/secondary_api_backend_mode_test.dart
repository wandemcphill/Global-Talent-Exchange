import 'package:flutter_test/flutter_test.dart';

import 'package:gte_frontend/data/admin_engine_api.dart';
import 'package:gte_frontend/data/admin_finance_api.dart';
import 'package:gte_frontend/data/agent_marketplace_api.dart';
import 'package:gte_frontend/data/club_api.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/data/community_api.dart';
import 'package:gte_frontend/data/competition_api.dart';
import 'package:gte_frontend/data/competition_control_repository.dart';
import 'package:gte_frontend/data/creator_api.dart';
import 'package:gte_frontend/data/creator_application_api.dart';
import 'package:gte_frontend/data/discovery_api.dart';
import 'package:gte_frontend/data/dispute_engine_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/hosted_competition_api.dart';
import 'package:gte_frontend/data/manager_market_repository.dart';
import 'package:gte_frontend/data/moderation_api.dart';
import 'package:gte_frontend/data/national_team_api.dart';
import 'package:gte_frontend/data/notification_settings_api.dart';
import 'package:gte_frontend/data/policy_admin_api.dart';
import 'package:gte_frontend/data/referral_api.dart';
import 'package:gte_frontend/data/regen_universe_api.dart';
import 'package:gte_frontend/data/risk_ops_api.dart';
import 'package:gte_frontend/data/sponsorship_admin_api.dart';
import 'package:gte_frontend/data/story_feed_api.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_api_repository.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_fixture_repository.dart';
import 'package:gte_frontend/features/club_identity/jerseys/data/club_identity_repository.dart';
import 'package:gte_frontend/features/club_identity/reputation/data/reputation_repository.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/trophy_cabinet_api_repository.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/trophy_cabinet_repository.dart';
import 'package:gte_frontend/features/club_sale_market/data/club_sale_market_repository.dart';
import 'package:gte_frontend/shared/auth/auth_identity_store.dart';

void main() {
  test('secondary APIs clamp liveThenFixture down to live', () {
    final MemoryAuthSessionStore authSessionStore = MemoryAuthSessionStore();

    final AdminEngineApi adminEngineApi = AdminEngineApi.standard(
      baseUrl: 'https://example.test',
      accessToken: 'token',
      mode: GteBackendMode.liveThenFixture,
    );
    _expectAuthedApiLive(adminEngineApi.client);

    final AdminFinanceApi adminFinanceApi = AdminFinanceApi.standard(
      baseUrl: 'https://example.test',
      accessToken: 'token',
      mode: GteBackendMode.liveThenFixture,
    );
    _expectAuthedApiLive(adminFinanceApi.client);

    final AgentMarketplaceApi agentMarketplaceApi = AgentMarketplaceApi(
      config: const GteRepositoryConfig(
        baseUrl: 'https://example.test',
        mode: GteBackendMode.liveThenFixture,
      ),
      transport: _NoopTransport(),
      accessToken: 'token',
      mode: GteBackendMode.liveThenFixture,
    );
    expect(agentMarketplaceApi.config.mode, GteBackendMode.live);
    expect(agentMarketplaceApi.mode, GteBackendMode.live);

    final ClubApi clubApi = ClubApi.standard(
      baseUrl: 'https://example.test',
      accessToken: 'token',
      mode: GteBackendMode.liveThenFixture,
    );
    expect(clubApi.config.mode, GteBackendMode.live);

    final ClubOpsApi clubOpsApi = ClubOpsApi.standard(
      baseUrl: 'https://example.test',
      accessToken: 'token',
      authSessionStore: authSessionStore,
      mode: GteBackendMode.liveThenFixture,
    );
    expect(clubOpsApi.config.mode, GteBackendMode.live);

    final CommunityApi communityApi = CommunityApi.standard(
      baseUrl: 'https://example.test',
      accessToken: 'token',
      mode: GteBackendMode.liveThenFixture,
    );
    _expectAuthedApiLive(communityApi.client);

    final CompetitionApi competitionApi = CompetitionApi.standard(
      baseUrl: 'https://example.test',
      accessToken: 'token',
      mode: GteBackendMode.liveThenFixture,
    );
    expect(competitionApi.config.mode, GteBackendMode.live);

    final CompetitionControlRepository competitionControlRepository =
        CompetitionControlRepository.standard(
          baseUrl: 'https://example.test',
          accessToken: 'token',
          mode: GteBackendMode.liveThenFixture,
        );
    expect(competitionControlRepository.config.mode, GteBackendMode.live);

    final CreatorApi creatorApi = CreatorApi.standard(
      baseUrl: 'https://example.test',
      accessToken: 'token',
      mode: GteBackendMode.liveThenFixture,
    );
    _expectAuthedApiLive(creatorApi.client);

    final CreatorApplicationApi creatorApplicationApi =
        CreatorApplicationApi.standard(
          baseUrl: 'https://example.test',
          accessToken: 'token',
          mode: GteBackendMode.liveThenFixture,
        );
    _expectAuthedApiLive(creatorApplicationApi.client);
    expect(creatorApplicationApi.mode, GteBackendMode.live);

    final DiscoveryApi discoveryApi = DiscoveryApi.standard(
      baseUrl: 'https://example.test',
      accessToken: 'token',
      mode: GteBackendMode.liveThenFixture,
    );
    _expectAuthedApiLive(discoveryApi.client);

    final DisputeEngineApi disputeEngineApi = DisputeEngineApi.standard(
      baseUrl: 'https://example.test',
      accessToken: 'token',
      mode: GteBackendMode.liveThenFixture,
    );
    _expectAuthedApiLive(disputeEngineApi.client);

    final HostedCompetitionApi hostedCompetitionApi =
        HostedCompetitionApi.standard(
          baseUrl: 'https://example.test',
          accessToken: 'token',
          mode: GteBackendMode.liveThenFixture,
        );
    _expectAuthedApiLive(hostedCompetitionApi.client);

    final ManagerMarketRepository managerMarketRepository =
        ManagerMarketRepository.standard(
          baseUrl: 'https://example.test',
          accessToken: 'token',
          mode: GteBackendMode.liveThenFixture,
        );
    expect(managerMarketRepository.config.mode, GteBackendMode.live);

    final ModerationApi moderationApi = ModerationApi.standard(
      baseUrl: 'https://example.test',
      accessToken: 'token',
      mode: GteBackendMode.liveThenFixture,
    );
    _expectAuthedApiLive(moderationApi.client);

    final NationalTeamApi nationalTeamApi = NationalTeamApi.standard(
      baseUrl: 'https://example.test',
      accessToken: 'token',
      mode: GteBackendMode.liveThenFixture,
    );
    _expectAuthedApiLive(nationalTeamApi.client);

    final NotificationSettingsApi notificationSettingsApi =
        NotificationSettingsApi.standard(
          baseUrl: 'https://example.test',
          accessToken: 'token',
          mode: GteBackendMode.liveThenFixture,
        );
    _expectAuthedApiLive(notificationSettingsApi.client);

    final PolicyAdminApi policyAdminApi = PolicyAdminApi.standard(
      baseUrl: 'https://example.test',
      accessToken: 'token',
      mode: GteBackendMode.liveThenFixture,
    );
    _expectAuthedApiLive(policyAdminApi.client);

    final ReferralApi referralApi = ReferralApi.standard(
      baseUrl: 'https://example.test',
      accessToken: 'token',
      authSessionStore: authSessionStore,
      mode: GteBackendMode.liveThenFixture,
    );
    _expectAuthedApiLive(referralApi.client);
    expect(referralApi.mode, GteBackendMode.live);

    final RegenUniverseApi regenUniverseApi = RegenUniverseApi.standard(
      baseUrl: 'https://example.test',
      mode: GteBackendMode.liveThenFixture,
    );
    _expectAuthedApiLive(regenUniverseApi.client);

    final RiskOpsApi riskOpsApi = RiskOpsApi.standard(
      baseUrl: 'https://example.test',
      accessToken: 'token',
      mode: GteBackendMode.liveThenFixture,
    );
    _expectAuthedApiLive(riskOpsApi.client);

    final SponsorshipAdminApi sponsorshipAdminApi =
        SponsorshipAdminApi.standard(
          baseUrl: 'https://example.test',
          accessToken: 'token',
          mode: GteBackendMode.liveThenFixture,
        );
    _expectAuthedApiLive(sponsorshipAdminApi.client);

    final StoryFeedApi storyFeedApi = StoryFeedApi.standard(
      baseUrl: 'https://example.test',
      accessToken: 'token',
      mode: GteBackendMode.liveThenFixture,
    );
    _expectAuthedApiLive(storyFeedApi.client);

    final DynastyApiRepository dynastyApiRepository =
        DynastyApiRepository.standard(
          baseUrl: 'https://example.test',
          mode: GteBackendMode.liveThenFixture,
        );
    expect(dynastyApiRepository.config.mode, GteBackendMode.live);

    final ClubIdentityApiRepository clubIdentityApiRepository =
        ClubIdentityApiRepository.standard(
          baseUrl: 'https://example.test',
          mode: GteBackendMode.liveThenFixture,
          transport: _NoopTransport(),
        );
    expect(clubIdentityApiRepository.config.mode, GteBackendMode.live);

    final ReputationApiRepository reputationApiRepository =
        ReputationApiRepository.standard(
          baseUrl: 'https://example.test',
          mode: GteBackendMode.liveThenFixture,
        );
    expect(reputationApiRepository.config.mode, GteBackendMode.live);

    final TrophyCabinetApiRepository trophyCabinetApiRepository =
        TrophyCabinetApiRepository.standard(
          baseUrl: 'https://example.test',
          mode: GteBackendMode.liveThenFixture,
        );
    expect(trophyCabinetApiRepository.config.mode, GteBackendMode.live);
  });

  test('secondary APIs preserve explicit fixture mode', () {
    final HostedCompetitionApi hostedCompetitionApi =
        HostedCompetitionApi.standard(
          baseUrl: 'https://example.test',
          accessToken: null,
          mode: GteBackendMode.fixture,
        );
    expect(hostedCompetitionApi.client.mode, GteBackendMode.fixture);
    expect(hostedCompetitionApi.client.config.mode, GteBackendMode.fixture);

    final CompetitionApi competitionApi = CompetitionApi.standard(
      baseUrl: 'https://example.test',
      accessToken: 'token',
      mode: GteBackendMode.fixture,
    );
    expect(competitionApi.config.mode, GteBackendMode.fixture);

    final AgentMarketplaceApi agentMarketplaceApi = AgentMarketplaceApi(
      config: const GteRepositoryConfig(
        baseUrl: 'https://example.test',
        mode: GteBackendMode.fixture,
      ),
      transport: _NoopTransport(),
      accessToken: 'token',
      mode: GteBackendMode.fixture,
    );
    expect(agentMarketplaceApi.config.mode, GteBackendMode.fixture);
    expect(agentMarketplaceApi.mode, GteBackendMode.fixture);
  });

  test(
    'clamped secondary APIs surface live failures instead of fixture data',
    () async {
      const _StatusTransport unavailable = _StatusTransport(
        statusCode: 503,
        body: <String, Object?>{'detail': 'backend offline'},
      );

      final AdminEngineApi adminEngineApi = AdminEngineApi.standard(
        baseUrl: 'https://example.test',
        accessToken: 'token',
        mode: GteBackendMode.liveThenFixture,
        transport: unavailable,
      );
      await _expectUnavailable(adminEngineApi.listFeatureFlags());

      final AdminFinanceApi adminFinanceApi = AdminFinanceApi.standard(
        baseUrl: 'https://example.test',
        accessToken: 'token',
        mode: GteBackendMode.liveThenFixture,
        transport: unavailable,
      );
      await _expectUnavailable(adminFinanceApi.fetchControlTower());

      final CreatorApplicationApi creatorApplicationApi =
          CreatorApplicationApi.standard(
            baseUrl: 'https://example.test',
            accessToken: 'token',
            mode: GteBackendMode.liveThenFixture,
            client: GteAuthedApi(
              config: const GteRepositoryConfig(
                baseUrl: 'https://example.test',
                mode: GteBackendMode.live,
              ),
              transport: unavailable,
              accessToken: 'token',
              mode: GteBackendMode.live,
            ),
          );
      await _expectUnavailable(creatorApplicationApi.fetchVerificationStatus());

      final HostedCompetitionApi api = HostedCompetitionApi.standard(
        baseUrl: 'https://example.test',
        accessToken: null,
        mode: GteBackendMode.liveThenFixture,
        transport: unavailable,
      );

      await expectLater(
        api.listTemplates(),
        throwsA(
          isA<GteApiException>().having(
            (GteApiException error) => error.type,
            'type',
            GteApiErrorType.unavailable,
          ),
        ),
      );
    },
  );

  test(
    'raw club surface repositories fail closed in liveThenFixture mode',
    () async {
      const GteRepositoryConfig config = GteRepositoryConfig(
        baseUrl: 'https://example.test',
        mode: GteBackendMode.liveThenFixture,
      );
      const _StatusTransport transport = _StatusTransport(
        statusCode: 503,
        body: <String, Object?>{'detail': 'backend offline'},
      );

      final ClubIdentityApiRepository clubIdentityRepository =
          ClubIdentityApiRepository(
            config: config,
            transport: transport,
            fixtures: MockClubIdentityRepository(),
          );
      await _expectUnavailable(clubIdentityRepository.fetchIdentity('club-1'));

      final ReputationApiRepository reputationRepository =
          ReputationApiRepository(
            config: config,
            transport: transport,
            fixtures: FixtureReputationRepository(),
          );
      await _expectUnavailable(reputationRepository.fetchOverview('club-1'));

      final DynastyApiRepository dynastyRepository = DynastyApiRepository(
        config: config,
        transport: transport,
        fixtures: DynastyFixtureRepository(),
      );
      await _expectUnavailable(dynastyRepository.fetchDynastyProfile('club-1'));

      final TrophyCabinetApiRepository trophyRepository =
          TrophyCabinetApiRepository(
            config: config,
            transport: transport,
            fixtures: StubTrophyCabinetRepository(),
          );
      await _expectUnavailable(
        trophyRepository.fetchTrophyCabinet(clubId: 'club-1'),
      );

      final ClubSaleMarketApiRepository saleMarketRepository =
          ClubSaleMarketApiRepository(
            client: GteAuthedApi(
              config: config,
              transport: transport,
              accessToken: 'token',
              mode: GteBackendMode.liveThenFixture,
            ),
          );
      await _expectUnavailable(saleMarketRepository.fetchValuation('club-1'));
    },
  );
}

void _expectAuthedApiLive(GteAuthedApi client) {
  expect(client.mode, GteBackendMode.live);
  expect(client.config.mode, GteBackendMode.live);
}

Future<void> _expectUnavailable(Future<dynamic> operation) async {
  await expectLater(
    operation,
    throwsA(
      isA<GteApiException>().having(
        (GteApiException error) => error.type,
        'type',
        GteApiErrorType.unavailable,
      ),
    ),
  );
}

class _NoopTransport implements GteTransport {
  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    return const GteTransportResponse(statusCode: 200, body: <Object?>[]);
  }
}

class _StatusTransport implements GteTransport {
  const _StatusTransport({required this.statusCode, required this.body});

  final int statusCode;
  final Object? body;

  @override
  Future<GteTransportResponse> send(GteTransportRequest request) async {
    return GteTransportResponse(statusCode: statusCode, body: body);
  }
}
