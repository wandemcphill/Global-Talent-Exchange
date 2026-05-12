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

  bool get isJoinable => status == GtexCompetitionStatus.registrationOpen && registeredClubs < maxClubs;

  String get entryFeeLabel => '${entryFeeCredits.toString()} coins';
  String get prizePoolLabel => '${prizePoolCredits.toString()} coins';
  String get capacityLabel => '$registeredClubs/$maxClubs clubs';
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
