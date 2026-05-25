import 'package:flutter/material.dart';
import 'package:gte_frontend/controllers/competition_controller.dart';
import 'package:gte_frontend/features/competition_redesign/data/gtex_competition_repository.dart'
    as competition_data;
import 'package:gte_frontend/features/competition_redesign/models/gtex_competition_models.dart'
    as competition_v2;
import 'package:gte_frontend/features/competition_redesign/presentation/gtex_competitions_hub_screen_v2.dart'
    as competition_ui;
import 'package:gte_frontend/features/competitions_hub/routing/competition_hub_destination.dart';
import 'package:gte_frontend/features/navigation_guards/gte_navigation_guards.dart';
import 'package:gte_frontend/models/competition_models.dart' as live;
import 'package:gte_frontend/models/competition_rule_models.dart' as live_rules;
import 'package:gte_frontend/models/match_type.dart';

/// Route-compatible V2 wrapper for the live competitions destination.
///
/// This mounts the GTEX V2 competition workspace without swapping the
/// production route onto demo data. The adapter reads and mutates through the
/// existing [CompetitionController].
class GteCompetitionsHubScreenV2 extends StatelessWidget {
  const GteCompetitionsHubScreenV2({
    super.key,
    required this.controller,
    this.isAuthenticated = false,
    this.onOpenLogin,
    this.canHostCompetitions = false,
    this.initialCompetitionId,
    this.inviteCode,
    CompetitionHubDestination currentDestination =
        CompetitionHubDestination.overview,
    ValueChanged<CompetitionHubDestination>? onDestinationChanged,
    bool isCheckingCreatorAccess = false,
    VoidCallback? onOpenCreatorAccessRequest,
    GteNavigationDependencies? navigationDependencies,
  });

  final CompetitionController controller;
  final bool isAuthenticated;
  final bool canHostCompetitions;
  final VoidCallback? onOpenLogin;
  final String? initialCompetitionId;
  final String? inviteCode;

  @override
  Widget build(BuildContext context) {
    return competition_ui.GtexCompetitionsHubScreenV2(
      initialCompetitionId: initialCompetitionId,
      repository: LiveGtexCompetitionRepositoryAdapter(
        controller: controller,
        isAuthenticated: isAuthenticated,
        canHostCompetitions: canHostCompetitions,
        onOpenLogin: onOpenLogin,
        inviteCode: inviteCode,
      ),
      canCreateCompetitions: isAuthenticated && canHostCompetitions,
    );
  }
}

