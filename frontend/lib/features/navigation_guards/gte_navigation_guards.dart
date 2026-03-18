import 'dart:async';

import 'package:flutter/widgets.dart';
import 'package:gte_frontend/data/competition_api.dart';
import 'package:gte_frontend/data/gte_authed_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/features/app_routes/gte_route_data.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_api_repository.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_profile_dto.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_repository.dart';
import 'package:gte_frontend/features/club_identity/jerseys/data/club_identity_dto.dart';
import 'package:gte_frontend/features/club_identity/jerseys/data/club_identity_repository.dart';
import 'package:gte_frontend/features/club_identity/jerseys/data/jersey_variant_dto.dart';
import 'package:gte_frontend/features/club_identity/reputation/data/reputation_repository.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/trophy_cabinet_dto.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/trophy_cabinet_repository.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/trophy_item_dto.dart';
import 'package:gte_frontend/models/competition_models.dart';

enum GteNavigationFallbackReason {
  inactiveWorldSuperCup,
  emptyTrophyCabinet,
  noDynastyYet,
  missingIdentitySetup,
}

class GteGuardResolution {
  const GteGuardResolution({
    required this.route,
    this.fallbackReason,
    this.message,
  });

  final GteAppRouteData route;
  final GteNavigationFallbackReason? fallbackReason;
  final String? message;

  bool get redirected => fallbackReason != null;
}

class GteNavigationDependencies {
  const GteNavigationDependencies({
    required this.apiBaseUrl,
    this.backendMode = GteBackendMode.liveThenFixture,
    String currentUserId = 'guest-user',
    String? currentUserName,
    String? currentUserRole,
    String? currentClubId,
    String? currentClubName,
    String? accessToken,
    bool isAuthenticated = false,
    this.onOpenLogin,
    this.competitionApi,
    this.trophyCabinetRepository,
    this.dynastyRepository,
    this.reputationRepository,
    this.clubIdentityRepository,
    this.resolveWorldSuperCupCompetitionId,
    this.hasIdentitySetup,
    this.currentUserIdProvider,
    this.currentUserNameProvider,
    this.currentUserRoleProvider,
    this.currentClubIdProvider,
    this.currentClubNameProvider,
    this.accessTokenProvider,
    this.isAuthenticatedProvider,
  })  : _currentUserId = currentUserId,
        _currentUserName = currentUserName,
        _currentUserRole = currentUserRole,
        _currentClubId = currentClubId,
        _currentClubName = currentClubName,
        _accessToken = accessToken,
        _isAuthenticated = isAuthenticated;

  final String apiBaseUrl;
  final GteBackendMode backendMode;
  final String _currentUserId;
  final String? _currentUserName;
  final String? _currentUserRole;
  final String? _currentClubId;
  final String? _currentClubName;
  final String? _accessToken;
  final bool _isAuthenticated;
  final Future<bool> Function(BuildContext context)? onOpenLogin;
  final CompetitionApi? competitionApi;
  final TrophyCabinetRepository? trophyCabinetRepository;
  final DynastyRepository? dynastyRepository;
  final ReputationRepository? reputationRepository;
  final ClubIdentityRepository? clubIdentityRepository;
  final FutureOr<String?> Function()? resolveWorldSuperCupCompetitionId;
  final FutureOr<bool> Function(String clubId, ClubIdentityDto? identity)?
      hasIdentitySetup;
  final String Function()? currentUserIdProvider;
  final String? Function()? currentUserNameProvider;
  final String? Function()? currentUserRoleProvider;
  final String? Function()? currentClubIdProvider;
  final String? Function()? currentClubNameProvider;
  final String? Function()? accessTokenProvider;
  final bool Function()? isAuthenticatedProvider;

  String get currentUserId => currentUserIdProvider?.call() ?? _currentUserId;

  String? get currentUserName =>
      currentUserNameProvider?.call() ?? _currentUserName;

  String? get currentUserRole =>
      currentUserRoleProvider?.call() ?? _currentUserRole;

