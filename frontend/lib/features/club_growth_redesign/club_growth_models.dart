import 'package:flutter/foundation.dart';
import 'package:gte_frontend/data/gte_models.dart';

@immutable
class GtexStaffProfile {
  const GtexStaffProfile({
    required this.id,
    required this.displayName,
    required this.staffType,
    required this.rarity,
    required this.skills,
    required this.salaryMinor,
    required this.commissionBps,
    required this.rating,
    required this.active,
    required this.metadata,
  });

  final String id;
  final String displayName;
  final String staffType;
  final String rarity;
  final List<String> skills;
  final int salaryMinor;
  final int commissionBps;
  final int rating;
  final bool active;
  final Map<String, Object?> metadata;

  factory GtexStaffProfile.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'club staff profile',
    );
    return GtexStaffProfile(
      id: GteJson.string(json, const <String>['id']),
      displayName: GteJson.string(json, const <String>[
        'display_name',
        'displayName',
      ]),
      staffType: GteJson.string(json, const <String>[
        'staff_type',
        'staffType',
      ]),
      rarity: GteJson.string(json, const <String>['rarity']),
      skills: _stringList(json, const <String>['skills', 'skills_json']),
      salaryMinor: GteJson.integer(json, const <String>[
        'salary_minor',
        'salaryMinor',
      ]),
      commissionBps: GteJson.integer(json, const <String>[
        'commission_bps',
        'commissionBps',
      ]),
      rating: GteJson.integer(json, const <String>['rating']),
      active: GteJson.boolean(json, const <String>['active'], fallback: true),
      metadata: GteJson.map(
        json,
        keys: const <String>['metadata', 'metadata_json', 'metadataJson'],
        fallback: const <String, Object?>{},
      ),
    );
  }
}

@immutable
class GtexStaffContract {
  const GtexStaffContract({
    required this.id,
    required this.clubId,
    required this.staffProfile,
    required this.status,
    required this.salaryMinor,
    required this.commissionBps,
    required this.durationDays,
    required this.roleScope,
    required this.exclusive,
    required this.startedAt,
    required this.endsAt,
    required this.acceptedAt,
    required this.terminatedAt,
    required this.updatedAt,
  });

  final String id;
  final String clubId;
  final GtexStaffProfile staffProfile;
  final String status;
  final int salaryMinor;
  final int commissionBps;
  final int durationDays;
  final String roleScope;
  final bool exclusive;
  final DateTime? startedAt;
  final DateTime? endsAt;
  final DateTime? acceptedAt;
  final DateTime? terminatedAt;
  final DateTime? updatedAt;

  bool get active => status == 'active';

  factory GtexStaffContract.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'club staff contract',
    );
    return GtexStaffContract(
      id: GteJson.string(json, const <String>['id']),
      clubId: GteJson.string(json, const <String>['club_id', 'clubId']),
      staffProfile: GtexStaffProfile.fromJson(
        GteJson.map(
          json,
          keys: const <String>['staff_profile', 'staffProfile'],
        ),
      ),
      status: GteJson.string(json, const <String>['status']),
      salaryMinor: GteJson.integer(json, const <String>[
        'salary_minor',
        'salaryMinor',
      ]),
      commissionBps: GteJson.integer(json, const <String>[
        'commission_bps',
        'commissionBps',
      ]),
      durationDays: GteJson.integer(json, const <String>[
        'duration_days',
        'durationDays',
      ]),
      roleScope: GteJson.string(json, const <String>[
        'role_scope',
        'roleScope',
      ]),
      exclusive: GteJson.boolean(json, const <String>['exclusive']),
      startedAt: GteJson.dateTimeOrNull(json, const <String>[
        'started_at',
        'startedAt',
      ]),
      endsAt: GteJson.dateTimeOrNull(json, const <String>['ends_at', 'endsAt']),
      acceptedAt: GteJson.dateTimeOrNull(json, const <String>[
        'accepted_at',
        'acceptedAt',
      ]),
      terminatedAt: GteJson.dateTimeOrNull(json, const <String>[
        'terminated_at',
        'terminatedAt',
      ]),
      updatedAt: GteJson.dateTimeOrNull(json, const <String>[
        'updated_at',
        'updatedAt',
      ]),
    );
  }
}

@immutable
class GtexAcademyProfile {
  const GtexAcademyProfile({
    required this.id,
    required this.clubId,
    required this.level,
    required this.investmentMinor,
    required this.generationCooldownUntil,
    required this.metadata,
    required this.updatedAt,
  });

