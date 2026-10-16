class Club {
  const Club({
    required this.id,
    required this.name,
    required this.country,
    required this.league,
    required this.stadium,
    required this.budgetInMillions,
    required this.startingXiRating,
    required this.academyLevel,
    required this.formLabel,
    required this.fans,
    required this.badgeAsset,
  });

  final String id;
  final String name;
  final String country;
  final String league;
  final String stadium;
  final double budgetInMillions;
  final int startingXiRating;
  final int academyLevel;
  final String formLabel;
  final int fans;
  final String badgeAsset;
}
