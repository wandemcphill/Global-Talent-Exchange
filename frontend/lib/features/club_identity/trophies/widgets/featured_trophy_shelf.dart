import 'package:flutter/material.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/trophy_item_dto.dart';
import 'package:gte_frontend/features/club_identity/trophies/widgets/trophy_tile.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class FeaturedTrophyShelf extends StatelessWidget {
  const FeaturedTrophyShelf({
    super.key,
    required this.trophies,
  });

  final List<TrophyItemDto> trophies;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      emphasized: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Featured shelf',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 8),
          Text(
            'The rarest silverware takes the front row in the cabinet.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 18),
          SizedBox(
            height: 278,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: trophies.length,
              separatorBuilder: (_, __) => const SizedBox(width: 14),
              itemBuilder: (BuildContext context, int index) {
                return TrophyTile(
                  trophy: trophies[index],
                  compact: true,
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
