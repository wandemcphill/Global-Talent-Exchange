import '../../../data/gte_models.dart';
import '../../shell/domain/gtex_surface_state.dart';

class CreatorSurfaceState<T> {
  const CreatorSurfaceState({
    required this.state,
    required this.message,
    this.data,
    this.blockedReason,
    this.auditRef,
  });

  factory CreatorSurfaceState.confirmed(
    T data, {
    String message = 'Creator surface confirmed by backend.',
    String? auditRef,
  }) {
    return CreatorSurfaceState<T>(
      state: GtexSurfaceState.confirmed,
      data: data,
      message: message,
      auditRef: auditRef,
    );
  }

  factory CreatorSurfaceState.degraded({
    T? data,
    required String message,
    String? auditRef,
  }) {
    return CreatorSurfaceState<T>(
      state: GtexSurfaceState.degraded,
      data: data,
      message: message,
      auditRef: auditRef,
    );
  }

  factory CreatorSurfaceState.blocked({
    T? data,
    required String message,
    String? blockedReason,
    String? auditRef,
  }) {
    return CreatorSurfaceState<T>(
      state: GtexSurfaceState.blocked,
      data: data,
      message: message,
      blockedReason: blockedReason ?? message,
      auditRef: auditRef,
    );
  }

  factory CreatorSurfaceState.empty({
    required String message,
    String? auditRef,
  }) {
    return CreatorSurfaceState<T>(
      state: GtexSurfaceState.empty,
      message: message,
      auditRef: auditRef,
    );
  }

  final GtexSurfaceState state;
  final T? data;
  final String message;
  final String? blockedReason;
  final String? auditRef;

  bool get isBlocked => state == GtexSurfaceState.blocked;
  bool get isDegraded => state == GtexSurfaceState.degraded;
  bool get hasData => data != null;
}

enum CreatorVerificationStatus { verified, pending, suspended, unknown }

extension CreatorVerificationStatusX on CreatorVerificationStatus {
  static CreatorVerificationStatus parse(Object? value) {
    final String normalized = _normalized(value);
    return switch (normalized) {
      'verified' ||
      'approved' ||
      'active' => CreatorVerificationStatus.verified,
      'pending' ||
      'review' ||
      'under_review' => CreatorVerificationStatus.pending,
      'suspended' || 'blocked' => CreatorVerificationStatus.suspended,
      _ => CreatorVerificationStatus.unknown,
    };
  }

  String get label {
    return switch (this) {
      CreatorVerificationStatus.verified => 'Verified',
      CreatorVerificationStatus.pending => 'Pending review',
      CreatorVerificationStatus.suspended => 'Suspended',
      CreatorVerificationStatus.unknown => 'Status unavailable',
    };
  }

  GtexSurfaceState get surfaceState {
    return switch (this) {
      CreatorVerificationStatus.verified => GtexSurfaceState.confirmed,
      CreatorVerificationStatus.pending => GtexSurfaceState.pending,
      CreatorVerificationStatus.suspended => GtexSurfaceState.blocked,
      CreatorVerificationStatus.unknown => GtexSurfaceState.degraded,
    };
  }

  bool get canPublish => this == CreatorVerificationStatus.verified;
}

enum CampaignStatus {
  draft,
  active,
  review,
  approved,
  rejected,
  settled,
  unknown,
}

extension CampaignStatusX on CampaignStatus {
  static CampaignStatus parse(Object? value) {
    final String normalized = _normalized(value);
    return switch (normalized) {
      'draft' => CampaignStatus.draft,
      'active' || 'live' => CampaignStatus.active,
      'review' || 'in_review' || 'pending_review' => CampaignStatus.review,
      'approved' => CampaignStatus.approved,
      'rejected' => CampaignStatus.rejected,
      'settled' || 'paid' => CampaignStatus.settled,
      _ => CampaignStatus.unknown,
    };
  }

  String get label {
    return switch (this) {
      CampaignStatus.draft => 'Draft',
      CampaignStatus.active => 'Active',
      CampaignStatus.review => 'In review',
      CampaignStatus.approved => 'Approved',
      CampaignStatus.rejected => 'Rejected',
      CampaignStatus.settled => 'Settled',
      CampaignStatus.unknown => 'Status unavailable',
    };
  }

