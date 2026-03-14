import 'gte_api_repository.dart';
import 'gte_authed_api.dart';
import 'gte_http_transport.dart';
import '../models/policy_admin_models.dart';

class PolicyAdminApi {
  PolicyAdminApi({
    required this.client,
    required this.fixtures,
  });

  final GteAuthedApi client;
  final _PolicyAdminFixtures fixtures;

  factory PolicyAdminApi.standard({
    required String baseUrl,
    required String? accessToken,
    GteBackendMode mode = GteBackendMode.liveThenFixture,
  }) {
    return PolicyAdminApi(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: mode),
        transport: GteHttpTransport(),
        accessToken: accessToken,
        mode: mode,
      ),
      fixtures: _PolicyAdminFixtures.seed(),
    );
  }

  factory PolicyAdminApi.fixture() {
    return PolicyAdminApi(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.fixture,
        ),
        transport: GteHttpTransport(),
        accessToken: 'fixture-token',
        mode: GteBackendMode.fixture,
      ),
      fixtures: _PolicyAdminFixtures.seed(),
    );
  }

  Future<List<CountryFeaturePolicy>> listCountryPolicies() {
    return client.withFallback<List<CountryFeaturePolicy>>(
      () async {
        final List<dynamic> payload =
            await client.getList('/admin/policies/country-policies');
        return payload
            .map(CountryFeaturePolicy.fromJson)
            .toList(growable: false);
      },
      fixtures.policies,
    );
  }

  Future<CountryFeaturePolicy> upsertCountryPolicy({
    required String countryCode,
    String bucketType = 'default',
    bool depositsEnabled = true,
    bool marketTradingEnabled = true,
    bool platformRewardWithdrawalsEnabled = true,
    bool userHostedGiftWithdrawalsEnabled = false,
    bool gtexCompetitionGiftWithdrawalsEnabled = false,
    bool nationalRewardWithdrawalsEnabled = false,
    int oneTimeRegionChangeAfterDays = 180,
    bool active = true,
  }) {
    return client.withFallback<CountryFeaturePolicy>(
      () async {
        final Object? payload = await client.request(
          'POST',
          '/admin/policies/country-policies',
          body: <String, Object?>{
            'country_code': countryCode,
            'bucket_type': bucketType,
            'deposits_enabled': depositsEnabled,
            'market_trading_enabled': marketTradingEnabled,
            'platform_reward_withdrawals_enabled':
                platformRewardWithdrawalsEnabled,
            'user_hosted_gift_withdrawals_enabled':
                userHostedGiftWithdrawalsEnabled,
            'gtex_competition_gift_withdrawals_enabled':
                gtexCompetitionGiftWithdrawalsEnabled,
            'national_reward_withdrawals_enabled':
                nationalRewardWithdrawalsEnabled,
            'one_time_region_change_after_days':
                oneTimeRegionChangeAfterDays,
            'active': active,
          },
        );
        return CountryFeaturePolicy.fromJson(payload);
      },
      () async => fixtures.upsertPolicy(countryCode: countryCode),
    );
  }
}

class _PolicyAdminFixtures {
  _PolicyAdminFixtures(this._policies);

  final List<CountryFeaturePolicy> _policies;

  static _PolicyAdminFixtures seed() {
    return _PolicyAdminFixtures(<CountryFeaturePolicy>[
      CountryFeaturePolicy(
        id: 'policy-1',
        countryCode: 'NG',
        bucketType: 'tier-1',
        depositsEnabled: true,
        marketTradingEnabled: true,
        platformRewardWithdrawalsEnabled: true,
        userHostedGiftWithdrawalsEnabled: false,
        gtexCompetitionGiftWithdrawalsEnabled: false,
        nationalRewardWithdrawalsEnabled: false,
        oneTimeRegionChangeAfterDays: 180,
        active: true,
        updatedAt: DateTime.parse('2026-03-12T00:00:00Z'),
      ),
    ]);
  }

  Future<List<CountryFeaturePolicy>> policies() async =>
      List<CountryFeaturePolicy>.of(_policies, growable: false);

  Future<CountryFeaturePolicy> upsertPolicy({
    required String countryCode,
  }) async {
    final CountryFeaturePolicy policy = CountryFeaturePolicy(
      id: 'policy-${_policies.length + 1}',
      countryCode: countryCode,
      bucketType: 'default',
      depositsEnabled: true,
      marketTradingEnabled: true,
      platformRewardWithdrawalsEnabled: true,
      userHostedGiftWithdrawalsEnabled: false,
      gtexCompetitionGiftWithdrawalsEnabled: false,
      nationalRewardWithdrawalsEnabled: false,
      oneTimeRegionChangeAfterDays: 180,
      active: true,
      updatedAt: DateTime.now().toUtc(),
    );
    _policies.insert(0, policy);
    return policy;
  }
}
