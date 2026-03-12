import 'package:flutter/material.dart';

import '../../../../widgets/gte_shell_theme.dart';
import '../../../../widgets/gte_state_panel.dart';
import '../../../../widgets/gte_surface_panel.dart';
import '../data/club_identity_repository.dart';
import '../widgets/badge_preview_widget.dart';
import '../widgets/clash_warning_banner.dart';
import '../widgets/club_code_chip.dart';
import '../widgets/identity_color_utils.dart';
import '../widgets/jersey_preview_card.dart';
import 'badge_editor_screen.dart';
import 'club_identity_controller.dart';
import 'identity_preview_screen.dart';
import 'jersey_editor_screen.dart';

class ClubIdentityScreen extends StatefulWidget {
  const ClubIdentityScreen({
    super.key,
    required this.clubId,
    this.initialClubName,
    this.controller,
    this.repository,
  });

  final String clubId;
  final String? initialClubName;
  final ClubIdentityController? controller;
  final ClubIdentityRepository? repository;

  @override
  State<ClubIdentityScreen> createState() => _ClubIdentityScreenState();
}

class _ClubIdentityScreenState extends State<ClubIdentityScreen> {
  late final ClubIdentityController _controller;
  late final bool _ownsController;

  @override
  void initState() {
    super.initState();
    _ownsController = widget.controller == null;
    _controller = widget.controller ??
        ClubIdentityController(
          clubId: widget.clubId,
          initialClubName: widget.initialClubName,
          repository: widget.repository ?? MockClubIdentityRepository(),
        );
    _controller.load();
  }

  @override
  void dispose() {
    if (_ownsController) {
      _controller.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (BuildContext context, _) {
        final identity = _controller.identity;
        return Scaffold(
          appBar: AppBar(
            title: const Text('Club Identity'),
            actions: <Widget>[
              if (_controller.hasUnsavedChanges)
                const Padding(
                  padding: EdgeInsets.only(right: 12),
                  child: Center(
                    child: Icon(Icons.circle,
                        size: 10, color: GteShellTheme.accentWarm),
                  ),
                ),
            ],
          ),
          body: Container(
            decoration: gteBackdropDecoration(),
            child: SafeArea(
              top: false,
              child: _controller.isLoading && identity == null
                  ? const Center(child: CircularProgressIndicator())
                  : identity == null
                      ? Padding(
                          padding: const EdgeInsets.all(20),
                          child: GteStatePanel(
                            title: 'Identity unavailable',
                            message: _controller.errorMessage ??
                                'The club identity profile could not be loaded.',
                            actionLabel: 'Retry',
                            onAction: _controller.load,
                            icon: Icons.shield_outlined,
                          ),
                        )
                      : RefreshIndicator(
                          onRefresh: _controller.reload,
                          child: SingleChildScrollView(
                            physics: const AlwaysScrollableScrollPhysics(),
                            padding: const EdgeInsets.fromLTRB(20, 12, 20, 40),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: <Widget>[
                                _HeaderPanel(
                                  controller: _controller,
                                  onEditBadge: _openBadgeEditor,
                                ),
                                const SizedBox(height: 20),
                                if (_controller.successMessage !=
                                    null) ...<Widget>[
                                  _InlineStatus(
                                    icon: Icons.check_circle_outline,
                                    message: _controller.successMessage!,
                                    color: GteShellTheme.positive,
                                  ),
                                  const SizedBox(height: 16),
                                ],
                                if (_controller.hasUnsavedChanges) ...<Widget>[
                                  const ClashWarningBanner(
                                    title: 'Unsaved changes',
                                    warnings: <String>[
                                      'Preview updates are local until you save. Reloading this screen will restore the last saved profile.',
                                    ],
                                  ),
                                  const SizedBox(height: 16),
                                ],
                                ClashWarningBanner(
                                  warnings: _controller.warnings,
                                  title: 'Kit readability',
                                ),
                                const SizedBox(height: 20),
                                _ActionPanel(
                                  controller: _controller,
                                  onEditJerseys: _openJerseyEditor,
                                  onEditBadge: _openBadgeEditor,
                                  onOpenPreview: _openPreviewScreen,
                                ),
                                const SizedBox(height: 20),
                                Text(
                                  'Jersey set',
                                  style:
                                      Theme.of(context).textTheme.headlineSmall,
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  'Every club gets a home, away, third, and goalkeeper kit ready for standings, intros, replay cards, and future visual upgrades.',
                                  style: Theme.of(context).textTheme.bodyMedium,
                                ),
                                const SizedBox(height: 16),
                                LayoutBuilder(
                                  builder: (BuildContext context,
                                      BoxConstraints constraints) {
                                    final double width = constraints.maxWidth;
                                    final int columns = width > 1180
                                        ? 4
                                        : width > 860
                                            ? 2
                                            : 1;
                                    final double cardWidth = columns == 1
                                        ? width
                                        : (width - ((columns - 1) * 16)) /
                                            columns;
                                    return Wrap(
                                      spacing: 16,
                                      runSpacing: 16,
                                      children: identity.jerseySet.all
                                          .map(
                                            (variant) => SizedBox(
                                              width: cardWidth,
                                              child: JerseyPreviewCard(
                                                variant: variant,
                                                compact: columns > 1,
                                                onTap: _openJerseyEditor,
                                              ),
                                            ),
                                          )
                                          .toList(growable: false),
                                    );
                                  },
                                ),
                              ],
                            ),
                          ),
                        ),
            ),
          ),
        );
      },
    );
  }

  Future<void> _openJerseyEditor() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => JerseyEditorScreen(
          controller: _controller,
        ),
      ),
    );
  }

  Future<void> _openBadgeEditor() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => BadgeEditorScreen(
          controller: _controller,
        ),
      ),
    );
  }

  Future<void> _openPreviewScreen() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => IdentityPreviewScreen(
          controller: _controller,
        ),
      ),
    );
  }
}

