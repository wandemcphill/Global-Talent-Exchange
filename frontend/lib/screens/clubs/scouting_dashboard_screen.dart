import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/club_ops_controller.dart';
import 'package:gte_frontend/data/club_ops_api.dart';
import 'package:gte_frontend/data/gte_api_repository.dart';
import 'package:gte_frontend/models/scouting_models.dart';
import 'package:gte_frontend/screens/clubs/club_ops_screen_host.dart';
import 'package:gte_frontend/screens/clubs/scouting_prospect_detail_screen.dart';
import 'package:gte_frontend/theme/gte_theme_tokens.dart';
import 'package:gte_frontend/widgets/clubs/club_ops_formatters.dart';
import 'package:gte_frontend/widgets/clubs/club_ops_scaffold.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';

class ScoutingDashboardScreen extends StatelessWidget {
  const ScoutingDashboardScreen({
    super.key,
    this.clubId = 'royal-lagos-fc',
    this.clubName,
    this.baseUrl = 'http://127.0.0.1:8000',
    this.mode = GteBackendMode.liveThenFixture,
    this.api,
    this.controller,
  });

  final String clubId;
  final String? clubName;
  final String baseUrl;
  final GteBackendMode mode;
  final ClubOpsApi? api;
  final ClubOpsController? controller;

  @override
  Widget build(BuildContext context) {
    return ClubOpsScreenHost(
      title: 'Recruiter dashboard',
      subtitle:
          'Track talent, run the shortlist, move deals across the pipeline, and spot patterns fast.',
      clubId: clubId,
      clubName: clubName,
      baseUrl: baseUrl,
      mode: mode,
      api: api,
      controller: controller,
      builder: (BuildContext context, ClubOpsController controller) {
        if (controller.isLoadingClubData && !controller.hasClubData) {
          return const Padding(
            padding: EdgeInsets.all(20),
            child: GteStatePanel(
              title: 'Loading recruiter dashboard',
              message:
                  'Preparing your tracked players, shortlist movement, and recommendation signals.',
              icon: Icons.travel_explore_outlined,
            ),
          );
        }

        final ScoutingDashboard? scouting = controller.scouting;
        final YouthPipelineSnapshot? youthPipeline = controller.youthPipeline;
        if (scouting == null || youthPipeline == null) {
          return const Padding(
            padding: EdgeInsets.all(20),
            child: GteStatePanel(
              title: 'Recruiter dashboard unavailable',
              message:
                  'The scouting board did not return enough data to build the recruiter control panel.',
              icon: Icons.person_search_outlined,
            ),
          );
        }

        return _RecruiterDashboardTabs(
          scouting: scouting,
          youthPipeline: youthPipeline,
          controller: controller,
          clubId: clubId,
          clubName: clubName,
        );
      },
    );
  }
}

class _RecruiterDashboardTabs extends StatefulWidget {
  const _RecruiterDashboardTabs({
    required this.scouting,
    required this.youthPipeline,
    required this.controller,
    required this.clubId,
    this.clubName,
  });

  final ScoutingDashboard scouting;
  final YouthPipelineSnapshot youthPipeline;
  final ClubOpsController controller;
  final String clubId;
  final String? clubName;

  @override
  State<_RecruiterDashboardTabs> createState() =>
      _RecruiterDashboardTabsState();
}

class _RecruiterDashboardTabsState extends State<_RecruiterDashboardTabs> {
  static const String _allPositionsLabel = 'All positions';

  late Map<String, _RecruiterPipelineStage> _pipelineStageByProspectId;
  late Map<String, List<String>> _notesByProspectId;
  late Set<String> _removedFromShortlist;

  _ShortlistFilter _statusFilter = _ShortlistFilter.all;
  String _positionFilter = _allPositionsLabel;

  @override
  void initState() {
    super.initState();
    _seedBoardState();
  }

  @override
  void didUpdateWidget(covariant _RecruiterDashboardTabs oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (_prospectSignature(oldWidget.scouting.prospects) !=
        _prospectSignature(widget.scouting.prospects)) {
      _seedBoardState();
    }
  }

  List<Prospect> get _prospects => widget.scouting.prospects;

  List<Prospect> get _shortlistProspects {
    final List<Prospect> prospects = _prospects.where((Prospect prospect) {
      return !_removedFromShortlist.contains(prospect.id) &&
          _stageForProspect(prospect) != _RecruiterPipelineStage.signed;
    }).toList(growable: false);
    prospects.sort((Prospect a, Prospect b) {
      final int scoreCompare = b.readinessScore.compareTo(a.readinessScore);
      if (scoreCompare != 0) {
        return scoreCompare;
      }
      return a.name.compareTo(b.name);
    });
    return prospects;
  }

  List<Prospect> get _recommendedProspects {
    final List<Prospect> prospects = List<Prospect>.from(_shortlistProspects);
    return prospects.take(5).toList(growable: false);
  }

  int get _contactedCount {
    return _prospects.where((Prospect prospect) {
      return _stageForProspect(prospect).index >=
          _RecruiterPipelineStage.contacted.index;
    }).length;
  }

  int get _activeConversationCount {
    return _prospects.where((Prospect prospect) {
      final _RecruiterPipelineStage stage = _stageForProspect(prospect);
      return stage == _RecruiterPipelineStage.contacted ||
          stage == _RecruiterPipelineStage.negotiation;
    }).length;
  }

  List<String> get _availablePositions {
    final Set<String> values = <String>{
      for (final Prospect prospect in _shortlistProspects) prospect.position,
    };
    final List<String> positions = values.toList(growable: false);
    positions.sort();
    return positions;
  }

  List<Prospect> get _filteredShortlist {
    return _shortlistProspects.where((Prospect prospect) {
      final bool matchesPosition = _positionFilter == _allPositionsLabel ||
          prospect.position == _positionFilter;
      final bool matchesStatus =
          _statusFilter.matches(_shortlistStatusFor(prospect));
      return matchesPosition && matchesStatus;
    }).toList(growable: false);
  }

