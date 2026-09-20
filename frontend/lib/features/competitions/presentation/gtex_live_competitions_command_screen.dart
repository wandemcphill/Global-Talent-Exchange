import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/competitions/live_competitions_provider.dart';
import 'package:gte_frontend/features/shared/data/gte_feature_support.dart';
import 'package:gte_frontend/features/streamer_tournament_engine/data/streamer_tournament_engine_models.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/hosted_competition_models.dart';
import 'package:gte_frontend/shared/providers/auth_provider.dart';
import 'package:gte_frontend/shared/providers/live_clients_provider.dart';
import 'package:gte_frontend/ui_gtex/components/gtex_command_center.dart';
import 'package:gte_frontend/ui_gtex/components/gtex_competition_command.dart';
import 'package:gte_frontend/ui_gtex/theme/gtex_colors.dart';
import 'package:gte_frontend/ui_gtex/theme/gtex_spacing.dart';
import 'package:gte_frontend/ui_gtex/theme/gtex_typography.dart';

/// The canonical, provider-backed competition hub. It does not merge GTEX,
/// hosted, and creator tournament records because those families have distinct
/// lifecycle and participation contracts.
class GtexLiveCompetitionsCommandScreen extends ConsumerStatefulWidget {
  const GtexLiveCompetitionsCommandScreen({
    super.key,
    required this.isAuthenticated,
    required this.onOpenLogin,
  });

  final bool isAuthenticated;
  final VoidCallback onOpenLogin;

  @override
  ConsumerState<GtexLiveCompetitionsCommandScreen> createState() =>
      _GtexLiveCompetitionsCommandScreenState();
}

