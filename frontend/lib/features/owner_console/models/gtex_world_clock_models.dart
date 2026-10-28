/// Typed models for the authoritative GTEX world clock and the owner daily briefing.
///
/// World clock contract: `GET /api/world/clock` (Global-Talent-Exchange PR #347). Game time is
/// only ever what the server returned; nothing here reads the device clock or runs timers.
///
/// Briefing: Verified events only.
library;

const String kWorldClockPath = '/api/world/clock';
const String? kOwnerBriefingEndpoint = null;

class WorldClockContractException implements Exception {
  const WorldClockContractException(this.message);
  final String message;
  @override
  String toString() => 'world_clock_contract_violation: $message';
}

final RegExp _isoDate = RegExp(r'^\d{4}-\d{2}-\d{2}$');
final RegExp _isoDateTimeWithOffset = RegExp(
  r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})$',
);

const List<String> _months = <String>[
  'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
  'September', 'October', 'November', 'December',
];
const List<String> _weekdays = <String>['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

typedef GtexWorldClockSnapshot = WorldClock;

class WorldClock {
  const WorldClock({
    required this.clockId,
    required this.worldTime,
    required this.worldDate,
    required this.isPaused,
    required this.progressionRate,
    required this.virtualMonthsPerSeason,
    this.gtexYearsRunning = 1,
    this.currentSeasonNumber = 1,
    this.currentSeasonLabel = 'GTEX Year 1 · Season 1',
  });

  /// Strictly validates the published schema; anything else is rejected rather than guessed.
  factory WorldClock.fromJson(Object? raw) {
    if (raw is! Map) {
      throw const WorldClockContractException('response is not an object');
    }
    final Map<Object?, Object?> r = raw;
    final Object? rawClockId = r['clock_id'];
    if (r.containsKey('clock_id')) {
      if (rawClockId is! String || rawClockId.trim().isEmpty) {
        throw const WorldClockContractException('clock_id missing');
      }
    } else if (!r.containsKey('virtual_time_utc')) {
      throw const WorldClockContractException('clock_id missing');
    }
    final String clockId = (rawClockId is String && rawClockId.trim().isNotEmpty)
        ? rawClockId.trim()
        : 'global';

    final Object? time = r['world_time'] ?? r['virtual_time_utc'];
    if (time is! String || !_isoDateTimeWithOffset.hasMatch(time)) {
      throw const WorldClockContractException(
        'world_time must be an ISO timestamp with an explicit UTC offset',
      );
    }
    final DateTime? instant = DateTime.tryParse(time)?.toUtc();
    if (instant == null) {
      throw const WorldClockContractException('world_time is not a valid instant');
    }
    final Object? rawDate = r['world_date'] ??
        (r['current_day'] != null ? instant.toIso8601String().substring(0, 10) : null);
    if (rawDate is! String || !_isoDate.hasMatch(rawDate)) {
      throw const WorldClockContractException('world_date must be YYYY-MM-DD');
    }
    if (instant.toIso8601String().substring(0, 10) != rawDate) {
      throw const WorldClockContractException(
        'world_date does not match the UTC date of world_time',
      );
    }
    final Object? paused = r['is_paused'];
    if (paused is! bool) {
      throw const WorldClockContractException('is_paused must be a boolean');
    }
    final Object? rate = r['progression_rate'] ?? r['tick_Hours'];
    if (rate is! num || !rate.isFinite || rate <= 0) {
      throw const WorldClockContractException('progression_rate must be a positive number');
    }
    final Object? months = r['virtual_months_per_season'] ?? 12;
    if (months is! num || months != months.truncate() || months < 1) {
      throw const WorldClockContractException(
        'virtual_months_per_season must be an integer >= 1',
      );
    }

    final int yearsRunning = switch (r['gtex_years_running']) {
      final num n when n > 0 => n.toInt(),
      final String s when int.tryParse(s) != null && int.parse(s) > 0 => int.parse(s),
      _ => 1,
    };
    final int seasonNumber = switch (r['current_season_number']) {
      final num n when n > 0 => n.toInt(),
      final String s when int.tryParse(s) != null && int.parse(s) > 0 => int.parse(s),
      _ => 1,
    };
    final String seasonLabel = switch (r['current_season_label']) {
      final String s when s.trim().isNotEmpty => s.trim(),
      _ => 'GTEX Year $yearsRunning · Season $seasonNumber',
    };

    return WorldClock(
      clockId: clockId,
      worldTime: instant,
      worldDate: rawDate,
      isPaused: paused,
      progressionRate: rate.toDouble(),
      virtualMonthsPerSeason: months.toInt(),
      gtexYearsRunning: yearsRunning,
      currentSeasonNumber: seasonNumber,
      currentSeasonLabel: seasonLabel,
    );
  }

  final String clockId;

  /// Server-issued virtual instant (UTC).
  final DateTime worldTime;

  /// Server-issued virtual date, `YYYY-MM-DD`.
  final String worldDate;
  final bool isPaused;
  final double progressionRate;
  final int virtualMonthsPerSeason;
  final int gtexYearsRunning;
  final int currentSeasonNumber;
  final String currentSeasonLabel;

  /// e.g. `Fri, 14 March 2031`, derived from the server's date string only.
  String get displayDate {
    final List<int> p = worldDate.split('-').map(int.parse).toList();
    final DateTime d = DateTime.utc(p[0], p[1], p[2]);
    return '${_weekdays[d.weekday - 1]}, ${d.day} ${_months[d.month - 1]} ${d.year}';
  }

  /// e.g. `09:05 UTC`.
  String get displayTime {
    String two(int v) => v.toString().padLeft(2, '0');
    return '${two(worldTime.hour)}:${two(worldTime.minute)} UTC';
  }

  String get displayRate {
    final String t = progressionRate.toStringAsFixed(4).replaceFirst(RegExp(r'\.?0+$'), '');
    return '${t}x';
  }

  String get displaySeasonBadge => currentSeasonLabel;
}

enum BriefingTargetType { decision, clubHistory, matchResult }

class BriefingTarget {
  const BriefingTarget(this.type, this.id);
  final BriefingTargetType type;
  final String id;

  static BriefingTarget? tryParse(Object? raw) {
    if (raw is! Map) return null;
    String? text(Object? v) {
      final String t = '${v ?? ''}'.trim();
      return t.isEmpty ? null : t;
    }

    switch (raw['type']) {
      case 'decision':
        final String? id = text(raw['inbox_item_id']);
        return id == null ? null : BriefingTarget(BriefingTargetType.decision, id);
      case 'club_history':
        final String? id = text(raw['club_id']);
        return id == null ? null : BriefingTarget(BriefingTargetType.clubHistory, id);
      case 'match_result':
        final String? id = text(raw['match_id']);
        return id == null ? null : BriefingTarget(BriefingTargetType.matchResult, id);
    }
    return null;
  }

  /// Existing Flutter destinations: private decision inbox, public club profile, 2D match viewer.
  /// The inbox route is owned by the separate B2 inbox-routing work and is referenced only here.
  String get route {
    switch (type) {
      case BriefingTargetType.decision:
        return '/app/inbox';
      case BriefingTargetType.clubHistory:
        return '/clubs/${Uri.encodeComponent(id)}/profile';
      case BriefingTargetType.matchResult:
        return '/matches/viewer/${Uri.encodeComponent(id)}';
    }
  }

  String get label {
    switch (type) {
      case BriefingTargetType.decision:
        return 'Open decision';
      case BriefingTargetType.clubHistory:
        return 'View club history';
      case BriefingTargetType.matchResult:
        return 'View match result';
    }
  }
}

class BriefingEvent {
  const BriefingEvent({
    required this.eventId,
    required this.headline,
    required this.occurredAt,
    this.detail,
    this.target,
  });
  final String eventId;
  final String headline;
  final String occurredAt;
  final String? detail;
  final BriefingTarget? target;
}

typedef GtexOwnerBriefing = OwnerBriefing;

class BoardroomDilemmaChoice {
  const BoardroomDilemmaChoice({
    required this.choiceId,
    required this.label,
    required this.summary,
    required this.backedRole,
    required this.effectsPreview,
  });

  factory BoardroomDilemmaChoice.fromJson(Object? raw) {
    if (raw is! Map) {
      return const BoardroomDilemmaChoice(
        choiceId: '',
        label: '',
        summary: '',
        backedRole: '',
        effectsPreview: '',
      );
    }
    final Map<Object?, Object?> m = raw;
    String text(Object? v) => '${v ?? ''}'.trim();
    return BoardroomDilemmaChoice(
      choiceId: text(m['choice_id']),
      label: text(m['label']),
      summary: text(m['summary']),
      backedRole: text(m['backed_role']),
      effectsPreview: text(m['effects_preview']),
    );
  }

  final String choiceId;
  final String label;
  final String summary;
  final String backedRole;
  final String effectsPreview;

  Map<String, dynamic> toJson() => <String, dynamic>{
    'choice_id': choiceId,
    'label': label,
    'summary': summary,
    'backed_role': backedRole,
    'effects_preview': effectsPreview,
  };
}

class BoardroomDilemma {
  const BoardroomDilemma({
    required this.dilemmaId,
    required this.title,
    required this.conflictSummary,
    required this.roleA,
    required this.roleB,
    this.status = 'open',
    this.selectedChoiceId,
    this.resolutionOutcome,
    this.choices = const <BoardroomDilemmaChoice>[],
  });

  factory BoardroomDilemma.fromJson(Object? raw) {
    if (raw is! Map) {
      return const BoardroomDilemma(
        dilemmaId: '',
        title: '',
        conflictSummary: '',
        roleA: '',
        roleB: '',
      );
    }
    final Map<Object?, Object?> m = raw;
    String text(Object? v) => '${v ?? ''}'.trim();
    String? optText(Object? v) {
      final String t = text(v);
      return t.isEmpty || t == 'null' ? null : t;
    }

    final List<BoardroomDilemmaChoice> choices = <BoardroomDilemmaChoice>[];
    final Object? rawChoices = m['choices'];
    if (rawChoices is List) {
      for (final Object? c in rawChoices) {
        if (c is Map) {
          choices.add(BoardroomDilemmaChoice.fromJson(c));
        }
      }
    }

    return BoardroomDilemma(
      dilemmaId: text(m['dilemma_id']),
      title: text(m['title']),
      conflictSummary: text(m['conflict_summary']),
      roleA: text(m['role_a']),
      roleB: text(m['role_b']),
      status: text(m['status']).isEmpty ? 'open' : text(m['status']),
      selectedChoiceId: optText(m['selected_choice_id']),
      resolutionOutcome: optText(m['resolution_outcome']),
      choices: choices,
    );
  }

  final String dilemmaId;
  final String title;
  final String conflictSummary;
  final String roleA;
  final String roleB;
  final String status;
  final String? selectedChoiceId;
  final String? resolutionOutcome;
  final List<BoardroomDilemmaChoice> choices;

  bool get isResolved => status == 'resolved' || (selectedChoiceId != null && selectedChoiceId!.isNotEmpty);

  Map<String, dynamic> toJson() => <String, dynamic>{
    'dilemma_id': dilemmaId,
    'title': title,
    'conflict_summary': conflictSummary,
    'role_a': roleA,
    'role_b': roleB,
    'status': status,
    'selected_choice_id': selectedChoiceId,
    'resolution_outcome': resolutionOutcome,
    'choices': choices.map((c) => c.toJson()).toList(),
  };

  BoardroomDilemma copyWith({
    String? dilemmaId,
    String? title,
    String? conflictSummary,
    String? roleA,
    String? roleB,
    String? status,
    String? selectedChoiceId,
    String? resolutionOutcome,
    List<BoardroomDilemmaChoice>? choices,
  }) => BoardroomDilemma(
    dilemmaId: dilemmaId ?? this.dilemmaId,
    title: title ?? this.title,
    conflictSummary: conflictSummary ?? this.conflictSummary,
    roleA: roleA ?? this.roleA,
    roleB: roleB ?? this.roleB,
    status: status ?? this.status,
    selectedChoiceId: selectedChoiceId ?? this.selectedChoiceId,
    resolutionOutcome: resolutionOutcome ?? this.resolutionOutcome,
    choices: choices ?? this.choices,
  );
}

class OwnerBriefing {
  const OwnerBriefing({
    required this.briefingId,
    required this.clubId,
    required this.worldDate,
    required this.events,
    this.rejectedEventCount = 0,
    this.explanation,
    this.boardroomDilemma,
  });

  factory OwnerBriefing.fromJson(Object? raw) {
    String? text(Object? v) {
      final String t = '${v ?? ''}'.trim();
      return t.isEmpty || t == 'null' ? null : t;
    }

    if (raw is! Map) throw const FormatException('owner_briefing_contract_violation');
    final String? id = text(raw['briefing_id']);
    final String? club = text(raw['club_id']);
    final String? date = text(raw['world_date']);
    if (id == null || club == null || date == null) {
      throw const FormatException('owner_briefing_contract_violation');
    }
    final List<BriefingEvent> events = <BriefingEvent>[];
    int rejected = 0;
    for (final Object? e in (raw['events'] is List ? raw['events'] as List : const <Object?>[])) {
      final Map<Object?, Object?>? m = e is Map ? e : null;
      final String? eventId = text(m?['event_id']);
      final String? headline = text(m?['headline']);
      final String? at = text(m?['occurred_at']);
      if (eventId == null || headline == null || at == null) {
        rejected++;
        continue;
      }
      events.add(BriefingEvent(
        eventId: eventId,
        headline: headline,
        occurredAt: at,
        detail: text(m?['detail']),
        target: BriefingTarget.tryParse(m?['target']),
      ));
    }

    final Object? rawDilemma = raw['boardroom_dilemma'] ?? raw['dilemma'];
    final BoardroomDilemma? dilemma = rawDilemma is Map
        ? BoardroomDilemma.fromJson(rawDilemma)
        : null;

    return OwnerBriefing(
      briefingId: id,
      clubId: club,
      worldDate: date,
      events: events,
      rejectedEventCount: rejected,
      explanation: text(raw['explanation']),
      boardroomDilemma: dilemma,
    );
  }

  final String briefingId;
  final String clubId;
  final String worldDate;
  final List<BriefingEvent> events;
  final int rejectedEventCount;

  /// Optional AI prose. Explanatory only; never the source of game facts.
  final String? explanation;

  /// Interactive multi-choice boardroom dilemma presented during the briefing.
  final BoardroomDilemma? boardroomDilemma;

  OwnerBriefing copyWith({
    String? briefingId,
    String? clubId,
    String? worldDate,
    List<BriefingEvent>? events,
    int? rejectedEventCount,
    String? explanation,
    BoardroomDilemma? boardroomDilemma,
  }) => OwnerBriefing(
    briefingId: briefingId ?? this.briefingId,
    clubId: clubId ?? this.clubId,
    worldDate: worldDate ?? this.worldDate,
    events: events ?? this.events,
    rejectedEventCount: rejectedEventCount ?? this.rejectedEventCount,
    explanation: explanation ?? this.explanation,
    boardroomDilemma: boardroomDilemma ?? this.boardroomDilemma,
  );
}

class GtexSponsorOffer {
  const GtexSponsorOffer({
    required this.offerId,
    required this.sponsorName,
    required this.slot,
    required this.strategyProfile,
    required this.upfrontSigningBonusGtex,
    required this.perMatchGrossGtex,
    required this.winBonusClauseGtex,
    required this.matchesDuration,
    required this.minPrestigeRequired,
    required this.locked,
    required this.gmRecommendation,
  });

  factory GtexSponsorOffer.fromJson(Object? raw) {
    if (raw is! Map) {
      return const GtexSponsorOffer(
        offerId: '',
        sponsorName: '',
        slot: '',
        strategyProfile: '',
        upfrontSigningBonusGtex: 0,
        perMatchGrossGtex: 0,
        winBonusClauseGtex: 0,
        matchesDuration: 0,
        minPrestigeRequired: 0,
        locked: false,
        gmRecommendation: '',
      );
    }
    final Map<Object?, Object?> m = raw;
    String text(Object? v) => '${v ?? ''}'.trim();
    int intVal(Object? v) => v is num ? v.toInt() : int.tryParse(text(v)) ?? 0;
    return GtexSponsorOffer(
      offerId: text(m['offer_id']),
      sponsorName: text(m['sponsor_name']),
      slot: text(m['slot']),
      strategyProfile: text(m['strategy_profile']),
      upfrontSigningBonusGtex: intVal(m['upfront_signing_bonus_gtex']),
      perMatchGrossGtex: intVal(m['per_match_gross_gtex']),
      winBonusClauseGtex: intVal(m['win_bonus_clause_gtex']),
      matchesDuration: intVal(m['matches_duration']),
      minPrestigeRequired: intVal(m['min_prestige_required']),
      locked: m['locked'] == true,
      gmRecommendation: text(m['gm_recommendation']),
    );
  }

  final String offerId;
  final String sponsorName;
  final String slot;
  final String strategyProfile;
  final int upfrontSigningBonusGtex;
  final int perMatchGrossGtex;
  final int winBonusClauseGtex;
  final int matchesDuration;
  final int minPrestigeRequired;
  final bool locked;
  final String gmRecommendation;

  Map<String, dynamic> toJson() => <String, dynamic>{
    'offer_id': offerId,
    'sponsor_name': sponsorName,
    'slot': slot,
    'strategy_profile': strategyProfile,
    'upfront_signing_bonus_gtex': upfrontSigningBonusGtex,
    'per_match_gross_gtex': perMatchGrossGtex,
    'win_bonus_clause_gtex': winBonusClauseGtex,
    'matches_duration': matchesDuration,
    'min_prestige_required': minPrestigeRequired,
    'locked': locked,
    'gm_recommendation': gmRecommendation,
  };
}

class GtexSponsorOffersPayload {
  const GtexSponsorOffersPayload({
    required this.gmName,
    required this.gmNegotiation,
    required this.clubPrestige,
    required this.prestigeTier,
    required this.activeWinBonusClauseGtex,
    required this.offers,
    this.activeDeals = const <Map<String, dynamic>>[],
  });

  factory GtexSponsorOffersPayload.fromJson(Object? raw) {
    if (raw is! Map) {
      return const GtexSponsorOffersPayload(
        gmName: 'General Manager',
        gmNegotiation: 10,
        clubPrestige: 20,
        prestigeTier: 'Contender',
        activeWinBonusClauseGtex: 0,
        offers: <GtexSponsorOffer>[],
      );
    }
    final Map<Object?, Object?> m = raw;
    String text(Object? v) => '${v ?? ''}'.trim();
    int intVal(Object? v) => v is num ? v.toInt() : int.tryParse(text(v)) ?? 0;

    final List<GtexSponsorOffer> offers = <GtexSponsorOffer>[];
    final Object? rawOffers = m['offers'];
    if (rawOffers is List) {
      for (final Object? item in rawOffers) {
        if (item is Map) {
          offers.add(GtexSponsorOffer.fromJson(item));
        }
      }
    }

    final List<Map<String, dynamic>> activeDeals = <Map<String, dynamic>>[];
    final Object? rawDeals = m['active_deals'];
    if (rawDeals is List) {
      for (final Object? d in rawDeals) {
        if (d is Map) {
          activeDeals.add(Map<String, dynamic>.from(d));
        }
      }
    }

    return GtexSponsorOffersPayload(
      gmName: text(m['gm_name']).isEmpty ? 'General Manager' : text(m['gm_name']),
      gmNegotiation: intVal(m['gm_negotiation']),
      clubPrestige: intVal(m['club_prestige']),
      prestigeTier: text(m['prestige_tier']).isEmpty ? 'Contender' : text(m['prestige_tier']),
      activeWinBonusClauseGtex: intVal(m['active_win_bonus_clause_gtex']),
      offers: offers,
      activeDeals: activeDeals,
    );
  }

  final String gmName;
  final int gmNegotiation;
  final int clubPrestige;
  final String prestigeTier;
  final int activeWinBonusClauseGtex;
  final List<GtexSponsorOffer> offers;
  final List<Map<String, dynamic>> activeDeals;

  Map<String, dynamic> toJson() => <String, dynamic>{
    'gm_name': gmName,
    'gm_negotiation': gmNegotiation,
    'club_prestige': clubPrestige,
    'prestige_tier': prestigeTier,
    'active_win_bonus_clause_gtex': activeWinBonusClauseGtex,
    'offers': offers.map((o) => o.toJson()).toList(),
    'active_deals': activeDeals,
  };
}

class GtexClubShareholder {
  const GtexClubShareholder({
    required this.userId,
    required this.username,
    required this.units,
    required this.sharePct,
    required this.tier,
    required this.estimatedDividendGtex,
  });

  factory GtexClubShareholder.fromJson(Object? raw) {
    if (raw is! Map) {
      return const GtexClubShareholder(
        userId: '',
        username: '',
        units: 0,
        sharePct: 0.0,
        tier: '',
        estimatedDividendGtex: 0.0,
      );
    }
    final Map<Object?, Object?> m = raw;
    String text(Object? v) => '${v ?? ''}'.trim();
    int intVal(Object? v) => v is num ? v.toInt() : int.tryParse(text(v)) ?? 0;
    double dblVal(Object? v) => v is num ? v.toDouble() : double.tryParse(text(v)) ?? 0.0;

    return GtexClubShareholder(
      userId: text(m['user_id']),
      username: text(m['username']),
      units: intVal(m['units']),
      sharePct: dblVal(m['share_pct']),
      tier: text(m['tier']),
      estimatedDividendGtex: dblVal(m['estimated_dividend_gtex']),
    );
  }

  final String userId;
  final String username;
  final int units;
  final double sharePct;
  final String tier;
  final double estimatedDividendGtex;

  Map<String, dynamic> toJson() => <String, dynamic>{
    'user_id': userId,
    'username': username,
    'units': units,
    'share_pct': sharePct,
    'tier': tier,
    'estimated_dividend_gtex': estimatedDividendGtex,
  };
}

class GtexClubShareholdersPayload {
  const GtexClubShareholdersPayload({
    required this.clubId,
    required this.clubName,
    required this.prestige,
    required this.prestigeTier,
    required this.valuationGtex,
    required this.totalMinorityUnits,
    required this.shareholderCount,
    required this.accruedDividendPoolGtex,
    required this.minorityTakeoverThresholdUnits,
    required this.myUnits,
    required this.shareholders,
  });

  factory GtexClubShareholdersPayload.fromJson(Object? raw) {
    if (raw is! Map) {
      return const GtexClubShareholdersPayload(
        clubId: '',
        clubName: '',
        prestige: 0,
        prestigeTier: '',
        valuationGtex: 0.0,
        totalMinorityUnits: 0,
        shareholderCount: 0,
        accruedDividendPoolGtex: 0.0,
        minorityTakeoverThresholdUnits: 0,
        myUnits: 0,
        shareholders: <GtexClubShareholder>[],
      );
    }
    final Map<Object?, Object?> m = raw;
    String text(Object? v) => '${v ?? ''}'.trim();
    int intVal(Object? v) => v is num ? v.toInt() : int.tryParse(text(v)) ?? 0;
    double dblVal(Object? v) => v is num ? v.toDouble() : double.tryParse(text(v)) ?? 0.0;

    final List<GtexClubShareholder> holders = <GtexClubShareholder>[];
    final Object? rawHolders = m['shareholders'];
    if (rawHolders is List) {
      for (final Object? item in rawHolders) {
        if (item is Map) {
          holders.add(GtexClubShareholder.fromJson(item));
        }
      }
    }

    return GtexClubShareholdersPayload(
      clubId: text(m['club_id']),
      clubName: text(m['club_name']),
      prestige: intVal(m['prestige']),
      prestigeTier: text(m['prestige_tier']),
      valuationGtex: dblVal(m['valuation_gtex']),
      totalMinorityUnits: intVal(m['total_minority_units']),
      shareholderCount: intVal(m['shareholder_count']),
      accruedDividendPoolGtex: dblVal(m['accrued_dividend_pool_gtex']),
      minorityTakeoverThresholdUnits: intVal(m['minority_takeover_threshold_units']),
      myUnits: intVal(m['my_units']),
      shareholders: holders,
    );
  }

  final String clubId;
  final String clubName;
  final int prestige;
  final String prestigeTier;
  final double valuationGtex;
  final int totalMinorityUnits;
  final int shareholderCount;
  final double accruedDividendPoolGtex;
  final int minorityTakeoverThresholdUnits;
  final int myUnits;
  final List<GtexClubShareholder> shareholders;

  bool get canTriggerTakeover =>
      minorityTakeoverThresholdUnits > 0 && myUnits >= minorityTakeoverThresholdUnits;

  Map<String, dynamic> toJson() => <String, dynamic>{
    'club_id': clubId,
    'club_name': clubName,
    'prestige': prestige,
    'prestige_tier': prestigeTier,
    'valuation_gtex': valuationGtex,
    'total_minority_units': totalMinorityUnits,
    'shareholder_count': shareholderCount,
    'accrued_dividend_pool_gtex': accruedDividendPoolGtex,
    'minority_takeover_threshold_units': minorityTakeoverThresholdUnits,
    'my_units': myUnits,
    'shareholders': shareholders.map((s) => s.toJson()).toList(),
  };
}

sealed class BriefingViewState {
  const BriefingViewState();
}

class BriefingLoading extends BriefingViewState {
  const BriefingLoading();
}

class BriefingUnavailable extends BriefingViewState {
  const BriefingUnavailable();
}

class BriefingError extends BriefingViewState {
  const BriefingError();
}

class BriefingEmpty extends BriefingViewState {
  const BriefingEmpty({this.worldDate});
  final String? worldDate;
}

class BriefingReady extends BriefingViewState {
  const BriefingReady(this.briefing, {this.stale = false});
  final OwnerBriefing briefing;
  final bool stale;
}
