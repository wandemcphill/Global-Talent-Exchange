import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/gte_authed_api.dart';
import '../shared/data/feature_api_provider.dart';
import '../shared/data/gte_feature_support.dart';

class FederationRecord {
  const FederationRecord({
    required this.id,
    required this.name,
    required this.rankingScore,
    required this.reputationScore,
    required this.audienceSize,
    required this.treasuryBalance,
    required this.memberCount,
    required this.isPublic,
    required this.defaultRealityMode,
  });

  final String id;
  final String name;
  final double rankingScore;
  final double reputationScore;
  final int audienceSize;
  final double treasuryBalance;
  final int memberCount;
  final bool isPublic;
  final String defaultRealityMode;

  factory FederationRecord.fromJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'federation');
    return FederationRecord(
      id: stringValue(json['id']),
      name: stringValue(json['name']),
      rankingScore: numberValue(json['ranking_score']),
      reputationScore: numberValue(json['reputation_score']),
      audienceSize: intValue(json['audience_size']),
      treasuryBalance: numberValue(json['treasury_balance']),
      memberCount:
          jsonMapList(json['members_json'], label: 'federation members').length,
      isPublic: boolValue(json['is_public'], fallback: true),
      defaultRealityMode: stringValue(
        json['default_reality_mode'],
        fallback: 'hybrid',
      ),
    );
  }
}

class FederationRankingRecord {
  const FederationRankingRecord({
    required this.federationId,
    required this.name,
    required this.rankingScore,
    required this.reputationScore,
    required this.audienceSize,
    required this.activityScore,
    required this.competitivenessScore,
  });

  final String federationId;
  final String name;
  final double rankingScore;
  final double reputationScore;
  final int audienceSize;
  final double activityScore;
  final double competitivenessScore;

  factory FederationRankingRecord.fromJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'federation ranking');
    return FederationRankingRecord(
      federationId: stringValue(json['federation_id']),
      name: stringValue(json['name']),
      rankingScore: numberValue(json['ranking_score']),
      reputationScore: numberValue(json['reputation_score']),
      audienceSize: intValue(json['audience_size']),
      activityScore: numberValue(json['activity_score']),
      competitivenessScore: numberValue(json['competitiveness_score']),
    );
  }
}

class RegionalTournamentRecord {
  const RegionalTournamentRecord({
    required this.regionCode,
    required this.regionLabel,
    required this.federationCount,
    required this.activeLeagueCount,
    required this.totalMemberClubs,
  });

  final String regionCode;
  final String regionLabel;
  final int federationCount;
  final int activeLeagueCount;
  final int totalMemberClubs;

  factory RegionalTournamentRecord.fromJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'regional tournament');
    return RegionalTournamentRecord(
      regionCode: stringValue(json['region_code']),
      regionLabel: stringValue(json['region_label']),
      federationCount: intValue(json['federation_count']),
      activeLeagueCount: intValue(json['active_league_count']),
      totalMemberClubs: intValue(json['total_member_clubs']),
    );
  }
}

class FederationHubData {
  const FederationHubData({
    required this.federations,
    required this.rankings,
    required this.regionalTournaments,
  });

  final List<FederationRecord> federations;
  final List<FederationRankingRecord> rankings;
  final List<RegionalTournamentRecord> regionalTournaments;
}

class FederationDetailData {
  const FederationDetailData({
    required this.federation,
    required this.dashboard,
    required this.governance,
    required this.narratives,
  });

  final FederationRecord federation;
  final JsonMap dashboard;
  final JsonMap governance;
  final List<JsonMap> narratives;
}

class FederationMembershipResult {
  const FederationMembershipResult({
    required this.status,
    required this.role,
    required this.violations,
  });

  final String status;
  final String role;
  final List<String> violations;

  factory FederationMembershipResult.fromJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'federation membership');
    final JsonMap metadata =
        jsonMapOrNull(json['metadata_json']) ?? const <String, Object?>{};
    return FederationMembershipResult(
      status: stringValue(json['status'], fallback: 'pending'),
      role: stringValue(json['role'], fallback: 'member_club'),
      violations: stringListValue(metadata['entry_violations']),
    );
  }
}

class FederationProposalActionResult {
  const FederationProposalActionResult({
    required this.id,
    required this.title,
    required this.status,
    this.voteType,
  });

  final String id;
  final String title;
  final String status;
  final String? voteType;

  factory FederationProposalActionResult.fromProposalJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'federation proposal action');
    return FederationProposalActionResult(
      id: stringValue(json['id']),
      title: stringValue(json['title'], fallback: 'Proposal'),
      status: stringValue(json['status'], fallback: 'open'),
      voteType: null,
    );
  }

  factory FederationProposalActionResult.fromVoteJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'federation vote action');
    return FederationProposalActionResult(
      id: stringValue(json['proposal_id']),
      title: stringValue(json['proposal_title'], fallback: 'Proposal'),
      status: stringValue(json['status'], fallback: 'open'),
      voteType: stringValue(json['vote_type'], fallback: ''),
    );
  }
}

class FederationsApi {
  const FederationsApi({required this.client});

  final GteAuthedApi client;

