enum GtexCompetitionKind {
  gtexTournament,
  nationalTeam,
  userHosted,
  creatorHosted,
  academy,
}

enum GtexCompetitionStatus {
  draft,
  registrationOpen,
  registrationClosed,
  live,
  completed,
}

extension GtexCompetitionKindLabel on GtexCompetitionKind {
  String get label {
    switch (this) {
      case GtexCompetitionKind.gtexTournament:
        return 'GTEX Tournament';
      case GtexCompetitionKind.nationalTeam:
        return 'National Team';
      case GtexCompetitionKind.userHosted:
        return 'User Hosted';
      case GtexCompetitionKind.creatorHosted:
        return 'Creator Hosted';
      case GtexCompetitionKind.academy:
        return 'Academy';
    }
  }
}

extension GtexCompetitionStatusLabel on GtexCompetitionStatus {
  String get label {
    switch (this) {
      case GtexCompetitionStatus.draft:
        return 'Draft';
      case GtexCompetitionStatus.registrationOpen:
        return 'Registration open';
      case GtexCompetitionStatus.registrationClosed:
        return 'Registration closed';
      case GtexCompetitionStatus.live:
        return 'Live';
      case GtexCompetitionStatus.completed:
        return 'Completed';
    }
  }
}

/// Coarse lifecycle position used to render the competition progress rail.
///
/// Derived from [GtexCompetitionStatus] plus settlement state rather than
/// stored separately, so the rail can never disagree with the badge.
enum GtexCompetitionLifecycleStage {
  upcoming,
  registration,
  live,
  completed,
  settlement,
}

extension GtexCompetitionLifecycleStageLabel on GtexCompetitionLifecycleStage {
  String get label {
    switch (this) {
      case GtexCompetitionLifecycleStage.upcoming:
        return 'Upcoming';
      case GtexCompetitionLifecycleStage.registration:
        return 'Registration';
      case GtexCompetitionLifecycleStage.live:
        return 'Live';
      case GtexCompetitionLifecycleStage.completed:
        return 'Completed';
      case GtexCompetitionLifecycleStage.settlement:
        return 'Settled';
    }
  }

  /// Ordering used by the rail to decide which steps are already behind us.
  int get rank => index;
}

/// Where the signed-in club stands inside a competition.
///
/// [unknown] is the honest default: the list payload does not always carry
/// participation, and guessing would be worse than staying quiet.
enum GtexCompetitionViewerOutcome {
  unknown,
  notEntered,
  registered,
  active,
  eliminated,
  winner,
}

extension GtexCompetitionViewerOutcomeLabel on GtexCompetitionViewerOutcome {
  String? get label {
    switch (this) {
      case GtexCompetitionViewerOutcome.unknown:
        return null;
      case GtexCompetitionViewerOutcome.notEntered:
        return 'Not entered';
      case GtexCompetitionViewerOutcome.registered:
        return 'Registered';
      case GtexCompetitionViewerOutcome.active:
        return 'Still in';
      case GtexCompetitionViewerOutcome.eliminated:
        return 'Eliminated';
      case GtexCompetitionViewerOutcome.winner:
        return 'Winner';
    }
  }
}

class GtexCompetitionSummary {
  const GtexCompetitionSummary({
    required this.id,
    required this.title,
    required this.kind,
    required this.status,
    required this.regionLabel,
    required this.entryFeeCredits,
    required this.prizePoolCredits,
    required this.registeredClubs,
    required this.maxClubs,
    required this.progressPercent,
    required this.currentStage,
    required this.startsAtLabel,
    required this.description,
    this.ownerClubName,
    this.creatorName,
    this.heroImageUrl,
    this.viewerOutcome = GtexCompetitionViewerOutcome.unknown,
    this.winnerClubName,
    this.prizeSettled = false,
  });

  final String id;
  final String title;
  final GtexCompetitionKind kind;
  final GtexCompetitionStatus status;
  final String regionLabel;
  final int entryFeeCredits;
  final int prizePoolCredits;
  final int registeredClubs;
  final int maxClubs;
  final double progressPercent;
  final String currentStage;
  final String startsAtLabel;
  final String description;
  final String? ownerClubName;
  final String? creatorName;
  final String? heroImageUrl;

