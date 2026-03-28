class LiveMatch {
  const LiveMatch({
    required this.id,
    required this.homeClub,
    required this.awayClub,
    required this.homeStarPlayer,
    required this.awayStarPlayer,
    required this.homeScore,
    required this.awayScore,
    required this.minute,
    required this.headline,
    required this.venue,
    required this.crowd,
    required this.momentum,
  });

  final String id;
  final String homeClub;
  final String awayClub;
  final String homeStarPlayer;
  final String awayStarPlayer;
  final int homeScore;
  final int awayScore;
  final int minute;
  final String headline;
  final String venue;
  final int crowd;
  final double momentum;
}
