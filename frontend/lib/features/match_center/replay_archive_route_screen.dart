import 'package:flutter/material.dart';

import '../../data/gte_api_repository.dart';
import '../../data/gte_authed_api.dart';
import '../../features/navigation_guards/gte_navigation_guards.dart';
import '../../features/shared/data/gte_feature_support.dart';
import '../../shared/auth/auth_identity_store.dart';
import '../../shared/models/auth_session.dart';
import '../../widgets/gte_metric_chip.dart';
import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';

class GteReplayArchiveRouteScreen extends StatefulWidget {
  const GteReplayArchiveRouteScreen({
    super.key,
    required this.dependencies,
    this.clubName,
    this.repository,
  });

  final GteNavigationDependencies dependencies;
  final String? clubName;
  final ReplayArchiveRouteRepository? repository;

  @override
  State<GteReplayArchiveRouteScreen> createState() =>
      _GteReplayArchiveRouteScreenState();
}

class _GteReplayArchiveRouteScreenState
    extends State<GteReplayArchiveRouteScreen> {
  late final ReplayArchiveRouteRepository _repository =
      widget.repository ??
      ReplayArchiveRouteRepository.standard(dependencies: widget.dependencies);
  late Future<ReplayArchiveOverview> _future = _loadOverview();

  String get _resolvedClubName {
    final String trimmed = (widget.clubName ?? '').trim();
    return trimmed.isEmpty ? 'Your club' : trimmed;
  }

  Future<ReplayArchiveOverview> _loadOverview() {
    return _repository.loadOverview(
      isAuthenticated: widget.dependencies.isAuthenticated,
    );
  }

  Future<void> _refresh() async {
    setState(() {
      _future = _loadOverview();
    });
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: const Text('Replay archive'),
          actions: <Widget>[
            IconButton(
              onPressed: _refresh,
              icon: const Icon(Icons.refresh_outlined),
            ),
          ],
        ),
        body: FutureBuilder<ReplayArchiveOverview>(
          future: _future,
          builder: (
            BuildContext context,
            AsyncSnapshot<ReplayArchiveOverview> snapshot,
          ) {
            if (snapshot.connectionState != ConnectionState.done &&
                !snapshot.hasData) {
              return const Padding(
                padding: EdgeInsets.all(20),
                child: GteStatePanel(
                  eyebrow: 'REPLAY ARCHIVE',
                  title: 'Loading replay archive',
                  message:
                      'Checking public replay visibility and participant access before opening archived match surfaces.',
                  icon: Icons.video_library_outlined,
                  accentColor: GteShellTheme.accentArena,
                  isLoading: true,
                ),
              );
            }
            if (snapshot.hasError && !snapshot.hasData) {
              return ListView(
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
                children: <Widget>[
                  GteStatePanel(
                    eyebrow: 'REPLAY ARCHIVE',
                    title: 'Replay archive unavailable',
                    message:
                        'The replay policy layer could not be reached right now, so this route is not falling back to the live matchday hub.\n\n${snapshot.error}',
                    icon: Icons.error_outline,
                    accentColor: GteShellTheme.accentWarm,
                  ),
                ],
              );
            }

            final ReplayArchiveOverview overview =
                snapshot.data ?? const ReplayArchiveOverview();
            return RefreshIndicator(
              onRefresh: _refresh,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
                children: <Widget>[
                  GteSurfacePanel(
                    emphasized: true,
                    accentColor: GteShellTheme.accentArena,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          '$_resolvedClubName replay discovery now runs through the replay-archive policy layer.',
                          style: Theme.of(context).textTheme.headlineSmall,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Public finals and approved late-round replays can surface here, while participant and competition-scoped archives stay gated to signed-in users.',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                        const SizedBox(height: 16),
                        Wrap(
                          spacing: 12,
                          runSpacing: 12,
                          children: <Widget>[
                            GteMetricChip(
                              label: 'Public replays',
                              value: overview.publicFeatured.length.toString(),
                            ),
                            GteMetricChip(
                              label: 'Your access',
                              value:
                                  widget.dependencies.isAuthenticated
                                      ? overview.myReplays.length.toString()
                                      : 'Sign in',
                            ),
                            const GteMetricChip(
                              label: 'Policy source',
                              value: '/replays',
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 18),
                  if (!widget.dependencies.isAuthenticated)
                    GteSurfacePanel(
                      accentColor: GteShellTheme.accentWarm,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(
                            'Participant replay access requires sign-in',
                            style: Theme.of(context).textTheme.titleLarge,
                          ),
                          const SizedBox(height: 8),
                          Text(
                            overview.personalLaneMessage ??
                                'Sign in to see participant-only and competition-scoped replays.',
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                        ],
                      ),
                    )
                  else
                    _ReplayArchiveSection(
                      title: 'Your accessible replays',
                      description:
                          'Competition and participant replay visibility is scoped by the replay-archive policy layer.',
                      entries: overview.myReplays,
                      emptyMessage:
                          overview.personalLaneMessage ??
                          'No participant or competition-scoped replays are visible to this account yet.',
                    ),
                  const SizedBox(height: 18),
                  _ReplayArchiveSection(
                    title: 'Featured public replays',
                    description:
                        'Only replay metadata approved for public visibility is listed here.',
                    entries: overview.publicFeatured,
                    emptyMessage:
                        'No public replay archive entries are available right now.',
                  ),
                ],
              ),
            );
          },
        ),
      ),
    );
  }
}

