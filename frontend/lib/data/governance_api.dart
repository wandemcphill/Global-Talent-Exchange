import 'gte_api_repository.dart';
import 'gte_authed_api.dart';
import 'gte_http_transport.dart';
import '../models/governance_models.dart';

class GovernanceApi {
  GovernanceApi({
    required this.client,
    required this.fixtures,
  });

  final GteAuthedApi client;
  final _GovernanceFixtures fixtures;

  factory GovernanceApi.standard({
    required String baseUrl,
    required String? accessToken,
    GteBackendMode mode = GteBackendMode.liveThenFixture,
  }) {
    return GovernanceApi(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: mode),
        transport: GteHttpTransport(),
        accessToken: accessToken,
        mode: mode,
      ),
      fixtures: _GovernanceFixtures.seed(),
    );
  }

  factory GovernanceApi.fixture() {
    return GovernanceApi(
      client: GteAuthedApi(
        config: const GteRepositoryConfig(
          baseUrl: 'http://127.0.0.1:8000',
          mode: GteBackendMode.fixture,
        ),
        transport: GteHttpTransport(),
        accessToken: 'fixture-token',
        mode: GteBackendMode.fixture,
      ),
      fixtures: _GovernanceFixtures.seed(),
    );
  }

  Future<List<GovernanceProposal>> listProposals({String? clubId}) {
    return client.withFallback<List<GovernanceProposal>>(
      () async {
        final Map<String, dynamic> payload = await client.getMap(
          '/governance/proposals',
          query: <String, Object?>{
            if (clubId != null && clubId.isNotEmpty) 'club_id': clubId,
          },
        );
        final List<dynamic> proposals = payload['proposals'] as List<dynamic>? ?? <dynamic>[];
        return proposals
            .map(GovernanceProposal.fromJson)
            .toList(growable: false);
      },
      fixtures.listProposals,
    );
  }

  Future<GovernanceProposalDetail> fetchProposal(String proposalId) {
    return client.withFallback<GovernanceProposalDetail>(
      () async {
        final Map<String, dynamic> payload =
            await client.getMap('/governance/proposals/$proposalId');
        return GovernanceProposalDetail.fromJson(payload);
      },
      () async => fixtures.detail(proposalId),
    );
  }

  Future<GovernanceOverview> fetchOverview() {
    return client.withFallback<GovernanceOverview>(
      () async {
        final Map<String, dynamic> payload =
            await client.getMap('/governance/me/overview');
        return GovernanceOverview.fromJson(payload);
      },
      fixtures.overview,
    );
  }

  Future<GovernanceProposalDetail> vote({
    required String proposalId,
    required String choice,
    String? comment,
  }) {
    return client.withFallback<GovernanceProposalDetail>(
      () async {
        final Object? payload = await client.request(
          'POST',
          '/governance/proposals/$proposalId/vote',
          body: <String, Object?>{
            'choice': choice,
            if (comment != null && comment.trim().isNotEmpty) 'comment': comment.trim(),
          },
        );
        final Map<String, dynamic> map = payload as Map<String, dynamic>? ?? <String, dynamic>{};
        return GovernanceProposalDetail.fromJson(<String, Object?>{
          'proposal': map['proposal'],
          'votes': <Object?>[map['vote']],
          'my_vote': map['vote'],
          'user_eligible': true,
        });
      },
      () async => fixtures.vote(proposalId, choice),
    );
  }

  Future<GovernanceProposal> updateProposalStatus({
    required String proposalId,
    required String status,
    String? resultSummary,
  }) {
    return client.withFallback<GovernanceProposal>(
      () async {
        final Object? payload = await client.request(
          'POST',
          '/admin/governance/proposals/$proposalId/status',
          body: <String, Object?>{
            'status': status,
            if (resultSummary != null) 'result_summary': resultSummary,
          },
        );
        return GovernanceProposal.fromJson(payload);
      },
      () async => fixtures.updateStatus(proposalId, status),
    );
  }
}

class _GovernanceFixtures {
  _GovernanceFixtures(this._proposals);

