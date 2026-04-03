import 'package:flutter/material.dart';

import '../../core/app_feedback.dart';
import '../../data/club_creation_api.dart';
import '../../data/gte_api_repository.dart';
import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';

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
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(title: const Text('Create your club')),
        body: ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
          children: <Widget>[
            GteSurfacePanel(
              emphasized: true,
              accentColor: GteShellTheme.accentClub,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'Launch a real club workspace',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Name the club, choose its public palette, and create the ownership workspace that unlocks club identity, competitions, scouting, and commercial surfaces.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 16),
                  Wrap(
                    spacing: 10,
                    runSpacing: 10,
                    children: const <Widget>[
                      Chip(label: Text('Live club creation')),
                      Chip(label: Text('Owner workspace')),
                      Chip(label: Text('Club routes unlock immediately')),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
            GteSurfacePanel(
              accentColor: GteShellTheme.accentClub,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'Club basics',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 14),
                  TextField(
                    controller: _clubNameController,
                    decoration: const InputDecoration(
                      labelText: 'Club name',
                      hintText: 'Lagos Comets FC',
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _shortNameController,
                    decoration: const InputDecoration(
                      labelText: 'Short name',
                      hintText: 'Comets',
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _slugController,
                    decoration: const InputDecoration(
                      labelText: 'Slug',
                      hintText: 'lagos-comets-fc',
                    ),
                  ),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    value: _visibility,
                    decoration: const InputDecoration(labelText: 'Visibility'),
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
            ),
            const SizedBox(height: 18),
            GteSurfacePanel(
              accentColor: GteShellTheme.accentWarm,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'Identity palette',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Choose a launch palette, then fine-tune the exact hex values if needed.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 16),
                  Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    children: _clubPalettes
                        .map((_ClubPalette palette) {
                          final bool selected = identical(
                            palette,
                            _selectedPalette,
                          );
                          return InkWell(
                            borderRadius: BorderRadius.circular(18),
                            onTap: () {
                              setState(() {
                                _applyPalette(palette);
                              });
                            },
                            child: Container(
                              width: 170,
                              padding: const EdgeInsets.all(14),
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(18),
                                border: Border.all(
                                  color:
                                      selected
                                          ? GteShellTheme.accentWarm
                                          : GteShellTheme.stroke,
                                ),
                                color: Colors.white.withValues(alpha: 0.03),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: <Widget>[
                                  Text(
                                    palette.name,
                                    style:
                                        Theme.of(context).textTheme.titleMedium,
                                  ),
                                  const SizedBox(height: 10),
                                  Row(
                                    children: <Widget>[
                                      _ColorDot(color: palette.primary),
                                      const SizedBox(width: 8),
                                      _ColorDot(color: palette.secondary),
                                      const SizedBox(width: 8),
                                      _ColorDot(color: palette.accent),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                          );
                        })
                        .toList(growable: false),
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: _primaryColorController,
                    decoration: const InputDecoration(
                      labelText: 'Primary color',
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _secondaryColorController,
                    decoration: const InputDecoration(
                      labelText: 'Secondary color',
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _accentColorController,
                    decoration: const InputDecoration(
                      labelText: 'Accent color',
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
            GteSurfacePanel(
              accentColor: GteShellTheme.accentCapital,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'Club location',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 14),
                  TextField(
                    controller: _venueController,
                    decoration: const InputDecoration(
                      labelText: 'Home venue',
                      hintText: 'Marina Arena',
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _countryCodeController,
                    decoration: const InputDecoration(
                      labelText: 'Country code',
                      hintText: 'NG',
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _regionController,
                    decoration: const InputDecoration(labelText: 'Region'),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _cityController,
                    decoration: const InputDecoration(labelText: 'City'),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _descriptionController,
                    maxLines: 4,
                    decoration: const InputDecoration(
                      labelText: 'Description',
                      hintText:
                          'Describe the club identity, fan culture, and sporting ambition.',
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
            GteStatePanel(
              eyebrow: 'READY TO LAUNCH',
              title: 'Create the club and unlock the full club lane',
              message:
                  'As soon as the club is created, this account will switch into its club workspace so identity, prestige, trophy, replay, and creator commerce routes open without another sign-in.',
              icon: Icons.rocket_launch_outlined,
              accentColor: GteShellTheme.accentClub,
              actionLabel: _submitting ? 'Creating...' : 'Create club',
              onAction: _submitting ? null : _submit,
            ),
          ],
        ),
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
