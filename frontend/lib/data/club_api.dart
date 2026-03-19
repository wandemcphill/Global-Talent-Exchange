import 'dart:async';

import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/gte_http_transport.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_api_repository.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_profile_dto.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_repository.dart';
import 'package:gte_frontend/features/club_identity/dynasty/data/dynasty_types.dart';
import 'package:gte_frontend/features/club_identity/jerseys/data/badge_profile_dto.dart';
import 'package:gte_frontend/features/club_identity/jerseys/data/club_identity_dto.dart';
import 'package:gte_frontend/features/club_identity/jerseys/data/club_identity_repository.dart';
import 'package:gte_frontend/features/club_identity/jerseys/data/jersey_set_dto.dart';
import 'package:gte_frontend/features/club_identity/reputation/data/reputation_models.dart';
import 'package:gte_frontend/features/club_identity/reputation/data/reputation_repository.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/honors_timeline_dto.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/season_honors_dto.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/trophy_cabinet_dto.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/trophy_cabinet_repository.dart';
import 'package:gte_frontend/features/club_identity/trophies/data/trophy_leaderboard_entry_dto.dart';
import 'package:gte_frontend/models/club_branding_models.dart';
import 'package:gte_frontend/models/club_catalog_models.dart';
import 'package:gte_frontend/models/club_models.dart';
import 'package:gte_frontend/models/club_reputation_models.dart';
import 'package:gte_frontend/widgets/gte_formatters.dart';

class ClubApi {
  ClubApi({
    required this.config,
    required this.transport,
    required ReputationRepository reputationRepository,
    required DynastyRepository dynastyRepository,
    required TrophyCabinetRepository trophyRepository,
    required ClubIdentityRepository identityRepository,
    _ClubFixtureStore? fixtures,
  })  : _reputationRepository = reputationRepository,
        _dynastyRepository = dynastyRepository,
        _trophyRepository = trophyRepository,
        _identityRepository = identityRepository,
        _fixtures = fixtures ?? _ClubFixtureStore.seeded();

  final GteRepositoryConfig config;
  final GteTransport transport;
  final ReputationRepository _reputationRepository;
  final DynastyRepository _dynastyRepository;
  final TrophyCabinetRepository _trophyRepository;
  final ClubIdentityRepository _identityRepository;
  final _ClubFixtureStore _fixtures;

  factory ClubApi.standard({
    required String baseUrl,
    GteBackendMode mode = GteBackendMode.liveThenFixture,
  }) {
    final GteRepositoryConfig config =
        GteRepositoryConfig(baseUrl: baseUrl, mode: mode);
    return ClubApi(
      config: config,
      transport: GteHttpTransport(),
      reputationRepository: ReputationApiRepository.standard(
        baseUrl: baseUrl,
        mode: mode,
      ),
      dynastyRepository: DynastyApiRepository.standard(
        baseUrl: baseUrl,
        mode: mode,
      ),
      trophyRepository: _ClubTrophyApiRepository(
        config: config,
        transport: GteHttpTransport(),
        fixtures: StubTrophyCabinetRepository(),
      ),
      identityRepository: _ClubIdentityApiRepository(
        config: config,
        transport: GteHttpTransport(),
        fixtures: MockClubIdentityRepository(),
      ),
    );
  }

  factory ClubApi.fixture() {
    return ClubApi.standard(
      baseUrl: 'http://127.0.0.1:8000',
      mode: GteBackendMode.fixture,
    );
  }

