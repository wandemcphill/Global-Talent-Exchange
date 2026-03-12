import 'package:flutter/material.dart';

import '../data/badge_profile_dto.dart';

class BadgeShapeSelector extends StatelessWidget {
  const BadgeShapeSelector({
    super.key,
    required this.selectedShape,
    required this.onSelected,
  });

  final BadgeShape selectedShape;
  final ValueChanged<BadgeShape> onSelected;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: BadgeShape.values.map((BadgeShape shape) {
        return ChoiceChip(
          selected: shape == selectedShape,
          label: Text(_label(shape)),
          onSelected: (_) => onSelected(shape),
        );
      }).toList(growable: false),
    );
  }

  String _label(BadgeShape shape) {
    switch (shape) {
      case BadgeShape.shield:
        return 'Shield';
      case BadgeShape.round:
        return 'Round';
      case BadgeShape.diamond:
        return 'Diamond';
      case BadgeShape.pennant:
        return 'Pennant';
    }
  }
}
