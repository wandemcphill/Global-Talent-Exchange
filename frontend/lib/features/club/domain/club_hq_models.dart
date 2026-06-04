typedef ClubJson = Map<String, Object?>;

enum ClubHqRole { owner, manager, scout, viewer }

ClubHqRole? clubHqRoleFromRaw(String raw) {
  switch (raw.trim().toLowerCase()) {
    case 'club.owner':
    case 'owner':
      return ClubHqRole.owner;
    case 'club.manager':
    case 'manager':
      return ClubHqRole.manager;
    case 'club.scout':
    case 'scout':
      return ClubHqRole.scout;
    case 'viewer':
    case 'guest':
      return ClubHqRole.viewer;
    default:
      return null;
  }
}

extension ClubHqRoleAccess on ClubHqRole {
  bool get canViewPrivate => this != ClubHqRole.viewer;
  bool get canViewFinance => this == ClubHqRole.owner;
  bool get canViewSponsorships => this == ClubHqRole.owner;
  bool get canManageBranding => this == ClubHqRole.owner;
  bool get canViewStaffAndAcademy =>
      this == ClubHqRole.owner || this == ClubHqRole.manager;
}

class ClubHqSnapshot {
  const ClubHqSnapshot({
    required this.dashboard,
    required this.finance,
    required this.readiness,
    required this.academy,
    required this.staff,
    required this.sponsorships,
    required this.branding,
    required this.trophies,
    required this.rankings,
  });

  final ClubDashboardDTO dashboard;
  final ClubFinanceDTO finance;
  final SquadReadinessDTO readiness;
  final ClubAcademyDTO academy;
  final ClubStaffDTO staff;
  final List<SponsorshipDTO> sponsorships;
  final ClubBrandingDTO branding;
  final List<TrophyDTO> trophies;
  final List<ClubRankingDTO> rankings;

  bool get isConfigured => dashboard.isConfigured;
}

class ClubDashboardDTO {
  const ClubDashboardDTO({
    required this.clubId,
    required this.name,
    this.badge,
    this.league,
    this.division,
    this.foundedYear,
    this.totalSquadValue,
    this.activeCompetitions = 0,
    this.alerts = const <String>[],
    this.recentActivity = const <String>[],
  });

  final String clubId;
  final String name;
  final String? badge;
  final String? league;
  final String? division;
  final int? foundedYear;
  final double? totalSquadValue;
  final int activeCompetitions;
  final List<String> alerts;
  final List<String> recentActivity;

  bool get isConfigured => clubId.trim().isNotEmpty && name.trim().isNotEmpty;

  factory ClubDashboardDTO.fromJson(Object? value) {
    final ClubJson json = clubAsMap(value);
    final ClubJson source = clubAsMap(
      json['dashboard'] ?? json['club'] ?? json['summary'] ?? json,
    );
    return ClubDashboardDTO(
      clubId: clubString(source, const <String>['club_id', 'clubId', 'id']),
      name: clubString(source, const <String>['name', 'club_name', 'clubName']),
      badge: clubNullableString(source, const <String>[
        'badge',
        'badge_url',
        'badgeUrl',
        'badge_asset',
      ]),
      league: clubNullableString(source, const <String>['league']),
      division: clubNullableString(source, const <String>['division']),
      foundedYear: clubNullableInt(source, const <String>[
        'founded_year',
        'foundedYear',
      ]),
      totalSquadValue: clubNullableNumber(source, const <String>[
        'total_squad_value',
        'totalSquadValue',
        'squad_value',
      ]),
      activeCompetitions: clubInt(source, const <String>[
        'active_competitions',
        'activeCompetitions',
      ]),
      alerts: clubStringList(source['alerts']),
      recentActivity: clubStringList(
        source['recent_activity'] ?? source['recentActivity'],
      ),
    );
  }
}

class ClubFinanceDTO {
  const ClubFinanceDTO({
    required this.clubId,
    required this.balance,
    this.revenue,
    this.expenses,
    this.transferBudget,
    this.wages,
    this.kpiTrend,
    this.lastSyncedAt,
    this.cashflow = const <FinanceSeriesPoint>[],
    this.alerts = const <String>[],
  });

  final String clubId;
  final double? balance;
  final double? revenue;
  final double? expenses;
  final double? transferBudget;
  final double? wages;
  final String? kpiTrend;
  final DateTime? lastSyncedAt;
  final List<FinanceSeriesPoint> cashflow;
  final List<String> alerts;