  Future<ClubDashboardData> fetchDashboard({
    required String clubId,
    String? clubName,
  }) async {
    final String fallbackClubName = clubName?.trim().isNotEmpty == true
        ? clubName!.trim()
        : prettifyClubId(clubId);
    final List<Object?> payload = await Future.wait<Object?>(<Future<Object?>>[
      _identityRepository.fetchIdentity(clubId),
      _reputationRepository.fetchOverview(clubId),
      _reputationRepository.fetchHistory(clubId),
      _reputationRepository.fetchLeaderboard(
        scope: PrestigeLeaderboardScope.global,
        currentClubId: clubId,
      ),
      _reputationRepository.fetchLeaderboard(
        scope: PrestigeLeaderboardScope.region,
        currentClubId: clubId,
      ),
      _loadOptionalDashboardPart<DynastyProfileDto>(
        load: () => _dynastyRepository.fetchDynastyProfile(clubId),
        fallback: _emptyDynastyProfile(
          clubId: clubId,
          clubName: fallbackClubName,
        ),
      ),
      _loadOptionalDashboardPart<TrophyCabinetDto>(
        load: () => _trophyRepository.fetchTrophyCabinet(clubId: clubId),
        fallback: _emptyTrophyCabinet(
          clubId: clubId,
          clubName: fallbackClubName,
        ),
      ),
      _fetchClubRecord(clubId),
    ]);

    final ClubIdentityDto identity = payload[0] as ClubIdentityDto;
    final ReputationProfileDto reputationProfile =
        payload[1] as ReputationProfileDto;
    final ReputationHistoryDto reputationHistory =
        payload[2] as ReputationHistoryDto;
    final PrestigeLeaderboardDto globalLeaderboard =
        payload[3] as PrestigeLeaderboardDto;
    final PrestigeLeaderboardDto regionalLeaderboard =
        payload[4] as PrestigeLeaderboardDto;
    final DynastyProfileDto dynastyProfile = payload[5] as DynastyProfileDto;
    final TrophyCabinetDto trophyCabinet = payload[6] as TrophyCabinetDto;
    final Map<String, Object?>? clubRecord =
        payload[7] as Map<String, Object?>?;

    final String resolvedClubName = _resolveClubName(
      clubName: clubName,
      identity: identity,
      reputationProfile: reputationProfile,
      clubId: clubId,
    );
    final ClubReputationSummary reputation = ClubReputationSummary(
      profile: reputationProfile,
      history: reputationHistory,
      contributors: _buildContributors(reputationProfile, reputationHistory),
      globalRank: _findLeaderboardEntry(globalLeaderboard, clubId),
      regionalRank: _findLeaderboardEntry(regionalLeaderboard, clubId),
    );
    final ClubBrandingProfile branding =
        _fixtures.brandingFor(clubId, resolvedClubName);
    final List<ClubCatalogItem> catalog = _fixtures.catalogFor(clubId);
    final List<ClubPurchaseRecord> purchaseHistory =
        _fixtures.purchaseHistoryFor(clubId);

    return ClubDashboardData(
      clubId: clubId,
      clubName: resolvedClubName,
      countryName: GteJson.stringOrNull(
        clubRecord ?? const <String, Object?>{},
        const <String>['country_name', 'countryName'],
      ),
      playerCount: clubRecord == null
          ? null
          : GteJson.integer(
              clubRecord,
              const <String>['player_count', 'playerCount'],
            ),
      identity: identity.copyWith(clubName: resolvedClubName),
      reputation: reputation,
      trophyCabinet: trophyCabinet,
      dynastyProfile: dynastyProfile,
      branding: branding,
      catalog: catalog,
      purchaseHistory: purchaseHistory,
      showcasePanels: _buildShowcasePanels(
        reputation: reputation,
        trophyCabinet: trophyCabinet,
        dynastyProfile: dynastyProfile,
        catalog: catalog,
      ),
      legacyMilestones:
          _buildLegacyMilestones(reputation, dynastyProfile, trophyCabinet),
    );
  }

  Future<ClubIdentityDto> saveIdentity({
    required String clubId,
    required ClubIdentityDto identity,
  }) async {
    await _identityRepository.patchIdentity(
      clubId: clubId,
      patch: identity.toIdentityPatchJson(),
    );
    await _identityRepository.patchJerseys(
      clubId: clubId,
      patch: identity.jerseySet.toJson(),
    );
    return _identityRepository.fetchIdentity(clubId);
  }

  Future<ClubBrandingProfile> saveBranding({
    required String clubId,
    required ClubBrandingProfile branding,
  }) async {
    await Future<void>.delayed(const Duration(milliseconds: 120));
    _fixtures.saveBranding(clubId, branding);
    return _fixtures.brandingFor(clubId, null);
  }

  Future<void> purchaseCatalogItem({
    required String clubId,
    required ClubCatalogItem item,
  }) async {
    await Future<void>.delayed(const Duration(milliseconds: 140));
    _fixtures.purchaseItem(clubId, item);
  }

  Future<void> equipCatalogItem({
    required String clubId,
    required ClubCatalogItem item,
  }) async {
    await Future<void>.delayed(const Duration(milliseconds: 120));
    _fixtures.equipItem(clubId, item);
  }

  Future<ClubAdminAnalytics> fetchAdminAnalytics() async {
    await Future<void>.delayed(const Duration(milliseconds: 120));
    return _fixtures.buildAdminAnalytics();
  }

  Future<List<BrandingReviewCase>> fetchBrandingModerationQueue() async {
    await Future<void>.delayed(const Duration(milliseconds: 120));
    return _fixtures.brandingReviewQueue();
  }

  Future<void> updateBrandingReview({
    required String reviewId,
    required bool approved,
  }) async {
    await Future<void>.delayed(const Duration(milliseconds: 100));
    _fixtures.updateBrandingReview(reviewId: reviewId, approved: approved);
  }

  String _resolveClubName({
    required String? clubName,
    required ClubIdentityDto identity,
    required ReputationProfileDto reputationProfile,
    required String clubId,
  }) {
    final String identityName = identity.clubName.trim();
    if (clubName != null && clubName.trim().isNotEmpty) {
      return clubName.trim();
    }
    if (identityName.isNotEmpty) {
      return identityName;
    }
    if (reputationProfile.clubName.trim().isNotEmpty) {
      return reputationProfile.clubName;
    }
    return prettifyClubId(clubId);
  }

  PrestigeLeaderboardEntryDto? _findLeaderboardEntry(
    PrestigeLeaderboardDto leaderboard,
    String clubId,
  ) {
    for (final PrestigeLeaderboardEntryDto entry in leaderboard.entries) {
      if (entry.clubId == clubId) {
        return entry;
      }
    }
    return null;
  }

