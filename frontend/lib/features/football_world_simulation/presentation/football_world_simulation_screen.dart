import 'package:flutter/material.dart';
import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/controllers/regen_universe_controller.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/shared/presentation/gte_feature_forms.dart';
import 'package:gte_frontend/models/regen_universe_models.dart';
import 'package:gte_frontend/widgets/gte_metric_chip.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

import '../data/football_world_simulation_models.dart';
import 'football_world_simulation_controller.dart';

class FootballWorldSimulationScreen extends StatefulWidget {
  const FootballWorldSimulationScreen({
    super.key,
    required this.baseUrl,
    required this.backendMode,
    this.accessToken,
    this.currentUserRole,
    this.clubId,
    this.clubName,
    this.competitionId,
  });

  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final String? currentUserRole;
  final String? clubId;
  final String? clubName;
  final String? competitionId;

  @override
  State<FootballWorldSimulationScreen> createState() =>
      _FootballWorldSimulationScreenState();
}

class _FootballWorldSimulationScreenState
    extends State<FootballWorldSimulationScreen> {
  late FootballWorldSimulationController _controller;
  late RegenUniverseController _regenController;

  bool get _isAdmin => <String>{
    'admin',
    'super_admin',
  }.contains((widget.currentUserRole ?? '').trim().toLowerCase());

  @override
  void initState() {
    super.initState();
    _controller = _buildController();
    _regenController = _buildRegenController();
    _load();
  }

  @override
  void didUpdateWidget(covariant FootballWorldSimulationScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.baseUrl != widget.baseUrl ||
        oldWidget.backendMode != widget.backendMode ||
        oldWidget.accessToken != widget.accessToken) {
      _controller.dispose();
      _regenController.dispose();
      _controller = _buildController();
      _regenController = _buildRegenController();
      _load();
      return;
    }
    if (oldWidget.clubId != widget.clubId ||
        oldWidget.competitionId != widget.competitionId) {
      _load();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    _regenController.dispose();
    super.dispose();
  }

  FootballWorldSimulationController _buildController() {
    return FootballWorldSimulationController.standard(
      baseUrl: widget.baseUrl,
      backendMode: widget.backendMode,
      accessToken: widget.accessToken,
    );
  }

  RegenUniverseController _buildRegenController() {
    return RegenUniverseController.standard(
      baseUrl: widget.baseUrl,
      backendMode: widget.backendMode,
    );
  }

  Future<void> _load() async {
    await Future.wait<void>(<Future<void>>[
      _controller.loadCultures(query: const FootballCultureListQuery(limit: 8)),
      _controller.loadContext(
        clubId: widget.clubId,
        competitionId: widget.competitionId,
        narrativeQuery: WorldNarrativeListQuery(
          clubId: widget.clubId,
          competitionId: widget.competitionId,
          limit: 8,
        ),
      ),
      _controller.loadFederations(),
      _regenController.load(),
    ]);
  }

  Future<void> _run(Future<void> Function() action, String success) async {
    await action();
    if (!mounted) {
      return;
    }
    if ((_controller.actionError ?? '').trim().isNotEmpty) {
      AppFeedback.showError(context, _controller.actionError!);
    } else {
      AppFeedback.showSuccess(context, success);
    }
  }

  Future<void> _upsertCulture() async {
    await showGteFormSheet(
      context,
      title: 'Upsert culture',
      fields: const <GteFormFieldSpec>[
        GteFormFieldSpec(key: 'key', label: 'Culture key'),
        GteFormFieldSpec(key: 'name', label: 'Display name'),
        GteFormFieldSpec(key: 'country', label: 'Country code'),
      ],
      onSubmit: (Map<String, String> values) async {
        if ((values['key'] ?? '').isEmpty || (values['name'] ?? '').isEmpty) {
          AppFeedback.showError(context, 'Enter culture key and display name.');
          return false;
        }
        await _run(
          () => _controller.upsertCulture(
            values['key']!,
            FootballCultureUpsertRequest(
              displayName: values['name']!,
              countryCode: values['country'],
            ),
          ),
          'Culture updated.',
        );
        return _controller.actionError == null;
      },
    );
  }

  Future<void> _upsertClubContext() async {
    final String? clubId = widget.clubId;
    if (clubId == null) {
      return;
    }
    await _run(
      () => _controller.upsertClubContext(
        clubId,
        const ClubWorldProfileUpsertRequest(
          supporterMood: 'charged',
          narrativePhase: 'momentum_building',
        ),
      ),
      'Club world context updated.',
    );
  }

  Future<void> _upsertNarrative() async {
    await showGteFormSheet(
      context,
      title: 'Upsert narrative',
      fields: const <GteFormFieldSpec>[
        GteFormFieldSpec(key: 'slug', label: 'Narrative slug'),
        GteFormFieldSpec(key: 'headline', label: 'Headline'),
        GteFormFieldSpec(key: 'arc', label: 'Arc type'),
      ],
      onSubmit: (Map<String, String> values) async {
        if ((values['slug'] ?? '').isEmpty ||
            (values['headline'] ?? '').isEmpty ||
            (values['arc'] ?? '').isEmpty) {
          AppFeedback.showError(context, 'Enter slug, headline, and arc type.');
          return false;
        }
        await _run(
          () => _controller.upsertNarrative(
            values['slug']!,
            WorldNarrativeUpsertRequest(
              clubId: widget.clubId,
              competitionId: widget.competitionId,
              headline: values['headline']!,
              arcType: values['arc']!,
            ),
          ),
          'Narrative updated.',
        );
        return _controller.actionError == null;
      },
    );
  }

  Future<void> _joinFederation(WorldFederation federation) async {
    final String clubId = widget.clubId?.trim() ?? '';
    if (clubId.isEmpty) {
      AppFeedback.showError(
        context,
        'A club context is required before joining a federation.',
      );
      return;
    }
    final WorldFederationMembership? membership = await _controller
        .joinFederation(federation.id, clubId: clubId);
    if (!mounted) {
      return;
    }
    if ((_controller.actionError ?? '').trim().isNotEmpty) {
      AppFeedback.showError(context, _controller.actionError!);
      return;
    }
    final bool pending =
        (membership?.status ?? '').trim().toLowerCase() == 'pending';
    AppFeedback.showSuccess(
      context,
      pending
          ? 'Federation membership submitted for review.'
          : 'Federation joined.',
    );
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: Text(widget.clubName ?? 'Football world simulation'),
          actions: <Widget>[
            IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
          ],
        ),
        body: AnimatedBuilder(
          animation: Listenable.merge(<Listenable>[
            _controller,
            _regenController,
          ]),
          builder: (BuildContext context, Widget? child) {
            final ClubWorldContext? club = _controller.clubContext;
            final CompetitionWorldContext? competition =
                _controller.competitionContext;
            final bool canJoinFederations =
                (widget.accessToken?.trim().isNotEmpty ?? false) &&
                (widget.clubId?.trim().isNotEmpty ?? false);
            return RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
                children: <Widget>[
                  GteSurfacePanel(
                    accentColor: const Color(0xFF8ED8FF),
                    emphasized: true,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          'Cultures, narratives, and club or competition context stay wired to the canonical football-world simulation.',
                          style: Theme.of(context).textTheme.bodyLarge,
                        ),
                        const SizedBox(height: 14),
                        Wrap(
                          spacing: 10,
                          runSpacing: 10,
                          children: <Widget>[
                            GteMetricChip(
                              label: 'Cultures',
                              value: _controller.cultures.length.toString(),
                            ),
                            GteMetricChip(
                              label: 'Federations',
                              value: _controller.federations.length.toString(),
                            ),
                            GteMetricChip(
                              label: 'Narratives',
                              value: _controller.narratives.length.toString(),
                            ),
                            if (club != null)
                              GteMetricChip(
                                label: 'Club reputation',
                                value: club.reputationScore.toString(),
                              ),
                            if (competition != null)
                              GteMetricChip(
                                label: 'Participants',
                                value: competition.participantCount.toString(),
                              ),
                          ],
                        ),
                        if (_isAdmin) ...<Widget>[
                          const SizedBox(height: 14),
                          Wrap(
                            spacing: 12,
                            runSpacing: 12,
                            children: <Widget>[
                              FilledButton.tonalIcon(
                                onPressed: _upsertCulture,
                                icon: const Icon(Icons.public_outlined),
                                label: const Text('Culture'),
                              ),
                              if (widget.clubId != null)
                                FilledButton.tonalIcon(
                                  onPressed: _upsertClubContext,
                                  icon: const Icon(Icons.shield_outlined),
                                  label: const Text('Club context'),
                                ),
                              FilledButton.tonalIcon(
                                onPressed: _upsertNarrative,
                                icon: const Icon(Icons.auto_stories_outlined),
                                label: const Text('Narrative'),
                              ),
                            ],
                          ),
                        ],
                      ],
                    ),
                  ),
                  const SizedBox(height: 18),
                  if (_controller.contextError != null &&
                      club == null &&
                      competition == null)
                    GteStatePanel(
                      title: 'World context unavailable',
                      message: _controller.contextError!,
                      icon: Icons.error_outline,
                    )
                  else if (club != null || competition != null)
                    GteSurfacePanel(
                      child: Text(
                        club != null
                            ? '${club.clubName}\nMood ${club.worldProfile['supporter_mood'] ?? '--'} • phase ${club.worldProfile['narrative_phase'] ?? '--'}\nNarratives ${club.activeNarratives.length} • hooks ${club.simulationHooks.length}'
                            : '${competition!.name}\n${competition.stage} • ${competition.status}\nNarratives ${competition.activeNarratives.length} • hooks ${competition.simulationHooks.length}',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ),
                  const SizedBox(height: 18),
                  _WorldRegenDeskCard(
                    controller: _regenController,
                    clubName: widget.clubName,
                  ),
                  const SizedBox(height: 18),
                  GteSurfacePanel(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          'World federations',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(height: 10),
                        Text(
                          canJoinFederations
                              ? 'The world summary now submits live federation membership requests for the active club.'
                              : 'Federation membership stays read-only until the active shell provides both a valid session and a club context.',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                        const SizedBox(height: 14),
                        if (_controller.isLoadingFederations &&
                            _controller.federations.isEmpty)
                          const GteStatePanel(
                            title: 'Loading federations',
                            message:
                                'Regional structures and member clubs are syncing.',
                            icon: Icons.public_outlined,
                            isLoading: true,
                          )
                        else if (_controller.federationError != null &&
                            _controller.federations.isEmpty)
                          GteStatePanel(
                            title: 'Federations unavailable',
                            message: _controller.federationError!,
                            icon: Icons.error_outline,
                          )
                        else if (_controller.federations.isEmpty)
                          const Text('No federations available right now.')
                        else
                          ..._controller.federations.take(6).map((
                            WorldFederation federation,
                          ) {
                            final String? membershipStatus = federation
                                .membershipStatusForClub(widget.clubId);
                            final bool joined = federation.isJoinedByClub(
                              widget.clubId,
                            );
                            final bool pending =
                                membershipStatus?.toLowerCase() == 'pending';
                            final bool isJoining =
                                _controller.isJoiningFederation &&
                                _controller.joiningFederationId ==
                                    federation.id;
                            final String buttonLabel =
                                joined
                                    ? 'Joined'
                                    : pending
                                    ? 'Pending'
                                    : canJoinFederations
                                    ? 'Join federation'
                                    : 'Read only';
                            return Padding(
                              padding: const EdgeInsets.only(bottom: 12),
                              child: Container(
                                padding: const EdgeInsets.all(14),
                                decoration: BoxDecoration(
                                  borderRadius: BorderRadius.circular(18),
                                  border: Border.all(
                                    color: const Color(
                                      0xFF8ED8FF,
                                    ).withValues(alpha: 0.20),
                                  ),
                                ),
                                child: Row(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: <Widget>[
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: <Widget>[
                                          Text(
                                            federation.name,
                                            style:
                                                Theme.of(
                                                  context,
                                                ).textTheme.titleMedium,
                                          ),
                                          const SizedBox(height: 6),
                                          Text(
                                            '${federation.regionLabel} • ${federation.memberClubCount} member clubs • ${federation.competitionCount} competitions',
                                            style:
                                                Theme.of(
                                                  context,
                                                ).textTheme.bodyMedium,
                                          ),
                                        ],
                                      ),
                                    ),
                                    const SizedBox(width: 12),
                                    FilledButton.tonal(
                                      onPressed:
                                          joined ||
                                                  pending ||
                                                  !canJoinFederations ||
                                                  isJoining
                                              ? null
                                              : () =>
                                                  _joinFederation(federation),
                                      child: Text(
                                        isJoining ? 'Joining...' : buttonLabel,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            );
                          }),
                      ],
                    ),
                  ),
                  const SizedBox(height: 18),
                  _SimpleWorldListCard(
                    title: 'World narratives',
                    lines: _controller.narratives
                        .map(
                          (WorldNarrative item) =>
                              '${item.headline} • ${item.arcType} • ${item.status}',
                        )
                        .toList(growable: false),
                    loading: _controller.isLoadingContext,
                    error: _controller.contextError,
                  ),
                  const SizedBox(height: 18),
                  _SimpleWorldListCard(
                    title: 'Football cultures',
                    lines: _controller.cultures
                        .map(
                          (FootballCulture item) =>
                              '${item.displayName} • ${item.scopeType} • ${item.countryCode ?? 'GLOBAL'}',
                        )
                        .toList(growable: false),
                    loading: _controller.isLoadingCultures,
                    error: _controller.cultureError,
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

class _WorldRegenDeskCard extends StatelessWidget {
  const _WorldRegenDeskCard({required this.controller, required this.clubName});

  final RegenUniverseController controller;
  final String? clubName;

  @override
  Widget build(BuildContext context) {
    final RegenGenerationTracking? tracking = controller.tracking;
    final Map<String, List<NationalRegenSeed>> regensByCountry =
        <String, List<NationalRegenSeed>>{};
    for (final NationalRegenSeed seed in controller.nationalRegens) {
      regensByCountry.putIfAbsent(
        seed.countryName,
        () => <NationalRegenSeed>[],
      );
      regensByCountry[seed.countryName]!.add(seed);
    }
    final List<MapEntry<String, List<NationalRegenSeed>>> groupedCountries =
        regensByCountry.entries.toList(growable: false)..sort(
          (
            MapEntry<String, List<NationalRegenSeed>> left,
            MapEntry<String, List<NationalRegenSeed>> right,
          ) => right.value.length.compareTo(left.value.length),
        );

    return GteSurfacePanel(
      accentColor: const Color(0xFF7BE0AD),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Regen universe desk',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 10),
          Text(
            clubName == null
                ? 'National pre-seeded regens, club generation events, and global tracking are visible from the live regen universe.'
                : 'National pre-seeded regens and club-generated prospects stay visible for $clubName from the live regen universe.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <Widget>[
              GteMetricChip(
                label: 'National seeds',
                value: controller.nationalRegens.length.toString(),
              ),
              GteMetricChip(
                label: 'Scouting feed',
                value: controller.scoutingFeed.length.toString(),
              ),
              GteMetricChip(
                label: 'Rising stars',
                value: controller.risingStars.length.toString(),
              ),
              if (tracking != null)
                GteMetricChip(
                  label: 'Peak GSI',
                  value: tracking.globalPeakRating.toString(),
                ),
            ],
          ),
          const SizedBox(height: 14),
          if (controller.isLoading && !controller.hasData)
            const GteStatePanel(
              title: 'Loading regen universe',
              message:
                  'National pre-seeds, club generation events, and tracking are syncing.',
              icon: Icons.auto_awesome_outlined,
              isLoading: true,
            )
          else if (controller.errorMessage != null && !controller.hasData)
            GteStatePanel(
              title: 'Regen universe unavailable',
              message: controller.errorMessage!,
              icon: Icons.error_outline,
            )
          else ...<Widget>[
            if (groupedCountries.isNotEmpty) ...<Widget>[
              Text(
                'National pre-seeded regens',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 10),
              ...groupedCountries.take(4).map((
                MapEntry<String, List<NationalRegenSeed>> entry,
              ) {
                final List<NationalRegenSeed> seeds =
                    entry.value..sort(
                      (NationalRegenSeed left, NationalRegenSeed right) =>
                          right.potentialRating.compareTo(left.potentialRating),
                    );
                return Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(18),
                      border: Border.all(
                        color: const Color(0xFF7BE0AD).withValues(alpha: 0.18),
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          entry.key,
                          style: Theme.of(context).textTheme.titleSmall,
                        ),
                        const SizedBox(height: 8),
                        ...seeds
                            .take(3)
                            .map(
                              (NationalRegenSeed seed) => Padding(
                                padding: const EdgeInsets.only(bottom: 6),
                                child: Text(
                                  '${seed.displayName} • ${seed.primaryPosition} • GSI ${seed.resolvedGsi} • POT ${seed.potentialRating} • ${_labelize(seed.rarityTier)}',
                                  style: Theme.of(context).textTheme.bodyMedium,
                                ),
                              ),
                            ),
                      ],
                    ),
                  ),
                );
              }),
            ],
            if (controller.scoutingFeed.isNotEmpty) ...<Widget>[
              const SizedBox(height: 4),
              Text(
                'Club and academy generation feed',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 10),
              ...controller.scoutingFeed
                  .take(4)
                  .map(
                    (RegenScoutingFeedItem item) => Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: Text(
                        '${item.title} • ${_labelize(item.feedType)}${item.player == null ? '' : ' • ${item.player!.name} (${item.player!.position})'}',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ),
                  ),
            ],
            if (controller.risingStars.isNotEmpty) ...<Widget>[
              const SizedBox(height: 4),
              Text(
                'Global rising regens',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 10),
              ...controller.risingStars
                  .take(4)
                  .map(
                    (RegenRisingStar star) => Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: Text(
                        '${star.player.name} • ${star.player.nationality} • GSI ${star.player.resolvedGsi} • POT ${star.player.potential} • ${star.momentumLabel}',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ),
                  ),
            ],
            if (tracking != null) ...<Widget>[
              const SizedBox(height: 4),
              Text('Tracking', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 10),
              Text(
                'Tracked seeded players: ${tracking.totalSeededPlayers}. Peak GSI reached: ${tracking.globalPeakRating}.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              if (tracking.countryDistribution.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(
                    tracking.countryDistribution
                        .take(4)
                        .map(
                          (RegenGenerationTrackingEntry entry) =>
                              '${entry.bucket} ${entry.count}',
                        )
                        .join(' • '),
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: GteShellTheme.textMuted,
                    ),
                  ),
                ),
            ],
          ],
        ],
      ),
    );
  }
}

String _labelize(String value) {
  final List<String> parts = value
      .split(RegExp(r'[_\s]+'))
      .where((String part) => part.trim().isNotEmpty)
      .map(
        (String part) =>
            '${part[0].toUpperCase()}${part.substring(1).toLowerCase()}',
      )
      .toList(growable: false);
  return parts.isEmpty ? '--' : parts.join(' ');
}

class _SimpleWorldListCard extends StatelessWidget {
  const _SimpleWorldListCard({
    required this.title,
    required this.lines,
    required this.loading,
    required this.error,
  });

  final String title;
  final List<String> lines;
  final bool loading;
  final String? error;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 10),
          if (loading && lines.isEmpty)
            const GteStatePanel(
              title: 'Loading',
              message: 'World simulation data is syncing.',
              icon: Icons.hourglass_bottom_outlined,
              isLoading: true,
            )
          else if (error != null && lines.isEmpty)
            GteStatePanel(
              title: 'Unavailable',
              message: error!,
              icon: Icons.error_outline,
            )
          else if (lines.isEmpty)
            const Text('No records available.')
          else
            ...lines
                .take(6)
                .map(
                  (String line) => Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Text(
                      line,
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ),
                ),
        ],
      ),
    );
  }
}
