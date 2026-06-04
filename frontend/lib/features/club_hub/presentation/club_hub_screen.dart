import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_controller.dart';
import 'package:gte_frontend/controllers/club_ops_controller.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/app_routes/gte_navigation_helpers.dart';
import 'package:gte_frontend/features/app_routes/gte_route_data.dart';
import 'package:gte_frontend/features/club_hub/widgets/club_hub_components.dart';
import 'package:gte_frontend/features/club_hub/widgets/squad_readiness_panel.dart';
import 'package:gte_frontend/features/club_navigation/club_navigation.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/features/shell/shell.dart' as shell;
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';
import 'package:gte_frontend/widgets/gtex_branding.dart';

class ClubHubScreen extends StatefulWidget {
  const ClubHubScreen({
    super.key,
    required this.clubId,
    this.clubName,
    this.controller,
    this.baseUrl = 'http://127.0.0.1:8000',
    this.backendMode = GteBackendMode.live,
    this.isAuthenticated = true,
    this.onOpenLogin,
    this.initialTab = ClubNavigationTab.squad,
    this.navigationDependencies,
    this.operationsController,
  });

  final String clubId;
  final String? clubName;
  final ClubController? controller;
  final String baseUrl;
  final GteBackendMode backendMode;
  final bool isAuthenticated;
  final VoidCallback? onOpenLogin;
  final ClubNavigationTab initialTab;
  final GteNavigationDependencies? navigationDependencies;
  final ClubOpsController? operationsController;

  @override
  State<ClubHubScreen> createState() => _ClubHubScreenState();
}

class _ClubHubScreenState extends State<ClubHubScreen> {
  ClubOpsController? _ownedOperationsController;

  ClubOpsController? get _operationsController =>
      widget.operationsController ?? _ownedOperationsController;

  GteNavigationDependencies get _dependencies =>
      widget.navigationDependencies ??
      GteNavigationDependencies(
        apiBaseUrl: widget.baseUrl,
        backendMode: widget.backendMode,
        currentClubId: widget.clubId,
        currentClubName: widget.clubName,
        isAuthenticated: widget.isAuthenticated,
      );

  String get _resolvedClubName {
    final String? trimmed = widget.clubName?.trim();
    if (trimmed != null && trimmed.isNotEmpty) {
      return trimmed;
    }
    return widget.clubId
        .split('-')
        .where((String fragment) => fragment.isNotEmpty)
        .map(
          (String fragment) =>
              '${fragment[0].toUpperCase()}${fragment.substring(1)}',
        )
        .join(' ');
  }

  bool get _ownsWorkspace {
    final String? currentClubId = _dependencies.currentClubId?.trim();
    return currentClubId != null && currentClubId == widget.clubId;
  }

  @override
  void initState() {
    super.initState();
    _ensureOperationsController();
  }

