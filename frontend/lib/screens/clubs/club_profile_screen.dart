import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_controller.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/club_identity/jerseys/widgets/identity_color_utils.dart';
import 'package:gte_frontend/models/club_models.dart';
import 'package:gte_frontend/screens/clubs/club_branding_screen.dart';
import 'package:gte_frontend/screens/clubs/club_dynasty_screen.dart';
import 'package:gte_frontend/screens/clubs/club_jersey_designer_screen.dart';
import 'package:gte_frontend/screens/clubs/club_reputation_screen.dart';
import 'package:gte_frontend/screens/clubs/club_showcase_screen.dart';
import 'package:gte_frontend/screens/clubs/club_trophy_cabinet_screen.dart';
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
    this.backendMode = GteBackendMode.live,
    this.accessToken,
    this.isAuthenticated = true,
    this.onOpenLogin,
  });

  final String clubId;
  final String? clubName;
  final ClubController? controller;
  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
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
    _controller =
        widget.controller ??
        ClubController.standard(
          clubId: widget.clubId,
          clubName: widget.clubName,
          baseUrl: widget.baseUrl,
          backendMode: widget.backendMode,
          accessToken: widget.accessToken,
        );
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _controller.ensureLoaded();
    });
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
        final ClubDashboardData? data = _controller.data;
        return Container(
          decoration: gteBackdropDecoration(),
          child: Scaffold(
            backgroundColor: Colors.transparent,
            appBar: AppBar(
              title: const Text('Club profile'),
              actions: <Widget>[
                IconButton(
                  onPressed: _controller.isLoading ? null : _controller.refresh,
                  icon: const Icon(Icons.refresh_outlined),
                ),
              ],
            ),
            body: data == null
                ? _buildLoadingState(context)
                : RefreshIndicator(
                    onRefresh: _controller.refresh,
                    child: ListView(
                      physics: const AlwaysScrollableScrollPhysics(),
                      padding: const EdgeInsets.fromLTRB(20, 12, 20, 28),
                      children: <Widget>[
                        _ProfileHero(controller: _controller, data: data),
                        const SizedBox(height: 18),
                        _ActionGrid(
                          onOpenShowcase: () => _open(context, ClubShowcaseScreen(controller: _controller)),
                          onOpenJerseys: () => _open(context, ClubJerseyDesignerScreen(controller: _controller)),
                          onOpenTrophies: () => _open(context, ClubTrophyCabinetScreen(controller: _controller)),
                          onOpenBranding: () => _open(context, ClubBrandingScreen(controller: _controller)),
                          onOpenReputation: () => _open(context, ClubReputationScreen(controller: _controller)),
                          onOpenDynasty: () => _open(context, ClubDynastyScreen(controller: _controller)),
                        ),
                        const SizedBox(height: 18),
                        Wrap(
                          spacing: 14,
                          runSpacing: 14,
                          children: <Widget>[
                            _MetricCard(
                              title: 'Trophies',
                              value: '${data.trophyCabinet.totalHonorsCount}',
                              caption:
                                  '${data.trophyCabinet.majorHonorsCount} major, ${data.trophyCabinet.eliteHonorsCount} elite',
                            ),
                            _MetricCard(
                              title: 'Prestige',
                              value: '${data.reputation.profile.currentScore}',
                              caption:
                                  'Global rank ${data.reputation.globalRank?.rank ?? 'N/A'}',
                            ),
                            _MetricCard(
                              title: 'Dynasty',
                              value: '${data.dynastyProfile.dynastyScore}',
                              caption:
                                  '${data.dynastyProfile.dynastyStatus.name} • ${data.dynastyProfile.currentEraLabel.name}',
                            ),
                            _MetricCard(
                              title: 'Showcase',
                              value: '${data.equippedCatalogCount}',
                              caption: 'Equipped cosmetics',
                            ),
                          ],
                        ),
                        const SizedBox(height: 18),
                        _SectionPanel(
                          title: 'Identity',
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Text(
                                '${data.identity.clubName} (${data.identity.shortClubCode})',
                                style: Theme.of(context).textTheme.titleLarge,
                              ),
                              const SizedBox(height: 8),
                              Text(
                                'Primary ${data.identity.colorPalette.primaryColor} • Secondary ${data.identity.colorPalette.secondaryColor} • Accent ${data.identity.colorPalette.accentColor}',
                              ),
                              const SizedBox(height: 12),
                              Wrap(
                                spacing: 10,
                                runSpacing: 10,
                                children: data.identity.jerseySet.all
                                    .map(
                                      (variant) => Chip(
                                        avatar: CircleAvatar(
                                          backgroundColor:
                                              identityColorFromHex(variant.primaryColor),
                                        ),
                                        label: Text(
                                          '${variant.label}: ${variant.patternType.name}',
                                        ),
                                      ),
                                    )
                                    .toList(growable: false),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 18),
                        _SectionPanel(
                          title: 'Latest legacy',
                          child: data.trophyCabinet.recentHonors.isEmpty
                              ? const Text('No official honors recorded yet.')
                              : Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: data.trophyCabinet.recentHonors
                                      .take(3)
                                      .map(
                                        (trophy) => Padding(
                                          padding: const EdgeInsets.only(bottom: 10),
                                          child: Text(
                                            '${trophy.trophyName} • ${trophy.seasonLabel} • ${trophy.finalResultSummary}',
                                          ),
                                        ),
                                      )
                                      .toList(growable: false),
                                ),
                        ),
                      ],
                    ),
                  ),
          ),
        );
      },
    );
  }

  Widget _buildLoadingState(BuildContext context) {
    if (_controller.isLoading) {
      return const Padding(
        padding: EdgeInsets.all(20),
        child: GteStatePanel(
          title: 'Loading club profile',
          message: 'Fetching the live club identity, trophy, and reputation surfaces.',
          icon: Icons.shield_outlined,
        ),
      );
    }
    return Padding(
      padding: const EdgeInsets.all(20),
      child: GteStatePanel(
        title: 'Club profile unavailable',
        message:
            _controller.errorMessage ??
            'The club profile could not be loaded from the live backend.',
        icon: Icons.shield_outlined,
        actionLabel:
            !widget.isAuthenticated && widget.onOpenLogin != null ? 'Sign in' : null,
        onAction: !widget.isAuthenticated ? widget.onOpenLogin : null,
      ),
    );
  }

  Future<void> _open(BuildContext context, Widget screen) {
    return Navigator.of(context).push(
      MaterialPageRoute<void>(builder: (BuildContext context) => screen),
    );
  }
}

