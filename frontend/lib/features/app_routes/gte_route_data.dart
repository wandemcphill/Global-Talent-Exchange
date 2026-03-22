import 'package:gte_frontend/features/club_identity/trophies/data/trophy_item_dto.dart';

class GteAppRouteRegistration {
  const GteAppRouteRegistration({
    required this.name,
    required this.path,
  });

  final String name;
  final String path;
}

class GteAppRouteNames {
  const GteAppRouteNames._();

  static const String competitionsDiscovery = 'competitions.discovery';
  static const String competitionCreate = 'competitions.create';
  static const String competitionDetail = 'competitions.detail';
  static const String competitionJoin = 'competitions.join';
  static const String competitionShare = 'competitions.share';
  static const String competitionWorldSuperCup = 'competitions.world-super-cup';
  static const String streamerTournamentsList = 'streamer-tournaments.list';
  static const String streamerTournamentDetail = 'streamer-tournaments.detail';
  static const String fanPredictionMatch = 'fan-predictions.match';
  static const String playerCardsBrowse = 'player-cards.browse';
  static const String playerCardDetail = 'player-cards.detail';
  static const String playerCardsInventory = 'player-cards.inventory';
  static const String creatorShareMarketClub = 'creator-share-market.club';
  static const String creatorShareMarketAdminControl =
      'creator-share-market.admin-control';
  static const String clubSaleMarketListings = 'club-sale-market.listings';
  static const String clubSaleMarketDetail = 'club-sale-market.detail';
  static const String clubSaleMarketOwnerOffers =
      'club-sale-market.owner-offers';
  static const String worldOverview = 'world.overview';
  static const String worldClubContext = 'world.club-context';
  static const String worldCompetitionContext = 'world.competition-context';
  static const String nationalTeamCompetitions = 'national-team.competitions';
  static const String nationalTeamEntry = 'national-team.entry';
  static const String nationalTeamHistory = 'national-team.history';
  static const String footballTransferCenter = 'football.transfer-center';
  static const String creatorStadiumClub = 'creator-stadium.club';
  static const String creatorStadiumMatch = 'creator-stadium.match';
  static const String creatorStadiumAdminControl =
      'creator-stadium.admin-control';
  static const String creatorLeagueFinancialReport =
      'creator-league.financial-report';
  static const String creatorLeagueSettlements = 'creator-league.settlements';
  static const String giftStabilizer = 'gift-stabilizer';

  static const String clubIdentityJerseys = 'club.identity.jerseys';
  static const String clubIdentityReputationOverview =
      'club.identity.reputation.overview';
  static const String clubIdentityReputationHistory =
      'club.identity.reputation.history';
  static const String clubIdentityReputationLeaderboard =
      'club.identity.reputation.leaderboard';
  static const String clubIdentityTrophyCabinet =
      'club.identity.trophies.cabinet';
  static const String clubIdentityTrophyTimeline =
      'club.identity.trophies.timeline';
  static const String clubIdentityTrophyLeaderboard =
      'club.identity.trophies.leaderboard';
  static const String clubIdentityDynastyOverview =
      'club.identity.dynasty.overview';
  static const String clubIdentityDynastyHistory =
      'club.identity.dynasty.history';
  static const String clubIdentityDynastyLeaderboard =
      'club.identity.dynasty.leaderboard';
  static const String clubIdentityReplays = 'club.identity.replays';
}

class GteAppRouteCatalog {
  const GteAppRouteCatalog._();

  static const List<GteAppRouteRegistration> registrations =
      <GteAppRouteRegistration>[
    GteAppRouteRegistration(
      name: GteAppRouteNames.competitionsDiscovery,
      path: '/competitions',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.competitionCreate,
      path: '/competitions/create',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.competitionWorldSuperCup,
      path: '/competitions/world-super-cup',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.competitionDetail,
      path: '/competitions/:competitionId',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.competitionJoin,
      path: '/competitions/:competitionId/join',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.competitionShare,
      path: '/competitions/:competitionId/share',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.streamerTournamentsList,
      path: '/streamer-tournaments',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.streamerTournamentDetail,
      path: '/streamer-tournaments/:tournamentId',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.fanPredictionMatch,
      path: '/fan-predictions/matches/:matchId',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.playerCardsBrowse,
      path: '/player-cards',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.playerCardDetail,
      path: '/player-cards/players/:playerId',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.playerCardsInventory,
      path: '/player-cards/inventory',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.creatorShareMarketClub,
      path: '/creator-share-market/clubs/:clubId',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.creatorShareMarketAdminControl,
      path: '/admin/creator-share-market/control',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.clubSaleMarketListings,
      path: '/clubs/sale-market',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.clubSaleMarketDetail,
      path: '/clubs/:clubId/sale-market',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.clubSaleMarketOwnerOffers,
      path: '/clubs/:clubId/sale-market/offers',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.worldOverview,
      path: '/world',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.worldClubContext,
      path: '/world/clubs/:clubId',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.worldCompetitionContext,
      path: '/world/competitions/:competitionId',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.nationalTeamCompetitions,
      path: '/national-team',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.nationalTeamEntry,
      path: '/national-team/entries/:entryId',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.nationalTeamHistory,
      path: '/national-team/history',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.footballTransferCenter,
      path: '/football/transfer-center',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.creatorStadiumClub,
      path: '/creator-stadium/clubs/:clubId',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.creatorStadiumMatch,
      path: '/creator-stadium/matches/:matchId',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.creatorStadiumAdminControl,
      path: '/admin/creator-stadium/control',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.creatorLeagueFinancialReport,
      path: '/admin/creator-league/financial-report',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.creatorLeagueSettlements,
      path: '/admin/creator-league/settlements',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.giftStabilizer,
      path: '/admin/gift-stabilizer',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.clubIdentityJerseys,
      path: '/clubs/:clubId/identity/jerseys',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.clubIdentityReputationOverview,
      path: '/clubs/:clubId/identity/reputation',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.clubIdentityReputationHistory,
      path: '/clubs/:clubId/identity/reputation/history',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.clubIdentityReputationLeaderboard,
      path: '/clubs/:clubId/identity/reputation/leaderboard',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.clubIdentityTrophyCabinet,
      path: '/clubs/:clubId/identity/trophies',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.clubIdentityTrophyTimeline,
      path: '/clubs/:clubId/identity/trophies/timeline',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.clubIdentityTrophyLeaderboard,
      path: '/clubs/:clubId/identity/trophies/leaderboard',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.clubIdentityDynastyOverview,
      path: '/clubs/:clubId/identity/dynasty',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.clubIdentityDynastyHistory,
      path: '/clubs/:clubId/identity/dynasty/history',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.clubIdentityDynastyLeaderboard,
      path: '/clubs/:clubId/identity/dynasty/leaderboard',
    ),
    GteAppRouteRegistration(
      name: GteAppRouteNames.clubIdentityReplays,
      path: '/clubs/:clubId/identity/replays',
    ),
  ];
}

