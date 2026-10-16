import 'package:flutter/material.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/trophy_item_dto.dart';
import 'package:gte_frontend/features/club_identity/trophies/widgets/trophy_tile.dart';

class TrophyGrid extends StatelessWidget {
  const TrophyGrid({
    super.key,
    required this.trophies,
    this.onSelected,
  });

  final List<TrophyItemDto> trophies;
  final ValueChanged<TrophyItemDto>? onSelected;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final bool stacked = constraints.maxWidth < 760;
        return Wrap(
          spacing: 14,
          runSpacing: 14,
          children: trophies.map((TrophyItemDto trophy) {
            return SizedBox(
              width: stacked ? constraints.maxWidth : 280,
              child: GestureDetector(
                onTap: onSelected == null ? null : () => onSelected!(trophy),
                child: TrophyTile(
                  trophy: trophy,
                  compact: !stacked,
                ),
              ),
            );
          }).toList(growable: false),
        );
      },
    );
  }
}
