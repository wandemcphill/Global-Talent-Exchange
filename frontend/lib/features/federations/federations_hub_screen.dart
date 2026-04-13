import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/app_feedback.dart';
import '../../core/constants/app_spacing.dart';
import '../../navigation/app_destinations.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/providers/auth_provider.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';
import '../../shared/widgets/gtex_premium_panels.dart';
import '../../widgets/gte_state_panel.dart';
import '../shared/data/feature_telemetry.dart';
import '../shared/data/gte_feature_support.dart';
import 'live_federations_provider.dart';

class FederationsHubScreen extends ConsumerStatefulWidget {
  const FederationsHubScreen({super.key});

  @override
  ConsumerState<FederationsHubScreen> createState() =>
      _FederationsHubScreenState();
}

class _FederationsHubScreenState extends ConsumerState<FederationsHubScreen> {
  @override
  void initState() {
    super.initState();
    trackFeatureEvent(
      topic: 'federations',
      name: 'federations_hub_viewed',
      dedupeKey: 'federations-hub-view',
    );
  }

  @override
  Widget build(BuildContext context) {
    final AsyncValue<FederationHubData> value = ref.watch(
      federationsHubProvider,
    );
    return AppPageLayout(
      title: 'Federations',
      subtitle:
          'Listings, rankings, governance context, and membership requests are now wired to the live federation backend.',
      trailing: DataSourceBadge(
        status:
            value.hasError ? DataSourceStatus.blocked : DataSourceStatus.live,
      ),
      children: <Widget>[
        value.when(
          data:
              (FederationHubData data) => Column(
                children: <Widget>[
                  GtexHeroPanel(
                    eyebrow: 'FEDERATION NETWORK',
                    title: 'Regional governance command',
                    description:
                        'Live rankings, treasury scale, public access, and tournament coverage across the federation ecosystem.',
                    metrics: <Widget>[
                      GtexStatTile(
                        label: 'Federations',
                        value: '${data.federations.length}',
                        tone: GtexSurfaceTone.live,
                      ),
                      GtexStatTile(
                        label: 'Ranked',
                        value: '${data.rankings.length}',
                        tone: GtexSurfaceTone.info,
                      ),
                      GtexStatTile(
                        label: 'Regions',
                        value: '${data.regionalTournaments.length}',
                        tone: GtexSurfaceTone.warning,
                      ),
                      GtexStatTile(
                        label: 'Public',
                        value:
                            '${data.federations.where((FederationRecord item) => item.isPublic).length}',
                        tone: GtexSurfaceTone.success,
                      ),
                    ],
                  ),
                  const SizedBox(height: spacingMD),
                  _SectionCard(
                    title: 'Regional tournaments',
                    subtitle:
                        'Live rollup of federation-backed regional tournament structures.',
                    child:
                        data.regionalTournaments.isEmpty
                            ? const _EmptyState(
                              message:
                                  'No regional federation tournaments yet.',
                            )
                            : Column(
                              children: data.regionalTournaments
                                  .map(
                                    (RegionalTournamentRecord item) => Padding(
                                      padding: const EdgeInsets.only(
                                        bottom: spacingSM,
                                      ),
                                      child: GtexListTile(
                                        title: item.regionLabel,
                                        subtitle:
                                            '${item.federationCount} federations | ${item.activeLeagueCount} active leagues | ${item.totalMemberClubs} member clubs',
                                        leadingIcon: Icons.public_rounded,
                                        tone: GtexSurfaceTone.info,
                                      ),
                                    ),
                                  )
                                  .toList(growable: false),
                            ),
                  ),
                  const SizedBox(height: spacingMD),
                  _SectionCard(
                    title: 'Global rankings',
                    subtitle:
                        'Live ranking table from `/federations/rankings`.',
                    child:
                        data.rankings.isEmpty
                            ? const _EmptyState(
                              message:
                                  'Ranking data has not been produced yet.',
                            )
                            : Column(
                              children: data.rankings
                                  .take(10)
                                  .map(
                                    (FederationRankingRecord item) => Padding(
                                      padding: const EdgeInsets.only(
                                        bottom: spacingSM,
                                      ),
                                      child: GtexListTile(
                                        title: item.name,
                                        subtitle:
                                            'Rank ${item.rankingScore.toStringAsFixed(1)} | Reputation ${item.reputationScore.toStringAsFixed(1)} | Audience ${_compactNumber(item.audienceSize)}',
                                        leadingIcon: Icons.leaderboard_rounded,
                                        tone: GtexSurfaceTone.success,
                                        trailing: GtexPill(
                                          label:
                                              'Score ${item.rankingScore.toStringAsFixed(1)}',
                                          tone: GtexSurfaceTone.live,
                                        ),
                                      ),
                                    ),
                                  )
                                  .toList(growable: false),
                            ),
                  ),
                  const SizedBox(height: spacingMD),
                  _SectionCard(
                    title: 'All federations',
                    subtitle:
                        'Every row opens a live federation detail route with governance and membership actions.',
                    child:
                        data.federations.isEmpty
                            ? const _EmptyState(
                              message: 'No federations are available yet.',
                            )
                            : Column(
                              children: data.federations
                                  .map(
                                    (FederationRecord federation) => Padding(
                                      padding: const EdgeInsets.only(
                                        bottom: spacingSM,
                                      ),
                                      child: GtexListTile(
                                        title: federation.name,
                                        subtitle:
                                            'Rank ${federation.rankingScore.toStringAsFixed(1)} | Members ${federation.memberCount} | Treasury ${_coin(federation.treasuryBalance)}',
                                        leadingIcon:
                                            Icons.account_balance_rounded,
                                        tone:
                                            federation.isPublic
                                                ? GtexSurfaceTone.live
                                                : GtexSurfaceTone.warning,
                                        trailing: FilledButton(
                                          onPressed:
                                              () => context.push(
                                                AppRoutes.federationDetailLocation(
                                                  federation.id,
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
                ],
              ),
          loading:
              () => const GteStatePanel(
                title: 'Loading federations',
                message:
                    'Syncing live federation rankings, regional tournaments, and governance context.',
                isLoading: true,
              ),
          error:
              (Object error, StackTrace stackTrace) => _BlockedCard(
                title: 'Federations are blocked',
                message: AppFeedback.messageFor(error),
              ),
        ),
      ],
    );
  }
}

class FederationDetailScreen extends ConsumerStatefulWidget {
  const FederationDetailScreen({super.key, required this.federationId});

  final String federationId;

  @override
  ConsumerState<FederationDetailScreen> createState() =>
      _FederationDetailScreenState();
}

class _FederationDetailScreenState
    extends ConsumerState<FederationDetailScreen> {
  @override
  void initState() {
    super.initState();
    trackFeatureEvent(
      topic: 'federations',
      name: 'federation_detail_viewed',
      payload: <String, Object?>{'federation_id': widget.federationId},
      dedupeKey: 'federation-detail-${widget.federationId}',
    );
  }

  @override
  Widget build(BuildContext context) {
    final AsyncValue<FederationDetailData> value = ref.watch(
      federationDetailProvider(widget.federationId),
    );
    final federationContext = ref.watch(federationContextProvider);
    return AppPageLayout(
      title: value.maybeWhen(
        data: (FederationDetailData data) => data.federation.name,
        orElse: () => 'Federation detail',
      ),
      subtitle:
          federationContext?.id == widget.federationId
              ? 'This session is already linked to this federation.'
              : 'Live federation dashboard, governance detail, and membership workflow.',
      trailing: DataSourceBadge(
        status:
            value.hasError ? DataSourceStatus.blocked : DataSourceStatus.live,
      ),
      children: <Widget>[
        value.when(
          data: (FederationDetailData detail) {
            final JsonMap reputation = jsonMap(
              detail.dashboard['reputation'],
              label: 'federation reputation',
              fallback: const <String, Object?>{},
            );
            final JsonMap rules = jsonMap(
              detail.dashboard['rules'],
              label: 'federation rules',
              fallback: const <String, Object?>{},
            );
            final List<JsonMap> leagues = jsonMapList(
              detail.dashboard['leagues'],
              label: 'federation leagues',
            );
            final List<JsonMap> proposals = jsonMapList(
              detail.governance['proposals'],
              label: 'federation proposals',
            );
            final List<JsonMap> votes = jsonMapList(
              detail.governance['votes'],
              label: 'federation votes',
            );
            final List<JsonMap> sanctions = jsonMapList(
              detail.governance['sanctions'],
              label: 'federation sanctions',
            );
            final clubContext = ref.watch(clubContextProvider);
            final String? currentUserId = ref.watch(currentUserIdProvider);
            final bool isAdmin =
                ref.watch(isAdminProvider) || ref.watch(isSuperAdminProvider);
            final List<JsonMap> members = jsonMapList(
              detail.dashboard['members'],
              label: 'federation members',
            );
            final bool canRequestMembership = clubContext != null;
            final bool hasActiveClubMembership =
                clubContext != null &&
                members.any(
                  (JsonMap member) =>
                      stringValue(member['club_id']) == clubContext.id &&
                      stringValue(member['status'], fallback: 'pending') ==
                          'active',
                );
            final bool canParticipateInGovernance =
                currentUserId != null &&
                (isAdmin ||
                    federationContext?.id == widget.federationId ||
                    hasActiveClubMembership);
            return Column(
              children: <Widget>[
                GtexHeroPanel(
                  eyebrow: 'FEDERATION DETAIL',
                  title: detail.federation.name,
                  description:
                      federationContext?.id == widget.federationId
                          ? 'This session is already linked to this federation.'
                          : 'Live federation dashboard, governance detail, and membership workflow.',
                  metrics: <Widget>[
                    GtexStatTile(
                      label: 'Ranking',
                      value: detail.federation.rankingScore.toStringAsFixed(1),
                      tone: GtexSurfaceTone.live,
                    ),
                    GtexStatTile(
                      label: 'Reputation',
                      value: detail.federation.reputationScore.toStringAsFixed(
                        1,
                      ),
                      tone: GtexSurfaceTone.info,
                    ),
                    GtexStatTile(
                      label: 'Audience',
                      value: _compactNumber(detail.federation.audienceSize),
                      tone: GtexSurfaceTone.success,
                    ),
                    GtexStatTile(
                      label: 'Members',
                      value: '${detail.federation.memberCount}',
                      tone: GtexSurfaceTone.warning,
                    ),
                    GtexStatTile(
                      label: 'Treasury',
                      value: _coin(detail.federation.treasuryBalance),
                      tone: GtexSurfaceTone.warning,
                    ),
                    GtexStatTile(
                      label: 'Reality mode',
                      value: detail.federation.defaultRealityMode,
                      tone: GtexSurfaceTone.info,
                    ),
                  ],
                  actions: <Widget>[
                    FilledButton(
                      onPressed:
                          canRequestMembership
                              ? () => _requestMembership(detail, clubContext.id)
                              : null,
                      child: Text(
                        canRequestMembership
                            ? 'Request membership'
                            : 'Club context required',
                      ),
                    ),
                    if (federationContext?.id == widget.federationId)
                      const GtexPill(
                        label: 'Session federation',
                        tone: GtexSurfaceTone.success,
                      ),
                    if (!canRequestMembership)
                      const GtexPill(
                        label: 'Verified club context required',
                        tone: GtexSurfaceTone.warning,
                      ),
                  ],
                ),
                const SizedBox(height: spacingMD),
                _SectionCard(
                  title: 'Leagues',
                  subtitle: 'Live federation dashboard output.',
                  child:
                      leagues.isEmpty
                          ? const _EmptyState(
                            message: 'No federation leagues returned yet.',
                          )
                          : Column(
                            children: leagues
                                .map(
                                  (JsonMap league) => Padding(
                                    padding: const EdgeInsets.only(
                                      bottom: spacingSM,
                                    ),
                                    child: GtexListTile(
                                      title: stringValue(
                                        league['name'],
                                        fallback: 'League',
                                      ),
                                      subtitle:
                                          '${stringValue(league['competition_type'], fallback: 'league')} | ${stringValue(league['status'], fallback: 'draft')} | ${stringValue(league['season_label'], fallback: 'season pending')}',
                                      leadingIcon: Icons.shield_outlined,
                                      tone: GtexSurfaceTone.info,
                                    ),
                                  ),
                                )
                                .toList(growable: false),
                          ),
                ),
                const SizedBox(height: spacingMD),
                _SectionCard(
                  title: 'Governance',
                  subtitle:
                      'Live proposals and sanctions from federation governance.',
                  trailing: FilledButton.tonal(
                    onPressed:
                        canParticipateInGovernance
                            ? () => _openProposalComposer(detail)
                            : null,
                    child: Text(
                      canParticipateInGovernance
                          ? 'Create proposal'
                          : 'Access required',
                    ),
                  ),
                  child: Column(
                    children: <Widget>[
                      if (!canParticipateInGovernance)
                        const Padding(
                          padding: EdgeInsets.only(bottom: spacingSM),
                          child: _EmptyState(
                            message:
                                'Governance actions unlock once this session has active federation participation.',
                          ),
                        ),
                      if (proposals.isEmpty)
                        const _EmptyState(
                          message: 'No live proposals returned yet.',
                        )
                      else
                        ...proposals.map((JsonMap proposal) {
                          final String proposalId = stringValue(proposal['id']);
                          JsonMap? myVote;
                          if (currentUserId != null) {
                            for (final JsonMap vote in votes) {
                              if (stringValue(vote['proposal_id']) ==
                                      proposalId &&
                                  stringValue(vote['user_id']) ==
                                      currentUserId) {
                                myVote = vote;
                                break;
                              }
                            }
                          }
                          return Padding(
                            padding: const EdgeInsets.only(bottom: spacingSM),
                            child: GtexListTile(
                              title: stringValue(
                                proposal['title'],
                                fallback: 'Proposal',
                              ),
                              subtitle:
                                  '${stringValue(proposal['status'], fallback: 'open')} | yes ${intValue(proposal['yes_votes'])} | no ${intValue(proposal['no_votes'])} | abstain ${intValue(proposal['abstain_votes'])}',
                              leadingIcon: Icons.how_to_vote_rounded,
                              tone: GtexSurfaceTone.warning,
                              trailing:
                                  myVote != null
                                      ? GtexPill(
                                        label:
                                            'Voted ${stringValue(myVote['vote_type'], fallback: 'recorded').toUpperCase()}',
                                        tone: GtexSurfaceTone.success,
                                      )
                                      : canParticipateInGovernance &&
                                          stringValue(
                                                proposal['status'],
                                                fallback: 'open',
                                              ) ==
                                              'open'
                                      ? FilledButton.tonal(
                                        onPressed:
                                            () => _openVoteSheet(proposal),
                                        child: const Text('Vote'),
                                      )
                                      : null,
                            ),
                          );
                        }),
                      if (sanctions.isNotEmpty) ...<Widget>[
                        const SizedBox(height: spacingMD),
                        Text(
                          'Sanctions',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: spacingSM),
                        ...sanctions.map(
                          (JsonMap sanction) => Padding(
                            padding: const EdgeInsets.only(bottom: spacingSM),
                            child: GtexListTile(
                              title: stringValue(
                                sanction['sanction_type'],
                                fallback: 'Sanction',
                              ),
                              subtitle: stringValue(
                                sanction['reason'],
                                fallback: 'No reason provided.',
                              ),
                              leadingIcon: Icons.gavel_rounded,
                              tone: GtexSurfaceTone.danger,
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                const SizedBox(height: spacingMD),
                _SectionCard(
                  title: 'Narratives',
                  subtitle:
                      'Live storyline generation for this federation ecosystem.',
                  child:
                      detail.narratives.isEmpty
                          ? const _EmptyState(
                            message: 'No narrative snapshots returned yet.',
                          )
                          : Column(
                            children: detail.narratives
                                .map(
                                  (JsonMap narrative) => Padding(
                                    padding: const EdgeInsets.only(
                                      bottom: spacingSM,
                                    ),
                                    child: GtexListTile(
                                      title: stringValue(
                                        narrative['headline'],
                                        fallback: 'Narrative',
                                      ),
                                      subtitle: stringValue(
                                        narrative['body'],
                                        fallback: 'No narrative body.',
                                      ),
                                      leadingIcon: Icons.auto_stories_rounded,
                                      tone: GtexSurfaceTone.info,
                                    ),
                                  ),
                                )
                                .toList(growable: false),
                          ),
                ),
                const SizedBox(height: spacingMD),
                _SectionCard(
                  title: 'Rules snapshot',
                  subtitle:
                      'Compact federation rule inventory from the live dashboard.',
                  child:
                      rules.isEmpty
                          ? const _EmptyState(
                            message: 'No rule payload returned yet.',
                          )
                          : Wrap(
                            spacing: spacingSM,
                            runSpacing: spacingSM,
                            children: rules.entries
                                .take(10)
                                .map(
                                  (MapEntry<String, Object?> entry) => GtexPill(
                                    label: '${entry.key}: ${entry.value}',
                                    tone: GtexSurfaceTone.info,
                                  ),
                                )
                                .toList(growable: false),
                          ),
                ),
                if (reputation.isNotEmpty) ...<Widget>[
                  const SizedBox(height: spacingMD),
                  _SectionCard(
                    title: 'Reputation snapshot',
                    subtitle:
                        'The same federation detail route also exposes live reputation metrics.',
                    child: Wrap(
                      spacing: spacingSM,
                      runSpacing: spacingSM,
                      children: reputation.entries
                          .map(
                            (MapEntry<String, Object?> entry) => GtexPill(
                              label: '${entry.key}: ${entry.value}',
                              tone: GtexSurfaceTone.success,
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
                title: 'Loading federation detail',
                message:
                    'Syncing governance, leagues, narratives, and rules from the live federation endpoints.',
                isLoading: true,
              ),
          error:
              (Object error, StackTrace stackTrace) => _BlockedCard(
                title: 'Federation detail is blocked',
                message: AppFeedback.messageFor(error),
              ),
        ),
      ],
    );
  }

  Future<void> _openProposalComposer(FederationDetailData detail) async {
    final GlobalKey<FormState> formKey = GlobalKey<FormState>();
    final TextEditingController titleController = TextEditingController();
    final TextEditingController summaryController = TextEditingController();
    String proposalType = 'rule_change';
    bool submitting = false;
    String? inlineError;

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (BuildContext sheetContext) {
        return StatefulBuilder(
          builder: (
            BuildContext context,
            void Function(void Function()) setState,
          ) {
            final double bottomInset = MediaQuery.of(context).viewInsets.bottom;
            return Padding(
              padding: EdgeInsets.fromLTRB(20, 20, 20, bottomInset + 20),
              child: Form(
                key: formKey,
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Create proposal',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Submit a live federation governance proposal.',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      if (inlineError != null) ...<Widget>[
                        const SizedBox(height: spacingSM),
                        Text(
                          inlineError!,
                          style: Theme.of(
                            context,
                          ).textTheme.bodyMedium?.copyWith(
                            color: Theme.of(context).colorScheme.error,
                          ),
                        ),
                      ],
                      const SizedBox(height: spacingMD),
                      DropdownButtonFormField<String>(
                        value: proposalType,
                        items: const <DropdownMenuItem<String>>[
                          DropdownMenuItem<String>(
                            value: 'rule_change',
                            child: Text('Rule change'),
                          ),
                          DropdownMenuItem<String>(
                            value: 'schedule_change',
                            child: Text('Schedule change'),
                          ),
                          DropdownMenuItem<String>(
                            value: 'competition_change',
                            child: Text('Competition change'),
                          ),
                        ],
                        onChanged:
                            submitting
                                ? null
                                : (String? value) {
                                  if (value == null) {
                                    return;
                                  }
                                  setState(() {
                                    proposalType = value;
                                  });
                                },
                        decoration: const InputDecoration(
                          labelText: 'Proposal type',
                        ),
                      ),
                      const SizedBox(height: spacingSM),
                      TextFormField(
                        controller: titleController,
                        decoration: const InputDecoration(labelText: 'Title'),
                        validator: (String? value) {
                          final String trimmed = value?.trim() ?? '';
                          if (trimmed.length < 4) {
                            return 'Enter a proposal title.';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: spacingSM),
                      TextFormField(
                        controller: summaryController,
                        decoration: const InputDecoration(labelText: 'Summary'),
                        minLines: 3,
                        maxLines: 6,
                        validator: (String? value) {
                          final String trimmed = value?.trim() ?? '';
                          if (trimmed.length < 10) {
                            return 'Enter a summary with enough detail.';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: spacingMD),
                      Row(
                        children: <Widget>[
                          Expanded(
                            child: OutlinedButton(
                              onPressed:
                                  submitting
                                      ? null
                                      : () => Navigator.of(sheetContext).pop(),
                              child: const Text('Cancel'),
                            ),
                          ),
                          const SizedBox(width: spacingSM),
                          Expanded(
                            child: FilledButton(
                              onPressed:
                                  submitting
                                      ? null
                                      : () async {
                                        if (!formKey.currentState!.validate()) {
                                          return;
                                        }
                                        setState(() {
                                          submitting = true;
                                          inlineError = null;
                                        });
                                        try {
                                          final FederationProposalActionResult
                                          result = await ref
                                              .read(federationsApiProvider)
                                              .createProposal(
                                                federationId:
                                                    widget.federationId,
                                                title:
                                                    titleController.text.trim(),
                                                summary:
                                                    summaryController.text
                                                        .trim(),
                                                proposalType: proposalType,
                                              );
                                          ref.invalidate(
                                            federationDetailProvider(
                                              widget.federationId,
                                            ),
                                          );
                                          if (sheetContext.mounted) {
                                            Navigator.of(sheetContext).pop();
                                          }
                                          if (!mounted) {
                                            return;
                                          }
                                          trackFeatureEvent(
                                            topic: 'federations',
                                            name: 'federation_proposal_created',
                                            payload: <String, Object?>{
                                              'federation_id':
                                                  widget.federationId,
                                              'proposal_id': result.id,
                                              'proposal_type': proposalType,
                                            },
                                          );
                                          AppFeedback.showSuccess(
                                            this.context,
                                            '${detail.federation.name} proposal "${result.title}" is now ${result.status}.',
                                          );
                                        } catch (error) {
                                          setState(() {
                                            inlineError =
                                                AppFeedback.messageFor(error);
                                          });
                                        } finally {
                                          if (sheetContext.mounted) {
                                            setState(() {
                                              submitting = false;
                                            });
                                          }
                                        }
                                      },
                              child: const Text('Submit'),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        );
      },
    );
  }

  Future<void> _openVoteSheet(JsonMap proposal) async {
    final String title = stringValue(proposal['title'], fallback: 'Proposal');
    final String summary = stringValue(
      proposal['summary'],
      fallback: 'No proposal summary provided.',
    );
    final String proposalId = stringValue(proposal['id']);
    if (proposalId.isEmpty) {
      AppFeedback.showError(
        context,
        const FormatException('Proposal id is missing from the live payload.'),
      );
      return;
    }
    await showModalBottomSheet<void>(
      context: context,
      builder: (BuildContext context) {
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(title, style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: spacingSM),
                Text(summary, style: Theme.of(context).textTheme.bodyMedium),
                const SizedBox(height: spacingMD),
                Wrap(
                  spacing: spacingSM,
                  runSpacing: spacingSM,
                  children: <Widget>[
                    FilledButton(
                      onPressed:
                          () => _castVote(
                            context,
                            proposalId: proposalId,
                            title: title,
                            voteType: 'yes',
                          ),
                      child: const Text('Vote yes'),
                    ),
                    FilledButton.tonal(
                      onPressed:
                          () => _castVote(
                            context,
                            proposalId: proposalId,
                            title: title,
                            voteType: 'no',
                          ),
                      child: const Text('Vote no'),
                    ),
                    OutlinedButton(
                      onPressed:
                          () => _castVote(
                            context,
                            proposalId: proposalId,
                            title: title,
                            voteType: 'abstain',
                          ),
                      child: const Text('Abstain'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Future<void> _castVote(
    BuildContext sheetContext, {
    required String proposalId,
    required String title,
    required String voteType,
  }) async {
    try {
      final FederationProposalActionResult result = await ref
          .read(federationsApiProvider)
          .castProposalVote(proposalId: proposalId, voteType: voteType);
      ref.invalidate(federationDetailProvider(widget.federationId));
      if (sheetContext.mounted) {
        Navigator.of(sheetContext).pop();
      }
      if (!mounted) {
        return;
      }
      trackFeatureEvent(
        topic: 'federations',
        name: 'federation_vote_cast',
        payload: <String, Object?>{
          'federation_id': widget.federationId,
          'proposal_id': proposalId,
          'vote_type': voteType,
        },
      );
      AppFeedback.showSuccess(
        context,
        'Vote ${result.voteType ?? voteType} recorded for "$title".',
      );
    } catch (error) {
      if (!mounted) {
        return;
      }
      AppFeedback.showError(context, error);
    }
  }

  Future<void> _requestMembership(
    FederationDetailData detail,
    String clubId,
  ) async {
    try {
      final FederationMembershipResult result = await ref
          .read(federationsApiProvider)
          .createMembership(
            federationId: widget.federationId,
            clubId: clubId,
            userId: ref.read(currentUserIdProvider),
          );
      trackFeatureEvent(
        topic: 'federations',
        name: 'federation_membership_requested',
        payload: <String, Object?>{
          'federation_id': widget.federationId,
          'club_id': clubId,
          'status': result.status,
        },
      );
      ref.invalidate(federationsHubProvider);
      ref.invalidate(federationDetailProvider(widget.federationId));
      if (!mounted) {
        return;
      }
      final String suffix =
          result.violations.isEmpty
              ? result.status
              : '${result.status} with ${result.violations.length} requirement note(s)';
      AppFeedback.showSuccess(
        context,
        '${detail.federation.name} membership request recorded as $suffix.',
      );
    } catch (error) {
      if (!mounted) {
        return;
      }
      AppFeedback.showError(context, error);
    }
  }
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({
    required this.title,
    required this.subtitle,
    required this.child,
    this.trailing,
  });

  final String title;
  final String subtitle;
  final Widget child;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return GtexSectionPanel(
      title: title,
      subtitle: subtitle,
      trailing: trailing,
      child: child,
    );
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
      title: title,
      message: message,
      icon: Icons.error_outline_rounded,
    );
  }
}

String _compactNumber(num value) {
  if (value >= 1000000) {
    return '${(value / 1000000).toStringAsFixed(1)}M';
  }
  if (value >= 1000) {
    return '${(value / 1000).toStringAsFixed(1)}K';
  }
  return value.toString();
}

String _coin(double value) => value.toStringAsFixed(0);
