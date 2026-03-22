import '../../shared/data/gte_feature_support.dart';

class StreamerTournamentRewardInput {
  const StreamerTournamentRewardInput({
    required this.title,
    required this.rewardType,
    required this.placementStart,
    required this.placementEnd,
    this.amount,
    this.cosmeticSku,
    this.metadata = const <String, Object?>{},
  });

  final String title;
  final String rewardType;
  final int placementStart;
  final int placementEnd;
  final double? amount;
  final String? cosmeticSku;
  final JsonMap metadata;

  JsonMap toJson() => <String, Object?>{
        'title': title,
        'reward_type': rewardType,
        'placement_start': placementStart,
        'placement_end': placementEnd,
        if (amount != null) 'amount': amount,
        if (cosmeticSku != null) 'cosmetic_sku': cosmeticSku,
        'metadata_json': metadata,
      };
}

class StreamerTournamentCreateRequest {
  const StreamerTournamentCreateRequest({
    required this.title,
    required this.tournamentType,
    this.slug,
    this.description,
    this.maxParticipants = 8,
    this.seasonId,
    this.linkedCompetitionId,
    this.playoffSourceCompetitionId,
    this.startsAt,
    this.endsAt,
    this.qualificationMethods = const <String>[],
    this.topGifterRankLimit,
    this.entryRules = const <String, Object?>{},
    this.metadata = const <String, Object?>{},
    this.rewards = const <StreamerTournamentRewardInput>[],
    this.inviteUserIds = const <String>[],
  });

  final String title;
  final String tournamentType;
  final String? slug;
  final String? description;
  final int maxParticipants;
  final String? seasonId;
  final String? linkedCompetitionId;
  final String? playoffSourceCompetitionId;
  final DateTime? startsAt;
  final DateTime? endsAt;
  final List<String> qualificationMethods;
  final int? topGifterRankLimit;
  final JsonMap entryRules;
  final JsonMap metadata;
  final List<StreamerTournamentRewardInput> rewards;
  final List<String> inviteUserIds;

  JsonMap toJson() => <String, Object?>{
        'title': title,
        'tournament_type': tournamentType,
        if (slug != null) 'slug': slug,
        if (description != null) 'description': description,
        'max_participants': maxParticipants,
        if (seasonId != null) 'season_id': seasonId,
        if (linkedCompetitionId != null)
          'linked_competition_id': linkedCompetitionId,
        if (playoffSourceCompetitionId != null)
          'playoff_source_competition_id': playoffSourceCompetitionId,
        if (startsAt != null) 'starts_at': startsAt!.toUtc().toIso8601String(),
        if (endsAt != null) 'ends_at': endsAt!.toUtc().toIso8601String(),
        'qualification_methods': qualificationMethods,
        if (topGifterRankLimit != null)
          'top_gifter_rank_limit': topGifterRankLimit,
        'entry_rules_json': entryRules,
        'metadata_json': metadata,
        'rewards': rewards
            .map((StreamerTournamentRewardInput item) => item.toJson())
            .toList(growable: false),
        'invite_user_ids': inviteUserIds,
      };
}

class StreamerTournamentUpdateRequest {
  const StreamerTournamentUpdateRequest({
    this.title,
    this.description,
    this.maxParticipants,
    this.seasonId,
    this.linkedCompetitionId,
    this.playoffSourceCompetitionId,
    this.startsAt,
    this.endsAt,
    this.qualificationMethods,
    this.topGifterRankLimit,
    this.entryRules,
    this.metadata,
  });

  final String? title;
  final String? description;
  final int? maxParticipants;
  final String? seasonId;
  final String? linkedCompetitionId;
  final String? playoffSourceCompetitionId;
  final DateTime? startsAt;
  final DateTime? endsAt;
  final List<String>? qualificationMethods;
  final int? topGifterRankLimit;
  final JsonMap? entryRules;
  final JsonMap? metadata;

  JsonMap toJson() => compactQuery(<String, Object?>{
        'title': title,
        'description': description,
        'max_participants': maxParticipants,
        'season_id': seasonId,
        'linked_competition_id': linkedCompetitionId,
        'playoff_source_competition_id': playoffSourceCompetitionId,
        'starts_at': startsAt?.toUtc().toIso8601String(),
        'ends_at': endsAt?.toUtc().toIso8601String(),
        'qualification_methods': qualificationMethods,
        'top_gifter_rank_limit': topGifterRankLimit,
        'entry_rules_json': entryRules,
        'metadata_json': metadata,
      });
}

class StreamerTournamentRewardPlanReplaceRequest {
  const StreamerTournamentRewardPlanReplaceRequest({
    required this.rewards,
  });

  final List<StreamerTournamentRewardInput> rewards;

  JsonMap toJson() => <String, Object?>{
        'rewards': rewards
            .map((StreamerTournamentRewardInput item) => item.toJson())
            .toList(growable: false),
      };
}

class StreamerTournamentInviteCreateRequest {
  const StreamerTournamentInviteCreateRequest({
    required this.userId,
    this.note,
    this.metadata = const <String, Object?>{},
  });

