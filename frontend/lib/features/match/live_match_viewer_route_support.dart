import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/constants/app_spacing.dart';
import '../../data/gte_api_repository.dart';
import '../../data/gte_authed_api.dart';
import '../../models/competition_models.dart';
import '../../models/match_type.dart';
import '../../models/match_view_state.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/providers/auth_provider.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';
import '../../shared/widgets/gtex_premium_panels.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';
import '../shared/data/gte_feature_support.dart';
import 'match_viewer_capability.dart';

class LiveMatchViewerBootstrap {
  const LiveMatchViewerBootstrap({
    required this.matchKey,
    required this.viewer,
    required this.competition,
  });

  final String matchKey;
  final JsonMap viewer;
  final CompetitionSummary competition;
}

abstract class LiveMatchViewerRepository {
  Future<LiveMatchViewerBootstrap> resolveBootstrap(String matchKey);

  Future<MatchViewState> loadViewState(
    String matchKey, {
    String? continuationToken,
  });
}

class ApiLiveMatchViewerRepository implements LiveMatchViewerRepository {
  const ApiLiveMatchViewerRepository({
    required this.api,
    required this.isAuthenticated,
  });

  final GteAuthedApi api;
  final bool isAuthenticated;

  @override
  Future<LiveMatchViewerBootstrap> resolveBootstrap(String matchKey) async {
    final JsonMap viewer = await _fetchFirstMap(api, <String>[
      '/api/match-viewer/$matchKey',
      '/match-viewer/$matchKey',
    ], auth: false);
    await _fetchFirstMap(api, <String>[
      '/api/match-viewer/$matchKey/session',
      '/match-viewer/$matchKey/session',
    ], auth: false);
    if (isAuthenticated) {
      try {
        await api.post('/api/matches/$matchKey/spectate');
      } catch (_) {
        // Viewer bootstrap remains the source of truth for live availability.
      }
    }
    return LiveMatchViewerBootstrap(
      matchKey: matchKey,
      viewer: viewer,
      competition: buildLiveViewerCompetition(matchKey, viewer),
    );
  }

  @override
  Future<MatchViewState> loadViewState(
    String matchKey, {
    String? continuationToken,
  }) async {
    final JsonMap session = await _fetchFirstMap(
      api,
      <String>[
        '/api/match-viewer/$matchKey/session',
        '/match-viewer/$matchKey/session',
      ],
      auth: false,
      query: <String, Object?>{
        if (continuationToken != null && continuationToken.isNotEmpty)
          'token': continuationToken,
      },
    );
    return MatchViewState.fromJson(session);
  }
}

final Provider<LiveMatchViewerRepository> liveMatchViewerRepositoryProvider =
    Provider<LiveMatchViewerRepository>((Ref ref) {
      return ApiLiveMatchViewerRepository(
        api: ref.watch(authedApiProvider),
        isAuthenticated: ref.watch(isAuthenticatedProvider),
      );
    });

final liveMatchViewerBootstrapProvider = FutureProvider.autoDispose
    .family<LiveMatchViewerBootstrap, String>((Ref ref, String matchKey) {
      return ref
          .watch(liveMatchViewerRepositoryProvider)
          .resolveBootstrap(matchKey);
    });

Future<LiveMatchViewerBootstrap> resolveLiveMatchViewerBootstrap(
  WidgetRef ref,
  String matchKey,
) {
  return ref.read(liveMatchViewerRepositoryProvider).resolveBootstrap(matchKey);
}

Future<MatchViewState> loadLiveMatchViewState(
  WidgetRef ref,
  String matchKey, {
  String? continuationToken,
}) {
  return ref
      .read(liveMatchViewerRepositoryProvider)
      .loadViewState(matchKey, continuationToken: continuationToken);
}

CompetitionSummary buildLiveViewerCompetition(String matchKey, JsonMap viewer) {
  final DateTime now = DateTime.now().toUtc();
  final String title = stringValue(
    viewer['title'],
    fallback: stringOrNullValue(viewer['match_label']) ?? 'Live match spectate',
  );
  return CompetitionSummary(
    id: matchKey,
    name: title,
    format: CompetitionFormat.cup,
    visibility: CompetitionVisibility.public,
    status: CompetitionStatus.inProgress,
    creatorId: 'gtex-live',
    creatorName: 'GTEX Live',
    participantCount: 2,
    capacity: 2,
    currency: 'coin',
    entryFee: 0,
    platformFeePct: 0,
    hostFeePct: 0,
    platformFeeAmount: 0,
    hostFeeAmount: 0,
    prizePool: 0,
    payoutStructure: const <CompetitionPayoutBreakdown>[],
    rulesSummary: 'Live match viewer route backed by match-viewer payloads.',
    matchType: MatchType.gtexHosted,
    joinEligibility: const CompetitionJoinEligibility(
      eligible: false,
      reason: 'spectate_only',
    ),
    beginnerFriendly: true,
    createdAt: now,
    updatedAt: now,
  );
}

class MatchRouteLoadingScreen extends StatelessWidget {
  const MatchRouteLoadingScreen({
    super.key,
    required this.title,
    required this.subtitle,
    required this.capability,
  });