  List<_ActivityEntry> get _recentActivities {
    final List<Prospect> prospects = List<Prospect>.from(_prospects)
      ..sort(
          (Prospect a, Prospect b) => b.lastUpdated.compareTo(a.lastUpdated));
    return prospects.take(5).map(_activityForProspect).toList(growable: false);
  }

  List<_ActionEntry> get _nextActions {
    final List<Prospect> prospects = List<Prospect>.from(_shortlistProspects)
      ..sort((Prospect a, Prospect b) {
        final _RecruiterPipelineStage aStage = _stageForProspect(a);
        final _RecruiterPipelineStage bStage = _stageForProspect(b);
        final int stageCompare = bStage.index.compareTo(aStage.index);
        if (stageCompare != 0) {
          return stageCompare;
        }
        return b.readinessScore.compareTo(a.readinessScore);
      });

    return prospects.take(4).map((Prospect prospect) {
      final _RecruiterPipelineStage stage = _stageForProspect(prospect);
      return _ActionEntry(
        title: prospect.name,
        detail: prospect.nextAction,
        caption: '${stage.label} | ${prospect.currentClub}',
        icon: stage.icon,
      );
    }).toList(growable: false);
  }

  @override
  Widget build(BuildContext context) {
    final GteThemeTokens tokens = GteShellTheme.tokensOf(context);
    return DefaultTabController(
      length: 4,
      child: Column(
        children: <Widget>[
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
            child: Container(
              decoration: BoxDecoration(
                color: tokens.panelStrong.withValues(alpha: 0.9),
                borderRadius: BorderRadius.circular(tokens.radiusLarge),
                border: Border.all(color: tokens.stroke),
              ),
              child: TabBar(
                isScrollable: true,
                dividerColor: Colors.transparent,
                indicatorColor: tokens.accent,
                indicatorSize: TabBarIndicatorSize.tab,
                tabs: const <Tab>[
                  Tab(text: 'Overview'),
                  Tab(text: 'Shortlist'),
                  Tab(text: 'Pipeline'),
                  Tab(text: 'Insights'),
                ],
              ),
            ),
          ),
          Expanded(
            child: TabBarView(
              children: <Widget>[
                _buildOverviewTab(context),
                _buildShortlistTab(context),
                _buildPipelineTab(context),
                _buildInsightsTab(context),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildOverviewTab(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
      children: <Widget>[
        ClubOpsHeadlinePanel(
          title: '${widget.scouting.clubName} recruiter desk',
          subtitle:
              'Who you are tracking, who looks promising, who you are already talking to, and what should happen next.',
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Wrap(
                spacing: 12,
                runSpacing: 12,
                children: <Widget>[
                  ClubOpsStatTile(
                    label: 'Players viewed',
                    value: clubOpsFormatCompactNumber(
                        widget.scouting.liveProspects),
                    detail:
                        '${_prospects.length} active cards are surfaced on this board right now.',
                    icon: Icons.visibility_outlined,
                    highlight: true,
                  ),
                  ClubOpsStatTile(
                    label: 'Shortlisted',
                    value: '${_shortlistProspects.length}',
                    detail: 'Players still active in your recruiter watchlist.',
                    icon: Icons.bookmark_added_outlined,
                  ),
                  ClubOpsStatTile(
                    label: 'Contacted',
                    value: '$_contactedCount',
                    detail:
                        'Players already at contact, negotiation, or signed stage.',
                    icon: Icons.mail_outline,
                  ),
                  ClubOpsStatTile(
                    label: 'Active conversations',
                    value: '$_activeConversationCount',
                    detail:
                        'Open recruiting threads that still need follow-up.',
                    icon: Icons.forum_outlined,
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: <Widget>[
                  _MetaChip(
                    icon: Icons.public_outlined,
                    label: '${widget.scouting.activeRegions} active regions',
                  ),
                  _MetaChip(
                    icon: Icons.assignment_outlined,
                    label:
                        '${widget.scouting.openAssignments} live assignments',
                  ),
                  _MetaChip(
                    icon: Icons.flag_outlined,
                    label:
                        '${widget.scouting.trialsScheduled} trials scheduled',
                  ),
                ],
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        LayoutBuilder(
          builder: (BuildContext context, BoxConstraints constraints) {
            return _buildTwoUpLayout(
              constraints.maxWidth,
              _buildRecentActivityPanel(context),
              _buildNextActionsPanel(context),
            );
          },
        ),
        const SizedBox(height: 16),
        ClubOpsSectionHeader(
          title: 'Recommended players',
          subtitle:
              'Top five matches from the current board with score and fit reasons.',
          action: FilledButton.tonal(
            onPressed: () => DefaultTabController.of(context).animateTo(1),
            child: const Text('Open shortlist'),
          ),
        ),
        const SizedBox(height: 12),
        LayoutBuilder(
          builder: (BuildContext context, BoxConstraints constraints) {
            final int columns = _columnsForWidth(
              constraints.maxWidth,
              minItemWidth: 280,
              maxColumns: 3,
            );
            final double cardWidth =
                _cardWidthFor(constraints.maxWidth, columns);
            return Wrap(
              spacing: 16,
              runSpacing: 16,
              children: _recommendedProspects
                  .map((Prospect prospect) => SizedBox(
                        width: cardWidth,
                        child: _buildRecommendedPlayerCard(context, prospect),
                      ))
                  .toList(growable: false),
            );
          },
        ),
      ],
    );
  }

  Widget _buildShortlistTab(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
      children: <Widget>[
        ClubOpsSectionHeader(
          title: 'Shortlist',
          subtitle:
              'Filter the talent watchlist by recruiter status and position before taking the next step.',
          action: FilledButton.tonal(
            onPressed: _resetFilters,
            child: const Text('Reset filters'),
          ),
        ),
        const SizedBox(height: 12),
        GteSurfacePanel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('Status', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 10),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: _ShortlistFilter.values
                    .map((filter) => ChoiceChip(
                          label: Text(filter.label),
                          selected: _statusFilter == filter,
                          onSelected: (_) {
                            setState(() {
                              _statusFilter = filter;
                            });
                          },
                        ))
                    .toList(growable: false),
              ),
              const SizedBox(height: 16),
              Text('Position', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 10),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: <String>[
                  _allPositionsLabel,
                  ..._availablePositions,
                ]
                    .map((String position) => ChoiceChip(
                          label: Text(position),
                          selected: _positionFilter == position,
                          onSelected: (_) {
                            setState(() {
                              _positionFilter = position;
                            });
                          },
                        ))
                    .toList(growable: false),
              ),
              const SizedBox(height: 16),
              Text(
                '${_filteredShortlist.length} of ${_shortlistProspects.length} players shown',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        if (_filteredShortlist.isEmpty)
          const GteStatePanel(
            title: 'No players match this filter',
            message:
                'Relax the status or position filter to bring prospects back into view.',
            icon: Icons.filter_alt_off_outlined,
          )
        else
          LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final int columns = _columnsForWidth(
                constraints.maxWidth,
                minItemWidth: 360,
                maxColumns: 2,
              );
              final double cardWidth =
                  _cardWidthFor(constraints.maxWidth, columns);
              return Wrap(
                spacing: 16,
                runSpacing: 16,
                children: _filteredShortlist
                    .map((Prospect prospect) => SizedBox(
                          width: cardWidth,
                          child: _buildShortlistCard(context, prospect),
                        ))
                    .toList(growable: false),
              );
            },
          ),
      ],
    );
  }

  Widget _buildRecentActivityPanel(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Recent activity',
              style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 8),
          Text(
            'The most recent movement across your shortlist and pipeline.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 14),
          for (final _ActivityEntry activity in _recentActivities) ...<Widget>[
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Container(
                  width: 34,
                  height: 34,
                  decoration: BoxDecoration(
                    color: activity.color.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(activity.icon, color: activity.color, size: 18),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(activity.title,
                          style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 2),
                      Text(activity.detail,
                          style: Theme.of(context).textTheme.bodyMedium),
                    ],
                  ),
                ),
              ],
            ),
            if (activity != _recentActivities.last) const SizedBox(height: 12),
          ],
        ],
      ),
    );
  }

  Widget _buildNextActionsPanel(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Text('Next actions',
                    style: Theme.of(context).textTheme.titleLarge),
              ),
              FilledButton.tonal(
                onPressed: () => DefaultTabController.of(context).animateTo(2),
                child: const Text('Open pipeline'),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Use these reminders to keep the board moving while the signal is still fresh.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 14),
          for (final _ActionEntry action in _nextActions) ...<Widget>[
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Icon(action.icon, size: 18, color: GteShellTheme.accentWarm),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(action.title,
                          style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 2),
                      Text(action.detail,
                          style: Theme.of(context).textTheme.bodyMedium),
                      const SizedBox(height: 2),
                      Text(action.caption,
                          style: Theme.of(context).textTheme.bodySmall),
                    ],
                  ),
                ),
              ],
            ),
            if (action != _nextActions.last) const SizedBox(height: 12),
          ],
        ],
      ),
    );
  }

  Widget _buildRecommendedPlayerCard(BuildContext context, Prospect prospect) {
    final bool canMove = _stageForProspect(prospect).index <
        _RecruiterPipelineStage.contacted.index;
    final List<String> reasons = _fitReasonsFor(prospect);
    return GteSurfacePanel(
      onTap: () => _openProspectProfile(prospect),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              _PlayerAvatar(
                label: prospect.name,
                accent: _stageColor(context, _stageForProspect(prospect)),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(prospect.name,
                        style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 4),
                    Text(
                      '${prospect.position} | ${prospect.currentClub}',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ],
                ),
              ),
              _ScoreBadge(score: prospect.readinessScore),
            ],
          ),
          const SizedBox(height: 14),
          Text('Why this match looks strong',
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          for (int index = 0;
              index < reasons.take(3).length;
              index++) ...<Widget>[
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                const Padding(
                  padding: EdgeInsets.only(top: 6),
                  child: Icon(Icons.circle, size: 6),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    reasons[index],
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ),
              ],
            ),
            if (index != reasons.take(3).length - 1) const SizedBox(height: 8),
          ],
          const SizedBox(height: 14),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: <Widget>[
              OutlinedButton.icon(
                onPressed: () => _openProspectProfile(prospect),
                icon: const Icon(Icons.open_in_new),
                label: const Text('View profile'),
              ),
              FilledButton.tonalIcon(
                onPressed: canMove ? () => _moveIntoPipeline(prospect) : null,
                icon: const Icon(Icons.swap_horiz),
                label: Text(canMove ? 'Move to pipeline' : 'In pipeline'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildShortlistCard(BuildContext context, Prospect prospect) {
    final _ShortlistStatus status = _shortlistStatusFor(prospect);
    final _RecruiterPipelineStage stage = _stageForProspect(prospect);
    final bool canMove = stage.index < _RecruiterPipelineStage.contacted.index;
    final List<String> notes = _notesForProspect(prospect);
    return GteSurfacePanel(
      onTap: () => _openProspectProfile(prospect),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              _PlayerAvatar(
                label: prospect.name,
                accent: _statusColor(context, status),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(prospect.name,
                        style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 4),
                    Text(
                      '${prospect.position} | ${prospect.region}',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      prospect.currentClub,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: <Widget>[
                  _ScoreBadge(score: prospect.readinessScore),
                  const SizedBox(height: 8),
                  _StatusBadge(
                    label: status.label,
                    color: _statusColor(context, status),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 14),
          Text(
            notes.isEmpty ? prospect.developmentProjection : notes.first,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: _remindersForProspect(prospect)
                .map((String reminder) => _ReminderChip(label: reminder))
                .toList(growable: false),
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: <Widget>[
              OutlinedButton.icon(
                onPressed: () => _openProspectProfile(prospect),
                icon: const Icon(Icons.open_in_new),
                label: const Text('View profile'),
              ),
              FilledButton.tonalIcon(
                onPressed: canMove ? () => _moveIntoPipeline(prospect) : null,
                icon: const Icon(Icons.swap_horiz),
                label: Text(canMove ? 'Move to pipeline' : 'In pipeline'),
              ),
              OutlinedButton.icon(
                onPressed: () => _openNoteComposer(prospect),
                icon: const Icon(Icons.note_add_outlined),
                label: const Text('Add note'),
              ),
              OutlinedButton.icon(
                onPressed: () => _removeFromShortlist(prospect),
                icon: const Icon(Icons.remove_circle_outline),
                label: const Text('Remove from shortlist'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildPipelineTab(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
      children: <Widget>[
        ClubOpsHeadlinePanel(
          title: 'Acquisition flow',
          subtitle:
              'Turn player discovery into a process. Drag any card across the board to update the current recruiting stage.',
          child: Wrap(
            spacing: 8,
            runSpacing: 8,
            children: <Widget>[
              _MetaChip(
                icon: Icons.groups_outlined,
                label: '${_prospects.length} tracked players',
              ),
              _MetaChip(
                icon: Icons.chat_bubble_outline,
                label: '$_activeConversationCount active conversations',
              ),
              _MetaChip(
                icon: Icons.verified_outlined,
                label:
                    '${_countAtOrBeyond(_RecruiterPipelineStage.signed)} signed',
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        ClubOpsSectionHeader(
          title: 'Pipeline board',
          subtitle:
              'Discovered to signed. Drag cards across stages and keep notes close to the player.',
          action: FilledButton.tonal(
            onPressed: _resetBoard,
            child: const Text('Reset board'),
          ),
        ),
        const SizedBox(height: 12),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: _RecruiterPipelineStage.values
                .map((stage) => Padding(
                      padding: EdgeInsets.only(
                        right: stage == _RecruiterPipelineStage.values.last
                            ? 0
                            : 16,
                      ),
                      child: SizedBox(
                        width: 300,
                        child: _buildPipelineColumn(context, stage),
                      ),
                    ))
                .toList(growable: false),
          ),
        ),
      ],
    );
  }

  Widget _buildPipelineColumn(
    BuildContext context,
    _RecruiterPipelineStage stage,
  ) {
    final Color accent = _stageColor(context, stage);
    final List<Prospect> prospects = _prospects.where((Prospect prospect) {
      return _stageForProspect(prospect) == stage;
    }).toList(growable: false)
      ..sort((Prospect a, Prospect b) {
        final int scoreCompare = b.readinessScore.compareTo(a.readinessScore);
        if (scoreCompare != 0) {
          return scoreCompare;
        }
        return a.name.compareTo(b.name);
      });

    return DragTarget<_PipelineDragData>(
      onWillAccept: (_PipelineDragData? data) => data != null,
      onAccept: (_PipelineDragData data) {
        final Prospect prospect = _prospects.firstWhere(
          (Prospect item) => item.id == data.prospectId,
        );
        _moveProspectToStage(prospect, stage);
      },
      builder: (
        BuildContext context,
        List<_PipelineDragData?> candidateData,
        List<dynamic> rejectedData,
      ) {
        final bool isActive = candidateData.isNotEmpty;
        return GteSurfacePanel(
          emphasized: isActive,
          accentColor: accent,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Row(
                children: <Widget>[
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(stage.label,
                            style: Theme.of(context).textTheme.titleLarge),
                        const SizedBox(height: 4),
                        Text(stage.description,
                            style: Theme.of(context).textTheme.bodyMedium),
                      ],
                    ),
                  ),
                  _StatusBadge(
                    label: '${prospects.length}',
                    color: accent,
                  ),
                ],
              ),
              const SizedBox(height: 16),
              if (prospects.isEmpty)
                Text(
                  'Drop a player here.',
                  style: Theme.of(context).textTheme.bodyMedium,
                )
              else
                for (final Prospect prospect in prospects) ...<Widget>[
                  Draggable<_PipelineDragData>(
                    data: _PipelineDragData(prospectId: prospect.id),
                    feedback: Material(
                      color: Colors.transparent,
                      child: SizedBox(
                        width: 268,
                        child: _buildPipelinePlayerCard(
                          context,
                          prospect,
                          stage,
                          isFeedback: true,
                        ),
                      ),
                    ),
                    childWhenDragging: Opacity(
                      opacity: 0.34,
                      child: _buildPipelinePlayerCard(
                        context,
                        prospect,
                        stage,
                      ),
                    ),
                    child: _buildPipelinePlayerCard(
                      context,
                      prospect,
                      stage,
                    ),
                  ),
                  if (prospect != prospects.last) const SizedBox(height: 12),
                ],
            ],
          ),
        );
      },
    );
  }

  Widget _buildPipelinePlayerCard(
    BuildContext context,
    Prospect prospect,
    _RecruiterPipelineStage stage, {
    bool isFeedback = false,
  }) {
    final List<String> notes = _notesForProspect(prospect);
    return GteSurfacePanel(
      onTap: isFeedback ? null : () => _openProspectProfile(prospect),
      padding: const EdgeInsets.all(16),
      accentColor: _stageColor(context, stage),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Text(prospect.name,
                    style: Theme.of(context).textTheme.titleMedium),
              ),
              _ScoreBadge(score: prospect.readinessScore),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            '${prospect.position} | ${prospect.currentClub}',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 12),
          Text(
            notes.isEmpty ? prospect.pathwayFitLabel : notes.first,
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 12),
          Text('Last action', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 4),
          Text(
            _lastActionForProspect(prospect),
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: _remindersForProspect(prospect)
                .take(1)
                .map((String reminder) => _ReminderChip(label: reminder))
                .toList(growable: false),
          ),
          if (!isFeedback) ...<Widget>[
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: <Widget>[
                OutlinedButton.icon(
                  onPressed: () => _openProspectProfile(prospect),
                  icon: const Icon(Icons.open_in_new),
                  label: const Text('View profile'),
                ),
                OutlinedButton.icon(
                  onPressed: () => _openNoteComposer(prospect),
                  icon: const Icon(Icons.note_add_outlined),
                  label: const Text('Add note'),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildInsightsTab(BuildContext context) {
    final _CountryPreference? topCountry =
        _countryPreferences.isEmpty ? null : _countryPreferences.first;
    final _CountMetric? topPosition =
        _positionMetrics.isEmpty ? null : _positionMetrics.first;
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
      children: <Widget>[
        ClubOpsHeadlinePanel(
          title: 'Scouting intelligence',
          subtitle:
              'Use the board to see what positions and countries are paying off and where your conversion is tightening or leaking.',
          child: Wrap(
            spacing: 8,
            runSpacing: 8,
            children: <Widget>[
              if (topCountry != null)
                _MetaChip(
                  icon: Icons.flag_outlined,
                  label: 'Top country: ${topCountry.country}',
                ),
              if (topPosition != null)
                _MetaChip(
                  icon: Icons.sports_soccer_outlined,
                  label: 'Top position: ${topPosition.label}',
                ),
              _MetaChip(
                icon: Icons.auto_graph_outlined,
                label:
                    'Overall conversion ${widget.youthPipeline.conversionPercent.toStringAsFixed(1)}%',
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        LayoutBuilder(
          builder: (BuildContext context, BoxConstraints constraints) {
            return _buildTwoUpLayout(
              constraints.maxWidth,
              _buildPositionsPanel(context),
              _buildCountriesPanel(context),
            );
          },
        ),
        const SizedBox(height: 16),
        ClubOpsSectionHeader(
          title: 'Conversion rates',
          subtitle:
              'How often players are moving from one stage to the next on this board.',
          action: FilledButton.tonal(
            onPressed: () => DefaultTabController.of(context).animateTo(2),
            child: const Text('Open board'),
          ),
        ),
        const SizedBox(height: 12),
        LayoutBuilder(
          builder: (BuildContext context, BoxConstraints constraints) {
            final int columns = _columnsForWidth(
              constraints.maxWidth,
              minItemWidth: 240,
              maxColumns: 4,
            );
            final double cardWidth =
                _cardWidthFor(constraints.maxWidth, columns);
            return Wrap(
              spacing: 16,
              runSpacing: 16,
              children: _conversionMetrics
                  .map((metric) => SizedBox(
                        width: cardWidth,
                        child: GteSurfacePanel(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Text(metric.percentLabel,
                                  style: Theme.of(context)
                                      .textTheme
                                      .headlineSmall),
                              const SizedBox(height: 6),
                              Text(metric.label,
                                  style:
                                      Theme.of(context).textTheme.titleMedium),
                              const SizedBox(height: 8),
                              Text(
                                '${metric.numerator} of ${metric.denominator} players',
                                style: Theme.of(context).textTheme.bodyMedium,
                              ),
                            ],
                          ),
                        ),
                      ))
                  .toList(growable: false),
            );
          },
        ),
        const SizedBox(height: 16),
        GteSurfacePanel(
          emphasized: true,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('Key insight',
                  style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 8),
              Text(
                _headlineInsight,
                style: Theme.of(context).textTheme.bodyLarge,
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        GteSurfacePanel(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('Board notes',
                  style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 12),
              for (final String note in <String>[
                ...widget.scouting.notes,
                ...widget.youthPipeline.notes.take(2)
              ])
                Padding(
                  padding: const EdgeInsets.only(bottom: 10),
                  child:
                      Text(note, style: Theme.of(context).textTheme.bodyMedium),
                ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildPositionsPanel(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Most scouted positions',
              style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 12),
          for (final _CountMetric metric in _positionMetrics.take(4))
            ClubOpsMetricRow(
              label: metric.label,
              value: '${metric.value} tracked',
              valueColor: GteShellTheme.accentClub,
            ),
        ],
      ),
    );
  }

  Widget _buildCountriesPanel(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text('Preferred countries',
              style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 12),
          for (final _CountryPreference country in _countryPreferences.take(4))
            ClubOpsMetricRow(
              label: country.country,
              value:
                  '${country.trackedPlayers} tracked | ${country.averageScore.toStringAsFixed(0)} avg',
              valueColor: GteShellTheme.accentCommunity,
            ),
        ],
      ),
    );
  }

  List<_CountMetric> get _positionMetrics {
    final Map<String, int> counts = <String, int>{};
    for (final Prospect prospect in _prospects) {
      counts.update(prospect.position, (int current) => current + 1,
          ifAbsent: () => 1);
    }
    final List<_CountMetric> metrics = counts.entries
        .map((_MapEntry<String, int> entry) =>
            _CountMetric(label: entry.key, value: entry.value))
        .toList(growable: false);
    metrics.sort((_CountMetric a, _CountMetric b) {
      final int countCompare = b.value.compareTo(a.value);
      if (countCompare != 0) {
        return countCompare;
      }
      return a.label.compareTo(b.label);
    });
    return metrics;
  }

  List<_CountryPreference> get _countryPreferences {
    final Map<String, List<Prospect>> buckets = <String, List<Prospect>>{};
    for (final Prospect prospect in _prospects) {
      buckets.putIfAbsent(prospect.region, () => <Prospect>[]).add(prospect);
    }

    final List<_CountryPreference> countries =
        buckets.entries.map((_MapEntry<String, List<Prospect>> entry) {
      final int totalScore = entry.value.fold<int>(
        0,
        (int running, Prospect prospect) => running + prospect.readinessScore,
      );
      return _CountryPreference(
        country: entry.key,
        trackedPlayers: entry.value.length,
        averageScore: totalScore / entry.value.length,
      );
    }).toList(growable: false);

    countries.sort((_CountryPreference a, _CountryPreference b) {
      final int countCompare = b.trackedPlayers.compareTo(a.trackedPlayers);
      if (countCompare != 0) {
        return countCompare;
      }
      return b.averageScore.compareTo(a.averageScore);
    });
    return countries;
  }

  List<_ConversionMetric> get _conversionMetrics {
    final int discoveredBase =
        _countAtOrBeyond(_RecruiterPipelineStage.discovered);
    final int shortlistedBase =
        _countAtOrBeyond(_RecruiterPipelineStage.shortlisted);
    final int contactedBase =
        _countAtOrBeyond(_RecruiterPipelineStage.contacted);
    final int negotiationBase =
        _countAtOrBeyond(_RecruiterPipelineStage.negotiation);

    return <_ConversionMetric>[
      _ConversionMetric(
        label: 'Discovered to shortlist',
        numerator: shortlistedBase,
        denominator: discoveredBase,
      ),
      _ConversionMetric(
        label: 'Shortlist to contact',
        numerator: contactedBase,
        denominator: shortlistedBase,
      ),
      _ConversionMetric(
        label: 'Contact to negotiation',
        numerator: negotiationBase,
        denominator: contactedBase,
      ),
      _ConversionMetric(
        label: 'Negotiation to signed',
        numerator: _countAtOrBeyond(_RecruiterPipelineStage.signed),
        denominator: negotiationBase,
      ),
    ];
  }

  String get _headlineInsight {
    if (_recommendedProspects.isEmpty) {
      return 'The board needs more live signals before a reliable pattern emerges.';
    }
    final Prospect lead = _recommendedProspects.first;
    final int sameRegionCount = _recommendedProspects
        .where((Prospect prospect) => prospect.region == lead.region)
        .length;
    final bool attackingProfile = _isAttackingPosition(lead.position);
    final String profileLabel =
        attackingProfile ? 'attacking profiles' : '${lead.position} profiles';
    if (sameRegionCount >= 2) {
      return 'Your strongest current matches are clustering around ${lead.region} $profileLabel under 18. Keep that lane warm before the next live window.';
    }
    return '${lead.name} is setting the board standard right now. Use that profile as the benchmark for the next shortlist review.';
  }

  void _seedBoardState() {
    _pipelineStageByProspectId = <String, _RecruiterPipelineStage>{
      for (final Prospect prospect in widget.scouting.prospects)
        prospect.id: _stageFromProspectStage(prospect.stage),
    };
    _notesByProspectId = <String, List<String>>{
      for (final Prospect prospect in widget.scouting.prospects)
        prospect.id: _seedNotesForProspect(prospect),
    };
    _removedFromShortlist = <String>{};
    _statusFilter = _ShortlistFilter.all;
    _positionFilter = _allPositionsLabel;
  }

  List<String> _seedNotesForProspect(Prospect prospect) {
    final ProspectReport? report =
        widget.controller.reportForProspect(prospect.id);
    final List<String> notes = <String>[];
    if (report != null && report.headline.isNotEmpty) {
      notes.add(report.headline);
    }
    if (prospect.developmentProjection.isNotEmpty) {
      notes.add(prospect.developmentProjection);
    }
    if (prospect.pathwayFitLabel.isNotEmpty) {
      notes.add(prospect.pathwayFitLabel);
    }
    return notes.toSet().toList(growable: false);
  }

  String _prospectSignature(List<Prospect> prospects) {
    return prospects
        .map((Prospect prospect) =>
            '${prospect.id}:${prospect.stage.name}:${prospect.lastUpdated.toIso8601String()}')
        .join('|');
  }

  _RecruiterPipelineStage _stageForProspect(Prospect prospect) {
    return _pipelineStageByProspectId[prospect.id] ??
        _stageFromProspectStage(prospect.stage);
  }

  _ShortlistStatus _shortlistStatusFor(Prospect prospect) {
    switch (_stageForProspect(prospect)) {
      case _RecruiterPipelineStage.discovered:
        return _ShortlistStatus.newLead;
      case _RecruiterPipelineStage.shortlisted:
        return _ShortlistStatus.reviewed;
      case _RecruiterPipelineStage.contacted:
      case _RecruiterPipelineStage.negotiation:
      case _RecruiterPipelineStage.signed:
        return _ShortlistStatus.contacted;
    }
  }

  List<String> _notesForProspect(Prospect prospect) {
    return _notesByProspectId[prospect.id] ?? const <String>[];
  }

  List<String> _remindersForProspect(Prospect prospect) {
    final _RecruiterPipelineStage stage = _stageForProspect(prospect);
    final List<String> reminders = <String>[prospect.nextAction];
    switch (stage) {
      case _RecruiterPipelineStage.discovered:
        reminders.add('Review match video');
      case _RecruiterPipelineStage.shortlisted:
        reminders.add('Book recruiter check-in');
      case _RecruiterPipelineStage.contacted:
        reminders.add('Follow up with agent');
      case _RecruiterPipelineStage.negotiation:
        reminders.add('Prepare final terms pack');
      case _RecruiterPipelineStage.signed:
        reminders.add('Plan onboarding block');
    }
    return reminders
        .where((String item) => item.trim().isNotEmpty)
        .toSet()
        .take(2)
        .toList(growable: false);
  }

  _ActivityEntry _activityForProspect(Prospect prospect) {
    final _RecruiterPipelineStage stage = _stageForProspect(prospect);
    return _ActivityEntry(
      title: '${stage.activityVerb} ${prospect.name}',
      detail:
          '${prospect.currentClub} | ${clubOpsFormatDate(prospect.lastUpdated)}',
      icon: stage.icon,
      color: _stageColor(context, stage),
    );
  }

  String _lastActionForProspect(Prospect prospect) {
    final _RecruiterPipelineStage stage = _stageForProspect(prospect);
    return '${stage.activityVerb} | ${clubOpsFormatDate(prospect.lastUpdated)}';
  }

  int _countAtOrBeyond(_RecruiterPipelineStage stage) {
    return _prospects.where((Prospect prospect) {
      return _stageForProspect(prospect).index >= stage.index;
    }).length;
  }

  void _moveIntoPipeline(Prospect prospect) {
    final _RecruiterPipelineStage currentStage = _stageForProspect(prospect);
    if (currentStage.index >= _RecruiterPipelineStage.contacted.index) {
      return;
    }
    setState(() {
      _pipelineStageByProspectId[prospect.id] =
          _RecruiterPipelineStage.contacted;
    });
  }

  void _removeFromShortlist(Prospect prospect) {
    setState(() {
      _removedFromShortlist.add(prospect.id);
    });
  }

  void _moveProspectToStage(
    Prospect prospect,
    _RecruiterPipelineStage stage,
  ) {
    setState(() {
      _pipelineStageByProspectId[prospect.id] = stage;
    });
  }

  void _resetFilters() {
    setState(() {
      _statusFilter = _ShortlistFilter.all;
      _positionFilter = _allPositionsLabel;
    });
  }

  void _resetBoard() {
    final Map<String, List<String>> existingNotes = _notesByProspectId;
    setState(() {
      _pipelineStageByProspectId = <String, _RecruiterPipelineStage>{
        for (final Prospect prospect in widget.scouting.prospects)
          prospect.id: _stageFromProspectStage(prospect.stage),
      };
      _removedFromShortlist.clear();
      _notesByProspectId = existingNotes;
    });
  }

  Future<void> _openNoteComposer(Prospect prospect) async {
    final TextEditingController noteController = TextEditingController();
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (BuildContext sheetContext) {
        return Padding(
          padding: EdgeInsets.fromLTRB(
            20,
            20,
            20,
            20 + MediaQuery.of(sheetContext).viewInsets.bottom,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Add note for ${prospect.name}',
                style: Theme.of(sheetContext).textTheme.titleLarge,
              ),
              const SizedBox(height: 8),
              Text(
                'Keep the note specific enough to drive the next action.',
                style: Theme.of(sheetContext).textTheme.bodyMedium,
              ),
              const SizedBox(height: 16),
              TextField(
                controller: noteController,
                maxLines: 4,
                decoration: const InputDecoration(
                  hintText: 'Strong aerial ability, needs stamina work',
                ),
              ),
              const SizedBox(height: 16),
              Row(
                children: <Widget>[
                  OutlinedButton(
                    onPressed: () => Navigator.of(sheetContext).pop(),
                    child: const Text('Cancel'),
                  ),
                  const SizedBox(width: 12),
                  FilledButton(
                    onPressed: () {
                      final String note = noteController.text.trim();
                      if (note.isEmpty) {
                        Navigator.of(sheetContext).pop();
                        return;
                      }
                      setState(() {
                        final List<String> existing =
                            List<String>.from(_notesForProspect(prospect));
                        existing.insert(0, note);
                        _notesByProspectId[prospect.id] = existing;
                      });
                      Navigator.of(sheetContext).pop();
                    },
                    child: const Text('Save note'),
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }

  void _openProspectProfile(Prospect prospect) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => ScoutingProspectDetailScreen(
          prospectId: prospect.id,
          controller: widget.controller,
          clubId: widget.clubId,
          clubName: widget.clubName,
        ),
      ),
    );
  }

  List<String> _fitReasonsFor(Prospect prospect) {
    return <String>[
      'Match score ${prospect.readinessScore} and ${prospect.pathwayFitLabel.toLowerCase()}.',
      if (prospect.strengths.isNotEmpty)
        'Strengths: ${prospect.strengths.take(2).join(', ')}.',
      if (prospect.focusAreas.isNotEmpty)
        'Development note: ${prospect.focusAreas.take(2).join(', ')}.',
    ];
  }

  Widget _buildTwoUpLayout(
    double maxWidth,
    Widget left,
    Widget right,
  ) {
    if (maxWidth < 920) {
      return Column(
        children: <Widget>[
          left,
          const SizedBox(height: 16),
          right,
        ],
      );
    }
    final double panelWidth = (maxWidth - 16) / 2;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        SizedBox(width: panelWidth, child: left),
        const SizedBox(width: 16),
        SizedBox(width: panelWidth, child: right),
      ],
    );
  }

  int _columnsForWidth(
    double width, {
    required double minItemWidth,
    required int maxColumns,
  }) {
    final int rawColumns = (width / minItemWidth).floor();
    if (rawColumns <= 1) {
      return 1;
    }
    if (rawColumns >= maxColumns) {
      return maxColumns;
    }
    return rawColumns;
  }

  double _cardWidthFor(double width, int columns) {
    if (columns <= 1) {
      return width;
    }
    return (width - ((columns - 1) * 16)) / columns;
  }

  Color _stageColor(BuildContext context, _RecruiterPipelineStage stage) {
    final GteThemeTokens tokens = GteShellTheme.tokensOf(context);
    switch (stage) {
      case _RecruiterPipelineStage.discovered:
        return tokens.accentClub;
      case _RecruiterPipelineStage.shortlisted:
        return tokens.accent;
      case _RecruiterPipelineStage.contacted:
        return tokens.accentArena;
      case _RecruiterPipelineStage.negotiation:
        return tokens.accentWarm;
      case _RecruiterPipelineStage.signed:
        return tokens.positive;
    }
  }

  Color _statusColor(BuildContext context, _ShortlistStatus status) {
    final GteThemeTokens tokens = GteShellTheme.tokensOf(context);
    switch (status) {
      case _ShortlistStatus.newLead:
        return tokens.accentClub;
      case _ShortlistStatus.reviewed:
        return tokens.accent;
      case _ShortlistStatus.contacted:
        return tokens.accentArena;
    }
  }
}

enum _RecruiterPipelineStage {
  discovered,
  shortlisted,
  contacted,
  negotiation,
  signed
}

extension _RecruiterPipelineStagePresentation on _RecruiterPipelineStage {
  String get label {
    switch (this) {
      case _RecruiterPipelineStage.discovered:
        return 'Discovered';
      case _RecruiterPipelineStage.shortlisted:
        return 'Shortlisted';
      case _RecruiterPipelineStage.contacted:
        return 'Contacted';
      case _RecruiterPipelineStage.negotiation:
        return 'Negotiation';
      case _RecruiterPipelineStage.signed:
        return 'Signed';
    }
  }

  String get description {
    switch (this) {
      case _RecruiterPipelineStage.discovered:
        return 'Fresh names that still need review.';
      case _RecruiterPipelineStage.shortlisted:
        return 'Tracked closely and worth deeper evaluation.';
      case _RecruiterPipelineStage.contacted:
        return 'Agent or club contact already opened.';
      case _RecruiterPipelineStage.negotiation:
        return 'Terms, welfare, or fit details being worked through.';
      case _RecruiterPipelineStage.signed:
        return 'Closed and ready for onboarding.';
    }
  }

  String get activityVerb {
    switch (this) {
      case _RecruiterPipelineStage.discovered:
        return 'Tracked';
      case _RecruiterPipelineStage.shortlisted:
        return 'Shortlisted';
      case _RecruiterPipelineStage.contacted:
        return 'Contacted agent for';
      case _RecruiterPipelineStage.negotiation:
        return 'Opened terms for';
      case _RecruiterPipelineStage.signed:
        return 'Signed';
    }
  }

  IconData get icon {
    switch (this) {
      case _RecruiterPipelineStage.discovered:
        return Icons.visibility_outlined;
      case _RecruiterPipelineStage.shortlisted:
        return Icons.bookmark_added_outlined;
      case _RecruiterPipelineStage.contacted:
        return Icons.mail_outline;
      case _RecruiterPipelineStage.negotiation:
        return Icons.handshake_outlined;
      case _RecruiterPipelineStage.signed:
        return Icons.verified_outlined;
    }
  }
}

enum _ShortlistStatus { newLead, reviewed, contacted }

extension _ShortlistStatusPresentation on _ShortlistStatus {
  String get label {
    switch (this) {
      case _ShortlistStatus.newLead:
        return 'New';
      case _ShortlistStatus.reviewed:
        return 'Reviewed';
      case _ShortlistStatus.contacted:
        return 'Contacted';
    }
  }
}

enum _ShortlistFilter { all, newLead, reviewed, contacted }

extension _ShortlistFilterPresentation on _ShortlistFilter {
  String get label {
    switch (this) {
      case _ShortlistFilter.all:
        return 'All';
      case _ShortlistFilter.newLead:
        return 'New';
      case _ShortlistFilter.reviewed:
        return 'Reviewed';
      case _ShortlistFilter.contacted:
        return 'Contacted';
    }
  }

  bool matches(_ShortlistStatus status) {
    switch (this) {
      case _ShortlistFilter.all:
        return true;
      case _ShortlistFilter.newLead:
        return status == _ShortlistStatus.newLead;
      case _ShortlistFilter.reviewed:
        return status == _ShortlistStatus.reviewed;
      case _ShortlistFilter.contacted:
        return status == _ShortlistStatus.contacted;
    }
  }
}

class _ActivityEntry {
  const _ActivityEntry({
    required this.title,
    required this.detail,
    required this.icon,
    required this.color,
  });

  final String title;
  final String detail;
  final IconData icon;
  final Color color;
}

class _ActionEntry {
  const _ActionEntry({
    required this.title,
    required this.detail,
    required this.caption,
    required this.icon,
  });

  final String title;
  final String detail;
  final String caption;
  final IconData icon;
}

class _CountMetric {
  const _CountMetric({
    required this.label,
    required this.value,
  });

  final String label;
  final int value;
}

class _CountryPreference {
  const _CountryPreference({
    required this.country,
    required this.trackedPlayers,
    required this.averageScore,
  });

  final String country;
  final int trackedPlayers;
  final double averageScore;
}

class _ConversionMetric {
  const _ConversionMetric({
    required this.label,
    required this.numerator,
    required this.denominator,
  });

  final String label;
  final int numerator;
  final int denominator;

  String get percentLabel {
    if (denominator <= 0) {
      return '0%';
    }
    return '${((numerator / denominator) * 100).toStringAsFixed(0)}%';
  }
}

class _PipelineDragData {
  const _PipelineDragData({
    required this.prospectId,
  });

  final String prospectId;
}

class _MetaChip extends StatelessWidget {
  const _MetaChip({
    required this.icon,
    required this.label,
  });

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Chip(
      avatar: Icon(icon, size: 18),
      label: Text(label),
    );
  }
}

class _ReminderChip extends StatelessWidget {
  const _ReminderChip({
    required this.label,
  });

  final String label;

  @override
  Widget build(BuildContext context) {
    final GteThemeTokens tokens = GteShellTheme.tokensOf(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(tokens.radiusPill),
        color: tokens.surfaceHighlight.withValues(alpha: 0.08),
        border: Border.all(color: tokens.stroke),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.bodySmall,
      ),
    );
  }
}

class _PlayerAvatar extends StatelessWidget {
  const _PlayerAvatar({
    required this.label,
    required this.accent,
  });

  final String label;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final List<String> parts = label
        .split(' ')
        .where((String item) => item.trim().isNotEmpty)
        .toList(growable: false);
    final String initials = parts.take(2).map((String item) => item[0]).join();
    return Container(
      width: 46,
      height: 46,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: accent.withValues(alpha: 0.16),
        border: Border.all(color: accent.withValues(alpha: 0.5)),
      ),
      alignment: Alignment.center,
      child: Text(
        initials.toUpperCase(),
        style: Theme.of(context).textTheme.titleMedium,
      ),
    );
  }
}

class _ScoreBadge extends StatelessWidget {
  const _ScoreBadge({
    required this.score,
  });

  final int score;

  @override
  Widget build(BuildContext context) {
    final GteThemeTokens tokens = GteShellTheme.tokensOf(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(tokens.radiusPill),
        color: tokens.accent.withValues(alpha: 0.16),
        border: Border.all(color: tokens.accent.withValues(alpha: 0.4)),
      ),
      child: Text(
        'Score $score',
        style: Theme.of(context).textTheme.titleMedium,
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({
    required this.label,
    required this.color,
  });

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(999),
        color: color.withValues(alpha: 0.14),
        border: Border.all(color: color.withValues(alpha: 0.45)),
      ),
      child: Text(
        label,
        style: Theme.of(context)
            .textTheme
            .bodySmall
            ?.copyWith(color: color, fontWeight: FontWeight.w700),
      ),
    );
  }
}

_RecruiterPipelineStage _stageFromProspectStage(ProspectStage stage) {
  switch (stage) {
    case ProspectStage.monitored:
      return _RecruiterPipelineStage.discovered;
    case ProspectStage.shortlisted:
      return _RecruiterPipelineStage.shortlisted;
    case ProspectStage.trial:
      return _RecruiterPipelineStage.contacted;
    case ProspectStage.scholarship:
      return _RecruiterPipelineStage.negotiation;
    case ProspectStage.promoted:
      return _RecruiterPipelineStage.signed;
  }
}

bool _isAttackingPosition(String position) {
  return const <String>{'LW', 'RW', 'CF', 'ST', 'SS', 'AM'}.contains(position);
}

typedef _MapEntry<K, V> = MapEntry<K, V>;