class _GtexLiveCompetitionsCommandScreenState
    extends ConsumerState<GtexLiveCompetitionsCommandScreen> {
  CompetitionFamilyRoute _family = CompetitionFamilyRoute.gtex;
  String? _selectedCompetitionId;
  bool _joining = false;

  @override
  Widget build(BuildContext context) {
    final AsyncValue<CompetitionHubData> hub = ref.watch(
      competitionHubProvider,
    );
    return hub.when(
      loading: _buildLoading,
      error: (Object error, StackTrace stackTrace) => _buildUnavailable(error),
      data: _buildLoaded,
    );
  }

  Widget _buildLoading() => _page(
    children: <Widget>[
      _masthead(
        status: GtexCommandStatus.preview,
        statusLabel: 'Loading',
        summary: 'Connecting to the competition feeds.',
        metrics: const <GtexCommandMetric>[
          GtexCommandMetric(
            label: 'GTEX',
            value: 'Loading',
            detail: 'Competition feed',
            accent: GtexColors.accentPrimary,
          ),
          GtexCommandMetric(
            label: 'Hosted',
            value: 'Loading',
            detail: 'Creator-run events',
            accent: GtexColors.accentBlue,
          ),
          GtexCommandMetric(
            label: 'Tournaments',
            value: 'Loading',
            detail: 'Creator circuits',
            accent: GtexColors.accentAmber,
          ),
        ],
      ),
      const SizedBox(height: GtexSpacing.lg),
      const _CompetitionStatePanel(
        title: 'Loading competition command',
        detail: 'No competition counts are shown until the providers respond.',
        icon: Icons.sync_rounded,
      ),
    ],
  );

  Widget _buildUnavailable(Object error) => _page(
    children: <Widget>[
      _masthead(
        status: GtexCommandStatus.unavailable,
        statusLabel: 'Unavailable',
        summary: 'Competition feeds could not be recovered from the service.',
        metrics: const <GtexCommandMetric>[
          GtexCommandMetric(
            label: 'GTEX',
            value: 'Unavailable',
            detail: 'Feed did not load',
            accent: GtexColors.accentRed,
          ),
          GtexCommandMetric(
            label: 'Hosted',
            value: 'Unavailable',
            detail: 'Feed did not load',
            accent: GtexColors.accentRed,
          ),
          GtexCommandMetric(
            label: 'Tournaments',
            value: 'Unavailable',
            detail: 'Feed did not load',
            accent: GtexColors.accentRed,
          ),
        ],
      ),
      const SizedBox(height: GtexSpacing.lg),
      _CompetitionStatePanel(
        title: 'Competition feed unavailable',
        detail: 'Retry when the service connection is available.',
        icon: Icons.cloud_off_rounded,
        action: GtexCommandAction(
          label: 'Retry',
          icon: Icons.refresh_rounded,
          accent: GtexColors.accentRed,
          onPressed: () => ref.invalidate(competitionHubProvider),
        ),
      ),
    ],
  );

  Widget _buildLoaded(CompetitionHubData data) {
    final List<_CompetitionCardData> cards = _cardsFor(data, _family);
    final String? selection =
        cards.any(
              (_CompetitionCardData item) => item.id == _selectedCompetitionId,
            )
            ? _selectedCompetitionId
            : null;
    return _page(
      children: <Widget>[
        _masthead(
          status: _hubStatus(data),
          statusLabel: _hubStatusLabel(data),
          summary:
              'Choose a football lane, then move from competition pressure into the live table and matchday.',
          metrics: <GtexCommandMetric>[
            GtexCommandMetric(
              label: 'GTEX',
              value: '${data.gtexCompetitions.length}',
              detail: 'GTEX-hosted competitions',
              accent: GtexColors.accentPrimary,
              icon: Icons.shield_outlined,
            ),
            GtexCommandMetric(
              label: 'Hosted',
              value: '${data.hostedCompetitions.length}',
              detail: 'User competition contracts',
              accent: GtexColors.accentBlue,
              icon: Icons.groups_outlined,
            ),
            GtexCommandMetric(
              label: 'Creator',
              value: '${data.streamerTournaments.length}',
              detail: 'Streamer tournament circuits',
              accent: GtexColors.accentAmber,
              icon: Icons.mic_none_rounded,
            ),
          ],
        ),
        const SizedBox(height: GtexSpacing.lg),
        GtexCompetitionFamilySelector<CompetitionFamilyRoute>(
          value: _family,
          onChanged:
              (CompetitionFamilyRoute value) => setState(() {
                _family = value;
                _selectedCompetitionId = null;
              }),
          items: const <GtexCompetitionFamilyItem<CompetitionFamilyRoute>>[
            GtexCompetitionFamilyItem<CompetitionFamilyRoute>(
              value: CompetitionFamilyRoute.gtex,
              label: 'GTEX competitions',
              accent: GtexColors.accentPrimary,
            ),
            GtexCompetitionFamilyItem<CompetitionFamilyRoute>(
              value: CompetitionFamilyRoute.hosted,
              label: 'Hosted competitions',
              accent: GtexColors.accentBlue,
            ),
            GtexCompetitionFamilyItem<CompetitionFamilyRoute>(
              value: CompetitionFamilyRoute.streamer,
              label: 'Creator tournaments',
              accent: GtexColors.accentAmber,
            ),
          ],
        ),
        const SizedBox(height: GtexSpacing.md),
        LayoutBuilder(
          builder: (BuildContext context, BoxConstraints constraints) {
            final Widget browse = _CompetitionBrowseList(
              family: _family,
              cards: cards,
              selectedId: selection,
              onSelected:
                  (String id) => setState(() => _selectedCompetitionId = id),
            );
            final Widget detail = _buildDetail(selection);
            if (constraints.maxWidth < 900) {
              return Column(
                children: <Widget>[
                  browse,
                  const SizedBox(height: GtexSpacing.md),
                  detail,
                ],
              );
            }
            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                SizedBox(width: 360, child: browse),
                const SizedBox(width: GtexSpacing.md),
                Expanded(child: detail),
              ],
            );
          },
        ),
      ],
    );
  }

  Widget _buildDetail(String? selection) {
    if (selection == null) {
      return const _CompetitionStatePanel(
        title: 'Select a competition',
        detail:
            'Its current contract, football context, and participation state appear here.',
        icon: Icons.sports_soccer_rounded,
      );
    }
    return switch (_family) {
      CompetitionFamilyRoute.gtex => _GtexCompetitionDetail(
        competitionId: selection,
        isAuthenticated: widget.isAuthenticated,
        joining: _joining,
        onOpenLogin: widget.onOpenLogin,
        onJoin: _joinGtexCompetition,
      ),
      CompetitionFamilyRoute.hosted => _HostedCompetitionDetail(
        competitionId: selection,
        isAuthenticated: widget.isAuthenticated,
        onOpenLogin: widget.onOpenLogin,
      ),
      CompetitionFamilyRoute.streamer => _StreamerTournamentDetail(
        tournamentId: selection,
      ),
    };
  }

  Future<void> _joinGtexCompetition(CompetitionSummary competition) async {
    if (!widget.isAuthenticated) {
      widget.onOpenLogin();
      return;
    }
    final String? userId = ref.read(currentUserIdProvider);
    if (userId == null ||
        userId.isEmpty ||
        !competition.joinEligibility.eligible) {
      return;
    }
    setState(() => _joining = true);
    try {
      await ref
          .read(competitionApiProvider)
          .joinCompetition(competition.id, userId: userId);
      ref.invalidate(competitionHubProvider);
      ref.invalidate(gtexCompetitionDetailProvider(competition.id));
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Competition entry confirmed.')),
        );
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Competition entry could not be completed.'),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _joining = false);
    }
  }

  Widget _masthead({
    required GtexCommandStatus status,
    required String statusLabel,
    required String summary,
    required List<GtexCommandMetric> metrics,
  }) => GtexCommandCenterMasthead(
    eyebrow: 'Competition command',
    identity: 'GTEX Football',
    identityDetail: 'Competition and matchday',
    title: 'The competition is the matchday.',
    summary: summary,
    statusLabel: statusLabel,
    status: status,
    metrics: metrics,
    primaryAction: GtexCommandAction(
      label: 'Refresh',
      icon: Icons.refresh_rounded,
      onPressed: () => ref.invalidate(competitionHubProvider),
    ),
  );

  List<_CompetitionCardData> _cardsFor(
    CompetitionHubData data,
    CompetitionFamilyRoute family,
  ) {
    switch (family) {
      case CompetitionFamilyRoute.gtex:
        return data.gtexCompetitions
            .map(_CompetitionCardData.fromGtex)
            .toList(growable: false);
      case CompetitionFamilyRoute.hosted:
        return data.hostedCompetitions
            .map(_CompetitionCardData.fromHosted)
            .toList(growable: false);
      case CompetitionFamilyRoute.streamer:
        return data.streamerTournaments
            .map(_CompetitionCardData.fromStreamer)
            .toList(growable: false);
    }
  }
}

