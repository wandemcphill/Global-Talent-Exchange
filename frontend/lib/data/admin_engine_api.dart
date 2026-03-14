import 'gte_api_repository.dart';
import 'gte_authed_api.dart';
import 'gte_http_transport.dart';
import '../models/admin_engine_models.dart';

class AdminEngineApi {
  AdminEngineApi({
    required this.client,
    required this.fixtures,
  });

  final GteAuthedApi client;
  final _AdminEngineFixtures fixtures;

  factory AdminEngineApi.standard({
    required String baseUrl,
    required String? accessToken,
    GteBackendMode mode = GteBackendMode.liveThenFixture,
  }) {
    return AdminEngineApi(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: mode),
        transport: GteHttpTransport(),
        accessToken: accessToken,
        mode: mode,
      ),
      fixtures: _AdminEngineFixtures.seed(),
    );
  }

  factory AdminEngineApi.fixture() {
    return AdminEngineApi(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.fixture,
        ),
        transport: GteHttpTransport(),
        accessToken: 'fixture-token',
        mode: GteBackendMode.fixture,
      ),
      fixtures: _AdminEngineFixtures.seed(),
    );
  }

  Future<List<AdminFeatureFlag>> listFeatureFlags() {
    return client.withFallback<List<AdminFeatureFlag>>(
      () async {
        final List<dynamic> payload =
            await client.getList('/admin/admin-engine/feature-flags');
        return payload.map(AdminFeatureFlag.fromJson).toList(growable: false);
      },
      fixtures.featureFlags,
    );
  }

  Future<AdminFeatureFlag> upsertFeatureFlag({
    required String featureKey,
    required String title,
    String? description,
    bool enabled = false,
    String audience = 'global',
  }) {
    return client.withFallback<AdminFeatureFlag>(
      () async {
        final Object? payload = await client.request(
          'POST',
          '/admin/admin-engine/feature-flags',
          body: <String, Object?>{
            'feature_key': featureKey,
            'title': title,
            'description': description,
            'enabled': enabled,
            'audience': audience,
          },
        );
        return AdminFeatureFlag.fromJson(payload);
      },
      () async => fixtures.upsertFeatureFlag(
        featureKey: featureKey,
        title: title,
        enabled: enabled,
      ),
    );
  }

  Future<List<AdminCalendarRule>> listCalendarRules() {
    return client.withFallback<List<AdminCalendarRule>>(
      () async {
        final List<dynamic> payload =
            await client.getList('/admin/admin-engine/calendar-rules');
        return payload.map(AdminCalendarRule.fromJson).toList(growable: false);
      },
      fixtures.calendarRules,
    );
  }

  Future<AdminCalendarRule> upsertCalendarRule({
    required String ruleKey,
    required String title,
    String? description,
    bool worldCupExclusive = false,
    bool active = true,
    int priority = 100,
    Map<String, Object?> config = const <String, Object?>{},
  }) {
    return client.withFallback<AdminCalendarRule>(
      () async {
        final Object? payload = await client.request(
          'POST',
          '/admin/admin-engine/calendar-rules',
          body: <String, Object?>{
            'rule_key': ruleKey,
            'title': title,
            'description': description,
            'world_cup_exclusive': worldCupExclusive,
            'active': active,
            'priority': priority,
            'config_json': config,
          },
        );
        return AdminCalendarRule.fromJson(payload);
      },
      () async => fixtures.upsertCalendarRule(ruleKey: ruleKey, title: title),
    );
  }

  Future<List<AdminRewardRule>> listRewardRules() {
    return client.withFallback<List<AdminRewardRule>>(
      () async {
        final List<dynamic> payload =
            await client.getList('/admin/admin-engine/reward-rules');
        return payload.map(AdminRewardRule.fromJson).toList(growable: false);
      },
      fixtures.rewardRules,
    );
  }

  Future<AdminRewardRule> upsertRewardRule({
    required String ruleKey,
    required String title,
    String? description,
    int tradingFeeBps = 2000,
    int giftPlatformRakeBps = 3000,
    int withdrawalFeeBps = 1000,
    double minimumWithdrawalFeeCredits = 5,
    int competitionPlatformFeeBps = 1000,
    bool active = true,
  }) {
    return client.withFallback<AdminRewardRule>(
      () async {
        final Object? payload = await client.request(
          'POST',
          '/admin/admin-engine/reward-rules',
          body: <String, Object?>{
            'rule_key': ruleKey,
            'title': title,
            'description': description,
            'trading_fee_bps': tradingFeeBps,
            'gift_platform_rake_bps': giftPlatformRakeBps,
            'withdrawal_fee_bps': withdrawalFeeBps,
            'minimum_withdrawal_fee_credits': minimumWithdrawalFeeCredits,
            'competition_platform_fee_bps': competitionPlatformFeeBps,
            'active': active,
          },
        );
        return AdminRewardRule.fromJson(payload);
      },
      () async => fixtures.upsertRewardRule(ruleKey: ruleKey, title: title),
    );
  }
}

