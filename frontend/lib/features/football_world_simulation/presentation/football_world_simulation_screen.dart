import 'package:flutter/material.dart';
import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/features/shared/presentation/gte_feature_forms.dart';
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
  late final FootballWorldSimulationController _controller;

  bool get _isAdmin => <String>{'admin', 'super_admin'}
      .contains((widget.currentUserRole ?? '').trim().toLowerCase());

  @override
  void initState() {
    super.initState();
    _controller = FootballWorldSimulationController.standard(
      baseUrl: widget.baseUrl,
      backendMode: widget.backendMode,
      accessToken: widget.accessToken,
    );
    _load();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    await _controller.loadCultures(
      query: const FootballCultureListQuery(limit: 8),
    );
    await _controller.loadContext(
      clubId: widget.clubId,
      competitionId: widget.competitionId,
      narrativeQuery: WorldNarrativeListQuery(
        clubId: widget.clubId,
        competitionId: widget.competitionId,
        limit: 8,
      ),
    );
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
          animation: _controller,
          builder: (BuildContext context, Widget? child) {
            final ClubWorldContext? club = _controller.clubContext;
            final CompetitionWorldContext? competition =
                _controller.competitionContext;
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
                  _SimpleWorldListCard(
                    title: 'World narratives',
                    lines: _controller.narratives
                        .map((WorldNarrative item) =>
                            '${item.headline} • ${item.arcType} • ${item.status}')
                        .toList(growable: false),
                    loading: _controller.isLoadingContext,
                    error: _controller.contextError,
                  ),
                  const SizedBox(height: 18),
                  _SimpleWorldListCard(
                    title: 'Football cultures',
                    lines: _controller.cultures
                        .map((FootballCulture item) =>
                            '${item.displayName} • ${item.scopeType} • ${item.countryCode ?? 'GLOBAL'}')
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
            ...lines.take(6).map(
                  (String line) => Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Text(line,
                        style: Theme.of(context).textTheme.bodyMedium),
                  ),
                ),
        ],
      ),
    );
  }
}