  List<ReputationContribution> _buildContributors(
    ReputationProfileDto profile,
    ReputationHistoryDto history,
  ) {
    final List<ReputationContribution> contributions =
        <ReputationContribution>[];
    for (final ReputationMilestoneDto milestone in profile.biggestMilestones) {
      contributions.add(
        ReputationContribution(
          title: milestone.title,
          detail: milestone.season == null
              ? 'Legacy milestone'
              : 'Season ${milestone.season}',
          delta: milestone.delta,
          categoryLabel: 'Legacy milestone',
        ),
      );
    }
    for (final ReputationEventDto event in history.events.take(3)) {
      contributions.add(
        ReputationContribution(
          title: event.title,
          detail: event.description,
          delta: event.delta,
          categoryLabel: _eventCategoryLabel(event.category),
        ),
      );
    }
    return contributions.take(6).toList(growable: false);
  }

  List<ClubShowcasePanel> _buildShowcasePanels({
    required ClubReputationSummary reputation,
    required TrophyCabinetDto trophyCabinet,
    required DynastyProfileDto dynastyProfile,
    required List<ClubCatalogItem> catalog,
  }) {
    return <ClubShowcasePanel>[
      ClubShowcasePanel(
        title: 'Club reputation',
        value: _prestigeTierLabel(reputation.profile.currentPrestigeTier),
        caption:
            '${reputation.profile.currentScore} reputation with ${reputation.recentEvents.length} recent growth events.',
      ),
      ClubShowcasePanel(
        title: 'Trophy cabinet',
        value: '${trophyCabinet.totalHonorsCount}',
        caption:
            '${trophyCabinet.majorHonorsCount} major honors and ${trophyCabinet.eliteHonorsCount} featured legacy pieces.',
      ),
      ClubShowcasePanel(
        title: 'Dynasty progression',
        value: _dynastyEraLabel(dynastyProfile.currentEraLabel),
        caption:
            'Dynasty score ${dynastyProfile.dynastyScore} with ${dynastyProfile.eras.length} recognized eras.',
      ),
      ClubShowcasePanel(
        title: 'Cosmetic locker',
        value:
            '${catalog.where((ClubCatalogItem item) => item.ownershipStatus != CatalogOwnershipStatus.available).length}',
        caption:
            'Transparent catalog ownership with equipped club cosmetics kept visible.',
      ),
    ];
  }

  List<ClubLegacyMilestone> _buildLegacyMilestones(
    ClubReputationSummary reputation,
    DynastyProfileDto dynastyProfile,
    TrophyCabinetDto trophyCabinet,
  ) {
    final List<ClubLegacyMilestone> milestones = <ClubLegacyMilestone>[
      ...reputation.profile.biggestMilestones.map(
        (ReputationMilestoneDto milestone) => ClubLegacyMilestone(
          title: milestone.title,
          subtitle: milestone.season == null
              ? 'Club reputation milestone'
              : 'Unlocked in Season ${milestone.season}',
          tagLabel:
              '${milestone.delta >= 0 ? '+' : ''}${milestone.delta} reputation',
          unlocked: true,
        ),
      ),
      ...dynastyProfile.eras.map(
        (era) => ClubLegacyMilestone(
          title: _dynastyEraLabel(era.eraLabel),
          subtitle: era.seasonSpanLabel,
          tagLabel: 'Peak ${era.peakScore}',
          unlocked: era.active || era.dynastyStatus != DynastyStatus.none,
        ),
      ),
      ...trophyCabinet.featuredHonors(limit: 2).map(
            (honor) => ClubLegacyMilestone(
              title: honor.trophyName,
              subtitle: '${honor.seasonLabel} ${honor.competitionRegion}',
              tagLabel: honor.prestigeLabel,
              unlocked: true,
            ),
          ),
    ];
    return milestones.take(6).toList(growable: false);
  }

  Future<T> _loadOptionalDashboardPart<T>({
    required Future<T> Function() load,
    required T fallback,
  }) async {
    try {
      return await load();
    } catch (_) {
      return fallback;
    }
  }

  DynastyProfileDto _emptyDynastyProfile({
    required String clubId,
    required String clubName,
  }) {
    return DynastyProfileDto.fromJson(<String, Object?>{
      'club_id': clubId,
      'club_name': clubName,
      'dynasty_status': 'none',
      'current_era_label': 'none',
      'active_dynasty_flag': false,
      'dynasty_score': 0,
      'active_streaks': <String, Object?>{
        'top_four': 0,
        'trophy_seasons': 0,
        'world_super_cup_qualification': 0,
        'positive_reputation': 0,
      },
      'last_four_season_summary': const <Object?>[],
      'reasons': const <String>[],
      'current_snapshot': null,
      'dynasty_timeline': const <Object?>[],
      'eras': const <Object?>[],
      'events': const <Object?>[],
    });
  }

  TrophyCabinetDto _emptyTrophyCabinet({
    required String clubId,
    required String clubName,
  }) {
    return TrophyCabinetDto.fromJson(<String, Object?>{
      'club_id': clubId,
      'club_name': clubName,
      'total_honors_count': 0,
      'major_honors_count': 0,
      'elite_honors_count': 0,
      'senior_honors_count': 0,
      'academy_honors_count': 0,
      'trophies_by_category': const <Object?>[],
      'trophies_by_season': const <Object?>[],
      'recent_honors': const <Object?>[],
      'historic_honors_timeline': const <Object?>[],
      'summary_outputs': const <String>[],
    });
  }

