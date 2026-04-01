import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/app_feedback.dart';
import '../../core/constants/app_spacing.dart';
import '../../navigation/app_destinations.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/widgets/gtex_action_surface.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';
import '../../shared/widgets/gtex_premium_panels.dart';
import '../../widgets/gte_state_panel.dart';
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
                GtexHeroPanel(
                  eyebrow: 'COUNTRY PROGRAMS',
                  title: 'National team operations board',
                  description:
                      'Live competitions, ranking ladders, and authenticated draft-squad history from the national-team engine.',
                  metrics: <Widget>[
                    _MetricChip(
                      label: 'Competitions',
                      value: '${data.competitions.length}',
                      tone: GtexSurfaceTone.live,
                    ),
                    _MetricChip(
                      label: 'Rankings',
                      value: '${data.rankings.length}',
                      tone: GtexSurfaceTone.info,
                    ),
                    _MetricChip(
                      label: 'My entries',
                      value: '${managedEntries.length}',
                      tone: GtexSurfaceTone.success,
                    ),
                  ],
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
                                  (competition) => Padding(
                                    padding: const EdgeInsets.only(
                                      bottom: spacingSM,
                                    ),
                                    child: GtexListTile(
                                      title: competition.title,
                                      subtitle:
                                          '${competition.seasonLabel} | ${competition.regionType} | ${competition.status}',
                                      leadingIcon: Icons.flag_circle_rounded,
                                      tone: GtexSurfaceTone.live,
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
                                  ) => Padding(
                                    padding: const EdgeInsets.only(
                                      bottom: spacingSM,
                                    ),
                                    child: GtexListTile(
                                      title: item.countryName,
                                      subtitle:
                                          'ELO ${item.eloRating.toStringAsFixed(1)} | W ${item.wins} D ${item.draws} L ${item.losses} | Titles ${item.titles}',
                                      leadingIcon: Icons.emoji_events_rounded,
                                      tone: GtexSurfaceTone.info,
                                    ),
                                  ),
                                )
                                .toList(growable: false),
                          ),
                ),
                const SizedBox(height: spacingMD),
                _SectionCard(
                  title: 'U17 national regen pool',
                  subtitle:
                      'Live `/regen-universe/national-regens` feed filtered to the 14-17 preseeded batch.',
                  child:
                      data.nationalRegens.isEmpty
                          ? const _EmptyState(
                            message:
                                'No preseeded 14-17 national regens are published yet.',
                          )
                          : Column(
                            children: data.nationalRegens
                                .take(12)
                                .map(
                                  (JsonMap item) => Padding(
                                    padding: const EdgeInsets.only(
                                      bottom: spacingSM,
                                    ),
                                    child: GtexListTile(
                                      title: stringValue(
                                        item['display_name'],
                                        fallback: 'National regen',
                                      ),
                                      subtitle:
                                          '${stringValue(item['country_name'])} | ${stringValue(item['primary_position'])} | Age ${intValue(item['age'])} | OVR ${intValue(item['current_rating'])} | POT ${intValue(item['potential_rating'])} | ${stringValue(item['rarity_tier']).toUpperCase()}',
                                      leadingIcon:
                                          Icons.workspace_premium_rounded,
                                      tone: GtexSurfaceTone.warning,
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
                            (dynamic entry) => Padding(
                              padding: const EdgeInsets.only(bottom: spacingSM),
                              child: GtexListTile(
                                title: entry.countryName as String,
                                subtitle:
                                    '${entry.competitionId} | Squad ${entry.squadSize}',
                                leadingIcon: Icons.history_rounded,
                                tone: GtexSurfaceTone.success,
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
              () => const GteStatePanel(
                eyebrow: 'NATIONAL TEAMS',
                title: 'Loading country competitions',
                message:
                    'Resolving the live competition index, ranking ladder, and authenticated federation history.',
                icon: Icons.public_rounded,
                isLoading: true,
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
                GtexHeroPanel(
                  eyebrow: 'COMPETITION DETAIL',
                  title: 'Country squad command',
                  description:
                      'Lifecycle stage, tournament framing, and draft-squad controls for this live national-team competition.',
                  metrics: <Widget>[
                    _MetricChip(
                      label: 'Season',
                      value: detail.competition.seasonLabel,
                      tone: GtexSurfaceTone.live,
                    ),
                    _MetricChip(
                      label: 'Region',
                      value: detail.competition.regionType,
                      tone: GtexSurfaceTone.info,
                    ),
                    _MetricChip(
                      label: 'Age band',
                      value: detail.competition.ageBand,
                      tone: GtexSurfaceTone.warning,
                    ),
                    _MetricChip(
                      label: 'Format',
                      value: detail.competition.formatType,
                      tone: GtexSurfaceTone.success,
                    ),
                    _MetricChip(
                      label: 'Lifecycle',
                      value: stringValue(
                        detail.lifecycle['current_stage'],
                        fallback: detail.competition.status,
                      ),
                      tone: GtexSurfaceTone.neutral,
                    ),
                  ],
                  actions: <Widget>[
                    FilledButton(
                      onPressed: () => _runAutoBuild(context),
                      child: const Text('Build draft squad'),
                    ),
                  ],
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
                            (dynamic entry) => Padding(
                              padding: const EdgeInsets.only(bottom: spacingSM),
                              child: GtexListTile(
                                title: entry.countryName as String,
                                subtitle:
                                    'Squad ${entry.squadSize} | Updated ${entry.updatedAt}',
                                leadingIcon: Icons.groups_rounded,
                                tone: GtexSurfaceTone.success,
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
                                  (JsonMap item) => Padding(
                                    padding: const EdgeInsets.only(
                                      bottom: spacingSM,
                                    ),
                                    child: GtexListTile(
                                      title: stringValue(
                                        item['stage'],
                                        fallback: 'Stage',
                                      ),
                                      subtitle: stringValue(
                                        item['summary'],
                                        fallback: 'No summary available.',
                                      ),
                                      leadingIcon: Icons.timeline_rounded,
                                      tone: GtexSurfaceTone.info,
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
                        GtexPill(
                          label:
                              'Theme ${stringValue(activeTheme['visual_style'], fallback: 'default')}',
                          icon: Icons.palette_rounded,
                          tone: GtexSurfaceTone.warning,
                        ),
                      if (activeAds.isNotEmpty) ...<Widget>[
                        const SizedBox(height: spacingSM),
                        Text(
                          'Active ads',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: spacingSM),
                        ...activeAds.map(
                          (JsonMap ad) => Padding(
                            padding: const EdgeInsets.only(bottom: spacingSM),
                            child: GtexListTile(
                              title: stringValue(
                                ad['placement'],
                                fallback: 'Ad',
                              ),
                              subtitle: stringValue(
                                ad['asset_url'],
                                fallback: 'Asset unavailable.',
                              ),
                              leadingIcon: Icons.campaign_rounded,
                              tone: GtexSurfaceTone.warning,
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
                          (JsonMap story) => Padding(
                            padding: const EdgeInsets.only(bottom: spacingSM),
                            child: GtexListTile(
                              title: stringValue(
                                story['type'],
                                fallback: 'Story',
                              ),
                              subtitle: stringValue(
                                story['narrative_text'],
                                fallback: 'No narrative text.',
                              ),
                              leadingIcon: Icons.auto_stories_rounded,
                              tone: GtexSurfaceTone.live,
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
              () => const GteStatePanel(
                eyebrow: 'NATIONAL TEAMS',
                title: 'Loading competition detail',
                message:
                    'Syncing lifecycle structure, submitted entries, and presentation metadata for this tournament.',
                icon: Icons.emoji_events_rounded,
                isLoading: true,
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
    final Listenable formListenable = Listenable.merge(<Listenable>[
      countryController,
      budgetController,
      tacticController,
    ]);
    try {
      final bool? confirmed = await showDialog<bool>(
        context: context,
        builder: (BuildContext context) {
          return AnimatedBuilder(
            animation: formListenable,
            builder: (BuildContext context, Widget? child) {
              final double? budget = double.tryParse(
                budgetController.text.trim(),
              );
              final bool canRun =
                  countryController.text.trim().isNotEmpty &&
                  budget != null &&
                  budget > 0;
              return GtexActionDialog(
                eyebrow: 'NATIONAL TEAMS',
                title: 'Build draft squad',
                description:
                    'Draft a live national-team squad package for this competition using a country code, budget ceiling, and tactical profile.',
                leadingIcon: Icons.flag_circle_rounded,
                content: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: <Widget>[
                    TextField(
                      controller: countryController,
                      textCapitalization: TextCapitalization.characters,
                      decoration: const InputDecoration(
                        labelText: 'Country code',
                        helperText: 'Use the federation country code.',
                      ),
                    ),
                    const SizedBox(height: spacingSM),
                    TextField(
                      controller: budgetController,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        labelText: 'Budget coin',
                        helperText:
                            'Positive coin budget sent to the live builder.',
                      ),
                    ),
                    const SizedBox(height: spacingSM),
                    TextField(
                      controller: tacticController,
                      decoration: const InputDecoration(
                        labelText: 'Tactic',
                        helperText: 'Leave blank to fall back to balanced.',
                      ),
                    ),
                  ],
                ),
                actions: <Widget>[
                  TextButton(
                    onPressed: () => Navigator.of(context).pop(false),
                    child: const Text('Cancel'),
                  ),
                  FilledButton(
                    onPressed:
                        canRun ? () => Navigator.of(context).pop(true) : null,
                    child: const Text('Run'),
                  ),
                ],
              );
            },
          );
        },
      );
      if (confirmed != true) {
        return;
      }
      final String countryCode = countryController.text.trim().toUpperCase();
      final double? budget = double.tryParse(budgetController.text.trim());
      final String resolvedTactic =
          tacticController.text.trim().isEmpty
              ? 'balanced'
              : tacticController.text.trim();
      if (countryCode.isEmpty) {
        if (!mounted) {
          return;
        }
        AppFeedback.showError(
          this.context,
          'Enter a country code before building a squad.',
        );
        return;
      }
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
      final JsonMap result = await ref
          .read(nationalTeamsApiProvider)
          .buildAutoSquad(
            competitionId: widget.competitionId,
            countryCode: countryCode,
            budgetCoin: budget,
            tactic: resolvedTactic,
          );
      trackFeatureEvent(
        topic: 'national_teams',
        name: 'national_team_auto_build_completed',
        payload: <String, Object?>{
          'competition_id': widget.competitionId,
          'country_code': countryCode,
        },
      );
      if (!mounted) {
        return;
      }
      await showModalBottomSheet<void>(
        context: this.context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (BuildContext context) {
          final List<JsonMap> players = jsonMapList(
            result['players'],
            label: 'auto build players',
          );
          return GtexActionSheetFrame(
            eyebrow: 'NATIONAL TEAMS',
            title: 'Draft squad result',
            description:
                'Live squad package returned for $countryCode using the $resolvedTactic build profile.',
            leadingIcon: Icons.groups_rounded,
            content: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: <Widget>[
                Wrap(
                  spacing: spacingSM,
                  runSpacing: spacingSM,
                  children: <Widget>[
                    GtexPill(
                      label: 'Country $countryCode',
                      icon: Icons.flag_rounded,
                      tone: GtexSurfaceTone.live,
                    ),
                    GtexPill(
                      label: 'Tactic $resolvedTactic',
                      icon: Icons.tune_rounded,
                      tone: GtexSurfaceTone.info,
                    ),
                  ],
                ),
                const SizedBox(height: spacingMD),
                Wrap(
                  spacing: spacingSM,
                  runSpacing: spacingSM,
                  children: <Widget>[
                    _MetricChip(
                      label: 'Formation',
                      value: stringValue(result['formation']),
                      tone: GtexSurfaceTone.live,
                    ),
                    _MetricChip(
                      label: 'Selected',
                      value: '${intValue(result['selected_count'])}',
                      tone: GtexSurfaceTone.info,
                    ),
                    _MetricChip(
                      label: 'Budget',
                      value: numberValue(
                        result['requested_budget_coin'],
                      ).toStringAsFixed(0),
                      tone: GtexSurfaceTone.warning,
                    ),
                    _MetricChip(
                      label: 'Remaining',
                      value: numberValue(
                        result['remaining_budget_coin'],
                      ).toStringAsFixed(0),
                      tone: GtexSurfaceTone.success,
                    ),
                  ],
                ),
                const SizedBox(height: spacingMD),
                if (players.isEmpty)
                  const _EmptyState(
                    message: 'No draft squad could be built for that input.',
                  )
                else
                  ...players.map(
                    (JsonMap player) => Padding(
                      padding: const EdgeInsets.only(bottom: spacingSM),
                      child: GtexListTile(
                        title: stringValue(
                          player['player_name'],
                          fallback: 'Player',
                        ),
                        subtitle:
                            '${stringValue(player['assigned_slot'], fallback: 'slot pending')} | ${stringValue(player['primary_position'], fallback: 'position pending')} | ${numberValue(player['loan_price_coin']).toStringAsFixed(0)} coin',
                        leadingIcon: Icons.person_pin_circle_rounded,
                        tone: GtexSurfaceTone.info,
                      ),
                    ),
                  ),
              ],
            ),
            actions: <Widget>[
              OutlinedButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('Close'),
              ),
            ],
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
            (JsonMap item) => Padding(
              padding: const EdgeInsets.only(bottom: spacingSM),
              child: GtexListTile(
                title: stringValue(item['country_name'], fallback: 'Country'),
                subtitle:
                    '${stringValue(item['status'], fallback: 'submitted')} | Strength ${numberValue(item['strength_rating']).toStringAsFixed(1)}',
                leadingIcon: Icons.flag_rounded,
                tone: GtexSurfaceTone.info,
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
    return GtexSectionPanel(title: title, subtitle: subtitle, child: child);
  }
}

class _MetricChip extends StatelessWidget {
  const _MetricChip({
    required this.label,
    required this.value,
    this.tone = GtexSurfaceTone.info,
  });

  final String label;
  final String value;
  final GtexSurfaceTone tone;

  @override
  Widget build(BuildContext context) {
    return GtexStatTile(label: label, value: value, tone: tone);
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return GtexListTile(
      title: 'Nothing live yet',
      subtitle: message,
      leadingIcon: Icons.hourglass_empty_rounded,
      tone: GtexSurfaceTone.neutral,
    );
  }
}

class _BlockedCard extends StatelessWidget {
  const _BlockedCard({required this.title, required this.message});

  final String title;
  final String message;

  @override
  Widget build(BuildContext context) {
    return GteStatePanel(
      eyebrow: 'NATIONAL TEAMS',
      title: title,
      message: message,
      icon: Icons.warning_amber_rounded,
    );
  }
}