enum GteReplaySurface {
  matchIntro,
  standingsCard,
  replayCard,
  worldSuperCupCard,
}

enum GteTransferCenterTab {
  windows,
  media,
  calendar,
}

extension GteReplaySurfaceX on GteReplaySurface {
  String get slug {
    switch (this) {
      case GteReplaySurface.matchIntro:
        return 'match-intro';
      case GteReplaySurface.standingsCard:
        return 'standings-card';
      case GteReplaySurface.replayCard:
        return 'replay-card';
      case GteReplaySurface.worldSuperCupCard:
        return 'world-super-cup-card';
    }
  }
}

extension GteTransferCenterTabX on GteTransferCenterTab {
  String get slug {
    switch (this) {
      case GteTransferCenterTab.windows:
        return 'windows';
      case GteTransferCenterTab.media:
        return 'media';
      case GteTransferCenterTab.calendar:
        return 'calendar';
    }
  }
}

GteReplaySurface gteReplaySurfaceFromRaw(String? raw) {
  switch (raw?.trim().toLowerCase()) {
    case 'match-intro':
      return GteReplaySurface.matchIntro;
    case 'standings-card':
      return GteReplaySurface.standingsCard;
    case 'world-super-cup-card':
      return GteReplaySurface.worldSuperCupCard;
    case 'replay-card':
    default:
      return GteReplaySurface.replayCard;
  }
}

GteTransferCenterTab gteTransferCenterTabFromRaw(String? raw) {
  switch (raw?.trim().toLowerCase()) {
    case 'media':
      return GteTransferCenterTab.media;
    case 'calendar':
      return GteTransferCenterTab.calendar;
    case 'windows':
    default:
      return GteTransferCenterTab.windows;
  }
}

TrophyScopeFilter gteTrophyScopeFilterFromRaw(String? raw) {
  switch (raw?.trim().toLowerCase()) {
    case 'senior':
      return TrophyScopeFilter.senior;
    case 'academy':
      return TrophyScopeFilter.academy;
    case 'all':
    default:
      return TrophyScopeFilter.all;
  }
}

abstract class GteAppRouteData {
  const GteAppRouteData();

  String get name;

  Uri toUri();
}

abstract class GteClubScopedRouteData extends GteAppRouteData {
  const GteClubScopedRouteData({
    required this.clubId,
    this.clubName,
  });

  final String clubId;
  final String? clubName;

  Map<String, String> buildClubQueryParameters({
    Map<String, String> extras = const <String, String>{},
  }) {
    final Map<String, String> query = <String, String>{
      ...extras,
    };
    final String? resolvedClubName = _nonEmpty(clubName);
    if (resolvedClubName != null) {
      query['clubName'] = resolvedClubName;
    }
    return query;
  }
}

class CompetitionsDiscoveryRouteData extends GteAppRouteData {
  const CompetitionsDiscoveryRouteData({
    this.highlight,
  });

  final String? highlight;

  @override
  String get name => GteAppRouteNames.competitionsDiscovery;

  @override
  Uri toUri() {
    final String? resolvedHighlight = _nonEmpty(highlight);
    return _buildUri(
      path: '/competitions',
      queryParameters: resolvedHighlight == null
          ? const <String, String>{}
          : <String, String>{'highlight': resolvedHighlight},
    );
  }
}

class CompetitionCreateRouteData extends GteAppRouteData {
  const CompetitionCreateRouteData();

  @override
  String get name => GteAppRouteNames.competitionCreate;

  @override
  Uri toUri() => _buildUri(path: '/competitions/create');
}

class CompetitionWorldSuperCupRouteData extends GteAppRouteData {
  const CompetitionWorldSuperCupRouteData();

  @override
  String get name => GteAppRouteNames.competitionWorldSuperCup;

  @override
  Uri toUri() => _buildUri(path: '/competitions/world-super-cup');
}

class CompetitionDetailRouteData extends GteAppRouteData {
  const CompetitionDetailRouteData({
    required this.competitionId,
    this.inviteCode,
  });

  final String competitionId;
  final String? inviteCode;

  @override
  String get name => GteAppRouteNames.competitionDetail;

  @override
  Uri toUri() {
    final String? resolvedInviteCode = _nonEmpty(inviteCode);
    return _buildUri(
      path: '/competitions/$competitionId',
      queryParameters: resolvedInviteCode == null
          ? const <String, String>{}
          : <String, String>{'inviteCode': resolvedInviteCode},
    );
  }
}

class CompetitionJoinRouteData extends GteAppRouteData {
  const CompetitionJoinRouteData({
    required this.competitionId,
    this.inviteCode,
  });

