import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/app_feedback.dart';
import '../../core/constants/app_spacing.dart';
import '../../navigation/app_destinations.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';
import '../shared/data/feature_telemetry.dart';
import '../shared/data/gte_feature_support.dart';
import 'live_national_teams_provider.dart';

class NationalTeamsScreen extends ConsumerStatefulWidget {
  const NationalTeamsScreen({super.key});

  @override
  ConsumerState<NationalTeamsScreen> createState() =>
      _NationalTeamsScreenState();
}

class _NationalTeamsScreenState extends ConsumerState<NationalTeamsScreen> {
  @override
  void initState() {
    super.initState();
    trackFeatureEvent(
      topic: 'national_teams',
      name: 'national_teams_hub_viewed',
      dedupeKey: 'national-teams-hub-view',
    );
  }

  @override
  Widget build(BuildContext context) {
    final AsyncValue<NationalTeamsHubData> value = ref.watch(
      nationalTeamsHubProvider,
    );
    return AppPageLayout(
      title: 'National Teams',
      subtitle:
          'Live country competitions, rankings, lifecycle detail, and draft squad actions are now wired to the national team backend.',
      trailing: DataSourceBadge(
        status:
            value.hasError ? DataSourceStatus.blocked : DataSourceStatus.live,
      ),
      children: <Widget>[
        value.when(
          data: (NationalTeamsHubData data) {
            final Iterable<dynamic> managedEntries =
                data.history?.managedEntries ?? const <dynamic>[];
            return Column(
              children: <Widget>[
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(spacingLG),
                    child: Wrap(
                      spacing: spacingSM,
                      runSpacing: spacingSM,
                      children: <Widget>[
                        _MetricChip(
                          label: 'Competitions',
                          value: '${data.competitions.length}',
                        ),
                        _MetricChip(
                          label: 'Rankings',
                          value: '${data.rankings.length}',
                        ),
                        _MetricChip(
                          label: 'My entries',
                          value: '${managedEntries.length}',
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: spacingMD),
                _SectionCard(
                  title: 'Competitions',
                  subtitle:
                      'Every competition opens a live detail route with lifecycle and presentation data.',
                  child:
                      data.competitions.isEmpty
                          ? const _EmptyState(
                            message:
                                'No national team competitions returned yet.',
                          )
                          : Column(
                            children: data.competitions
                                .map(
                                  (competition) => ListTile(
                                    contentPadding: EdgeInsets.zero,
                                    title: Text(competition.title),
                                    subtitle: Text(
                                      '${competition.seasonLabel} | ${competition.regionType} | ${competition.status}',
                                    ),
                                    trailing: FilledButton(
                                      onPressed:
                                          () => context.push(
                                            AppRoutes.nationalTeamDetailLocation(
                                              competition.id,
                                            ),
                                          ),
                                      child: const Text('Open'),
                                    ),
                                  ),
                                )
                                .toList(growable: false),
                          ),
                ),
                const SizedBox(height: spacingMD),
                _SectionCard(
                  title: 'Country rankings',
                  subtitle: 'Live `/national-team-engine/rankings` feed.',
                  child:
                      data.rankings.isEmpty
                          ? const _EmptyState(
                            message: 'Country rankings are not available yet.',
                          )
                          : Column(
                            children: data.rankings
                                .take(12)
                                .map(
                                  (
                                    NationalTeamCountryRankingRecord item,
                                  ) => ListTile(
                                    contentPadding: EdgeInsets.zero,
                                    title: Text(item.countryName),
                                    subtitle: Text(
                                      'ELO ${item.eloRating.toStringAsFixed(1)} | W ${item.wins} D ${item.draws} L ${item.losses} | Titles ${item.titles}',
                                    ),
                                  ),
                                )
                                .toList(growable: false),
                          ),
                ),
                if (managedEntries.isNotEmpty) ...<Widget>[
                  const SizedBox(height: spacingMD),
                  _SectionCard(
                    title: 'My history',
                    subtitle:
                        'Authenticated sessions also read `/national-team-engine/me/history`.',
                    child: Column(
                      children: managedEntries
                          .map(
                            (dynamic entry) => ListTile(
                              contentPadding: EdgeInsets.zero,
                              title: Text(entry.countryName as String),
                              subtitle: Text(
                                '${entry.competitionId} | Squad ${entry.squadSize}',
                              ),
                            ),
                          )
                          .toList(growable: false),
                    ),
                  ),
                ],
              ],
            );
          },
          loading:
              () => const Center(
                child: Padding(
                  padding: EdgeInsets.all(spacingLG),
                  child: CircularProgressIndicator(),
                ),
              ),
          error:
              (Object error, StackTrace stackTrace) => _BlockedCard(
                title: 'National teams are blocked',
                message: AppFeedback.messageFor(error),
              ),
        ),
      ],
    );
  }
}

class NationalTeamCompetitionDetailScreen extends ConsumerStatefulWidget {
  const NationalTeamCompetitionDetailScreen({
    super.key,
    required this.competitionId,
  });

  final String competitionId;

  @override
  ConsumerState<NationalTeamCompetitionDetailScreen> createState() =>
      _NationalTeamCompetitionDetailScreenState();
}

class _NationalTeamCompetitionDetailScreenState
    extends ConsumerState<NationalTeamCompetitionDetailScreen> {
  @override
  void initState() {
    super.initState();
    trackFeatureEvent(
      topic: 'national_teams',
      name: 'national_team_competition_viewed',
      payload: <String, Object?>{'competition_id': widget.competitionId},
      dedupeKey: 'national-team-${widget.competitionId}',
    );
  }

  @override
  Widget build(BuildContext context) {
    final AsyncValue<NationalTeamCompetitionDetailData> value = ref.watch(
      nationalTeamCompetitionDetailProvider(widget.competitionId),
    );
    return AppPageLayout(
      title: value.maybeWhen(
        data:
            (NationalTeamCompetitionDetailData data) => data.competition.title,
        orElse: () => 'National team competition',
      ),
      subtitle:
          'Live lifecycle detail plus a draft-squad action backed by `/national-team-engine/competitions/${widget.competitionId}`.',
      trailing: DataSourceBadge(
        status:
            value.hasError ? DataSourceStatus.blocked : DataSourceStatus.live,
      ),
      children: <Widget>[
        value.when(
          data: (NationalTeamCompetitionDetailData detail) {
            final List<JsonMap> representativeEntries = jsonMapList(
              detail.lifecycle['representative_entries'],
              label: 'representative entries',
            );
            final List<JsonMap> qualifiedEntries = jsonMapList(
              detail.lifecycle['qualified_entries'],
              label: 'qualified entries',
            );
            final List<JsonMap> submittedEntries = jsonMapList(
              detail.lifecycle['submitted_entries'],
              label: 'submitted entries',
            );
            final List<JsonMap> stageHistory = jsonMapList(
              detail.lifecycle['stage_history'],
              label: 'stage history',
            );
            final List<JsonMap> storyEvents = jsonMapList(
              detail.presentation['story_events'],
              label: 'story events',
            );
            final List<JsonMap> activeAds = jsonMapList(
              detail.presentation['active_ads'],
              label: 'active ads',
            );
            final JsonMap? activeTheme = jsonMapOrNull(
              detail.presentation['active_theme'],
            );
            final List<dynamic> myEntries =
                detail.history?.managedEntries
                    .where(
                      (entry) => entry.competitionId == widget.competitionId,
                    )
                    .toList(growable: false) ??
                const <dynamic>[];
            return Column(
              children: <Widget>[
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(spacingLG),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Wrap(
                          spacing: spacingSM,
                          runSpacing: spacingSM,
                          children: <Widget>[
                            _MetricChip(
                              label: 'Season',
                              value: detail.competition.seasonLabel,
                            ),
                            _MetricChip(
                              label: 'Region',
                              value: detail.competition.regionType,
                            ),
                            _MetricChip(
                              label: 'Age band',
                              value: detail.competition.ageBand,
                            ),
                            _MetricChip(
                              label: 'Format',
                              value: detail.competition.formatType,
                            ),
                            _MetricChip(
                              label: 'Lifecycle',
                              value: stringValue(
                                detail.lifecycle['current_stage'],
                                fallback: detail.competition.status,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: spacingMD),
                        FilledButton(
                          onPressed: () => _runAutoBuild(context),
                          child: const Text('Build draft squad'),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: spacingMD),
                if (myEntries.isNotEmpty) ...<Widget>[
                  _SectionCard(
                    title: 'My submitted entries',
                    subtitle:
                        'Authenticated session history for this competition.',
                    child: Column(
                      children: myEntries
                          .map(
                            (dynamic entry) => ListTile(
                              contentPadding: EdgeInsets.zero,
                              title: Text(entry.countryName as String),
                              subtitle: Text(
                                'Squad ${entry.squadSize} | Updated ${entry.updatedAt}',
                              ),
                            ),
                          )
                          .toList(growable: false),
                    ),
                  ),
                  const SizedBox(height: spacingMD),
                ],
                _SectionCard(
                  title: 'Lifecycle overview',
                  subtitle:
                      'Representative, qualified, and submitted entries are all coming from the live lifecycle payload.',
                  child: Column(
                    children: <Widget>[
                      _LifecycleList(
                        title: 'Representative entries',
                        items: representativeEntries,
                      ),
                      const SizedBox(height: spacingMD),
                      _LifecycleList(
                        title: 'Qualified entries',
                        items: qualifiedEntries,
                      ),
                      const SizedBox(height: spacingMD),
                      _LifecycleList(
                        title: 'Submitted entries',
                        items: submittedEntries,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: spacingMD),
                _SectionCard(
                  title: 'Stage history',
                  subtitle: 'The competition lifecycle progress log.',
                  child:
                      stageHistory.isEmpty
                          ? const _EmptyState(
                            message: 'No stage history has been recorded yet.',
                          )
                          : Column(
                            children: stageHistory
                                .map(
                                  (JsonMap item) => ListTile(
                                    contentPadding: EdgeInsets.zero,
                                    title: Text(
                                      stringValue(
                                        item['stage'],
                                        fallback: 'Stage',
                                      ),
                                    ),
                                    subtitle: Text(
                                      stringValue(
                                        item['summary'],
                                        fallback: 'No summary available.',
                                      ),
                                    ),
                                  ),
                                )
                                .toList(growable: false),
                          ),
                ),
                const SizedBox(height: spacingMD),
                _SectionCard(
                  title: 'Presentation layer',
                  subtitle:
                      'Live tournament presentation data, including theme, ads, and stories.',
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      if (activeTheme != null)
                        Chip(
                          label: Text(
                            'Theme ${stringValue(activeTheme['visual_style'], fallback: 'default')}',
                          ),
                        ),
                      if (activeAds.isNotEmpty) ...<Widget>[
                        const SizedBox(height: spacingSM),
                        Text(
                          'Active ads',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: spacingSM),
                        ...activeAds.map(
                          (JsonMap ad) => ListTile(
                            contentPadding: EdgeInsets.zero,
                            title: Text(
                              stringValue(ad['placement'], fallback: 'Ad'),
                            ),
                            subtitle: Text(
                              stringValue(
                                ad['asset_url'],
                                fallback: 'Asset unavailable.',
                              ),
                            ),
                          ),
                        ),
                      ],
                      if (storyEvents.isNotEmpty) ...<Widget>[
                        const SizedBox(height: spacingSM),
                        Text(
                          'Story events',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: spacingSM),
                        ...storyEvents.map(
                          (JsonMap story) => ListTile(
                            contentPadding: EdgeInsets.zero,
                            title: Text(
                              stringValue(story['type'], fallback: 'Story'),
                            ),
                            subtitle: Text(
                              stringValue(
                                story['narrative_text'],
                                fallback: 'No narrative text.',
                              ),
                            ),
                          ),
                        ),
                      ],
                      if (activeTheme == null &&
                          activeAds.isEmpty &&
                          storyEvents.isEmpty)
                        const _EmptyState(
                          message: 'No live presentation data returned yet.',
                        ),
                    ],
                  ),
                ),
              ],
            );
          },
          loading:
              () => const Center(
                child: Padding(
                  padding: EdgeInsets.all(spacingLG),
                  child: CircularProgressIndicator(),
                ),
              ),
          error:
              (Object error, StackTrace stackTrace) => _BlockedCard(
                title: 'Competition detail is blocked',
                message: AppFeedback.messageFor(error),
              ),
        ),
      ],
    );
  }

  Future<void> _runAutoBuild(BuildContext context) async {
    final TextEditingController countryController = TextEditingController(
      text: 'NG',
    );
    final TextEditingController budgetController = TextEditingController(
      text: '2500000',
    );
    final TextEditingController tacticController = TextEditingController(
      text: 'balanced',
    );
    final bool? confirmed = await showDialog<bool>(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: const Text('Build draft squad'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              TextField(
                controller: countryController,
                decoration: const InputDecoration(labelText: 'Country code'),
              ),
              const SizedBox(height: spacingSM),
              TextField(
                controller: budgetController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'Budget coin'),
              ),
              const SizedBox(height: spacingSM),
              TextField(
                controller: tacticController,
                decoration: const InputDecoration(labelText: 'Tactic'),
              ),
            ],
          ),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Run'),
            ),
          ],
        );
      },
    );
    if (confirmed != true) {
      return;
    }
    final double? budget = double.tryParse(budgetController.text.trim());
    if (budget == null || budget <= 0) {
      if (!mounted) {
        return;
      }
      AppFeedback.showError(
        this.context,
        'Enter a valid positive budget before building a squad.',
      );
      return;
    }
    try {
      final JsonMap result = await ref
          .read(nationalTeamsApiProvider)
          .buildAutoSquad(
            competitionId: widget.competitionId,
            countryCode: countryController.text.trim().toUpperCase(),
            budgetCoin: budget,
            tactic:
                tacticController.text.trim().isEmpty
                    ? 'balanced'
                    : tacticController.text.trim(),
          );
      trackFeatureEvent(
        topic: 'national_teams',
        name: 'national_team_auto_build_completed',
        payload: <String, Object?>{
          'competition_id': widget.competitionId,
          'country_code': countryController.text.trim().toUpperCase(),
        },
      );
      if (!mounted) {
        return;
      }
      await showModalBottomSheet<void>(
        context: this.context,
        isScrollControlled: true,
        builder: (BuildContext context) {
          final List<JsonMap> players = jsonMapList(
            result['players'],
            label: 'auto build players',
          );
          return SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(spacingLG),
              child: SingleChildScrollView(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    Text(
                      'Draft squad result',
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    const SizedBox(height: spacingMD),
                    Wrap(
                      spacing: spacingSM,
                      runSpacing: spacingSM,
                      children: <Widget>[
                        _MetricChip(
                          label: 'Formation',
                          value: stringValue(result['formation']),
                        ),
                        _MetricChip(
                          label: 'Selected',
                          value: '${intValue(result['selected_count'])}',
                        ),
                        _MetricChip(
                          label: 'Budget',
                          value: numberValue(
                            result['requested_budget_coin'],
                          ).toStringAsFixed(0),
                        ),
                        _MetricChip(
                          label: 'Remaining',
                          value: numberValue(
                            result['remaining_budget_coin'],
                          ).toStringAsFixed(0),
                        ),
                      ],
                    ),
                    const SizedBox(height: spacingMD),
                    if (players.isEmpty)
                      const _EmptyState(
                        message:
                            'No draft squad could be built for that input.',
                      )
                    else
                      ...players.map(
                        (JsonMap player) => ListTile(
                          contentPadding: EdgeInsets.zero,
                          title: Text(
                            stringValue(
                              player['player_name'],
                              fallback: 'Player',
                            ),
                          ),
                          subtitle: Text(
                            '${stringValue(player['assigned_slot'], fallback: 'slot pending')} | ${stringValue(player['primary_position'], fallback: 'position pending')} | ${numberValue(player['loan_price_coin']).toStringAsFixed(0)} coin',
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ),
          );
        },
      );
    } catch (error) {
      if (!mounted) {
        return;
      }
      AppFeedback.showError(this.context, error);
    }
  }
}

class _LifecycleList extends StatelessWidget {
  const _LifecycleList({required this.title, required this.items});

  final String title;
  final List<JsonMap> items;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(title, style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: spacingSM),
        if (items.isEmpty)
          const _EmptyState(message: 'No teams recorded for this stage yet.')
        else
          ...items.map(
            (JsonMap item) => ListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(
                stringValue(item['country_name'], fallback: 'Country'),
              ),
              subtitle: Text(
                '${stringValue(item['status'], fallback: 'submitted')} | Strength ${numberValue(item['strength_rating']).toStringAsFixed(1)}',
              ),
            ),
          ),
      ],
    );
  }
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({
    required this.title,
    required this.subtitle,
    required this.child,
  });

  final String title;
  final String subtitle;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(spacingLG),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(title, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: spacingXS),
            Text(subtitle),
            const SizedBox(height: spacingMD),
            child,
          ],
        ),
      ),
    );
  }
}

class _MetricChip extends StatelessWidget {
  const _MetricChip({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Chip(label: Text('$label: $value'));
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Text(message);
  }
}

class _BlockedCard extends StatelessWidget {
  const _BlockedCard({required this.title, required this.message});

  final String title;
  final String message;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(spacingLG),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(title, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: spacingSM),
            Text(message),
          ],
        ),
      ),
    );
  }
}
