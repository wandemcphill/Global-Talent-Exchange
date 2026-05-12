import 'package:gte_frontend/data/gte_models.dart';

class NationalTeamCompetition {
  const NationalTeamCompetition({
    required this.id,
    required this.key,
    required this.title,
    required this.seasonLabel,
    required this.regionType,
    required this.ageBand,
    required this.formatType,
    required this.status,
    required this.notes,
    required this.active,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String key;
  final String title;
  final String seasonLabel;
  final String regionType;
  final String ageBand;
  final String formatType;
  final String status;
  final String? notes;
  final bool active;
  final DateTime createdAt;
  final DateTime updatedAt;

  factory NationalTeamCompetition.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'national team competition',
    );
    return NationalTeamCompetition(
      id: GteJson.string(json, <String>['id']),
      key: GteJson.string(json, <String>['key']),
      title: GteJson.string(json, <String>['title']),
      seasonLabel: GteJson.string(json, <String>[
        'season_label',
        'seasonLabel',
      ]),
      regionType: GteJson.string(json, <String>[
        'region_type',
        'regionType',
      ], fallback: 'global'),
      ageBand: GteJson.string(json, <String>[
        'age_band',
        'ageBand',
      ], fallback: 'senior'),
      formatType: GteJson.string(json, <String>[
        'format_type',
        'formatType',
      ], fallback: 'cup'),
      status: GteJson.string(json, <String>['status'], fallback: 'draft'),
      notes: GteJson.stringOrNull(json, <String>['notes']),
      active: GteJson.boolean(json, <String>['active'], fallback: true),
      createdAt: GteJson.dateTime(json, <String>['created_at', 'createdAt']),
      updatedAt: GteJson.dateTime(json, <String>['updated_at', 'updatedAt']),
    );
  }
}

class NationalTeamRentalPlayer {
  const NationalTeamRentalPlayer({
    required this.playerId,
    required this.playerName,
    required this.overallRating,
    required this.primaryPosition,
    required this.currentClubName,
    required this.currentLeagueName,
    required this.nationality,
    required this.countryCode,
    required this.age,
    required this.gsi,
    required this.baseValueCoin,
    required this.loanPriceCoin,
    required this.tierLabel,
    required this.sourceBucket,
    required this.isRegen,
    required this.isPreseededNationalRegen,
    required this.marketEligible,
  });

  final String playerId;
  final String playerName;
  final double? overallRating;
  final String? primaryPosition;
  final String? currentClubName;
  final String? currentLeagueName;
  final String? nationality;
  final String? countryCode;
  final int? age;
  final double? gsi;
  final double? baseValueCoin;
  final double? loanPriceCoin;
  final String? tierLabel;
  final String sourceBucket;
  final bool isRegen;
  final bool isPreseededNationalRegen;
  final bool marketEligible;

  factory NationalTeamRentalPlayer.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'national team rental player',
    );
    return NationalTeamRentalPlayer(
      playerId: GteJson.string(json, <String>['player_id', 'playerId']),
      playerName: GteJson.string(json, <String>['player_name', 'playerName']),
      overallRating: _numberOrNull(json, <String>[
        'overall_rating',
        'overallRating',
      ]),
      primaryPosition: GteJson.stringOrNull(json, <String>[
        'primary_position',
        'primaryPosition',
        'position',
      ]),
      currentClubName: GteJson.stringOrNull(json, <String>[
        'current_club_name',
        'currentClubName',
      ]),
      currentLeagueName: GteJson.stringOrNull(json, <String>[
        'current_league_name',
        'currentLeagueName',
      ]),
      nationality: GteJson.stringOrNull(json, <String>['nationality']),
      countryCode: GteJson.stringOrNull(json, <String>[
        'country_code',
        'countryCode',
      ]),
      age: GteJson.integerOrNull(json, <String>['age']),
      gsi: _numberOrNull(json, <String>['gsi']),
      baseValueCoin: _numberOrNull(json, <String>[
        'base_value_coin',
        'baseValueCoin',
      ]),
      loanPriceCoin: _numberOrNull(json, <String>[
        'loan_price_coin',
        'loanPriceCoin',
      ]),
      tierLabel: GteJson.stringOrNull(json, <String>[
        'tier_label',
        'tierLabel',
      ]),
      sourceBucket: GteJson.string(json, <String>[
        'source_bucket',
        'sourceBucket',
      ], fallback: 'market'),
      isRegen: GteJson.boolean(json, <String>['is_regen', 'isRegen']),
      isPreseededNationalRegen: GteJson.boolean(json, <String>[
        'is_preseeded_national_regen',
        'isPreseededNationalRegen',
      ]),
      marketEligible: GteJson.boolean(json, <String>[
        'market_eligible',
        'marketEligible',
      ], fallback: true),
    );
  }
}

class NationalTeamRentalPlayerCollection {
  const NationalTeamRentalPlayerCollection({
    required this.total,
    required this.items,
  });

  final int total;
  final List<NationalTeamRentalPlayer> items;

  factory NationalTeamRentalPlayerCollection.fromJson(Object? value) {
    if (value is List || value is List<Object?>) {
      final List<NationalTeamRentalPlayer> items = GteJson.list(
        value,
        label: 'national team rental players',
      ).map(NationalTeamRentalPlayer.fromJson).toList(growable: false);
      return NationalTeamRentalPlayerCollection(
        total: items.length,
        items: items,
      );
    }
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'national team rental player collection',
    );
    final List<NationalTeamRentalPlayer> items = GteJson.typedList(
      json,
      <String>['items'],
      NationalTeamRentalPlayer.fromJson,
    );
    return NationalTeamRentalPlayerCollection(
      total: GteJson.integer(json, <String>['total'], fallback: items.length),
      items: items,
    );
  }
}

