import 'package:flutter/material.dart';
import 'package:gte_frontend/features/club_identity/jerseys/widgets/identity_color_utils.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class BrandingThemeCard extends StatelessWidget {
  const BrandingThemeCard({
    super.key,
    required this.title,
    required this.description,
    required this.previewColors,
    required this.selected,
    required this.onTap,
    this.tagLabel,
  });

  final String title;
  final String description;
  final List<String> previewColors;
  final bool selected;
  final VoidCallback onTap;
  final String? tagLabel;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      emphasized: selected,
      onTap: onTap,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Text(
                  title,
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
              if (tagLabel != null)
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(999),
                    color: GteShellTheme.panelStrong.withValues(alpha: 0.94),
                    border: Border.all(color: GteShellTheme.stroke),
                  ),
                  child: Text(
                    tagLabel!,
                    style: Theme.of(context).textTheme.labelLarge,
                  ),
                ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            description,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 14),
          Row(
            children: previewColors.take(3).map((String colorHex) {
              return Container(
                width: 28,
                height: 28,
                margin: const EdgeInsets.only(right: 8),
                decoration: BoxDecoration(
                  color: identityColorFromHex(colorHex),
                  shape: BoxShape.circle,
                ),
              );
            }).toList(growable: false),
          ),
        ],
      ),
    );
  }
}
