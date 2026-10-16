import 'package:gte_frontend/data/gte_models.dart';

/// Closed-loop living-star payload from GET /api/players/{id}/living-star.
class GtexRegenLivingStar {
  const GtexRegenLivingStar({
    required this.playerId,
    required this.archetypeCode,
    required this.archetypeLabel,
    required this.archetypeSummary,
    required this.moodCode,
    required this.moodLabel,
    required this.moodSeverity,
    required this.voiceLine,
    required this.voiceTone,
    required this.exitStage,
    required this.exitLabel,
    required this.exitSeverity,
    required this.canPetitionTermination,
    required this.ownerActions,
    required this.promises,
    required this.grievances,
    required this.inboxNotes,
    required this.behaviorBrief,
    this.regenId,
    this.heirStatus,
    this.heirTriggerKey,
    this.heirProspectIds = const <String>[],
    this.isUniqueCollectible = true,
  });

  final String playerId;
  final String? regenId;
  final bool isUniqueCollectible;
  final String archetypeCode;
  final String archetypeLabel;
  final String archetypeSummary;
  final String moodCode;
  final String moodLabel;
  final int moodSeverity;
  final String voiceLine;
  final String voiceTone;
  final String exitStage;
  final String exitLabel;
  final int exitSeverity;
  final bool canPetitionTermination;
  final List<String> ownerActions;
  final List<GtexRegenPromiseMemory> promises;
  final List<String> grievances;
  final List<String> inboxNotes;
  final GtexRegenBehaviorBrief behaviorBrief;
  final String? heirStatus;
  final String? heirTriggerKey;
  final List<String> heirProspectIds;

  factory GtexRegenLivingStar.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen living star',
    );
    final Map<String, Object?> archetype = GteJson.map(
      GteJson.value(json, const <String>['archetype']),
      label: 'archetype',
    );
    final Map<String, Object?> mood = GteJson.map(
      GteJson.value(json, const <String>['mood']),
      label: 'mood',
    );
    final Map<String, Object?> monologue = GteJson.map(
      GteJson.value(json, const <String>['monologue']),
      label: 'monologue',
    );
    final Map<String, Object?> exit = GteJson.map(
      GteJson.value(json, const <String>['exit_ladder', 'exitLadder']),
      label: 'exit ladder',
    );
    final Object? heirRaw = GteJson.value(json, const <String>[
      'heir_spark',
      'heirSpark',
    ]);
    final Map<String, Object?>? heir =
        heirRaw == null
            ? null
            : GteJson.map(heirRaw, label: 'heir spark');

    return GtexRegenLivingStar(
      playerId: GteJson.string(json, const <String>['player_id', 'playerId']),
      regenId: GteJson.stringOrNull(json, const <String>['regen_id', 'regenId']),
      isUniqueCollectible: GteJson.boolean(
        json,
        const <String>['is_unique_collectible', 'isUniqueCollectible'],
        fallback: true,
      ),
      archetypeCode: GteJson.string(archetype, const <String>['code']),
      archetypeLabel: GteJson.string(archetype, const <String>['label']),
      archetypeSummary: GteJson.string(archetype, const <String>['summary']),
      moodCode: GteJson.string(mood, const <String>['code']),
      moodLabel: GteJson.string(mood, const <String>['label']),
      moodSeverity: GteJson.integer(mood, const <String>['severity'], fallback: 0),
      voiceLine: GteJson.string(monologue, const <String>[
        'voice_line',
        'voiceLine',
      ]),
      voiceTone: GteJson.string(
        monologue,
        const <String>['tone'],
        fallback: 'wary',
      ),
      exitStage: GteJson.string(exit, const <String>['stage']),
      exitLabel: GteJson.string(exit, const <String>['label']),
      exitSeverity: GteJson.integer(exit, const <String>['severity'], fallback: 0),
      canPetitionTermination: GteJson.boolean(
        exit,
        const <String>['can_petition_termination', 'canPetitionTermination'],
      ),
      ownerActions: GteJson.typedList(
        exit,
        const <String>['owner_actions', 'ownerActions'],
        (Object? e) => e?.toString() ?? '',
      ).where((String s) => s.trim().isNotEmpty).toList(growable: false),
      promises: GteJson.typedList(
        json,
        const <String>['promises'],
        GtexRegenPromiseMemory.fromJson,
      ),
      grievances: GteJson.typedList(
        json,
        const <String>['grievances'],
        (Object? e) => e?.toString() ?? '',
      ).where((String s) => s.trim().isNotEmpty).toList(growable: false),
      inboxNotes: GteJson.typedList(
        json,
        const <String>['inbox_notes', 'inboxNotes'],
        (Object? e) => e?.toString() ?? '',
      ).where((String s) => s.trim().isNotEmpty).toList(growable: false),
      behaviorBrief: GtexRegenBehaviorBrief.fromJson(
        GteJson.value(json, const <String>['behavior_brief', 'behaviorBrief']),
      ),
      heirStatus: heir == null
          ? null
          : GteJson.stringOrNull(heir, const <String>['status']),
      heirTriggerKey: heir == null
          ? null
          : GteJson.stringOrNull(heir, const <String>[
            'trigger_key',
            'triggerKey',
          ]),
      heirProspectIds: heir == null
          ? const <String>[]
          : GteJson.typedList(
            heir,
            const <String>['prospect_ids', 'prospectIds'],
            (Object? e) => e?.toString() ?? '',
          ).where((String s) => s.trim().isNotEmpty).toList(growable: false),
    );
  }
}

