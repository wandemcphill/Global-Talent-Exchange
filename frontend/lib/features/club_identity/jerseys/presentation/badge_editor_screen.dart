import 'package:flutter/material.dart';

import '../../../../widgets/gte_shell_theme.dart';
import '../../../../widgets/gte_state_panel.dart';
import '../../../../widgets/gte_surface_panel.dart';
import '../data/badge_profile_dto.dart';
import '../data/club_identity_defaults.dart';
import '../data/club_identity_dto.dart';
import '../widgets/badge_preview_widget.dart';
import '../widgets/badge_shape_selector.dart';
import '../widgets/clash_warning_banner.dart';
import '../widgets/identity_color_utils.dart';
import 'club_identity_controller.dart';

class BadgeEditorScreen extends StatefulWidget {
  const BadgeEditorScreen({
    super.key,
    required this.controller,
  });

  final ClubIdentityController controller;

  @override
  State<BadgeEditorScreen> createState() => _BadgeEditorScreenState();
}

class _BadgeEditorScreenState extends State<BadgeEditorScreen> {
  late final TextEditingController _clubNameController;
  late final TextEditingController _shortCodeController;
  late final TextEditingController _initialsController;

  ClubIdentityController get _controller => widget.controller;

  @override
  void initState() {
    super.initState();
    final ClubIdentityDto? identity = _controller.identity;
    _clubNameController = TextEditingController(text: identity?.clubName ?? '');
    _shortCodeController = TextEditingController(
      text: identity?.shortClubCode ?? '',
    );
    _initialsController = TextEditingController(
      text: identity?.badgeProfile.initials ?? '',
    );
  }