class _ReplayArchiveSection extends StatelessWidget {
  const _ReplayArchiveSection({
    required this.title,
    required this.description,
    required this.entries,
    required this.emptyMessage,
  });

  final String title;
  final String description;
  final List<ReplayArchiveEntry> entries;
  final String emptyMessage;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        GteSurfacePanel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(title, style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 8),
              Text(description, style: Theme.of(context).textTheme.bodyMedium),
            ],
          ),
        ),
        const SizedBox(height: 12),
        if (entries.isEmpty)
          GteStatePanel(
            title: 'No replay entries',
            message: emptyMessage,
            icon: Icons.video_library_outlined,
          )
        else
          ...entries.map(
            (ReplayArchiveEntry entry) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: GteSurfacePanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      entry.matchLabel,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 6),
                    Text(
                      entry.competitionLabel,
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 10,
                      runSpacing: 10,
                      children: <Widget>[
                        GteMetricChip(label: 'State', value: entry.stateLabel),
                        GteMetricChip(
                          label: 'Score',
                          value: '${entry.homeGoals}-${entry.awayGoals}',
                        ),
                        GteMetricChip(
                          label: 'Visibility',
                          value: entry.visibilityLabel,
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Text(
                      'Kickoff ${entry.scheduledStartLabel}',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
            ),
          ),
      ],
    );
  }
}

class ReplayArchiveOverview {
  const ReplayArchiveOverview({
    this.publicFeatured = const <ReplayArchiveEntry>[],
    this.myReplays = const <ReplayArchiveEntry>[],
    this.personalLaneMessage =
        'Sign in to see participant-only and competition-scoped replays.',
  });

  final List<ReplayArchiveEntry> publicFeatured;
  final List<ReplayArchiveEntry> myReplays;
  final String? personalLaneMessage;
}

class ReplayArchiveEntry {
  const ReplayArchiveEntry({
    required this.replayId,
    required this.fixtureId,
    required this.homeClubName,
    required this.awayClubName,
    required this.homeGoals,
    required this.awayGoals,
    required this.competitionName,
    required this.scheduledStart,
    required this.live,
    this.stageName,
    this.finalWhistleAt,
    this.isFinal = false,
    this.resolvedVisibility = 'competition',
  });

  final String replayId;
  final String fixtureId;
  final String homeClubName;
  final String awayClubName;
  final int homeGoals;
  final int awayGoals;
  final String competitionName;
  final DateTime scheduledStart;
  final bool live;
  final String? stageName;
  final DateTime? finalWhistleAt;
  final bool isFinal;
  final String resolvedVisibility;

  factory ReplayArchiveEntry.fromJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'replay archive summary');
    final JsonMap homeClub = jsonMap(
      json['home_club'],
      label: 'home club',
      fallback: const <String, Object?>{},
    );
    final JsonMap awayClub = jsonMap(
      json['away_club'],
      label: 'away club',
      fallback: const <String, Object?>{},
    );
    final JsonMap scoreline = jsonMap(
      json['scoreline'],
      label: 'replay scoreline',
      fallback: const <String, Object?>{},
    );
    final JsonMap competition = jsonMap(
      json['competition_context'],
      label: 'replay competition context',
      fallback: const <String, Object?>{},
    );
    return ReplayArchiveEntry(
      replayId: stringValue(json['replay_id']),
      fixtureId: stringValue(json['fixture_id']),
      homeClubName: stringValue(homeClub['club_name'], fallback: 'Home'),
      awayClubName: stringValue(awayClub['club_name'], fallback: 'Away'),
      homeGoals: intValue(scoreline['home_goals']),
      awayGoals: intValue(scoreline['away_goals']),
      competitionName: stringValue(
        competition['competition_name'],
        fallback: 'Replay archive',
      ),
      scheduledStart:
          dateTimeValue(json['scheduled_start']) ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true),
      live: boolValue(json['live']),
      stageName: stringOrNullValue(competition['stage_name']),
      finalWhistleAt: dateTimeValue(json['final_whistle_at']),
      isFinal: boolValue(competition['is_final']),
      resolvedVisibility: stringValue(
        competition['resolved_visibility'],
        fallback: stringValue(
          competition['replay_visibility'],
          fallback: 'competition',
        ),
      ),
    );
  }

  String get matchLabel => '$homeClubName vs $awayClubName';

  String get competitionLabel {
    final String stage = (stageName ?? '').trim();
    if (stage.isEmpty) {
      return competitionName;
    }
    return '$competitionName • $stage';
  }

  String get stateLabel {
    if (live) {
      return 'Live';
    }
    if (finalWhistleAt != null) {
      return 'Archived';
    }
    return 'Scheduled';
  }

  String get visibilityLabel {
    final String normalized = resolvedVisibility.trim().toLowerCase();
    switch (normalized) {
      case 'public':
        return 'Public';
      case 'participants':
        return 'Participants';
      case 'competition':
        return 'Competition';
      case 'private':
        return 'Private';
      default:
        return normalized.isEmpty ? 'Scoped' : normalized;
    }
  }

  String get scheduledStartLabel {
    final DateTime local = scheduledStart.toLocal();
    final String month = local.month.toString().padLeft(2, '0');
    final String day = local.day.toString().padLeft(2, '0');
    final String hour = local.hour.toString().padLeft(2, '0');
    final String minute = local.minute.toString().padLeft(2, '0');
    return '${local.year}-$month-$day $hour:$minute';
  }
}