  GtexSurfaceState get surfaceState {
    return switch (this) {
      CampaignStatus.draft => GtexSurfaceState.pending,
      CampaignStatus.active ||
      CampaignStatus.approved ||
      CampaignStatus.settled => GtexSurfaceState.confirmed,
      CampaignStatus.review => GtexSurfaceState.pending,
      CampaignStatus.rejected => GtexSurfaceState.blocked,
      CampaignStatus.unknown => GtexSurfaceState.degraded,
    };
  }
}

enum ClipModerationStatus { pending, approved, flagged, rejected, unknown }

extension ClipModerationStatusX on ClipModerationStatus {
  static ClipModerationStatus parse(Object? value) {
    final String normalized = _normalized(value);
    return switch (normalized) {
      'pending' || 'review' || 'under_review' => ClipModerationStatus.pending,
      'approved' || 'live' => ClipModerationStatus.approved,
      'flagged' || 'needs_response' => ClipModerationStatus.flagged,
      'rejected' || 'denied' => ClipModerationStatus.rejected,
      _ => ClipModerationStatus.unknown,
    };
  }

  String get label {
    return switch (this) {
      ClipModerationStatus.pending => 'Under review',
      ClipModerationStatus.approved => 'Live',
      ClipModerationStatus.flagged => 'Flagged',
      ClipModerationStatus.rejected => 'Rejected',
      ClipModerationStatus.unknown => 'Status unavailable',
    };
  }

  String get creatorActionLabel {
    return switch (this) {
      ClipModerationStatus.pending => 'No creator action available',
      ClipModerationStatus.approved => 'View analytics',
      ClipModerationStatus.flagged => 'Respond',
      ClipModerationStatus.rejected => 'Appeal',
      ClipModerationStatus.unknown => 'Contract degraded',
    };
  }

  GtexSurfaceState get surfaceState {
    return switch (this) {
      ClipModerationStatus.pending => GtexSurfaceState.pending,
      ClipModerationStatus.approved => GtexSurfaceState.confirmed,
      ClipModerationStatus.flagged => GtexSurfaceState.degraded,
      ClipModerationStatus.rejected => GtexSurfaceState.blocked,
      ClipModerationStatus.unknown => GtexSurfaceState.degraded,
    };
  }
}

enum WalletTransactionType { credit, debit, hold, release, unknown }

extension WalletTransactionTypeX on WalletTransactionType {
  static WalletTransactionType parse(Object? value) {
    final String normalized = _normalized(value);
    return switch (normalized) {
      'credit' => WalletTransactionType.credit,
      'debit' => WalletTransactionType.debit,
      'hold' || 'reserve' || 'reservation' => WalletTransactionType.hold,
      'release' || 'released' => WalletTransactionType.release,
      _ => WalletTransactionType.unknown,
    };
  }
}

enum AnalyticsPeriod { day, week, month, season }

extension AnalyticsPeriodX on AnalyticsPeriod {
  String get queryValue {
    return switch (this) {
      AnalyticsPeriod.day => 'day',
      AnalyticsPeriod.week => 'week',
      AnalyticsPeriod.month => 'month',
      AnalyticsPeriod.season => 'season',
    };
  }
}

class CreatorProfileDto {
  const CreatorProfileDto({
    required this.id,
    required this.displayName,
    required this.verificationStatus,
    this.totalReach,
    this.engagementRate,
    this.contentCount,
    this.joinedAt,
  });

  factory CreatorProfileDto.fromSummaryJson(Object? value) {
    final Map<String, Object?> root = GteJson.map(value);
    final Map<String, Object?> profile = GteJson.map(
      root,
      keys: const <String>['profile'],
      fallback: root,
    );
    return CreatorProfileDto(
      id: GteJson.string(profile, const <String>[
        'id',
        'creator_id',
        'creatorId',
      ]),
      displayName: GteJson.string(profile, const <String>[
        'display_name',
        'displayName',
        'handle',
      ]),
      verificationStatus: CreatorVerificationStatusX.parse(
        GteJson.value(profile, const <String>[
          'verification_status',
          'verificationStatus',
          'status',
        ]),
      ),
      totalReach: GteJson.integerOrNull(root, const <String>[
        'total_reach',
        'totalReach',
      ]),
      engagementRate: _numberOrNull(root, const <String>[
        'engagement_rate',
        'engagementRate',
      ]),
      contentCount: GteJson.integerOrNull(root, const <String>[
        'content_count',
        'contentCount',
      ]),
      joinedAt: GteJson.dateTimeOrNull(profile, const <String>[
        'joined_at',
        'joinedAt',
        'created_at',
        'createdAt',
      ]),
    );
  }

