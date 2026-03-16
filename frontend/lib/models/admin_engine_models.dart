import 'package:gte_frontend/data/gte_models.dart';

class AdminFeatureFlag {
  const AdminFeatureFlag({
    required this.id,
    required this.featureKey,
    required this.title,
    required this.description,
    required this.enabled,
    required this.audience,
    required this.updatedAt,
  });

  final String id;
  final String featureKey;
  final String title;
  final String? description;
  final bool enabled;
  final String audience;
  final DateTime updatedAt;

  factory AdminFeatureFlag.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'feature flag');
    return AdminFeatureFlag(
      id: GteJson.string(json, <String>['id']),
      featureKey:
          GteJson.string(json, <String>['feature_key', 'featureKey']),
      title: GteJson.string(json, <String>['title']),
      description: GteJson.stringOrNull(json, <String>['description']),
      enabled: GteJson.boolean(json, <String>['enabled'], fallback: false),
      audience: GteJson.string(json, <String>['audience'], fallback: 'global'),
      updatedAt: GteJson.dateTime(json, <String>['updated_at', 'updatedAt']),
    );
  }
}

class AdminCalendarRule {
  const AdminCalendarRule({
    required this.id,
    required this.ruleKey,
    required this.title,
    required this.description,
    required this.worldCupExclusive,
    required this.active,
    required this.priority,
    required this.config,
    required this.updatedAt,
  });

  final String id;
  final String ruleKey;
  final String title;
  final String? description;
  final bool worldCupExclusive;
  final bool active;
  final int priority;
  final Map<String, Object?> config;
  final DateTime updatedAt;

  factory AdminCalendarRule.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'calendar rule');
    return AdminCalendarRule(
      id: GteJson.string(json, <String>['id']),
      ruleKey: GteJson.string(json, <String>['rule_key', 'ruleKey']),
      title: GteJson.string(json, <String>['title']),
      description: GteJson.stringOrNull(json, <String>['description']),
      worldCupExclusive: GteJson.boolean(
          json, <String>['world_cup_exclusive', 'worldCupExclusive'],
          fallback: false),
      active: GteJson.boolean(json, <String>['active'], fallback: true),
      priority: GteJson.integer(json, <String>['priority'], fallback: 100),
      config: GteJson.map(
          json, keys: <String>['config_json', 'configJson', 'config'],
          fallback: const <String, Object?>{}),
      updatedAt: GteJson.dateTime(json, <String>['updated_at', 'updatedAt']),
    );
  }
}

class AdminRewardRule {
  const AdminRewardRule({
    required this.id,
    required this.ruleKey,
    required this.title,
    required this.description,
    required this.tradingFeeBps,
    required this.giftPlatformRakeBps,
    required this.withdrawalFeeBps,
    required this.minimumWithdrawalFeeCredits,
    required this.competitionPlatformFeeBps,
    required this.active,
    required this.updatedAt,
  });

  final String id;
  final String ruleKey;
  final String title;
  final String? description;
  final int tradingFeeBps;
  final int giftPlatformRakeBps;
  final int withdrawalFeeBps;
  final double minimumWithdrawalFeeCredits;
  final int competitionPlatformFeeBps;
  final bool active;
  final DateTime updatedAt;

  factory AdminRewardRule.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'reward rule');
    return AdminRewardRule(
      id: GteJson.string(json, <String>['id']),
      ruleKey: GteJson.string(json, <String>['rule_key', 'ruleKey']),
      title: GteJson.string(json, <String>['title']),
      description: GteJson.stringOrNull(json, <String>['description']),
      tradingFeeBps: GteJson.integer(
          json, <String>['trading_fee_bps', 'tradingFeeBps'],
          fallback: 0),
      giftPlatformRakeBps: GteJson.integer(
          json, <String>['gift_platform_rake_bps', 'giftPlatformRakeBps'],
          fallback: 0),
      withdrawalFeeBps: GteJson.integer(
          json, <String>['withdrawal_fee_bps', 'withdrawalFeeBps'],
          fallback: 0),
      minimumWithdrawalFeeCredits: GteJson.number(
          json, <String>['minimum_withdrawal_fee_credits', 'minimumWithdrawalFeeCredits'],
          fallback: 0),
      competitionPlatformFeeBps: GteJson.integer(
          json, <String>['competition_platform_fee_bps', 'competitionPlatformFeeBps'],
          fallback: 0),
      active: GteJson.boolean(json, <String>['active'], fallback: true),
      updatedAt: GteJson.dateTime(json, <String>['updated_at', 'updatedAt']),
    );
  }
}