  Future<Map<String, Object?>?> _fetchClubRecord(String clubId) async {
    if (config.mode == GteBackendMode.fixture) {
      return null;
    }
    try {
      final GteTransportResponse response = await transport.send(
        GteTransportRequest(
          method: 'GET',
          uri: config.uriFor('/clubs/$clubId'),
          headers: const <String, String>{'Accept': 'application/json'},
        ),
      );
      if (response.statusCode >= 400 || response.body == null) {
        return null;
      }
      return GteJson.map(response.body, label: 'club record');
    } catch (_) {
      return null;
    }
  }
}

class _ClubIdentityApiRepository extends ClubIdentityRepository {
  _ClubIdentityApiRepository({
    required this.config,
    required this.transport,
    required this.fixtures,
  });

  final GteRepositoryConfig config;
  final GteTransport transport;
  final ClubIdentityRepository fixtures;

  @override
  Future<BadgeProfileDto> fetchBadge(String clubId) {
    return _withFallback<BadgeProfileDto>(
      () async => BadgeProfileDto.fromJson(
        _asMap(await _request('GET', '/api/clubs/$clubId/badge')),
      ),
      () => fixtures.fetchBadge(clubId),
    );
  }

  @override
  Future<ClubIdentityDto> fetchIdentity(String clubId) {
    return _withFallback<ClubIdentityDto>(
      () async => ClubIdentityDto.fromJson(
        _asMap(await _request('GET', '/api/clubs/$clubId/identity')),
      ),
      () => fixtures.fetchIdentity(clubId),
    );
  }

  @override
  Future<JerseySetDto> fetchJerseys(String clubId) {
    return _withFallback<JerseySetDto>(
      () async => JerseySetDto.fromJson(
        _asMap(await _request('GET', '/api/clubs/$clubId/jerseys')),
      ),
      () => fixtures.fetchJerseys(clubId),
    );
  }

  @override
  Future<ClubIdentityDto> patchIdentity({
    required String clubId,
    required Map<String, dynamic> patch,
  }) {
    return _withFallback<ClubIdentityDto>(
      () async => ClubIdentityDto.fromJson(
        _asMap(await _request(
          'PATCH',
          '/api/clubs/$clubId/identity',
          body: patch,
        )),
      ),
      () => fixtures.patchIdentity(clubId: clubId, patch: patch),
    );
  }

  @override
  Future<JerseySetDto> patchJerseys({
    required String clubId,
    required Map<String, dynamic> patch,
  }) {
    return _withFallback<JerseySetDto>(
      () async => JerseySetDto.fromJson(
        _asMap(await _request(
          'PATCH',
          '/api/clubs/$clubId/jerseys',
          body: patch,
        )),
      ),
      () => fixtures.patchJerseys(clubId: clubId, patch: patch),
    );
  }

  Future<T> _withFallback<T>(
    Future<T> Function() liveCall,
    Future<T> Function() fixtureCall,
  ) async {
    if (config.mode == GteBackendMode.fixture) {
      return fixtureCall();
    }
    try {
      return await liveCall();
    } on GteApiException catch (error) {
      if (config.mode == GteBackendMode.liveThenFixture &&
          (error.supportsFixtureFallback ||
              error.type == GteApiErrorType.notFound ||
              error.type == GteApiErrorType.unknown)) {
        return fixtureCall();
      }
      rethrow;
    } on GteParsingException {
      if (config.mode == GteBackendMode.liveThenFixture) {
        return fixtureCall();
      }
      rethrow;
    }
  }

  Future<Object?> _request(
    String method,
    String path, {
    Object? body,
  }) async {
    try {
      final GteTransportResponse response = await transport.send(
        GteTransportRequest(
          method: method,
          uri: config.uriFor(path),
          headers: const <String, String>{'Accept': 'application/json'},
          body: body,
        ),
      );
      if (response.statusCode >= 400) {
        throw GteApiException(
          type: _errorType(response.statusCode),
          message: _errorMessage(response.body),
          statusCode: response.statusCode,
          cause: response.body,
        );
      }
      return response.body;
    } on GteApiException {
      rethrow;
    } catch (error) {
      throw GteApiException(
        type: GteApiErrorType.network,
        message: 'Unable to load club identity right now.',
        cause: error,
      );
    }
  }
}

class _ClubTrophyApiRepository implements TrophyCabinetRepository {
  _ClubTrophyApiRepository({
    required this.config,
    required this.transport,
    required this.fixtures,
  });

  final GteRepositoryConfig config;
  final GteTransport transport;
  final TrophyCabinetRepository fixtures;

  @override
  Future<TrophyCabinetDto> fetchTrophyCabinet({
    required String clubId,
    String? teamScope,
  }) {
    return _withFallback<TrophyCabinetDto>(
      () async => TrophyCabinetDto.fromJson(
        _asMap(await _request(
          '/api/clubs/$clubId/trophy-cabinet',
          query: <String, Object?>{'team_scope': teamScope},
        )),
      ),
      () => fixtures.fetchTrophyCabinet(clubId: clubId, teamScope: teamScope),
    );
  }

