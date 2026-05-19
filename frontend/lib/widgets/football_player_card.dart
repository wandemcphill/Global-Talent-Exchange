import 'package:flutter/material.dart';

import '../core/widgets/player_card.dart';
import '../models/player_avatar.dart';

class FootballPlayerCard extends StatelessWidget {
  const FootballPlayerCard({
    super.key,
    required this.playerName,
    required this.tierLabel,
    required this.avatar,
    this.imageUrl,
    this.position,
    this.clubName,
    this.nationalityCode,
    this.rating,
    this.ratingLabel = 'Overall rating',
    this.valueLabel,
    this.wageLabel,
    this.ageLabel,
    this.potentialLabel,
    this.scoutingBandLabel,
    this.attributes = const <String>[],
    this.actions = const <Widget>[],
  });

  final String playerName;
  final String tierLabel;
  final PlayerAvatar? avatar;
  final String? imageUrl;
  final String? position;
  final String? clubName;
  final String? nationalityCode;
  final int? rating;
  final String ratingLabel;
  final String? valueLabel;
  final String? wageLabel;
  final String? ageLabel;
  final String? potentialLabel;
  final String? scoutingBandLabel;
  final List<String> attributes;
  final List<Widget> actions;

  @override
  Widget build(BuildContext context) {
    return PlayerCard(
      name: playerName,
      rating: rating ?? 0,
      ratingLabel: ratingLabel,
      showRating: rating != null,
      image: imageUrl ?? '',
      playerAvatar: avatar,
      position: position,
      subtitle: <String>[
        tierLabel,
        if (clubName != null && clubName!.trim().isNotEmpty) clubName!.trim(),
      ].join(' | '),
      avatarSize: 88,
      layout: PlayerCardLayout.horizontal,
      badgeLabels: <String>[
        if (position != null && position!.trim().isNotEmpty) position!.trim(),
        if (nationalityCode != null && nationalityCode!.trim().isNotEmpty)
          nationalityCode!.trim().toUpperCase(),
      ],
      metrics: <PlayerCardMetric>[
        if (valueLabel != null)
          PlayerCardMetric(label: 'Value', value: valueLabel!),
        if (wageLabel != null)
          PlayerCardMetric(label: 'Wage', value: wageLabel!),
        if (ageLabel != null) PlayerCardMetric(label: 'Age', value: ageLabel!),
        if (scoutingBandLabel != null)
          PlayerCardMetric(label: 'GSI', value: scoutingBandLabel!),
        if (potentialLabel != null)
          PlayerCardMetric(label: 'Potential', value: potentialLabel!),
        for (final String attribute in attributes.take(4))
          PlayerCardMetric(label: 'Form', value: attribute),
      ],
      actions: actions,
    );
  }
}