  final String id;
  final String displayName;
  final CreatorVerificationStatus verificationStatus;
  final int? totalReach;
  final double? engagementRate;
  final int? contentCount;
  final DateTime? joinedAt;
}

class ClipRefDto {
  const ClipRefDto({required this.id, required this.title});

  factory ClipRefDto.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value);
    return ClipRefDto(
      id: GteJson.string(json, const <String>['id', 'clip_id', 'clipId']),
      title: GteJson.string(json, const <String>[
        'title',
        'name',
      ], fallback: 'Sponsored clip'),
    );
  }

  final String id;
  final String title;
}

class CampaignPerformanceDto {
  const CampaignPerformanceDto({
    this.viewCount,
    this.engagementRate,
    this.settlementAmount,
  });

  factory CampaignPerformanceDto.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value);
    return CampaignPerformanceDto(
      viewCount: GteJson.integerOrNull(json, const <String>[
        'view_count',
        'viewCount',
        'views',
      ]),
      engagementRate: _numberOrNull(json, const <String>[
        'engagement_rate',
        'engagementRate',
      ]),
      settlementAmount: _numberOrNull(json, const <String>[
        'settlement_amount',
        'settlementAmount',
      ]),
    );
  }

  final int? viewCount;
  final double? engagementRate;
  final double? settlementAmount;
}

class CampaignDto {
  const CampaignDto({
    required this.id,
    required this.title,
    required this.status,
    this.sponsor,
    this.brief,
    this.budget,
    this.currency,
    this.startDate,
    this.endDate,
    this.clips = const <ClipRefDto>[],
    this.performance,
    this.auditRef,
  });

  factory CampaignDto.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value);
    final Object? performance = GteJson.value(json, const <String>[
      'performance',
      'campaign_performance',
      'campaignPerformance',
    ]);
    return CampaignDto(
      id: GteJson.string(json, const <String>[
        'id',
        'campaign_id',
        'campaignId',
        'competition_id',
        'competitionId',
      ]),
      title: GteJson.string(json, const <String>['title', 'name']),
      sponsor: GteJson.stringOrNull(json, const <String>['sponsor']),
      brief: GteJson.stringOrNull(json, const <String>['brief']),
      budget: _numberOrNull(json, const <String>['budget']),
      currency: GteJson.stringOrNull(json, const <String>['currency']),
      status: CampaignStatusX.parse(
        GteJson.value(json, const <String>[
          'status',
          'campaign_status',
          'campaignStatus',
        ]),
      ),
      startDate: GteJson.dateTimeOrNull(json, const <String>[
        'start_date',
        'startDate',
      ]),
      endDate: GteJson.dateTimeOrNull(json, const <String>[
        'end_date',
        'endDate',
      ]),
      clips: GteJson.typedList<ClipRefDto>(json, const <String>[
        'clips',
      ], ClipRefDto.fromJson),
      performance:
          performance == null
              ? null
              : CampaignPerformanceDto.fromJson(performance),
      auditRef: GteJson.stringOrNull(json, const <String>[
        'audit_ref',
        'auditRef',
      ]),
    );
  }

  final String id;
  final String title;
  final String? sponsor;
  final String? brief;
  final double? budget;
  final String? currency;
  final CampaignStatus status;
  final DateTime? startDate;
  final DateTime? endDate;
  final List<ClipRefDto> clips;
  final CampaignPerformanceDto? performance;
  final String? auditRef;

  bool get hasFullCampaignContract {
    return sponsor != null &&
        brief != null &&
        budget != null &&
        currency != null &&
        status != CampaignStatus.unknown;
  }
}

class SponsoredClipDto {
  const SponsoredClipDto({
    required this.id,
    required this.campaignId,
    required this.title,
    required this.status,
    this.url,
    this.thumbnailUrl,
    this.moderationNote,
    this.publishedAt,
    this.viewCount,
    this.engagementRate,
    this.auditRef,
  });

