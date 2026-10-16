import 'package:flutter/material.dart';

import '../data/jersey_variant_dto.dart';

class PatternSelector extends StatelessWidget {
  const PatternSelector({
    super.key,
    required this.selected,
    required this.onSelected,
  });

  final PatternType selected;
  final ValueChanged<PatternType> onSelected;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: PatternType.values.map((PatternType type) {
        final bool isSelected = type == selected;
        return ChoiceChip(
          selected: isSelected,
          label: Text(_label(type)),
          onSelected: (_) => onSelected(type),
        );
      }).toList(growable: false),
    );
  }

  String _label(PatternType type) {
    switch (type) {
      case PatternType.solid:
        return 'Solid';
      case PatternType.stripes:
        return 'Stripes';
      case PatternType.hoops:
        return 'Hoops';
      case PatternType.sash:
        return 'Sash';
      case PatternType.chevron:
        return 'Chevron';
      case PatternType.gradient:
        return 'Gradient';
    }
  }
}