class _CompetitionBrowseList extends StatelessWidget {
  const _CompetitionBrowseList({
    required this.family,
    required this.cards,
    required this.selectedId,
    required this.onSelected,
  });
  final CompetitionFamilyRoute family;
  final List<_CompetitionCardData> cards;
  final String? selectedId;
  final ValueChanged<String> onSelected;

  @override
  Widget build(BuildContext context) {
    if (cards.isEmpty) {
      return _CompetitionStatePanel(
        title: '${family.label} are quiet',
        detail: 'The provider returned no records for this competition family.',
        icon: Icons.event_busy_rounded,
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text('Competition board', style: GtexText.displaySM),
        const SizedBox(height: GtexSpacing.sm),
        ...cards.map(
          (_CompetitionCardData card) => Padding(
            padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
            child: _CompetitionCard(
              card: card,
              selected: card.id == selectedId,
              onTap: () => onSelected(card.id),
            ),
          ),
        ),
      ],
    );
  }
}

class _CompetitionCard extends StatelessWidget {
  const _CompetitionCard({
    required this.card,
    required this.selected,
    required this.onTap,
  });
  final _CompetitionCardData card;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
    color: Colors.transparent,
    child: InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
      child: Ink(
        padding: const EdgeInsets.all(GtexSpacing.md),
        decoration: BoxDecoration(
          color:
              selected
                  ? card.accent.withValues(alpha: 0.12)
                  : GtexColors.surfaceRaised,
          border: Border.all(
            color: selected ? card.accent : GtexColors.surfaceBorder,
          ),
          borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              card.status.toUpperCase(),
              style: GtexText.labelSM.copyWith(color: card.accent),
            ),
            const SizedBox(height: 4),
            Text(
              card.title,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: GtexText.labelLG.copyWith(color: GtexColors.textPrimary),
            ),
            const SizedBox(height: 4),
            Text(
              card.detail,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: GtexText.bodySM.copyWith(color: GtexColors.textSecondary),
            ),
          ],
        ),
      ),
    ),
  );
}

