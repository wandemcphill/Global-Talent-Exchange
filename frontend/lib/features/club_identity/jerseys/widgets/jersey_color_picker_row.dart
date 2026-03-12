import 'package:flutter/material.dart';

import '../../../../widgets/gte_shell_theme.dart';
import 'identity_color_utils.dart';

class JerseyColorPickerRow extends StatelessWidget {
  const JerseyColorPickerRow({
    super.key,
    required this.label,
    required this.selectedColor,
    required this.onSelected,
    required this.paletteSuggestions,
  });

  final String label;
  final String selectedColor;
  final ValueChanged<String> onSelected;
  final List<String> paletteSuggestions;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Row(
          children: <Widget>[
            Text(label, style: Theme.of(context).textTheme.titleMedium),
            const Spacer(),
            Text(
              selectedColor.toUpperCase(),
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ),
        const SizedBox(height: 10),
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: paletteSuggestions.map((String colorHex) {
            final Color color = identityColorFromHex(colorHex);
            final bool selected =
                colorHex.toUpperCase() == selectedColor.toUpperCase();
            return GestureDetector(
              onTap: () => onSelected(colorHex),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 180),
                width: selected ? 44 : 38,
                height: selected ? 44 : 38,
                decoration: BoxDecoration(
                  color: color,
                  shape: BoxShape.circle,
                  border: Border.all(
                    color:
                        selected ? GteShellTheme.accent : GteShellTheme.stroke,
                    width: selected ? 3 : 1.4,
                  ),
                  boxShadow: <BoxShadow>[
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.25),
                      blurRadius: 14,
                      offset: const Offset(0, 8),
                    ),
                  ],
                ),
                child: selected
                    ? Icon(
                        Icons.check,
                        color: identityReadableOn(color),
                        size: 18,
                      )
                    : null,
              ),
            );
          }).toList(growable: false),
        ),
      ],
    );
  }
}