  final String competitionId;
  final String? inviteCode;

  @override
  String get name => GteAppRouteNames.competitionJoin;

  @override
  Uri toUri() {
    final String? resolvedInviteCode = _nonEmpty(inviteCode);
    return _buildUri(
      path: '/competitions/$competitionId/join',
      queryParameters: resolvedInviteCode == null
          ? const <String, String>{}
          : <String, String>{'inviteCode': resolvedInviteCode},
    );
  }
}

class CompetitionShareRouteData extends GteAppRouteData {
  const CompetitionShareRouteData({
    required this.competitionId,
  });

  final String competitionId;

  @override
  String get name => GteAppRouteNames.competitionShare;

  @override
  Uri toUri() => _buildUri(path: '/competitions/$competitionId/share');
}

class ClubIdentityJerseysRouteData extends GteClubScopedRouteData {
  const ClubIdentityJerseysRouteData({
    required super.clubId,
    super.clubName,
  });

  @override
  String get name => GteAppRouteNames.clubIdentityJerseys;

  @override
  Uri toUri() => _buildUri(
        path: '/clubs/$clubId/identity/jerseys',
        queryParameters: buildClubQueryParameters(),
      );
}

class ClubReputationOverviewRouteData extends GteClubScopedRouteData {
  const ClubReputationOverviewRouteData({
    required super.clubId,
    super.clubName,
  });

  @override
  String get name => GteAppRouteNames.clubIdentityReputationOverview;

  @override
  Uri toUri() => _buildUri(
        path: '/clubs/$clubId/identity/reputation',
        queryParameters: buildClubQueryParameters(),
      );
}

class ClubReputationHistoryRouteData extends GteClubScopedRouteData {
  const ClubReputationHistoryRouteData({
    required super.clubId,
    super.clubName,
  });

  @override
  String get name => GteAppRouteNames.clubIdentityReputationHistory;

  @override
  Uri toUri() => _buildUri(
        path: '/clubs/$clubId/identity/reputation/history',
        queryParameters: buildClubQueryParameters(),
      );
}

class ClubReputationLeaderboardRouteData extends GteClubScopedRouteData {
  const ClubReputationLeaderboardRouteData({
    required super.clubId,
    super.clubName,
  });

  @override
  String get name => GteAppRouteNames.clubIdentityReputationLeaderboard;

  @override
  Uri toUri() => _buildUri(
        path: '/clubs/$clubId/identity/reputation/leaderboard',
        queryParameters: buildClubQueryParameters(),
      );
}

class ClubTrophyCabinetRouteData extends GteClubScopedRouteData {
  const ClubTrophyCabinetRouteData({
    required super.clubId,
    super.clubName,
    this.filter = TrophyScopeFilter.all,
  });

  final TrophyScopeFilter filter;

  @override
  String get name => GteAppRouteNames.clubIdentityTrophyCabinet;

  @override
  Uri toUri() => _buildUri(
        path: '/clubs/$clubId/identity/trophies',
        queryParameters: buildClubQueryParameters(
          extras: filter == TrophyScopeFilter.all
              ? const <String, String>{}
              : <String, String>{'scope': filter.name},
        ),
      );
}

class ClubTrophyTimelineRouteData extends GteClubScopedRouteData {
  const ClubTrophyTimelineRouteData({
    required super.clubId,
    super.clubName,
    this.filter = TrophyScopeFilter.all,
  });

  final TrophyScopeFilter filter;

  @override
  String get name => GteAppRouteNames.clubIdentityTrophyTimeline;

  @override
  Uri toUri() => _buildUri(
        path: '/clubs/$clubId/identity/trophies/timeline',
        queryParameters: buildClubQueryParameters(
          extras: filter == TrophyScopeFilter.all
              ? const <String, String>{}
              : <String, String>{'scope': filter.name},
        ),
      );
}

class ClubTrophyLeaderboardRouteData extends GteClubScopedRouteData {
  const ClubTrophyLeaderboardRouteData({
    required super.clubId,
    super.clubName,
    this.filter = TrophyScopeFilter.all,
  });

  final TrophyScopeFilter filter;

  @override
  String get name => GteAppRouteNames.clubIdentityTrophyLeaderboard;

  @override
  Uri toUri() => _buildUri(
        path: '/clubs/$clubId/identity/trophies/leaderboard',
        queryParameters: buildClubQueryParameters(
          extras: filter == TrophyScopeFilter.all
              ? const <String, String>{}
              : <String, String>{'scope': filter.name},
        ),
      );
}

class ClubDynastyOverviewRouteData extends GteClubScopedRouteData {
  const ClubDynastyOverviewRouteData({
    required super.clubId,
    super.clubName,
  });

  @override
  String get name => GteAppRouteNames.clubIdentityDynastyOverview;

  @override
  Uri toUri() => _buildUri(
        path: '/clubs/$clubId/identity/dynasty',
        queryParameters: buildClubQueryParameters(),
      );
}

class ClubDynastyHistoryRouteData extends GteClubScopedRouteData {
  const ClubDynastyHistoryRouteData({
    required super.clubId,
    super.clubName,
  });

  @override
  String get name => GteAppRouteNames.clubIdentityDynastyHistory;

  @override
  Uri toUri() => _buildUri(
        path: '/clubs/$clubId/identity/dynasty/history',
        queryParameters: buildClubQueryParameters(),
      );
}

class ClubDynastyLeaderboardRouteData extends GteClubScopedRouteData {
  const ClubDynastyLeaderboardRouteData({
    required super.clubId,
    super.clubName,
  });

  @override
  String get name => GteAppRouteNames.clubIdentityDynastyLeaderboard;

