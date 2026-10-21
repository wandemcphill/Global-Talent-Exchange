import 'package:flutter/foundation.dart';

/// Canonical GTEX Shell route builders and legacy alias redirect table
/// (Master Plan Document E3, Phase A3).
///
/// Preserves compatibility for all ~60 legacy routes while providing
/// deterministic canonical paths for the upgraded shell.
@immutable
class GtexCanonicalRoutes {
  const GtexCanonicalRoutes._();

  static const String home = '/app/home';
  static const String inbox = '/app/inbox';
  static const String matchday = '/app/matchday';
  static const String matchdayFixtures = '/app/matchday/fixtures';
  static const String matchdayNational = '/app/matchday/national';
  static const String market = '/app/market';
  static const String marketShares = '/app/market/shares';
  static const String marketCards = '/app/market/cards';
  static const String marketCreators = '/app/market/creators';
  static const String newsroom = '/app/newsroom';
  static const String world = '/app/world';
  static const String worldRegens = '/app/world/regens';
  static const String worldFederations = '/app/world/federations';
  static const String worldAwards = '/app/world/awards';
  static const String wallet = '/app/wallet';
  static const String walletOrders = '/app/wallet/orders';
  static const String walletHoldings = '/app/wallet/holdings';
  static const String walletDeposit = '/app/wallet/deposit';
  static const String walletWithdraw = '/app/wallet/withdraw';
  static const String walletJackpot = '/app/wallet/jackpot';
  static const String walletTraderDesk = '/app/wallet/trader-desk';
  static const String studio = '/app/studio';
  static const String community = '/app/community';
  static const String you = '/app/you';
  static const String youSettings = '/app/you/settings';
  static const String youKyc = '/app/you/kyc';
  static const String youSupport = '/app/you/support';
  static const String youRewards = '/app/you/rewards';
  static const String admin = '/admin';
  static const String adminQueues = '/admin/queues';
  static const String adminOwnerReviews = '/admin/owner-reviews';
  static const String signIn = '/auth/login';

  static String clubRoot(String clubId) => '/app/club/${_cleanId(clubId)}';
  static String clubSquad(String clubId) =>
      '${clubRoot(clubId)}/squad';
  static String clubLineup(String clubId) =>
      '${clubRoot(clubId)}/squad/lineup';
  static String clubStaff(String clubId) =>
      '${clubRoot(clubId)}/staff';
  static String clubAcademy(String clubId) =>
      '${clubRoot(clubId)}/academy';
  static String clubRecruitment(String clubId) =>
      '${clubRoot(clubId)}/recruitment';
  static String clubTransfers(String clubId) =>
      '${clubRoot(clubId)}/transfers';
  static String clubTransferOffer(String clubId, String offerId) =>
      '${clubRoot(clubId)}/transfers/offers/${_cleanId(offerId)}';
  static String clubFinance(String clubId) =>
      '${clubRoot(clubId)}/finance';
  static String clubBoardroom(String clubId) =>
      '${clubRoot(clubId)}/boardroom';
  static String clubIdentity(String clubId) =>
      '${clubRoot(clubId)}/identity';

  static String inboxItem(String itemId) => '/app/inbox/${_cleanId(itemId)}';
  static String matchdayCompetition(String competitionId) =>
      '/app/matchday/competitions/${_cleanId(competitionId)}';
  static String matchdayMatch(String matchKey) =>
      '/app/matchday/match/${_cleanId(matchKey)}';
  static String newsroomArticle(String articleId) =>
      '/app/newsroom/${_cleanId(articleId)}';
  static String worldClub(String clubId) =>
      '/app/world/clubs/${_cleanId(clubId)}';
  static String worldFederation(String federationId) =>
      '/app/world/federations/${_cleanId(federationId)}';
  static String playerProfile(String playerId) =>
      '/players/${_cleanId(playerId)}';

  static String _cleanId(String raw) => Uri.encodeComponent(raw.trim());
}

@immutable
class GtexRouteAliasResolution {
  const GtexRouteAliasResolution({
    required this.inputPath,
    required this.canonicalPath,
    required this.isLegacyAlias,
  });

  final String inputPath;
  final String canonicalPath;
  final bool isLegacyAlias;
}

class GtexRouteAliasTable {
  const GtexRouteAliasTable._();

  static const String defaultClubPlaceholder = 'active';

