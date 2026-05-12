import 'package:flutter/material.dart';

import '../../core/app_feedback.dart';
import '../../data/club_creation_api.dart';
import '../../data/gte_api_repository.dart';
import '../../ui_gtex/components/gtex_button.dart';
import '../../ui_gtex/components/gtex_panel.dart';
import '../../ui_gtex/components/gtex_status_chip.dart';
import '../../ui_gtex/layout/gtex_focus_flow_scaffold.dart';
import '../../ui_gtex/theme/gtex_colors.dart';
import '../../ui_gtex/theme/gtex_spacing.dart';

class CreateClubScreen extends StatefulWidget {
  const CreateClubScreen({
    super.key,
    required this.baseUrl,
    required this.accessToken,
    required this.backendMode,
    this.onClubCreated,
  });

  final String baseUrl;
  final String accessToken;
  final GteBackendMode backendMode;
  final ValueChanged<GteCreatedClubProfile>? onClubCreated;

  @override
  State<CreateClubScreen> createState() => _CreateClubScreenState();
}

class _CreateClubScreenState extends State<CreateClubScreen> {
  late final ClubCreationApi _api;
  final TextEditingController _clubNameController = TextEditingController();
  final TextEditingController _shortNameController = TextEditingController();
  final TextEditingController _slugController = TextEditingController();
  final TextEditingController _countryCodeController = TextEditingController(
    text: 'NG',
  );
  final TextEditingController _regionController = TextEditingController(
    text: 'Lagos',
  );
  final TextEditingController _cityController = TextEditingController(
    text: 'Lagos',
  );
  final TextEditingController _venueController = TextEditingController();
  final TextEditingController _descriptionController = TextEditingController();
  final TextEditingController _primaryColorController = TextEditingController();
  final TextEditingController _secondaryColorController =
      TextEditingController();
  final TextEditingController _accentColorController = TextEditingController();

  bool _submitting = false;
  bool _slugWasEdited = false;
  String _visibility = 'public';
  _ClubPalette _selectedPalette = _clubPalettes.first;

  @override
  void initState() {
    super.initState();
    _api = ClubCreationApi.standard(
      baseUrl: widget.baseUrl,
      accessToken: widget.accessToken,
      mode: widget.backendMode,
    );
    _applyPalette(_selectedPalette);
    _clubNameController.addListener(_handleClubNameChanged);
    _slugController.addListener(_handleSlugEdited);
  }

  @override
  void dispose() {
    _clubNameController.dispose();
    _shortNameController.dispose();
    _slugController.dispose();
    _countryCodeController.dispose();
    _regionController.dispose();
    _cityController.dispose();
    _venueController.dispose();
    _descriptionController.dispose();
    _primaryColorController.dispose();
    _secondaryColorController.dispose();
    _accentColorController.dispose();
    super.dispose();
  }

  void _handleClubNameChanged() {
    if (_slugWasEdited) {
      return;
    }
    final String generated = _slugify(_clubNameController.text);
    if (_slugController.text != generated) {
      _slugController.text = generated;
    }
  }

  void _handleSlugEdited() {
    final String current = _slugController.text.trim();
    final String generated = _slugify(_clubNameController.text);
    _slugWasEdited = current.isNotEmpty && current != generated;
  }

  void _applyPalette(_ClubPalette palette) {
    _selectedPalette = palette;
    _primaryColorController.text = palette.primary;
    _secondaryColorController.text = palette.secondary;
    _accentColorController.text = palette.accent;
  }