  @override
  Uri toUri() => _buildUri(
        path: '/clubs/$clubId/identity/dynasty/leaderboard',
        queryParameters: buildClubQueryParameters(),
      );
}

class ClubReplaysRouteData extends GteClubScopedRouteData {
  const ClubReplaysRouteData({
    required super.clubId,
    super.clubName,
    this.surface = GteReplaySurface.replayCard,
  });

  final GteReplaySurface surface;

  @override
  String get name => GteAppRouteNames.clubIdentityReplays;

  @override
  Uri toUri() => _buildUri(
        path: '/clubs/$clubId/identity/replays',
        queryParameters: buildClubQueryParameters(
          extras: surface == GteReplaySurface.replayCard
              ? const <String, String>{}
              : <String, String>{'surface': surface.slug},
        ),
      );
}

class StreamerTournamentsListRouteData extends GteAppRouteData {
  const StreamerTournamentsListRouteData();

  @override
  String get name => GteAppRouteNames.streamerTournamentsList;

  @override
  Uri toUri() => _buildUri(path: '/streamer-tournaments');
}

class StreamerTournamentDetailRouteData extends GteAppRouteData {
  const StreamerTournamentDetailRouteData({
    required this.tournamentId,
  });

  final String tournamentId;

  @override
  String get name => GteAppRouteNames.streamerTournamentDetail;

  @override
  Uri toUri() => _buildUri(path: '/streamer-tournaments/$tournamentId');
}

class FanPredictionMatchRouteData extends GteAppRouteData {
  const FanPredictionMatchRouteData({
    required this.matchId,
  });

  final String matchId;

  @override
  String get name => GteAppRouteNames.fanPredictionMatch;

  @override
  Uri toUri() => _buildUri(path: '/fan-predictions/matches/$matchId');
}

class PlayerCardsBrowseRouteData extends GteAppRouteData {
  const PlayerCardsBrowseRouteData();

  @override
  String get name => GteAppRouteNames.playerCardsBrowse;

  @override
  Uri toUri() => _buildUri(path: '/player-cards');
}

class PlayerCardDetailRouteData extends GteAppRouteData {
  const PlayerCardDetailRouteData({
    required this.playerId,
  });

  final String playerId;

  @override
  String get name => GteAppRouteNames.playerCardDetail;

  @override
  Uri toUri() => _buildUri(path: '/player-cards/players/$playerId');
}

class PlayerCardsInventoryRouteData extends GteAppRouteData {
  const PlayerCardsInventoryRouteData();

  @override
  String get name => GteAppRouteNames.playerCardsInventory;

  @override
  Uri toUri() => _buildUri(path: '/player-cards/inventory');
}

class CreatorShareMarketClubRouteData extends GteClubScopedRouteData {
  const CreatorShareMarketClubRouteData({
    required super.clubId,
    super.clubName,
  });

  @override
  String get name => GteAppRouteNames.creatorShareMarketClub;

  @override
  Uri toUri() => _buildUri(
        path: '/creator-share-market/clubs/$clubId',
        queryParameters: buildClubQueryParameters(),
      );
}

class CreatorShareMarketAdminControlRouteData extends GteAppRouteData {
  const CreatorShareMarketAdminControlRouteData();

  @override
  String get name => GteAppRouteNames.creatorShareMarketAdminControl;

  @override
  Uri toUri() => _buildUri(path: '/admin/creator-share-market/control');
}

class ClubSaleMarketListingsRouteData extends GteAppRouteData {
  const ClubSaleMarketListingsRouteData();

  @override
  String get name => GteAppRouteNames.clubSaleMarketListings;

  @override
  Uri toUri() => _buildUri(path: '/clubs/sale-market');
}

class ClubSaleMarketDetailRouteData extends GteClubScopedRouteData {
  const ClubSaleMarketDetailRouteData({
    required super.clubId,
    super.clubName,
  });

  @override
  String get name => GteAppRouteNames.clubSaleMarketDetail;

  @override
  Uri toUri() => _buildUri(
        path: '/clubs/$clubId/sale-market',
        queryParameters: buildClubQueryParameters(),
      );
}

class ClubSaleMarketOwnerOffersRouteData extends GteClubScopedRouteData {
  const ClubSaleMarketOwnerOffersRouteData({
    required super.clubId,
    super.clubName,
  });

  @override
  String get name => GteAppRouteNames.clubSaleMarketOwnerOffers;

  @override
  Uri toUri() => _buildUri(
        path: '/clubs/$clubId/sale-market/offers',
        queryParameters: buildClubQueryParameters(),
      );
}

class WorldOverviewRouteData extends GteAppRouteData {
  const WorldOverviewRouteData();

  @override
  String get name => GteAppRouteNames.worldOverview;

  @override
  Uri toUri() => _buildUri(path: '/world');
}

class WorldClubContextRouteData extends GteClubScopedRouteData {
  const WorldClubContextRouteData({
    required super.clubId,
    super.clubName,
  });

  @override
  String get name => GteAppRouteNames.worldClubContext;

  @override
  Uri toUri() => _buildUri(
        path: '/world/clubs/$clubId',
        queryParameters: buildClubQueryParameters(),
      );
}

class WorldCompetitionContextRouteData extends GteAppRouteData {
  const WorldCompetitionContextRouteData({
    required this.competitionId,
  });

  final String competitionId;

  @override
  String get name => GteAppRouteNames.worldCompetitionContext;

  @override
  Uri toUri() => _buildUri(path: '/world/competitions/$competitionId');
}

class NationalTeamCompetitionsRouteData extends GteAppRouteData {
  const NationalTeamCompetitionsRouteData();

  @override
  String get name => GteAppRouteNames.nationalTeamCompetitions;

  @override
  Uri toUri() => _buildUri(path: '/national-team');
}