  /// Where the signed-in club stands. Defaults to
  /// [GtexCompetitionViewerOutcome.unknown] when the payload omits it.
  final GtexCompetitionViewerOutcome viewerOutcome;

  /// Winning club, only meaningful once the competition is completed.
  final String? winnerClubName;

  /// Whether prize coins have been released to the winners.
  final bool prizeSettled;

  bool get isJoinable => status == GtexCompetitionStatus.registrationOpen && registeredClubs < maxClubs;

  String get entryFeeLabel => '${entryFeeCredits.toString()} coins';
  String get prizePoolLabel => '${prizePoolCredits.toString()} coins';
  String get capacityLabel => '$registeredClubs/$maxClubs clubs';

  /// Lifecycle position used by the progress rail.
  ///
  /// Settlement is only reported once the competition is finished *and* the
  /// prizes have actually been released, so a completed-but-unsettled
  /// tournament still reads as pending payout rather than done.
  GtexCompetitionLifecycleStage get lifecycleStage {
    switch (status) {
      case GtexCompetitionStatus.draft:
        return GtexCompetitionLifecycleStage.upcoming;
      case GtexCompetitionStatus.registrationOpen:
        return GtexCompetitionLifecycleStage.registration;
      case GtexCompetitionStatus.registrationClosed:
        return GtexCompetitionLifecycleStage.registration;
      case GtexCompetitionStatus.live:
        return GtexCompetitionLifecycleStage.live;
      case GtexCompetitionStatus.completed:
        return prizeSettled
            ? GtexCompetitionLifecycleStage.settlement
            : GtexCompetitionLifecycleStage.completed;
    }
  }

  /// Whether the competition is finished but prize coins are still pending.
  bool get isAwaitingSettlement =>
      status == GtexCompetitionStatus.completed && !prizeSettled;

  /// Short outcome badge for the signed-in club, or null when unknown.
  String? get viewerOutcomeLabel => viewerOutcome.label;
}

class GtexCompetitionFixture {
  const GtexCompetitionFixture({
    required this.id,
    required this.homeClub,
    required this.awayClub,
    required this.stage,
    required this.timeLabel,
    this.homeScore,
    this.awayScore,
    this.isLive = false,
  });

  final String id;
  final String homeClub;
  final String awayClub;
  final String stage;
  final String timeLabel;
  final int? homeScore;
  final int? awayScore;
  final bool isLive;

  String get scoreLabel {
    if (homeScore == null || awayScore == null) {
      return 'vs';
    }
    return '$homeScore - $awayScore';
  }
}

class GtexCompetitionStanding {
  const GtexCompetitionStanding({
    required this.rank,
    required this.clubName,
    required this.played,
    required this.wins,
    required this.draws,
    required this.losses,
    required this.goalDifference,
    required this.points,
  });

  final int rank;
  final String clubName;
  final int played;
  final int wins;
  final int draws;
  final int losses;
  final int goalDifference;
  final int points;
}

class GtexTournamentStageProgress {
  const GtexTournamentStageProgress({
    required this.title,
    required this.statusLabel,
    required this.progressPercent,
    required this.summary,
  });

  final String title;
  final String statusLabel;
  final double progressPercent;
  final String summary;
}

class GtexCompetitionRule {
  const GtexCompetitionRule({
    required this.title,
    required this.description,
  });

  final String title;
  final String description;
}

class GtexCompetitionDetail {
  const GtexCompetitionDetail({
    required this.summary,
    required this.fixtures,
    required this.standings,
    required this.stages,
    required this.rules,
    required this.newsSignals,
  });

  final GtexCompetitionSummary summary;
  final List<GtexCompetitionFixture> fixtures;
  final List<GtexCompetitionStanding> standings;
  final List<GtexTournamentStageProgress> stages;
  final List<GtexCompetitionRule> rules;
  final List<String> newsSignals;
}

class GtexCompetitionDraft {
  const GtexCompetitionDraft({
    required this.title,
    required this.kind,
    required this.entryFeeCredits,
    required this.maxClubs,
    required this.rulePreset,
    required this.visibility,
  });

  final String title;
  final GtexCompetitionKind kind;
  final int entryFeeCredits;
  final int maxClubs;
  final String rulePreset;
  final String visibility;
}
