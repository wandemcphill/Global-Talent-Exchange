class Player {
  const Player({
    required this.id,
    required this.name,
    required this.position,
    required this.country,
    required this.age,
    required this.rating,
    required this.potential,
    required this.valueInMillions,
    required this.pace,
    required this.technique,
    required this.mentality,
    required this.image,
    this.isHot = false,
  });

  final String id;
  final String name;
  final String position;
  final String country;
  final int age;
  final int rating;
  final int potential;
  final double valueInMillions;
  final double pace;
  final double technique;
  final double mentality;
  final String image;
  final bool isHot;
}