  String? get currentClubId => currentClubIdProvider?.call() ?? _currentClubId;

  String? get currentClubName =>
      currentClubNameProvider?.call() ?? _currentClubName;

  String? get accessToken => accessTokenProvider?.call() ?? _accessToken;

  bool get isAuthenticated =>
      isAuthenticatedProvider?.call() ?? _isAuthenticated;

  bool get isAdminRole => <String>{'admin', 'super_admin'}
      .contains((currentUserRole ?? '').trim().toLowerCase());

  CompetitionApi createCompetitionApi() {
    return competitionApi ??
        CompetitionApi.standard(
          baseUrl: apiBaseUrl,
          mode: backendMode,
        );
  }

  TrophyCabinetRepository createTrophyCabinetRepository() {
    return trophyCabinetRepository ?? StubTrophyCabinetRepository();
  }

  DynastyRepository createDynastyRepository() {
    return dynastyRepository ??
        DynastyApiRepository.standard(
          baseUrl: apiBaseUrl,
          mode: backendMode,
        );
  }

  ReputationRepository createReputationRepository() {
    return reputationRepository ??
        ReputationApiRepository.standard(
          baseUrl: apiBaseUrl,
          mode: backendMode,
        );
  }

  ClubIdentityRepository createClubIdentityRepository() {
    return clubIdentityRepository ??
        ClubIdentityApiRepository.standard(
          baseUrl: apiBaseUrl,
          mode: backendMode,
        );
  }

  GteAuthedApi createAuthedApi({
    String? overrideAccessToken,
  }) {
    return GteAuthedApi(
      config: GteRepositoryConfig(
        baseUrl: apiBaseUrl,
        mode: backendMode,
      ),
      transport: GteHttpTransport(),
      accessToken: overrideAccessToken ?? accessToken,
      mode: backendMode,
    );
  }
}

class GteNavigationGuardResolver {
  const GteNavigationGuardResolver({
    required this.dependencies,
  });

  final GteNavigationDependencies dependencies;

  Future<GteGuardResolution> resolve(GteAppRouteData route) async {
    if (route is CompetitionWorldSuperCupRouteData) {
      return _resolveWorldSuperCup(route);
    }
    if (route is ClubTrophyTimelineRouteData) {
      return _resolveTrophyTimeline(route);
    }
    if (route is ClubDynastyHistoryRouteData) {
      return _resolveDynastyHistory(route);
    }
    if (route is ClubReplaysRouteData) {
      return _resolveReplayPreview(route);
    }
    return GteGuardResolution(route: route);
  }

  Future<GteGuardResolution> _resolveWorldSuperCup(
    CompetitionWorldSuperCupRouteData route,
  ) async {
    final String? resolvedCompetitionId =
        await dependencies.resolveWorldSuperCupCompetitionId?.call();
    if (resolvedCompetitionId != null &&
        resolvedCompetitionId.trim().isNotEmpty) {
      return GteGuardResolution(
        route: CompetitionDetailRouteData(
          competitionId: resolvedCompetitionId.trim(),
        ),
      );
    }

    try {
      final CompetitionListResponse response = await dependencies
          .createCompetitionApi()
          .fetchCompetitions(userId: dependencies.currentUserId);
      final CompetitionSummary? competition =
          _findWorldSuperCupCompetition(response.items);
      if (competition != null && _isWorldSuperCupActive(competition)) {
        return GteGuardResolution(
          route: CompetitionDetailRouteData(
            competitionId: competition.id,
          ),
        );
      }
    } catch (_) {
      // Route safely degrades to the broader discovery feed when live status
      // cannot be confirmed.
    }

    return const GteGuardResolution(
      route: CompetitionsDiscoveryRouteData(
        highlight: 'world-super-cup',
      ),
      fallbackReason: GteNavigationFallbackReason.inactiveWorldSuperCup,
      message: 'World Super Cup is not active right now.',
    );
  }

