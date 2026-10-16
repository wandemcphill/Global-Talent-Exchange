import 'package:gte_frontend/features/club_identity/reputation/data/reputation_models.dart';

class ReputationContribution {
  const ReputationContribution({
    required this.title,
    required this.detail,
    required this.delta,
    required this.categoryLabel,
  });

  final String title;
  final String detail;
  final int delta;
  final String categoryLabel;
}

class ClubReputationSummary {
  const ClubReputationSummary({
    required this.profile,
    required this.history,
    required this.contributors,
    this.globalRank,
    this.regionalRank,
  });

  final ReputationProfileDto profile;
  final ReputationHistoryDto history;
  final List<ReputationContribution> contributors;
  final PrestigeLeaderboardEntryDto? globalRank;
  final PrestigeLeaderboardEntryDto? regionalRank;

  List<ReputationEventDto> get recentEvents =>
      history.events.take(5).toList(growable: false);
}
