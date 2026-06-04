typedef SquadJson = Map<String, Object?>;

enum SquadAvailabilityStatus {
  available,
  injured,
  suspended,
  away,
  unfit,
  unknown,
}

SquadAvailabilityStatus squadAvailabilityFromRaw(String raw) {
  switch (raw.trim().toLowerCase()) {
    case 'available':
      return SquadAvailabilityStatus.available;
    case 'injured':
      return SquadAvailabilityStatus.injured;
    case 'suspended':
      return SquadAvailabilityStatus.suspended;
    case 'away':
    case 'international_duty':
      return SquadAvailabilityStatus.away;
    case 'unfit':
      return SquadAvailabilityStatus.unfit;
    default:
      return SquadAvailabilityStatus.unknown;
  }
}

extension SquadAvailabilityStatusLabel on SquadAvailabilityStatus {
  String get label {
    return switch (this) {
      SquadAvailabilityStatus.available => 'Available',
      SquadAvailabilityStatus.injured => 'Injured',
      SquadAvailabilityStatus.suspended => 'Suspended',
      SquadAvailabilityStatus.away => 'Away',
      SquadAvailabilityStatus.unfit => 'Unfit',
      SquadAvailabilityStatus.unknown => 'Unknown',
    };
  }
}

class SquadOperationsSnapshot {
  const SquadOperationsSnapshot({
    required this.roster,
    required this.availabilityMatrix,
    required this.injuries,
    required this.chemistry,
    required this.contracts,
    required this.scoutingNotes,
  });

  final List<SquadPlayerDTO> roster;
  final AvailabilityMatrix availabilityMatrix;
  final List<InjuryDTO> injuries;
  final ChemistryReport chemistry;
  final List<ContractStatusDTO> contracts;
  final List<ScoutingNoteDTO> scoutingNotes;

  int get availableCount =>
      roster
          .where(
            (SquadPlayerDTO player) =>
                player.availability == SquadAvailabilityStatus.available,
          )
          .length;

  int get injuredCount =>
      roster
          .where(
            (SquadPlayerDTO player) =>
                player.availability == SquadAvailabilityStatus.injured,
          )
          .length;

  int get suspendedCount =>
      roster
          .where(
            (SquadPlayerDTO player) =>
                player.availability == SquadAvailabilityStatus.suspended,
          )
          .length;

  int get selectionReadyCount =>
      roster.where((SquadPlayerDTO player) => player.selectionReady).length;
}

class SquadPlayerDTO {
  const SquadPlayerDTO({
    required this.id,
    required this.name,
    required this.position,
    this.age,
    this.nationality,
    required this.availability,
    this.injuryDetail,
    required this.morale,
    required this.chemistryFit,
    required this.contractStatus,
    required this.selectionReady,
    this.scoutingNotes = const <ScoutingNoteDTO>[],
    required this.stats,
  });

  final String id;
  final String name;
  final String position;
  final int? age;
  final String? nationality;
  final SquadAvailabilityStatus availability;
  final InjuryDTO? injuryDetail;
  final MoraleScore morale;
  final ChemistryFitDTO chemistryFit;
  final ContractStatusDTO contractStatus;
  final bool selectionReady;
  final List<ScoutingNoteDTO> scoutingNotes;
  final PlayerStatsDTO stats;

