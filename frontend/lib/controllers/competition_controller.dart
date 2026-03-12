import 'package:flutter/foundation.dart';
import 'package:gte_frontend/data/competition_api.dart';
import 'package:gte_frontend/models/competition_models.dart';
import 'package:gte_frontend/models/competition_rule_models.dart';

class CompetitionController extends ChangeNotifier {
  CompetitionController({
    required CompetitionApi api,
    required String currentUserId,
    String? currentUserName,
  })  : _api = api,
        _currentUserId = currentUserId,
        _currentUserName = currentUserName,
        draft = CompetitionDraft.initial(
          creatorId: currentUserId,
          creatorName: currentUserName,
        );

  final CompetitionApi _api;
  CompetitionDraft draft;

  String _currentUserId;
  String? _currentUserName;

  bool isLoadingDiscovery = false;
  bool isLoadingDetail = false;
  bool isPublishing = false;
  bool isJoining = false;
  bool isCreatingInvite = false;

  String searchQuery = '';

  CompetitionDiscoverySection section = CompetitionDiscoverySection.trending;
  List<CompetitionSummary> competitions = const <CompetitionSummary>[];
  CompetitionSummary? selectedCompetition;
  CompetitionFinancialSummary? selectedFinancials;
  CompetitionInviteView? latestInvite;

  String? discoveryError;
  String? detailError;
  String? actionError;

  String get currentUserId => _currentUserId;

  String? get currentUserName => _currentUserName;

  bool get hasDraftErrors => draft.validationErrors.isNotEmpty;

  List<String> get draftErrors => draft.validationErrors;

  CompetitionSummary get previewSummary {
    final List<CompetitionPayoutBreakdown> payouts = draft.payoutRules
        .map(
          (CompetitionDraftPayoutRule rule) => CompetitionPayoutBreakdown(
            place: rule.place,
            percent: rule.percent,
            amount: draft.projectedPrizePool * rule.percent,
          ),
        )
        .toList(growable: false);
    return CompetitionSummary(
      id: draft.competitionId ?? 'preview',
      name: draft.name.trim().isEmpty
          ? 'Untitled creator competition'
          : draft.name.trim(),
      format: draft.format,
      visibility: draft.visibility,
      status: CompetitionStatus.draft,
      creatorId: draft.creatorId,
      creatorName: draft.creatorName,
      participantCount: 0,
      capacity: draft.capacity,
      currency: draft.currency,
      entryFee: draft.entryFee,
      platformFeePct: draft.platformFeePct,
      hostFeePct: draft.hostFeePct,
      platformFeeAmount: draft.projectedPlatformFee,
      hostFeeAmount: draft.projectedHostFee,
      prizePool: draft.projectedPrizePool,
      payoutStructure: payouts,
      rulesSummary: draft.rulesSummary,
      joinEligibility: const CompetitionJoinEligibility(
        eligible: false,
        reason: 'competition_not_open',
      ),
      beginnerFriendly: draft.beginnerFriendly,
      createdAt: DateTime.now().toUtc(),
      updatedAt: DateTime.now().toUtc(),
    );
  }

  CompetitionFinancialSummary get previewFinancials {
    final CompetitionSummary summary = previewSummary;
    return CompetitionFinancialSummary(
      competitionId: summary.id,
      participantCount: summary.capacity,
      entryFee: summary.entryFee,
      grossPool: draft.grossPoolAtCapacity,
      platformFeeAmount: draft.projectedPlatformFee,
      hostFeeAmount: draft.projectedHostFee,
      prizePool: draft.projectedPrizePool,
      payoutStructure: summary.payoutStructure,
      currency: draft.currency,
    );
  }

