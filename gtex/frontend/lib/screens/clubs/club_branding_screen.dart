import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_controller.dart';
import 'package:gte_frontend/features/club_identity/jerseys/widgets/identity_color_utils.dart';
import 'package:gte_frontend/screens/clubs/club_jersey_designer_screen.dart';
import 'package:gte_frontend/screens/clubs/club_showcase_screen.dart';
import 'package:gte_frontend/widgets/clubs/branding_theme_card.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class ClubBrandingScreen extends StatefulWidget {
  const ClubBrandingScreen({
    super.key,
    required this.controller,
  });

  final ClubController controller;

  @override
  State<ClubBrandingScreen> createState() => _ClubBrandingScreenState();
}

class _ClubBrandingScreenState extends State<ClubBrandingScreen> {
  late final TextEditingController _mottoController;
  late final FocusNode _mottoFocusNode;

  @override
  void initState() {
    super.initState();
    _mottoController = TextEditingController();
    _mottoFocusNode = FocusNode();
    widget.controller.addListener(_syncMotto);
    _syncMotto();
  }

  @override
  void dispose() {
    widget.controller.removeListener(_syncMotto);
    _mottoController.dispose();
    _mottoFocusNode.dispose();
    super.dispose();
  }

  void _syncMotto() {
    final branding = widget.controller.branding;
    if (branding == null || _mottoFocusNode.hasFocus) {
      return;
    }
    if (_mottoController.text != branding.motto) {
      _mottoController.text = branding.motto;
    }
  }

  @override
  Widget build(BuildContext context) {
    final controller = widget.controller;
    return AnimatedBuilder(
      animation: controller,
      builder: (BuildContext context, _) {
        final branding = controller.branding;
        return Container(
          decoration: gteBackdropDecoration(),
          child: Scaffold(
            backgroundColor: Colors.transparent,
            appBar: AppBar(
              title: const Text('Club Identity'),
            ),
            body: branding == null
                ? Padding(
                    padding: const EdgeInsets.all(20),
                    child: GteStatePanel(
                      title: 'Club identity unavailable',
                      message: controller.errorMessage ??
                          'Load the club profile before opening this screen.',
                      icon: Icons.shield_outlined,
                    ),
                  )
                : ListView(
                    padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
                    children: <Widget>[
                      if (controller.noticeMessage != null) ...<Widget>[
                        GteSurfacePanel(
                          child: Text(
                            controller.noticeMessage!,
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                        ),
                        const SizedBox(height: 18),
                      ],
                      Row(
                        children: <Widget>[
                          Expanded(
                            child: Text(
                              'Branding themes',
                              style: Theme.of(context).textTheme.headlineSmall,
                            ),
                          ),
                          FilledButton.tonalIcon(
                            onPressed: () => Navigator.of(context).push<void>(
                              MaterialPageRoute<void>(
                                builder: (BuildContext context) =>
                                    ClubJerseyDesignerScreen(controller: controller),
                              ),
                            ),
                            icon: const Icon(Icons.checkroom_outlined),
                            label: const Text('Jersey design'),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 14,
                        runSpacing: 14,
                        children: branding.availableThemes.map((theme) {
                          return SizedBox(
                            width: 280,
                            child: BrandingThemeCard(
                              title: theme.name,
                              description: theme.description,
                              previewColors: <String>[
                                theme.primaryColor,
                                theme.secondaryColor,
                                theme.accentColor,
                              ],
                              selected: theme.id == branding.selectedThemeId,
                              tagLabel: theme.bannerLabel,
                              onTap: () => controller.updateBrandingTheme(theme.id),
                            ),
                          );
                        }).toList(growable: false),
                      ),
                      const SizedBox(height: 20),
                      Text(
                        'Showcase backdrops',
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 14,
                        runSpacing: 14,
                        children: branding.availableBackdrops.map((backdrop) {
                          return SizedBox(
                            width: 280,
                            child: BrandingThemeCard(
                              title: backdrop.name,
                              description: backdrop.description,
                              previewColors: backdrop.gradientColors,
                              selected: backdrop.id == branding.selectedBackdropId,
                              tagLabel: backdrop.caption,
                              onTap: () => controller.updateBackdrop(backdrop.id),
                            ),
                          );
                        }).toList(growable: false),
                      ),
                      const SizedBox(height: 20),
                      GteSurfacePanel(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Text(
                              'Club motto',
                              style: Theme.of(context).textTheme.titleLarge,
                            ),
                            const SizedBox(height: 10),
                            TextField(
                              controller: _mottoController,
                              focusNode: _mottoFocusNode,
                              onChanged: controller.updateMotto,
                              maxLength: 60,
                              decoration: const InputDecoration(
                                hintText: 'Write a short club legacy line',
                              ),
                            ),
                            const SizedBox(height: 10),
                            Text(
                              branding.reviewNote,
                              style: Theme.of(context).textTheme.bodyMedium,
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 20),
                      _BrandingPreview(branding: branding),
                      const SizedBox(height: 20),
                      Wrap(
                        spacing: 12,
                        runSpacing: 12,
                        children: <Widget>[
                          FilledButton.icon(
                            onPressed:
                                controller.isSavingBranding ? null : controller.saveBranding,
                            icon: controller.isSavingBranding
                                ? const SizedBox(
                                    width: 16,
                                    height: 16,
                                    child: CircularProgressIndicator(strokeWidth: 2),
                                  )
                                : const Icon(Icons.save_outlined),
                            label: const Text('Save branding'),
                          ),
                          OutlinedButton.icon(
                            onPressed: () => Navigator.of(context).push<void>(
                              MaterialPageRoute<void>(
                                builder: (BuildContext context) =>
                                    ClubShowcaseScreen(controller: controller),
                              ),
                            ),
                            icon: const Icon(Icons.slideshow_outlined),
                            label: const Text('Open showcase'),
                          ),
                        ],
                      ),
                    ],
                  ),
          ),
        );
      },
    );
  }
}

class _BrandingPreview extends StatelessWidget {
  const _BrandingPreview({
    required this.branding,
  });

  final dynamic branding;

  @override
  Widget build(BuildContext context) {
    final theme = branding.selectedTheme;
    final backdrop = branding.selectedBackdrop;
    return GteSurfacePanel(
      emphasized: true,
      padding: EdgeInsets.zero,
      child: Container(
        padding: const EdgeInsets.all(22),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(28),
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: backdrop.gradientColors
                .map(identityColorFromHex)
                .toList(growable: false),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              theme.name,
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text(
              branding.motto,
              style: Theme.of(context).textTheme.bodyLarge,
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 10,
              children: <Widget>[
                _Swatch(colorHex: theme.primaryColor),
                _Swatch(colorHex: theme.secondaryColor),
                _Swatch(colorHex: theme.accentColor),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _Swatch extends StatelessWidget {
  const _Swatch({
    required this.colorHex,
  });

  final String colorHex;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 24,
      height: 24,
      decoration: BoxDecoration(
        color: identityColorFromHex(colorHex),
        shape: BoxShape.circle,
      ),
    );
  }
}
