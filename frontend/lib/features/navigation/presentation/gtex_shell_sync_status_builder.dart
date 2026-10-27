import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/competition_controller.dart';
import 'package:gte_frontend/controllers/creator_controller.dart';
import 'package:gte_frontend/controllers/referral_controller.dart';
import 'package:gte_frontend/features/navigation/routing/gte_navigation_route.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/widgets/gte_sync_status_card.dart';

/// Extracted sync-status card factory for `GteNavigationShellScreen`
/// (Phase B1 shell decomposition).
class GtexShellSyncStatusBuilder {
  const GtexShellSyncStatusBuilder._();

  static GteSyncStatusCard build({
    required GtePrimaryDestination destination,
    required Color accent,
    required GteExchangeController exchangeController,
    required CompetitionController competitionController,
    required CreatorController creatorController,
    required ReferralController referralController,
    required bool isReferralRuntimeAvailable,
    required String runtimeModeLabel,
    required String apiHostLabel,
    required String runtimeAudienceLabel,
  }) {
    switch (destination) {
      case GtePrimaryDestination.competitions:
        return GteSyncStatusCard(
          title: 'Competitions',
          status:
              competitionController.discoveryError == null
                  ? 'Fixtures, brackets, and competition updates are synced.'
                  : 'Competition feed degraded. Showing the latest available snapshot.',
          syncedAt: competitionController.discoverySyncedAt,
          accent: accent,
          isRefreshing: competitionController.isLoadingDiscovery,
          onRefresh: competitionController.loadDiscovery,
        );
      case GtePrimaryDestination.market:
        return GteSyncStatusCard(
          title: 'Transfer Hub',
          status:
              exchangeController.marketError == null
                  ? 'Listings, prices, clubs, and negotiation context are ready.'
                  : 'Transfer board degraded. The last confirmed board is still visible.',
          syncedAt: exchangeController.marketSyncedAt,
          accent: accent,
          isRefreshing: exchangeController.isLoadingMarket,
          onRefresh: () => exchangeController.loadMarket(reset: true),
        );
      case GtePrimaryDestination.regens:
        return GteSyncStatusCard(
          title: 'Regen World',
          status:
              'Regen prospects, lineage, contracts, and Create-a-Son orders '
              'load from the live regen universe.',
          syncedAt: null,
          accent: accent,
          isRefreshing: false,
          onRefresh: null,
        );
      case GtePrimaryDestination.hub:
        final bool creatorHealthy = creatorController.errorMessage == null;
        return GteSyncStatusCard(
          title: 'Community',
          status:
              creatorHealthy
                  ? isReferralRuntimeAvailable
                      ? 'Creator tools, referral activity, and community signals are synced.'
                      : 'Creator tools are live. Referral rewards will appear here once that runtime is enabled.'
                  : 'Community feed degraded. Showing the latest available snapshot.',
          syncedAt: creatorController.syncedAt,
          accent: accent,
          isRefreshing:
              referralController.isLoading || creatorController.isLoading,
          onRefresh:
              exchangeController.isAuthenticated
                  ? () {
                    referralController.load();
                    creatorController.load();
                  }
                  : null,
        );
      case GtePrimaryDestination.community:
        return GteSyncStatusCard(
          title: 'Community',
          status:
              exchangeController.isAuthenticated
                  ? 'Watchlists, live threads, direct messages, and creator-club follows are wired to live community endpoints.'
                  : 'Public live threads are visible. Sign in to manage watchlists, follows, and direct messages.',
          syncedAt: null,
          accent: accent,
          isRefreshing: false,
          onRefresh: null,
        );
      case GtePrimaryDestination.club:
        return GteSyncStatusCard(
          title: 'Club operations',
          status:
              'Club management opens here once this account owns or is linked to a club.',
          syncedAt: exchangeController.marketSyncedAt,
          accent: accent,
          isRefreshing: false,
          onRefresh: null,
        );
      case GtePrimaryDestination.wallet:
        return GteSyncStatusCard(
          title: 'Club funds',
          status:
              exchangeController.isAuthenticated
                  ? 'Balance, player holdings, and activity records are up to date.'
                  : 'Sign in to view funds, holdings, and account activity.',
          syncedAt:
              exchangeController.portfolioSyncedAt ??
              exchangeController.ordersSyncedAt,
          accent: accent,
          isRefreshing:
              exchangeController.isLoadingPortfolio ||
              exchangeController.isLoadingOrders,
          onRefresh:
              exchangeController.isAuthenticated
                  ? exchangeController.refreshAccount
                  : null,
        );
      case GtePrimaryDestination.home:
        return GteSyncStatusCard(
          title: 'Home sync',
          status:
              'Home keeps your club, matchday, scouting, and world routes aligned.',
          detail:
              'Runtime $runtimeModeLabel on $apiHostLabel - $runtimeAudienceLabel',
          syncedAt: exchangeController.marketSyncedAt,
          accent: accent,
          isRefreshing: exchangeController.isBootstrapping,
          onRefresh: exchangeController.bootstrap,
        );
    }
  }
}