class NationalTeamEntryRouteData extends GteAppRouteData {
  const NationalTeamEntryRouteData({
    required this.entryId,
  });

  final String entryId;

  @override
  String get name => GteAppRouteNames.nationalTeamEntry;

  @override
  Uri toUri() => _buildUri(path: '/national-team/entries/$entryId');
}

class NationalTeamHistoryRouteData extends GteAppRouteData {
  const NationalTeamHistoryRouteData();

  @override
  String get name => GteAppRouteNames.nationalTeamHistory;

  @override
  Uri toUri() => _buildUri(path: '/national-team/history');
}

class FootballTransferCenterRouteData extends GteAppRouteData {
  const FootballTransferCenterRouteData({
    this.tab = GteTransferCenterTab.windows,
  });

  final GteTransferCenterTab tab;

  @override
  String get name => GteAppRouteNames.footballTransferCenter;

  @override
  Uri toUri() => _buildUri(
        path: '/football/transfer-center',
        queryParameters: tab == GteTransferCenterTab.windows
            ? const <String, String>{}
            : <String, String>{'tab': tab.slug},
      );
}

class CreatorStadiumClubRouteData extends GteClubScopedRouteData {
  const CreatorStadiumClubRouteData({
    required super.clubId,
    super.clubName,
    this.seasonId,
  });

  final String? seasonId;

  @override
  String get name => GteAppRouteNames.creatorStadiumClub;

  @override
  Uri toUri() => _buildUri(
        path: '/creator-stadium/clubs/$clubId',
        queryParameters: buildClubQueryParameters(
          extras: seasonId == null
              ? const <String, String>{}
              : <String, String>{'seasonId': seasonId!},
        ),
      );
}

class CreatorStadiumMatchRouteData extends GteAppRouteData {
  const CreatorStadiumMatchRouteData({
    required this.matchId,
  });

  final String matchId;

  @override
  String get name => GteAppRouteNames.creatorStadiumMatch;

  @override
  Uri toUri() => _buildUri(path: '/creator-stadium/matches/$matchId');
}

class CreatorStadiumAdminControlRouteData extends GteAppRouteData {
  const CreatorStadiumAdminControlRouteData();

  @override
  String get name => GteAppRouteNames.creatorStadiumAdminControl;

  @override
  Uri toUri() => _buildUri(path: '/admin/creator-stadium/control');
}

class CreatorLeagueFinancialReportRouteData extends GteAppRouteData {
  const CreatorLeagueFinancialReportRouteData({
    this.seasonId,
  });

  final String? seasonId;

  @override
  String get name => GteAppRouteNames.creatorLeagueFinancialReport;

  @override
  Uri toUri() => _buildUri(
        path: '/admin/creator-league/financial-report',
        queryParameters: seasonId == null
            ? const <String, String>{}
            : <String, String>{'seasonId': seasonId!},
      );
}

class CreatorLeagueSettlementsRouteData extends GteAppRouteData {
  const CreatorLeagueSettlementsRouteData({
    this.seasonId,
  });

  final String? seasonId;

  @override
  String get name => GteAppRouteNames.creatorLeagueSettlements;

  @override
  Uri toUri() => _buildUri(
        path: '/admin/creator-league/settlements',
        queryParameters: seasonId == null
            ? const <String, String>{}
            : <String, String>{'seasonId': seasonId!},
      );
}

class GiftStabilizerRouteData extends GteAppRouteData {
  const GiftStabilizerRouteData();

  @override
  String get name => GteAppRouteNames.giftStabilizer;

  @override
  Uri toUri() => _buildUri(path: '/admin/gift-stabilizer');
}

class GteNamedNavigationRequest {
  const GteNamedNavigationRequest({
    required this.routeName,
    this.pathParameters = const <String, String>{},
    this.queryParameters = const <String, String>{},
  });

  final String routeName;
  final Map<String, String> pathParameters;
  final Map<String, String> queryParameters;
}

class GteAppRouteParser {
  const GteAppRouteParser._();

  static GteAppRouteData? parse(Object? raw) {
    if (raw is GteAppRouteData) {
      return raw;
    }
    if (raw is GteNamedNavigationRequest) {
      return fromNamedRequest(
        raw.routeName,
        pathParameters: raw.pathParameters,
        queryParameters: raw.queryParameters,
      );
    }
    if (raw is Uri) {
      return fromUri(raw);
    }
    if (raw is String) {
      final String trimmed = raw.trim();
      if (trimmed.isEmpty) {
        return null;
      }
      if (_looksLikePath(trimmed) || _looksLikeDeepLink(trimmed)) {
        return fromUri(Uri.parse(trimmed));
      }
      return fromNamedRequest(trimmed);
    }
    return null;
  }