class _AdminEngineFixtures {
  _AdminEngineFixtures(this._featureFlags, this._calendarRules, this._rewardRules);

  final List<AdminFeatureFlag> _featureFlags;
  final List<AdminCalendarRule> _calendarRules;
  final List<AdminRewardRule> _rewardRules;

  static _AdminEngineFixtures seed() {
    return _AdminEngineFixtures(
      <AdminFeatureFlag>[
        AdminFeatureFlag(
          id: 'flag-1',
          featureKey: 'arena_live',
          title: 'Arena live',
          description: 'Enables cinematic arena layouts.',
          enabled: true,
          audience: 'global',
          updatedAt: DateTime.parse('2026-03-12T00:00:00Z'),
        ),
      ],
      <AdminCalendarRule>[
        AdminCalendarRule(
          id: 'rule-1',
          ruleKey: 'world-cup-lock',
          title: 'World cup exclusive window',
          description: 'Reserve windows during world cup.',
          worldCupExclusive: true,
          active: true,
          priority: 10,
          config: const <String, Object?>{'window_days': 7},
          updatedAt: DateTime.parse('2026-03-12T00:00:00Z'),
        ),
      ],
      <AdminRewardRule>[
        AdminRewardRule(
          id: 'reward-1',
          ruleKey: 'default',
          title: 'Default reward policy',
          description: 'Base trading fee and withdrawal policy.',
          tradingFeeBps: 2000,
          giftPlatformRakeBps: 3000,
          withdrawalFeeBps: 1000,
          minimumWithdrawalFeeCredits: 5,
          competitionPlatformFeeBps: 1000,
          active: true,
          updatedAt: DateTime.parse('2026-03-12T00:00:00Z'),
        ),
      ],
    );
  }

  Future<List<AdminFeatureFlag>> featureFlags() async =>
      List<AdminFeatureFlag>.of(_featureFlags, growable: false);

  Future<AdminFeatureFlag> upsertFeatureFlag({
    required String featureKey,
    required String title,
    required bool enabled,
  }) async {
    final AdminFeatureFlag flag = AdminFeatureFlag(
      id: 'flag-${_featureFlags.length + 1}',
      featureKey: featureKey,
      title: title,
      description: null,
      enabled: enabled,
      audience: 'global',
      updatedAt: DateTime.now().toUtc(),
    );
    _featureFlags.insert(0, flag);
    return flag;
  }

  Future<List<AdminCalendarRule>> calendarRules() async =>
      List<AdminCalendarRule>.of(_calendarRules, growable: false);

  Future<AdminCalendarRule> upsertCalendarRule({
    required String ruleKey,
    required String title,
  }) async {
    final AdminCalendarRule rule = AdminCalendarRule(
      id: 'rule-${_calendarRules.length + 1}',
      ruleKey: ruleKey,
      title: title,
      description: null,
      worldCupExclusive: false,
      active: true,
      priority: 100,
      config: const <String, Object?>{},
      updatedAt: DateTime.now().toUtc(),
    );
    _calendarRules.insert(0, rule);
    return rule;
  }

  Future<List<AdminRewardRule>> rewardRules() async =>
      List<AdminRewardRule>.of(_rewardRules, growable: false);

  Future<AdminRewardRule> upsertRewardRule({
    required String ruleKey,
    required String title,
  }) async {
    final AdminRewardRule rule = AdminRewardRule(
      id: 'reward-${_rewardRules.length + 1}',
      ruleKey: ruleKey,
      title: title,
      description: null,
      tradingFeeBps: 2000,
      giftPlatformRakeBps: 3000,
      withdrawalFeeBps: 1000,
      minimumWithdrawalFeeCredits: 5,
      competitionPlatformFeeBps: 1000,
      active: true,
      updatedAt: DateTime.now().toUtc(),
    );
    _rewardRules.insert(0, rule);
    return rule;
  }
}