  final String userId;
  final String? note;
  final JsonMap metadata;

  JsonMap toJson() => <String, Object?>{
        'user_id': userId,
        if (note != null) 'note': note,
        'metadata_json': metadata,
      };
}

class StreamerTournamentJoinRequest {
  const StreamerTournamentJoinRequest({
    this.qualificationSourceHint,
    this.metadata = const <String, Object?>{},
  });

  final String? qualificationSourceHint;
  final JsonMap metadata;

  JsonMap toJson() => <String, Object?>{
        if (qualificationSourceHint != null)
          'qualification_source_hint': qualificationSourceHint,
        'metadata_json': metadata,
      };
}

class StreamerTournamentPublishRequest {
  const StreamerTournamentPublishRequest({
    this.submissionNotes,
  });

  final String? submissionNotes;

  JsonMap toJson() => compactQuery(<String, Object?>{
        'submission_notes': submissionNotes,
      });
}

class StreamerTournamentReviewRequest {
  const StreamerTournamentReviewRequest({
    required this.approve,
    this.notes,
  });

  final bool approve;
  final String? notes;

  JsonMap toJson() => <String, Object?>{
        'approve': approve,
        if (notes != null) 'notes': notes,
      };
}

class StreamerTournamentPolicyUpsertRequest {
  const StreamerTournamentPolicyUpsertRequest({
    this.rewardCoinApprovalLimit = 500,
    this.rewardCreditApprovalLimit = 5000,
    this.maxCosmeticRewardsWithoutReview = 10,
    this.maxRewardSlots = 12,
    this.maxInvitesPerTournament = 64,
    this.topGifterRankLimit = 25,
    this.active = true,
    this.config = const <String, Object?>{},
  });

  final double rewardCoinApprovalLimit;
  final double rewardCreditApprovalLimit;
  final int maxCosmeticRewardsWithoutReview;
  final int maxRewardSlots;
  final int maxInvitesPerTournament;
  final int topGifterRankLimit;
  final bool active;
  final JsonMap config;

  JsonMap toJson() => <String, Object?>{
        'reward_coin_approval_limit': rewardCoinApprovalLimit,
        'reward_credit_approval_limit': rewardCreditApprovalLimit,
        'max_cosmetic_rewards_without_review': maxCosmeticRewardsWithoutReview,
        'max_reward_slots': maxRewardSlots,
        'max_invites_per_tournament': maxInvitesPerTournament,
        'top_gifter_rank_limit': topGifterRankLimit,
        'active': active,
        'config_json': config,
      };
}

class StreamerTournamentRiskReviewRequest {
  const StreamerTournamentRiskReviewRequest({
    required this.action,
    this.notes,
  });

  final String action;
  final String? notes;

  JsonMap toJson() => <String, Object?>{
        'action': action,
        if (notes != null) 'notes': notes,
      };
}

class StreamerTournamentSettlementPlacement {
  const StreamerTournamentSettlementPlacement({
    required this.userId,
    required this.placement,
    this.note,
  });

  final String userId;
  final int placement;
  final String? note;

  JsonMap toJson() => <String, Object?>{
        'user_id': userId,
        'placement': placement,
        if (note != null) 'note': note,
      };
}

class StreamerTournamentSettleRequest {
  const StreamerTournamentSettleRequest({
    required this.placements,
    this.note,
  });

  final List<StreamerTournamentSettlementPlacement> placements;
  final String? note;

  JsonMap toJson() => <String, Object?>{
        'placements': placements
            .map((StreamerTournamentSettlementPlacement item) => item.toJson())
            .toList(growable: false),
        if (note != null) 'note': note,
      };
}

class StreamerTournamentRiskSignalsQuery {
  const StreamerTournamentRiskSignalsQuery();

  Map<String, Object?> toQuery() => const <String, Object?>{};
}

class StreamerTournamentPolicy {
  const StreamerTournamentPolicy._(this.raw);

  final JsonMap raw;

  factory StreamerTournamentPolicy.fromJson(Object? value) {
    return StreamerTournamentPolicy._(
      jsonMap(value, label: 'streamer tournament policy'),
    );
  }

  String get id => stringValue(raw['id']);
  String get policyKey => stringValue(raw['policy_key']);
  double get rewardCoinApprovalLimit =>
      numberValue(raw['reward_coin_approval_limit']);
  double get rewardCreditApprovalLimit =>
      numberValue(raw['reward_credit_approval_limit']);
  int get maxCosmeticRewardsWithoutReview =>
      intValue(raw['max_cosmetic_rewards_without_review']);
  int get maxRewardSlots => intValue(raw['max_reward_slots']);
  int get maxInvitesPerTournament =>
      intValue(raw['max_invites_per_tournament']);
  int get topGifterRankLimit => intValue(raw['top_gifter_rank_limit']);
  bool get active => boolValue(raw['active']);
  JsonMap get config =>
      jsonMap(raw['config_json'], fallback: const <String, Object?>{});
}

