import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_controller.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/club_hub/widgets/club_hub_content.dart';
import 'package:gte_frontend/features/club_identity/dynasty/presentation/era_history_screen.dart';
import 'package:gte_frontend/features/club_navigation/club_navigation.dart';
import 'package:gte_frontend/models/club_models.dart';
import 'package:gte_frontend/screens/clubs/club_branding_screen.dart';
import 'package:gte_frontend/screens/clubs/club_dynasty_screen.dart';
import 'package:gte_frontend/screens/clubs/club_purchase_history_screen.dart';
import 'package:gte_frontend/screens/clubs/club_reputation_screen.dart';
import 'package:gte_frontend/screens/clubs/club_trophy_cabinet_screen.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';

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
  });

  final String clubId;
  final String? clubName;
  final ClubController? controller;
  final String baseUrl;
  final GteBackendMode backendMode;
  final bool isAuthenticated;
  final VoidCallback? onOpenLogin;
  final ClubNavigationTab initialTab;

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
          return const Center(child: CircularProgressIndicator());
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
        return RefreshIndicator(
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
          ),
        );
      },
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

  Future<void> _openDynasty(BuildContext context) {
    return Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) =>
            ClubDynastyScreen(controller: _controller),
      ),
    );
  }

  Future<void> _openEraHistory(BuildContext context) {
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