  Future<void> _submit() async {
    final String clubName = _clubNameController.text.trim();
    final String slug = _slugify(_slugController.text);
    if (clubName.length < 2) {
      AppFeedback.showError(context, 'Enter a club name.');
      return;
    }
    if (slug.length < 2) {
      AppFeedback.showError(context, 'Enter a valid club slug.');
      return;
    }
    if (!_isHexColor(_primaryColorController.text) ||
        !_isHexColor(_secondaryColorController.text) ||
        !_isHexColor(_accentColorController.text)) {
      AppFeedback.showError(
        context,
        'Use valid hex colors like #0B1F3A for the club palette.',
      );
      return;
    }

    setState(() {
      _submitting = true;
    });
    try {
      final GteCreatedClubProfile created = await _api.createClub(
        GteCreateClubRequest(
          clubName: clubName,
          shortName: _emptyToNull(_shortNameController.text),
          slug: slug,
          primaryColor: _normalizedHex(_primaryColorController.text),
          secondaryColor: _normalizedHex(_secondaryColorController.text),
          accentColor: _normalizedHex(_accentColorController.text),
          homeVenueName: _emptyToNull(_venueController.text),
          countryCode: _emptyToNull(_countryCodeController.text),
          regionName: _emptyToNull(_regionController.text),
          cityName: _emptyToNull(_cityController.text),
          description: _emptyToNull(_descriptionController.text),
          visibility: _visibility,
        ),
      );
      if (!mounted) {
        return;
      }
      widget.onClubCreated?.call(created);
      AppFeedback.showSuccess(context, '${created.clubName} is live.');
      Navigator.of(context).pop<GteCreatedClubProfile>(created);
    } catch (error) {
      if (mounted) {
        AppFeedback.showError(context, error);
      }
    } finally {
      if (mounted) {
        setState(() {
          _submitting = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return GtexFocusFlowScaffold(
      title: 'Launch your GTEX club',
      subtitle:
          'Create the live ownership workspace that unlocks squad management, club identity, competitions, finances, followers, shares, and news.',
      maxWidth: 1240,
      accent: GtexColors.gold,
      leading: Align(
        alignment: Alignment.centerLeft,
        child: GtexButton(
          label: 'Back',
          icon: Icons.arrow_back,
          variant: GtexButtonVariant.ghost,
          compact: true,
          onPressed: () => Navigator.of(context).maybePop(),
        ),
      ),
      child: LayoutBuilder(
        builder: (BuildContext context, BoxConstraints constraints) {
          final bool stacked = constraints.maxWidth < 930;
          final Widget briefing = _ClubLaunchBriefing(stacked: stacked);
          final Widget form = Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              _FormSection(
                title: 'Club basics',
                subtitle: 'Name the club and decide how visible it should be.',
                accent: GtexColors.gold,
                children: <Widget>[
                  TextField(
                    controller: _clubNameController,
                    style: const TextStyle(color: GtexColors.text),
                    decoration: _gtexInputDecoration(
                      label: 'Club name',
                      hint: 'Lagos Comets FC',
                      icon: Icons.shield_outlined,
                    ),
                  ),
                  const SizedBox(height: GtexSpacing.sm),
                  TextField(
                    controller: _shortNameController,
                    style: const TextStyle(color: GtexColors.text),
                    decoration: _gtexInputDecoration(
                      label: 'Short name',
                      hint: 'Comets',
                      icon: Icons.badge_outlined,
                    ),
                  ),
                  const SizedBox(height: GtexSpacing.sm),
                  TextField(
                    controller: _slugController,
                    style: const TextStyle(color: GtexColors.text),
                    decoration: _gtexInputDecoration(
                      label: 'Slug',
                      hint: 'lagos-comets-fc',
                      icon: Icons.link,
                    ),
                  ),
                  const SizedBox(height: GtexSpacing.sm),
                  DropdownButtonFormField<String>(
                    value: _visibility,
                    dropdownColor: GtexColors.panelStrong,
                    style: const TextStyle(color: GtexColors.text),
                    decoration: _gtexInputDecoration(
                      label: 'Visibility',
                      icon: Icons.visibility_outlined,
                    ),
                    items: const <DropdownMenuItem<String>>[
                      DropdownMenuItem<String>(
                        value: 'public',
                        child: Text('Public'),
                      ),
                      DropdownMenuItem<String>(
                        value: 'community',
                        child: Text('Community'),
                      ),
                      DropdownMenuItem<String>(
                        value: 'private',
                        child: Text('Private'),
                      ),
                    ],
                    onChanged: (String? value) {
                      if (value == null) {
                        return;
                      }
                      setState(() {
                        _visibility = value;
                      });
                    },
                  ),
                ],
              ),
              const SizedBox(height: GtexSpacing.md),
              _FormSection(
                title: 'Identity palette',
                subtitle:
                    'Pick a launch palette, then fine-tune the exact club colors.',
                accent: GtexColors.pitch,
                children: <Widget>[
                  Wrap(
                    spacing: GtexSpacing.sm,
                    runSpacing: GtexSpacing.sm,
                    children: _clubPalettes
                        .map((_ClubPalette palette) {
                          final bool selected = identical(
                            palette,
                            _selectedPalette,
                          );
                          return _PaletteChoice(
                            palette: palette,
                            selected: selected,
                            onTap: () {
                              setState(() {
                                _applyPalette(palette);
                              });
                            },
                          );
                        })
                        .toList(growable: false),
                  ),
                  const SizedBox(height: GtexSpacing.md),
                  TextField(
                    controller: _primaryColorController,
                    style: const TextStyle(color: GtexColors.text),
                    decoration: _gtexInputDecoration(
                      label: 'Primary color',
                      icon: Icons.palette_outlined,
                    ),
                  ),
                  const SizedBox(height: GtexSpacing.sm),
                  TextField(
                    controller: _secondaryColorController,
                    style: const TextStyle(color: GtexColors.text),
                    decoration: _gtexInputDecoration(
                      label: 'Secondary color',
                      icon: Icons.color_lens_outlined,
                    ),
                  ),
                  const SizedBox(height: GtexSpacing.sm),
                  TextField(
                    controller: _accentColorController,
                    style: const TextStyle(color: GtexColors.text),
                    decoration: _gtexInputDecoration(
                      label: 'Accent color',
                      icon: Icons.bolt_outlined,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: GtexSpacing.md),
              _FormSection(
                title: 'Location and story',
                subtitle:
                    'Give the club a home base and a football identity people can follow.',
                accent: GtexColors.cyan,
                children: <Widget>[
                  TextField(
                    controller: _venueController,
                    style: const TextStyle(color: GtexColors.text),
                    decoration: _gtexInputDecoration(
                      label: 'Home venue',
                      hint: 'Marina Arena',
                      icon: Icons.stadium_outlined,
                    ),
                  ),
                  const SizedBox(height: GtexSpacing.sm),
                  TextField(
                    controller: _countryCodeController,
                    style: const TextStyle(color: GtexColors.text),
                    decoration: _gtexInputDecoration(
                      label: 'Country code',
                      hint: 'NG',
                      icon: Icons.flag_outlined,
                    ),
                  ),
                  const SizedBox(height: GtexSpacing.sm),
                  TextField(
                    controller: _regionController,
                    style: const TextStyle(color: GtexColors.text),
                    decoration: _gtexInputDecoration(
                      label: 'Region',
                      icon: Icons.map_outlined,
                    ),
                  ),
                  const SizedBox(height: GtexSpacing.sm),
                  TextField(
                    controller: _cityController,
                    style: const TextStyle(color: GtexColors.text),
                    decoration: _gtexInputDecoration(
                      label: 'City',
                      icon: Icons.location_city_outlined,
                    ),
                  ),
                  const SizedBox(height: GtexSpacing.sm),
                  TextField(
                    controller: _descriptionController,
                    maxLines: 4,
                    style: const TextStyle(color: GtexColors.text),
                    decoration: _gtexInputDecoration(
                      label: 'Description',
                      hint:
                          'Describe the club identity, fan culture, and sporting ambition.',
                      icon: Icons.notes_outlined,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: GtexSpacing.md),
              _LaunchPanel(
                submitting: _submitting,
                onSubmit: _submitting ? null : _submit,
              ),
            ],
          );

          if (stacked) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                briefing,
                const SizedBox(height: GtexSpacing.lg),
                form,
              ],
            );
          }
          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Expanded(flex: 4, child: briefing),
              const SizedBox(width: GtexSpacing.lg),
              Expanded(flex: 6, child: form),
            ],
          );
        },
      ),
    );
  }
}

class _ClubLaunchBriefing extends StatelessWidget {
  const _ClubLaunchBriefing({required this.stacked});

  final bool stacked;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        const GtexStatusChip(
          label: 'LIVE CLUB CREATION',
          icon: Icons.rocket_launch_outlined,
          tone: GtexStatusTone.premium,
        ),
        const SizedBox(height: GtexSpacing.lg),
        Text(
          'This is where a user stops browsing and becomes a club owner.',
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
            color: GtexColors.text,
            fontWeight: FontWeight.w900,
            height: 1.08,
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        Text(
          'The form still calls the live club creation API. The redesign simply puts that serious operation inside the same GTEX command-center language as the market and owner dashboard.',
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
            color: GtexColors.textSecondary,
            height: 1.45,
          ),
        ),
        const SizedBox(height: GtexSpacing.lg),
        Wrap(
          spacing: GtexSpacing.md,
          runSpacing: GtexSpacing.md,
          children: <Widget>[
            _BriefingTile(
              width: stacked ? double.infinity : 250,
              title: 'Owner workspace',
              body: 'Squad, transfers, finances, trophies, identity.',
              icon: Icons.admin_panel_settings_outlined,
              accent: GtexColors.gold,
            ),
            _BriefingTile(
              width: stacked ? double.infinity : 250,
              title: 'Public profile',
              body: 'Followers, shares, club value, and public story.',
              icon: Icons.public_outlined,
              accent: GtexColors.pitch,
            ),
            _BriefingTile(
              width: stacked ? double.infinity : 250,
              title: 'Competition path',
              body: 'A club identity ready for fixtures and tournaments.',
              icon: Icons.emoji_events_outlined,
              accent: GtexColors.cyan,
            ),
          ],
        ),
      ],
    );
  }
}

