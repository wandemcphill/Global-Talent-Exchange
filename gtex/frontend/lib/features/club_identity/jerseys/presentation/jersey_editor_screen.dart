import 'package:flutter/material.dart';

import '../../../../widgets/gte_shell_theme.dart';
import '../../../../widgets/gte_state_panel.dart';
import '../../../../widgets/gte_surface_panel.dart';
import '../data/club_identity_defaults.dart';
import '../data/jersey_variant_dto.dart';
import '../widgets/clash_warning_banner.dart';
import '../widgets/jersey_color_picker_row.dart';
import '../widgets/jersey_preview_card.dart';
import '../widgets/identity_status_banner.dart';
import '../widgets/pattern_selector.dart';
import 'club_identity_controller.dart';

class JerseyEditorScreen extends StatefulWidget {
  const JerseyEditorScreen({
    super.key,
    required this.controller,
  });

  final ClubIdentityController controller;

  @override
  State<JerseyEditorScreen> createState() => _JerseyEditorScreenState();
}

class _JerseyEditorScreenState extends State<JerseyEditorScreen> {
  JerseyType _selectedType = JerseyType.home;

  ClubIdentityController get _controller => widget.controller;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (BuildContext context, _) {
        final identity = _controller.identity;
        return PopScope(
          canPop: !_controller.hasUnsavedChanges,
          onPopInvokedWithResult: (
            bool didPop,
            Object? result,
          ) async {
            if (didPop || !_controller.hasUnsavedChanges) {
              return;
            }
            final NavigatorState navigator = Navigator.of(context);
            final _LeaveAction action = await _showLeaveDialog();
            if (!mounted) {
              return;
            }
            switch (action) {
              case _LeaveAction.stay:
                return;
              case _LeaveAction.discard:
                _controller.discardUnsavedChanges();
                navigator.pop();
                return;
              case _LeaveAction.save:
                await _controller.saveAll();
                if (!mounted) {
                  return;
                }
                navigator.pop();
                return;
            }
          },
          child: Scaffold(
            appBar: AppBar(
              title: const Text('Jersey Editor'),
              actions: <Widget>[
                IconButton(
                  tooltip: 'Reload saved kits',
                  onPressed: _controller.reload,
                  icon: const Icon(Icons.refresh),
                ),
                IconButton(
                  tooltip: 'Save changes',
                  onPressed: _controller.saveAll,
                  icon: const Icon(Icons.save_outlined),
                ),
              ],
            ),
            body: Container(
              decoration: gteBackdropDecoration(),
              child: identity == null
                  ? const Padding(
                      padding: EdgeInsets.all(20),
                      child: GteStatePanel(
                        title: 'Jersey editor unavailable',
                        message: 'Load a club identity before editing kits.',
                        icon: Icons.checkroom_outlined,
                      ),
                    )
                  : SingleChildScrollView(
                      padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(
                            'Kit workstation',
                            style: Theme.of(context).textTheme.headlineSmall,
                          ),
                          const SizedBox(height: 8),
                          Text(
                            'Tweak each strip with live preview feedback, then keep home and away clearly separated for quick match readability.',
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                          const SizedBox(height: 20),
                          if (_controller.errorMessage != null) ...<Widget>[
                            IdentityStatusBanner(
                              icon: Icons.error_outline,
                              message: _controller.errorMessage!,
                              color: GteShellTheme.negative,
                            ),
                            const SizedBox(height: 16),
                          ],
                          ClashWarningBanner(
                            warnings: _controller.warnings,
                            title: _controller.hasUnsavedChanges
                                ? 'Draft warnings'
                                : 'Live kit check',
                          ),
                          const SizedBox(height: 20),
                          Wrap(
                            spacing: 12,
                            runSpacing: 12,
                            children: identity.jerseySet.all
                                .map((JerseyVariantDto variant) {
                              return SizedBox(
                                width: 240,
                                child: JerseyPreviewCard(
                                  variant: variant,
                                  compact: true,
                                  selected: variant.jerseyType == _selectedType,
                                  onTap: () {
                                    setState(() {
                                      _selectedType = variant.jerseyType;
                                    });
                                  },
                                ),
                              );
                            }).toList(growable: false),
                          ),
                          const SizedBox(height: 20),
                          LayoutBuilder(
                            builder: (BuildContext context,
                                BoxConstraints constraints) {
                              final bool stacked = constraints.maxWidth < 920;
                              final JerseyVariantDto variant =
                                  identity.jerseySet.variantFor(_selectedType);
                              final Widget preview = SizedBox(
                                width: stacked ? constraints.maxWidth : 320,
                                child: JerseyPreviewCard(
                                  variant: variant,
                                ),
                              );
                              final Widget controls = SizedBox(
                                width: stacked
                                    ? constraints.maxWidth
                                    : constraints.maxWidth - 352,
                                child: _EditorControls(
                                  controller: _controller,
                                  selectedType: _selectedType,
                                ),
                              );
                              return Wrap(
                                spacing: 20,
                                runSpacing: 20,
                                children: stacked
                                    ? <Widget>[preview, controls]
                                    : <Widget>[preview, controls],
                              );
                            },
                          ),
                        ],
                      ),
                    ),
            ),
          ),
        );
      },
    );
  }

  Future<_LeaveAction> _showLeaveDialog() async {
    final _LeaveAction? action = await showDialog<_LeaveAction>(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: const Text('Leave with unsaved changes?'),
          content: const Text(
            'Your local jersey edits are still in preview mode. Save or discard before leaving this screen.',
          ),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.of(context).pop(_LeaveAction.stay),
              child: const Text('Stay'),
            ),
            FilledButton.tonal(
              onPressed: () {
                Navigator.of(context).pop(_LeaveAction.discard);
              },
              child: const Text('Discard'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(_LeaveAction.save),
              child: const Text('Save & leave'),
            ),
          ],
        );
      },
    );
    return action ?? _LeaveAction.stay;
  }
}

