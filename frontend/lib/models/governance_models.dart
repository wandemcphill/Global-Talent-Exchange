import 'package:gte_frontend/data/gte_models.dart';

class GovernanceProposal {
  const GovernanceProposal({
    required this.id,
    required this.clubId,
    required this.proposerUserId,
    required this.scope,
    required this.status,
    required this.title,
    required this.summary,
    required this.category,
    required this.votingStartsAtIso,
    required this.votingEndsAtIso,
    required this.minimumTokensRequired,
    required this.quorumTokenWeight,
    required this.yesWeight,
    required this.noWeight,
    required this.abstainWeight,
    required this.uniqueVoterCount,
    required this.resultSummary,
    required this.metadata,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String? clubId;
  final String proposerUserId;
  final String scope;
  final String status;
  final String title;
  final String summary;
  final String category;
  final String? votingStartsAtIso;
  final String? votingEndsAtIso;
  final int minimumTokensRequired;
  final int quorumTokenWeight;
  final int yesWeight;
  final int noWeight;
  final int abstainWeight;
  final int uniqueVoterCount;
  final String? resultSummary;
  final Map<String, Object?> metadata;
  final DateTime createdAt;
  final DateTime updatedAt;

  factory GovernanceProposal.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'governance proposal');
    return GovernanceProposal(
      id: GteJson.string(json, <String>['id']),
      clubId: GteJson.stringOrNull(json, <String>['club_id', 'clubId']),
      proposerUserId:
          GteJson.string(json, <String>['proposer_user_id', 'proposerUserId']),
      scope: GteJson.string(json, <String>['scope'], fallback: 'club'),
      status: GteJson.string(json, <String>['status'], fallback: 'open'),
      title: GteJson.string(json, <String>['title']),
      summary: GteJson.string(json, <String>['summary']),
      category: GteJson.string(json, <String>['category'], fallback: 'general'),
      votingStartsAtIso: GteJson.stringOrNull(
          json, <String>['voting_starts_at_iso', 'votingStartsAtIso']),
      votingEndsAtIso: GteJson.stringOrNull(
          json, <String>['voting_ends_at_iso', 'votingEndsAtIso']),
      minimumTokensRequired: GteJson.integer(
          json, <String>['minimum_tokens_required', 'minimumTokensRequired'],
          fallback: 0),
      quorumTokenWeight: GteJson.integer(
          json, <String>['quorum_token_weight', 'quorumTokenWeight'],
          fallback: 0),
      yesWeight: GteJson.integer(json, <String>['yes_weight', 'yesWeight'], fallback: 0),
      noWeight: GteJson.integer(json, <String>['no_weight', 'noWeight'], fallback: 0),
      abstainWeight: GteJson.integer(
          json, <String>['abstain_weight', 'abstainWeight'],
          fallback: 0),
      uniqueVoterCount: GteJson.integer(
          json, <String>['unique_voter_count', 'uniqueVoterCount'],
          fallback: 0),
      resultSummary:
          GteJson.stringOrNull(json, <String>['result_summary', 'resultSummary']),
      metadata: GteJson.map(
          json, <String>['metadata_json', 'metadataJson', 'metadata'],
          fallback: const <String, Object?>{}),
      createdAt: GteJson.dateTime(json, <String>['created_at', 'createdAt']),
      updatedAt: GteJson.dateTime(json, <String>['updated_at', 'updatedAt']),
    );
  }
}

class GovernanceVote {
  const GovernanceVote({
    required this.id,
    required this.proposalId,
    required this.voterUserId,
    required this.clubId,
    required this.choice,
    required this.tokenWeight,
    required this.influenceWeight,
    required this.comment,
    required this.isProxyVote,
    required this.metadata,
    required this.createdAt,
    required this.updatedAt,
  });

  final String id;
  final String proposalId;
  final String voterUserId;
  final String? clubId;
  final String choice;
  final int tokenWeight;
  final int influenceWeight;
  final String? comment;
  final bool isProxyVote;
  final Map<String, Object?> metadata;
  final DateTime createdAt;
  final DateTime updatedAt;

  factory GovernanceVote.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'governance vote');
    return GovernanceVote(
      id: GteJson.string(json, <String>['id']),
      proposalId: GteJson.string(json, <String>['proposal_id', 'proposalId']),
      voterUserId: GteJson.string(json, <String>['voter_user_id', 'voterUserId']),
      clubId: GteJson.stringOrNull(json, <String>['club_id', 'clubId']),
      choice: GteJson.string(json, <String>['choice'], fallback: 'abstain'),
      tokenWeight:
          GteJson.integer(json, <String>['token_weight', 'tokenWeight'], fallback: 0),
      influenceWeight: GteJson.integer(
          json, <String>['influence_weight', 'influenceWeight'],
          fallback: 0),
      comment: GteJson.stringOrNull(json, <String>['comment']),
      isProxyVote: GteJson.boolean(
          json, <String>['is_proxy_vote', 'isProxyVote'],
          fallback: false),
      metadata: GteJson.map(
          json, <String>['metadata_json', 'metadataJson', 'metadata'],
          fallback: const <String, Object?>{}),
      createdAt: GteJson.dateTime(json, <String>['created_at', 'createdAt']),
      updatedAt: GteJson.dateTime(json, <String>['updated_at', 'updatedAt']),
    );
  }
}

class GovernanceProposalDetail {
  const GovernanceProposalDetail({
    required this.proposal,
    required this.votes,
    required this.myVote,
    required this.userEligible,
    required this.eligibilityReason,
  });

  final GovernanceProposal proposal;
  final List<GovernanceVote> votes;
  final GovernanceVote? myVote;
  final bool userEligible;
  final String? eligibilityReason;

  factory GovernanceProposalDetail.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'governance proposal detail');
    return GovernanceProposalDetail(
      proposal:
          GovernanceProposal.fromJson(GteJson.value(json, <String>['proposal'])),
      votes: GteJson.typedList(
        json,
        <String>['votes'],
        GovernanceVote.fromJson,
      ),
      myVote: GteJson.value(json, <String>['my_vote', 'myVote']) == null
          ? null
          : GovernanceVote.fromJson(
              GteJson.value(json, <String>['my_vote', 'myVote'])),
      userEligible:
          GteJson.boolean(json, <String>['user_eligible', 'userEligible'], fallback: false),
      eligibilityReason:
          GteJson.stringOrNull(json, <String>['eligibility_reason', 'eligibilityReason']),
    );
  }
}

class GovernanceOverview {
  const GovernanceOverview({
    required this.openProposalCount,
    required this.clubsWithTokens,
    required this.eligibleClubIds,
    required this.recentVoteCount,
  });

  final int openProposalCount;
  final int clubsWithTokens;
  final List<String> eligibleClubIds;
  final int recentVoteCount;

  factory GovernanceOverview.fromJson(Object? value) {
    final Map<String, Object?> json =
        GteJson.map(value, label: 'governance overview');
    return GovernanceOverview(
      openProposalCount: GteJson.integer(
          json, <String>['open_proposal_count', 'openProposalCount'],
          fallback: 0),
      clubsWithTokens:
          GteJson.integer(json, <String>['clubs_with_tokens', 'clubsWithTokens'], fallback: 0),
      eligibleClubIds: GteJson.typedList(
        json,
        <String>['eligible_club_ids', 'eligibleClubIds'],
        (Object? value) => value?.toString() ?? '',
      ),
      recentVoteCount: GteJson.integer(
          json, <String>['recent_vote_count', 'recentVoteCount'],
          fallback: 0),
    );
  }
}
