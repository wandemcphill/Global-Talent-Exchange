class ScoutingDashboard {
  const ScoutingDashboard({
    required this.clubId,
    required this.clubName,
    required this.openAssignments,
    required this.activeRegions,
    required this.liveProspects,
    required this.trialsScheduled,
    required this.assignments,
    required this.prospects,
    required this.reports,
    required this.notes,
  });

  final String clubId;
  final String clubName;
  final int openAssignments;
  final int activeRegions;
  final int liveProspects;
  final int trialsScheduled;
  final List<ScoutAssignment> assignments;
  final List<Prospect> prospects;
  final List<ProspectReport> reports;
  final List<String> notes;
}

class ScoutAssignment {
  const ScoutAssignment({
    required this.id,
    required this.scoutName,
    required this.region,
    required this.competition,
    required this.focusArea,
    required this.priorityLabel,
    required this.statusLabel,
    required this.dueDate,
    required this.activeProspects,
    required this.travelWindow,
    required this.objective,
  });

  final String id;
  final String scoutName;
  final String region;
  final String competition;
  final String focusArea;
  final String priorityLabel;
  final String statusLabel;
  final DateTime dueDate;
  final int activeProspects;
  final String travelWindow;
  final String objective;
}

enum ProspectStage {
  monitored,
  shortlisted,
  trial,
  scholarship,
  promoted,
}

class Prospect {
  const Prospect({
    required this.id,
    required this.name,
    required this.position,
    required this.age,
    required this.region,
    required this.currentClub,
    required this.stage,
    required this.readinessScore,
    required this.developmentProjection,
    required this.pathwayFitLabel,
    required this.nextAction,
    required this.availabilityLabel,
    required this.lastUpdated,
    required this.strengths,
    required this.focusAreas,
  });

  final String id;
  final String name;
  final String position;
  final int age;
  final String region;
  final String currentClub;
  final ProspectStage stage;
  final int readinessScore;
  final String developmentProjection;
  final String pathwayFitLabel;
  final String nextAction;
  final String availabilityLabel;
  final DateTime lastUpdated;
  final List<String> strengths;
  final List<String> focusAreas;
}

class ProspectReport {
  const ProspectReport({
    required this.id,
    required this.prospectId,
    required this.scoutName,
    required this.headline,
    required this.createdAt,
    required this.overallFit,
    required this.technicalNote,
    required this.physicalNote,
    required this.characterNote,
    required this.recommendation,
  });

  final String id;
  final String prospectId;
  final String scoutName;
  final String headline;
  final DateTime createdAt;
  final String overallFit;
  final String technicalNote;
  final String physicalNote;
  final String characterNote;
  final String recommendation;
}

class YouthPipelineSnapshot {
  const YouthPipelineSnapshot({
    required this.trackedProspects,
    required this.shortlistedProspects,
    required this.trialists,
    required this.scholarshipOffers,
    required this.promotedPlayers,
    required this.conversionPercent,
    required this.stages,
    required this.notes,
  });

  final int trackedProspects;
  final int shortlistedProspects;
  final int trialists;
  final int scholarshipOffers;
  final int promotedPlayers;
  final double conversionPercent;
  final List<YouthPipelineStage> stages;
  final List<String> notes;
}

class YouthPipelineStage {
  const YouthPipelineStage({
    required this.label,
    required this.count,
    required this.description,
  });

  final String label;
  final int count;
  final String description;
}

class ScoutingAnalyticsSnapshot {
  const ScoutingAnalyticsSnapshot({
    required this.assignmentCompletionPercent,
    required this.regionalCoveragePercent,
    required this.shortlistToTrialPercent,
    required this.trialToScholarshipPercent,
    required this.youthConversionPercent,
    required this.funnel,
    required this.assignmentLoad,
  });

  final double assignmentCompletionPercent;
  final double regionalCoveragePercent;
  final double shortlistToTrialPercent;
  final double trialToScholarshipPercent;
  final double youthConversionPercent;
  final List<YouthPipelineStage> funnel;
  final List<ScoutAssignment> assignmentLoad;
}