  Future<List<FederationRecord>> listFederations() async {
    final List<dynamic> payload = await client.getList(
      '/federations',
      auth: false,
    );
    return payload.map(FederationRecord.fromJson).toList(growable: false);
  }

  Future<List<FederationRankingRecord>> listRankings() async {
    final List<dynamic> payload = await client.getList(
      '/federations/rankings',
      auth: false,
    );
    return payload
        .map(FederationRankingRecord.fromJson)
        .toList(growable: false);
  }

  Future<List<RegionalTournamentRecord>> listRegionalTournaments() async {
    final List<dynamic> payload = await client.getList(
      '/federations/regional-tournaments',
      auth: false,
    );
    return payload
        .map(RegionalTournamentRecord.fromJson)
        .toList(growable: false);
  }

  Future<JsonMap> fetchDashboard(String federationId) {
    return client.getMap('/federations/$federationId', auth: false);
  }

  Future<JsonMap> fetchGovernance(String federationId) {
    return client.getMap('/federations/$federationId/governance', auth: false);
  }

  Future<List<JsonMap>> fetchNarratives(String federationId) async {
    final List<dynamic> payload = await client.getList(
      '/federations/$federationId/narratives',
      auth: false,
    );
    return payload
        .map((dynamic item) => jsonMap(item, label: 'federation narrative'))
        .toList(growable: false);
  }

  Future<FederationMembershipResult> createMembership({
    required String federationId,
    required String clubId,
    String? userId,
  }) async {
    final Object? payload = await client.post(
      '/federations/$federationId/memberships',
      body: <String, Object?>{
        'club_id': clubId,
        'user_id': userId,
        'role': 'member_club',
        'auto_activate': true,
        'metadata_json': <String, Object?>{'source': 'federations_hub'},
      },
    );
    return FederationMembershipResult.fromJson(payload);
  }

  Future<FederationProposalActionResult> createProposal({
    required String federationId,
    required String title,
    required String summary,
    String proposalType = 'rule_change',
    String? leagueId,
    DateTime? votingEndsAt,
  }) async {
    final Object? payload = await client.post(
      '/federations/$federationId/proposals',
      body: <String, Object?>{
        'league_id': leagueId,
        'proposal_type': proposalType,
        'title': title,
        'summary': summary,
        if (votingEndsAt != null)
          'voting_ends_at': votingEndsAt.toUtc().toIso8601String(),
        'payload_json': const <String, Object?>{},
        'metadata_json': const <String, Object?>{'source': 'federations_hub'},
      },
    );
    return FederationProposalActionResult.fromProposalJson(payload);
  }

  Future<FederationProposalActionResult> castProposalVote({
    required String proposalId,
    required String voteType,
    String? comment,
  }) async {
    final Object? payload = await client.post(
      '/federations/proposals/$proposalId/votes',
      body: <String, Object?>{
        'vote_type': voteType,
        if (comment != null && comment.trim().isNotEmpty)
          'comment': comment.trim(),
      },
    );
    final JsonMap vote = jsonMap(payload, label: 'federation vote');
    return FederationProposalActionResult.fromVoteJson(<String, Object?>{
      ...vote,
      'proposal_id': stringValue(vote['proposal_id'], fallback: proposalId),
      'proposal_title': stringValue(
        vote['proposal_title'],
        fallback: 'Proposal',
      ),
      'status': 'open',
      'vote_type': stringValue(vote['vote_type']),
    });
  }
}

final Provider<FederationsApi> federationsApiProvider =
    createFeatureApiProvider<FederationsApi>(
      (GteAuthedApi client) => FederationsApi(client: client),
    );

final FutureProvider<FederationHubData> federationsHubProvider =
    FutureProvider<FederationHubData>((Ref ref) async {
      final FederationsApi api = ref.watch(federationsApiProvider);
      final Future<List<FederationRecord>> federationsFuture =
          api.listFederations();
      final Future<List<FederationRankingRecord>> rankingsFuture =
          api.listRankings();
      final Future<List<RegionalTournamentRecord>> regionalFuture =
          api.listRegionalTournaments();
      return FederationHubData(
        federations: await federationsFuture,
        rankings: await rankingsFuture,
        regionalTournaments: await regionalFuture,
      );
    });

final dynamic federationDetailProvider = FutureProvider.autoDispose.family<
  FederationDetailData,
  String
>((Ref ref, String federationId) async {
  final FederationsApi api = ref.watch(federationsApiProvider);
  final FederationHubData hub = await ref.watch(federationsHubProvider.future);
  FederationRecord? federation;
  for (final FederationRecord item in hub.federations) {
    if (item.id == federationId) {
      federation = item;
      break;
    }
  }
  federation ??= (await api.listFederations()).firstWhere(
    (FederationRecord item) => item.id == federationId,
  );
  final Future<JsonMap> dashboardFuture = api.fetchDashboard(federationId);
  final Future<JsonMap> governanceFuture = api.fetchGovernance(federationId);
  final Future<List<JsonMap>> narrativesFuture = api.fetchNarratives(
    federationId,
  );
  return FederationDetailData(
    federation: federation,
    dashboard: await dashboardFuture,
    governance: await governanceFuture,
    narratives: await narrativesFuture,
  );
});