  @override
  void didUpdateWidget(ClubHubScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.operationsController != widget.operationsController ||
        oldWidget.clubId != widget.clubId ||
        oldWidget.baseUrl != widget.baseUrl ||
        oldWidget.backendMode != widget.backendMode) {
      _disposeOwnedOperationsController();
      _ensureOperationsController();
    }
  }

  @override
  void dispose() {
    _disposeOwnedOperationsController();
    super.dispose();
  }

  void _ensureOperationsController() {
    if (!widget.isAuthenticated || widget.operationsController != null) {
      widget.operationsController?.loadClubData();
      return;
    }
    _ownedOperationsController = ClubOpsController(
      api:
          widget.backendMode == GteBackendMode.fixture
              ? ClubOpsApi.fixture(baseUrl: widget.baseUrl)
              : ClubOpsApi.standard(
                baseUrl: widget.baseUrl,
                mode: widget.backendMode,
              ),
      clubId: widget.clubId,
      clubName: widget.clubName,
    )..loadClubData();
  }

  void _disposeOwnedOperationsController() {
    _ownedOperationsController?.dispose();
    _ownedOperationsController = null;
  }

  Future<void> _openRoute(BuildContext context, GteAppRouteData route) {
    return GteNavigationHelpers.pushRoute<void>(
      context,
      route: route,
      dependencies: _dependencies,
    );
  }

  Widget _buildRouteButton({
    required VoidCallback? onPressed,
    required IconData icon,
    required String label,
    bool emphasized = false,
  }) {
    if (emphasized) {
      return FilledButton.icon(
        onPressed: onPressed,
        icon: Icon(icon),
        label: Text(label),
      );
    }
    return FilledButton.tonalIcon(
      onPressed: onPressed,
      icon: Icon(icon),
      label: Text(label),
    );
  }

  Widget _buildOperationsPanel() {
    final ClubOpsController? operationsController = _operationsController;
    final Widget panel = ClubHqOperationsPanel(
      data: widget.controller?.data,
      operationsController: operationsController,
      onRefresh: operationsController?.refreshClubData,
    );
    final ClubController? clubController = widget.controller;
    if (clubController == null) {
      return panel;
    }
    return AnimatedBuilder(
      animation: clubController,
      builder: (BuildContext context, Widget? child) {
        return ClubHqOperationsPanel(
          data: clubController.data,
          operationsController: operationsController,
          onRefresh: operationsController?.refreshClubData,
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.isAuthenticated) {
      return Container(
        decoration: gteBackdropDecoration(),
        child: Scaffold(
          backgroundColor: Colors.transparent,
          appBar: AppBar(title: const Text('Club command')),
          body: Padding(
            padding: const EdgeInsets.all(20),
            child: GteStatePanel(
              eyebrow: 'CLUB ACCESS',
              title: 'Sign in to open club routes',
              message:
                  'Club extensions need an authenticated session before world context, owner inbox, and club-scoped flows can open.',
              actionLabel: widget.onOpenLogin == null ? null : 'Sign in',
              onAction: widget.onOpenLogin,
              icon: Icons.login_outlined,
              accentColor: GteShellTheme.accentClub,
            ),
          ),
        ),
      );
    }

    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              const Text('Club command'),
              Text(
                _resolvedClubName,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
          ),
        ),
        body: ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
          children: <Widget>[
            GteSurfacePanel(
              emphasized: true,
              accentColor: GteShellTheme.accentClub,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      const GtexLogoMark(size: 36, compact: true),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Text(
                              _resolvedClubName,
                              style: Theme.of(context).textTheme.headlineSmall,
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'This is the power room for your club. Identity, trophies, ownership, world context, and media-facing routes stay together so the club feels like a real institution.',
                              style: Theme.of(context).textTheme.bodyMedium,
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  Wrap(
                    spacing: 10,
                    runSpacing: 10,
                    children: const <Widget>[
                      Chip(label: Text('Club power')),
                      Chip(label: Text('Owner control')),
                      Chip(label: Text('World context')),
                      Chip(label: Text('Broadcast-ready')),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
            _ClubCommandOperatingPanel(
              controller: widget.controller,
              isOwnerWorkspace: _ownsWorkspace,
              onOpenLogin: widget.onOpenLogin,
            ),
            const SizedBox(height: 18),
            _ClubCommandSquadReadinessSection(
              controller: widget.controller,
              fallbackClubName: _resolvedClubName,
            ),
            const SizedBox(height: 18),
            _buildOperationsPanel(),
            const SizedBox(height: 18),
            GteSurfacePanel(
              accentColor: GteShellTheme.accentClub,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'Club command',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Open the routes that shape how the club looks, competes, and gets remembered.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 16),
                  Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    children: <Widget>[
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              const CompetitionCreateRouteData(),
                            ),
                        icon: Icons.add_circle_outline,
                        label: 'Create competition',
                        emphasized: true,
                      ),
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              ClubIdentityJerseysRouteData(
                                clubId: widget.clubId,
                                clubName: _resolvedClubName,
                              ),
                            ),
                        icon: Icons.shield_outlined,
                        label: 'Club identity',
                      ),
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              ClubReputationOverviewRouteData(
                                clubId: widget.clubId,
                                clubName: _resolvedClubName,
                              ),
                            ),
                        icon: Icons.workspace_premium_outlined,
                        label: 'Reputation',
                      ),
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              ClubTrophyCabinetRouteData(
                                clubId: widget.clubId,
                                clubName: _resolvedClubName,
                              ),
                            ),
                        icon: Icons.emoji_events_outlined,
                        label: 'Trophy cabinet',
                      ),
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              ClubDynastyOverviewRouteData(
                                clubId: widget.clubId,
                                clubName: _resolvedClubName,
                              ),
                            ),
                        icon: Icons.auto_graph_outlined,
                        label: 'Dynasty',
                      ),
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              ClubAiAssistantRouteData(
                                clubId: widget.clubId,
                                clubName: _resolvedClubName,
                              ),
                            ),
                        icon: Icons.smart_toy_outlined,
                        label: 'AI assistant',
                      ),
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              ClubReplaysRouteData(
                                clubId: widget.clubId,
                                clubName: _resolvedClubName,
                              ),
                            ),
                        icon: Icons.play_circle_outline,
                        label: 'Replay archive',
                      ),
                    ],
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
                    'Ownership and commerce',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Move from ownership into sale-market, creator-stadium, and creator-share-market flows without leaving the club workspace.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 16),
                  Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    children: <Widget>[
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              CreatorShareMarketClubRouteData(
                                clubId: widget.clubId,
                                clubName: _resolvedClubName,
                              ),
                            ),
                        icon: Icons.insights_outlined,
                        label: 'Creator share market',
                        emphasized: true,
                      ),
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              CreatorStadiumClubRouteData(
                                clubId: widget.clubId,
                                clubName: _resolvedClubName,
                              ),
                            ),
                        icon: Icons.theaters_outlined,
                        label: 'Creator stadium',
                      ),
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              ClubSaleMarketDetailRouteData(
                                clubId: widget.clubId,
                                clubName: _resolvedClubName,
                              ),
                            ),
                        icon: Icons.sell_outlined,
                        label: 'Sell this club',
                      ),
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              const ClubSaleMarketListingsRouteData(),
                            ),
                        icon: Icons.storefront_outlined,
                        label: 'Browse club market',
                      ),
                      _buildRouteButton(
                        onPressed:
                            _ownsWorkspace
                                ? () => _openRoute(
                                  context,
                                  ClubSaleMarketOwnerOffersRouteData(
                                    clubId: widget.clubId,
                                    clubName: _resolvedClubName,
                                  ),
                                )
                                : null,
                        icon: Icons.inbox_outlined,
                        label: 'Owner offer inbox',
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),
                  Text(
                    _ownsWorkspace
                        ? 'Owner offer review is live for this club workspace.'
                        : 'Switch into this club owner workspace before opening owner offer review.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
            GteSurfacePanel(
              accentColor: GteShellTheme.accentArena,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'World and scouting desk',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Use the club as the anchor point for world context, club-generated regens, national pre-seeds, transfer planning, and streamer tournaments.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 16),
                  Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    children: <Widget>[
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              WorldClubContextRouteData(
                                clubId: widget.clubId,
                                clubName: _resolvedClubName,
                              ),
                            ),
                        icon: Icons.public_outlined,
                        label: 'World context',
                        emphasized: true,
                      ),
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              WorldClubContextRouteData(
                                clubId: widget.clubId,
                                clubName: _resolvedClubName,
                              ),
                            ),
                        icon: Icons.auto_awesome_outlined,
                        label: 'Regen universe',
                      ),
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              const FootballTransferCenterRouteData(),
                            ),
                        icon: Icons.swap_horiz_outlined,
                        label: 'Transfer center',
                      ),
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              const PlayerCardsBrowseRouteData(),
                            ),
                        icon: Icons.style_outlined,
                        label: 'Player cards',
                      ),
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              const NationalTeamCompetitionsRouteData(),
                            ),
                        icon: Icons.flag_outlined,
                        label: 'National teams',
                      ),
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              const StreamerTournamentsListRouteData(),
                            ),
                        icon: Icons.live_tv_outlined,
                        label: 'Streamer tournaments',
                      ),
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              const BroadcastDeskRouteData(),
                            ),
                        icon: Icons.podcasts_outlined,
                        label: 'Broadcast desk',
                      ),
                      _buildRouteButton(
                        onPressed:
                            () => _openRoute(
                              context,
                              const GtexJackpotRouteData(),
                            ),
                        icon: Icons.celebration_outlined,
                        label: 'GTEX jackpot',
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ClubCommandSquadReadinessSection extends StatelessWidget {
  const _ClubCommandSquadReadinessSection({
    required this.controller,
    required this.fallbackClubName,
  });

  final ClubController? controller;
  final String fallbackClubName;

  @override
  Widget build(BuildContext context) {
    if (controller != null) {
      return AnimatedBuilder(
        animation: controller!,
        builder: (BuildContext context, Widget? child) {
          return _buildPanel();
        },
      );
    }
    return _buildPanel();
  }

  Widget _buildPanel() {
    final ClubController? mountedController = controller;
    final data = mountedController?.data;
    final bool isSyncing = mountedController?.isLoading == true;
    final String? errorMessage = mountedController?.errorMessage;

    if (data != null) {
      return SquadReadinessPanel(
        snapshot: SquadReadinessSnapshot.fromDashboard(
          data,
          isSyncing: isSyncing,
          errorMessage: errorMessage,
        ),
      );
    }

    return SquadReadinessPanel(
      snapshot: SquadReadinessSnapshot.blocked(
        clubName: fallbackClubName,
        message:
            mountedController == null
                ? 'No club dashboard controller is mounted on this route yet.'
                : isSyncing
                ? 'Club dashboard payload is still syncing.'
                : errorMessage ?? 'Club dashboard payload has not loaded yet.',
      ),
    );
  }
}

class _ClubCommandOperatingPanel extends StatelessWidget {
  const _ClubCommandOperatingPanel({
    required this.controller,
    required this.isOwnerWorkspace,
    required this.onOpenLogin,
  });

  final ClubController? controller;
  final bool isOwnerWorkspace;
  final VoidCallback? onOpenLogin;

  @override
  Widget build(BuildContext context) {
    if (controller != null) {
      return AnimatedBuilder(
        animation: controller!,
        builder: (BuildContext context, Widget? child) {
          return _buildPanel(context);
        },
      );
    }
    return _buildPanel(context);
  }

  Widget _buildPanel(BuildContext context) {
    final data = controller?.data;
    final bool isLoading = controller?.isLoading == true;
    final String? error = controller?.errorMessage;
    final bool hasController = controller != null;
    final bool hasData = data != null;

    final List<_ClubCommandSignal> signals = <_ClubCommandSignal>[
      _ClubCommandSignal(
        title: 'Squad readiness',
        value:
            !hasController
                ? 'BLOCKED'
                : isLoading
                ? 'SYNCING'
                : data?.playerCount == null
                ? 'UNKNOWN'
                : '${data!.playerCount}',
        state:
            !hasController
                ? shell.GtexSurfaceState.blocked
                : isLoading
                ? shell.GtexSurfaceState.syncing
                : data?.playerCount == null
                ? shell.GtexSurfaceState.degraded
                : data!.playerCount! > 0
                ? shell.GtexSurfaceState.confirmed
                : shell.GtexSurfaceState.empty,
        message:
            !hasController
                ? 'No club dashboard controller is mounted on this route yet.'
                : data?.playerCount == null
                ? 'The backend has not exposed registered squad count for this club.'
                : data!.playerCount! > 0
                ? 'Registered players are present in the club dashboard payload.'
                : 'The club dashboard returned no registered players.',
        icon: Icons.groups_outlined,
      ),
      _ClubCommandSignal(
        title: 'Formation health',
        value: hasData ? 'PENDING' : 'WAITING',
        state:
            hasData
                ? shell.GtexSurfaceState.pending
                : isLoading
                ? shell.GtexSurfaceState.syncing
                : shell.GtexSurfaceState.empty,
        message:
            'Formation health is waiting for a dedicated squad-shape endpoint; no match state is invented here.',
        icon: Icons.grid_view_outlined,
      ),
      _ClubCommandSignal(
        title: 'Scouting',
        value:
            !hasData
                ? 'WAITING'
                : data.reputation.recentEvents.isEmpty
                ? 'EMPTY'
                : '${data.reputation.recentEvents.length}',
        state:
            !hasData
                ? shell.GtexSurfaceState.empty
                : data.reputation.recentEvents.isEmpty
                ? shell.GtexSurfaceState.empty
                : shell.GtexSurfaceState.confirmed,
        message:
            !hasData || data.reputation.recentEvents.isEmpty
                ? 'No scouting or reputation events are present in this club snapshot.'
                : 'Recent reputation events are available for club intelligence review.',
        icon: Icons.manage_search_outlined,
      ),
      _ClubCommandSignal(
        title: 'Finance',
        value: 'PENDING',
        state:
            error != null
                ? shell.GtexSurfaceState.degraded
                : shell.GtexSurfaceState.pending,
        message:
            'Club finance remains explicit until a finance payload is mounted in this hub.',
        icon: Icons.account_balance_wallet_outlined,
      ),
      _ClubCommandSignal(
        title: 'Academy',
        value:
            !hasData ? 'WAITING' : '${data.trophyCabinet.academyHonorsCount}',
        state:
            !hasData
                ? shell.GtexSurfaceState.empty
                : data.trophyCabinet.academyHonorsCount > 0
                ? shell.GtexSurfaceState.confirmed
                : shell.GtexSurfaceState.empty,
        message:
            !hasData || data.trophyCabinet.academyHonorsCount == 0
                ? 'No academy honors are present in this club payload yet.'
                : 'Academy honors are confirmed in the trophy cabinet payload.',
        icon: Icons.school_outlined,
      ),
      _ClubCommandSignal(
        title: 'Sponsorships',
        value:
            !hasData
                ? 'WAITING'
                : data.catalog.any(_isSponsorshipCatalogItem)
                ? 'FOUND'
                : 'EMPTY',
        state:
            !hasData
                ? shell.GtexSurfaceState.empty
                : data.catalog.any(_isSponsorshipCatalogItem)
                ? shell.GtexSurfaceState.confirmed
                : shell.GtexSurfaceState.empty,
        message:
            !hasData || !data.catalog.any(_isSponsorshipCatalogItem)
                ? 'No sponsorship block is present in this club payload.'
                : 'Sponsorship catalog entries are available for this club.',
        icon: Icons.handshake_outlined,
      ),
    ];

    return GteSurfacePanel(
      key: const Key('club-command-operating-panel'),
      accentColor: GteShellTheme.accentClub,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              const Icon(Icons.dashboard_customize_outlined),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Club operating board',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'The club route exposes what is ready, blocked, empty, or waiting for backend truth before deeper migration.',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              if (!isOwnerWorkspace && onOpenLogin != null) ...<Widget>[
                const SizedBox(width: 12),
                FilledButton.tonalIcon(
                  onPressed: onOpenLogin,
                  icon: const Icon(Icons.login_outlined),
                  label: const Text('Sign in'),
                ),
              ],
            ],
          ),
          if (error != null) ...<Widget>[
            const SizedBox(height: 14),
            Text(
              error,
              style: Theme.of(
                context,
              ).textTheme.bodyMedium?.copyWith(color: GteShellTheme.warning),
            ),
          ],
          const SizedBox(height: 16),
          LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final bool compact = constraints.maxWidth < 760;
              final double width =
                  compact
                      ? constraints.maxWidth
                      : (constraints.maxWidth - 24) / 3;
              return Wrap(
                spacing: 12,
                runSpacing: 12,
                children: signals
                    .map(
                      (_ClubCommandSignal signal) => SizedBox(
                        width: width,
                        child: _ClubCommandSignalTile(signal: signal),
                      ),
                    )
                    .toList(growable: false),
              );
            },
          ),
        ],
      ),
    );
  }

  static bool _isSponsorshipCatalogItem(dynamic item) {
    final String category = item.category.toString().toLowerCase();
    final String title = item.title.toString().toLowerCase();
    return category.contains('sponsor') || title.contains('sponsor');
  }
}

