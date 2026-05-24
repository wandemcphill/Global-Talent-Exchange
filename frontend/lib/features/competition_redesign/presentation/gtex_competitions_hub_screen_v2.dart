import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

import '../data/gtex_competition_repository.dart';
import '../models/gtex_competition_models.dart';

class GtexCompetitionsHubScreenV2 extends StatefulWidget {
  const GtexCompetitionsHubScreenV2({
    super.key,
    this.repository,
    this.initialCompetitionId,
    this.allowFixtureData = false,
  });

  final GtexCompetitionRepository? repository;
  final String? initialCompetitionId;
  final bool allowFixtureData;

  @override
  State<GtexCompetitionsHubScreenV2> createState() =>
      _GtexCompetitionsHubScreenV2State();
}

class _GtexCompetitionsHubScreenV2State
    extends State<GtexCompetitionsHubScreenV2> {
  List<GtexCompetitionSummary> _competitions = const <GtexCompetitionSummary>[];
  GtexCompetitionDetail? _detail;
  String? _selectedId;
  GtexCompetitionKind? _filter;
  String _query = '';
  bool _loading = true;
  int _tabIndex = 0;

  GtexCompetitionRepository? get _repository =>
      widget.repository ??
      (widget.allowFixtureData ? const DemoGtexCompetitionRepository() : null);

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final GtexCompetitionRepository? repository = _repository;
    if (repository == null) {
      if (!mounted) return;
      setState(() => _loading = false);
      return;
    }
    final List<GtexCompetitionSummary> competitions =
        await repository.listCompetitions();
    if (!mounted) return;
    GtexCompetitionSummary? featured;
    for (final GtexCompetitionSummary item in competitions) {
      if (widget.initialCompetitionId?.trim().isNotEmpty == true &&
          item.id == widget.initialCompetitionId!.trim()) {
        featured = item;
        break;
      }
      if (item.id == 'global-talent-cup') {
        featured = item;
      }
    }
    setState(() {
      _competitions = competitions;
      _selectedId =
          widget.initialCompetitionId?.trim().isNotEmpty == true
              ? widget.initialCompetitionId!.trim()
              : competitions.isEmpty
              ? null
              : (featured ?? competitions.first).id;
      _loading = false;
    });
    if (_selectedId != null) {
      await _select(_selectedId!);
    }
  }

  Future<void> _select(String competitionId) async {
    final GtexCompetitionRepository? repository = _repository;
    if (repository == null) {
      return;
    }
    setState(() {
      _selectedId = competitionId;
      _tabIndex = 0;
    });
    final GtexCompetitionDetail detail = await repository.getCompetitionDetail(
      competitionId,
    );
    if (!mounted) return;
    setState(() => _detail = detail);
  }

  Future<void> _activateCompetitionAction(
    GtexCompetitionSummary summary,
  ) async {
    final GtexCompetitionRepository? repository = _repository;
    if (repository == null) {
      return;
    }
    if (!summary.isJoinable) {
      setState(() => _tabIndex = 0);
      return;
    }
    try {
      await repository.joinCompetition(summary.id);
      if (!mounted) return;
      await _select(summary.id);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Competition entry synced.')),
      );
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Competition action failed: $error')),
      );
    }
  }

  List<GtexCompetitionSummary> get _visibleCompetitions {
    return _competitions
        .where((GtexCompetitionSummary item) {
          final bool matchesKind = _filter == null || item.kind == _filter;
          final bool matchesQuery =
              _query.trim().isEmpty ||
              item.title.toLowerCase().contains(_query.toLowerCase()) ||
              item.regionLabel.toLowerCase().contains(_query.toLowerCase());
          return matchesKind && matchesQuery;
        })
        .toList(growable: false);
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    final GtexCompetitionRepository? repository = _repository;
    if (repository == null) {
      return const GtexEmptyState(
        title: 'Live competitions unavailable',
        message:
            'Competition OS data requires a live repository. Fixture competitions are only available in explicit test mode.',
        icon: Icons.emoji_events_outlined,
        accent: GtexColors.gold,
      );
    }

    return GtexMasterDetailScaffold(
      title: 'GTEX Competitions',
      subtitle:
          'Monitor tournaments, join GTEX cups, run user-hosted competitions, and track progress from one calm workspace.',
      accent: GtexColors.gold,
      mobileLeftTitle: 'Competitions',
      actions: <Widget>[
        GtexActionButton(
          label: 'Create competition',
          icon: Icons.add_circle_outline,
          accent: GtexColors.gold,
          onPressed: () {
            Navigator.of(context).push<void>(
              MaterialPageRoute<void>(
                builder:
                    (_) =>
                        GtexCompetitionCreateScreenV2(repository: repository),
              ),
            );
          },
        ),
      ],
      leftPanel: _buildLeftPanel(context),
      detail: _buildDetailPanel(context),
      rightPanel: _buildRightPanel(context),
      rightPanelWidth: 360,
    );
  }

  Widget _buildLeftPanel(BuildContext context) {
    final List<GtexCompetitionSummary> visible = _visibleCompetitions;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        GtexSearchField(
          hintText: 'Search tournaments, cups, creators...',
          onChanged: (String value) => setState(() => _query = value),
        ),
        const SizedBox(height: GtexSpacing.md),
        Wrap(
          spacing: GtexSpacing.xs,
          runSpacing: GtexSpacing.xs,
          children: <Widget>[
            _FilterPill(
              label: 'All',
              selected: _filter == null,
              onTap: () => setState(() => _filter = null),
            ),
            for (final GtexCompetitionKind kind in GtexCompetitionKind.values)
              _FilterPill(
                label: kind.label,
                selected: _filter == kind,
                onTap: () => setState(() => _filter = kind),
              ),
          ],
        ),
        const SizedBox(height: GtexSpacing.md),
        Expanded(
          child: ListView.separated(
            itemCount: visible.length,
            separatorBuilder: (_, __) => const SizedBox(height: GtexSpacing.sm),
            itemBuilder: (BuildContext context, int index) {
              final GtexCompetitionSummary item = visible[index];
              return GtexPanel(
                isSelected: item.id == _selectedId,
                accent: _statusColor(item.status),
                onTap: () => _select(item.id),
                padding: const EdgeInsets.all(GtexSpacing.md),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Row(
                      children: <Widget>[
                        Expanded(
                          child: Text(
                            item.title,
                            style: Theme.of(
                              context,
                            ).textTheme.titleSmall?.copyWith(
                              color: GtexColors.text,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                        ),
                        GtexStatusChip(
                          label: item.status.label,
                          color: _statusColor(item.status),
                          compact: true,
                        ),
                      ],
                    ),
                    const SizedBox(height: GtexSpacing.xs),
                    Text(
                      item.regionLabel,
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: GtexColors.textMuted,
                      ),
                    ),
                    const SizedBox(height: GtexSpacing.sm),
                    LinearProgressIndicator(
                      value: item.progressPercent.clamp(0, 1),
                      minHeight: 5,
                      backgroundColor: GtexColors.line,
                      color: _statusColor(item.status),
                    ),
                    const SizedBox(height: GtexSpacing.xs),
                    Text(
                      '${item.currentStage} • ${item.capacityLabel}',
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: GtexColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  Widget _buildDetailPanel(BuildContext context) {
    final GtexCompetitionDetail? detail = _detail;
    if (detail == null) {
      return const GtexEmptyState(
        title: 'Select a tournament',
        message:
            'Choose a competition from the left panel to open fixtures, standings, bracket, progress, and rules.',
        icon: Icons.emoji_events_outlined,
      );
    }

    final GtexCompetitionSummary summary = detail.summary;
    return LayoutBuilder(
      builder: (BuildContext context, BoxConstraints constraints) {
        final double tabHeight =
            constraints.maxHeight.isFinite
                ? (constraints.maxHeight * .58).clamp(280.0, 520.0)
                : 420.0;
        return ListView(
          padding: EdgeInsets.zero,
          children: <Widget>[
            GtexPanel(
              accent: GtexColors.gold,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Container(
                        width: 64,
                        height: 64,
                        decoration: BoxDecoration(
                          color: GtexColors.gold.withValues(alpha: .14),
                          borderRadius: BorderRadius.circular(
                            GtexSpacing.radiusLg,
                          ),
                          border: Border.all(
                            color: GtexColors.gold.withValues(alpha: .55),
                          ),
                        ),
                        child: const Icon(
                          Icons.emoji_events,
                          color: GtexColors.gold,
                          size: 34,
                        ),
                      ),
                      const SizedBox(width: GtexSpacing.md),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Text(
                              summary.title,
                              style: Theme.of(
                                context,
                              ).textTheme.headlineSmall?.copyWith(
                                color: GtexColors.text,
                                fontWeight: FontWeight.w900,
                              ),
                            ),
                            const SizedBox(height: GtexSpacing.xs),
                            Text(
                              summary.description,
                              style: Theme.of(
                                context,
                              ).textTheme.bodyMedium?.copyWith(
                                color: GtexColors.textSecondary,
                                height: 1.45,
                              ),
                            ),
                            const SizedBox(height: GtexSpacing.sm),
                            Wrap(
                              spacing: GtexSpacing.xs,
                              runSpacing: GtexSpacing.xs,
                              children: <Widget>[
                                GtexStatusChip(
                                  label: summary.kind.label,
                                  icon: Icons.category_outlined,
                                  color: GtexColors.cyan,
                                ),
                                GtexStatusChip(
                                  label: summary.status.label,
                                  icon: Icons.circle,
                                  color: _statusColor(summary.status),
                                ),
                                GtexStatusChip(
                                  label: summary.startsAtLabel,
                                  icon: Icons.schedule,
                                  color: GtexColors.gold,
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: GtexSpacing.md),
                  Wrap(
                    spacing: GtexSpacing.sm,
                    runSpacing: GtexSpacing.sm,
                    children: <Widget>[
                      SizedBox(
                        width: 190,
                        child: GtexMetricTile(
                          label: 'Prize pool',
                          value: summary.prizePoolLabel,
                          icon: Icons.account_balance_wallet_outlined,
                          accent: GtexColors.gold,
                        ),
                      ),
                      SizedBox(
                        width: 190,
                        child: GtexMetricTile(
                          label: 'Entry',
                          value: summary.entryFeeLabel,
                          icon: Icons.confirmation_number_outlined,
                          accent: GtexColors.pitch,
                        ),
                      ),
                      SizedBox(
                        width: 190,
                        child: GtexMetricTile(
                          label: 'Capacity',
                          value: summary.capacityLabel,
                          icon: Icons.groups_outlined,
                          accent: GtexColors.cyan,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: GtexSpacing.md),
            _buildTabs(context),
            const SizedBox(height: GtexSpacing.md),
            SizedBox(
              height: tabHeight,
              child: _buildSelectedTab(context, detail),
            ),
          ],
        );
      },
    );
  }

  Widget _buildTabs(BuildContext context) {
    const List<String> tabs = <String>[
      'Progress',
      'Fixtures',
      'Standings',
      'Bracket',
      'Rules',
    ];
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: <Widget>[
          for (int i = 0; i < tabs.length; i++) ...<Widget>[
            _FilterPill(
              label: tabs[i],
              selected: _tabIndex == i,
              onTap: () => setState(() => _tabIndex = i),
            ),
            const SizedBox(width: GtexSpacing.xs),
          ],
        ],
      ),
    );
  }

  Widget _buildSelectedTab(BuildContext context, GtexCompetitionDetail detail) {
    switch (_tabIndex) {
      case 1:
        return _FixturesList(fixtures: detail.fixtures);
      case 2:
        return _StandingsTable(standings: detail.standings);
      case 3:
        return _BracketProgress(stages: detail.stages);
      case 4:
        return _RulesList(rules: detail.rules);
      case 0:
      default:
        return _ProgressMonitor(detail: detail);
    }
  }

  Widget _buildRightPanel(BuildContext context) {
    final GtexCompetitionDetail? detail = _detail;
    if (detail == null) {
      return const SizedBox.shrink();
    }
    final GtexCompetitionSummary summary = detail.summary;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        GtexPanel(
          title: 'Competition actions',
          subtitle: 'Join, monitor, publish, or open the operations workspace.',
          accent: GtexColors.gold,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              GtexActionButton(
                label: summary.isJoinable ? 'Join tournament' : 'Open monitor',
                icon:
                    summary.isJoinable
                        ? Icons.login
                        : Icons.monitor_heart_outlined,
                accent: summary.isJoinable ? GtexColors.pitch : GtexColors.gold,
                onPressed: () => _activateCompetitionAction(summary),
              ),
              const SizedBox(height: GtexSpacing.sm),
              GtexActionButton(
                label: 'View rules',
                icon: Icons.rule_folder_outlined,
                secondary: true,
                accent: GtexColors.cyan,
                onPressed: () => setState(() => _tabIndex = 4),
              ),
              const SizedBox(height: GtexSpacing.sm),
              GtexActionButton(
                label: 'Share competition',
                icon: Icons.ios_share,
                secondary: true,
                accent: GtexColors.gold,
                onPressed: () async {
                  await Clipboard.setData(
                    ClipboardData(text: 'gtex://competition/${summary.id}'),
                  );
                  if (!context.mounted) return;
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Competition link copied.')),
                  );
                },
              ),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'AI News signals',
          subtitle:
              'Stories the GTEX newsroom can generate from this competition.',
          accent: GtexColors.pitch,
          child: Column(
            children: <Widget>[
              for (final String signal in detail.newsSignals)
                Padding(
                  padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      const Icon(
                        Icons.auto_awesome,
                        color: GtexColors.pitch,
                        size: 18,
                      ),
                      const SizedBox(width: GtexSpacing.xs),
                      Expanded(
                        child: Text(
                          signal,
                          style: Theme.of(
                            context,
                          ).textTheme.bodySmall?.copyWith(
                            color: GtexColors.textSecondary,
                            height: 1.35,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        Expanded(
          child: GtexPanel(
            title: 'Ops checklist',
            subtitle:
                'Designed for user-hosted, creator-hosted, and admin progress monitoring.',
            accent: GtexColors.cyan,
            child: Column(
              children: const <Widget>[
                _ChecklistRow(
                  label: 'Registration rules verified',
                  complete: true,
                ),
                _ChecklistRow(label: 'Fixtures generated', complete: true),
                _ChecklistRow(
                  label: 'Payment settlement monitored',
                  complete: true,
                ),
                _ChecklistRow(
                  label: 'Dispute window configured',
                  complete: false,
                ),
                _ChecklistRow(
                  label: 'Final awards/news queued',
                  complete: false,
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Color _statusColor(GtexCompetitionStatus status) {
    switch (status) {
      case GtexCompetitionStatus.draft:
        return GtexColors.textMuted;
      case GtexCompetitionStatus.registrationOpen:
        return GtexColors.pitch;
      case GtexCompetitionStatus.registrationClosed:
        return GtexColors.gold;
      case GtexCompetitionStatus.live:
        return GtexColors.danger;
      case GtexCompetitionStatus.completed:
        return GtexColors.cyan;
    }
  }
}

class GtexCompetitionCreateScreenV2 extends StatefulWidget {
  const GtexCompetitionCreateScreenV2({
    super.key,
    this.repository,
    this.allowFixtureData = false,
  });

  final GtexCompetitionRepository? repository;
  final bool allowFixtureData;

  @override
  State<GtexCompetitionCreateScreenV2> createState() =>
      _GtexCompetitionCreateScreenV2State();
}

class _GtexCompetitionCreateScreenV2State
    extends State<GtexCompetitionCreateScreenV2> {
  int _step = 0;
  GtexCompetitionKind _kind = GtexCompetitionKind.userHosted;
  int _entryFee = 100;
  int _maxClubs = 16;
  String _rulePreset = 'Balanced cup rules';
  String _visibility = 'Public';
  final TextEditingController _title = TextEditingController(
    text: 'Weekend Talent Cup',
  );

  GtexCompetitionRepository? get _repository =>
      widget.repository ??
      (widget.allowFixtureData ? const DemoGtexCompetitionRepository() : null);

  @override
  void dispose() {
    _title.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final GtexCompetitionRepository? repository = _repository;
    if (repository == null) {
      return const GtexEmptyState(
        title: 'Competition creation unavailable',
        message:
            'Competition creation requires a live Competition OS repository. Fixture drafts are only available in explicit test mode.',
        icon: Icons.add_circle_outline,
        accent: GtexColors.gold,
      );
    }
    return GtexFocusFlowScaffold(
      title: 'Create GTEX competition',
      subtitle:
          'Set up a user-hosted or creator-hosted competition without leaving the GTEX route system.',
      accent: GtexColors.gold,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          _StepHeader(step: _step),
          const SizedBox(height: GtexSpacing.lg),
          if (_step == 0) _buildIdentityStep(context),
          if (_step == 1) _buildRulesStep(context),
          if (_step == 2) _buildReviewStep(context),
          const SizedBox(height: GtexSpacing.lg),
          Row(
            children: <Widget>[
              if (_step > 0)
                GtexActionButton(
                  label: 'Back',
                  icon: Icons.arrow_back,
                  secondary: true,
                  onPressed: () => setState(() => _step -= 1),
                ),
              const Spacer(),
              GtexActionButton(
                label: _step == 2 ? 'Save draft' : 'Continue',
                icon: _step == 2 ? Icons.save_outlined : Icons.arrow_forward,
                accent: GtexColors.gold,
                onPressed: () async {
                  if (_step < 2) {
                    setState(() => _step += 1);
                    return;
                  }
                  await repository.createCompetition(
                    GtexCompetitionDraft(
                      title: _title.text,
                      kind: _kind,
                      entryFeeCredits: _entryFee,
                      maxClubs: _maxClubs,
                      rulePreset: _rulePreset,
                      visibility: _visibility,
                    ),
                  );
                  if (!context.mounted) {
                    return;
                  }
                  Navigator.of(context).pop();
                },
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildIdentityStep(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        TextField(
          controller: _title,
          decoration: const InputDecoration(
            labelText: 'Competition title',
            hintText: 'Weekend Talent Cup',
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        Wrap(
          spacing: GtexSpacing.sm,
          runSpacing: GtexSpacing.sm,
          children: <Widget>[
            for (final GtexCompetitionKind kind in <GtexCompetitionKind>[
              GtexCompetitionKind.userHosted,
              GtexCompetitionKind.creatorHosted,
              GtexCompetitionKind.gtexTournament,
            ])
              _FilterPill(
                label: kind.label,
                selected: _kind == kind,
                onTap: () => setState(() => _kind = kind),
              ),
          ],
        ),
      ],
    );
  }

  Widget _buildRulesStep(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        _SliderLine(
          label: 'Entry fee',
          value: _entryFee.toDouble(),
          min: 0,
          max: 1000,
          suffix: ' coins',
          onChanged: (double v) => setState(() => _entryFee = v.round()),
        ),
        const SizedBox(height: GtexSpacing.md),
        _SliderLine(
          label: 'Max clubs',
          value: _maxClubs.toDouble(),
          min: 4,
          max: 64,
          suffix: ' clubs',
          onChanged: (double v) => setState(() => _maxClubs = v.round()),
        ),
        const SizedBox(height: GtexSpacing.md),
        DropdownButtonFormField<String>(
          value: _rulePreset,
          decoration: const InputDecoration(labelText: 'Rule preset'),
          items: const <DropdownMenuItem<String>>[
            DropdownMenuItem<String>(
              value: 'Balanced cup rules',
              child: Text('Balanced cup rules'),
            ),
            DropdownMenuItem<String>(
              value: 'National-team rental enabled',
              child: Text('National-team rental enabled'),
            ),
            DropdownMenuItem<String>(
              value: 'Academy/regens only',
              child: Text('Academy/regens only'),
            ),
          ],
          onChanged:
              (String? value) =>
                  setState(() => _rulePreset = value ?? _rulePreset),
        ),
      ],
    );
  }

  Widget _buildReviewStep(BuildContext context) {
    final int prizePool = _entryFee * _maxClubs;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: <Widget>[
        GtexPanel(
          title: _title.text,
          subtitle:
              'Review before Codex wires this to publish preview / live backend creation.',
          accent: GtexColors.gold,
          child: Column(
            children: <Widget>[
              _ReviewRow(label: 'Type', value: _kind.label),
              _ReviewRow(label: 'Entry fee', value: '$_entryFee coins'),
              _ReviewRow(label: 'Max clubs', value: '$_maxClubs'),
              _ReviewRow(label: 'Estimated pool', value: '$prizePool coins'),
              _ReviewRow(label: 'Rules', value: _rulePreset),
              _ReviewRow(label: 'Visibility', value: _visibility),
            ],
          ),
        ),
      ],
    );
  }
}

class _ProgressMonitor extends StatelessWidget {
  const _ProgressMonitor({required this.detail});
  final GtexCompetitionDetail detail;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      itemCount: detail.stages.length,
      separatorBuilder: (_, __) => const SizedBox(height: GtexSpacing.sm),
      itemBuilder: (BuildContext context, int index) {
        final GtexTournamentStageProgress stage = detail.stages[index];
        return GtexPanel(
          accent:
              stage.progressPercent >= 1 ? GtexColors.pitch : GtexColors.gold,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                children: <Widget>[
                  Expanded(
                    child: Text(
                      stage.title,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        color: GtexColors.text,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                  ),
                  GtexStatusChip(
                    label: stage.statusLabel,
                    color:
                        stage.progressPercent >= 1
                            ? GtexColors.pitch
                            : GtexColors.gold,
                  ),
                ],
              ),
              const SizedBox(height: GtexSpacing.sm),
              LinearProgressIndicator(
                value: stage.progressPercent.clamp(0, 1),
                color:
                    stage.progressPercent >= 1
                        ? GtexColors.pitch
                        : GtexColors.gold,
                backgroundColor: GtexColors.line,
              ),
              const SizedBox(height: GtexSpacing.sm),
              Text(
                stage.summary,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  color: GtexColors.textSecondary,
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _FixturesList extends StatelessWidget {
  const _FixturesList({required this.fixtures});
  final List<GtexCompetitionFixture> fixtures;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      itemCount: fixtures.length,
      separatorBuilder: (_, __) => const SizedBox(height: GtexSpacing.sm),
      itemBuilder: (BuildContext context, int index) {
        final GtexCompetitionFixture fixture = fixtures[index];
        return GtexPanel(
          accent: fixture.isLive ? GtexColors.danger : GtexColors.cyan,
          child: Row(
            children: <Widget>[
              GtexStatusChip(
                label: fixture.stage,
                color: fixture.isLive ? GtexColors.danger : GtexColors.cyan,
              ),
              const SizedBox(width: GtexSpacing.md),
              Expanded(
                child: Text(
                  fixture.homeClub,
                  style: const TextStyle(
                    color: GtexColors.text,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              Text(
                fixture.scoreLabel,
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: GtexColors.gold,
                  fontWeight: FontWeight.w900,
                ),
              ),
              Expanded(
                child: Text(
                  fixture.awayClub,
                  textAlign: TextAlign.end,
                  style: const TextStyle(
                    color: GtexColors.text,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
              const SizedBox(width: GtexSpacing.md),
              Text(
                fixture.timeLabel,
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: GtexColors.textMuted),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _StandingsTable extends StatelessWidget {
  const _StandingsTable({required this.standings});
  final List<GtexCompetitionStanding> standings;

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      accent: GtexColors.pitch,
      child: SingleChildScrollView(
        child: DataTable(
          columns: const <DataColumn>[
            DataColumn(label: Text('#')),
            DataColumn(label: Text('Club')),
            DataColumn(label: Text('P')),
            DataColumn(label: Text('W')),
            DataColumn(label: Text('D')),
            DataColumn(label: Text('L')),
            DataColumn(label: Text('GD')),
            DataColumn(label: Text('PTS')),
          ],
          rows: <DataRow>[
            for (final GtexCompetitionStanding row in standings)
              DataRow(
                cells: <DataCell>[
                  DataCell(Text('${row.rank}')),
                  DataCell(Text(row.clubName)),
                  DataCell(Text('${row.played}')),
                  DataCell(Text('${row.wins}')),
                  DataCell(Text('${row.draws}')),
                  DataCell(Text('${row.losses}')),
                  DataCell(Text('${row.goalDifference}')),
                  DataCell(Text('${row.points}')),
                ],
              ),
          ],
        ),
      ),
    );
  }
}

class _BracketProgress extends StatelessWidget {
  const _BracketProgress({required this.stages});
  final List<GtexTournamentStageProgress> stages;

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: <Widget>[
        GtexPanel(
          title: 'Bracket progression',
          subtitle:
              'Current stage progress, fixture state, and settlement readiness for this competition.',
          accent: GtexColors.gold,
          child: Wrap(
            spacing: GtexSpacing.md,
            runSpacing: GtexSpacing.md,
            children: <Widget>[
              for (final GtexTournamentStageProgress stage in stages)
                SizedBox(
                  width: 220,
                  child: GtexPanel(
                    accent:
                        stage.progressPercent > 0
                            ? GtexColors.gold
                            : GtexColors.line,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          stage.title,
                          style: const TextStyle(
                            color: GtexColors.text,
                            fontWeight: FontWeight.w900,
                          ),
                        ),
                        const SizedBox(height: GtexSpacing.sm),
                        GtexStatusChip(
                          label: stage.statusLabel,
                          color:
                              stage.progressPercent >= 1
                                  ? GtexColors.pitch
                                  : GtexColors.gold,
                        ),
                      ],
                    ),
                  ),
                ),
            ],
          ),
        ),
      ],
    );
  }
}

class _RulesList extends StatelessWidget {
  const _RulesList({required this.rules});
  final List<GtexCompetitionRule> rules;

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      itemCount: rules.length,
      separatorBuilder: (_, __) => const SizedBox(height: GtexSpacing.sm),
      itemBuilder: (BuildContext context, int index) {
        final GtexCompetitionRule rule = rules[index];
        return GtexPanel(
          accent: GtexColors.cyan,
          title: rule.title,
          child: Text(
            rule.description,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: GtexColors.textSecondary,
              height: 1.4,
            ),
          ),
        );
      },
    );
  }
}

class _FilterPill extends StatelessWidget {
  const _FilterPill({
    required this.label,
    required this.selected,
    required this.onTap,
  });
  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return ChoiceChip(
      selected: selected,
      label: Text(label),
      onSelected: (_) => onTap(),
      selectedColor: GtexColors.gold.withValues(alpha: .22),
      backgroundColor: GtexColors.panelAlt,
      labelStyle: TextStyle(
        color: selected ? GtexColors.gold : GtexColors.textSecondary,
        fontWeight: FontWeight.w800,
      ),
      side: BorderSide(color: selected ? GtexColors.gold : GtexColors.line),
    );
  }
}

class _ChecklistRow extends StatelessWidget {
  const _ChecklistRow({required this.label, required this.complete});
  final String label;
  final bool complete;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
      child: Row(
        children: <Widget>[
          Icon(
            complete ? Icons.check_circle : Icons.radio_button_unchecked,
            color: complete ? GtexColors.pitch : GtexColors.textMuted,
            size: 18,
          ),
          const SizedBox(width: GtexSpacing.xs),
          Expanded(
            child: Text(
              label,
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: GtexColors.textSecondary),
            ),
          ),
        ],
      ),
    );
  }
}

class _StepHeader extends StatelessWidget {
  const _StepHeader({required this.step});
  final int step;

  @override
  Widget build(BuildContext context) {
    const List<String> labels = <String>['Identity', 'Rules', 'Review'];
    return Row(
      children: <Widget>[
        for (int i = 0; i < labels.length; i++) ...<Widget>[
          Expanded(
            child: Column(
              children: <Widget>[
                CircleAvatar(
                  backgroundColor:
                      i <= step ? GtexColors.gold : GtexColors.panelAlt,
                  foregroundColor:
                      i <= step ? Colors.black : GtexColors.textMuted,
                  child: Text('${i + 1}'),
                ),
                const SizedBox(height: GtexSpacing.xs),
                Text(
                  labels[i],
                  style: TextStyle(
                    color: i <= step ? GtexColors.gold : GtexColors.textMuted,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ],
            ),
          ),
          if (i < labels.length - 1)
            Container(
              width: 40,
              height: 2,
              color: i < step ? GtexColors.gold : GtexColors.line,
            ),
        ],
      ],
    );
  }
}

class _SliderLine extends StatelessWidget {
  const _SliderLine({
    required this.label,
    required this.value,
    required this.min,
    required this.max,
    required this.suffix,
    required this.onChanged,
  });
  final String label;
  final double value;
  final double min;
  final double max;
  final String suffix;
  final ValueChanged<double> onChanged;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          '$label: ${value.round()}$suffix',
          style: const TextStyle(
            color: GtexColors.text,
            fontWeight: FontWeight.w800,
          ),
        ),
        Slider(
          value: value,
          min: min,
          max: max,
          divisions: (max - min).round(),
          onChanged: onChanged,
        ),
      ],
    );
  }
}

class _ReviewRow extends StatelessWidget {
  const _ReviewRow({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: GtexSpacing.xs),
      child: Row(
        children: <Widget>[
          Expanded(
            child: Text(
              label,
              style: const TextStyle(
                color: GtexColors.textMuted,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          Text(
            value,
            style: const TextStyle(
              color: GtexColors.text,
              fontWeight: FontWeight.w900,
            ),
          ),
        ],
      ),
    );
  }
}