  List<CompetitionSummary> get visibleCompetitions {
    final String query = searchQuery.trim().toLowerCase();
    List<CompetitionSummary> filtered =
        List<CompetitionSummary>.of(competitions);
    if (section == CompetitionDiscoverySection.trending) {
      filtered.sort((CompetitionSummary left, CompetitionSummary right) {
        final int participantCompare =
            right.participantCount.compareTo(left.participantCount);
        if (participantCompare != 0) {
          return participantCompare;
        }
        return right.updatedAt.compareTo(left.updatedAt);
      });
    } else if (section == CompetitionDiscoverySection.newest) {
      filtered.sort((CompetitionSummary left, CompetitionSummary right) {
        return right.createdAt.compareTo(left.createdAt);
      });
    } else if (section == CompetitionDiscoverySection.freeToJoin) {
      filtered = filtered
          .where((CompetitionSummary item) => item.isFreeToJoin)
          .toList(growable: false);
    } else if (section == CompetitionDiscoverySection.paid) {
      filtered = filtered
          .where((CompetitionSummary item) => !item.isFreeToJoin)
          .toList(growable: false);
    } else if (section == CompetitionDiscoverySection.creator) {
      filtered = filtered
          .where(
            (CompetitionSummary item) => item.creatorId == _currentUserId,
          )
          .toList(growable: false);
    } else if (section == CompetitionDiscoverySection.leagues) {
      filtered = filtered
          .where((CompetitionSummary item) => item.isLeague)
          .toList(growable: false);
    } else if (section == CompetitionDiscoverySection.cups) {
      filtered = filtered
          .where((CompetitionSummary item) => item.isCup)
          .toList(growable: false);
    }
    if (query.isEmpty) {
      return filtered;
    }
    return filtered.where((CompetitionSummary item) {
      final String haystack = <String>[
        item.name,
        item.creatorLabel,
        item.rulesSummary,
        item.safeFormatLabel,
      ].join(' ').toLowerCase();
      return haystack.contains(query);
    }).toList(growable: false);
  }

  Future<void> bootstrap() async {
    if (competitions.isNotEmpty || isLoadingDiscovery) {
      return;
    }
    await loadDiscovery();
  }

  Future<void> loadDiscovery() async {
    isLoadingDiscovery = true;
    discoveryError = null;
    notifyListeners();
    try {
      final CompetitionListResponse response = await _api.fetchCompetitions(
        userId: _currentUserId,
      );
      competitions = response.items;
      _syncSelectedFromList();
    } catch (error) {
      discoveryError = error.toString();
    } finally {
      isLoadingDiscovery = false;
      notifyListeners();
    }
  }

  Future<void> openCompetition(
    String competitionId, {
    String? inviteCode,
  }) async {
    isLoadingDetail = true;
    detailError = null;
    notifyListeners();
    try {
      final List<Object> payload = await Future.wait<Object>(<Future<Object>>[
        _api.fetchCompetition(
          competitionId,
          userId: _currentUserId,
          inviteCode: inviteCode,
        ),
        _api.fetchFinancials(
          competitionId,
          userId: _currentUserId,
        ),
      ]);
      selectedCompetition = payload[0] as CompetitionSummary;
      selectedFinancials = payload[1] as CompetitionFinancialSummary;
    } catch (error) {
      detailError = error.toString();
    } finally {
      isLoadingDetail = false;
      notifyListeners();
    }
  }

  void setSection(CompetitionDiscoverySection value) {
    if (section == value) {
      return;
    }
    section = value;
    notifyListeners();
  }

  void setSearchQuery(String value) {
    if (searchQuery == value) {
      return;
    }
    searchQuery = value;
    notifyListeners();
  }

  void updateCurrentUser({
    required String userId,
    String? userName,
  }) {
    if (_currentUserId == userId && _currentUserName == userName) {
      return;
    }
    _currentUserId = userId;
    _currentUserName = userName;
    if (draft.creatorId != userId || draft.creatorName != userName) {
      draft = draft.copyWith(
        creatorId: userId,
        creatorName: userName,
      );
    }
    _syncSelectedFromList();
    notifyListeners();
  }

  void startNewDraft() {
    draft = CompetitionDraft.initial(
      creatorId: _currentUserId,
      creatorName: _currentUserName,
    );
    actionError = null;
    notifyListeners();
  }

  void updateDraftName(String value) {
    draft = draft.copyWith(name: value);
    notifyListeners();
  }

  void updateDraftFormat(CompetitionFormat format) {
    draft = draft.copyWith(
      format: format,
      rules: CompetitionRuleSet.defaults(format),
    );
    notifyListeners();
  }

  void updateDraftVisibility(CompetitionVisibility visibility) {
    draft = draft.copyWith(visibility: visibility);
    notifyListeners();
  }

  void updateDraftBeginnerFriendly(bool value) {
    draft = draft.copyWith(beginnerFriendly: value);
    notifyListeners();
  }

  void updateDraftCapacity(int value) {
    draft = draft.copyWith(capacity: value);
    notifyListeners();
  }

  void updateDraftEntryFee(double value) {
    draft = draft.copyWith(entryFee: value);
    notifyListeners();
  }