class _EditorControls extends StatelessWidget {
  const _EditorControls({
    required this.controller,
    required this.selectedType,
  });

  final ClubIdentityController controller;
  final JerseyType selectedType;

  @override
  Widget build(BuildContext context) {
    final identity = controller.identity!;
    final variant = identity.jerseySet.variantFor(selectedType);
    final List<String> suggestions = <String>{
      identity.colorPalette.primaryColor,
      identity.colorPalette.secondaryColor,
      identity.colorPalette.accentColor,
      identity.colorPalette.shortsColor,
      identity.colorPalette.socksColor,
      ...ClubIdentityDefaults.suggestedColors,
    }.toList(growable: false);

    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Text(
                  '${variant.label} kit controls',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
              if (controller.hasUnsavedChanges)
                Text(
                  'Unsaved',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: GteShellTheme.accentWarm,
                      ),
                ),
            ],
          ),
          const SizedBox(height: 16),
          JerseyColorPickerRow(
            label: 'Primary color',
            selectedColor: variant.primaryColor,
            paletteSuggestions: suggestions,
            onSelected: (String value) {
              controller.updateJerseyVariant(selectedType, primaryColor: value);
            },
          ),
          const SizedBox(height: 18),
          JerseyColorPickerRow(
            label: 'Secondary color',
            selectedColor: variant.secondaryColor,
            paletteSuggestions: suggestions,
            onSelected: (String value) {
              controller.updateJerseyVariant(selectedType,
                  secondaryColor: value);
            },
          ),
          const SizedBox(height: 18),
          JerseyColorPickerRow(
            label: 'Accent color',
            selectedColor: variant.accentColor,
            paletteSuggestions: suggestions,
            onSelected: (String value) {
              controller.updateJerseyVariant(selectedType, accentColor: value);
            },
          ),
          const SizedBox(height: 18),
          Text('Pattern', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 10),
          PatternSelector(
            selected: variant.patternType,
            onSelected: (PatternType type) {
              controller.updateJerseyVariant(selectedType, patternType: type);
            },
          ),
          const SizedBox(height: 18),
          _EnumDropdown<CollarStyle>(
            label: 'Collar style',
            value: variant.collarStyle,
            options: CollarStyle.values,
            itemLabel: _collarLabel,
            onChanged: (CollarStyle? value) {
              if (value != null) {
                controller.updateJerseyVariant(selectedType,
                    collarStyle: value);
              }
            },
          ),
          const SizedBox(height: 18),
          _EnumDropdown<SleeveStyle>(
            label: 'Sleeve style',
            value: variant.sleeveStyle,
            options: SleeveStyle.values,
            itemLabel: _sleeveLabel,
            onChanged: (SleeveStyle? value) {
              if (value != null) {
                controller.updateJerseyVariant(selectedType,
                    sleeveStyle: value);
              }
            },
          ),
          const SizedBox(height: 18),
          JerseyColorPickerRow(
            label: 'Shorts color',
            selectedColor: variant.shortsColor,
            paletteSuggestions: suggestions,
            onSelected: (String value) {
              controller.updateJerseyVariant(selectedType, shortsColor: value);
            },
          ),
          const SizedBox(height: 18),
          JerseyColorPickerRow(
            label: 'Socks color',
            selectedColor: variant.socksColor,
            paletteSuggestions: suggestions,
            onSelected: (String value) {
              controller.updateJerseyVariant(selectedType, socksColor: value);
            },
          ),
          const SizedBox(height: 24),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              FilledButton.tonalIcon(
                onPressed: () => controller.regenerateFallbackKit(selectedType),
                icon: const Icon(Icons.auto_fix_high_outlined),
                label: const Text('Auto-generate fallback kit'),
              ),
              OutlinedButton.icon(
                onPressed: controller.discardUnsavedChanges,
                icon: const Icon(Icons.restore),
                label: const Text('Discard unsaved'),
              ),
              OutlinedButton.icon(
                onPressed: controller.resetToGeneratedDefaults,
                icon: const Icon(Icons.restart_alt),
                label: const Text('Reset all to defaults'),
              ),
              FilledButton.icon(
                onPressed: controller.saveAll,
                icon: controller.isSaving
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.save_outlined),
                label: const Text('Save changes'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _EnumDropdown<T> extends StatelessWidget {
  const _EnumDropdown({
    required this.label,
    required this.value,
    required this.options,
    required this.itemLabel,
    required this.onChanged,
  });

  final String label;
  final T value;
  final List<T> options;
  final String Function(T) itemLabel;
  final ValueChanged<T?> onChanged;

  @override
  Widget build(BuildContext context) {
    return DropdownButtonFormField<T>(
      initialValue: value,
      decoration: InputDecoration(
        labelText: label,
        filled: true,
        fillColor: GteShellTheme.panelStrong.withValues(alpha: 0.5),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(18),
          borderSide: const BorderSide(color: GteShellTheme.stroke),
        ),
      ),
      dropdownColor: GteShellTheme.panelStrong,
      items: options
          .map(
            (T option) => DropdownMenuItem<T>(
              value: option,
              child: Text(itemLabel(option)),
            ),
          )
          .toList(growable: false),
      onChanged: onChanged,
    );
  }
}

enum _LeaveAction { stay, discard, save }

String _collarLabel(CollarStyle style) {
  switch (style) {
    case CollarStyle.crew:
      return 'Crew';
    case CollarStyle.vNeck:
      return 'V-neck';
    case CollarStyle.polo:
      return 'Polo';
    case CollarStyle.wrap:
      return 'Wrap';
  }
}

String _sleeveLabel(SleeveStyle style) {
  switch (style) {
    case SleeveStyle.short:
      return 'Short';
    case SleeveStyle.long:
      return 'Long';
    case SleeveStyle.raglan:
      return 'Raglan';
    case SleeveStyle.cuffed:
      return 'Cuffed';
  }
}