  static GteAppRouteData? fromNamedRequest(
    String routeName, {
    Map<String, String> pathParameters = const <String, String>{},
    Map<String, String> queryParameters = const <String, String>{},
  }) {
    final String normalized = normalizeRouteName(routeName);
    final String? clubId = _nonEmpty(pathParameters['clubId']);
    final String? clubName = _nonEmpty(queryParameters['clubName']);
    final String? seasonId = _nonEmpty(queryParameters['seasonId']);
    final TrophyScopeFilter filter =
        gteTrophyScopeFilterFromRaw(queryParameters['scope']);

    switch (normalized) {
      case GteAppRouteNames.competitionsDiscovery:
        return CompetitionsDiscoveryRouteData(
          highlight: _nonEmpty(queryParameters['highlight']),
        );
      case GteAppRouteNames.competitionCreate:
        return const CompetitionCreateRouteData();
      case GteAppRouteNames.competitionWorldSuperCup:
        return const CompetitionWorldSuperCupRouteData();
      case GteAppRouteNames.competitionDetail:
        final String? competitionId =
            _nonEmpty(pathParameters['competitionId']);
        if (competitionId == null) {
          return null;
        }
        return CompetitionDetailRouteData(
          competitionId: competitionId,
          inviteCode: _nonEmpty(queryParameters['inviteCode']),
        );
      case GteAppRouteNames.competitionJoin:
        final String? competitionId =
            _nonEmpty(pathParameters['competitionId']);
        if (competitionId == null) {
          return null;
        }
        return CompetitionJoinRouteData(
          competitionId: competitionId,
          inviteCode: _nonEmpty(queryParameters['inviteCode']),
        );
      case GteAppRouteNames.competitionShare:
        final String? competitionId =
            _nonEmpty(pathParameters['competitionId']);
        if (competitionId == null) {
          return null;
        }
        return CompetitionShareRouteData(
          competitionId: competitionId,
        );
      case GteAppRouteNames.streamerTournamentsList:
        return const StreamerTournamentsListRouteData();
      case GteAppRouteNames.streamerTournamentDetail:
        final String? tournamentId = _nonEmpty(pathParameters['tournamentId']);
        if (tournamentId == null) {
          return null;
        }
        return StreamerTournamentDetailRouteData(
          tournamentId: tournamentId,
        );
      case GteAppRouteNames.fanPredictionMatch:
        final String? matchId = _nonEmpty(pathParameters['matchId']);
        if (matchId == null) {
          return null;
        }
        return FanPredictionMatchRouteData(matchId: matchId);
      case GteAppRouteNames.playerCardsBrowse:
        return const PlayerCardsBrowseRouteData();
      case GteAppRouteNames.playerCardDetail:
        final String? playerId = _nonEmpty(pathParameters['playerId']);
        if (playerId == null) {
          return null;
        }
        return PlayerCardDetailRouteData(playerId: playerId);
      case GteAppRouteNames.playerCardsInventory:
        return const PlayerCardsInventoryRouteData();
      case GteAppRouteNames.creatorShareMarketClub:
        if (clubId == null) {
          return null;
        }
        return CreatorShareMarketClubRouteData(
          clubId: clubId,
          clubName: clubName,
        );
      case GteAppRouteNames.creatorShareMarketAdminControl:
        return const CreatorShareMarketAdminControlRouteData();
      case GteAppRouteNames.clubSaleMarketListings:
        return const ClubSaleMarketListingsRouteData();
      case GteAppRouteNames.clubSaleMarketDetail:
        if (clubId == null) {
          return null;
        }
        return ClubSaleMarketDetailRouteData(
          clubId: clubId,
          clubName: clubName,
        );
      case GteAppRouteNames.clubSaleMarketOwnerOffers:
        if (clubId == null) {
          return null;
        }
        return ClubSaleMarketOwnerOffersRouteData(
          clubId: clubId,
          clubName: clubName,
        );
      case GteAppRouteNames.worldOverview:
        return const WorldOverviewRouteData();
      case GteAppRouteNames.worldClubContext:
        if (clubId == null) {
          return null;
        }
        return WorldClubContextRouteData(
          clubId: clubId,
          clubName: clubName,
        );
      case GteAppRouteNames.worldCompetitionContext:
        final String? competitionId =
            _nonEmpty(pathParameters['competitionId']);
        if (competitionId == null) {
          return null;
        }
        return WorldCompetitionContextRouteData(
          competitionId: competitionId,
        );
      case GteAppRouteNames.nationalTeamCompetitions:
        return const NationalTeamCompetitionsRouteData();
      case GteAppRouteNames.nationalTeamEntry:
        final String? entryId = _nonEmpty(pathParameters['entryId']);
        if (entryId == null) {
          return null;
        }
        return NationalTeamEntryRouteData(entryId: entryId);
      case GteAppRouteNames.nationalTeamHistory:
        return const NationalTeamHistoryRouteData();
      case GteAppRouteNames.footballTransferCenter:
        return FootballTransferCenterRouteData(
          tab: gteTransferCenterTabFromRaw(queryParameters['tab']),
        );
      case GteAppRouteNames.creatorStadiumClub:
        if (clubId == null) {
          return null;
        }
        return CreatorStadiumClubRouteData(
          clubId: clubId,
          clubName: clubName,
          seasonId: seasonId,
        );
      case GteAppRouteNames.creatorStadiumMatch:
        final String? matchId = _nonEmpty(pathParameters['matchId']);
        if (matchId == null) {
          return null;
        }
        return CreatorStadiumMatchRouteData(matchId: matchId);
      case GteAppRouteNames.creatorStadiumAdminControl:
        return const CreatorStadiumAdminControlRouteData();
      case GteAppRouteNames.creatorLeagueFinancialReport:
        return CreatorLeagueFinancialReportRouteData(seasonId: seasonId);
      case GteAppRouteNames.creatorLeagueSettlements:
        return CreatorLeagueSettlementsRouteData(seasonId: seasonId);
      case GteAppRouteNames.giftStabilizer:
        return const GiftStabilizerRouteData();
      case GteAppRouteNames.clubIdentityJerseys:
        if (clubId == null) {
          return null;
        }
        return ClubIdentityJerseysRouteData(
          clubId: clubId,
          clubName: clubName,
        );
      case GteAppRouteNames.clubIdentityReputationOverview:
        if (clubId == null) {
          return null;
        }
        return ClubReputationOverviewRouteData(
          clubId: clubId,
          clubName: clubName,
        );
      case GteAppRouteNames.clubIdentityReputationHistory:
        if (clubId == null) {
          return null;
        }
        return ClubReputationHistoryRouteData(
          clubId: clubId,
          clubName: clubName,
        );
      case GteAppRouteNames.clubIdentityReputationLeaderboard:
        if (clubId == null) {
          return null;
        }
        return ClubReputationLeaderboardRouteData(
          clubId: clubId,
          clubName: clubName,
        );
      case GteAppRouteNames.clubIdentityTrophyCabinet:
        if (clubId == null) {
          return null;
        }
        return ClubTrophyCabinetRouteData(
          clubId: clubId,
          clubName: clubName,
          filter: filter,
        );
      case GteAppRouteNames.clubIdentityTrophyTimeline:
        if (clubId == null) {
          return null;
        }
        return ClubTrophyTimelineRouteData(
          clubId: clubId,
          clubName: clubName,
          filter: filter,
        );
      case GteAppRouteNames.clubIdentityTrophyLeaderboard:
        if (clubId == null) {
          return null;
        }
        return ClubTrophyLeaderboardRouteData(
          clubId: clubId,
          clubName: clubName,
          filter: filter,
        );
      case GteAppRouteNames.clubIdentityDynastyOverview:
        if (clubId == null) {
          return null;
        }
        return ClubDynastyOverviewRouteData(
          clubId: clubId,
          clubName: clubName,
        );
      case GteAppRouteNames.clubIdentityDynastyHistory:
        if (clubId == null) {
          return null;
        }
        return ClubDynastyHistoryRouteData(
          clubId: clubId,
          clubName: clubName,
        );
      case GteAppRouteNames.clubIdentityDynastyLeaderboard:
        if (clubId == null) {
          return null;
        }
        return ClubDynastyLeaderboardRouteData(
          clubId: clubId,
          clubName: clubName,
        );
      case GteAppRouteNames.clubIdentityReplays:
        if (clubId == null) {
          return null;
        }
        return ClubReplaysRouteData(
          clubId: clubId,
          clubName: clubName,
          surface: gteReplaySurfaceFromRaw(queryParameters['surface']),
        );
      default:
        return null;
    }
  }