class StreamerTournamentRiskSignal {
  const StreamerTournamentRiskSignal._(this.raw);

  final JsonMap raw;

  factory StreamerTournamentRiskSignal.fromJson(Object? value) {
    return StreamerTournamentRiskSignal._(
      jsonMap(value, label: 'streamer tournament risk signal'),
    );
  }

  String get id => stringValue(raw['id']);
  String get tournamentId => stringValue(raw['tournament_id']);
  String get signalKey => stringValue(raw['signal_key']);
  String get severity => stringValue(raw['severity']);
  String get status => stringValue(raw['status']);
  String get summary => stringValue(raw['summary']);
  String? get detail => stringOrNullValue(raw['detail']);
  DateTime? get detectedAt => dateTimeValue(raw['detected_at']);
  DateTime? get reviewedAt => dateTimeValue(raw['reviewed_at']);
  String? get reviewedByUserId => stringOrNullValue(raw['reviewed_by_user_id']);
  JsonMap get metadata =>
      jsonMap(raw['metadata_json'], fallback: const <String, Object?>{});
}

class StreamerTournament {
  const StreamerTournament._(this.raw);

  final JsonMap raw;

  factory StreamerTournament.fromJson(Object? value) {
    return StreamerTournament._(
      jsonMap(value, label: 'streamer tournament'),
    );
  }

  String get id => stringValue(raw['id']);
  String get hostUserId => stringValue(raw['host_user_id']);
  String get creatorProfileId => stringValue(raw['creator_profile_id']);
  String get creatorClubId => stringValue(raw['creator_club_id']);
  String? get seasonId => stringOrNullValue(raw['season_id']);
  String? get linkedCompetitionId =>
      stringOrNullValue(raw['linked_competition_id']);
  String? get playoffSourceCompetitionId =>
      stringOrNullValue(raw['playoff_source_competition_id']);
  String get slug => stringValue(raw['slug']);
  String get title => stringValue(raw['title']);
  String? get description => stringOrNullValue(raw['description']);
  String get tournamentType => stringValue(raw['tournament_type']);
  String get status => stringValue(raw['status']);
  String get approvalStatus => stringValue(raw['approval_status']);
  int get maxParticipants => intValue(raw['max_participants']);
  bool get requiresAdminApproval => boolValue(raw['requires_admin_approval']);
  bool get highRewardFlag => boolValue(raw['high_reward_flag']);
  DateTime? get startsAt => dateTimeValue(raw['starts_at']);
  DateTime? get endsAt => dateTimeValue(raw['ends_at']);
  DateTime? get submittedAt => dateTimeValue(raw['submitted_at']);
  DateTime? get approvedAt => dateTimeValue(raw['approved_at']);
  DateTime? get rejectedAt => dateTimeValue(raw['rejected_at']);
  DateTime? get completedAt => dateTimeValue(raw['completed_at']);
  String? get approvedByUserId => stringOrNullValue(raw['approved_by_user_id']);
  String? get rejectedByUserId => stringOrNullValue(raw['rejected_by_user_id']);
  String? get submissionNotes => stringOrNullValue(raw['submission_notes']);
  String? get approvalNotes => stringOrNullValue(raw['approval_notes']);
  JsonMap get entryRules =>
      jsonMap(raw['entry_rules_json'], fallback: const <String, Object?>{});
  JsonMap get metadata =>
      jsonMap(raw['metadata_json'], fallback: const <String, Object?>{});
  List<JsonMap> get rewards =>
      jsonMapList(raw['rewards'], label: 'streamer tournament rewards');
  List<JsonMap> get invites =>
      jsonMapList(raw['invites'], label: 'streamer tournament invites');
  List<JsonMap> get entries =>
      jsonMapList(raw['entries'], label: 'streamer tournament entries');
  List<JsonMap> get openRiskSignals => jsonMapList(
        raw['open_risk_signals'],
        label: 'streamer tournament open risk signals',
      );
}

class StreamerTournamentList {
  const StreamerTournamentList({
    required this.tournaments,
  });

  const StreamerTournamentList.empty()
      : tournaments = const <StreamerTournament>[];

  final List<StreamerTournament> tournaments;

  factory StreamerTournamentList.fromJson(Object? value) {
    final JsonMap json = jsonMap(value, label: 'streamer tournament list');
    return StreamerTournamentList(
      tournaments: parseList(
        json['tournaments'],
        StreamerTournament.fromJson,
        label: 'streamer tournaments',
      ),
    );
  }
}

class StreamerTournamentSettlement {
  const StreamerTournamentSettlement._(this.raw);

  final JsonMap raw;

  factory StreamerTournamentSettlement.fromJson(Object? value) {
    return StreamerTournamentSettlement._(
      jsonMap(value, label: 'streamer tournament settlement'),
    );
  }

  StreamerTournament get tournament =>
      StreamerTournament.fromJson(raw['tournament']);
  List<JsonMap> get grants =>
      jsonMapList(raw['grants'], label: 'streamer tournament reward grants');
}