class _GtexCompetitionDetail extends ConsumerWidget {
  const _GtexCompetitionDetail({
    required this.competitionId,
    required this.isAuthenticated,
    required this.joining,
    required this.onOpenLogin,
    required this.onJoin,
  });
  final String competitionId;
  final bool isAuthenticated;
  final bool joining;
  final VoidCallback onOpenLogin;
  final ValueChanged<CompetitionSummary> onJoin;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<GtexCompetitionDetailBundle> detail = ref.watch(
      gtexCompetitionDetailProvider(competitionId),
    );
    return detail.when(
      loading:
          () => const _CompetitionStatePanel(
            title: 'Loading competition detail',
            detail: 'Loading its authoritative table and fixture feed.',
            icon: Icons.sync_rounded,
          ),
      error:
          (Object error, StackTrace stackTrace) => _CompetitionStatePanel(
            title: 'Competition detail unavailable',
            detail:
                'The competition, financial, standings, or fixture service did not respond.',
            icon: Icons.cloud_off_rounded,
            action: GtexCommandAction(
              label: 'Retry',
              icon: Icons.refresh_rounded,
              accent: GtexColors.accentRed,
              onPressed:
                  () => ref.invalidate(
                    gtexCompetitionDetailProvider(competitionId),
                  ),
            ),
          ),
      data:
          (GtexCompetitionDetailBundle bundle) => _GtexCompetitionDetailBody(
            bundle: bundle,
            isAuthenticated: isAuthenticated,
            joining: joining,
            onOpenLogin: onOpenLogin,
            onJoin: onJoin,
          ),
    );
  }
}

class _GtexCompetitionDetailBody extends StatelessWidget {
  const _GtexCompetitionDetailBody({
    required this.bundle,
    required this.isAuthenticated,
    required this.joining,
    required this.onOpenLogin,
    required this.onJoin,
  });
  final GtexCompetitionDetailBundle bundle;
  final bool isAuthenticated;
  final bool joining;
  final VoidCallback onOpenLogin;
  final ValueChanged<CompetitionSummary> onJoin;