class _HeaderPanel extends StatelessWidget {
  const _HeaderPanel({
    required this.controller,
    required this.onEditBadge,
  });

  final ClubIdentityController controller;
  final VoidCallback onEditBadge;

  @override
  Widget build(BuildContext context) {
    final identity = controller.identity!;
    return GteSurfacePanel(
      emphasized: true,
      child: LayoutBuilder(
        builder: (BuildContext context, BoxConstraints constraints) {
          final bool stacked = constraints.maxWidth < 780;
          final Widget content = Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                children: <Widget>[
                  Expanded(
                    child: Text(
                      identity.clubName,
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                  ),
                  ClubCodeChip(code: identity.shortClubCode),
                ],
              ),
              const SizedBox(height: 10),
              Text(
                'Build a distinctive badge and kit system that stays recognizable in fast football surfaces.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 18),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: <Widget>[
                  _PaletteSwatch(
                    label: 'Primary',
                    colorHex: identity.colorPalette.primaryColor,
                  ),
                  _PaletteSwatch(
                    label: 'Secondary',
                    colorHex: identity.colorPalette.secondaryColor,
                  ),
                  _PaletteSwatch(
                    label: 'Accent',
                    colorHex: identity.colorPalette.accentColor,
                  ),
                ],
              ),
              const SizedBox(height: 18),
              FilledButton.tonalIcon(
                onPressed: onEditBadge,
                icon: const Icon(Icons.shield_outlined),
                label: const Text('Refine badge'),
              ),
            ],
          );

          if (stacked) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                BadgePreviewWidget(badge: identity.badgeProfile, size: 132),
                const SizedBox(height: 20),
                content,
              ],
            );
          }

          return Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: <Widget>[
              BadgePreviewWidget(badge: identity.badgeProfile, size: 132),
              const SizedBox(width: 24),
              Expanded(child: content),
            ],
          );
        },
      ),
    );
  }
}

class _PaletteSwatch extends StatelessWidget {
  const _PaletteSwatch({
    required this.label,
    required this.colorHex,
  });

  final String label;
  final String colorHex;

  @override
  Widget build(BuildContext context) {
    final Color color = identityColorFromHex(colorHex);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: GteShellTheme.stroke),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Container(
            width: 14,
            height: 14,
            decoration: BoxDecoration(
              color: color,
              shape: BoxShape.circle,
              border: Border.all(color: Colors.white.withValues(alpha: 0.24)),
            ),
          ),
          const SizedBox(width: 8),
          Text(label, style: Theme.of(context).textTheme.bodyMedium),
        ],
      ),
    );
  }
}

class _ActionPanel extends StatelessWidget {
  const _ActionPanel({
    required this.controller,
    required this.onEditJerseys,
    required this.onEditBadge,
    required this.onOpenPreview,
  });

  final ClubIdentityController controller;
  final VoidCallback onEditJerseys;
  final VoidCallback onEditBadge;
  final VoidCallback onOpenPreview;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Wrap(
        spacing: 12,
        runSpacing: 12,
        children: <Widget>[
          FilledButton.tonalIcon(
            onPressed: onEditJerseys,
            icon: const Icon(Icons.checkroom_outlined),
            label: const Text('Edit jerseys'),
          ),
          FilledButton.tonalIcon(
            onPressed: onEditBadge,
            icon: const Icon(Icons.shield_outlined),
            label: const Text('Edit badge'),
          ),
          FilledButton.tonalIcon(
            onPressed: onOpenPreview,
            icon: const Icon(Icons.slideshow_outlined),
            label: const Text('Preview surfaces'),
          ),
          FilledButton.icon(
            onPressed: controller.isSaving ? null : controller.saveAll,
            icon: controller.isSaving
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.save_outlined),
            label: const Text('Save changes'),
          ),
          OutlinedButton.icon(
            onPressed: controller.isLoading ? null : controller.reload,
            icon: const Icon(Icons.refresh),
            label: const Text('Reload'),
          ),
        ],
      ),
    );
  }
}

class _InlineStatus extends StatelessWidget {
  const _InlineStatus({
    required this.icon,
    required this.message,
    required this.color,
  });

  final IconData icon;
  final String message;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withValues(alpha: 0.35)),
      ),
      child: Row(
        children: <Widget>[
          Icon(icon, color: color),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              message,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: GteShellTheme.textPrimary,
                  ),
            ),
          ),
        ],
      ),
    );
  }
}
