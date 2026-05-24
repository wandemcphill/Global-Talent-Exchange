import 'dart:async';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:gte_frontend/data/club_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/features/club_growth_redesign/club_growth_redesign.dart';
import 'package:gte_frontend/features/club_lifecycle_redesign/club_lifecycle_redesign.dart';
import 'package:gte_frontend/features/club_redesign/club_redesign.dart';
import 'package:gte_frontend/features/navigation/routing/gte_navigation_route.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

class GtexClubOwnerDashboardScreenV2 extends StatefulWidget {
  const GtexClubOwnerDashboardScreenV2({
    super.key,
    required this.clubId,
    this.clubName,
    this.baseUrl,
    this.backendMode,
    this.accessToken,
    this.authedApi,
    this.snapshotApi,
    this.ownerName,
    this.walletCredits = 0,
    this.isAuthenticated = true,
    this.onOpenLogin,
  });

  final String clubId;
  final String? clubName;
  final String? baseUrl;
  final GteBackendMode? backendMode;
  final String? accessToken;
  final GteAuthedApi? authedApi;
  final ClubApi? snapshotApi;
  final String? ownerName;
  final int walletCredits;
  final bool isAuthenticated;
  final VoidCallback? onOpenLogin;

  @override
  State<GtexClubOwnerDashboardScreenV2> createState() =>
      _GtexClubOwnerDashboardScreenV2State();
}

