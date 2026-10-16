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
    final Map<String, Object?> json = GteJson.map(value, label: 'feature flag');
    return AdminFeatureFlag(
      id: GteJson.string(json, <String>['id']),
      featureKey: GteJson.string(json, <String>['feature_key', 'featureKey']),
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
      config: GteJson.map(json,
          keys: <String>['config_json', 'configJson', 'config'],
          fallback: const <String, Object?>{}),
      updatedAt: GteJson.dateTime(json, <String>['updated_at', 'updatedAt']),
    );
  }
}

class AdminGiftStabilityControlConfig {
  const AdminGiftStabilityControlConfig({
    required this.maxGiftValue,
    required this.maxDailySpend,
    required this.cooldownSeconds,
    required this.requiresKyc,
  });

  final double maxGiftValue;
  final double maxDailySpend;
  final int cooldownSeconds;
  final bool requiresKyc;

  const AdminGiftStabilityControlConfig.defaults()
      : maxGiftValue = 0,
        maxDailySpend = 0,
        cooldownSeconds = 0,
        requiresKyc = false;

  factory AdminGiftStabilityControlConfig.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'gift stability control',
      fallback: const <String, Object?>{},
    );
    return AdminGiftStabilityControlConfig(
      maxGiftValue: GteJson.number(
        json,
        <String>['max_gift_value', 'maxGiftValue'],
      ),
      maxDailySpend: GteJson.number(
        json,
        <String>['max_daily_spend', 'maxDailySpend'],
      ),
      cooldownSeconds: GteJson.integer(
        json,
        <String>['cooldown_seconds', 'cooldownSeconds'],
      ),
      requiresKyc: GteJson.boolean(
        json,
        <String>['requires_kyc', 'requiresKyc'],
      ),
    );
  }

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'max_gift_value': maxGiftValue,
      'max_daily_spend': maxDailySpend,
      'cooldown_seconds': cooldownSeconds,
      'requires_kyc': requiresKyc,
    };
  }
}

class AdminRewardLoopControlConfig {
  const AdminRewardLoopControlConfig({
    required this.maxMultiplier,
    required this.cooldownSeconds,
    required this.dailyCap,
    required this.enabled,
  });

  final double maxMultiplier;
  final int cooldownSeconds;
  final double dailyCap;
  final bool enabled;

  const AdminRewardLoopControlConfig.defaults()
      : maxMultiplier = 0,
        cooldownSeconds = 0,
        dailyCap = 0,
        enabled = false;

  factory AdminRewardLoopControlConfig.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'reward loop control',
      fallback: const <String, Object?>{},
    );
    return AdminRewardLoopControlConfig(
      maxMultiplier: GteJson.number(
        json,
        <String>['max_multiplier', 'maxMultiplier'],
      ),
      cooldownSeconds: GteJson.integer(
        json,
        <String>['cooldown_seconds', 'cooldownSeconds'],
      ),
      dailyCap: GteJson.number(
        json,
        <String>['daily_cap', 'dailyCap'],
      ),
      enabled: GteJson.boolean(
        json,
        <String>['enabled'],
      ),
    );
  }

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'max_multiplier': maxMultiplier,
      'cooldown_seconds': cooldownSeconds,
      'daily_cap': dailyCap,
      'enabled': enabled,
    };
  }
}

class AdminFanPredictionFairnessConfig {
  const AdminFanPredictionFairnessConfig({
    required this.maxStake,
    required this.dailyEntryCap,
    required this.rewardPoolShareBps,
    required this.enabled,
  });

  final double maxStake;
  final int dailyEntryCap;
  final int rewardPoolShareBps;
  final bool enabled;

  const AdminFanPredictionFairnessConfig.defaults()
      : maxStake = 0,
        dailyEntryCap = 0,
        rewardPoolShareBps = 0,
        enabled = false;

  factory AdminFanPredictionFairnessConfig.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'fan prediction fairness control',
      fallback: const <String, Object?>{},
    );
    return AdminFanPredictionFairnessConfig(
      maxStake: GteJson.number(
        json,
        <String>['max_stake', 'maxStake'],
      ),
      dailyEntryCap: GteJson.integer(
        json,
        <String>['daily_entry_cap', 'dailyEntryCap'],
      ),
      rewardPoolShareBps: GteJson.integer(
        json,
        <String>['reward_pool_share_bps', 'rewardPoolShareBps'],
      ),
      enabled: GteJson.boolean(
        json,
        <String>['enabled'],
      ),
    );
  }

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'max_stake': maxStake,
      'daily_entry_cap': dailyEntryCap,
      'reward_pool_share_bps': rewardPoolShareBps,
      'enabled': enabled,
    };
  }
}

