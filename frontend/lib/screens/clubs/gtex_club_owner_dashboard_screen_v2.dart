import 'dart:async';

import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_controller.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/features/club_growth_redesign/club_growth_redesign.dart';
import 'package:gte_frontend/features/club_lifecycle_redesign/club_lifecycle_redesign.dart';
import 'package:gte_frontend/features/club_redesign/club_redesign.dart';
import 'package:gte_frontend/features/club_identity/reputation/data/reputation_models.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/trophy_item_dto.dart';
import 'package:gte_frontend/models/club_catalog_models.dart';
import 'package:gte_frontend/models/club_models.dart';
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
  ClubController? _controller;
  GtexClubLifecycleController? _lifecycleController;
  GtexClubGrowthController? _growthController;

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
        oldWidget.authedApi != widget.authedApi) {
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
    _controller?.dispose();
    _lifecycleController?.dispose();
    _growthController?.dispose();
    _controller = null;
    _lifecycleController = null;
    _growthController = null;
  }

  void _createController() {
    if (!widget.isAuthenticated) {
      _controller = null;
      _lifecycleController = null;
      _growthController = null;
      return;
    }
    final String? baseUrl = widget.baseUrl;
    if (baseUrl == null || baseUrl.trim().isEmpty) {
      _controller = null;
      _lifecycleController = null;
      _growthController = null;
      return;
    }
    final GteBackendMode backendMode =
        widget.backendMode ?? GteBackendMode.live;
    final ClubController controller = ClubController.standard(
      clubId: widget.clubId,
      clubName: widget.clubName,
      baseUrl: baseUrl,
      backendMode: backendMode,
      accessToken: widget.accessToken,
    );
    _controller = controller;
    controller.ensureLoaded();
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

  @override
  Widget build(BuildContext context) {
    final ClubController? controller = _controller;
    if (!widget.isAuthenticated || controller == null) {
      return GtexClubOwnerDashboardV2(
        clubId: widget.clubId,
        clubName: widget.clubName,
        baseUrl: widget.baseUrl,
        backendMode: widget.backendMode,
        isAuthenticated: widget.isAuthenticated,
        onOpenLogin: widget.onOpenLogin,
      );
    }

    final GtexClubLifecycleController? lifecycleController =
        _lifecycleController;
    final GtexClubGrowthController? growthController = _growthController;
    return AnimatedBuilder(
      animation: Listenable.merge(<Listenable>[
        controller,
        if (lifecycleController != null) lifecycleController,
        if (growthController != null) growthController,
      ]),
      builder: (BuildContext context, Widget? child) {
        final ClubDashboardData? data = controller.data;
        if (controller.isLoading && data == null) {
          return const Center(child: CircularProgressIndicator());
        }
        if (data == null) {
          return Padding(
            padding: const EdgeInsets.all(GtexSpacing.lg),
            child: GtexEmptyState(
              title: 'Club command unavailable',
              message:
                  controller.errorMessage ??
                  'GTEX could not load live club data for this owner workspace.',
              icon: Icons.shield_outlined,
              actionLabel: 'Retry club',
              onAction: controller.load,
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
          initialSnapshot: _snapshotFromLiveClub(data),
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

  GtexClubWorkspaceSnapshot _snapshotFromLiveClub(ClubDashboardData data) {
    final List<ClubPurchaseRecord> purchases = data.purchaseHistory;
    final int openOrdersCredits = purchases
        .where((ClubPurchaseRecord item) => !item.equipped)
        .fold<int>(
          0,
          (int total, ClubPurchaseRecord item) =>
              total + item.priceCredits.round(),
        );
    final int squadValueCredits = data.catalog
        .where(
          (ClubCatalogItem item) =>
              item.ownershipStatus != CatalogOwnershipStatus.available,
        )
        .fold<int>(
          0,
          (int total, ClubCatalogItem item) =>
              total + item.priceCredits.round(),
        );
    final List<TrophyItemDto> honors = data.trophyCabinet.featuredHonors(
      limit: 6,
    );
    final List<String> identityTags = <String>[
      data.identity.colorPalette.paletteName,
      data.reputation.profile.currentPrestigeTier.label,
      if (data.playerCount != null) '${data.playerCount} registered players',
      '${data.equippedCatalogCount} equipped identity assets',
    ].where((String value) => value.trim().isNotEmpty).toList(growable: false);

    return GtexClubWorkspaceSnapshot(
      clubId: data.clubId,
      clubName: data.clubName,
      shortCode: _shortCode(data),
      country: data.countryName ?? data.reputation.profile.regionLabel,
      division: data.reputation.profile.currentPrestigeTier.label,
      ownerName: widget.ownerName ?? 'Club owner',
      followers: data.reputation.profile.currentScore,
      shareholders: data.reputation.contributors.length,
      finances: GtexClubFinancialSnapshot(
        walletCredits: widget.walletCredits,
        squadValueCredits: squadValueCredits,
        openOrdersCredits: openOrdersCredits,
        monthlyRevenueCredits: data.purchaseHistory.fold<int>(
          0,
          (int total, ClubPurchaseRecord item) =>
              total + item.priceCredits.round(),
        ),
        sharePriceCredits:
            data.reputation.profile.currentScore <= 0
                ? 1
                : data.reputation.profile.currentScore,
      ),
      squad: const <GtexClubMember>[],
      news: data.reputation.recentEvents
          .map(
            (ReputationEventDto event) => GtexClubNewsItem(
              id: event.id,
              headline: event.title,
              category: event.category.label,
              timestampLabel: event.seasonLabel,
              summary: event.description,
            ),
          )
          .toList(growable: false),
      orders: purchases
          .take(8)
          .map(
            (ClubPurchaseRecord item) => GtexClubOrderItem(
              id: item.id,
              title: item.itemTitle,
              status: item.statusLabel,
              amountCredits: item.priceCredits.round(),
              timestampLabel: _dateLabel(item.purchasedAt),
            ),
          )
          .toList(growable: false),
      trophies: honors
          .map(
            (TrophyItemDto item) => GtexClubTrophy(
              id: item.trophyWinId,
              title: item.trophyName,
              season: item.seasonLabel,
              tier: item.prestigeLabel,
            ),
          )
          .toList(growable: false),
      identityTags: identityTags,
      activity: <String>[
        if (data.trophyCabinet.totalHonorsCount > 0)
          '${data.trophyCabinet.totalHonorsCount} honors in the cabinet',
        if (data.purchaseHistory.isNotEmpty)
          '${data.purchaseHistory.length} identity purchases recorded',
        if (data.reputation.recentEvents.isNotEmpty)
          '${data.reputation.recentEvents.length} reputation events synced',
        if (data.playerCount != null) '${data.playerCount} players registered',
      ],
    );
  }

  String _shortCode(ClubDashboardData data) {
    final String direct = data.identity.shortClubCode.trim();
    if (direct.isNotEmpty) {
      return direct.toUpperCase();
    }
    final List<String> parts = data.clubName
        .split(RegExp(r'\s+'))
        .where((String part) => part.trim().isNotEmpty)
        .toList(growable: false);
    if (parts.isEmpty) {
      return 'GTX';
    }
    return parts.take(3).map((String part) => part[0].toUpperCase()).join();
  }

  String _dateLabel(DateTime value) {
    final DateTime local = value.toLocal();
    return '${local.year}-${local.month.toString().padLeft(2, '0')}-${local.day.toString().padLeft(2, '0')}';
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