  factory SponsoredClipDto.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value);
    return SponsoredClipDto(
      id: GteJson.string(json, const <String>['id', 'clip_id', 'clipId']),
      campaignId: GteJson.string(json, const <String>[
        'campaign_id',
        'campaignId',
      ], fallback: ''),
      title: GteJson.string(json, const <String>[
        'title',
        'name',
      ], fallback: 'Sponsored clip'),
      url: GteJson.stringOrNull(json, const <String>['url']),
      thumbnailUrl: GteJson.stringOrNull(json, const <String>[
        'thumbnail_url',
        'thumbnailUrl',
      ]),
      status: ClipModerationStatusX.parse(
        GteJson.value(json, const <String>[
          'status',
          'moderation_state',
          'moderationState',
        ]),
      ),
      moderationNote: GteJson.stringOrNull(json, const <String>[
        'moderation_note',
        'moderationNote',
      ]),
      publishedAt: GteJson.dateTimeOrNull(json, const <String>[
        'published_at',
        'publishedAt',
      ]),
      viewCount: GteJson.integerOrNull(json, const <String>[
        'view_count',
        'viewCount',
      ]),
      engagementRate: _numberOrNull(json, const <String>[
        'engagement_rate',
        'engagementRate',
      ]),
      auditRef: GteJson.stringOrNull(json, const <String>[
        'audit_ref',
        'auditRef',
      ]),
    );
  }

  final String id;
  final String campaignId;
  final String title;
  final String? url;
  final String? thumbnailUrl;
  final ClipModerationStatus status;
  final String? moderationNote;
  final DateTime? publishedAt;
  final int? viewCount;
  final double? engagementRate;
  final String? auditRef;

  bool get canShowPerformance => status == ClipModerationStatus.approved;
}

class CreatorAnalyticsDto {
  const CreatorAnalyticsDto({
    required this.period,
    this.totalViews,
    this.totalEngagement,
    this.followerGrowth,
    this.audienceDemographics = const <String, Object?>{},
    this.topClips = const <ClipRefDto>[],
  });

  factory CreatorAnalyticsDto.fromInsightsJson(
    Object? value, {
    required AnalyticsPeriod period,
  }) {
    final Map<String, Object?> json = GteJson.map(value);
    final Map<String, Object?> creatorMetrics = GteJson.map(
      json,
      keys: const <String>['creator_metrics', 'creatorMetrics'],
      fallback: const <String, Object?>{},
    );
    return CreatorAnalyticsDto(
      period: period,
      totalViews:
          GteJson.integerOrNull(json, const <String>[
            'total_views',
            'totalViews',
          ]) ??
          GteJson.integerOrNull(creatorMetrics, const <String>[
            'total_views',
            'totalViews',
          ]),
      totalEngagement: GteJson.integerOrNull(json, const <String>[
        'total_engagement',
        'totalEngagement',
      ]),
      followerGrowth: _numberOrNull(json, const <String>[
        'follower_growth',
        'followerGrowth',
      ]),
      audienceDemographics: GteJson.map(
        json,
        keys: const <String>['audience_demographics', 'audienceDemographics'],
        fallback: const <String, Object?>{},
      ),
      topClips: GteJson.typedList<ClipRefDto>(json, const <String>[
        'top_clips',
        'topClips',
      ], ClipRefDto.fromJson),
    );
  }

  final AnalyticsPeriod period;
  final int? totalViews;
  final int? totalEngagement;
  final double? followerGrowth;
  final Map<String, Object?> audienceDemographics;
  final List<ClipRefDto> topClips;

  bool get hasModuleAnalyticsContract {
    return totalViews != null ||
        totalEngagement != null ||
        followerGrowth != null ||
        audienceDemographics.isNotEmpty ||
        topClips.isNotEmpty;
  }
}

class WalletBalanceDto {
  const WalletBalanceDto({
    required this.available,
    required this.currency,
    this.reserved,
    this.lastSyncedAt,
  });