class GtexRegenPromiseMemory {
  const GtexRegenPromiseMemory({
    required this.key,
    required this.statement,
    required this.status,
    required this.broken,
  });

  final String key;
  final String statement;
  final String status;
  final bool broken;

  factory GtexRegenPromiseMemory.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'regen promise',
    );
    return GtexRegenPromiseMemory(
      key: GteJson.string(json, const <String>['key']),
      statement: GteJson.string(json, const <String>['statement']),
      status: GteJson.string(json, const <String>['status'], fallback: 'open'),
      broken: GteJson.boolean(json, const <String>['broken']),
    );
  }
}

class GtexRegenBehaviorBrief {
  const GtexRegenBehaviorBrief({
    required this.playerId,
    required this.riskAppetite,
    required this.pressingIntensity,
    required this.bigGameNerves,
    required this.celebrationHunger,
    required this.captaincyWillingness,
    required this.shotGreed,
    required this.disciplineRisk,
    this.notes = const <String>[],
  });

  final String playerId;
  final double riskAppetite;
  final double pressingIntensity;
  final double bigGameNerves;
  final double celebrationHunger;
  final double captaincyWillingness;
  final double shotGreed;
  final double disciplineRisk;
  final List<String> notes;

  factory GtexRegenBehaviorBrief.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'behavior brief',
    );
    double read(String a, String b) =>
        GteJson.number(json, <String>[a, b], fallback: 0.5);
    return GtexRegenBehaviorBrief(
      playerId: GteJson.string(json, const <String>['player_id', 'playerId']),
      riskAppetite: read('risk_appetite', 'riskAppetite'),
      pressingIntensity: read('pressing_intensity', 'pressingIntensity'),
      bigGameNerves: read('big_game_nerves', 'bigGameNerves'),
      celebrationHunger: read('celebration_hunger', 'celebrationHunger'),
      captaincyWillingness: read('captaincy_willingness', 'captaincyWillingness'),
      shotGreed: read('shot_greed', 'shotGreed'),
      disciplineRisk: read('discipline_risk', 'disciplineRisk'),
      notes: GteJson.typedList(
        json,
        const <String>['notes'],
        (Object? e) => e?.toString() ?? '',
      ).where((String s) => s.trim().isNotEmpty).toList(growable: false),
    );
  }
}
