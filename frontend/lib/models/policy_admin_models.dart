import 'package:gte_frontend/data/gte_models.dart';

class CountryFeaturePolicy {
  const CountryFeaturePolicy({
    required this.id,
    required this.countryCode,
    required this.bucketType,
    required this.depositsEnabled,
    required this.marketTradingEnabled,
    required this.platformRewardWithdrawalsEnabled,
    required this.userHostedGiftWithdrawalsEnabled,
    required this.gtexCompetitionGiftWithdrawalsEnabled,
    required this.nationalRewardWithdrawalsEnabled,
    required this.oneTimeRegionChangeAfterDays,
    required this.active,
    required this.updatedAt,
  });

  final String id;
  final String countryCode;
  final String bucketType;
  final bool depositsEnabled;
  final bool marketTradingEnabled;
  final bool platformRewardWithdrawalsEnabled;
  final bool userHostedGiftWithdrawalsEnabled;
  final bool gtexCompetitionGiftWithdrawalsEnabled;
  final bool nationalRewardWithdrawalsEnabled;
  final int oneTimeRegionChangeAfterDays;
  final bool active;
  final DateTime updatedAt;

  factory CountryFeaturePolicy.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'country policy');
    return CountryFeaturePolicy(
      id: GteJson.string(json, <String>['id'], fallback: ''),
      countryCode:
          GteJson.string(json, <String>['country_code', 'countryCode']),
      bucketType:
          GteJson.string(json, <String>['bucket_type', 'bucketType'], fallback: 'default'),
      depositsEnabled: GteJson.boolean(
          json, <String>['deposits_enabled', 'depositsEnabled'],
          fallback: true),
      marketTradingEnabled: GteJson.boolean(
          json, <String>['market_trading_enabled', 'marketTradingEnabled'],
          fallback: true),
      platformRewardWithdrawalsEnabled: GteJson.boolean(
          json, <String>['platform_reward_withdrawals_enabled', 'platformRewardWithdrawalsEnabled'],
          fallback: true),
      userHostedGiftWithdrawalsEnabled: GteJson.boolean(
          json, <String>['user_hosted_gift_withdrawals_enabled', 'userHostedGiftWithdrawalsEnabled'],
          fallback: false),
      gtexCompetitionGiftWithdrawalsEnabled: GteJson.boolean(
          json, <String>['gtex_competition_gift_withdrawals_enabled', 'gtexCompetitionGiftWithdrawalsEnabled'],
          fallback: false),
      nationalRewardWithdrawalsEnabled: GteJson.boolean(
          json, <String>['national_reward_withdrawals_enabled', 'nationalRewardWithdrawalsEnabled'],
          fallback: false),
      oneTimeRegionChangeAfterDays: GteJson.integer(
          json, <String>['one_time_region_change_after_days', 'oneTimeRegionChangeAfterDays'],
          fallback: 0),
      active: GteJson.boolean(json, <String>['active'], fallback: true),
      updatedAt: GteJson.dateTimeOrNull(json, <String>['updated_at', 'updatedAt']) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
    );
  }
}