  bool get hasBackendBalance => balance != null;

  factory ClubFinanceDTO.fromJson(Object? value, {String fallbackClubId = ''}) {
    final ClubJson json = clubAsMap(value);
    final ClubJson summary = clubAsMap(
      json['balance_summary'] ?? json['balanceSummary'] ?? json['summary'],
    );
    return ClubFinanceDTO(
      clubId: clubString(json, const <String>[
        'club_id',
        'clubId',
      ], fallback: fallbackClubId),
      balance:
          clubNullableNumber(summary, const <String>[
            'balance',
            'current_balance',
            'currentBalance',
          ]) ??
          clubNullableNumber(json, const <String>[
            'balance',
            'current_balance',
            'currentBalance',
          ]),
      revenue:
          clubNullableNumber(summary, const <String>[
            'revenue',
            'monthly_income',
            'monthlyIncome',
          ]) ??
          clubNullableNumber(json, const <String>['revenue']),
      expenses:
          clubNullableNumber(summary, const <String>[
            'expenses',
            'monthly_expenses',
            'monthlyExpenses',
          ]) ??
          clubNullableNumber(json, const <String>['expenses']),
      transferBudget:
          clubNullableNumber(summary, const <String>[
            'transfer_budget',
            'transferBudget',
          ]) ??
          clubNullableNumber(json, const <String>[
            'transfer_budget',
            'transferBudget',
          ]),
      wages:
          clubNullableNumber(summary, const <String>[
            'wages',
            'payroll_commitment',
            'payrollCommitment',
          ]) ??
          clubNullableNumber(json, const <String>['wages']),
      kpiTrend: clubNullableString(json, const <String>[
        'kpi_trend',
        'kpiTrend',
        'trend',
      ]),
      lastSyncedAt: clubNullableDate(json, const <String>[
        'last_synced_at',
        'lastSyncedAt',
        'updated_at',
        'updatedAt',
      ]),
      cashflow: clubAsList(
        json['cashflow'],
      ).map(FinanceSeriesPoint.fromJson).toList(growable: false),
      alerts: clubStringList(json['alerts'] ?? json['finance_notes']),
    );
  }
}

class FinanceSeriesPoint {
  const FinanceSeriesPoint({required this.label, this.revenue, this.expenses});

  final String label;
  final double? revenue;
  final double? expenses;

  factory FinanceSeriesPoint.fromJson(Object? value) {
    final ClubJson json = clubAsMap(value);
    return FinanceSeriesPoint(
      label: clubString(json, const <String>['label', 'month', 'date']),
      revenue: clubNullableNumber(json, const <String>['revenue', 'income']),
      expenses: clubNullableNumber(json, const <String>['expenses', 'wages']),
    );
  }
}

class SquadReadinessDTO {
  const SquadReadinessDTO({
    this.eligibleCount = 0,
    this.injuredCount = 0,
    this.suspendedCount = 0,
    this.availableForNextFixture = 0,
    this.readinessScore,
  });

  final int eligibleCount;
  final int injuredCount;
  final int suspendedCount;
  final int availableForNextFixture;
  final double? readinessScore;

  factory SquadReadinessDTO.fromJson(Object? value) {
    final ClubJson json = clubAsMap(value);
    return SquadReadinessDTO(
      eligibleCount: clubInt(json, const <String>[
        'eligible_count',
        'eligibleCount',
      ]),
      injuredCount: clubInt(json, const <String>[
        'injured_count',
        'injuredCount',
      ]),
      suspendedCount: clubInt(json, const <String>[
        'suspended_count',
        'suspendedCount',
      ]),
      availableForNextFixture: clubInt(json, const <String>[
        'available_for_next_fixture',
        'availableForNextFixture',
        'available',
      ]),
      readinessScore: clubNullableNumber(json, const <String>[
        'readiness_score',
        'readinessScore',
      ]),
    );
  }
}

class ClubAcademyDTO {
  const ClubAcademyDTO({
    this.players = const <AcademyPlayerDTO>[],
    this.graduationsPipeline = const <String>[],
    this.facilitiesRating,
  });

  final List<AcademyPlayerDTO> players;
  final List<String> graduationsPipeline;
  final double? facilitiesRating;

