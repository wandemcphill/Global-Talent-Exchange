import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_controller.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/app_routes/gte_navigation_helpers.dart';
import 'package:gte_frontend/features/app_routes/gte_route_data.dart';
import 'package:gte_frontend/features/club_hub/widgets/club_hub_content.dart';
import 'package:gte_frontend/features/club_identity/dynasty/presentation/era_history_screen.dart';
import 'package:gte_frontend/features/club_navigation/club_navigation.dart';
import 'package:gte_frontend/models/club_models.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/screens/clubs/club_branding_screen.dart';
import 'package:gte_frontend/screens/clubs/club_dynasty_screen.dart';
import 'package:gte_frontend/screens/clubs/club_purchase_history_screen.dart';
import 'package:gte_frontend/screens/clubs/club_reputation_screen.dart';
import 'package:gte_frontend/screens/clubs/club_trophy_cabinet_screen.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_sync_status_card.dart';

class ClubHubScreen extends StatefulWidget {
  const ClubHubScreen({
    super.key,
    required this.clubId,
    this.clubName,
    this.controller,
    this.baseUrl = 'http://127.0.0.1:8000',
    this.backendMode = GteBackendMode.liveThenFixture,
    this.isAuthenticated = true,
    this.onOpenLogin,
    this.initialTab = ClubNavigationTab.squad,
    this.navigationDependencies,
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

  @override
  State<ClubHubScreen> createState() => _ClubHubScreenState();
}

class _ClubHubScreenState extends State<ClubHubScreen> {
  late final ClubController _controller;
  late final bool _ownsController;
  late ClubNavigationTab _selectedTab;

  @override
  void initState() {
    super.initState();
    _selectedTab = widget.initialTab;
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
      builder: (BuildContext context, Widget? child) {
        if (_controller.isLoading && !_controller.hasData) {
          return const Padding(
            padding: EdgeInsets.all(20),
            child: GteStatePanel(
              eyebrow: 'CLUB SYSTEMS',
              title: 'Loading club identity command room',
              message:
                  'Squad, prestige, trophies, and history surfaces are being assembled for a cleaner club lane.',
              icon: Icons.shield_outlined,
              accentColor: Color(0xFF85B8FF),
              isLoading: true,
            ),
          );
        }

        if (_controller.errorMessage != null && !_controller.hasData) {
          return Padding(
            padding: const EdgeInsets.all(20),
            child: GteStatePanel(
              title: 'Club hub unavailable',
              message: _controller.errorMessage!,
              actionLabel: 'Retry',
              onAction: _controller.load,
              icon: Icons.shield_outlined,
            ),
          );
        }

        final ClubDashboardData data = _controller.data!;
        return Column(
          children: <Widget>[
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
              child: GteSyncStatusCard(
                title: 'Club identity systems',
                status: widget.isAuthenticated
                    ? 'Squad, prestige, culture, and identity layers are in writable mode.'
                    : 'Guest preview mode is active for club surfaces.',
                syncedAt: _controller.dataSyncedAt,
                accent: const Color(0xFF85B8FF),
                isRefreshing: _controller.isLoading,
                onRefresh: _controller.refresh,
              ),
            ),
            if (!widget.isAuthenticated)
              const Padding(
                padding: EdgeInsets.fromLTRB(20, 8, 20, 0),
                child: GteStatePanel(
                  eyebrow: 'GUEST PREVIEW',
                  title:
                      'Club identity is open for scouting, but edits stay protected.',
                  message:
                      'Browse squad mood, history, and prestige from the public concourse. Sign in to reshape branding, dynasty, and reputation layers.',
                  icon: Icons.lock_outline,
                  accentColor: Color(0xFF85B8FF),
                ),
              ),
            const SizedBox(height: 8),
            Expanded(
              child: RefreshIndicator(
                onRefresh: _controller.refresh,
                child: ClubHubContent(
                  controller: _controller,
                  data: data,
                  selectedTab: _selectedTab,
                  isAuthenticated: widget.isAuthenticated,
                  noticeMessage: _controller.noticeMessage,
                  onOpenLogin: widget.onOpenLogin,
                  onTabSelected: (ClubNavigationTab tab) {
                    if (_selectedTab == tab) {
                      return;
                    }
                    setState(() {
                      _selectedTab = tab;
                    });
                  },
                  onOpenIdentity: () => _openIdentity(context),
                  onOpenReputation: () => _openReputation(context),
                  onOpenTrophies: () => _openTrophies(context),
                  onOpenDynasty: () => _openDynasty(context),
                  onOpenEraHistory: () => _openEraHistory(context),
                  onOpenPurchaseHistory: () => _openPurchaseHistory(context),
                  navigationDependencies: widget.navigationDependencies,
                ),
              ),
            ),
          ],
        );
      },
    );
  }

  Future<void> _openIdentity(BuildContext context) {
    final GteNavigationDependencies? dependencies =
        widget.navigationDependencies;
    if (dependencies != null) {
      return GteNavigationHelpers.pushRoute<void>(
        context,
        route: ClubIdentityJerseysRouteData(
          clubId: widget.clubId,
          clubName: widget.clubName,
        ),
        dependencies: dependencies,
      );
    }
    return Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) =>
            ClubBrandingScreen(controller: _controller),
      ),
    );
  }

  Future<void> _openReputation(BuildContext context) {
    final GteNavigationDependencies? dependencies =
        widget.navigationDependencies;
    if (dependencies != null) {
      return GteNavigationHelpers.pushRoute<void>(
        context,
        route: ClubReputationOverviewRouteData(
          clubId: widget.clubId,
          clubName: widget.clubName,
        ),
        dependencies: dependencies,
      );
    }
    return Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) =>
            ClubReputationScreen(controller: _controller),
      ),
    );
  }

  Future<void> _openTrophies(BuildContext context) {
    final GteNavigationDependencies? dependencies =
        widget.navigationDependencies;
    if (dependencies != null) {
      return GteNavigationHelpers.pushRoute<void>(
        context,
        route: ClubTrophyCabinetRouteData(
          clubId: widget.clubId,
          clubName: widget.clubName,
        ),
        dependencies: dependencies,
      );
    }
    return Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) =>
            ClubTrophyCabinetScreen(controller: _controller),
      ),
    );
  }

  Future<void> _openDynasty(BuildContext context) {
    final GteNavigationDependencies? dependencies =
        widget.navigationDependencies;
    if (dependencies != null) {
      return GteNavigationHelpers.pushRoute<void>(
        context,
        route: ClubDynastyOverviewRouteData(
          clubId: widget.clubId,
          clubName: widget.clubName,
        ),
        dependencies: dependencies,
      );
    }
    return Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) =>
            ClubDynastyScreen(controller: _controller),
      ),
    );
  }

  Future<void> _openEraHistory(BuildContext context) {
    final GteNavigationDependencies? dependencies =
        widget.navigationDependencies;
    if (dependencies != null) {
      return GteNavigationHelpers.pushRoute<void>(
        context,
        route: ClubDynastyHistoryRouteData(
          clubId: widget.clubId,
          clubName: widget.clubName,
        ),
        dependencies: dependencies,
      );
    }
    return Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => EraHistoryScreen(
          clubId: widget.clubId,
          baseUrl: widget.baseUrl,
          backendMode: widget.backendMode,
        ),
      ),
    );
  }

  Future<void> _openPurchaseHistory(BuildContext context) {
    return Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) =>
            ClubPurchaseHistoryScreen(controller: _controller),
      ),
    );
  }
}