class _BriefingTile extends StatelessWidget {
  const _BriefingTile({
    required this.width,
    required this.title,
    required this.body,
    required this.icon,
    required this.accent,
  });

  final double width;
  final String title;
  final String body;
  final IconData icon;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: width,
      child: GtexPanel(
        title: title,
        subtitle: body,
        trailing: Icon(icon, color: accent),
        accent: accent,
        child: const SizedBox.shrink(),
      ),
    );
  }
}

class _FormSection extends StatelessWidget {
  const _FormSection({
    required this.title,
    required this.subtitle,
    required this.accent,
    required this.children,
  });

  final String title;
  final String subtitle;
  final Color accent;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      title: title,
      subtitle: subtitle,
      accent: accent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: children,
      ),
    );
  }
}

class _PaletteChoice extends StatelessWidget {
  const _PaletteChoice({
    required this.palette,
    required this.selected,
    required this.onTap,
  });

  final _ClubPalette palette;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final Color accent = selected ? GtexColors.pitch : GtexColors.textMuted;
    return SizedBox(
      width: 170,
      child: GtexPanel(
        title: palette.name,
        accent: accent,
        isSelected: selected,
        onTap: onTap,
        padding: const EdgeInsets.all(GtexSpacing.md),
        child: Row(
          children: <Widget>[
            _ColorDot(color: palette.primary),
            const SizedBox(width: GtexSpacing.xs),
            _ColorDot(color: palette.secondary),
            const SizedBox(width: GtexSpacing.xs),
            _ColorDot(color: palette.accent),
          ],
        ),
      ),
    );
  }
}