  @override
  Widget build(BuildContext context) {
    final CompetitionSummary competition = bundle.competition;
    final GtexCommandStatus status = _statusForCompetition(competition.status);
    final Widget participation = _participation(competition);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        GtexCommandCenterMasthead(
          eyebrow: 'GTEX competition',
          identity: competition.creatorLabel,
          identityDetail: competition.hostSummary,
          title: competition.name,
          summary:
              competition.rulesSummary.isEmpty
                  ? 'Competition rules have not been supplied.'
                  : competition.rulesSummary,
          statusLabel: _competitionStatusLabel(competition.status),
          status: status,
          metrics: <GtexCommandMetric>[
            GtexCommandMetric(
              label: 'Format',
              value: competition.safeFormatLabel,
              detail: competition.rankingLabel,
              accent: GtexColors.accentPrimary,
            ),
            GtexCommandMetric(
              label: 'Participants',
              value: '${competition.participantCount}',
              detail:
                  competition.capacity > 0
                      ? 'Capacity ${competition.capacity}'
                      : 'Capacity not reported',
              accent: GtexColors.accentBlue,
            ),
            GtexCommandMetric(
              label: 'Matchday',
              value: '${bundle.fixtures.length}',
              detail: 'Reported fixtures',
              accent: GtexColors.accentAmber,
            ),
          ],
        ),
        const SizedBox(height: GtexSpacing.md),
        participation,
        const SizedBox(height: GtexSpacing.lg),
        _DetailSection(
          title: 'Current football context',
          child: _Fixtures(fixtures: bundle.fixtures),
        ),
        const SizedBox(height: GtexSpacing.lg),
        _DetailSection(
          title: 'Standings',
          child: _Standings(standings: bundle.standings),
        ),
        const SizedBox(height: GtexSpacing.lg),
        _DetailSection(
          title: 'Competition economy',
          child: _CompetitionEconomy(financials: bundle.financials),
        ),
      ],
    );
  }

  Widget _participation(CompetitionSummary competition) {
    if (!isAuthenticated) {
      return _CompetitionStatePanel(
        title: 'Sign in to check participation',
        detail:
            'Join eligibility is evaluated for your account by the competition service.',
        icon: Icons.lock_outline_rounded,
        action: GtexCommandAction(
          label: 'Sign in',
          icon: Icons.login_rounded,
          onPressed: onOpenLogin,
        ),
      );
    }
    final CompetitionJoinEligibility eligibility = competition.joinEligibility;
    if (!eligibility.eligible) {
      return _CompetitionStatePanel(
        title: 'Participation locked',
        detail:
            eligibility.reason?.trim().isNotEmpty == true
                ? eligibility.reason!
                : 'The competition service does not currently permit entry.',
        icon: Icons.lock_outline_rounded,
      );
    }
    if (eligibility.requiresInvite ||
        eligibility.requiresPasscode ||
        competition.requiresPasscode) {
      return _CompetitionStatePanel(
        title: 'Participation requires verification',
        detail:
            eligibility.requiresInvite
                ? 'An invite is required by the competition service.'
                : 'A passcode is required by the competition service.',
        icon: Icons.verified_user_outlined,
      );
    }
    return _CompetitionStatePanel(
      title: 'Ready to participate',
      detail:
          'Your account is currently eligible to enter this GTEX competition.',
      icon: Icons.how_to_reg_rounded,
      action: GtexCommandAction(
        label: joining ? 'Joining…' : 'Join competition',
        icon: Icons.sports_soccer_rounded,
        onPressed: joining ? null : () => onJoin(competition),
      ),
    );
  }
}

class _HostedCompetitionDetail extends ConsumerStatefulWidget {
  const _HostedCompetitionDetail({
    required this.competitionId,
    required this.isAuthenticated,
    required this.onOpenLogin,
  });
  final String competitionId;
  final bool isAuthenticated;
  final VoidCallback onOpenLogin;

  @override
  ConsumerState<_HostedCompetitionDetail> createState() =>
      _HostedCompetitionDetailState();
}

class _HostedCompetitionDetailState
    extends ConsumerState<_HostedCompetitionDetail> {
  bool _joining = false;

  @override
  Widget build(BuildContext context) {
    final AsyncValue<HostedCompetitionDetailBundle> detail = ref.watch(
      hostedCompetitionDetailProvider(widget.competitionId),
    );
    return detail.when(
      loading:
          () => const _CompetitionStatePanel(
            title: 'Loading hosted competition',
            detail: 'Loading the host-owned competition contract.',
            icon: Icons.sync_rounded,
          ),
      error:
          (Object error, StackTrace stackTrace) => _CompetitionStatePanel(
            title: 'Hosted competition unavailable',
            detail:
                'This host-owned competition detail could not be recovered.',
            icon: Icons.cloud_off_rounded,
          ),
      data: _buildDetail,
    );
  }

  Widget _buildDetail(HostedCompetitionDetailBundle bundle) {
    final HostedCompetitionDetail detail = bundle.detail;
    final HostedCompetition competition = detail.competition;
    if (!widget.isAuthenticated) {
      return _CompetitionStatePanel(
        title: competition.title,
        detail:
            'Sign in to evaluate participation in this host-owned competition.',
        icon: Icons.lock_outline_rounded,
        action: GtexCommandAction(
          label: 'Sign in',
          icon: Icons.login_rounded,
          onPressed: widget.onOpenLogin,
        ),
      );
    }
    if (!detail.joinOpen) {
      return _CompetitionStatePanel(
        title: competition.title,
        detail:
            'Participation is not open according to the hosted competition contract.',
        icon: Icons.lock_outline_rounded,
      );
    }
    if (competition.requiresPasscode) {
      return _CompetitionStatePanel(
        title: competition.title,
        detail:
            'A passcode is required by this hosted competition. Entry is not submitted without it.',
        icon: Icons.verified_user_outlined,
      );
    }
    return _CompetitionStatePanel(
      title: competition.title,
      detail:
          'Participation is open. ${bundle.standings.length} standings records were reported.',
      icon: Icons.groups_outlined,
      action: GtexCommandAction(
        label: _joining ? 'Joiningâ€¦' : 'Join hosted competition',
        icon: Icons.how_to_reg_rounded,
        onPressed: _joining ? null : () => _join(competition.id),
      ),
    );
  }

  Future<void> _join(String competitionId) async {
    setState(() => _joining = true);
    try {
      await ref
          .read(hostedCompetitionApiProvider)
          .joinCompetition(competitionId);
      ref.invalidate(competitionHubProvider);
      ref.invalidate(hostedCompetitionDetailProvider(competitionId));
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Hosted competition entry confirmed.')),
        );
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Hosted competition entry could not be completed.'),
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _joining = false);
      }
    }
  }
}