  final String id;
  final String clubId;
  final int level;
  final int investmentMinor;
  final DateTime? generationCooldownUntil;
  final Map<String, Object?> metadata;
  final DateTime? updatedAt;

  factory GtexAcademyProfile.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'club academy profile',
    );
    return GtexAcademyProfile(
      id: GteJson.string(json, const <String>['id']),
      clubId: GteJson.string(json, const <String>['club_id', 'clubId']),
      level: GteJson.integer(json, const <String>['level']),
      investmentMinor: GteJson.integer(json, const <String>[
        'investment_minor',
        'investmentMinor',
      ]),
      generationCooldownUntil: GteJson.dateTimeOrNull(json, const <String>[
        'generation_cooldown_until',
        'generationCooldownUntil',
      ]),
      metadata: GteJson.map(
        json,
        keys: const <String>['metadata', 'metadata_json', 'metadataJson'],
        fallback: const <String, Object?>{},
      ),
      updatedAt: GteJson.dateTimeOrNull(json, const <String>[
        'updated_at',
        'updatedAt',
      ]),
    );
  }
}

@immutable
class GtexAcademyProspect {
  const GtexAcademyProspect({
    required this.id,
    required this.clubId,
    required this.displayName,
    required this.nationality,
    required this.position,
    required this.age,
    required this.personality,
    required this.currentAbility,
    required this.potential,
    required this.portraitAssetRef,
    required this.status,
    required this.metadata,
    required this.updatedAt,
  });

  final String id;
  final String clubId;
  final String displayName;
  final String? nationality;
  final String position;
  final int age;
  final Map<String, Object?> personality;
  final int currentAbility;
  final int potential;
  final String? portraitAssetRef;
  final String status;
  final Map<String, Object?> metadata;
  final DateTime? updatedAt;

  bool get contractEligible =>
      status == 'discovered' ||
      status == 'trial' ||
      status == 'academy' ||
      status == 'contract_rejected';
  bool get promotable => status == 'youth_signed';

  factory GtexAcademyProspect.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'club academy prospect',
    );
    return GtexAcademyProspect(
      id: GteJson.string(json, const <String>['id']),
      clubId: GteJson.string(json, const <String>['club_id', 'clubId']),
      displayName: GteJson.string(json, const <String>[
        'display_name',
        'displayName',
      ]),
      nationality: GteJson.stringOrNull(json, const <String>['nationality']),
      position: GteJson.string(json, const <String>['position']),
      age: GteJson.integer(json, const <String>['age']),
      personality: GteJson.map(
        json,
        keys: const <String>['personality', 'personality_json'],
        fallback: const <String, Object?>{},
      ),
      currentAbility: GteJson.integer(json, const <String>[
        'current_ability',
        'currentAbility',
      ]),
      potential: GteJson.integer(json, const <String>['potential']),
      portraitAssetRef: GteJson.stringOrNull(json, const <String>[
        'portrait_asset_ref',
        'portraitAssetRef',
      ]),
      status: GteJson.string(json, const <String>['status']),
      metadata: GteJson.map(
        json,
        keys: const <String>['metadata', 'metadata_json', 'metadataJson'],
        fallback: const <String, Object?>{},
      ),
      updatedAt: GteJson.dateTimeOrNull(json, const <String>[
        'updated_at',
        'updatedAt',
      ]),
    );
  }
}

@immutable
class GtexAcademyContractOffer {
  const GtexAcademyContractOffer({
    required this.id,
    required this.clubId,
    required this.prospectId,
    required this.status,
    required this.wageMinor,
    required this.durationMonths,
    required this.responseReason,
    required this.updatedAt,
  });

  final String id;
  final String clubId;
  final String prospectId;
  final String status;
  final int wageMinor;
  final int durationMonths;
  final String? responseReason;
  final DateTime? updatedAt;

  factory GtexAcademyContractOffer.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'academy contract offer',
    );
    return GtexAcademyContractOffer(
      id: GteJson.string(json, const <String>['id']),
      clubId: GteJson.string(json, const <String>['club_id', 'clubId']),
      prospectId: GteJson.string(json, const <String>[
        'prospect_id',
        'prospectId',
      ]),
      status: GteJson.string(json, const <String>['status']),
      wageMinor: GteJson.integer(json, const <String>[
        'wage_minor',
        'wageMinor',
      ]),
      durationMonths: GteJson.integer(json, const <String>[
        'duration_months',
        'durationMonths',
      ]),
      responseReason: GteJson.stringOrNull(json, const <String>[
        'response_reason',
        'responseReason',
      ]),
      updatedAt: GteJson.dateTimeOrNull(json, const <String>[
        'updated_at',
        'updatedAt',
      ]),
    );
  }
}