  factory ClubAcademyDTO.fromJson(Object? value) {
    final ClubJson json = clubAsMap(value);
    return ClubAcademyDTO(
      players: clubAsList(
        json['players'],
      ).map(AcademyPlayerDTO.fromJson).toList(growable: false),
      graduationsPipeline: clubStringList(
        json['graduations_pipeline'] ??
            json['graduationsPipeline'] ??
            json['promotions'],
      ),
      facilitiesRating: clubNullableNumber(json, const <String>[
        'facilities_rating',
        'facilitiesRating',
      ]),
    );
  }
}

class AcademyPlayerDTO {
  const AcademyPlayerDTO({
    required this.id,
    required this.name,
    this.position,
    this.age,
    this.status,
  });

  final String id;
  final String name;
  final String? position;
  final int? age;
  final String? status;

  factory AcademyPlayerDTO.fromJson(Object? value) {
    final ClubJson json = clubAsMap(value);
    return AcademyPlayerDTO(
      id: clubString(json, const <String>['id', 'player_id', 'playerId']),
      name: clubString(json, const <String>['name', 'player_name']),
      position: clubNullableString(json, const <String>['position']),
      age: clubNullableInt(json, const <String>['age']),
      status: clubNullableString(json, const <String>[
        'status',
        'status_label',
        'statusLabel',
      ]),
    );
  }
}

class ClubStaffDTO {
  const ClubStaffDTO({this.members = const <StaffMemberDTO>[]});

  final List<StaffMemberDTO> members;

  factory ClubStaffDTO.fromJson(Object? value) {
    final ClubJson json = clubAsMap(value);
    final Object? list = json['members'] ?? json['staff'];
    return ClubStaffDTO(
      members: clubAsList(
        list,
      ).map(StaffMemberDTO.fromJson).toList(growable: false),
    );
  }
}

class StaffMemberDTO {
  const StaffMemberDTO({
    required this.role,
    required this.name,
    this.contractEnd,
    this.status,
  });

  final String role;
  final String name;
  final DateTime? contractEnd;
  final String? status;

  factory StaffMemberDTO.fromJson(Object? value) {
    final ClubJson json = clubAsMap(value);
    return StaffMemberDTO(
      role: clubString(json, const <String>['role']),
      name: clubString(json, const <String>['name']),
      contractEnd: clubNullableDate(json, const <String>[
        'contract_end',
        'contractEnd',
      ]),
      status: clubNullableString(json, const <String>['status']),
    );
  }
}

class SponsorshipDTO {
  const SponsorshipDTO({
    required this.id,
    required this.sponsor,
    this.value,
    this.startDate,
    this.endDate,
    this.status,
    this.deliverables = const <String>[],
  });

  final String id;
  final String sponsor;
  final double? value;
  final DateTime? startDate;
  final DateTime? endDate;
  final String? status;
  final List<String> deliverables;

  factory SponsorshipDTO.fromJson(Object? value) {
    final ClubJson json = clubAsMap(value);
    return SponsorshipDTO(
      id: clubString(json, const <String>['id', 'contract_id', 'contractId']),
      sponsor: clubString(json, const <String>[
        'sponsor',
        'sponsor_name',
        'sponsorName',
      ]),
      value: clubNullableNumber(json, const <String>[
        'value',
        'total_value',
        'totalValue',
      ]),
      startDate: clubNullableDate(json, const <String>[
        'start_date',
        'startDate',
      ]),
      endDate: clubNullableDate(json, const <String>['end_date', 'endDate']),
      status: clubNullableString(json, const <String>['status']),
      deliverables: clubStringList(json['deliverables']),
    );
  }
}

class ClubBrandingDTO {
  const ClubBrandingDTO({
    this.badge,
    this.colors = const <String>[],
    this.kit,
    this.assets = const <String>[],
  });

  final String? badge;
  final List<String> colors;
  final String? kit;
  final List<String> assets;

  factory ClubBrandingDTO.fromJson(Object? value) {
    final ClubJson json = clubAsMap(value);
    return ClubBrandingDTO(
      badge: clubNullableString(json, const <String>[
        'badge',
        'badge_url',
        'badgeUrl',
      ]),
      colors: clubStringList(json['colors']),
      kit: clubNullableString(json, const <String>['kit', 'home_kit']),
      assets: clubStringList(json['assets']),
    );
  }
}

class TrophyDTO {
  const TrophyDTO({
    required this.id,
    required this.name,
    this.competition,
    this.season,
    this.type,
  });

  final String id;
  final String name;
  final String? competition;
  final String? season;
  final String? type;