class _StreamerTournamentDetail extends ConsumerWidget {
  const _StreamerTournamentDetail({required this.tournamentId});
  final String tournamentId;
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<StreamerTournamentDetailBundle> detail = ref.watch(
      streamerTournamentDetailProvider(tournamentId),
    );
    return detail.when(
      loading:
          () => const _CompetitionStatePanel(
            title: 'Loading creator tournament',
            detail: 'Loading the creator tournament contract.',
            icon: Icons.sync_rounded,
          ),
      error:
          (Object error, StackTrace stackTrace) => _CompetitionStatePanel(
            title: 'Creator tournament unavailable',
            detail: 'This creator tournament detail could not be recovered.',
            icon: Icons.cloud_off_rounded,
          ),
      data:
          (StreamerTournamentDetailBundle bundle) => _CompetitionStatePanel(
            title: bundle.tournament.title,
            detail:
                'Creator tournament status: ${bundle.tournament.status}. Entry follows the creator tournament contract.',
            icon: Icons.mic_none_rounded,
          ),
    );
  }
}

class _Fixtures extends StatelessWidget {
  const _Fixtures({required this.fixtures});
  final List<JsonMap> fixtures;
  @override
  Widget build(BuildContext context) {
    if (fixtures.isEmpty) {
      return const _CompetitionStatePanel(
        title: 'No fixtures reported',
        detail:
            'No matchday fixtures are available from this competition feed.',
        icon: Icons.calendar_today_outlined,
      );
    }
    return Column(
      children: fixtures
          .map((JsonMap fixture) {
            final String home =
                _value(fixture, const <String>[
                  'home_team_name',
                  'homeName',
                  'home_name',
                  'home',
                ]) ??
                'Home team unavailable';
            final String away =
                _value(fixture, const <String>[
                  'away_team_name',
                  'awayName',
                  'away_name',
                  'away',
                ]) ??
                'Away team unavailable';
            final String status =
                _value(fixture, const <String>['status', 'state']) ??
                'Fixture reported';
            final String? time = _value(fixture, const <String>[
              'scheduled_at',
              'scheduledAt',
              'kickoff_at',
            ]);
            final String? score = _score(fixture);
            final String? matchKey = _value(fixture, const <String>[
              'match_key',
              'matchKey',
            ]);
            return Padding(
              padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
              child: GtexMatchdayFixtureTile(
                home: home,
                away: away,
                stateLabel: status,
                contextLabel: time,
                scoreLabel: score,
                onOpenMatch:
                    matchKey == null
                        ? null
                        : () => context.go(
                          '/matches/viewer/${Uri.encodeComponent(matchKey)}',
                        ),
              ),
            );
          })
          .toList(growable: false),
    );
  }
}

