import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_controller.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/club_identity/dynasty/presentation/club_dynasty_overview_screen.dart';
import 'package:gte_frontend/models/club_models.dart';
import 'package:gte_frontend/screens/clubs/club_branding_screen.dart';
import 'package:gte_frontend/screens/clubs/club_catalog_screen.dart';
import 'package:gte_frontend/screens/clubs/club_purchase_history_screen.dart';
import 'package:gte_frontend/screens/clubs/club_reputation_screen.dart';
import 'package:gte_frontend/screens/clubs/club_showcase_screen.dart';
import 'package:gte_frontend/screens/clubs/club_trophy_cabinet_screen.dart';
import 'package:gte_frontend/widgets/clubs/club_header_card.dart';
import 'package:gte_frontend/widgets/clubs/featured_trophy_card.dart';
import 'package:gte_frontend/widgets/clubs/reputation_progress_card.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class ClubProfileScreen extends StatefulWidget {
  const ClubProfileScreen({
    super.key,
    required this.clubId,
    this.clubName,
    this.controller,
    this.baseUrl = 'http://127.0.0.1:8000',
    this.backendMode = GteBackendMode.liveThenFixture,
    this.isAuthenticated = true,
    this.onOpenLogin,
  });

  final String clubId;
  final String? clubName;
  final ClubController? controller;
  final String baseUrl;
  final GteBackendMode backendMode;
  final bool isAuthenticated;
  final VoidCallback? onOpenLogin;

  @override
  State<ClubProfileScreen> createState() => _ClubProfileScreenState();
}

class _ClubProfileScreenState extends State<ClubProfileScreen> {
  late final ClubController _controller;
  late final bool _ownsController;

  @override
  void initState() {
    super.initState();
    _ownsController = widget.controller == null;
    _controller = widget.controller ??
        ClubController.standard(
          clubId: widget.clubId,
          clubName: widget.clubName,
          baseUrl: widget.baseUrl,
          backendMode: widget.backendMode,
        );
    _controller.ensureLoaded();
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
        if (_controller.isLoading && !_controller.hasData) {
          return const _LoadingView();
        }
        if (_controller.errorMessage != null && !_controller.hasData) {
          return Padding(
            padding: const EdgeInsets.all(20),
            child: GteStatePanel(
              title: 'Club identity unavailable',
              message: _controller.errorMessage!,
              actionLabel: 'Retry',
              onAction: _controller.load,
              icon: Icons.shield_outlined,
            ),
          );
        }

        final ClubDashboardData data = _controller.data!;
        return RefreshIndicator(
          onRefresh: _controller.refresh,
          child: SingleChildScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                GteSurfacePanel(
                  emphasized: true,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Club identity',
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Manage club reputation, trophy cabinet, dynasty progression, jersey design, and cosmetic catalog surfaces from one place.',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ],
                  ),
                ),
                if (!widget.isAuthenticated &&
                    widget.onOpenLogin != null) ...<Widget>[
                  const SizedBox(height: 18),
                  GteSurfacePanel(
                    child: Row(
                      children: <Widget>[
                        const Icon(Icons.lock_outline),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            'Sign in to save club identity updates to the live profile. Preview data remains available while signed out.',
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                        ),
                        const SizedBox(width: 12),
                        FilledButton.tonal(
                          onPressed: widget.onOpenLogin,
                          child: const Text('Sign in'),
                        ),
                      ],
                    ),
                  ),
                ],
                if (_controller.noticeMessage != null) ...<Widget>[
                  const SizedBox(height: 18),
                  _InlineNotice(message: _controller.noticeMessage!),
                ],
                const SizedBox(height: 18),
                ClubHeaderCard(data: data),
                const SizedBox(height: 18),
                _ActionGrid(
                  controller: _controller,
                  clubId: widget.clubId,
                  baseUrl: widget.baseUrl,
                  backendMode: widget.backendMode,
                ),
                const SizedBox(height: 18),
                ReputationProgressCard(reputation: data.reputation),
                const SizedBox(height: 18),
                if (data.trophyCabinet.featuredHonors().isNotEmpty)
                  FeaturedTrophyCard(
                    trophy: data.trophyCabinet.featuredHonors().first,
                    onTap: () => _openTrophies(context),
                  ),
                const SizedBox(height: 18),
                Text(
                  'Showcase panels',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: 12),
                Wrap(
                  spacing: 14,
                  runSpacing: 14,
                  children: data.showcasePanels.map((ClubShowcasePanel panel) {
                    return SizedBox(
                      width: 240,
                      child: GteSurfacePanel(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Text(
                              panel.title,
                              style: Theme.of(context).textTheme.titleLarge,
                            ),
                            const SizedBox(height: 8),
                            Text(
                              panel.value,
                              style: Theme.of(context).textTheme.headlineSmall,
                            ),
                            const SizedBox(height: 8),
                            Text(
                              panel.caption,
                              style: Theme.of(context).textTheme.bodyMedium,
                            ),
                          ],
                        ),
                      ),
                    );
                  }).toList(growable: false),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Future<void> _openReputation(BuildContext context) {
    return Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) =>
            ClubReputationScreen(controller: _controller),
      ),
    );
  }

  Future<void> _openTrophies(BuildContext context) {
    return Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) =>
            ClubTrophyCabinetScreen(controller: _controller),
      ),
    );
  }

  Future<void> _openIdentity(BuildContext context) {
    return Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) =>
            ClubBrandingScreen(controller: _controller),
      ),
    );
  }
}

