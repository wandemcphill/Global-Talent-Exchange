import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/constants/app_spacing.dart';
import '../../data/gte_api_repository.dart';
import '../../data/gte_authed_api.dart';
import 'package:gte_frontend/features/compete/domain/competition_models.dart';
import 'package:gte_frontend/features/match_center/models/match_view_state.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/providers/auth_provider.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';
import '../../shared/widgets/gtex_premium_panels.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';
import '../shared/data/gte_feature_support.dart';
import 'data/live_match_fixtures.dart';
import 'live_match_session.dart';
import 'models/match_event.dart';
import 'models/match_timeline_frame.dart';
import 'match_viewer_capability.dart';

class LiveMatchViewerBootstrap {
  const LiveMatchViewerBootstrap({
    required this.matchKey,
    required this.viewer,
    required this.competition,
    this.spectateSession,
    this.initialViewState,
  });

  final String matchKey;
  final JsonMap viewer;
  final CompetitionSummary competition;
  final LiveMatchSpectateSession? spectateSession;
  final MatchViewState? initialViewState;
}

class LiveMatchViewerQualifiedRoute {
  const LiveMatchViewerQualifiedRoute({
    required this.bootstrap,
    required this.initialViewState,
  });

  final LiveMatchViewerBootstrap bootstrap;
  final MatchViewState initialViewState;
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
    ], auth: false);
    final CompetitionSummary competition = buildLiveViewerCompetition(
      matchKey,
      viewer,
    );
    final MatchViewState initialViewState = MatchViewState.fromJson(
      await _fetchFirstMap(api, <String>[
        '/api/match-viewer/$matchKey/session',
      ], auth: false),
    );
    LiveMatchSpectateSession? spectateSession;
    if (isAuthenticated) {
      try {
        final Object? response = await api.post(
          '/api/matches/$matchKey/spectate',
        );
        spectateSession = LiveMatchSpectateSession.fromJson(response);
      } catch (_) {
        // Viewer bootstrap remains the source of truth for live availability.
      }
    }
    return LiveMatchViewerBootstrap(
      matchKey: matchKey,
      viewer: viewer,
      competition: competition,
      spectateSession: spectateSession,
      initialViewState: initialViewState,
    );
  }

  @override
  Future<MatchViewState> loadViewState(
    String matchKey, {
    String? continuationToken,
  }) async {
    final JsonMap session = await _fetchFirstMap(
      api,
      <String>['/api/match-viewer/$matchKey/session'],
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

final liveMatchViewerQualifiedRouteProvider = FutureProvider.autoDispose.family<
  LiveMatchViewerQualifiedRoute,
  String
>((Ref ref, String matchKey) async {
  final LiveMatchViewerRepository repository = ref.watch(
    liveMatchViewerRepositoryProvider,
  );
  final LiveMatchViewerBootstrap bootstrap = await repository.resolveBootstrap(
    matchKey,
  );
  final MatchViewState initialViewState =
      bootstrap.initialViewState ?? await repository.loadViewState(matchKey);
  return LiveMatchViewerQualifiedRoute(
    bootstrap: bootstrap,
    initialViewState: qualifyLiveMatchViewerState(
      matchKey: matchKey,
      state: initialViewState,
    ),
  );
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

MatchViewState qualifyLiveMatchViewerState({
  required String matchKey,
  required MatchViewState state,
}) {
  final String normalizedMatchKey = matchKey.trim();
  final String resolvedMatchId = state.matchId.trim();
  if (resolvedMatchId.isEmpty || resolvedMatchId != normalizedMatchKey) {
    throw const GteApiException(
      type: GteApiErrorType.parsing,
      message:
          'This 2D matchday session is unavailable for the selected match.',
    );
  }
  if (state.frames.isEmpty) {
    throw const GteApiException(
      type: GteApiErrorType.parsing,
      message:
          'This 2D matchday session is unavailable because the live timeline was incomplete.',
    );
  }
  final int lastFrameSecond = state.frames.last.timeSeconds.ceil();
  if (state.segmentEndSeconds < state.segmentStartSeconds) {
    throw const GteApiException(
      type: GteApiErrorType.parsing,
      message:
          'This 2D matchday session is unavailable because the live segment timing was inconsistent.',
    );
  }
  if (state.durationSeconds < state.segmentEndSeconds) {
    throw const GteApiException(
      type: GteApiErrorType.parsing,
      message:
          'This 2D matchday session is unavailable because the verified timeline ended unexpectedly.',
    );
  }
  if (state.durationSeconds < lastFrameSecond ||
      state.segmentEndSeconds < lastFrameSecond) {
    throw const GteApiException(
      type: GteApiErrorType.parsing,
      message:
          'This 2D matchday session is unavailable because the live segment did not verify cleanly.',
    );
  }
  if (state.hasMoreSegments &&
      (state.nextSegmentToken?.trim().isEmpty ?? true)) {
    throw const GteApiException(
      type: GteApiErrorType.parsing,
      message:
          'This 2D matchday session is unavailable because the next live segment could not be verified.',
    );
  }
  return state;
}

LiveMatchSnapshot liveMatchSnapshotFromQualifiedViewState(
  MatchViewState state,
) {
  final MatchTimelineFrame frame = state.lastFrame;
  final List<LiveMatchEvent> events = state.events
      .map(_liveEventFromMatchEvent)
      .toList(growable: false);
  return LiveMatchSnapshot(
    matchId: state.matchId,
    homeTeam: state.homeTeam.teamName,
    awayTeam: state.awayTeam.teamName,
    homeScore: frame.homeScore,
    awayScore: frame.awayScore,
    minute: frame.clockMinute.floor(),
    phase: _livePhaseFromViewFrame(frame),
    momentum: const <int>[],
    commentary: events,
    homeLineup: _lineupFromFrame(frame, side: MatchViewerSide.home),
    awayLineup: _lineupFromFrame(frame, side: MatchViewerSide.away),
    substitutions: events
        .where(
          (LiveMatchEvent event) =>
              event.type == LiveMatchEventType.substitution,
        )
        .toList(growable: false),
    cards: events
        .where((LiveMatchEvent event) => event.type == LiveMatchEventType.card)
        .toList(growable: false),
    tacticalSuggestions: const <LiveMatchTacticalSuggestion>[],
    keyMoments: const <LiveMatchHighlightClip>[],
    highlights: const <LiveMatchHighlightClip>[],
    standardHighlightExpiresAt: DateTime.fromMillisecondsSinceEpoch(
      0,
      isUtc: true,
    ),
    premiumHighlightExpiresAt: DateTime.fromMillisecondsSinceEpoch(
      0,
      isUtc: true,
    ),
  );
}

LiveMatchPhase _livePhaseFromViewFrame(MatchTimelineFrame frame) {
  switch (frame.phase) {
    case MatchViewerPhase.halftime:
      return LiveMatchPhase.halftime;
    case MatchViewerPhase.fulltime:
      return LiveMatchPhase.fullTime;
    case MatchViewerPhase.kickoff:
    case MatchViewerPhase.openPlay:
    case MatchViewerPhase.setPiece:
      return frame.clockMinute >= 45
          ? LiveMatchPhase.secondHalf
          : LiveMatchPhase.firstHalf;
  }
}

LiveMatchEvent _liveEventFromMatchEvent(MatchEvent event) {
  return LiveMatchEvent(
    minute: event.minute,
    title:
        event.bannerText.trim().isNotEmpty ? event.bannerText : event.type.name,
    detail: event.commentary,
    team: event.teamName ?? '',
    type: _liveEventTypeFromViewEvent(event.type),
    isKeyMoment: event.isMajor,
  );
}

LiveMatchEventType _liveEventTypeFromViewEvent(MatchViewerEventType type) {
  switch (type) {
    case MatchViewerEventType.goal:
      return LiveMatchEventType.goal;
    case MatchViewerEventType.redCard:
    case MatchViewerEventType.yellowCard:
      return LiveMatchEventType.card;
    case MatchViewerEventType.substitution:
      return LiveMatchEventType.substitution;
    case MatchViewerEventType.kickoff:
    case MatchViewerEventType.save:
    case MatchViewerEventType.miss:
    case MatchViewerEventType.foul:
    case MatchViewerEventType.offside:
    case MatchViewerEventType.injury:
    case MatchViewerEventType.halftime:
    case MatchViewerEventType.fulltime:
    case MatchViewerEventType.attack:
    case MatchViewerEventType.pass:
    case MatchViewerEventType.setPiece:
    case MatchViewerEventType.penalty:
    case MatchViewerEventType.neutral:
      return LiveMatchEventType.incident;
  }
}

List<LiveMatchLineupPlayer> _lineupFromFrame(
  MatchTimelineFrame frame, {
  required MatchViewerSide side,
}) {
  return frame.players
      .where((MatchViewerPlayerFrame player) => player.side == side)
      .map(
        (MatchViewerPlayerFrame player) => LiveMatchLineupPlayer(
          name: player.label,
          position: _positionLabel(player),
          rating: 0,
          playerId: player.playerId,
        ),
      )
      .toList(growable: false);
}

String _positionLabel(MatchViewerPlayerFrame player) {
  return switch (player.role) {
    MatchViewerRole.goalkeeper => 'GK',
    MatchViewerRole.defender => 'DF',
    MatchViewerRole.midfielder => 'MF',
    MatchViewerRole.forward => 'FW',
  };
}

CompetitionSummary buildLiveViewerCompetition(String matchKey, JsonMap viewer) {
  final JsonMap? competitionPayload =
      jsonMapOrNull(viewer['competition_summary']) ??
      jsonMapOrNull(viewer['competition']);
  if (competitionPayload == null) {
    throw GteApiException(
      type: GteApiErrorType.parsing,
      message:
          'This live match viewer route is blocked because the backend did not provide a competition summary for $matchKey.',
    );
  }
  _requireLiveViewerCompetitionSummary(matchKey, competitionPayload);
  return CompetitionSummary.fromJson(competitionPayload);
}

void _requireLiveViewerCompetitionSummary(String matchKey, JsonMap payload) {
  final JsonMap financials =
      jsonMapOrNull(
        _firstPresentValue(payload, <String>[
          'financials',
          'fees',
          'fee_summary',
        ]),
      ) ??
      const <String, Object?>{};
  final JsonMap? eligibility = jsonMapOrNull(
    _firstPresentValue(payload, <String>[
      'join_eligibility',
      'joinEligibility',
    ]),
  );
  final List<String> missing = <String>[];

  void requireText(List<String> keys, String label) {
    if (_firstNonEmptyString(<JsonMap>[payload], keys) == null) {
      missing.add(label);
    }
  }

  void requirePresent(List<JsonMap> maps, List<String> keys, String label) {
    if (_firstPresentValueFromMaps(maps, keys) == null) {
      missing.add(label);
    }
  }

  void requireTimestamp(List<String> keys, String label) {
    final Object? value = _firstPresentValue(payload, keys);
    if (_dateTimeOrNull(value) == null) {
      missing.add(label);
    }
  }

  requireText(<String>['id'], 'id');
  requireText(<String>['name'], 'name');
  requireText(<String>[
    'format',
    'competition_format',
    'competitionFormat',
  ], 'format');
  requireText(<String>['visibility'], 'visibility');
  requireText(<String>['status', 'contest_status', 'contestStatus'], 'status');
  requireText(<String>['creator_id', 'creatorId'], 'creator_id');
  requirePresent(
    <JsonMap>[payload],
    <String>['participant_count', 'participantCount'],
    'participant_count',
  );
  requirePresent(
    <JsonMap>[payload],
    <String>['capacity', 'max_participants', 'maxParticipants'],
    'capacity',
  );
  requireText(<String>['rules_summary', 'rulesSummary'], 'rules_summary');
  requirePresent(
    <JsonMap>[payload, financials],
    <String>['currency'],
    'currency',
  );
  requirePresent(
    <JsonMap>[payload, financials],
    <String>['entry_fee', 'entryFee'],
    'entry_fee',
  );
  requirePresent(
    <JsonMap>[payload, financials],
    <String>['platform_fee_pct', 'platformFeePct'],
    'platform_fee_pct',
  );
  requirePresent(
    <JsonMap>[payload, financials],
    <String>['host_fee_pct', 'hostFeePct'],
    'host_fee_pct',
  );
  requirePresent(
    <JsonMap>[payload, financials],
    <String>['platform_fee_amount', 'platformFeeAmount'],
    'platform_fee_amount',
  );
  requirePresent(
    <JsonMap>[payload, financials],
    <String>['host_fee_amount', 'hostFeeAmount'],
    'host_fee_amount',
  );
  requirePresent(
    <JsonMap>[payload, financials],
    <String>['prize_pool', 'prizePool'],
    'prize_pool',
  );
  requirePresent(
    <JsonMap>[payload, financials],
    <String>['payout_structure', 'payoutStructure'],
    'payout_structure',
  );
  if (eligibility == null) {
    missing.add('join_eligibility');
  } else {
    requirePresent(
      <JsonMap>[eligibility],
      <String>['eligible'],
      'join_eligibility.eligible',
    );
  }
  requireTimestamp(<String>['created_at', 'createdAt'], 'created_at');
  requireTimestamp(<String>['updated_at', 'updatedAt'], 'updated_at');

  if (missing.isNotEmpty) {
    throw GteApiException(
      type: GteApiErrorType.parsing,
      message:
          'This live match viewer route is blocked because the backend competition summary for $matchKey was incomplete: ${missing.join(', ')}.',
    );
  }
}

Object? _firstPresentValue(JsonMap map, List<String> keys) {
  return _firstPresentValueFromMaps(<JsonMap>[map], keys);
}

Object? _firstPresentValueFromMaps(List<JsonMap> maps, List<String> keys) {
  for (final JsonMap map in maps) {
    for (final String key in keys) {
      final Object? value = map[key];
      if (value != null) {
        return value;
      }
    }
  }
  return null;
}

String? _firstNonEmptyString(List<JsonMap> maps, List<String> keys) {
  final String? text =
      stringOrNullValue(_firstPresentValueFromMaps(maps, keys))?.trim();
  if (text == null || text.isEmpty) {
    return null;
  }
  return text;
}

DateTime? _dateTimeOrNull(Object? value) {
  if (value is DateTime) {
    return value;
  }
  final String? text = stringOrNullValue(value)?.trim();
  if (text == null || text.isEmpty) {
    return null;
  }
  return DateTime.tryParse(text);
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
    this.detailTitle = 'Viewer contract unavailable',
    this.detailSubtitle =
        'This route stays visibly blocked until the mounted runtime can answer with real match-viewer data.',
    this.supplementalPanels = const <Widget>[],
  });

  final String title;
  final String subtitle;
  final String reason;
  final String detailTitle;
  final String detailSubtitle;
  final List<Widget> supplementalPanels;

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
          subtitle: detailSubtitle,
          child: GteStatePanel(
            title: detailTitle,
            message: reason,
            icon: Icons.error_outline_rounded,
            accentColor: Theme.of(context).colorScheme.error,
          ),
        ),
        ...supplementalPanels,
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
    MatchViewerCapability.legacyRuntime => GtexSurfaceTone.danger,
    MatchViewerCapability.blocked => GtexSurfaceTone.danger,
  };
}