  @override
  Future<HonorsTimelineDto> fetchHonorsTimeline({
    required String clubId,
    String? teamScope,
  }) {
    return _withFallback<HonorsTimelineDto>(
      () async => HonorsTimelineDto.fromJson(
        _asMap(await _request(
          '/api/clubs/$clubId/honors-timeline',
          query: <String, Object?>{'team_scope': teamScope},
        )),
      ),
      () => fixtures.fetchHonorsTimeline(clubId: clubId, teamScope: teamScope),
    );
  }

  @override
  Future<SeasonHonorsArchiveDto> fetchSeasonHonors({
    required String clubId,
    String? teamScope,
  }) {
    return _withFallback<SeasonHonorsArchiveDto>(
      () async => SeasonHonorsArchiveDto.fromJson(
        _asMap(await _request(
          '/api/clubs/$clubId/season-honors',
          query: <String, Object?>{'team_scope': teamScope},
        )),
      ),
      () => fixtures.fetchSeasonHonors(clubId: clubId, teamScope: teamScope),
    );
  }

  @override
  Future<TrophyLeaderboardDto> fetchTrophyLeaderboard({
    String? teamScope,
  }) {
    return _withFallback<TrophyLeaderboardDto>(
      () async => TrophyLeaderboardDto.fromJson(
        _asMap(await _request(
          '/api/leaderboards/trophies',
          query: <String, Object?>{'team_scope': teamScope},
        )),
      ),
      () => fixtures.fetchTrophyLeaderboard(teamScope: teamScope),
    );
  }

  Future<T> _withFallback<T>(
    Future<T> Function() liveCall,
    Future<T> Function() fixtureCall,
  ) async {
    if (config.mode == GteBackendMode.fixture) {
      return fixtureCall();
    }
    try {
      return await liveCall();
    } on GteApiException catch (error) {
      if (config.mode == GteBackendMode.liveThenFixture &&
          (error.supportsFixtureFallback ||
              error.type == GteApiErrorType.notFound ||
              error.type == GteApiErrorType.unknown)) {
        return fixtureCall();
      }
      rethrow;
    } on GteParsingException {
      if (config.mode == GteBackendMode.liveThenFixture) {
        return fixtureCall();
      }
      rethrow;
    }
  }

  Future<Object?> _request(
    String path, {
    Map<String, Object?> query = const <String, Object?>{},
  }) async {
    try {
      final GteTransportResponse response = await transport.send(
        GteTransportRequest(
          method: 'GET',
          uri: config.uriFor(path, query),
          headers: const <String, String>{'Accept': 'application/json'},
        ),
      );
      if (response.statusCode >= 400) {
        throw GteApiException(
          type: _errorType(response.statusCode),
          message: _errorMessage(response.body),
          statusCode: response.statusCode,
          cause: response.body,
        );
      }
      return response.body;
    } on GteApiException {
      rethrow;
    } catch (error) {
      throw GteApiException(
        type: GteApiErrorType.network,
        message: 'Unable to load trophy cabinet data.',
        cause: error,
      );
    }
  }
}

class _ClubFixtureStore {
  _ClubFixtureStore.seeded()
      : _brandingByClub = <String, ClubBrandingProfile>{
          'royal-lagos-fc': ClubBrandingProfile(
            selectedThemeId: 'royal-night',
            selectedBackdropId: 'marble-gallery',
            motto: 'Earned prestige, worn with legacy.',
            availableThemes: _themes,
            availableBackdrops: _backdrops,
            reviewStatus: 'Ready for showcase',
            reviewNote:
                'Branding stays within club identity rules and keeps jersey contrast readable.',
          ),
        },
        _ownedByClub = <String, Set<String>>{
          'royal-lagos-fc': <String>{
            'catalog-founder-frame',
            'catalog-grand-banner',
          },
        },
        _equippedByClub = <String, Map<String, String>>{
          'royal-lagos-fc': <String, String>{
            'showcase': 'catalog-founder-frame',
          },
        },
        _purchaseHistoryByClub = <String, List<ClubPurchaseRecord>>{
          'royal-lagos-fc': <ClubPurchaseRecord>[
            ClubPurchaseRecord(
              id: 'purchase-001',
              itemId: 'catalog-founder-frame',
              itemTitle: 'Founder frame',
              category: 'Club identity',
              purchasedAt: DateTime.utc(2026, 2, 14, 16, 30),
              priceCredits: 60,
              confirmationLabel: 'Catalog purchase CP-001',
              statusLabel: 'Equipped in showcase',
              transparencyNote:
                  'Permanent cosmetic unlock. No random reward outcomes.',
              equipped: true,
            ),
          ],
        },
        _brandingQueue = <BrandingReviewCase>[
          const BrandingReviewCase(
            id: 'review-001',
            clubName: 'Royal Lagos FC',
            submittedAtLabel: '2026-03-10 19:40 UTC',
            themeName: 'Royal night',
            backdropName: 'Marble gallery',
            motto: 'Earned prestige, worn with legacy.',
            statusLabel: 'Pending review',
            reviewNote:
                'Verify banner contrast before publishing to global showcase.',
          ),
          const BrandingReviewCase(
            id: 'review-002',
            clubName: 'Atlas Sporting',
            submittedAtLabel: '2026-03-09 18:15 UTC',
            themeName: 'Continental stone',
            backdropName: 'Legacy corridor',
            motto: 'From silverware to dynasty.',
            statusLabel: 'Pending review',
            reviewNote:
                'Backdrop is strong; confirm motto still fits moderation length.',
          ),
        ];

