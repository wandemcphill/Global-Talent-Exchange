import 'package:flutter/material.dart';

import '../broadcast_package_models.dart';

class PlayerRatingsStripWidget extends StatelessWidget {
  const PlayerRatingsStripWidget({super.key, required this.players});

  final List<MatchPresentationPlayer> players;

  @override
  Widget build(BuildContext context) {
    if (players.isEmpty) {
      return const SizedBox.shrink();
    }
    return DecoratedBox(
      key: const Key('player-ratings-strip'),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: const Color(0xDC091119),
        border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(10),
        child: Wrap(
          spacing: 8,
          runSpacing: 8,
          children: players
              .map(
                (MatchPresentationPlayer player) => Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 8,
                  ),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(12),
                    color: Colors.white.withValues(alpha: 0.05),
                  ),
                  child: Text(
                    '${player.playerName} ${player.rating?.toStringAsFixed(1) ?? '--'}',
                    style: Theme.of(context).textTheme.labelMedium?.copyWith(
                      color: Colors.white,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              )
              .toList(growable: false),
        ),
      ),
    );
  }
}
