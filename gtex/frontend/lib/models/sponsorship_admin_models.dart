import 'package:gte_frontend/data/gte_models.dart';

class SponsorshipPackageView {
  const SponsorshipPackageView({
    required this.id,
    required this.code,
    required this.name,
    required this.assetType,
    required this.baseAmountMinor,
    required this.currency,
    required this.defaultDurationMonths,
    required this.payoutSchedule,
    required this.description,
    required this.isActive,
  });

  final String id;
  final String code;
  final String name;
  final String assetType;
  final int baseAmountMinor;
  final String currency;
  final int defaultDurationMonths;
  final String payoutSchedule;
  final String description;
  final bool isActive;

  factory SponsorshipPackageView.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'sponsorship package');
    return SponsorshipPackageView(
      id: GteJson.string(json, <String>['id']),
      code: GteJson.string(json, <String>['code']),
      name: GteJson.string(json, <String>['name']),
      assetType:
          GteJson.string(json, <String>['asset_type', 'assetType'], fallback: 'general'),
      baseAmountMinor: GteJson.integer(
          json, <String>['base_amount_minor', 'baseAmountMinor'],
          fallback: 0),
      currency: GteJson.string(json, <String>['currency'], fallback: 'USD'),
      defaultDurationMonths: GteJson.integer(
          json, <String>['default_duration_months', 'defaultDurationMonths'],
          fallback: 0),
      payoutSchedule: GteJson.string(
          json, <String>['payout_schedule', 'payoutSchedule'],
          fallback: 'quarterly'),
      description: GteJson.string(json, <String>['description'], fallback: ''),
      isActive: GteJson.boolean(json, <String>['is_active', 'isActive'], fallback: true),
    );
  }
}

class SponsorshipContractView {
  const SponsorshipContractView({
    required this.id,
    required this.clubId,
    required this.packageId,
    required this.assetType,
    required this.sponsorName,
    required this.status,
    required this.contractAmountMinor,
    required this.currency,
    required this.durationMonths,
    required this.payoutSchedule,
    required this.startAt,
    required this.endAt,
    required this.moderationRequired,
    required this.moderationStatus,
    required this.customCopy,
    required this.customLogoUrl,
    required this.performanceBonusMinor,
    required this.settledAmountMinor,
    required this.outstandingAmountMinor,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String clubId;
  final String? packageId;
  final String assetType;
  final String sponsorName;
  final String status;
  final int contractAmountMinor;
  final String currency;
  final int durationMonths;
  final String payoutSchedule;
  final DateTime startAt;
  final DateTime endAt;
  final bool moderationRequired;
  final String moderationStatus;
  final String? customCopy;
  final String? customLogoUrl;
  final int performanceBonusMinor;
  final int settledAmountMinor;
  final int outstandingAmountMinor;
  final DateTime createdAt;
  final DateTime updatedAt;

  factory SponsorshipContractView.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'sponsorship contract');
    return SponsorshipContractView(
      id: GteJson.string(json, <String>['id']),
      clubId: GteJson.string(json, <String>['club_id', 'clubId']),
      packageId:
          GteJson.stringOrNull(json, <String>['package_id', 'packageId']),
      assetType:
          GteJson.string(json, <String>['asset_type', 'assetType'], fallback: 'general'),
      sponsorName:
          GteJson.string(json, <String>['sponsor_name', 'sponsorName']),
      status: GteJson.string(json, <String>['status'], fallback: 'pending'),
      contractAmountMinor: GteJson.integer(
          json, <String>['contract_amount_minor', 'contractAmountMinor'],
          fallback: 0),
      currency: GteJson.string(json, <String>['currency'], fallback: 'USD'),
      durationMonths: GteJson.integer(
          json, <String>['duration_months', 'durationMonths'],
          fallback: 0),
      payoutSchedule: GteJson.string(
          json, <String>['payout_schedule', 'payoutSchedule'],
          fallback: 'quarterly'),
      startAt: GteJson.dateTime(json, <String>['start_at', 'startAt']),
      endAt: GteJson.dateTime(json, <String>['end_at', 'endAt']),
      moderationRequired: GteJson.boolean(
          json, <String>['moderation_required', 'moderationRequired'],
          fallback: false),
      moderationStatus: GteJson.string(
          json, <String>['moderation_status', 'moderationStatus'],
          fallback: 'pending'),
      customCopy:
          GteJson.stringOrNull(json, <String>['custom_copy', 'customCopy']),
      customLogoUrl:
          GteJson.stringOrNull(json, <String>['custom_logo_url', 'customLogoUrl']),
      performanceBonusMinor: GteJson.integer(
          json, <String>['performance_bonus_minor', 'performanceBonusMinor'],
          fallback: 0),
      settledAmountMinor: GteJson.integer(
          json, <String>['settled_amount_minor', 'settledAmountMinor'],
          fallback: 0),
      outstandingAmountMinor: GteJson.integer(
          json, <String>['outstanding_amount_minor', 'outstandingAmountMinor'],
          fallback: 0),
      createdAt: GteJson.dateTime(json, <String>['created_at', 'createdAt']),
      updatedAt: GteJson.dateTime(json, <String>['updated_at', 'updatedAt']),
    );
  }
}
