import 'package:flutter/material.dart';
import 'package:gte_frontend/core/app_feedback.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/data/national_team_api.dart';
import 'package:gte_frontend/features/shared/presentation/gte_feature_forms.dart';
import 'package:gte_frontend/models/national_team_models.dart';
import 'package:gte_frontend/widgets/gte_metric_chip.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

import '../data/fan_wars_models.dart';
import '../data/fan_wars_repository.dart';
import 'fan_wars_controller.dart';

class FanWarsScreen extends StatefulWidget {
  const FanWarsScreen({
    super.key,
    required this.baseUrl,
    required this.backendMode,
    this.accessToken,
    this.currentUserRole,
    this.entryId,
    this.showHistory = false,
  });

  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final String? currentUserRole;
  final String? entryId;
  final bool showHistory;

  @override
  State<FanWarsScreen> createState() => _FanWarsScreenState();
}

class _FanWarsScreenState extends State<FanWarsScreen> {
  late final FanWarsController _controller;
  late final FanWarsRepository _repository;
  late final NationalTeamApi _nationalTeamApi;

  List<NationalTeamCompetition> _competitions =
      const <NationalTeamCompetition>[];
  NationalTeamEntryDetail? _entryDetail;
  NationalTeamUserHistory? _history;
  NationsCupOverview? _nationsCup;
  String? _competitionId;
  String? _nationalError;
  bool _isLoadingNational = false;
  String _boardType = 'country';

  bool get _isAdmin => <String>{'admin', 'super_admin'}
      .contains((widget.currentUserRole ?? '').trim().toLowerCase());