  Future<GteGuardResolution> _resolveTrophyTimeline(
    ClubTrophyTimelineRouteData route,
  ) async {
    try {
      final TrophyCabinetDto cabinet =
          await dependencies.createTrophyCabinetRepository().fetchTrophyCabinet(
                clubId: route.clubId,
                teamScope: route.filter.queryValue,
              );
      if (!cabinet.isEmpty) {
        return GteGuardResolution(route: route);
      }
      return GteGuardResolution(
        route: ClubTrophyCabinetRouteData(
          clubId: route.clubId,
          clubName: route.clubName ?? cabinet.clubName,
          filter: route.filter,
        ),
        fallbackReason: GteNavigationFallbackReason.emptyTrophyCabinet,
        message: 'Open the trophy cabinet first to unlock timeline navigation.',
      );
    } catch (_) {
      return GteGuardResolution(route: route);
    }
  }

  Future<GteGuardResolution> _resolveDynastyHistory(
    ClubDynastyHistoryRouteData route,
  ) async {
    try {
      final DynastyProfileDto profile =
          await dependencies.createDynastyRepository().fetchDynastyProfile(
                route.clubId,
              );
      if (profile.hasRecognizedDynasty) {
        return GteGuardResolution(route: route);
      }
      return GteGuardResolution(
        route: ClubDynastyOverviewRouteData(
          clubId: route.clubId,
          clubName: route.clubName ?? profile.clubName,
        ),
        fallbackReason: GteNavigationFallbackReason.noDynastyYet,
        message: 'Dynasty history unlocks after the club establishes an era.',
      );
    } catch (_) {
      return GteGuardResolution(route: route);
    }
  }

  Future<GteGuardResolution> _resolveReplayPreview(
    ClubReplaysRouteData route,
  ) async {
    ClubIdentityDto? identity;
    try {
      identity =
          await dependencies.createClubIdentityRepository().fetchIdentity(
                route.clubId,
              );
    } catch (_) {
      return GteGuardResolution(route: route);
    }

    final bool hasSetup = await (dependencies.hasIdentitySetup?.call(
          route.clubId,
          identity,
        ) ??
        _defaultHasIdentitySetup(identity));
    if (hasSetup) {
      return GteGuardResolution(route: route);
    }
    return GteGuardResolution(
      route: ClubIdentityJerseysRouteData(
        clubId: route.clubId,
        clubName: route.clubName ?? identity.clubName,
      ),
      fallbackReason: GteNavigationFallbackReason.missingIdentitySetup,
      message: 'Set up club identity before opening replay surfaces.',
    );
  }
}

CompetitionSummary? _findWorldSuperCupCompetition(
  List<CompetitionSummary> competitions,
) {
  for (final CompetitionSummary competition in competitions) {
    final String haystack =
        '${competition.id} ${competition.name}'.toLowerCase();
    if (haystack.contains('world super cup') ||
        haystack.contains('world-super-cup')) {
      return competition;
    }
  }
  return null;
}

bool _isWorldSuperCupActive(CompetitionSummary competition) {
  switch (competition.status) {
    case CompetitionStatus.draft:
    case CompetitionStatus.completed:
    case CompetitionStatus.cancelled:
    case CompetitionStatus.refunded:
    case CompetitionStatus.disputed:
      return false;
    case CompetitionStatus.published:
    case CompetitionStatus.openForJoin:
    case CompetitionStatus.filled:
    case CompetitionStatus.locked:
    case CompetitionStatus.inProgress:
      return true;
  }
}

bool _defaultHasIdentitySetup(ClubIdentityDto? identity) {
  if (identity == null) {
    return false;
  }
  if (identity.clubName.trim().isEmpty ||
      identity.shortClubCode.trim().isEmpty) {
    return false;
  }
  if (identity.badgeProfile.initials.trim().isEmpty) {
    return false;
  }
  return identity.jerseySet.all.every(_hasReadableKitConfiguration);
}

bool _hasReadableKitConfiguration(JerseyVariantDto variant) {
  return variant.primaryColor.trim().isNotEmpty &&
      variant.secondaryColor.trim().isNotEmpty &&
      variant.accentColor.trim().isNotEmpty;
}