  factory TrophyDTO.fromJson(Object? value) {
    final ClubJson json = clubAsMap(value);
    return TrophyDTO(
      id: clubString(json, const <String>['id']),
      name: clubString(json, const <String>['name']),
      competition: clubNullableString(json, const <String>['competition']),
      season: clubNullableString(json, const <String>['season']),
      type: clubNullableString(json, const <String>['type']),
    );
  }
}

class ClubRankingDTO {
  const ClubRankingDTO({
    required this.rank,
    this.previousRank,
    this.points,
    this.division,
    this.history = const <RankingHistoryPoint>[],
  });

  final int rank;
  final int? previousRank;
  final double? points;
  final String? division;
  final List<RankingHistoryPoint> history;

  factory ClubRankingDTO.fromJson(Object? value) {
    final ClubJson json = clubAsMap(value);
    return ClubRankingDTO(
      rank: clubInt(json, const <String>['rank']),
      previousRank: clubNullableInt(json, const <String>[
        'previous_rank',
        'previousRank',
      ]),
      points: clubNullableNumber(json, const <String>['points']),
      division: clubNullableString(json, const <String>['division']),
      history: clubAsList(
        json['history'],
      ).map(RankingHistoryPoint.fromJson).toList(growable: false),
    );
  }
}

class RankingHistoryPoint {
  const RankingHistoryPoint({required this.label, required this.rank});

  final String label;
  final int rank;

  factory RankingHistoryPoint.fromJson(Object? value) {
    final ClubJson json = clubAsMap(value);
    return RankingHistoryPoint(
      label: clubString(json, const <String>['label', 'week', 'date']),
      rank: clubInt(json, const <String>['rank']),
    );
  }
}

ClubJson clubAsMap(Object? value) {
  if (value is Map<String, Object?>) {
    return value;
  }
  if (value is Map) {
    return value.map(
      (Object? key, Object? nestedValue) =>
          MapEntry<String, Object?>(key.toString(), nestedValue),
    );
  }
  return <String, Object?>{};
}

List<Object?> clubAsList(Object? value) {
  if (value is List<Object?>) {
    return value;
  }
  if (value is List) {
    return List<Object?>.from(value);
  }
  return const <Object?>[];
}

String clubString(ClubJson json, List<String> keys, {String fallback = ''}) {
  return clubNullableString(json, keys) ?? fallback;
}

String? clubNullableString(ClubJson json, List<String> keys) {
  for (final String key in keys) {
    final Object? raw = json[key];
    if (raw == null) {
      continue;
    }
    final String parsed = raw.toString().trim();
    if (parsed.isNotEmpty) {
      return parsed;
    }
  }
  return null;
}

double? clubNullableNumber(ClubJson json, List<String> keys) {
  for (final String key in keys) {
    final Object? raw = json[key];
    if (raw == null) {
      continue;
    }
    if (raw is num) {
      return raw.toDouble();
    }
    final double? parsed = double.tryParse(raw.toString());
    if (parsed != null) {
      return parsed;
    }
  }
  return null;
}

int clubInt(ClubJson json, List<String> keys, {int fallback = 0}) {
  return clubNullableInt(json, keys) ?? fallback;
}

int? clubNullableInt(ClubJson json, List<String> keys) {
  for (final String key in keys) {
    final Object? raw = json[key];
    if (raw == null) {
      continue;
    }
    if (raw is int) {
      return raw;
    }
    if (raw is num) {
      return raw.round();
    }
    final int? parsed = int.tryParse(raw.toString());
    if (parsed != null) {
      return parsed;
    }
  }
  return null;
}

DateTime? clubNullableDate(ClubJson json, List<String> keys) {
  for (final String key in keys) {
    final Object? raw = json[key];
    if (raw == null) {
      continue;
    }
    if (raw is DateTime) {
      return raw.toUtc();
    }
    final DateTime? parsed = DateTime.tryParse(raw.toString());
    if (parsed != null) {
      return parsed.toUtc();
    }
  }
  return null;
}

List<String> clubStringList(Object? value) {
  return clubAsList(value)
      .map((Object? item) {
        if (item is Map) {
          return clubString(clubAsMap(item), const <String>[
            'label',
            'name',
            'title',
            'note',
            'content',
          ]);
        }
        return item?.toString().trim() ?? '';
      })
      .where((String item) => item.isNotEmpty)
      .toList(growable: false);
}
