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