abstract class ReplayArchiveRouteRepository {
  Future<ReplayArchiveOverview> loadOverview({required bool isAuthenticated});

  factory ReplayArchiveRouteRepository.standard({
    required GteNavigationDependencies dependencies,
  }) {
    final GteBackendMode resolvedMode = gteProductionBackendMode(
      dependencies.backendMode,
    );
    if (resolvedMode == GteBackendMode.fixture) {
      return const EmptyReplayArchiveRouteRepository();
    }
    return ApiReplayArchiveRouteRepository(
      api: GteAuthedApi(
        config: GteRepositoryConfig(
          baseUrl: dependencies.apiBaseUrl,
          mode: resolvedMode,
        ),
        transport: createModeAwareTransport(resolvedMode),
        authSession: _buildReplayArchiveSession(dependencies),
        authSessionStore: MemoryAuthSessionStore(),
        deviceId: 'gtex-replay-archive-route',
        mode: resolvedMode,
      ),
    );
  }
}

class ApiReplayArchiveRouteRepository implements ReplayArchiveRouteRepository {
  const ApiReplayArchiveRouteRepository({required this.api});

  final GteAuthedApi api;

  @override
  Future<ReplayArchiveOverview> loadOverview({
    required bool isAuthenticated,
  }) async {
    final List<dynamic> featuredPayload = await api.getList(
      '/replays/public/featured',
      auth: false,
    );
    final List<ReplayArchiveEntry> publicFeatured = featuredPayload
        .map(ReplayArchiveEntry.fromJson)
        .toList(growable: false);

    if (!isAuthenticated) {
      return ReplayArchiveOverview(
        publicFeatured: publicFeatured,
        personalLaneMessage:
            'Sign in to see participant-only and competition-scoped replays.',
      );
    }

    try {
      final List<dynamic> myPayload = await api.getList('/replays/me');
      return ReplayArchiveOverview(
        publicFeatured: publicFeatured,
        myReplays: myPayload
            .map(ReplayArchiveEntry.fromJson)
            .toList(growable: false),
        personalLaneMessage: null,
      );
    } on GteApiException catch (error) {
      return ReplayArchiveOverview(
        publicFeatured: publicFeatured,
        personalLaneMessage: error.message,
      );
    }
  }
}

class EmptyReplayArchiveRouteRepository
    implements ReplayArchiveRouteRepository {
  const EmptyReplayArchiveRouteRepository();

  @override
  Future<ReplayArchiveOverview> loadOverview({
    required bool isAuthenticated,
  }) async {
    return ReplayArchiveOverview(
      personalLaneMessage:
          isAuthenticated
              ? 'Replay archive data is waiting for the backend replay policy layer.'
              : 'Sign in to see participant-only and competition-scoped replays.',
    );
  }
}

AuthSession? _buildReplayArchiveSession(
  GteNavigationDependencies dependencies,
) {
  final String accessToken = (dependencies.accessToken ?? '').trim();
  if (!dependencies.isAuthenticated || accessToken.isEmpty) {
    return null;
  }
  return AuthSession(
    userId: dependencies.currentUserId,
    accessToken: accessToken,
    refreshToken: '',
    sessionId: 'replay-archive-route',
    role: dependencies.currentUserRole ?? 'user',
    clubId: dependencies.currentClubId,
    clubName: dependencies.currentClubName,
    userName: dependencies.currentUserName,
    displayName: dependencies.currentUserName,
  );
}
