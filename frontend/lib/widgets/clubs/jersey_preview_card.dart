import 'package:flutter/material.dart';
import 'package:gte_frontend/features/club_identity/jerseys/data/jersey_variant_dto.dart';
import 'package:gte_frontend/features/club_identity/jerseys/widgets/identity_color_utils.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class JerseyPreviewCard extends StatelessWidget {
  const JerseyPreviewCard({
    super.key,
    required this.variant,
    this.selected = false,
    this.onTap,
  });

  final JerseyVariantDto variant;
  final bool selected;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final Color primary = identityColorFromHex(variant.primaryColor);
    final Color secondary = identityColorFromHex(variant.secondaryColor);
    final Color accent = identityColorFromHex(variant.accentColor);
    return GteSurfacePanel(
      onTap: onTap,
      emphasized: selected,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Align(
            alignment: Alignment.center,
            child: Stack(
              alignment: Alignment.center,
              children: <Widget>[
                Container(
                  width: 110,
                  height: 132,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(22),
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: <Color>[primary, secondary],
                    ),
                    border: Border.all(
                      color: selected ? GteShellTheme.accent : accent,
                      width: 2,
                    ),
                  ),
                ),
                Positioned(
                  top: 14,
                  child: Container(
                    width: 64,
                    height: 12,
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(999),
                      color: accent,
                    ),
                  ),
                ),
                Positioned(
                  top: 54,
                  child: Text(
                    variant.frontText,
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          color: identityReadableOn(primary),
                        ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Text(
            variant.label,
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 6),
          Text(
            '${variant.patternType.name} • ${variant.collarStyle.name} • ${variant.sleeveStyle.name}',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        ],
      ),
    );
  }
}
