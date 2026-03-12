import 'trophy_item_dto.dart';

class HonorsTimelineDto {
  const HonorsTimelineDto({
    required this.clubId,
    required this.clubName,
    required this.honors,
  });

  final String clubId;
  final String clubName;
  final List<TrophyItemDto> honors;

  bool get isEmpty => honors.isEmpty;

  factory HonorsTimelineDto.fromJson(Map<String, dynamic> json) {
    return HonorsTimelineDto(
      clubId: json['club_id'] as String,
      clubName: json['club_name'] as String,
      honors: (json['honors'] as List<dynamic>)
          .map((dynamic item) =>
              TrophyItemDto.fromJson(item as Map<String, dynamic>))
          .toList(growable: false),
    );
  }
}