  final Map<String, ClubBrandingProfile> _brandingByClub;
  final Map<String, Set<String>> _ownedByClub;
  final Map<String, Map<String, String>> _equippedByClub;
  final Map<String, List<ClubPurchaseRecord>> _purchaseHistoryByClub;
  final List<BrandingReviewCase> _brandingQueue;

  ClubBrandingProfile brandingFor(String clubId, String? clubName) {
    return _brandingByClub.putIfAbsent(
      clubId,
      () => ClubBrandingProfile(
        selectedThemeId: _themes.first.id,
        selectedBackdropId: _backdrops.first.id,
        motto: '${clubName ?? prettifyClubId(clubId)} built on legacy.',
        availableThemes: _themes,
        availableBackdrops: _backdrops,
        reviewStatus: 'Ready for showcase',
        reviewNote:
            'Branding preview is using club-safe defaults until a live moderation workflow is available.',
      ),
    );
  }

  void saveBranding(String clubId, ClubBrandingProfile branding) {
    _brandingByClub[clubId] = branding.copyWith(
      availableThemes: _themes,
      availableBackdrops: _backdrops,
      reviewStatus: 'Ready for showcase',
      reviewNote: 'Latest branding update saved to the club preview profile.',
    );
  }

  List<ClubCatalogItem> catalogFor(String clubId) {
    final Set<String> owned = _ownedByClub[clubId] ?? <String>{};
    final Map<String, String> equipped =
        _equippedByClub[clubId] ?? <String, String>{};
    return _catalogBlueprints.map((ClubCatalogItem item) {
      CatalogOwnershipStatus status = CatalogOwnershipStatus.available;
      if (equipped[item.slot] == item.id) {
        status = CatalogOwnershipStatus.equipped;
      } else if (owned.contains(item.id)) {
        status = CatalogOwnershipStatus.owned;
      }
      return item.copyWith(ownershipStatus: status);
    }).toList(growable: false);
  }

  List<ClubPurchaseRecord> purchaseHistoryFor(String clubId) {
    return List<ClubPurchaseRecord>.from(
      _purchaseHistoryByClub[clubId] ?? const <ClubPurchaseRecord>[],
      growable: false,
    )..sort(
        (ClubPurchaseRecord left, ClubPurchaseRecord right) =>
            right.purchasedAt.compareTo(left.purchasedAt),
      );
  }

  void purchaseItem(String clubId, ClubCatalogItem item) {
    final Set<String> owned =
        _ownedByClub.putIfAbsent(clubId, () => <String>{});
    owned.add(item.id);
    final List<ClubPurchaseRecord> history = _purchaseHistoryByClub.putIfAbsent(
        clubId, () => <ClubPurchaseRecord>[]);
    final bool equipped =
        (_equippedByClub[clubId] ?? const <String, String>{})[item.slot] ==
            item.id;
    history.insert(
      0,
      ClubPurchaseRecord(
        id: 'purchase-${history.length + 100}',
        itemId: item.id,
        itemTitle: item.title,
        category: item.category,
        purchasedAt: DateTime.now().toUtc(),
        priceCredits: item.priceCredits,
        confirmationLabel: 'Catalog purchase CP-${history.length + 100}',
        statusLabel: equipped ? 'Equipped in club showcase' : 'Owned in locker',
        transparencyNote: item.transparencyNote,
        equipped: equipped,
      ),
    );
  }

  void equipItem(String clubId, ClubCatalogItem item) {
    final Map<String, String> equipped =
        _equippedByClub.putIfAbsent(clubId, () => <String, String>{});
    equipped[item.slot] = item.id;
    final List<ClubPurchaseRecord> history = _purchaseHistoryByClub.putIfAbsent(
        clubId, () => <ClubPurchaseRecord>[]);
    for (int index = 0; index < history.length; index += 1) {
      final ClubPurchaseRecord record = history[index];
      if (record.itemId == item.id) {
        history[index] = record.copyWith(
          equipped: true,
          statusLabel: 'Equipped in club showcase',
        );
      } else if (_itemSlot(record.itemId) == item.slot) {
        history[index] = record.copyWith(
          equipped: false,
          statusLabel: 'Owned in locker',
        );
      }
    }
  }