  factory SquadPlayerDTO.fromJson(Object? value) {
    final SquadJson json = squadAsMap(value);
    return SquadPlayerDTO(
      id: squadString(json, const <String>['id', 'player_id', 'playerId']),
      name: squadString(json, const <String>['name', 'player_name']),
      position: squadString(json, const <String>['position'], fallback: 'N/A'),
      age: squadNullableInt(json, const <String>['age']),
      nationality: squadNullableString(json, const <String>['nationality']),
      availability: squadAvailabilityFromRaw(
        squadString(
          squadAsMap(json['availability']),
          const <String>['status'],
          fallback: squadString(json, const <String>['availability']),
        ),
      ),
      injuryDetail:
          json['injury_detail'] == null && json['injuryDetail'] == null
              ? null
              : InjuryDTO.fromJson(
                json['injury_detail'] ?? json['injuryDetail'],
              ),
      morale: MoraleScore.fromJson(json['morale']),
      chemistryFit: ChemistryFitDTO.fromJson(
        json['chemistry_fit'] ?? json['chemistryFit'],
      ),
      contractStatus: ContractStatusDTO.fromJson(
        json['contract_status'] ?? json['contractStatus'],
        fallbackPlayerId: squadString(json, const <String>[
          'id',
          'player_id',
          'playerId',
        ]),
      ),
      selectionReady: squadBool(json, const <String>[
        'selection_ready',
        'selectionReady',
      ]),
      scoutingNotes: squadAsList(
        json['scouting_notes'] ?? json['scoutingNotes'],
      ).map(ScoutingNoteDTO.fromJson).toList(growable: false),
      stats: PlayerStatsDTO.fromJson(json['stats']),
    );
  }
}

class InjuryDTO {
  const InjuryDTO({
    this.playerId,
    this.playerName,
    this.type,
    this.expectedReturn,
    this.severity,
    this.injuryDate,
  });

  final String? playerId;
  final String? playerName;
  final String? type;
  final DateTime? expectedReturn;
  final String? severity;
  final DateTime? injuryDate;

  factory InjuryDTO.fromJson(Object? value) {
    final SquadJson json = squadAsMap(value);
    return InjuryDTO(
      playerId: squadNullableString(json, const <String>[
        'player_id',
        'playerId',
      ]),
      playerName: squadNullableString(json, const <String>[
        'player_name',
        'playerName',
      ]),
      type: squadNullableString(json, const <String>['type']),
      expectedReturn: squadNullableDate(json, const <String>[
        'expected_return',
        'expectedReturn',
      ]),
      severity: squadNullableString(json, const <String>['severity']),
      injuryDate: squadNullableDate(json, const <String>[
        'injury_date',
        'injuryDate',
      ]),
    );
  }
}

class MoraleScore {
  const MoraleScore({required this.score, required this.label, this.trend});

  final int score;
  final String label;
  final String? trend;

  factory MoraleScore.fromJson(Object? value) {
    final SquadJson json = squadAsMap(value);
    return MoraleScore(
      score: squadInt(json, const <String>['score']),
      label: squadString(json, const <String>['label'], fallback: 'unknown'),
      trend: squadNullableString(json, const <String>['trend']),
    );
  }
}

class ChemistryFitDTO {
  const ChemistryFitDTO({
    required this.overallScore,
    required this.positionFit,
    required this.teamFit,
    this.warnings = const <String>[],
  });

  final int overallScore;
  final int positionFit;
  final int teamFit;
  final List<String> warnings;

  factory ChemistryFitDTO.fromJson(Object? value) {
    final SquadJson json = squadAsMap(value);
    return ChemistryFitDTO(
      overallScore: squadInt(json, const <String>[
        'overall_score',
        'overallScore',
      ]),
      positionFit: squadInt(json, const <String>[
        'position_fit',
        'positionFit',
      ]),
      teamFit: squadInt(json, const <String>['team_fit', 'teamFit']),
      warnings: squadStringList(json['warnings']),
    );
  }
}

class ChemistryReport {
  const ChemistryReport({this.overallScore, this.warnings = const <String>[]});

  final int? overallScore;
  final List<String> warnings;

  factory ChemistryReport.fromJson(Object? value) {
    final SquadJson json = squadAsMap(value);
    return ChemistryReport(
      overallScore: squadNullableInt(json, const <String>[
        'overall_score',
        'overallScore',
      ]),
      warnings: squadStringList(json['warnings']),
    );
  }
}

class ContractStatusDTO {
  const ContractStatusDTO({
    this.playerId,
    this.playerName,
    this.endDate,
    this.status,
    this.weeksRemaining,
    this.alert,
  });