  @override
  void dispose() {
    _clubNameController.dispose();
    _shortCodeController.dispose();
    _initialsController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (BuildContext context, _) {
        final ClubIdentityDto? identity = _controller.identity;
        if (identity != null) {
          _syncTextControllers(identity);
        }
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
              title: const Text('Badge Editor'),
              actions: <Widget>[
                IconButton(
                  tooltip: 'Reload',
                  onPressed: _controller.reload,
                  icon: const Icon(Icons.refresh),
                ),
                IconButton(
                  tooltip: 'Save',
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
                        title: 'Badge editor unavailable',
                        message:
                            'Load a club identity before editing the badge.',
                        icon: Icons.shield_outlined,
                      ),
                    )
                  : SingleChildScrollView(
                      padding: const EdgeInsets.fromLTRB(20, 12, 20, 32),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(
                            'Badge composition',
                            style: Theme.of(context).textTheme.headlineSmall,
                          ),
                          const SizedBox(height: 8),
                          Text(
                            'Tune monogram, icon family, and shape while keeping the palette aligned with the club\'s kits.',
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                          const SizedBox(height: 20),
                          ClashWarningBanner(
                            warnings: _controller.hasUnsavedChanges
                                ? const <String>[
                                    'Badge and club-code changes are still local until you save the profile.',
                                  ]
                                : const <String>[],
                            title: 'Edit state',
                          ),
                          const SizedBox(height: 20),
                          LayoutBuilder(
                            builder: (
                              BuildContext context,
                              BoxConstraints constraints,
                            ) {
                              final bool stacked = constraints.maxWidth < 920;
                              final Widget preview = SizedBox(
                                width: stacked ? constraints.maxWidth : 300,
                                child: GteSurfacePanel(
                                  emphasized: true,
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.center,
                                    children: <Widget>[
                                      BadgePreviewWidget(
                                        badge: identity.badgeProfile,
                                        size: 148,
                                      ),
                                      const SizedBox(height: 16),
                                      Text(
                                        identity.clubName,
                                        style: Theme.of(context)
                                            .textTheme
                                            .headlineSmall,
                                        textAlign: TextAlign.center,
                                      ),
                                      const SizedBox(height: 6),
                                      Text(
                                        identity.shortClubCode,
                                        style: Theme.of(context)
                                            .textTheme
                                            .bodyMedium,
                                      ),
                                    ],
                                  ),
                                ),
                              );
                              final Widget form = SizedBox(
                                width: stacked
                                    ? constraints.maxWidth
                                    : constraints.maxWidth - 332,
                                child: _BadgeEditorForm(
                                  controller: _controller,
                                  clubNameController: _clubNameController,
                                  shortCodeController: _shortCodeController,
                                  initialsController: _initialsController,
                                ),
                              );
                              return Wrap(
                                spacing: 20,
                                runSpacing: 20,
                                children: <Widget>[preview, form],
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

  void _syncTextControllers(ClubIdentityDto identity) {
    if (_clubNameController.text != identity.clubName) {
      _clubNameController.value = _clubNameController.value.copyWith(
        text: identity.clubName,
        selection: TextSelection.collapsed(offset: identity.clubName.length),
      );
    }
    if (_shortCodeController.text != identity.shortClubCode) {
      _shortCodeController.value = _shortCodeController.value.copyWith(
        text: identity.shortClubCode,
        selection:
            TextSelection.collapsed(offset: identity.shortClubCode.length),
      );
    }
    if (_initialsController.text != identity.badgeProfile.initials) {
      _initialsController.value = _initialsController.value.copyWith(
        text: identity.badgeProfile.initials,
        selection: TextSelection.collapsed(
          offset: identity.badgeProfile.initials.length,
        ),
      );
    }
  }

  Future<_LeaveAction> _showLeaveDialog() async {
    final _LeaveAction? action = await showDialog<_LeaveAction>(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: const Text('Leave badge edits?'),
          content: const Text(
            'You have unsaved badge or club-code changes. Save or discard them before leaving this screen.',
          ),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.of(context).pop(_LeaveAction.stay),
              child: const Text('Stay'),
            ),
            FilledButton.tonal(
              onPressed: () => Navigator.of(context).pop(_LeaveAction.discard),
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

class _BadgeEditorForm extends StatelessWidget {
  const _BadgeEditorForm({
    required this.controller,
    required this.clubNameController,
    required this.shortCodeController,
    required this.initialsController,
  });

  final ClubIdentityController controller;
  final TextEditingController clubNameController;
  final TextEditingController shortCodeController;
  final TextEditingController initialsController;

  @override
  Widget build(BuildContext context) {
    final ClubIdentityDto identity = controller.identity!;
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Identity details',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 16),
          TextField(
            controller: clubNameController,
            decoration: _inputDecoration('Club name'),
            onChanged: controller.updateClubName,
          ),
          const SizedBox(height: 16),
          TextField(
            controller: shortCodeController,
            decoration: _inputDecoration('Short club code'),
            maxLength: 4,
            textCapitalization: TextCapitalization.characters,
            onChanged: controller.updateShortClubCode,
          ),
          const SizedBox(height: 8),
          TextField(
            controller: initialsController,
            decoration: _inputDecoration('Badge initials / monogram'),
            maxLength: 4,
            textCapitalization: TextCapitalization.characters,
            onChanged: (String value) {
              controller.updateBadge(initials: value.toUpperCase());
            },
          ),
          const SizedBox(height: 18),
          Text('Badge shape', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 10),
          BadgeShapeSelector(
            selectedShape: identity.badgeProfile.shape,
            onSelected: (BadgeShape shape) {
              controller.updateBadge(shape: shape);
            },
          ),
          const SizedBox(height: 18),
          DropdownButtonFormField<BadgeIconFamily>(
            initialValue: identity.badgeProfile.iconFamily,
            decoration: _inputDecoration('Icon family'),
            dropdownColor: GteShellTheme.panelStrong,
            items: BadgeIconFamily.values
                .map(
                  (BadgeIconFamily family) => DropdownMenuItem<BadgeIconFamily>(
                    value: family,
                    child: Text(_iconLabel(family)),
                  ),
                )
                .toList(growable: false),
            onChanged: (BadgeIconFamily? family) {
              if (family != null) {
                controller.updateBadge(iconFamily: family);
              }
            },
          ),
          const SizedBox(height: 18),
          Text(
            'Palette binding',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <Widget>[
              _ColorTile(
                label: 'Primary',
                colorHex: identity.colorPalette.primaryColor,
              ),
              _ColorTile(
                label: 'Secondary',
                colorHex: identity.colorPalette.secondaryColor,
              ),
              _ColorTile(
                label: 'Accent',
                colorHex: identity.colorPalette.accentColor,
              ),
            ],
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              FilledButton.tonalIcon(
                onPressed: controller.bindBadgeToPalette,
                icon: const Icon(Icons.palette_outlined),
                label: const Text('Bind badge to palette'),
              ),
              OutlinedButton.icon(
                onPressed: controller.resetToGeneratedDefaults,
                icon: const Icon(Icons.auto_fix_high_outlined),
                label: const Text('Reset generated defaults'),
              ),
              OutlinedButton.icon(
                onPressed: controller.discardUnsavedChanges,
                icon: const Icon(Icons.restore),
                label: const Text('Discard unsaved'),
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
          const SizedBox(height: 20),
          Text(
            'Palette presets',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: ClubIdentityDefaults.palettes.map((palette) {
              return InkWell(
                onTap: () => controller.updatePalette(palette),
                borderRadius: BorderRadius.circular(18),
                child: Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(18),
                    border: Border.all(color: GteShellTheme.stroke),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: <Widget>[
                      _ColorDot(colorHex: palette.primaryColor),
                      const SizedBox(width: 6),
                      _ColorDot(colorHex: palette.secondaryColor),
                      const SizedBox(width: 6),
                      _ColorDot(colorHex: palette.accentColor),
                      const SizedBox(width: 10),
                      Text(palette.paletteName),
                    ],
                  ),
                ),
              );
            }).toList(growable: false),
          ),
        ],
      ),
    );
  }

  InputDecoration _inputDecoration(String label) {
    return InputDecoration(
      labelText: label,
      filled: true,
      fillColor: GteShellTheme.panelStrong.withValues(alpha: 0.5),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(18),
        borderSide: const BorderSide(color: GteShellTheme.stroke),
      ),
    );
  }

  String _iconLabel(BadgeIconFamily family) {
    switch (family) {
      case BadgeIconFamily.star:
        return 'Star';
      case BadgeIconFamily.lion:
        return 'Lion';
      case BadgeIconFamily.eagle:
        return 'Eagle';
      case BadgeIconFamily.crown:
        return 'Crown';
      case BadgeIconFamily.oak:
        return 'Oak';
      case BadgeIconFamily.bolt:
        return 'Bolt';
    }
  }
}

enum _LeaveAction { stay, discard, save }

class _ColorTile extends StatelessWidget {
  const _ColorTile({
    required this.label,
    required this.colorHex,
  });

  final String label;
  final String colorHex;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: GteShellTheme.stroke),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          _ColorDot(colorHex: colorHex),
          const SizedBox(width: 8),
          Text(label),
        ],
      ),
    );
  }
}

class _ColorDot extends StatelessWidget {
  const _ColorDot({
    required this.colorHex,
  });

  final String colorHex;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 14,
      height: 14,
      decoration: BoxDecoration(
        color: identityColorFromHex(colorHex),
        shape: BoxShape.circle,
        border: Border.all(color: Colors.white.withValues(alpha: 0.25)),
      ),
    );
  }
}