  ClubAdminAnalytics buildAdminAnalytics() {
    final List<ClubPurchaseRecord> allPurchases = _purchaseHistoryByClub.values
        .expand((List<ClubPurchaseRecord> history) => history)
        .toList(growable: false);
    final double revenue = allPurchases.fold<double>(
      0,
      (double sum, ClubPurchaseRecord record) => sum + record.priceCredits,
    );
    final int equippedCount = _equippedByClub.values.fold<int>(
      0,
      (int sum, Map<String, String> slots) => sum + slots.length,
    );
    return ClubAdminAnalytics(
      revenueSummaries: <ClubRevenueSummary>[
        ClubRevenueSummary(
          label: 'Catalog revenue',
          valueLabel: gteFormatCredits(revenue),
          caption: 'Transparent cosmetic purchases only.',
        ),
        ClubRevenueSummary(
          label: 'Branding reviews',
          valueLabel: '${_brandingQueue.length}',
          caption: 'Pending club identity moderation items.',
        ),
        ClubRevenueSummary(
          label: 'Equipped cosmetics',
          valueLabel: '$equippedCount',
          caption: 'Visible showcase cosmetics across tracked clubs.',
        ),
      ],
      topClubs: const <ClubRankingEntry>[
        ClubRankingEntry(
          rank: 1,
          clubName: 'Royal Lagos FC',
          metricLabel: 'Community prestige',
          valueLabel: '1184 reputation',
          contextLabel: 'Legendary tier',
        ),
        ClubRankingEntry(
          rank: 2,
          clubName: 'Monte Carlo Athletic',
          metricLabel: 'Community prestige',
          valueLabel: '1462 reputation',
          contextLabel: 'Dynasty watch',
        ),
        ClubRankingEntry(
          rank: 3,
          clubName: 'Atlas Sporting',
          metricLabel: 'Trophy cabinet',
          valueLabel: '9 honors',
          contextLabel: 'Continental form',
        ),
      ],
      topDynasties: const <ClubRankingEntry>[
        ClubRankingEntry(
          rank: 1,
          clubName: 'Royal Lagos FC',
          metricLabel: 'Dynasty progression',
          valueLabel: 'Global Dynasty',
          contextLabel: 'Score 84',
        ),
        ClubRankingEntry(
          rank: 2,
          clubName: 'Atlas Sporting',
          metricLabel: 'Dynasty progression',
          valueLabel: 'Dominant Era',
          contextLabel: 'Score 68',
        ),
        ClubRankingEntry(
          rank: 3,
          clubName: 'Nile Athletic',
          metricLabel: 'Dynasty progression',
          valueLabel: 'Emerging Power',
          contextLabel: 'Score 42',
        ),
      ],
      moderationHeadline:
          'Club identity moderation is focused on readable, aspirational showcase assets.',
      moderationHighlights: <String>[
        'Review queue is sized for cosmetic themes, banner copy, and showcase backdrops.',
        'No random reward mechanics or chance-based catalog language is present in these surfaces.',
        'Transparent purchase confirmation remains required before catalog ownership changes.',
      ],
    );
  }

  List<BrandingReviewCase> brandingReviewQueue() {
    return List<BrandingReviewCase>.from(_brandingQueue, growable: false);
  }

  void updateBrandingReview({
    required String reviewId,
    required bool approved,
  }) {
    for (int index = 0; index < _brandingQueue.length; index += 1) {
      final BrandingReviewCase review = _brandingQueue[index];
      if (review.id == reviewId) {
        _brandingQueue[index] = review.copyWith(
          statusLabel: approved ? 'Approved for showcase' : 'Changes requested',
          reviewNote: approved
              ? 'Branding aligns with club identity guidance and showcase readability.'
              : 'Adjust contrast or motto length before resubmitting this club identity update.',
        );
      }
    }
  }

  String? _itemSlot(String itemId) {
    for (final ClubCatalogItem item in _catalogBlueprints) {
      if (item.id == itemId) {
        return item.slot;
      }
    }
    return null;
  }
}

const List<ClubBrandingTheme> _themes = <ClubBrandingTheme>[
  ClubBrandingTheme(
    id: 'royal-night',
    name: 'Royal night',
    description: 'Deep navy presentation with bright legacy trim.',
    bannerLabel: 'Heritage banner',
    primaryColor: '#123C73',
    secondaryColor: '#F5F7FA',
    accentColor: '#E2A400',
  ),
  ClubBrandingTheme(
    id: 'continental-stone',
    name: 'Continental stone',
    description: 'Marble neutrals for trophy cabinet and legacy walls.',
    bannerLabel: 'Cabinet banner',
    primaryColor: '#C7D2DA',
    secondaryColor: '#1E293B',
    accentColor: '#C0841A',
  ),
  ClubBrandingTheme(
    id: 'supporter-flare',
    name: 'Supporter flare',
    description: 'Crowd-led banner tone for fan prestige celebrations.',
    bannerLabel: 'Supporter banner',
    primaryColor: '#8A1538',
    secondaryColor: '#F8E16C',
    accentColor: '#FFD166',
  ),
];

const List<ClubShowcaseBackdrop> _backdrops = <ClubShowcaseBackdrop>[
  ClubShowcaseBackdrop(
    id: 'marble-gallery',
    name: 'Marble gallery',
    description: 'Trophy cabinet walls with calm legacy lighting.',
    gradientColors: <String>['#1E293B', '#0F172A', '#334155'],
    caption: 'Built for trophy cabinet reveals and legacy milestones.',
  ),
  ClubShowcaseBackdrop(
    id: 'stadium-crowd',
    name: 'Stadium crowd',
    description: 'Fan prestige backdrop with low-light flare.',
    gradientColors: <String>['#082F49', '#0F172A', '#123C73'],
    caption: 'Best for club reputation and supporter identity moments.',
  ),
  ClubShowcaseBackdrop(
    id: 'legacy-corridor',
    name: 'Legacy corridor',
    description: 'Quiet showcase tunnel for dynasty progression stories.',
    gradientColors: <String>['#1C1917', '#292524', '#44403C'],
    caption: 'Works well for dynasty eras and retired milestone cards.',
  ),
];