class _Standings extends StatelessWidget {
  const _Standings({required this.standings});
  final List<JsonMap> standings;
  @override
  Widget build(BuildContext context) {
    if (standings.isEmpty) {
      return const _CompetitionStatePanel(
        title: 'No standings reported',
        detail: 'No league table is available from this competition feed.',
        icon: Icons.leaderboard_outlined,
      );
    }
    return Container(
      decoration: BoxDecoration(
        color: GtexColors.surfaceRaised,
        border: Border.all(color: GtexColors.surfaceBorder),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
      ),
      child: Column(
        children: standings
            .map(
              (JsonMap row) => GtexCompetitionStandingRow(
                position:
                    _value(row, const <String>['position', 'rank']) ?? '–',
                name:
                    _value(row, const <String>[
                      'club_name',
                      'team_name',
                      'name',
                    ]) ??
                    'Club unavailable',
                points: _value(row, const <String>['points', 'pts']) ?? '–',
                played: _value(row, const <String>['played', 'matches_played']),
              ),
            )
            .toList(growable: false),
      ),
    );
  }
}

class _CompetitionEconomy extends StatelessWidget {
  const _CompetitionEconomy({required this.financials});
  final CompetitionFinancialSummary financials;

  @override
  Widget build(BuildContext context) {
    final String currency =
        financials.currency.trim().isEmpty
            ? 'Currency unavailable'
            : financials.currency;
    return Container(
      padding: const EdgeInsets.all(GtexSpacing.md),
      decoration: BoxDecoration(
        color: GtexColors.surfaceRaised,
        border: Border.all(color: GtexColors.surfaceBorder),
        borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
      ),
      child: Wrap(
        spacing: GtexSpacing.lg,
        runSpacing: GtexSpacing.sm,
        children: <Widget>[
          _EconomyValue(
            label: 'Entry',
            value: _money(financials.entryFee, currency),
          ),
          _EconomyValue(
            label: 'Prize pool',
            value: _money(financials.prizePool, currency),
          ),
          _EconomyValue(
            label: 'Gross pool',
            value: _money(financials.grossPool, currency),
          ),
          _EconomyValue(
            label: 'Remaining slots',
            value: '${financials.remainingSlots}',
          ),
        ],
      ),
    );
  }
}

class _EconomyValue extends StatelessWidget {
  const _EconomyValue({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => SizedBox(
    width: 132,
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(
          label.toUpperCase(),
          style: GtexText.labelSM.copyWith(color: GtexColors.textSecondary),
        ),
        const SizedBox(height: 4),
        Text(
          value,
          overflow: TextOverflow.ellipsis,
          style: GtexText.monoMD.copyWith(color: GtexColors.accentAmber),
        ),
      ],
    ),
  );
}

class _DetailSection extends StatelessWidget {
  const _DetailSection({required this.title, required this.child});
  final String title;
  final Widget child;
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: <Widget>[
      Text(title, style: GtexText.displaySM),
      const SizedBox(height: GtexSpacing.sm),
      child,
    ],
  );
}

class _CompetitionStatePanel extends StatelessWidget {
  const _CompetitionStatePanel({
    required this.title,
    required this.detail,
    required this.icon,
    this.action,
  });
  final String title;
  final String detail;
  final IconData icon;
  final Widget? action;
  @override
  Widget build(BuildContext context) => Container(
    width: double.infinity,
    padding: const EdgeInsets.all(GtexSpacing.lg),
    decoration: BoxDecoration(
      color: GtexColors.surfaceRaised,
      border: Border.all(color: GtexColors.surfaceBorder),
      borderRadius: BorderRadius.circular(GtexSpacing.radiusMd),
    ),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Icon(icon, color: GtexColors.accentBlue),
        const SizedBox(height: GtexSpacing.sm),
        Text(title, style: GtexText.displaySM),
        const SizedBox(height: 4),
        Text(
          detail,
          style: GtexText.bodyMD.copyWith(color: GtexColors.textSecondary),
        ),
        if (action != null) ...<Widget>[
          const SizedBox(height: GtexSpacing.md),
          action!,
        ],
      ],
    ),
  );
}