class _ProfileHero extends StatelessWidget {
  const _ProfileHero({
    required this.controller,
    required this.data,
  });

  final ClubController controller;
  final ClubDashboardData data;

  @override
  Widget build(BuildContext context) {
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
            colors: <Color>[
              identityColorFromHex(data.identity.colorPalette.primaryColor),
              identityColorFromHex(data.identity.colorPalette.secondaryColor),
            ],
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(data.clubName, style: Theme.of(context).textTheme.displaySmall),
            const SizedBox(height: 8),
            Text(
              data.branding.motto,
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                    color: GteShellTheme.textPrimary.withValues(alpha: 0.85),
                  ),
            ),
            const SizedBox(height: 12),
            Text(
              '${data.countryName ?? 'Region unset'} • ${data.playerCount ?? 0} registered players',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            if (controller.noticeMessage != null) ...<Widget>[
              const SizedBox(height: 12),
              Text(controller.noticeMessage!, style: Theme.of(context).textTheme.bodyMedium),
            ],
          ],
        ),
      ),
    );
  }
}

class _ActionGrid extends StatelessWidget {
  const _ActionGrid({
    required this.onOpenShowcase,
    required this.onOpenJerseys,
    required this.onOpenTrophies,
    required this.onOpenBranding,
    required this.onOpenReputation,
    required this.onOpenDynasty,
  });

  final VoidCallback onOpenShowcase;
  final VoidCallback onOpenJerseys;
  final VoidCallback onOpenTrophies;
  final VoidCallback onOpenBranding;
  final VoidCallback onOpenReputation;
  final VoidCallback onOpenDynasty;

  @override
  Widget build(BuildContext context) {
    final List<({IconData icon, String title, VoidCallback onPressed})> actions =
        <({IconData icon, String title, VoidCallback onPressed})>[
      (icon: Icons.slideshow_outlined, title: 'Showcase', onPressed: onOpenShowcase),
      (icon: Icons.checkroom_outlined, title: 'Jerseys', onPressed: onOpenJerseys),
      (icon: Icons.emoji_events_outlined, title: 'Trophies', onPressed: onOpenTrophies),
      (icon: Icons.auto_awesome_outlined, title: 'Branding', onPressed: onOpenBranding),
      (icon: Icons.workspace_premium_outlined, title: 'Reputation', onPressed: onOpenReputation),
      (icon: Icons.timeline_outlined, title: 'Dynasty', onPressed: onOpenDynasty),
    ];
    return Wrap(
      spacing: 12,
      runSpacing: 12,
      children: actions
          .map(
            (action) => FilledButton.tonalIcon(
              onPressed: action.onPressed,
              icon: Icon(action.icon),
              label: Text(action.title),
            ),
          )
          .toList(growable: false),
    );
  }
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({
    required this.title,
    required this.value,
    required this.caption,
  });

  final String title;
  final String value;
  final String caption;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 220,
      child: GteSurfacePanel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(title, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Text(value, style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 6),
            Text(caption, style: Theme.of(context).textTheme.bodyMedium),
          ],
        ),
      ),
    );
  }
}

class _SectionPanel extends StatelessWidget {
  const _SectionPanel({
    required this.title,
    required this.child,
  });

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 12),
          child,
        ],
      ),
    );
  }
}