@immutable
class GtexSponsorshipClubSummary {
  const GtexSponsorshipClubSummary({
    required this.activeContracts,
    required this.pendingContracts,
    required this.settledPayoutMinor,
    required this.outstandingPayoutMinor,
    required this.openLeads,
  });

  final int activeContracts;
  final int pendingContracts;
  final int settledPayoutMinor;
  final int outstandingPayoutMinor;
  final int openLeads;

  factory GtexSponsorshipClubSummary.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'club sponsorship summary',
    );
    return GtexSponsorshipClubSummary(
      activeContracts: GteJson.integer(json, const <String>[
        'active_contracts',
        'activeContracts',
      ]),
      pendingContracts: GteJson.integer(json, const <String>[
        'pending_contracts',
        'pendingContracts',
      ]),
      settledPayoutMinor: GteJson.integer(json, const <String>[
        'settled_payout_minor',
        'settledPayoutMinor',
      ]),
      outstandingPayoutMinor: GteJson.integer(json, const <String>[
        'outstanding_payout_minor',
        'outstandingPayoutMinor',
      ]),
      openLeads: GteJson.integer(json, const <String>[
        'open_leads',
        'openLeads',
      ]),
    );
  }
}

@immutable
class GtexClubGrowthDashboard {
  const GtexClubGrowthDashboard({
    required this.clubId,
    required this.staffMarket,
    required this.staffContracts,
    required this.staffEffects,
    required this.academyProfile,
    required this.academyProspects,
    required this.sponsorship,
    required this.updatedAt,
  });

  final String clubId;
  final List<GtexStaffProfile> staffMarket;
  final List<GtexStaffContract> staffContracts;
  final Map<String, int> staffEffects;
  final GtexAcademyProfile academyProfile;
  final List<GtexAcademyProspect> academyProspects;
  final GtexSponsorshipClubSummary sponsorship;
  final DateTime? updatedAt;

  int get activeStaffCount =>
      staffContracts.where((GtexStaffContract item) => item.active).length;

  factory GtexClubGrowthDashboard.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'club growth dashboard',
    );
    return GtexClubGrowthDashboard(
      clubId: GteJson.string(json, const <String>['club_id', 'clubId']),
      staffMarket: GteJson.typedList(json, const <String>[
        'staff_market',
        'staffMarket',
      ], GtexStaffProfile.fromJson),
      staffContracts: GteJson.typedList(json, const <String>[
        'staff_contracts',
        'staffContracts',
      ], GtexStaffContract.fromJson),
      staffEffects: _intMap(
        GteJson.map(
          json,
          keys: const <String>['staff_effects', 'staffEffects'],
          fallback: const <String, Object?>{},
        ),
      ),
      academyProfile: GtexAcademyProfile.fromJson(
        GteJson.map(
          json,
          keys: const <String>['academy_profile', 'academyProfile'],
        ),
      ),
      academyProspects: GteJson.typedList(json, const <String>[
        'academy_prospects',
        'academyProspects',
      ], GtexAcademyProspect.fromJson),
      sponsorship: GtexSponsorshipClubSummary.fromJson(
        GteJson.map(json, keys: const <String>['sponsorship']),
      ),
      updatedAt: GteJson.dateTimeOrNull(json, const <String>[
        'updated_at',
        'updatedAt',
      ]),
    );
  }
}

List<String> _stringList(Map<String, Object?> json, List<String> keys) {
  final Object? value = GteJson.value(json, keys);
  if (value is List) {
    return value
        .map((Object? item) => item?.toString().trim() ?? '')
        .where((String item) => item.isNotEmpty)
        .toList(growable: false);
  }
  return const <String>[];
}

Map<String, int> _intMap(Map<String, Object?> json) {
  return json.map((String key, Object? value) {
    if (value is int) {
      return MapEntry<String, int>(key, value);
    }
    if (value is num) {
      return MapEntry<String, int>(key, value.toInt());
    }
    return MapEntry<String, int>(
      key,
      int.tryParse(value?.toString() ?? '') ?? 0,
    );
  });
}
