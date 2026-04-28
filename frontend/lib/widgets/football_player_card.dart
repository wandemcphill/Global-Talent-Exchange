import 'package:flutter/material.dart';

import '../models/player_avatar.dart';
import 'player_card_avatar.dart';

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
    this.valueLabel,
    this.wageLabel,
    this.ageLabel,
    this.potentialLabel,
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
  final String? valueLabel;
  final String? wageLabel;
  final String? ageLabel;
  final String? potentialLabel;
  final List<String> attributes;
  final List<Widget> actions;

  @override
  Widget build(BuildContext context) {
    final ColorScheme colorScheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        color: colorScheme.surfaceContainerHigh,
        border: Border.all(color: colorScheme.outlineVariant),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              SizedBox(
                width: 96,
                child: Column(
                  children: <Widget>[
                    PlayerCardAvatar(
                      avatar: avatar,
                      imageUrl: imageUrl,
                      size: 88,
                    ),
                    const SizedBox(height: 8),
                    Wrap(
                      alignment: WrapAlignment.center,
                      spacing: 6,
                      runSpacing: 6,
                      children: <Widget>[
                        _CardBadge(label: position ?? 'POS'),
                        if (nationalityCode != null)
                          _CardBadge(label: nationalityCode!.toUpperCase()),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        if (rating != null) ...<Widget>[
                          _RatingBox(rating: rating!),
                          const SizedBox(width: 10),
                        ],
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Text(
                                playerName,
                                style: Theme.of(context).textTheme.titleLarge,
                              ),
                              const SizedBox(height: 4),
                              Text(
                                <String>[
                                  tierLabel,
                                  if (clubName != null) clubName!,
                                ].join(' | '),
                                style: Theme.of(context).textTheme.bodyMedium,
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: <Widget>[
                        if (valueLabel != null)
                          _AttributePill(label: 'Value', value: valueLabel!),
                        if (wageLabel != null)
                          _AttributePill(label: 'Wage', value: wageLabel!),
                        if (ageLabel != null)
                          _AttributePill(label: 'Age', value: ageLabel!),
                        if (potentialLabel != null)
                          _AttributePill(
                            label: 'Potential',
                            value: potentialLabel!,
                          ),
                        for (final String attribute in attributes.take(4))
                          _AttributePill(label: 'Form', value: attribute),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
          if (actions.isNotEmpty) ...<Widget>[
            const SizedBox(height: 14),
            Wrap(spacing: 10, runSpacing: 10, children: actions),
          ],
        ],
      ),
    );
  }
}

class _RatingBox extends StatelessWidget {
  const _RatingBox({required this.rating});

  final int rating;

  @override
  Widget build(BuildContext context) {
    final ColorScheme colorScheme = Theme.of(context).colorScheme;
    return Container(
      width: 54,
      padding: const EdgeInsets.symmetric(vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        color: colorScheme.primary,
      ),
      child: Column(
        children: <Widget>[
          Text(
            rating.toString(),
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
              color: colorScheme.onPrimary,
              fontWeight: FontWeight.w800,
            ),
          ),
          Text(
            'OVR',
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: colorScheme.onPrimary.withValues(alpha: 0.78),
            ),
          ),
        ],
      ),
    );
  }
}

class _CardBadge extends StatelessWidget {
  const _CardBadge({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(6),
        color: Theme.of(context).colorScheme.secondaryContainer,
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
          color: Theme.of(context).colorScheme.onSecondaryContainer,
          fontWeight: FontWeight.w700,
        ),
      ),
    );
  }
}

class _AttributePill extends StatelessWidget {
  const _AttributePill({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(6),
        color: Theme.of(context).colorScheme.surfaceContainerHighest,
      ),
      child: RichText(
        text: TextSpan(
          style: Theme.of(context).textTheme.labelMedium,
          children: <TextSpan>[
            TextSpan(text: '$label '),
            TextSpan(
              text: value,
              style: const TextStyle(fontWeight: FontWeight.w800),
            ),
          ],
        ),
      ),
    );
  }
}