class _ActionGrid extends StatelessWidget {
  const _ActionGrid({
    required this.controller,
    required this.clubId,
    required this.baseUrl,
    required this.backendMode,
  });

  final ClubController controller;
  final String clubId;
  final String baseUrl;
  final GteBackendMode backendMode;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 12,
      runSpacing: 12,
      children: <Widget>[
        FilledButton.tonalIcon(
          onPressed: () => Navigator.of(context).push<void>(
            MaterialPageRoute<void>(
              builder: (BuildContext context) =>
                  ClubReputationScreen(controller: controller),
            ),
          ),
          icon: const Icon(Icons.stars_outlined),
          label: const Text('Open reputation'),
        ),
        FilledButton.tonalIcon(
          onPressed: () => Navigator.of(context).push<void>(
            MaterialPageRoute<void>(
              builder: (BuildContext context) =>
                  ClubTrophyCabinetScreen(controller: controller),
            ),
          ),
          icon: const Icon(Icons.emoji_events_outlined),
          label: const Text('Open trophies'),
        ),
        FilledButton.tonalIcon(
          onPressed: () => Navigator.of(context).push<void>(
            MaterialPageRoute<void>(
              builder: (BuildContext context) =>
                  ClubBrandingScreen(controller: controller),
            ),
          ),
          icon: const Icon(Icons.shield_outlined),
          label: const Text('Open identity'),
        ),
        FilledButton.tonalIcon(
          onPressed: () => Navigator.of(context).push<void>(
            MaterialPageRoute<void>(
              builder: (BuildContext context) => ClubDynastyOverviewScreen(
                clubId: clubId,
                baseUrl: baseUrl,
                backendMode: backendMode,
              ),
            ),
          ),
          icon: const Icon(Icons.timeline_outlined),
          label: const Text('Open dynasty'),
        ),
        FilledButton.tonalIcon(
          onPressed: () => Navigator.of(context).push<void>(
            MaterialPageRoute<void>(
              builder: (BuildContext context) =>
                  ClubShowcaseScreen(controller: controller),
            ),
          ),
          icon: const Icon(Icons.slideshow_outlined),
          label: const Text('Open showcase'),
        ),
        FilledButton.tonalIcon(
          onPressed: () => Navigator.of(context).push<void>(
            MaterialPageRoute<void>(
              builder: (BuildContext context) =>
                  ClubCatalogScreen(controller: controller),
            ),
          ),
          icon: const Icon(Icons.storefront_outlined),
          label: const Text('Open catalog'),
        ),
        FilledButton.tonalIcon(
          onPressed: () => Navigator.of(context).push<void>(
            MaterialPageRoute<void>(
              builder: (BuildContext context) =>
                  ClubPurchaseHistoryScreen(controller: controller),
            ),
          ),
          icon: const Icon(Icons.receipt_long_outlined),
          label: const Text('Purchase history'),
        ),
      ],
    );
  }
}

class _InlineNotice extends StatelessWidget {
  const _InlineNotice({
    required this.message,
  });

  final String message;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        color: GteShellTheme.accent.withValues(alpha: 0.12),
        border: Border.all(color: GteShellTheme.accent.withValues(alpha: 0.28)),
      ),
      child: Row(
        children: <Widget>[
          const Icon(Icons.check_circle_outline, color: GteShellTheme.accent),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              message,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ),
        ],
      ),
    );
  }
}

class _LoadingView extends StatelessWidget {
  const _LoadingView();

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
      children: const <Widget>[
        GteSurfacePanel(child: SizedBox(height: 90)),
        SizedBox(height: 18),
        GteSurfacePanel(child: SizedBox(height: 220)),
        SizedBox(height: 18),
        GteSurfacePanel(child: SizedBox(height: 160)),
      ],
    );
  }
}