  static WalletBalanceDto? fromJsonOrNull(Object? value) {
    final Map<String, Object?> json = GteJson.map(value);
    final bool hasAvailableKey = _containsAnyKey(json, const <String>[
      'available',
      'available_balance',
      'availableBalance',
      'wallet_available_balance',
      'walletAvailableBalance',
      'wallet_available_credit',
      'walletAvailableCredit',
    ]);
    if (!hasAvailableKey) {
      return null;
    }
    final double? available = _numberOrNull(json, const <String>[
      'available',
      'available_balance',
      'availableBalance',
      'wallet_available_balance',
      'walletAvailableBalance',
      'wallet_available_credit',
      'walletAvailableCredit',
    ]);
    if (available == null) {
      return null;
    }
    return WalletBalanceDto(
      available: available,
      reserved: _numberOrNull(json, const <String>[
        'reserved',
        'reserved_balance',
        'reservedBalance',
        'wallet_reserved_balance',
        'walletReservedBalance',
      ]),
      currency: GteJson.string(json, const <String>[
        'currency',
        'wallet_currency',
        'walletCurrency',
      ], fallback: 'credits'),
      lastSyncedAt: GteJson.dateTimeOrNull(json, const <String>[
        'last_synced_at',
        'lastSyncedAt',
      ]),
    );
  }

  final double available;
  final double? reserved;
  final String currency;
  final DateTime? lastSyncedAt;
}

class WalletTransactionDto {
  const WalletTransactionDto({
    required this.id,
    required this.type,
    required this.amount,
    required this.currency,
    required this.reference,
    required this.status,
    this.createdAt,
  });

  factory WalletTransactionDto.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value);
    return WalletTransactionDto(
      id: GteJson.string(json, const <String>['id']),
      type: WalletTransactionTypeX.parse(
        GteJson.value(json, const <String>[
          'type',
          'transaction_type',
          'transactionType',
        ]),
      ),
      amount: GteJson.requiredNumber(json, const <String>['amount']),
      currency: GteJson.string(json, const <String>[
        'currency',
      ], fallback: 'credits'),
      reference: GteJson.string(json, const <String>[
        'reference',
      ], fallback: 'unreferenced'),
      createdAt: GteJson.dateTimeOrNull(json, const <String>[
        'created_at',
        'createdAt',
      ]),
      status: GteJson.string(json, const <String>[
        'status',
      ], fallback: 'posted'),
    );
  }

  final String id;
  final WalletTransactionType type;
  final double amount;
  final String currency;
  final String reference;
  final DateTime? createdAt;
  final String status;
}

class CreatorWalletDto {
  const CreatorWalletDto({
    required this.balance,
    required this.pendingSettlements,
    this.recentTransactions = const <WalletTransactionDto>[],
  });

  factory CreatorWalletDto.fromFinanceJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value);
    return CreatorWalletDto(
      balance: WalletBalanceDto.fromJsonOrNull(json),
      pendingSettlements: GteJson.integer(json, const <String>[
        'pending_settlements',
        'pendingSettlements',
        'pending_withdrawals',
        'pendingWithdrawals',
      ]),
      recentTransactions: GteJson.typedList<WalletTransactionDto>(
        json,
        const <String>['recent_transactions', 'recentTransactions'],
        WalletTransactionDto.fromJson,
      ),
    );
  }

  final WalletBalanceDto? balance;
  final int pendingSettlements;
  final List<WalletTransactionDto> recentTransactions;

  GtexSurfaceState get surfaceState {
    return balance == null
        ? GtexSurfaceState.blocked
        : GtexSurfaceState.confirmed;
  }

  bool canWithdraw(double amount) {
    final WalletBalanceDto? currentBalance = balance;
    if (currentBalance == null) {
      return false;
    }
    return amount > 0 && amount <= currentBalance.available;
  }
}

class SettlementDto {
  const SettlementDto({
    required this.id,
    required this.status,
    required this.amount,
    required this.currency,
    this.auditRef,
  });

  factory SettlementDto.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value);
    return SettlementDto(
      id: GteJson.string(json, const <String>['id', 'settlement_id']),
      status: GteJson.string(json, const <String>['status']),
      amount: GteJson.requiredNumber(json, const <String>['amount']),
      currency: GteJson.string(json, const <String>[
        'currency',
      ], fallback: 'credits'),
      auditRef: GteJson.stringOrNull(json, const <String>[
        'audit_ref',
        'auditRef',
      ]),
    );
  }

  final String id;
  final String status;
  final double amount;
  final String currency;
  final String? auditRef;
}

class ModerationInboxItemDto {
  const ModerationInboxItemDto({
    required this.id,
    required this.clip,
    required this.status,
    this.reason,
    this.updatedAt,
    this.auditRef,
  });