const List<ClubCatalogItem> _catalogBlueprints = <ClubCatalogItem>[
  ClubCatalogItem(
    id: 'catalog-founder-frame',
    title: 'Founder frame',
    category: 'Club identity',
    slot: 'showcase',
    description:
        'Polished showcase frame for club profile and branding panels.',
    priceCredits: 60,
    highlightColor: '#E2A400',
    previewLabel: 'Legacy frame',
    transparencyNote: 'Permanent cosmetic purchase. No random reward outcomes.',
    ownershipStatus: CatalogOwnershipStatus.available,
    isFeatured: true,
  ),
  ClubCatalogItem(
    id: 'catalog-grand-banner',
    title: 'Grand banner',
    category: 'Branding theme',
    slot: 'banner',
    description:
        'Wide banner treatment for club showcase headers and profile cards.',
    priceCredits: 48,
    highlightColor: '#7DE2D1',
    previewLabel: 'Profile banner',
    transparencyNote:
        'Catalog purchase with transparent pricing and permanent ownership.',
    ownershipStatus: CatalogOwnershipStatus.available,
  ),
  ClubCatalogItem(
    id: 'catalog-kit-trim-gold',
    title: 'Gold trim pack',
    category: 'Jersey design',
    slot: 'kit_trim',
    description: 'Accent trim set for home and away jersey customization.',
    priceCredits: 36,
    highlightColor: '#F59E0B',
    previewLabel: 'Jersey trim',
    transparencyNote:
        'Cosmetic trim set only. No gameplay effect or chance element.',
    ownershipStatus: CatalogOwnershipStatus.available,
  ),
  ClubCatalogItem(
    id: 'catalog-cabinet-lights',
    title: 'Cabinet lights',
    category: 'Trophy cabinet',
    slot: 'cabinet',
    description:
        'Warm shelf lighting for featured trophies and showcase panels.',
    priceCredits: 42,
    highlightColor: '#FCD34D',
    previewLabel: 'Cabinet glow',
    transparencyNote:
        'Permanent cabinet cosmetic unlocked through direct purchase.',
    ownershipStatus: CatalogOwnershipStatus.available,
  ),
  ClubCatalogItem(
    id: 'catalog-supporter-mosaic',
    title: 'Supporter mosaic',
    category: 'Showcase',
    slot: 'backdrop',
    description: 'Fan prestige backdrop for club showcase and dynasty recaps.',
    priceCredits: 55,
    highlightColor: '#60A5FA',
    previewLabel: 'Backdrop scene',
    transparencyNote:
        'Fixed-price showcase backdrop with no random variations.',
    ownershipStatus: CatalogOwnershipStatus.available,
    isFeatured: true,
  ),
];

Map<String, Object?> _asMap(Object? value) {
  return GteJson.map(value, label: 'club payload');
}

GteApiErrorType _errorType(int statusCode) {
  if (statusCode == 404) {
    return GteApiErrorType.notFound;
  }
  if (statusCode == 422) {
    return GteApiErrorType.validation;
  }
  if (statusCode >= 500) {
    return GteApiErrorType.unavailable;
  }
  return GteApiErrorType.unknown;
}

String _errorMessage(Object? payload) {
  if (payload is String && payload.trim().isNotEmpty) {
    return payload;
  }
  if (payload is Map) {
    final Map<String, Object?> json = GteJson.map(payload);
    final String? detail = GteJson.stringOrNull(
      json,
      const <String>['detail', 'message', 'error'],
    );
    if (detail != null && detail.isNotEmpty) {
      return detail;
    }
  }
  return 'Club request failed.';
}

String _eventCategoryLabel(ReputationEventCategory category) {
  switch (category) {
    case ReputationEventCategory.league:
      return 'League';
    case ReputationEventCategory.continental:
      return 'Continental';
    case ReputationEventCategory.worldSuperCup:
      return 'World Super Cup';
    case ReputationEventCategory.awards:
      return 'Awards';
    case ReputationEventCategory.general:
      return 'Club';
  }
}

String _prestigeTierLabel(PrestigeTier tier) {
  switch (tier) {
    case PrestigeTier.local:
      return 'Local';
    case PrestigeTier.rising:
      return 'Rising';
    case PrestigeTier.established:
      return 'Established';
    case PrestigeTier.elite:
      return 'Elite';
    case PrestigeTier.legendary:
      return 'Legendary';
    case PrestigeTier.dynasty:
      return 'Dynasty';
  }
}

String _dynastyEraLabel(DynastyEraType value) {
  switch (value) {
    case DynastyEraType.emergingPower:
      return 'Emerging Power';
    case DynastyEraType.dominantEra:
      return 'Dominant Era';
    case DynastyEraType.continentalDynasty:
      return 'Continental Dynasty';
    case DynastyEraType.globalDynasty:
      return 'Global Dynasty';
    case DynastyEraType.fallenGiant:
      return 'Fallen Giant';
    case DynastyEraType.none:
      return 'No Active Dynasty';
  }
}