class _ClubCommandSignal {
  const _ClubCommandSignal({
    required this.title,
    required this.value,
    required this.state,
    required this.message,
    required this.icon,
  });

  final String title;
  final String value;
  final shell.GtexSurfaceState state;
  final String message;
  final IconData icon;
}

class _ClubCommandSignalTile extends StatelessWidget {
  const _ClubCommandSignalTile({required this.signal});

  final _ClubCommandSignal signal;

  @override
  Widget build(BuildContext context) {
    final Color color = _colorFor(signal.state);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: color.withValues(alpha: 0.24)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Icon(signal.icon, color: color, size: 18),
              const SizedBox(width: 8),
              Text(
                signal.state.name.toUpperCase(),
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  color: color,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(signal.title, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          Text(signal.value, style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 8),
          Text(signal.message, style: Theme.of(context).textTheme.bodyMedium),
        ],
      ),
    );
  }

  Color _colorFor(shell.GtexSurfaceState state) {
    switch (state) {
      case shell.GtexSurfaceState.confirmed:
      case shell.GtexSurfaceState.data:
        return GteShellTheme.positive;
      case shell.GtexSurfaceState.blocked:
      case shell.GtexSurfaceState.error:
        return GteShellTheme.negative;
      case shell.GtexSurfaceState.pending:
      case shell.GtexSurfaceState.degraded:
        return GteShellTheme.warning;
      case shell.GtexSurfaceState.loading:
      case shell.GtexSurfaceState.syncing:
      case shell.GtexSurfaceState.reconnecting:
        return GteShellTheme.accentClub;
      case shell.GtexSurfaceState.empty:
        return GteShellTheme.textMuted;
    }
  }
}