  factory ModerationInboxItemDto.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value);
    final Object? clipJson = GteJson.value(json, const <String>['clip']);
    final SponsoredClipDto clip =
        clipJson == null
            ? SponsoredClipDto.fromJson(json)
            : SponsoredClipDto.fromJson(clipJson);
    return ModerationInboxItemDto(
      id: GteJson.string(json, const <String>['id', 'item_id', 'itemId']),
      clip: clip,
      status: ClipModerationStatusX.parse(
        GteJson.value(json, const <String>[
          'status',
          'moderation_state',
          'moderationState',
        ]),
      ),
      reason: GteJson.stringOrNull(json, const <String>['reason']),
      updatedAt: GteJson.dateTimeOrNull(json, const <String>[
        'updated_at',
        'updatedAt',
      ]),
      auditRef: GteJson.stringOrNull(json, const <String>[
        'audit_ref',
        'auditRef',
      ]),
    );
  }

  final String id;
  final SponsoredClipDto clip;
  final ClipModerationStatus status;
  final String? reason;
  final DateTime? updatedAt;
  final String? auditRef;
}

class CreateCampaignRequest {
  const CreateCampaignRequest({
    required this.title,
    required this.brief,
    required this.auditRef,
    this.sponsor,
    this.budget,
    this.currency,
  });

  final String title;
  final String brief;
  final String? sponsor;
  final double? budget;
  final String? currency;
  final String auditRef;

  bool get hasAuditRef => auditRef.trim().isNotEmpty;

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'title': title,
      'brief': brief,
      if (sponsor != null) 'sponsor': sponsor,
      if (budget != null) 'budget': budget,
      if (currency != null) 'currency': currency,
      'audit_ref': auditRef,
      'audit_event': 'creator.campaign.created',
    };
  }
}

class SubmitClipRequest {
  const SubmitClipRequest({
    required this.campaignId,
    required this.title,
    required this.url,
    required this.auditRef,
  });

  final String campaignId;
  final String title;
  final String url;
  final String auditRef;

  bool get hasAuditRef => auditRef.trim().isNotEmpty;

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'campaign_id': campaignId,
      'title': title,
      'url': url,
      'audit_ref': auditRef,
      'audit_event': 'creator.clip.submitted',
    };
  }
}

class CreatorWithdrawalRequest {
  const CreatorWithdrawalRequest({
    required this.amount,
    required this.currency,
    required this.method,
    required this.auditRef,
  });

  final double amount;
  final String currency;
  final String method;
  final String auditRef;

  bool get hasAuditRef => auditRef.trim().isNotEmpty;

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'amount': amount,
      'currency': currency,
      'method': method,
      'audit_ref': auditRef,
      'audit_event': 'creator.withdrawal.requested',
    };
  }
}

class CreatorWithdrawalReceiptDto {
  const CreatorWithdrawalReceiptDto({
    required this.id,
    required this.status,
    required this.auditRef,
  });

  factory CreatorWithdrawalReceiptDto.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value);
    return CreatorWithdrawalReceiptDto(
      id: GteJson.string(json, const <String>['id', 'withdrawal_id']),
      status: GteJson.string(json, const <String>['status']),
      auditRef: GteJson.string(json, const <String>['audit_ref', 'auditRef']),
    );
  }

  final String id;
  final String status;
  final String auditRef;
}

sealed class CreatorWsEvent {
  const CreatorWsEvent();
}

class CreatorCampaignUpdated extends CreatorWsEvent {
  const CreatorCampaignUpdated(this.campaign);

  final CampaignDto campaign;
}

class CreatorClipModerationEvent extends CreatorWsEvent {
  const CreatorClipModerationEvent(this.clip);

  final SponsoredClipDto clip;
}

class CreatorWalletUpdated extends CreatorWsEvent {
  const CreatorWalletUpdated(this.wallet);

  final CreatorWalletDto wallet;
}

class CreatorSettlementUpdated extends CreatorWsEvent {
  const CreatorSettlementUpdated(this.settlement);

  final SettlementDto settlement;
}

bool _containsAnyKey(Map<String, Object?> json, List<String> keys) {
  return keys.any(json.containsKey);
}

double? _numberOrNull(Map<String, Object?> json, List<String> keys) {
  final Object? value = GteJson.value(json, keys);
  if (value == null) {
    return null;
  }
  if (value is num) {
    return value.toDouble();
  }
  return double.tryParse(value.toString());
}

String _normalized(Object? value) {
  return value?.toString().trim().toLowerCase().replaceAll('-', '_') ?? '';
}