class LiveGtexCompetitionRepositoryAdapter
    implements competition_data.GtexCompetitionRepository {
  const LiveGtexCompetitionRepositoryAdapter({
    required this.controller,
    required this.isAuthenticated,
    this.canHostCompetitions = false,
    this.onOpenLogin,
    this.inviteCode,
  });

  final CompetitionController controller;
  final bool isAuthenticated;
  final bool canHostCompetitions;
  final VoidCallback? onOpenLogin;
  final String? inviteCode;

  @override
  Future<List<competition_v2.GtexCompetitionSummary>> listCompetitions() async {
    await controller.bootstrap();
    final List<live.CompetitionSummary> summaries = controller.competitions
        .toList(growable: true);
    final live.CompetitionSummary? selected = controller.selectedCompetition;
    if (selected != null &&
        !summaries.any(
          (live.CompetitionSummary item) => item.id == selected.id,
        )) {
      summaries.insert(0, selected);
    }
    return summaries.map(_toV2Summary).toList(growable: false);
  }

  @override
  Future<competition_v2.GtexCompetitionDetail> getCompetitionDetail(
    String competitionId,
  ) async {
    await controller.openCompetition(competitionId, inviteCode: inviteCode);
    final live.CompetitionSummary summary =
        controller.selectedCompetition ??
        controller.competitions.firstWhere(
          (live.CompetitionSummary item) => item.id == competitionId,
          orElse: () => controller.competitions.first,
        );
    return _toV2Detail(summary, controller.selectedFinancials);
  }

  @override
  Future<void> joinCompetition(String competitionId) async {
    if (!isAuthenticated) {
      onOpenLogin?.call();
      throw StateError('Sign in to create a GTEX competition.');
    }
    if (!canHostCompetitions) {
      throw StateError(
        'This account is not cleared to host GTEX competitions yet.',
      );
    }
    await controller.openCompetition(competitionId, inviteCode: inviteCode);
    await controller.joinSelectedCompetition(inviteCode: inviteCode);
  }

  @override
  Future<void> createCompetition(
    competition_v2.GtexCompetitionDraft draft,
  ) async {
    if (!isAuthenticated) {
      onOpenLogin?.call();
      return;
    }
    controller.startNewDraft();
    controller.updateDraftName(draft.title);
    controller.updateDraftFormat(_formatFromV2(draft.kind));
    controller.updateDraftVisibility(_visibilityFromV2(draft.visibility));
    controller.updateDraftEntryFee(draft.entryFeeCredits.toDouble());
    controller.updateDraftCapacity(draft.maxClubs);
    controller.updateDraftRules(
      live_rules.CompetitionRuleSet.defaults(_formatFromV2(draft.kind)),
    );
    await controller.publishDraft();
  }

  competition_v2.GtexCompetitionSummary _toV2Summary(
    live.CompetitionSummary item,
  ) {
    return competition_v2.GtexCompetitionSummary(
      id: item.id,
      title: item.name,
      kind: _kindFromLive(item),
      status: _statusFromLive(item.status),
      regionLabel: item.hostSummary,
      entryFeeCredits: item.entryFee.round(),
      prizePoolCredits: item.prizePool.round(),
      registeredClubs: item.participantCount,
      maxClubs: item.capacity,
      progressPercent: item.fillRate.clamp(0, 1).toDouble(),
      currentStage: _stageLabel(item.status),
      startsAtLabel: _startsAtLabel(item),
      description:
          item.rulesSummary.trim().isEmpty
              ? item.economyNotice
              : item.rulesSummary,
      ownerClubName: item.isUserHosted ? item.creatorLabel : null,
      creatorName: item.creatorName,
    );
  }

  competition_v2.GtexCompetitionDetail _toV2Detail(
    live.CompetitionSummary summary,
    live.CompetitionFinancialSummary? financials,
  ) {
    final competition_v2.GtexCompetitionSummary v2Summary = _toV2Summary(
      summary,
    );
    return competition_v2.GtexCompetitionDetail(
      summary: v2Summary,
      fixtures: const <competition_v2.GtexCompetitionFixture>[],
      standings: const <competition_v2.GtexCompetitionStanding>[],
      stages: <competition_v2.GtexTournamentStageProgress>[
        competition_v2.GtexTournamentStageProgress(
          title: 'Registration',
          statusLabel:
              summary.participantCount >= summary.capacity
                  ? 'Full'
                  : _stageLabel(summary.status),
          progressPercent: summary.fillRate.clamp(0, 1).toDouble(),
          summary:
              '${summary.participantCount}/${summary.capacity} clubs registered through live competition data.',
        ),
        competition_v2.GtexTournamentStageProgress(
          title: 'Prize settlement',
          statusLabel:
              financials == null
                  ? 'Pending'
                  : '${financials.prizePool.round()} ${financials.currency}',
          progressPercent:
              summary.status == live.CompetitionStatus.completed ? 1 : 0,
          summary:
              financials == null
                  ? 'Financial snapshot is not available yet.'
                  : 'Gross pool ${financials.grossPool.round()} ${financials.currency}, platform fee ${financials.platformFeeAmount.round()} ${financials.currency}.',
        ),
      ],
      rules: <competition_v2.GtexCompetitionRule>[
        competition_v2.GtexCompetitionRule(
          title: 'Competition rules',
          description:
              summary.rulesSummary.trim().isEmpty
                  ? 'Rules are synced from the live competition API when published.'
                  : summary.rulesSummary,
        ),
        competition_v2.GtexCompetitionRule(
          title: 'Entry economy',
          description: summary.economyNotice,
        ),
        if (summary.specialRules?.trim().isNotEmpty == true)
          competition_v2.GtexCompetitionRule(
            title: 'Special rules',
            description: summary.specialRules!.trim(),
          ),
      ],
      newsSignals: <String>[
        '${summary.name} is ${_stageLabel(summary.status).toLowerCase()} with ${summary.participantCount}/${summary.capacity} clubs registered.',
        'Prize pool currently sits at ${summary.prizePool.round()} ${summary.currency}.',
        if (summary.creatorName?.trim().isNotEmpty == true)
          '${summary.creatorName!.trim()} is driving the creator-hosted competition feed.',
      ],
    );
  }

  competition_v2.GtexCompetitionKind _kindFromLive(
    live.CompetitionSummary item,
  ) {
    switch (item.matchType) {
      case MatchType.gtexHosted:
        return competition_v2.GtexCompetitionKind.gtexTournament;
      case MatchType.fastMatch:
        return competition_v2.GtexCompetitionKind.academy;
      case MatchType.userHosted:
        return item.creatorName?.trim().isNotEmpty == true
            ? competition_v2.GtexCompetitionKind.creatorHosted
            : competition_v2.GtexCompetitionKind.userHosted;
    }
  }

  competition_v2.GtexCompetitionStatus _statusFromLive(
    live.CompetitionStatus status,
  ) {
    switch (status) {
      case live.CompetitionStatus.draft:
        return competition_v2.GtexCompetitionStatus.draft;
      case live.CompetitionStatus.published:
      case live.CompetitionStatus.openForJoin:
        return competition_v2.GtexCompetitionStatus.registrationOpen;
      case live.CompetitionStatus.filled:
      case live.CompetitionStatus.locked:
        return competition_v2.GtexCompetitionStatus.registrationClosed;
      case live.CompetitionStatus.inProgress:
        return competition_v2.GtexCompetitionStatus.live;
      case live.CompetitionStatus.completed:
      case live.CompetitionStatus.cancelled:
      case live.CompetitionStatus.refunded:
      case live.CompetitionStatus.disputed:
        return competition_v2.GtexCompetitionStatus.completed;
    }
  }

  String _stageLabel(live.CompetitionStatus status) {
    switch (status) {
      case live.CompetitionStatus.draft:
        return 'Draft setup';
      case live.CompetitionStatus.published:
        return 'Published';
      case live.CompetitionStatus.openForJoin:
        return 'Registration';
      case live.CompetitionStatus.filled:
        return 'Full';
      case live.CompetitionStatus.locked:
        return 'Locked';
      case live.CompetitionStatus.inProgress:
        return 'Live';
      case live.CompetitionStatus.completed:
        return 'Completed';
      case live.CompetitionStatus.cancelled:
        return 'Cancelled';
      case live.CompetitionStatus.refunded:
        return 'Refunded';
      case live.CompetitionStatus.disputed:
        return 'Disputed';
    }
  }

  String _startsAtLabel(live.CompetitionSummary item) {
    final DateTime? scheduled = item.scheduledStartAt;
    if (scheduled == null) {
      return item.status == live.CompetitionStatus.inProgress
          ? 'Live now'
          : 'Schedule pending';
    }
    final DateTime local = scheduled.toLocal();
    return '${local.year}-${local.month.toString().padLeft(2, '0')}-${local.day.toString().padLeft(2, '0')}';
  }

  live.CompetitionFormat _formatFromV2(
    competition_v2.GtexCompetitionKind kind,
  ) {
    switch (kind) {
      case competition_v2.GtexCompetitionKind.gtexTournament:
      case competition_v2.GtexCompetitionKind.nationalTeam:
      case competition_v2.GtexCompetitionKind.creatorHosted:
      case competition_v2.GtexCompetitionKind.userHosted:
        return live.CompetitionFormat.cup;
      case competition_v2.GtexCompetitionKind.academy:
        return live.CompetitionFormat.league;
    }
  }

  live.CompetitionVisibility _visibilityFromV2(String value) {
    switch (value.trim().toLowerCase()) {
      case 'private':
        return live.CompetitionVisibility.private;
      case 'invite only':
      case 'invite_only':
      case 'inviteonly':
        return live.CompetitionVisibility.inviteOnly;
      default:
        return live.CompetitionVisibility.public;
    }
  }
}
