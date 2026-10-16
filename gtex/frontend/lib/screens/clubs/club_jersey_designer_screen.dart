import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_controller.dart';
import 'package:gte_frontend/features/club_identity/jerseys/data/club_identity_defaults.dart';
import 'package:gte_frontend/features/club_identity/jerseys/data/jersey_variant_dto.dart';
import 'package:gte_frontend/widgets/clubs/jersey_color_picker.dart';
import 'package:gte_frontend/widgets/clubs/jersey_preview_card.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class ClubJerseyDesignerScreen extends StatelessWidget {
  const ClubJerseyDesignerScreen({
    super.key,
    required this.controller,
  });

  final ClubController controller;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: controller,
      builder: (BuildContext context, _) {
        final identity = controller.identity;
        final JerseyVariantDto? activeVariant = controller.selectedKitVariant;
        return Container(
          decoration: gteBackdropDecoration(),
          child: Scaffold(
            backgroundColor: Colors.transparent,
            appBar: AppBar(
              title: const Text('Jersey design'),
            ),
            body: identity == null || activeVariant == null
                ? Padding(
                    padding: const EdgeInsets.all(20),
                    child: GteStatePanel(
                      title: 'Jersey design unavailable',
                      message: controller.errorMessage ??
                          'Load the club profile before opening this screen.',
                      icon: Icons.checkroom_outlined,
                    ),
                  )
                : ListView(
                    padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
                    children: <Widget>[
                      SegmentedButton<JerseyType>(
                        segments: identity.jerseySet.all.map((variant) {
                          return ButtonSegment<JerseyType>(
                            value: variant.jerseyType,
                            label: Text(variant.label),
                          );
                        }).toList(growable: false),
                        selected: <JerseyType>{controller.selectedKit},
                        onSelectionChanged: (Set<JerseyType> selection) {
                          controller.setSelectedKit(selection.first);
                        },
                      ),
                      const SizedBox(height: 18),
                      JerseyPreviewCard(
                        variant: activeVariant,
                        selected: true,
                      ),
                      const SizedBox(height: 18),
                      GteSurfacePanel(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Text(
                              'Color controls',
                              style: Theme.of(context).textTheme.titleLarge,
                            ),
                            const SizedBox(height: 16),
                            JerseyColorPicker(
                              label: 'Primary',
                              selectedColor: activeVariant.primaryColor,
                              colors: ClubIdentityDefaults.suggestedColors,
                              onSelected: (String value) =>
                                  controller.updateSelectedKit(primaryColor: value),
                            ),
                            const SizedBox(height: 16),
                            JerseyColorPicker(
                              label: 'Secondary',
                              selectedColor: activeVariant.secondaryColor,
                              colors: ClubIdentityDefaults.suggestedColors,
                              onSelected: (String value) => controller.updateSelectedKit(
                                secondaryColor: value,
                              ),
                            ),
                            const SizedBox(height: 16),
                            JerseyColorPicker(
                              label: 'Trim',
                              selectedColor: activeVariant.accentColor,
                              colors: ClubIdentityDefaults.suggestedColors,
                              onSelected: (String value) =>
                                  controller.updateSelectedKit(accentColor: value),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 18),
                      GteSurfacePanel(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Text(
                              'Style controls',
                              style: Theme.of(context).textTheme.titleLarge,
                            ),
                            const SizedBox(height: 16),
                            DropdownButtonFormField<PatternType>(
                              value: activeVariant.patternType,
                              items: PatternType.values.map((PatternType pattern) {
                                return DropdownMenuItem<PatternType>(
                                  value: pattern,
                                  child: Text(pattern.name),
                                );
                              }).toList(growable: false),
                              onChanged: (PatternType? value) {
                                if (value != null) {
                                  controller.updateSelectedKit(patternType: value);
                                }
                              },
                              decoration:
                                  const InputDecoration(labelText: 'Template'),
                            ),
                            const SizedBox(height: 14),
                            DropdownButtonFormField<CollarStyle>(
                              value: activeVariant.collarStyle,
                              items:
                                  CollarStyle.values.map((CollarStyle collar) {
                                return DropdownMenuItem<CollarStyle>(
                                  value: collar,
                                  child: Text(collar.name),
                                );
                              }).toList(growable: false),
                              onChanged: (CollarStyle? value) {
                                if (value != null) {
                                  controller.updateSelectedKit(collarStyle: value);
                                }
                              },
                              decoration:
                                  const InputDecoration(labelText: 'Collar'),
                            ),
                            const SizedBox(height: 14),
                            DropdownButtonFormField<SleeveStyle>(
                              value: activeVariant.sleeveStyle,
                              items:
                                  SleeveStyle.values.map((SleeveStyle sleeve) {
                                return DropdownMenuItem<SleeveStyle>(
                                  value: sleeve,
                                  child: Text(sleeve.name),
                                );
                              }).toList(growable: false),
                              onChanged: (SleeveStyle? value) {
                                if (value != null) {
                                  controller.updateSelectedKit(sleeveStyle: value);
                                }
                              },
                              decoration:
                                  const InputDecoration(labelText: 'Sleeve style'),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 18),
                      FilledButton.icon(
                        onPressed:
                            controller.isSavingIdentity ? null : controller.saveIdentity,
                        icon: controller.isSavingIdentity
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : const Icon(Icons.save_outlined),
                        label: const Text('Save jersey design'),
                      ),
                    ],
                  ),
          ),
        );
      },
    );
  }
}