  static const Map<String, String> _exactAliases = <String, String>{
    '/': GtexCanonicalRoutes.home,
    '/home': GtexCanonicalRoutes.home,
    '/app': GtexCanonicalRoutes.home,
    '/app/play': GtexCanonicalRoutes.matchday,
    '/app/play/overview': GtexCanonicalRoutes.matchday,
    '/app/play/fixtures': GtexCanonicalRoutes.matchdayFixtures,
    '/app/competitions': GtexCanonicalRoutes.matchday,
    '/competitions': GtexCanonicalRoutes.matchday,
    '/competitions/streamer/engine': GtexCanonicalRoutes.matchday,
    '/matches': GtexCanonicalRoutes.matchday,
    '/matches/native-3d': GtexCanonicalRoutes.matchday,
    '/matches/spectate': GtexCanonicalRoutes.matchday,
    '/matches/simulate': GtexCanonicalRoutes.matchday,
    '/national-team': GtexCanonicalRoutes.matchdayNational,
    '/national-teams': GtexCanonicalRoutes.matchdayNational,
    '/app/transfer-hub': GtexCanonicalRoutes.marketShares,
    '/app/player-market': GtexCanonicalRoutes.marketShares,
    '/app/player-cards': GtexCanonicalRoutes.marketCards,
    '/player-cards': GtexCanonicalRoutes.marketCards,
    '/creator-share-market': GtexCanonicalRoutes.marketCreators,
    '/app/regens': GtexCanonicalRoutes.worldRegens,
    '/app/regen-universe': GtexCanonicalRoutes.worldRegens,
    '/world': GtexCanonicalRoutes.world,
    '/world/regens': GtexCanonicalRoutes.worldRegens,
    '/world/federations': GtexCanonicalRoutes.worldFederations,
    '/app/capital': GtexCanonicalRoutes.wallet,
    '/app/capital/orders': GtexCanonicalRoutes.walletOrders,
    '/app/capital/holdings': GtexCanonicalRoutes.walletHoldings,
    '/app/orders': GtexCanonicalRoutes.walletOrders,
    '/app/holdings': GtexCanonicalRoutes.walletHoldings,
    '/app/portfolio': GtexCanonicalRoutes.walletHoldings,
    '/app/coin-traders': GtexCanonicalRoutes.walletTraderDesk,
    '/app/trader-dashboard': GtexCanonicalRoutes.walletTraderDesk,
    '/app/capital/coin-traders': GtexCanonicalRoutes.walletTraderDesk,
    '/app/capital/trader-dashboard': GtexCanonicalRoutes.walletTraderDesk,
    '/gtex/jackpot': GtexCanonicalRoutes.walletJackpot,
    '/news': GtexCanonicalRoutes.newsroom,
    '/owner/newsroom': GtexCanonicalRoutes.newsroom,
    '/owner/inbox': GtexCanonicalRoutes.inbox,
    '/app/hub': GtexCanonicalRoutes.studio,
    '/app/social': GtexCanonicalRoutes.community,
    '/clips': GtexCanonicalRoutes.community,
    '/profile': GtexCanonicalRoutes.you,
    '/profile/login': GtexCanonicalRoutes.signIn,
    '/profile/admin': GtexCanonicalRoutes.admin,
    '/settings': GtexCanonicalRoutes.youSettings,
    '/kyc': GtexCanonicalRoutes.youKyc,
    '/support': GtexCanonicalRoutes.youSupport,
    '/tasks': GtexCanonicalRoutes.youRewards,
    '/owner/admin': GtexCanonicalRoutes.adminOwnerReviews,
  };