  final List<GovernanceProposal> _proposals;

  static _GovernanceFixtures seed() {
    final List<GovernanceProposal> proposals = <GovernanceProposal>[
      GovernanceProposal(
        id: 'gov-1',
        clubId: 'club-1',
        proposerUserId: 'user-1',
        scope: 'club',
        status: 'open',
        title: 'Raise academy scouting budget',
        summary: 'Increase academy scouting allocation by 12% for next quarter.',
        category: 'budget',
        votingStartsAtIso: '2026-03-12T10:00:00Z',
        votingEndsAtIso: '2026-03-19T10:00:00Z',
        minimumTokensRequired: 5,
        quorumTokenWeight: 100,
        yesWeight: 45,
        noWeight: 12,
        abstainWeight: 3,
        uniqueVoterCount: 18,
        resultSummary: null,
        metadata: const <String, Object?>{'lane': 'club'},
        createdAt: DateTime.parse('2026-03-12T10:00:00Z'),
        updatedAt: DateTime.parse('2026-03-12T10:00:00Z'),
      ),
    ];
    return _GovernanceFixtures(proposals);
  }

  Future<List<GovernanceProposal>> listProposals() async =>
      List<GovernanceProposal>.of(_proposals, growable: false);

  Future<GovernanceProposalDetail> detail(String proposalId) async {
    final GovernanceProposal proposal =
        _proposals.firstWhere((GovernanceProposal item) => item.id == proposalId);
    return GovernanceProposalDetail(
      proposal: proposal,
      votes: const <GovernanceVote>[],
      myVote: null,
      userEligible: true,
      eligibilityReason: null,
    );
  }

  Future<GovernanceOverview> overview() async {
    return GovernanceOverview(
      openProposalCount: _proposals.length,
      clubsWithTokens: 1,
      eligibleClubIds: const <String>['club-1'],
      recentVoteCount: 4,
    );
  }

  Future<GovernanceProposalDetail> vote(String proposalId, String choice) async {
    final GovernanceProposal proposal =
        _proposals.firstWhere((GovernanceProposal item) => item.id == proposalId);
    return GovernanceProposalDetail(
      proposal: proposal,
      votes: const <GovernanceVote>[],
      myVote: GovernanceVote(
        id: 'vote-1',
        proposalId: proposalId,
        voterUserId: 'user-1',
        clubId: proposal.clubId,
        choice: choice,
        tokenWeight: 10,
        influenceWeight: 10,
        comment: null,
        isProxyVote: false,
        metadata: const <String, Object?>{},
        createdAt: DateTime.now().toUtc(),
        updatedAt: DateTime.now().toUtc(),
      ),
      userEligible: true,
      eligibilityReason: null,
    );
  }

  Future<GovernanceProposal> updateStatus(String proposalId, String status) async {
    final int index =
        _proposals.indexWhere((GovernanceProposal item) => item.id == proposalId);
    if (index == -1) {
      return _proposals.first;
    }
    final GovernanceProposal updated = GovernanceProposal(
      id: _proposals[index].id,
      clubId: _proposals[index].clubId,
      proposerUserId: _proposals[index].proposerUserId,
      scope: _proposals[index].scope,
      status: status,
      title: _proposals[index].title,
      summary: _proposals[index].summary,
      category: _proposals[index].category,
      votingStartsAtIso: _proposals[index].votingStartsAtIso,
      votingEndsAtIso: _proposals[index].votingEndsAtIso,
      minimumTokensRequired: _proposals[index].minimumTokensRequired,
      quorumTokenWeight: _proposals[index].quorumTokenWeight,
      yesWeight: _proposals[index].yesWeight,
      noWeight: _proposals[index].noWeight,
      abstainWeight: _proposals[index].abstainWeight,
      uniqueVoterCount: _proposals[index].uniqueVoterCount,
      resultSummary: 'Closed by admin.',
      metadata: _proposals[index].metadata,
      createdAt: _proposals[index].createdAt,
      updatedAt: DateTime.now().toUtc(),
    );
    _proposals[index] = updated;
    return updated;
  }
}
