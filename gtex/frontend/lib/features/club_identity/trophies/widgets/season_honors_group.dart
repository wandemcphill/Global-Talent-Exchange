import 'package:flutter/material.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/season_honors_dto.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/trophy_item_dto.dart';
import 'package:gte_frontend/features/club_identity/trophies/widgets/major_honor_badge.dart';
import 'package:gte_frontend/features/club_identity/trophies/widgets/trophy_tile.dart';

class SeasonHonorsGroup extends StatelessWidget {
  const SeasonHonorsGroup({
    super.key,
    required this.record,
  });

  final SeasonHonorsRecordDto record;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: <Widget>[
            Text(
              record.teamScope.label,
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(width: 10),
            if (record.teamScope.label == 'Academy')
              const MajorHonorBadge(
                label: 'Academy',
                style: MajorHonorBadgeStyle.academy,
              ),
          ],
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: record.honors.map((honor) {
            return SizedBox(
              width: 260,
              child: TrophyTile(trophy: honor),
            );
          }).toList(growable: false),
        ),
      ],
    );
  }
}
