import 'player_avatar.dart';

class AcademyDashboard {
  const AcademyDashboard({
    required this.clubId,
    required this.clubName,
    required this.pathwaySummary,
    required this.programs,
    required this.players,
    required this.trainingCycles,
    required this.promotions,
    required this.notes,
  });

  final String clubId;
  final String clubName;
  final AcademyPathwaySummary pathwaySummary;
  final List<AcademyProgram> programs;
  final List<AcademyPlayer> players;
  final List<TrainingCycle> trainingCycles;
  final List<AcademyPromotion> promotions;
  final List<String> notes;
}

class AcademyPathwaySummary {
  const AcademyPathwaySummary({
    required this.developmentBudget,
    required this.squadSize,
    required this.promotionsThisSeason,
    required this.graduationRatePercent,
    required this.staffCoverageLabel,
    required this.facilityLabel,
  });

  final double developmentBudget;
  final int squadSize;
  final int promotionsThisSeason;
  final double graduationRatePercent;
  final String staffCoverageLabel;
  final String facilityLabel;
}

class AcademyProgram {
  const AcademyProgram({
    required this.id,
    required this.name,
    required this.ageBand,
    required this.focusArea,
    required this.staffLead,
    required this.weeklyHours,
    required this.enrolledPlayers,
    required this.statusLabel,
    required this.outcomeLabel,
    required this.description,
  });

  final String id;
  final String name;
  final String ageBand;
  final String focusArea;
  final String staffLead;
  final int weeklyHours;
  final int enrolledPlayers;
  final String statusLabel;
  final String outcomeLabel;
  final String description;
}

class AcademyPlayer {
  const AcademyPlayer({
    required this.id,
    required this.name,
    required this.position,
    required this.age,
    required this.pathwayStage,
    required this.potentialBand,
    required this.developmentProgressPercent,
    required this.readinessScore,
    required this.minutesTarget,
    required this.statusLabel,
    required this.nextMilestone,
    required this.strengths,
    required this.focusAreas,
    this.playerId,
    this.secondaryPositions = const <String>[],
    this.nationality,
    this.nationalityCode,
    this.dominantFoot,
    this.roleArchetype,
    this.formationSlots = const <String>[],
    this.squadEligible,
    this.avatarSeedToken,
    this.avatarDnaSeed,
    this.avatar,
    this.currentValueCredits,
    this.promotedToSenior = false,
  });

  final String id;
  final String name;
  final String position;
  final int age;
  final String pathwayStage;
  final String potentialBand;
  final double developmentProgressPercent;
  final int readinessScore;
  final int minutesTarget;
  final String statusLabel;
  final String nextMilestone;
  final List<String> strengths;
  final List<String> focusAreas;
  final String? playerId;
  final List<String> secondaryPositions;
  final String? nationality;
  final String? nationalityCode;
  final String? dominantFoot;
  final String? roleArchetype;
  final List<String> formationSlots;
  final bool? squadEligible;
  final String? avatarSeedToken;
  final String? avatarDnaSeed;
  final PlayerAvatar? avatar;
  final double? currentValueCredits;
  final bool promotedToSenior;

  String get canonicalPlayerId {
    final String? candidate = playerId?.trim();
    return candidate == null || candidate.isEmpty ? id : candidate;
  }
}

class TrainingCycle {
  const TrainingCycle({
    required this.id,
    required this.title,
    required this.phaseLabel,
    required this.focus,
    required this.cohortLabel,
    required this.startDate,
    required this.endDate,
    required this.attendancePercent,
    required this.intensityLabel,
    required this.expectedPromotionCount,
    required this.objective,
  });

  final String id;
  final String title;
  final String phaseLabel;
  final String focus;
  final String cohortLabel;
  final DateTime startDate;
  final DateTime endDate;
  final double attendancePercent;
  final String intensityLabel;
  final int expectedPromotionCount;
  final String objective;
}

class AcademyPromotion {
  const AcademyPromotion({
    required this.playerName,
    required this.destination,
    required this.occurredAt,
    required this.note,
  });

  final String playerName;
  final String destination;
  final DateTime occurredAt;
  final String note;
}

class AcademyAnalyticsSnapshot {
  const AcademyAnalyticsSnapshot({
    required this.conversionRatePercent,
    required this.retentionRatePercent,
    required this.averageReadinessScore,
    required this.promotionsThisSeason,
    required this.pathwayHealthLabel,
    required this.programMix,
  });

  final double conversionRatePercent;
  final double retentionRatePercent;
  final int averageReadinessScore;
  final int promotionsThisSeason;
  final String pathwayHealthLabel;
  final List<AcademyProgram> programMix;
}