extension on _GtexLiveCompetitionsCommandScreenState {
  Widget _page({required List<Widget> children}) => SafeArea(
    child: SingleChildScrollView(
      padding: const EdgeInsets.all(GtexSpacing.lg),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 1440),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: children,
        ),
      ),
    ),
  );
}

class _CompetitionCardData {
  const _CompetitionCardData({
    required this.id,
    required this.title,
    required this.status,
    required this.detail,
    required this.accent,
  });
  final String id;
  final String title;
  final String status;
  final String detail;
  final Color accent;
  factory _CompetitionCardData.fromGtex(CompetitionSummary item) =>
      _CompetitionCardData(
        id: item.id,
        title: item.name,
        status: _competitionStatusLabel(item.status),
        detail: item.hostSummary,
        accent: GtexColors.accentPrimary,
      );
  factory _CompetitionCardData.fromHosted(HostedCompetition item) =>
      _CompetitionCardData(
        id: item.id,
        title: item.title,
        status: item.status,
        detail:
            item.description.isEmpty ? 'Hosted competition' : item.description,
        accent: GtexColors.accentBlue,
      );
  factory _CompetitionCardData.fromStreamer(StreamerTournament item) =>
      _CompetitionCardData(
        id: item.id,
        title: item.title,
        status: item.status,
        detail: item.description ?? 'Creator tournament',
        accent: GtexColors.accentAmber,
      );
}

GtexCommandStatus _statusForCompetition(CompetitionStatus status) =>
    switch (status) {
      CompetitionStatus.inProgress => GtexCommandStatus.live,
      CompetitionStatus.openForJoin ||
      CompetitionStatus.published => GtexCommandStatus.open,
      CompetitionStatus.draft ||
      CompetitionStatus.locked ||
      CompetitionStatus.filled => GtexCommandStatus.active,
      CompetitionStatus.completed => GtexCommandStatus.offline,
      CompetitionStatus.cancelled ||
      CompetitionStatus.refunded ||
      CompetitionStatus.disputed => GtexCommandStatus.unavailable,
    };
String _competitionStatusLabel(CompetitionStatus status) => switch (status) {
  CompetitionStatus.openForJoin => 'Open for join',
  CompetitionStatus.inProgress => 'Matchday live',
  CompetitionStatus.published => 'Published',
  CompetitionStatus.filled => 'Full',
  CompetitionStatus.locked => 'Locked',
  CompetitionStatus.completed => 'Completed',
  CompetitionStatus.cancelled => 'Cancelled',
  CompetitionStatus.refunded => 'Refunded',
  CompetitionStatus.disputed => 'Disputed',
  CompetitionStatus.draft => 'Draft',
};
GtexCommandStatus _hubStatus(CompetitionHubData data) =>
    data.gtexCompetitions.any(
          (CompetitionSummary item) =>
              item.status == CompetitionStatus.inProgress,
        )
        ? GtexCommandStatus.live
        : data.gtexCompetitions.any(
          (CompetitionSummary item) =>
              item.status == CompetitionStatus.openForJoin,
        )
        ? GtexCommandStatus.open
        : GtexCommandStatus.active;
String _hubStatusLabel(CompetitionHubData data) =>
    data.gtexCompetitions.any(
          (CompetitionSummary item) =>
              item.status == CompetitionStatus.inProgress,
        )
        ? 'Matchday live'
        : data.gtexCompetitions.any(
          (CompetitionSummary item) =>
              item.status == CompetitionStatus.openForJoin,
        )
        ? 'Competition open'
        : 'Competition board';
String? _value(JsonMap map, List<String> keys) {
  for (final String key in keys) {
    final Object? value = map[key];
    if (value != null && value.toString().trim().isNotEmpty) {
      return value.toString();
    }
  }
  return null;
}

String? _score(JsonMap map) {
  final String? home = _value(map, const <String>['home_score', 'homeScore']);
  final String? away = _value(map, const <String>['away_score', 'awayScore']);
  return home != null && away != null ? '$home–$away' : null;
}

String _money(double amount, String currency) =>
    '${amount.toStringAsFixed(2)} $currency';