class AdminRewardRuleStabilityControls {
  const AdminRewardRuleStabilityControls({
    required this.userHostedGift,
    required this.gtexCompetitionGift,
    required this.creatorMatchGift,
    required this.creatorViewerPurchase,
    required this.reward,
    required this.fanPrediction,
  });

  final AdminGiftStabilityControlConfig userHostedGift;
  final AdminGiftStabilityControlConfig gtexCompetitionGift;
  final AdminGiftStabilityControlConfig creatorMatchGift;
  final AdminRewardLoopControlConfig creatorViewerPurchase;
  final AdminRewardLoopControlConfig reward;
  final AdminFanPredictionFairnessConfig fanPrediction;

  const AdminRewardRuleStabilityControls.defaults()
      : userHostedGift = const AdminGiftStabilityControlConfig.defaults(),
        gtexCompetitionGift = const AdminGiftStabilityControlConfig.defaults(),
        creatorMatchGift = const AdminGiftStabilityControlConfig.defaults(),
        creatorViewerPurchase = const AdminRewardLoopControlConfig.defaults(),
        reward = const AdminRewardLoopControlConfig.defaults(),
        fanPrediction = const AdminFanPredictionFairnessConfig.defaults();

  factory AdminRewardRuleStabilityControls.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'reward rule stability controls',
      fallback: const <String, Object?>{},
    );
    return AdminRewardRuleStabilityControls(
      userHostedGift: AdminGiftStabilityControlConfig.fromJson(
        GteJson.map(
          json,
          keys: <String>['user_hosted_gift', 'userHostedGift'],
          fallback: const <String, Object?>{},
        ),
      ),
      gtexCompetitionGift: AdminGiftStabilityControlConfig.fromJson(
        GteJson.map(
          json,
          keys: <String>['gtex_competition_gift', 'gtexCompetitionGift'],
          fallback: const <String, Object?>{},
        ),
      ),
      creatorMatchGift: AdminGiftStabilityControlConfig.fromJson(
        GteJson.map(
          json,
          keys: <String>['creator_match_gift', 'creatorMatchGift'],
          fallback: const <String, Object?>{},
        ),
      ),
      creatorViewerPurchase: AdminRewardLoopControlConfig.fromJson(
        GteJson.map(
          json,
          keys: <String>[
            'creator_viewer_purchase',
            'creatorViewerPurchase',
          ],
          fallback: const <String, Object?>{},
        ),
      ),
      reward: AdminRewardLoopControlConfig.fromJson(
        GteJson.map(
          json,
          keys: <String>['reward'],
          fallback: const <String, Object?>{},
        ),
      ),
      fanPrediction: AdminFanPredictionFairnessConfig.fromJson(
        GteJson.map(
          json,
          keys: <String>['fan_prediction', 'fanPrediction'],
          fallback: const <String, Object?>{},
        ),
      ),
    );
  }

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'user_hosted_gift': userHostedGift.toJson(),
      'gtex_competition_gift': gtexCompetitionGift.toJson(),
      'creator_match_gift': creatorMatchGift.toJson(),
      'creator_viewer_purchase': creatorViewerPurchase.toJson(),
      'reward': reward.toJson(),
      'fan_prediction': fanPrediction.toJson(),
    };
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
    required this.stabilityControls,
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
  final AdminRewardRuleStabilityControls stabilityControls;
  final bool active;
  final DateTime updatedAt;

  factory AdminRewardRule.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'reward rule');
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
          json,
          <String>[
            'minimum_withdrawal_fee_credits',
            'minimumWithdrawalFeeCredits'
          ],
          fallback: 0),
      competitionPlatformFeeBps: GteJson.integer(json,
          <String>['competition_platform_fee_bps', 'competitionPlatformFeeBps'],
          fallback: 0),
      stabilityControls: AdminRewardRuleStabilityControls.fromJson(
        GteJson.map(
          json,
          keys: <String>['stability_controls', 'stabilityControls'],
          fallback: const <String, Object?>{},
        ),
      ),
      active: GteJson.boolean(json, <String>['active'], fallback: true),
      updatedAt: GteJson.dateTime(json, <String>['updated_at', 'updatedAt']),
    );
  }

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'id': id,
      'rule_key': ruleKey,
      'title': title,
      'description': description,
      'trading_fee_bps': tradingFeeBps,
      'gift_platform_rake_bps': giftPlatformRakeBps,
      'withdrawal_fee_bps': withdrawalFeeBps,
      'minimum_withdrawal_fee_credits': minimumWithdrawalFeeCredits,
      'competition_platform_fee_bps': competitionPlatformFeeBps,
      'stability_controls': stabilityControls.toJson(),
      'active': active,
      'updated_at': updatedAt.toUtc().toIso8601String(),
    };
  }
}
