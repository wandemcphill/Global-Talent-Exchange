import 'package:flutter/material.dart';
import 'package:gte_frontend/features/club_identity/jerseys/widgets/identity_color_utils.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';

class JerseyColorPicker extends StatelessWidget {
  const JerseyColorPicker({
    super.key,
    required this.label,
    required this.selectedColor,
    required this.colors,
    required this.onSelected,
  });

  final String label;
  final String selectedColor;
  final List<String> colors;
  final ValueChanged<String> onSelected;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(label, style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 10),
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: colors.map((String colorHex) {
            final bool active = colorHex == selectedColor;
            return GestureDetector(
              onTap: () => onSelected(colorHex),
              child: Container(
                width: 34,
                height: 34,
                decoration: BoxDecoration(
                  color: identityColorFromHex(colorHex),
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: active ? GteShellTheme.accentWarm : GteShellTheme.stroke,
                    width: active ? 3 : 1,
                  ),
                ),
              ),
            );
          }).toList(growable: false),
        ),
      ],
    );
  }
}