  final String title;
  final String subtitle;
  final MatchViewerCapability capability;

  @override
  Widget build(BuildContext context) {
    return AppPageLayout(
      title: title,
      subtitle: subtitle,
      trailing: _RouteBadgeRow(
        status: DataSourceStatus.live,
        capability: capability,
      ),
      children: <Widget>[
        GtexHeroPanel(
          eyebrow: 'MATCH ROUTE VERIFY',
          title: title,
          description: subtitle,
          metrics: <Widget>[
            GtexPill(
              label: capability.label.replaceAll('_', ' '),
              tone: _capabilityTone(capability),
            ),
            const GtexPill(
              label: 'LIVE ENDPOINT CHECK',
              tone: GtexSurfaceTone.live,
            ),
          ],
        ),
        GtexSectionPanel(
          eyebrow: 'RUNTIME GATE',
          title: 'Verifying shipped capability',
          subtitle:
              'The active shell only opens this match route after the live match-viewer session confirms the mounted capability.',
          child: const GteStatePanel(
            title: 'Loading route',
            message: 'Verifying the live route capability before entry.',
            isLoading: true,
          ),
        ),
      ],
    );
  }
}

class MatchRouteBlockedScreen extends StatelessWidget {
  const MatchRouteBlockedScreen({
    super.key,
    required this.title,
    required this.subtitle,
    required this.reason,
  });

  final String title;
  final String subtitle;
  final String reason;

  @override
  Widget build(BuildContext context) {
    return AppPageLayout(
      title: title,
      subtitle: subtitle,
      trailing: const _RouteBadgeRow(
        status: DataSourceStatus.blocked,
        capability: MatchViewerCapability.blocked,
      ),
      children: <Widget>[
        GtexHeroPanel(
          eyebrow: 'MATCH ROUTE GATE',
          title: title,
          description: subtitle,
          metrics: const <Widget>[
            GtexPill(label: 'Route blocked', tone: GtexSurfaceTone.danger),
            GtexPill(label: 'BLOCKED', tone: GtexSurfaceTone.danger),
            GtexPill(label: 'TRUTH PRESERVED', tone: GtexSurfaceTone.warning),
          ],
        ),
        GtexSectionPanel(
          eyebrow: 'BLOCKED DETAIL',
          title: 'Blocked detail',
          subtitle:
              'This route stays visibly blocked until the mounted runtime can answer with real match-viewer data.',
          child: GteStatePanel(
            title: 'Viewer contract unavailable',
            message: reason,
            icon: Icons.error_outline_rounded,
            accentColor: Theme.of(context).colorScheme.error,
          ),
        ),
      ],
    );
  }
}

class MatchRouteCapabilityOverlay extends StatelessWidget {
  const MatchRouteCapabilityOverlay({
    super.key,
    required this.child,
    required this.capability,
    this.status = DataSourceStatus.live,
  });

  final Widget child;
  final MatchViewerCapability capability;
  final DataSourceStatus status;

  @override
  Widget build(BuildContext context) {
    if (!kDebugMode) {
      return child;
    }
    return Stack(
      fit: StackFit.expand,
      children: <Widget>[
        child,
        Positioned(
          top: spacingMD,
          right: spacingMD,
          child: SafeArea(
            child: GteSurfacePanel(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              accentColor: capability.color(context),
              child: IgnorePointer(
                child: _RouteBadgeRow(status: status, capability: capability),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _RouteBadgeRow extends StatelessWidget {
  const _RouteBadgeRow({required this.status, required this.capability});

  final DataSourceStatus status;
  final MatchViewerCapability capability;

  @override
  Widget build(BuildContext context) {
    if (!kDebugMode) {
      return const SizedBox.shrink();
    }
    return Wrap(
      spacing: spacingSM,
      runSpacing: spacingSM,
      children: <Widget>[
        DataSourceBadge(status: status),
        MatchViewerCapabilityBadge(capability: capability),
      ],
    );
  }
}

Future<JsonMap> _fetchFirstMap(
  GteAuthedApi api,
  List<String> paths, {
  required bool auth,
  Map<String, Object?> query = const <String, Object?>{},
}) async {
  GteApiException? lastError;
  for (final String path in paths) {
    try {
      return await api.getMap(path, auth: auth, query: query);
    } on GteApiException catch (error) {
      lastError = error;
      if (error.statusCode == 404 || error.statusCode == 405) {
        continue;
      }
      rethrow;
    }
  }
  throw lastError ??
      const GteApiException(
        type: GteApiErrorType.notFound,
        message: 'No live match viewer endpoint responded for this match key.',
      );
}

GtexSurfaceTone _capabilityTone(MatchViewerCapability capability) {
  return switch (capability) {
    MatchViewerCapability.twoD => GtexSurfaceTone.live,
    MatchViewerCapability.pseudo3d => GtexSurfaceTone.info,
    MatchViewerCapability.flutter3d => GtexSurfaceTone.warning,
    MatchViewerCapability.native3d => GtexSurfaceTone.success,
    MatchViewerCapability.blocked => GtexSurfaceTone.danger,
  };
}