  final String? playerId;
  final String? playerName;
  final DateTime? endDate;
  final String? status;
  final int? weeksRemaining;
  final String? alert;

  bool get isRenewalRisk => weeksRemaining != null && weeksRemaining! < 26;

  factory ContractStatusDTO.fromJson(
    Object? value, {
    String? fallbackPlayerId,
  }) {
    final SquadJson json = squadAsMap(value);
    return ContractStatusDTO(
      playerId:
          squadNullableString(json, const <String>['player_id', 'playerId']) ??
          fallbackPlayerId,
      playerName: squadNullableString(json, const <String>[
        'player_name',
        'playerName',
      ]),
      endDate: squadNullableDate(json, const <String>['end_date', 'endDate']),
      status: squadNullableString(json, const <String>['status']),
      weeksRemaining: squadNullableInt(json, const <String>[
        'weeks_remaining',
        'weeksRemaining',
      ]),
      alert: squadNullableString(json, const <String>['alert']),
    );
  }
}

class ScoutingNoteDTO {
  const ScoutingNoteDTO({
    this.playerId,
    this.authorId,
    required this.content,
    this.createdAt,
    this.tags = const <String>[],
  });

  final String? playerId;
  final String? authorId;
  final String content;
  final DateTime? createdAt;
  final List<String> tags;

  factory ScoutingNoteDTO.fromJson(Object? value) {
    final SquadJson json = squadAsMap(value);
    return ScoutingNoteDTO(
      playerId: squadNullableString(json, const <String>[
        'player_id',
        'playerId',
      ]),
      authorId: squadNullableString(json, const <String>[
        'author_id',
        'authorId',
      ]),
      content: squadString(json, const <String>['content', 'note']),
      createdAt: squadNullableDate(json, const <String>[
        'created_at',
        'createdAt',
      ]),
      tags: squadStringList(json['tags']),
    );
  }
}

class PlayerStatsDTO {
  const PlayerStatsDTO({this.appearances, this.rating});

  final int? appearances;
  final double? rating;

  factory PlayerStatsDTO.fromJson(Object? value) {
    final SquadJson json = squadAsMap(value);
    return PlayerStatsDTO(
      appearances: squadNullableInt(json, const <String>['appearances']),
      rating: squadNullableNumber(json, const <String>['rating']),
    );
  }
}

class AvailabilityMatrix {
  const AvailabilityMatrix({
    this.players = const <AvailabilityMatrixPlayer>[],
    this.fixtures = const <AvailabilityFixture>[],
    this.cells = const <AvailabilityCell>[],
    this.rows = const <AvailabilityRow>[],
  });

  final List<AvailabilityMatrixPlayer> players;
  final List<AvailabilityFixture> fixtures;
  final List<AvailabilityCell> cells;
  final List<AvailabilityRow> rows;

  bool get hasPlayers => players.isNotEmpty || rows.isNotEmpty;

  factory AvailabilityMatrix.fromJson(Object? value) {
    final SquadJson json = squadAsMap(value);
    return AvailabilityMatrix(
      players: squadAsList(
        json['players'],
      ).map(AvailabilityMatrixPlayer.fromJson).toList(growable: false),
      fixtures: squadAsList(
        json['fixtures'],
      ).map(AvailabilityFixture.fromJson).toList(growable: false),
      cells: squadAsList(
        json['cells'],
      ).map(AvailabilityCell.fromJson).toList(growable: false),
      rows: squadAsList(
        json['rows'],
      ).map(AvailabilityRow.fromJson).toList(growable: false),
    );
  }
}

class AvailabilityRow {
  const AvailabilityRow({
    this.playerId = '',
    this.name = '',
    this.position = '',
    this.statuses = const <SquadAvailabilityStatus>[],
  });

  final String playerId;
  final String name;
  final String position;
  final List<SquadAvailabilityStatus> statuses;

