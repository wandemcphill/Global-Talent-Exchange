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
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(spacingLG),
                      child: Wrap(
                        spacing: spacingSM,
                        runSpacing: spacingSM,
                        children: <Widget>[
                          _MetricChip(
                            label: 'Federations',
                            value: '${data.federations.length}',
                          ),
                          _MetricChip(
                            label: 'Ranked',
                            value: '${data.rankings.length}',
                          ),
                          _MetricChip(
                            label: 'Regions',
                            value: '${data.regionalTournaments.length}',
                          ),
                          _MetricChip(
                            label: 'Public',
                            value:
                                '${data.federations.where((FederationRecord item) => item.isPublic).length}',
                          ),
                        ],
                      ),
                    ),
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
                                    (RegionalTournamentRecord item) => ListTile(
                                      contentPadding: EdgeInsets.zero,
                                      title: Text(item.regionLabel),
                                      subtitle: Text(
                                        '${item.federationCount} federations | ${item.activeLeagueCount} active leagues | ${item.totalMemberClubs} member clubs',
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
                                    (FederationRankingRecord item) => ListTile(
                                      contentPadding: EdgeInsets.zero,
                                      title: Text(item.name),
                                      subtitle: Text(
                                        'Rank ${item.rankingScore.toStringAsFixed(1)} | Reputation ${item.reputationScore.toStringAsFixed(1)} | Audience ${_compactNumber(item.audienceSize)}',
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
                                    (FederationRecord federation) => ListTile(
                                      contentPadding: EdgeInsets.zero,
                                      title: Text(federation.name),
                                      subtitle: Text(
                                        'Rank ${federation.rankingScore.toStringAsFixed(1)} | Members ${federation.memberCount} | Treasury ${_coin(federation.treasuryBalance)}',
                                      ),
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
                                  )
                                  .toList(growable: false),
                            ),
                  ),
                ],
              ),
          loading:
              () => const Center(
                child: Padding(
                  padding: EdgeInsets.all(spacingLG),
                  child: CircularProgressIndicator(),
                ),
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
    final federationContext = ref.watch(
      federationContextProvider,
    );
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
            final List<JsonMap> sanctions = jsonMapList(
              detail.governance['sanctions'],
              label: 'federation sanctions',
            );
            final clubContext = ref.watch(clubContextProvider);
            final bool canRequestMembership = clubContext != null;
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
                              label: 'Ranking',
                              value: detail.federation.rankingScore
                                  .toStringAsFixed(1),
                            ),
                            _MetricChip(
                              label: 'Reputation',
                              value: detail.federation.reputationScore
                                  .toStringAsFixed(1),
                            ),
                            _MetricChip(
                              label: 'Audience',
                              value: _compactNumber(
                                detail.federation.audienceSize,
                              ),
                            ),
                            _MetricChip(
                              label: 'Members',
                              value: '${detail.federation.memberCount}',
                            ),
                            _MetricChip(
                              label: 'Treasury',
                              value: _coin(detail.federation.treasuryBalance),
                            ),
                            _MetricChip(
                              label: 'Reality mode',
                              value: detail.federation.defaultRealityMode,
                            ),
                          ],
                        ),
                        const SizedBox(height: spacingMD),
                        Wrap(
                          spacing: spacingSM,
                          runSpacing: spacingSM,
                          children: <Widget>[
                            FilledButton(
                              onPressed:
                                  canRequestMembership
                                      ? () => _requestMembership(
                                        detail,
                                        clubContext.id,
                                      )
                                      : null,
                              child: Text(
                                canRequestMembership
                                    ? 'Request membership'
                                    : 'Club context required',
                              ),
                            ),
                            if (federationContext?.id == widget.federationId)
                              const Chip(label: Text('Session federation')),
                          ],
                        ),
                        if (!canRequestMembership) ...<Widget>[
                          const SizedBox(height: spacingSM),
                          const Text(
                            'Membership requests require an authenticated session with a verified club context.',
                          ),
                        ],
                      ],
                    ),
                  ),
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
                                  (JsonMap league) => ListTile(
                                    contentPadding: EdgeInsets.zero,
                                    title: Text(
                                      stringValue(
                                        league['name'],
                                        fallback: 'League',
                                      ),
                                    ),
                                    subtitle: Text(
                                      '${stringValue(league['competition_type'], fallback: 'league')} | ${stringValue(league['status'], fallback: 'draft')} | ${stringValue(league['season_label'], fallback: 'season pending')}',
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
                  child: Column(
                    children: <Widget>[
                      if (proposals.isEmpty)
                        const _EmptyState(
                          message: 'No live proposals returned yet.',
                        )
                      else
                        ...proposals.map(
                          (JsonMap proposal) => ListTile(
                            contentPadding: EdgeInsets.zero,
                            title: Text(
                              stringValue(
                                proposal['title'],
                                fallback: 'Proposal',
                              ),
                            ),
                            subtitle: Text(
                              '${stringValue(proposal['status'], fallback: 'open')} | yes ${intValue(proposal['yes_votes'])} | no ${intValue(proposal['no_votes'])} | abstain ${intValue(proposal['abstain_votes'])}',
                            ),
                          ),
                        ),
                      if (sanctions.isNotEmpty) ...<Widget>[
                        const SizedBox(height: spacingMD),
                        Text(
                          'Sanctions',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: spacingSM),
                        ...sanctions.map(
                          (JsonMap sanction) => ListTile(
                            contentPadding: EdgeInsets.zero,
                            title: Text(
                              stringValue(
                                sanction['sanction_type'],
                                fallback: 'Sanction',
                              ),
                            ),
                            subtitle: Text(
                              stringValue(
                                sanction['reason'],
                                fallback: 'No reason provided.',
                              ),
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
                                  (JsonMap narrative) => ListTile(
                                    contentPadding: EdgeInsets.zero,
                                    title: Text(
                                      stringValue(
                                        narrative['headline'],
                                        fallback: 'Narrative',
                                      ),
                                    ),
                                    subtitle: Text(
                                      stringValue(
                                        narrative['body'],
                                        fallback: 'No narrative body.',
                                      ),
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
                                  (MapEntry<String, Object?> entry) => Chip(
                                    label: Text('${entry.key}: ${entry.value}'),
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
                            (MapEntry<String, Object?> entry) => Chip(
                              label: Text('${entry.key}: ${entry.value}'),
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
                title: 'Federation detail is blocked',
                message: AppFeedback.messageFor(error),
              ),
        ),
      ],
    );
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