class _LaunchPanel extends StatelessWidget {
  const _LaunchPanel({required this.submitting, required this.onSubmit});

  final bool submitting;
  final VoidCallback? onSubmit;

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      title: 'Ready to launch',
      subtitle:
          'Create the club and this account moves straight into the owner dashboard.',
      accent: GtexColors.pitch,
      trailing: const Icon(
        Icons.rocket_launch_outlined,
        color: GtexColors.pitch,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          if (submitting) ...<Widget>[
            const LinearProgressIndicator(color: GtexColors.pitch),
            const SizedBox(height: GtexSpacing.md),
          ],
          GtexButton(
            label: submitting ? 'Creating club...' : 'Create club',
            icon: Icons.shield_outlined,
            onPressed: onSubmit,
          ),
        ],
      ),
    );
  }
}

class _ColorDot extends StatelessWidget {
  const _ColorDot({required this.color});

  final String color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 22,
      height: 22,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: _parseColor(color),
        border: Border.all(color: Colors.white.withValues(alpha: 0.35)),
      ),
    );
  }
}

InputDecoration _gtexInputDecoration({
  required String label,
  required IconData icon,
  String? hint,
}) {
  final OutlineInputBorder border = OutlineInputBorder(
    borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
    borderSide: BorderSide(color: GtexColors.line.withValues(alpha: 0.9)),
  );
  return InputDecoration(
    labelText: label,
    hintText: hint,
    labelStyle: const TextStyle(color: GtexColors.textMuted),
    hintStyle: TextStyle(color: GtexColors.textMuted.withValues(alpha: 0.78)),
    prefixIcon: Icon(icon, color: GtexColors.gold),
    filled: true,
    fillColor: Colors.white.withValues(alpha: 0.045),
    border: border,
    enabledBorder: border,
    focusedBorder: border.copyWith(
      borderSide: const BorderSide(color: GtexColors.gold),
    ),
  );
}