  void updateDraftPlatformFee(double value) {
    draft = draft.copyWith(platformFeePct: value);
    notifyListeners();
  }

  void updateDraftHostFee(double value) {
    draft = draft.copyWith(hostFeePct: value);
    notifyListeners();
  }

  void updateDraftPayoutPreset(int winnerCount) {
    draft = draft.copyWith(
      payoutRules: defaultPayoutRules(winnerCount: winnerCount),
    );
    notifyListeners();
  }

  void updateDraftRules(CompetitionRuleSet rules) {
    draft = draft.copyWith(rules: rules);
    notifyListeners();
  }

  Future<CompetitionSummary?> publishDraft() async {
    if (draft.validationErrors.isNotEmpty) {
      actionError = draft.validationErrors.first;
      notifyListeners();
      return null;
    }
    isPublishing = true;
    actionError = null;
    notifyListeners();
    try {
      CompetitionSummary created = await _api.createCompetition(draft);
      created = await _api.publishCompetition(
        created.id,
        openForJoin: true,
        userId: _currentUserId,
      );
      latestInvite = await _api.createInvite(
        created.id,
        issuedBy: _currentUserId,
        note: '${created.safeFormatLabel} invite',
      );
      selectedCompetition = created;
      selectedFinancials = await _api.fetchFinancials(
        created.id,
        userId: _currentUserId,
      );
      await loadDiscovery();
      draft = draft.copyWith(competitionId: created.id);
      return created;
    } catch (error) {
      actionError = error.toString();
      notifyListeners();
      return null;
    } finally {
      isPublishing = false;
      notifyListeners();
    }
  }

  Future<CompetitionSummary?> joinSelectedCompetition({
    String? inviteCode,
  }) async {
    final CompetitionSummary? current = selectedCompetition;
    if (current == null) {
      return null;
    }
    isJoining = true;
    actionError = null;
    notifyListeners();
    try {
      final CompetitionSummary joined = await _api.joinCompetition(
        current.id,
        userId: _currentUserId,
        userName: _currentUserName,
        inviteCode: inviteCode,
      );
      selectedCompetition = joined;
      selectedFinancials = await _api.fetchFinancials(
        joined.id,
        userId: _currentUserId,
      );
      _replaceCompetition(joined);
      return joined;
    } catch (error) {
      actionError = error.toString();
      notifyListeners();
      return null;
    } finally {
      isJoining = false;
      notifyListeners();
    }
  }

  Future<CompetitionInviteView?> ensureInviteForSelectedCompetition() async {
    final CompetitionSummary? current = selectedCompetition;
    if (current == null) {
      return null;
    }
    if (latestInvite != null) {
      return latestInvite;
    }
    return createInviteForCompetition(current.id);
  }

  Future<CompetitionInviteView?> createInviteForCompetition(
    String competitionId, {
    String? note,
  }) async {
    isCreatingInvite = true;
    actionError = null;
    notifyListeners();
    try {
      latestInvite = await _api.createInvite(
        competitionId,
        issuedBy: _currentUserId,
        note: note,
      );
      return latestInvite;
    } catch (error) {
      actionError = error.toString();
      notifyListeners();
      return null;
    } finally {
      isCreatingInvite = false;
      notifyListeners();
    }
  }

  String formatJoinReason(String? reason) {
    switch (reason) {
      case 'already_joined':
        return 'You are already entered in this creator competition.';
      case 'competition_not_open':
        return 'This creator competition is not open for new entries yet.';
      case 'competition_full':
        return 'This creator competition has reached capacity.';
      case 'invite_required':
        return 'An invite code is required before you can join this creator competition.';
      default:
        return 'Review the published rules and contest status before joining.';
    }
  }

  void _syncSelectedFromList() {
    final CompetitionSummary? current = selectedCompetition;
    if (current == null) {
      return;
    }
    final int index = competitions.indexWhere(
      (CompetitionSummary item) => item.id == current.id,
    );
    if (index == -1) {
      return;
    }
    selectedCompetition = competitions[index];
  }

  void _replaceCompetition(CompetitionSummary next) {
    final int index = competitions.indexWhere(
      (CompetitionSummary item) => item.id == next.id,
    );
    if (index == -1) {
      competitions = <CompetitionSummary>[next, ...competitions];
    } else {
      final List<CompetitionSummary> updated =
          List<CompetitionSummary>.of(competitions);
      updated[index] = next;
      competitions = updated;
    }
  }
}
