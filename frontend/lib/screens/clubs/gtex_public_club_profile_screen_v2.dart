import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_controller.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/club_redesign/club_redesign.dart';
import 'package:gte_frontend/features/club_identity/reputation/data/reputation_models.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/trophy_item_dto.dart';
import 'package:gte_frontend/models/club_catalog_models.dart';
import 'package:gte_frontend/models/club_models.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

class GtexPublicClubProfileScreenV2 extends StatefulWidget {
  const GtexPublicClubProfileScreenV2({
    super.key,
    required this.clubId,
    this.clubName,
    this.baseUrl,
    this.backendMode,
    this.accessToken,
    this.isAuthenticated = true,
    this.onOpenLogin,
  });

  final String clubId;
  final String? clubName;
  final String? baseUrl;
  final GteBackendMode? backendMode;
  final String? accessToken;
  final bool isAuthenticated;
  final VoidCallback? onOpenLogin;

  @override
  State<GtexPublicClubProfileScreenV2> createState() =>
      _GtexPublicClubProfileScreenV2State();
}

class _GtexPublicClubProfileScreenV2State
    extends State<GtexPublicClubProfileScreenV2> {
  ClubController? _controller;

  @override
  void initState() {
    super.initState();
    _createController();
  }

  @override
  void didUpdateWidget(covariant GtexPublicClubProfileScreenV2 oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.clubId != widget.clubId ||
        oldWidget.baseUrl != widget.baseUrl ||
        oldWidget.backendMode != widget.backendMode ||
        oldWidget.accessToken != widget.accessToken) {
      _controller?.dispose();
      _createController();
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  void _createController() {
    final String? baseUrl = widget.baseUrl;
    if (baseUrl == null || baseUrl.trim().isEmpty) {
      _controller = null;
      return;
    }
    final ClubController controller = ClubController.standard(
      clubId: widget.clubId,
      clubName: widget.clubName,
      baseUrl: baseUrl,
      backendMode: widget.backendMode ?? GteBackendMode.live,
      accessToken: widget.accessToken,
    );
    _controller = controller;
    controller.ensureLoaded();
  }

  @override
  Widget build(BuildContext context) {
    final ClubController? controller = _controller;
    if (controller == null) {
      return Padding(
        padding: const EdgeInsets.all(GtexSpacing.lg),
        child: GtexEmptyState(
          title: 'Club profile unavailable',
          message:
              'GTEX needs a live API base URL before this public club profile can load.',
          icon: Icons.shield_outlined,
        ),
      );
    }

    return AnimatedBuilder(
      animation: controller,
      builder: (BuildContext context, Widget? child) {
        final ClubDashboardData? data = controller.data;
        if (controller.isLoading && data == null) {
          return const Center(child: CircularProgressIndicator());
        }
        if (data == null) {
          return Padding(
            padding: const EdgeInsets.all(GtexSpacing.lg),
            child: GtexEmptyState(
              title: 'Club profile unavailable',
              message:
                  controller.errorMessage ??
                  'GTEX could not load this public club from the live backend.',
              icon: Icons.shield_outlined,
              actionLabel: 'Retry club',
              onAction: controller.load,
            ),
          );
        }

        return GtexPublicClubProfileV2(
          clubId: widget.clubId,
          clubName: widget.clubName,
          baseUrl: widget.baseUrl,
          backendMode: widget.backendMode,
          accessToken: widget.accessToken,
          initialSnapshot: _snapshotFromLiveClub(data),
          isAuthenticated: widget.isAuthenticated,
          onOpenLogin: widget.onOpenLogin,
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
      '${data.equippedCatalogCount} public identity assets',
    ].where((String value) => value.trim().isNotEmpty).toList(growable: false);

    return GtexClubWorkspaceSnapshot(
      clubId: data.clubId,
      clubName: data.clubName,
      shortCode: _shortCode(data),
      country: data.countryName ?? data.reputation.profile.regionLabel,
      division: data.reputation.profile.currentPrestigeTier.label,
      ownerName: 'Club owner',
      followers: data.reputation.profile.currentScore,
      shareholders: data.reputation.contributors.length,
      finances: GtexClubFinancialSnapshot(
        walletCredits: 0,
        squadValueCredits: squadValueCredits,
        openOrdersCredits: openOrdersCredits,
        monthlyRevenueCredits: purchases.fold<int>(
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
          '${data.trophyCabinet.totalHonorsCount} honors recorded',
        if (data.reputation.recentEvents.isNotEmpty)
          '${data.reputation.recentEvents.length} newsroom signals synced',
        if (data.reputation.contributors.isNotEmpty)
          '${data.reputation.contributors.length} club reputation contributors',
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