class NationalTeamEntry {
  const NationalTeamEntry({
    required this.id,
    required this.competitionId,
    required this.countryCode,
    required this.countryName,
    required this.managerUserId,
    required this.squadSize,
    required this.metadata,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String competitionId;
  final String countryCode;
  final String countryName;
  final String? managerUserId;
  final int squadSize;
  final Map<String, Object?> metadata;
  final DateTime createdAt;
  final DateTime updatedAt;

  factory NationalTeamEntry.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'national team entry',
    );
    return NationalTeamEntry(
      id: GteJson.string(json, <String>['id']),
      competitionId: GteJson.string(json, <String>[
        'competition_id',
        'competitionId',
      ]),
      countryCode: GteJson.string(json, <String>[
        'country_code',
        'countryCode',
      ]),
      countryName: GteJson.string(json, <String>[
        'country_name',
        'countryName',
      ]),
      managerUserId: GteJson.stringOrNull(json, <String>[
        'manager_user_id',
        'managerUserId',
      ]),
      squadSize: GteJson.integer(json, <String>[
        'squad_size',
        'squadSize',
      ], fallback: 0),
      metadata: GteJson.map(
        json,
        keys: <String>['metadata_json', 'metadataJson', 'metadata'],
        fallback: const <String, Object?>{},
      ),
      createdAt: GteJson.dateTime(json, <String>['created_at', 'createdAt']),
      updatedAt: GteJson.dateTime(json, <String>['updated_at', 'updatedAt']),
    );
  }
}

double? _numberOrNull(Map<String, Object?> json, List<String> keys) {
  final Object? rawValue = GteJson.value(json, keys);
  if (rawValue == null) {
    return null;
  }
  if (rawValue is num) {
    return rawValue.toDouble();
  }
  return double.tryParse(rawValue.toString());
}

class NationalTeamSquadMember {
  const NationalTeamSquadMember({
    required this.id,
    required this.entryId,
    required this.userId,
    required this.playerName,
    required this.shirtNumber,
    required this.roleLabel,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String entryId;
  final String userId;
  final String playerName;
  final int? shirtNumber;
  final String? roleLabel;
  final String status;
  final DateTime createdAt;
  final DateTime updatedAt;

  factory NationalTeamSquadMember.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'national team squad member',
    );
    return NationalTeamSquadMember(
      id: GteJson.string(json, <String>['id']),
      entryId: GteJson.string(json, <String>['entry_id', 'entryId']),
      userId: GteJson.string(json, <String>['user_id', 'userId']),
      playerName: GteJson.string(json, <String>['player_name', 'playerName']),
      shirtNumber: GteJson.integerOrNull(json, <String>[
        'shirt_number',
        'shirtNumber',
      ]),
      roleLabel: GteJson.stringOrNull(json, <String>[
        'role_label',
        'roleLabel',
      ]),
      status: GteJson.string(json, <String>['status'], fallback: 'selected'),
      createdAt: GteJson.dateTime(json, <String>['created_at', 'createdAt']),
      updatedAt: GteJson.dateTime(json, <String>['updated_at', 'updatedAt']),
    );
  }
}

class NationalTeamManagerHistory {
  const NationalTeamManagerHistory({
    required this.id,
    required this.entryId,
    required this.userId,
    required this.actionType,
    required this.note,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String entryId;
  final String? userId;
  final String actionType;
  final String? note;
  final DateTime createdAt;
  final DateTime updatedAt;

  factory NationalTeamManagerHistory.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'national team history',
    );
    return NationalTeamManagerHistory(
      id: GteJson.string(json, <String>['id']),
      entryId: GteJson.string(json, <String>['entry_id', 'entryId']),
      userId: GteJson.stringOrNull(json, <String>['user_id', 'userId']),
      actionType: GteJson.string(json, <String>['action_type', 'actionType']),
      note: GteJson.stringOrNull(json, <String>['note']),
      createdAt: GteJson.dateTime(json, <String>['created_at', 'createdAt']),
      updatedAt: GteJson.dateTime(json, <String>['updated_at', 'updatedAt']),
    );
  }
}

class NationalTeamEntryDetail {
  const NationalTeamEntryDetail({
    required this.entry,
    required this.squadMembers,
    required this.managerHistory,
  });

  final NationalTeamEntry entry;
  final List<NationalTeamSquadMember> squadMembers;
  final List<NationalTeamManagerHistory> managerHistory;

  factory NationalTeamEntryDetail.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'national team entry detail',
    );
    return NationalTeamEntryDetail(
      entry: NationalTeamEntry.fromJson(json),
      squadMembers: GteJson.typedList(json, <String>[
        'squad_members',
        'squadMembers',
      ], NationalTeamSquadMember.fromJson),
      managerHistory: GteJson.typedList(json, <String>[
        'manager_history',
        'managerHistory',
      ], NationalTeamManagerHistory.fromJson),
    );
  }
}

class NationalTeamUserHistory {
  const NationalTeamUserHistory({
    required this.managedEntries,
    required this.squadMemberships,
  });

  final List<NationalTeamEntry> managedEntries;
  final List<NationalTeamSquadMember> squadMemberships;

  factory NationalTeamUserHistory.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'national team history',
    );
    return NationalTeamUserHistory(
      managedEntries: GteJson.typedList(json, <String>[
        'managed_entries',
        'managedEntries',
      ], NationalTeamEntry.fromJson),
      squadMemberships: GteJson.typedList(json, <String>[
        'squad_memberships',
        'squadMemberships',
      ], NationalTeamSquadMember.fromJson),
    );
  }
}