  static GteAppRouteData? fromUri(Uri uri) {
    final List<String> segments = _normalizedSegments(uri);
    if (segments.isEmpty) {
      return null;
    }

    if (segments.first == 'competitions') {
      if (segments.length == 1) {
        return CompetitionsDiscoveryRouteData(
          highlight: _nonEmpty(uri.queryParameters['highlight']),
        );
      }
      if (segments.length == 2) {
        if (segments[1] == 'create') {
          return const CompetitionCreateRouteData();
        }
        if (segments[1] == 'world-super-cup') {
          return const CompetitionWorldSuperCupRouteData();
        }
        return CompetitionDetailRouteData(
          competitionId: segments[1],
          inviteCode: _nonEmpty(uri.queryParameters['inviteCode']),
        );
      }
      if (segments.length == 3) {
        final String competitionId = segments[1];
        if (segments[2] == 'join') {
          return CompetitionJoinRouteData(
            competitionId: competitionId,
            inviteCode: _nonEmpty(uri.queryParameters['inviteCode']),
          );
        }
        if (segments[2] == 'share') {
          return CompetitionShareRouteData(
            competitionId: competitionId,
          );
        }
      }
      return null;
    }

    if (segments.first == 'streamer-tournaments') {
      if (segments.length == 1) {
        return const StreamerTournamentsListRouteData();
      }
      if (segments.length == 2) {
        return StreamerTournamentDetailRouteData(
          tournamentId: segments[1],
        );
      }
      return null;
    }

    if (segments.length == 3 &&
        segments.first == 'fan-predictions' &&
        segments[1] == 'matches') {
      return FanPredictionMatchRouteData(matchId: segments[2]);
    }

    if (segments.first == 'player-cards') {
      if (segments.length == 1) {
        return const PlayerCardsBrowseRouteData();
      }
      if (segments.length == 2 && segments[1] == 'inventory') {
        return const PlayerCardsInventoryRouteData();
      }
      if (segments.length == 3 && segments[1] == 'players') {
        return PlayerCardDetailRouteData(playerId: segments[2]);
      }
      return null;
    }

    if (segments.length >= 3 &&
        segments.first == 'creator-share-market' &&
        segments[1] == 'clubs') {
      return segments.length == 3
          ? CreatorShareMarketClubRouteData(
              clubId: segments[2],
              clubName: _nonEmpty(uri.queryParameters['clubName']),
            )
          : null;
    }

    if (segments.first == 'world') {
      if (segments.length == 1) {
        return const WorldOverviewRouteData();
      }
      if (segments.length == 3 && segments[1] == 'clubs') {
        return WorldClubContextRouteData(
          clubId: segments[2],
          clubName: _nonEmpty(uri.queryParameters['clubName']),
        );
      }
      if (segments.length == 3 && segments[1] == 'competitions') {
        return WorldCompetitionContextRouteData(
          competitionId: segments[2],
        );
      }
      return null;
    }

    if (segments.first == 'national-team') {
      if (segments.length == 1) {
        return const NationalTeamCompetitionsRouteData();
      }
      if (segments.length == 2 && segments[1] == 'history') {
        return const NationalTeamHistoryRouteData();
      }
      if (segments.length == 3 && segments[1] == 'entries') {
        return NationalTeamEntryRouteData(entryId: segments[2]);
      }
      return null;
    }

    if (segments.length >= 2 &&
        segments.first == 'football' &&
        segments[1] == 'transfer-center') {
      return FootballTransferCenterRouteData(
        tab: gteTransferCenterTabFromRaw(uri.queryParameters['tab']),
      );
    }

    if (segments.first == 'creator-stadium') {
      if (segments.length == 3 && segments[1] == 'clubs') {
        return CreatorStadiumClubRouteData(
          clubId: segments[2],
          clubName: _nonEmpty(uri.queryParameters['clubName']),
          seasonId: _nonEmpty(uri.queryParameters['seasonId']),
        );
      }
      if (segments.length == 3 && segments[1] == 'matches') {
        return CreatorStadiumMatchRouteData(matchId: segments[2]);
      }
      return null;
    }

    if (segments.first == 'admin') {
      if (segments.length == 3 &&
          segments[1] == 'creator-share-market' &&
          segments[2] == 'control') {
        return const CreatorShareMarketAdminControlRouteData();
      }
      if (segments.length == 3 &&
          segments[1] == 'creator-stadium' &&
          segments[2] == 'control') {
        return const CreatorStadiumAdminControlRouteData();
      }
      if (segments.length == 3 &&
          segments[1] == 'creator-league' &&
          segments[2] == 'financial-report') {
        return CreatorLeagueFinancialReportRouteData(
          seasonId: _nonEmpty(uri.queryParameters['seasonId']),
        );
      }
      if (segments.length == 3 &&
          segments[1] == 'creator-league' &&
          segments[2] == 'settlements') {
        return CreatorLeagueSettlementsRouteData(
          seasonId: _nonEmpty(uri.queryParameters['seasonId']),
        );
      }
      if (segments.length == 2 && segments[1] == 'gift-stabilizer') {
        return const GiftStabilizerRouteData();
      }
      return null;
    }

    if (segments.first == 'clubs') {
      if (segments.length == 2 && segments[1] == 'sale-market') {
        return const ClubSaleMarketListingsRouteData();
      }
      if (segments.length == 3 && segments[2] == 'sale-market') {
        return ClubSaleMarketDetailRouteData(
          clubId: segments[1],
          clubName: _nonEmpty(uri.queryParameters['clubName']),
        );
      }
      if (segments.length == 4 &&
          segments[2] == 'sale-market' &&
          segments[3] == 'offers') {
        return ClubSaleMarketOwnerOffersRouteData(
          clubId: segments[1],
          clubName: _nonEmpty(uri.queryParameters['clubName']),
        );
      }
    }

    if (segments.length < 4 ||
        segments.first != 'clubs' ||
        segments[2] != 'identity') {
      return null;
    }

    final String clubId = segments[1];
    final String? clubName = _nonEmpty(uri.queryParameters['clubName']);
    final TrophyScopeFilter filter =
        gteTrophyScopeFilterFromRaw(uri.queryParameters['scope']);

    switch (segments[3]) {
      case 'jerseys':
        return segments.length == 4
            ? ClubIdentityJerseysRouteData(
                clubId: clubId,
                clubName: clubName,
              )
            : null;
      case 'reputation':
        if (segments.length == 4) {
          return ClubReputationOverviewRouteData(
            clubId: clubId,
            clubName: clubName,
          );
        }
        if (segments.length == 5 && segments[4] == 'history') {
          return ClubReputationHistoryRouteData(
            clubId: clubId,
            clubName: clubName,
          );
        }
        if (segments.length == 5 && segments[4] == 'leaderboard') {
          return ClubReputationLeaderboardRouteData(
            clubId: clubId,
            clubName: clubName,
          );
        }
        return null;
      case 'trophies':
        if (segments.length == 4) {
          return ClubTrophyCabinetRouteData(
            clubId: clubId,
            clubName: clubName,
            filter: filter,
          );
        }
        if (segments.length == 5 && segments[4] == 'timeline') {
          return ClubTrophyTimelineRouteData(
            clubId: clubId,
            clubName: clubName,
            filter: filter,
          );
        }
        if (segments.length == 5 && segments[4] == 'leaderboard') {
          return ClubTrophyLeaderboardRouteData(
            clubId: clubId,
            clubName: clubName,
            filter: filter,
          );
        }
        return null;
      case 'dynasty':
        if (segments.length == 4) {
          return ClubDynastyOverviewRouteData(
            clubId: clubId,
            clubName: clubName,
          );
        }
        if (segments.length == 5 && segments[4] == 'history') {
          return ClubDynastyHistoryRouteData(
            clubId: clubId,
            clubName: clubName,
          );
        }
        if (segments.length == 5 && segments[4] == 'leaderboard') {
          return ClubDynastyLeaderboardRouteData(
            clubId: clubId,
            clubName: clubName,
          );
        }
        return null;
      case 'replays':
        return segments.length == 4
            ? ClubReplaysRouteData(
                clubId: clubId,
                clubName: clubName,
                surface: gteReplaySurfaceFromRaw(
                  uri.queryParameters['surface'],
                ),
              )
            : null;
      default:
        return null;
    }
  }