class _ClubPalette {
  const _ClubPalette({
    required this.name,
    required this.primary,
    required this.secondary,
    required this.accent,
  });

  final String name;
  final String primary;
  final String secondary;
  final String accent;
}

const List<_ClubPalette> _clubPalettes = <_ClubPalette>[
  _ClubPalette(
    name: 'Atlantic Gold',
    primary: '#0A2647',
    secondary: '#F5F7FA',
    accent: '#F5B700',
  ),
  _ClubPalette(
    name: 'Forest Charge',
    primary: '#113A2D',
    secondary: '#EAF4F4',
    accent: '#2DD881',
  ),
  _ClubPalette(
    name: 'Crimson Tide',
    primary: '#501B2D',
    secondary: '#F8F0F2',
    accent: '#FF7B54',
  ),
  _ClubPalette(
    name: 'Metro Ice',
    primary: '#102542',
    secondary: '#D7E3FC',
    accent: '#5BC0EB',
  ),
];

String _slugify(String value) {
  return value
      .trim()
      .toLowerCase()
      .replaceAll(RegExp(r'[^a-z0-9]+'), '-')
      .replaceAll(RegExp(r'-+'), '-')
      .replaceAll(RegExp(r'^-+|-+$'), '');
}

String? _emptyToNull(String value) {
  final String trimmed = value.trim();
  return trimmed.isEmpty ? null : trimmed;
}

String _normalizedHex(String value) {
  final String trimmed = value.trim().toUpperCase();
  return trimmed.startsWith('#') ? trimmed : '#$trimmed';
}

bool _isHexColor(String value) {
  final String normalized = _normalizedHex(value);
  return RegExp(r'^#[0-9A-F]{6}$').hasMatch(normalized);
}

Color _parseColor(String value) {
  final String normalized = _normalizedHex(value).replaceFirst('#', '');
  return Color(int.parse('FF$normalized', radix: 16));
}