  @override
  void initState() {
    super.initState();
    _controller = FanWarsController.standard(
      baseUrl: widget.baseUrl,
      backendMode: widget.backendMode,
      accessToken: widget.accessToken,
    );
    _repository = FanWarsApiRepository.standard(
      baseUrl: widget.baseUrl,
      mode: widget.backendMode,
      accessToken: widget.accessToken,
    );
    _nationalTeamApi = NationalTeamApi.standard(
      baseUrl: widget.baseUrl,
      accessToken: widget.accessToken,
      mode: widget.backendMode,
    );
    _load();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    await _controller.loadBoards(_boardType);
    setState(() {
      _nationalError = null;
      _isLoadingNational = true;
    });
    try {
      final List<Future<void>> tasks = <Future<void>>[
        _nationalTeamApi
            .listCompetitions()
            .then((List<NationalTeamCompetition> value) {
          _competitions = value;
        }),
        if (widget.entryId != null)
          _nationalTeamApi
              .fetchEntryDetail(widget.entryId!)
              .then((NationalTeamEntryDetail value) {
            _entryDetail = value;
          }),
        if (widget.showHistory)
          _nationalTeamApi
              .fetchUserHistory()
              .then((NationalTeamUserHistory value) {
            _history = value;
          }),
        if (_competitionId != null)
          _repository
              .fetchNationsCup(_competitionId!)
              .then((NationsCupOverview value) {
            _nationsCup = value;
          }),
      ];
      await Future.wait<void>(tasks);
    } catch (error) {
      _nationalError = AppFeedback.messageFor(error);
    } finally {
      if (mounted) {
        setState(() {
          _isLoadingNational = false;
        });
      }
    }
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

  Future<void> _resolveCompetitionId() async {
    final Map<String, String>? values = await showGteFormSheet(
      context,
      title: 'Load Nations Cup',
      fields: <GteFormFieldSpec>[
        GteFormFieldSpec(
          key: 'competitionId',
          label: 'Competition id',
          initialValue: _competitionId ?? '',
        ),
      ],
      onSubmit: (Map<String, String> values) async {
        final String id = values['competitionId']?.trim() ?? '';
        if (id.isEmpty) {
          AppFeedback.showError(context, 'Enter a competition id.');
          return false;
        }
        setState(() => _competitionId = id);
        await _load();
        return _nationalError == null;
      },
    );
    if (values != null && mounted) {
      AppFeedback.showSuccess(context, 'Nations Cup loaded.');
    }
  }

  Future<void> _createNationsCup() async {
    await _run(
      () => _controller.createNationsCup(
        NationsCupCreateRequest(
          startDate: DateTime.now(),
          title: 'GTEX Nations Cup',
        ),
      ),
      'Nations Cup created.',
    );
    _nationsCup = _controller.nationsCup;
    _competitionId = _nationsCup?.competitionId;
  }

  Future<void> _advanceNationsCup() async {
    if (_competitionId == null) {
      AppFeedback.showError(context, 'Load a canonical competition id first.');
      return;
    }
    await _run(
      () => _controller.advanceNationsCup(_competitionId!),
      'Nations Cup advanced.',
    );
    _nationsCup = _controller.nationsCup;
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: const Text('Fan wars / Nations Cup'),
          actions: <Widget>[
            IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
          ],
        ),
        body: AnimatedBuilder(
          animation: _controller,
          builder: (BuildContext context, Widget? child) {
            return RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
                children: <Widget>[
                  GteSurfacePanel(
                    accentColor: GteShellTheme.accentArena,
                    emphasized: true,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          'Global, club, and country boards plus Nations Cup context are routed through the canonical fan-wars engine.',
                          style: Theme.of(context).textTheme.bodyLarge,
                        ),
                        const SizedBox(height: 14),
                        Wrap(
                          spacing: 10,
                          runSpacing: 10,
                          children: <Widget>[
                            GteMetricChip(
                              label: 'Board',
                              value: _boardType.toUpperCase(),
                            ),
                            GteMetricChip(
                              label: 'Entries',
                              value: _controller.leaderboard?.entries.length
                                      .toString() ??
                                  '0',
                            ),
                            GteMetricChip(
                              label: 'Competitions',
                              value: _competitions.length.toString(),
                            ),
                          ],
                        ),
                        const SizedBox(height: 14),
                        Wrap(
                          spacing: 12,
                          runSpacing: 12,
                          children: <Widget>[
                            FilledButton.tonalIcon(
                              onPressed: _resolveCompetitionId,
                              icon: const Icon(Icons.flag_outlined),
                              label: Text(_competitionId == null
                                  ? 'Load Nations Cup'
                                  : 'Change competition'),
                            ),
                            if (_isAdmin)
                              FilledButton.tonalIcon(
                                onPressed: _createNationsCup,
                                icon: const Icon(Icons.add_circle_outline),
                                label: const Text('Create cup'),
                              ),
                            if (_isAdmin && _competitionId != null)
                              FilledButton.tonalIcon(
                                onPressed: _advanceNationsCup,
                                icon: const Icon(Icons.skip_next_outlined),
                                label: const Text('Advance cup'),
                              ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 18),
                  _SimpleFanWarsCard(
                    title: 'Leaderboards',
                    lines: (_controller.leaderboard?.entries ??
                            const <Map<String, Object?>>[])
                        .map((Map<String, Object?> item) =>
                            '${item['display_name'] ?? item['country_name'] ?? item['profile_id'] ?? 'Profile'} • ${item['total_points'] ?? item['points'] ?? 0}')
                        .toList(growable: false),
                    loading: _controller.isLoadingBoards,
                    error: _controller.boardsError,
                  ),
                  const SizedBox(height: 18),
                  _SimpleFanWarsCard(
                    title: 'Rivalries',
                    lines: (_controller.rivalries?.entries ??
                            const <Map<String, Object?>>[])
                        .map((Map<String, Object?> item) =>
                            '${item['left_display_name']} vs ${item['right_display_name']} • gap ${item['points_gap']}')
                        .toList(growable: false),
                    loading: _controller.isLoadingBoards,
                    error: _controller.boardsError,
                  ),
                  const SizedBox(height: 18),
                  _SimpleFanWarsCard(
                    title: 'National-team competitions',
                    lines: _competitions
                        .map((NationalTeamCompetition item) =>
                            '${item.title} • ${item.seasonLabel} • ${item.status}')
                        .toList(growable: false),
                    loading: _isLoadingNational,
                    error: _nationalError,
                  ),
                  if (_entryDetail != null) ...<Widget>[
                    const SizedBox(height: 18),
                    GteSurfacePanel(
                      child: Text(
                        'Entry ${_entryDetail!.entry.countryName}\nCompetition ${_entryDetail!.entry.competitionId}\nSquad ${_entryDetail!.squadMembers.length} • manager history ${_entryDetail!.managerHistory.length}',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ),
                  ],
                  if (_history != null) ...<Widget>[
                    const SizedBox(height: 18),
                    GteSurfacePanel(
                      child: Text(
                        'Managed entries ${_history!.managedEntries.length}\nSquad memberships ${_history!.squadMemberships.length}',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ),
                  ],
                  if (_nationsCup != null) ...<Widget>[
                    const SizedBox(height: 18),
                    GteSurfacePanel(
                      child: Text(
                        '${_nationsCup!.title}\n${_nationsCup!.status} • ${_nationsCup!.seasonLabel ?? '--'}\nEntries ${_nationsCup!.entries.length} • groups ${_nationsCup!.groups.length}',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ),
                  ],
                ],
              ),
            );
          },
        ),
      ),
    );
  }
}

class _SimpleFanWarsCard extends StatelessWidget {
  const _SimpleFanWarsCard({
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
              message: 'Competition and fan-war data are syncing.',
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