  static String normalizeRouteName(String routeName) {
    return routeName
        .trim()
        .replaceAll('/', '.')
        .replaceAll('_', '-')
        .split('.')
        .map((String segment) => segment.trim().toLowerCase())
        .where((String segment) => segment.isNotEmpty)
        .join('.');
  }
}

Uri _buildUri({
  required String path,
  Map<String, String> queryParameters = const <String, String>{},
}) {
  return Uri(
    path: path,
    queryParameters: queryParameters.isEmpty ? null : queryParameters,
  );
}

String? _nonEmpty(String? value) {
  final String? trimmed = value?.trim();
  return trimmed == null || trimmed.isEmpty ? null : trimmed;
}

bool _looksLikePath(String raw) => raw.startsWith('/');

bool _looksLikeDeepLink(String raw) => raw.contains('://');

List<String> _normalizedSegments(Uri uri) {
  final List<String> pathSegments = uri.pathSegments
      .map((String segment) => segment.trim())
      .where((String segment) => segment.isNotEmpty)
      .toList(growable: true);
  if (uri.scheme.isNotEmpty &&
      uri.scheme != 'http' &&
      uri.scheme != 'https' &&
      uri.authority.trim().isNotEmpty) {
    pathSegments.insert(0, uri.authority.trim());
  }
  return pathSegments;
}