  factory AvailabilityRow.fromJson(Object? value) {
    final SquadJson json = squadAsMap(value);
    return AvailabilityRow(
      playerId: squadString(json, const <String>[
        'player_id',
        'playerId',
        'id',
      ]),
      name: squadString(json, const <String>['name', 'player_name']),
      position: squadString(json, const <String>['position']),
      statuses: squadAsList(json['statuses'])
          .map(
            (Object? status) =>
                squadAvailabilityFromRaw(status?.toString() ?? ''),
          )
          .toList(growable: false),
    );
  }
}

class AvailabilityMatrixPlayer {
  const AvailabilityMatrixPlayer({
    required this.playerId,
    required this.name,
    required this.position,
  });

  final String playerId;
  final String name;
  final String position;

  factory AvailabilityMatrixPlayer.fromJson(Object? value) {
    final SquadJson json = squadAsMap(value);
    return AvailabilityMatrixPlayer(
      playerId: squadString(json, const <String>[
        'player_id',
        'playerId',
        'id',
      ]),
      name: squadString(json, const <String>['name', 'player_name']),
      position: squadString(json, const <String>['position'], fallback: 'N/A'),
    );
  }
}

class AvailabilityFixture {
  const AvailabilityFixture({required this.fixtureId, required this.label});

  final String fixtureId;
  final String label;

  factory AvailabilityFixture.fromJson(Object? value) {
    final SquadJson json = squadAsMap(value);
    return AvailabilityFixture(
      fixtureId: squadString(json, const <String>[
        'fixture_id',
        'fixtureId',
        'id',
      ]),
      label: squadString(json, const <String>['label', 'opponent', 'name']),
    );
  }
}

class AvailabilityCell {
  const AvailabilityCell({
    required this.playerId,
    required this.fixtureId,
    required this.status,
  });

  final String playerId;
  final String fixtureId;
  final SquadAvailabilityStatus status;

  factory AvailabilityCell.fromJson(Object? value) {
    final SquadJson json = squadAsMap(value);
    return AvailabilityCell(
      playerId: squadString(json, const <String>['player_id', 'playerId']),
      fixtureId: squadString(json, const <String>['fixture_id', 'fixtureId']),
      status: squadAvailabilityFromRaw(
        squadString(json, const <String>['status']),
      ),
    );
  }
}

SquadJson squadAsMap(Object? value) {
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

List<Object?> squadAsList(Object? value) {
  if (value is List<Object?>) {
    return value;
  }
  if (value is List) {
    return List<Object?>.from(value);
  }
  return const <Object?>[];
}

String squadString(SquadJson json, List<String> keys, {String fallback = ''}) {
  return squadNullableString(json, keys) ?? fallback;
}

String? squadNullableString(SquadJson json, List<String> keys) {
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

double? squadNullableNumber(SquadJson json, List<String> keys) {
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

int squadInt(SquadJson json, List<String> keys, {int fallback = 0}) {
  return squadNullableInt(json, keys) ?? fallback;
}

int? squadNullableInt(SquadJson json, List<String> keys) {
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

bool squadBool(SquadJson json, List<String> keys, {bool fallback = false}) {
  for (final String key in keys) {
    final Object? raw = json[key];
    if (raw == null) {
      continue;
    }
    if (raw is bool) {
      return raw;
    }
    final String normalized = raw.toString().toLowerCase().trim();
    if (normalized == 'true' || normalized == '1' || normalized == 'yes') {
      return true;
    }
    if (normalized == 'false' || normalized == '0' || normalized == 'no') {
      return false;
    }
  }
  return fallback;
}

DateTime? squadNullableDate(SquadJson json, List<String> keys) {
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

List<String> squadStringList(Object? value) {
  return squadAsList(value)
      .map((Object? item) {
        if (item is Map) {
          return squadString(squadAsMap(item), const <String>[
            'label',
            'name',
            'title',
            'content',
            'note',
          ]);
        }
        return item?.toString().trim() ?? '';
      })
      .where((String item) => item.isNotEmpty)
      .toList(growable: false);
}
