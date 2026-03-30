import 'package:flutter/material.dart';

import '../broadcast_package_models.dart';

class ReactionPanelWidget extends StatelessWidget {
  const ReactionPanelWidget({
    super.key,
    required this.reactions,
    this.storylines = const <String>[],
  });

  final List<MatchReactionCard> reactions;
  final List<String> storylines;

  @override
  Widget build(BuildContext context) {
    final List<Widget> cards =
        reactions.isNotEmpty
            ? reactions
                .take(5)
                .map((MatchReactionCard item) => _ReactionCard(item: item))
                .toList(growable: false)
            : storylines
                .take(4)
                .map(
                  (String storyline) => _ReactionCard(
                    item: MatchReactionCard(
                      source: 'Storyline',
                      headline: 'Matchday note',
                      detail: storyline,
                      tag: 'context',
                    ),
                  ),
                )
                .toList(growable: false);
    return DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(28),
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[Color(0xFF14161D), Color(0xFF0B1016)],
        ),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'Matchday Desk',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w900,
                  ),
            ),
            const SizedBox(height: 6),
            Text(
              'Staff reaction, press notes, and side-panel storylines.',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.white70,
                  ),
            ),
            const SizedBox(height: 16),
            if (cards.isEmpty)
              Text(
                'No reaction or newsroom items are attached to this live payload yet.',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Colors.white70,
                    ),
              )
            else
              ...cards.expand(
                (Widget item) => <Widget>[item, const SizedBox(height: 10)],
              ),
          ],
        ),
      ),
    );
  }
}

class _ReactionCard extends StatelessWidget {
  const _ReactionCard({required this.item});

  final MatchReactionCard item;

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: Colors.white.withValues(alpha: 0.07)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Wrap(
              spacing: 8,
              runSpacing: 8,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: <Widget>[
                Text(
                  item.source.toUpperCase(),
                  style: Theme.of(context).textTheme.labelMedium?.copyWith(
                        color: const Color(0xFFFDA29B),
                        fontWeight: FontWeight.w800,
                        letterSpacing: 0.8,
                      ),
                ),
                if (item.tag != null)
                  Text(
                    item.tag!.toUpperCase(),
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: Colors.white54,
                          fontWeight: FontWeight.w700,
                        ),
                  ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              item.headline,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w800,
                  ),
            ),
            const SizedBox(height: 6),
            Text(
              item.detail,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Colors.white70,
                    height: 1.35,
                  ),
            ),
          ],
        ),
      ),
    );
  }
}