class _GtexClubOwnerDashboardScreenV2State
    extends State<GtexClubOwnerDashboardScreenV2> {
  ClubApi? _snapshotApi;
  GtexClubLifecycleController? _lifecycleController;
  GtexClubGrowthController? _growthController;
  GtexClubWorkspaceSnapshot? _snapshot;
  String? _snapshotError;
  bool _snapshotLoading = false;
  int _snapshotRequestId = 0;

  @override
  void initState() {
    super.initState();
    _createController();
  }

  @override
  void didUpdateWidget(covariant GtexClubOwnerDashboardScreenV2 oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.clubId != widget.clubId ||
        oldWidget.baseUrl != widget.baseUrl ||
        oldWidget.backendMode != widget.backendMode ||
        oldWidget.accessToken != widget.accessToken ||
        oldWidget.authedApi != widget.authedApi ||
        oldWidget.snapshotApi != widget.snapshotApi ||
        oldWidget.clubName != widget.clubName) {
      _disposeControllers();
      _createController();
    }
  }

  @override
  void dispose() {
    _disposeControllers();
    super.dispose();
  }

  void _disposeControllers() {
    _lifecycleController?.dispose();
    _growthController?.dispose();
    _snapshotRequestId += 1;
    _snapshotApi = null;
    _snapshot = null;
    _snapshotError = null;
    _snapshotLoading = false;
    _lifecycleController = null;
    _growthController = null;
  }

  void _createController() {
    if (!widget.isAuthenticated) {
      _snapshotApi = null;
      _lifecycleController = null;
      _growthController = null;
      return;
    }
    final String? baseUrl = widget.baseUrl;
    if (baseUrl == null || baseUrl.trim().isEmpty) {
      _snapshotApi = null;
      _lifecycleController = null;
      _growthController = null;
      return;
    }
    final GteBackendMode backendMode =
        widget.backendMode ?? GteBackendMode.live;
    _snapshotApi =
        widget.snapshotApi ??
        ClubApi.standard(
          baseUrl: baseUrl,
          mode: backendMode,
          accessToken: widget.accessToken,
        );
    unawaited(_loadSnapshot(notify: false));
    final GtexClubLifecycleController lifecycleController =
        GtexClubLifecycleController(
          api: GtexClubLifecycleApi.standard(
            baseUrl: baseUrl,
            accessToken: widget.accessToken,
            mode: backendMode,
            client: widget.authedApi,
          ),
          clubId: widget.clubId,
        );
    _lifecycleController = lifecycleController;
    unawaited(lifecycleController.load());
    final GtexClubGrowthController growthController = GtexClubGrowthController(
      api: GtexClubGrowthApi.standard(
        baseUrl: baseUrl,
        accessToken: widget.accessToken,
        mode: backendMode,
        client: widget.authedApi,
      ),
      clubId: widget.clubId,
    );
    _growthController = growthController;
    unawaited(growthController.load());
  }

  Future<void> _loadSnapshot({bool notify = true}) {
    final ClubApi? api = _snapshotApi;
    if (api == null) {
      return Future<void>.value();
    }
    final int requestId = ++_snapshotRequestId;
    void update(VoidCallback callback) {
      if (notify && mounted) {
        setState(callback);
      } else {
        callback();
      }
    }

    update(() {
      _snapshotLoading = true;
      _snapshotError = null;
      _snapshot = null;
    });
    final Future<void> task = () async {
      try {
        final GtexClubWorkspaceSnapshot snapshot = await api
            .fetchV2WorkspaceSnapshot(
              clubId: widget.clubId,
              clubName: widget.clubName,
            );
        if (!mounted || requestId != _snapshotRequestId) {
          return;
        }
        setState(() {
          _snapshot = snapshot;
          _snapshotError = null;
          _snapshotLoading = false;
        });
      } catch (error) {
        if (!mounted || requestId != _snapshotRequestId) {
          return;
        }
        setState(() {
          _snapshot = null;
          _snapshotError = _snapshotErrorMessage(error);
          _snapshotLoading = false;
        });
      }
    }();
    return task;
  }

  String _snapshotErrorMessage(Object error) {
    if (error is GteApiException) {
      return error.message;
    }
    return 'GTEX could not load the live club V2 snapshot. $error';
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.isAuthenticated) {
      return GtexClubOwnerDashboardV2(
        clubId: widget.clubId,
        clubName: widget.clubName,
        baseUrl: widget.baseUrl,
        backendMode: widget.backendMode,
        isAuthenticated: widget.isAuthenticated,
        onOpenLogin: widget.onOpenLogin,
        onOpenMarket: () => context.go(const GteNavigationRoute.market().path),
        onCreateCompetition:
            () => context.go(const GteNavigationRoute.competitions().path),
      );
    }
    if (_snapshotApi == null) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.all(GtexSpacing.lg),
          child: GtexEmptyState(
            title: 'Live club workspace required',
            message:
                'This club workspace no longer opens with demo data. Connect the live backend session before loading owner operations.',
            icon: Icons.shield_outlined,
          ),
        ),
      );
    }

    final GtexClubLifecycleController? lifecycleController =
        _lifecycleController;
    final GtexClubGrowthController? growthController = _growthController;
    return AnimatedBuilder(
      animation: Listenable.merge(<Listenable>[
        if (lifecycleController != null) lifecycleController,
        if (growthController != null) growthController,
      ]),
      builder: (BuildContext context, Widget? child) {
        final GtexClubWorkspaceSnapshot? snapshot = _snapshot;
        if (_snapshotLoading && snapshot == null) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot == null) {
          return Padding(
            padding: const EdgeInsets.all(GtexSpacing.lg),
            child: GtexEmptyState(
              title: 'Live club snapshot unavailable',
              message:
                  _snapshotError ??
                  'GTEX could not load the live Club V2 snapshot for this owner workspace.',
              icon: Icons.shield_outlined,
              actionLabel: 'Retry club',
              onAction: () => unawaited(_loadSnapshot()),
            ),
          );
        }

        return GtexClubOwnerDashboardV2(
          clubId: widget.clubId,
          clubName: widget.clubName,
          baseUrl: widget.baseUrl,
          backendMode: widget.backendMode,
          isAuthenticated: widget.isAuthenticated,
          onOpenLogin: widget.onOpenLogin,
          onOpenMarket:
              () => context.go(const GteNavigationRoute.market().path),
          onCreateCompetition:
              () => context.go(const GteNavigationRoute.competitions().path),
          initialSnapshot: snapshot,
          lifecycleDashboard: lifecycleController?.dashboard,
          lifecycleLoading: lifecycleController?.busy ?? false,
          lifecycleError: lifecycleController?.error,
          growthDashboard: growthController?.dashboard,
          growthLoading: growthController?.busy ?? false,
          growthError: growthController?.error,
          onRefreshLifecycle:
              lifecycleController == null
                  ? null
                  : () => unawaited(lifecycleController.load()),
          onSyncSquadRegistration:
              lifecycleController == null
                  ? null
                  : () =>
                      unawaited(lifecycleController.syncSquadRegistration()),
          onSubmitSquadRegistration:
              lifecycleController == null
                  ? null
                  : () =>
                      unawaited(lifecycleController.submitSquadRegistration()),
          onLockSquadRegistration:
              lifecycleController == null
                  ? null
                  : () =>
                      unawaited(lifecycleController.lockSquadRegistration()),
          onAdvanceLifecycle:
              lifecycleController == null
                  ? null
                  : () => unawaited(lifecycleController.advanceLifecycle()),
          onRefreshGrowth:
              growthController == null
                  ? null
                  : () => unawaited(growthController.load()),
          onHireStaff:
              growthController == null
                  ? null
                  : (String staffId) =>
                      unawaited(growthController.hireStaff(staffId)),
          onGenerateAcademyProspects:
              growthController == null
                  ? null
                  : () => unawaited(growthController.generateProspects()),
          onOfferAcademyContract:
              growthController == null
                  ? null
                  : (String prospectId) => unawaited(
                    growthController.offerAndAcceptProspectContract(prospectId),
                  ),
          onPromoteAcademyProspect:
              growthController == null
                  ? null
                  : (String prospectId) =>
                      unawaited(growthController.promoteProspect(prospectId)),
        );
      },
    );
  }
}

class GtexClubOwnerDashboardPreviewV2 extends StatelessWidget {
  const GtexClubOwnerDashboardPreviewV2({super.key});

  @override
  Widget build(BuildContext context) {
    return GtexClubOwnerDashboardV2(
      clubId: 'preview-club',
      clubName: 'GTEX Preview Club',
      isAuthenticated: true,
    );
  }
}