  /// Resolves any raw path (canonical or legacy alias) into its canonical
  /// Document E3 route.
  static GtexRouteAliasResolution resolve(
    String? rawPath, {
    String? activeClubId,
  }) {
    final String trimmed = (rawPath ?? '').trim();
    if (trimmed.isEmpty) {
      return const GtexRouteAliasResolution(
        inputPath: '',
        canonicalPath: GtexCanonicalRoutes.home,
        isLegacyAlias: true,
      );
    }

    final String normalizedInput =
        trimmed.startsWith('/') ? trimmed : '/$trimmed';
    final Uri? uri = Uri.tryParse(normalizedInput);
    if (uri == null) {
      return GtexRouteAliasResolution(
        inputPath: trimmed,
        canonicalPath: GtexCanonicalRoutes.home,
        isLegacyAlias: true,
      );
    }

    final String cleanPath = _stripTrailingSlash(uri.path);
    final String clubKey =
        (activeClubId ?? '').trim().isEmpty
            ? defaultClubPlaceholder
            : activeClubId!.trim();

    // Check query-driven legacy market modes first (e.g., `/app/market?mode=ownership`).
    if (cleanPath == '/app/market' || cleanPath == '/market') {
      final String? mode =
          uri.queryParameters['mode'] ?? uri.queryParameters['tab'];
      if (mode == 'ownership' || mode == 'holdings') {
        return GtexRouteAliasResolution(
          inputPath: trimmed,
          canonicalPath: GtexCanonicalRoutes.walletHoldings,
          isLegacyAlias: true,
        );
      }
      if (mode == 'cards') {
        return GtexRouteAliasResolution(
          inputPath: trimmed,
          canonicalPath: GtexCanonicalRoutes.marketCards,
          isLegacyAlias: true,
        );
      }
      if (cleanPath == '/market') {
        return GtexRouteAliasResolution(
          inputPath: trimmed,
          canonicalPath: GtexCanonicalRoutes.market,
          isLegacyAlias: true,
        );
      }
      return GtexRouteAliasResolution(
        inputPath: trimmed,
        canonicalPath: GtexCanonicalRoutes.market,
        isLegacyAlias: false,
      );
    }

    if (_exactAliases.containsKey(cleanPath)) {
      return GtexRouteAliasResolution(
        inputPath: trimmed,
        canonicalPath: _exactAliases[cleanPath]!,
        isLegacyAlias: cleanPath != _exactAliases[cleanPath],
      );
    }

    // Club-scoped legacy aliases.
    if (cleanPath == '/app/club' || cleanPath == '/club') {
      return GtexRouteAliasResolution(
        inputPath: trimmed,
        canonicalPath: GtexCanonicalRoutes.clubRoot(clubKey),
        isLegacyAlias: true,
      );
    }
    if (cleanPath == '/lineup') {
      return GtexRouteAliasResolution(
        inputPath: trimmed,
        canonicalPath: GtexCanonicalRoutes.clubLineup(clubKey),
        isLegacyAlias: true,
      );
    }
    if (cleanPath == '/coaches' || cleanPath == '/managers') {
      return GtexRouteAliasResolution(
        inputPath: trimmed,
        canonicalPath: GtexCanonicalRoutes.clubStaff(clubKey),
        isLegacyAlias: true,
      );
    }
    if (cleanPath == '/market/transfers' ||
        cleanPath == '/football/transfer-center' ||
        cleanPath == '/app/transfers') {
      return GtexRouteAliasResolution(
        inputPath: trimmed,
        canonicalPath: GtexCanonicalRoutes.clubTransfers(clubKey),
        isLegacyAlias: true,
      );
    }

    final List<String> segments =
        uri.pathSegments.where((String s) => s.isNotEmpty).toList();

    // Pattern: `/matches/viewer/:matchKey`, `/matches/broadcast/:matchKey`, `/matches/3d/:matchKey`
    if (segments.length == 3 &&
        segments[0] == 'matches' &&
        (segments[1] == 'viewer' ||
            segments[1] == 'broadcast' ||
            segments[1] == '3d')) {
      return GtexRouteAliasResolution(
        inputPath: trimmed,
        canonicalPath: GtexCanonicalRoutes.matchdayMatch(segments[2]),
        isLegacyAlias: true,
      );
    }

    // Pattern: `/competitions/:family/:id` or `/competitions/:id`
    if (segments.length == 3 &&
        segments[0] == 'competitions' &&
        segments[1] != 'streamer') {
      return GtexRouteAliasResolution(
        inputPath: trimmed,
        canonicalPath: GtexCanonicalRoutes.matchdayCompetition(segments[2]),
        isLegacyAlias: true,
      );
    }
    if (segments.length == 2 &&
        segments[0] == 'competitions' &&
        segments[1] != 'create') {
      return GtexRouteAliasResolution(
        inputPath: trimmed,
        canonicalPath: GtexCanonicalRoutes.matchdayCompetition(segments[1]),
        isLegacyAlias: true,
      );
    }

    // Pattern: `/world/federations/:federationId`
    if (segments.length == 3 &&
        segments[0] == 'world' &&
        segments[1] == 'federations') {
      return GtexRouteAliasResolution(
        inputPath: trimmed,
        canonicalPath: GtexCanonicalRoutes.worldFederation(segments[2]),
        isLegacyAlias: true,
      );
    }

    // Pattern: `/market/transfers/:listingId`
    if (segments.length == 3 &&
        segments[0] == 'market' &&
        segments[1] == 'transfers') {
      return GtexRouteAliasResolution(
        inputPath: trimmed,
        canonicalPath: GtexCanonicalRoutes.clubTransferOffer(
          clubKey,
          segments[2],
        ),
        isLegacyAlias: true,
      );
    }

    // Pattern: `/clubs/:clubId/identity*` or `/clubs/:clubId`
    if (segments.length >= 2 && segments[0] == 'clubs') {
      final String targetClubId = segments[1];
      if (segments.length >= 3 && segments[2] == 'identity') {
        return GtexRouteAliasResolution(
          inputPath: trimmed,
          canonicalPath: GtexCanonicalRoutes.clubIdentity(targetClubId),
          isLegacyAlias: true,
        );
      }
      return GtexRouteAliasResolution(
        inputPath: trimmed,
        canonicalPath: GtexCanonicalRoutes.clubRoot(targetClubId),
        isLegacyAlias: true,
      );
    }

    // Pattern: `/players/:playerId/profile` -> `/players/:playerId`
    if (segments.length == 3 &&
        segments[0] == 'players' &&
        segments[2] == 'profile') {
      return GtexRouteAliasResolution(
        inputPath: trimmed,
        canonicalPath: GtexCanonicalRoutes.playerProfile(segments[1]),
        isLegacyAlias: true,
      );
    }

    return GtexRouteAliasResolution(
      inputPath: trimmed,
      canonicalPath: cleanPath,
      isLegacyAlias: false,
    );
  }

  static String _stripTrailingSlash(String path) {
    if (path.length > 1 && path.endsWith('/')) {
      return path.substring(0, path.length - 1);
    }
    return path;
  }
}
