import '../../../data/gte_api_repository.dart';
import '../../../data/gte_authed_api.dart';
import '../../../data/gte_models.dart';
import '../../shell/domain/gtex_surface_state.dart';
import 'creator_dtos.dart';

abstract class ICreatorRepository {
  Future<CreatorSurfaceState<CreatorProfileDto>> getProfile();
  Future<CreatorSurfaceState<List<CampaignDto>>> getCampaigns();
  Future<CreatorSurfaceState<CampaignDto>> getCampaignDetail(String id);
  Future<CreatorSurfaceState<CampaignDto>> createCampaign(
    CreateCampaignRequest request,
  );
  Future<CreatorSurfaceState<List<SponsoredClipDto>>> getClips();
  Future<CreatorSurfaceState<void>> submitClip(SubmitClipRequest request);
  Future<CreatorSurfaceState<CreatorAnalyticsDto>> getAnalytics(
    AnalyticsPeriod period,
  );
  Future<CreatorSurfaceState<CreatorWalletDto>> getWallet();
  Future<CreatorSurfaceState<CreatorWithdrawalReceiptDto>> requestWithdrawal(
    CreatorWithdrawalRequest request,
  );
  Future<CreatorSurfaceState<List<SettlementDto>>> getSettlements();
  Future<CreatorSurfaceState<List<ModerationInboxItemDto>>>
  getModerationInbox();
  Stream<CreatorWsEvent> subscribeToCreatorEvents();
}

class CreatorApiRepository implements ICreatorRepository {
  const CreatorApiRepository({required this.client});

  final GteAuthedApi client;

  @override
  Future<CreatorSurfaceState<CreatorProfileDto>> getProfile() async {
    try {
      final Map<String, dynamic> payload = await client.getMap(
        '/api/v2/creator/profile',
      );
      final Object? profilePayload = GteJson.value(payload, const <String>[
        'profile',
      ]);
      return _stateFromContract<CreatorProfileDto>(
        payload,
        data:
            profilePayload == null
                ? null
                : CreatorProfileDto.fromSummaryJson(payload),
        contractName: 'creator profile',
        confirmedMessage:
            'Creator profile loaded from /api/v2/creator/profile.',
        emptyMessage: 'Creator profile contract returned no profile.',
        missingDataIsBlocked: true,
      );
    } on Object catch (error) {
      return _stateFromError<CreatorProfileDto>(
        error,
        contractName: 'creator profile',
      );
    }
  }

  @override
  Future<CreatorSurfaceState<List<CampaignDto>>> getCampaigns() async {
    try {
      final Map<String, dynamic> payload = await client.getMap(
        '/api/v2/creator/campaigns',
      );
      final List<CampaignDto> campaigns = GteJson.typedList<CampaignDto>(
        payload,
        const <String>['campaigns'],
        CampaignDto.fromJson,
      );
      return _stateFromContract<List<CampaignDto>>(
        payload,
        data: campaigns,
        contractName: 'creator campaigns',
        confirmedMessage:
            'Creator campaigns loaded from /api/v2/creator/campaigns.',
        emptyMessage: 'No creator campaigns returned by backend.',
      );
    } on Object catch (error) {
      return _stateFromError<List<CampaignDto>>(
        error,
        contractName: 'creator campaigns',
        degradedData: const <CampaignDto>[],
      );
    }
  }

  @override
  Future<CreatorSurfaceState<CampaignDto>> getCampaignDetail(String id) async {
    final String targetId = id.trim();
    if (targetId.isEmpty) {
      return CreatorSurfaceState<CampaignDto>.blocked(
        message: 'Campaign detail is blocked without a campaign id.',
        blockedReason: 'creator.campaign.id_missing',
      );
    }
    try {
      final Map<String, dynamic> payload = await client.getMap(
        '/api/v2/creator/campaigns/$targetId',
      );
      final Object? campaignPayload = GteJson.value(payload, const <String>[
        'campaign',
      ]);
      return _stateFromContract<CampaignDto>(
        payload,
        data:
            campaignPayload == null
                ? null
                : CampaignDto.fromJson(campaignPayload),
        contractName: 'creator campaign detail',
        confirmedMessage:
            'Campaign detail loaded from /api/v2/creator/campaigns/$targetId.',
        emptyMessage: 'Creator campaign detail returned no campaign.',
        missingDataIsBlocked: true,
      );
    } on Object catch (error) {
      return _stateFromError<CampaignDto>(
        error,
        contractName: 'creator campaign detail',
      );
    }
  }

  @override
  Future<CreatorSurfaceState<CampaignDto>> createCampaign(
    CreateCampaignRequest request,
  ) async {
    if (!request.hasAuditRef) {
      return CreatorSurfaceState<CampaignDto>.blocked(
        message: 'Campaign creation is blocked without an audit ref.',
        blockedReason: 'creator.audit_ref_missing',
      );
    }
    try {
      final Map<String, Object?> payload = _asMap(
        await client.post('/api/v2/creator/campaigns', body: request.toJson()),
      );
      final Object? campaignPayload = GteJson.value(payload, const <String>[
        'campaign',
      ]);
      return _stateFromContract<CampaignDto>(
        payload,
        data:
            campaignPayload == null
                ? null
                : CampaignDto.fromJson(campaignPayload),
        contractName: 'creator campaign creation',
        confirmedMessage: 'Campaign creation confirmed by backend.',
        emptyMessage: 'Campaign creation returned no campaign payload.',
        missingDataIsBlocked: true,
        fallbackAuditRef: request.auditRef,
      );
    } on Object catch (error) {
      return _stateFromError<CampaignDto>(
        error,
        contractName: 'creator campaign creation',
        fallbackAuditRef: request.auditRef,
      );
    }
  }

  @override
  Future<CreatorSurfaceState<List<SponsoredClipDto>>> getClips() async {
    try {
      final Map<String, dynamic> payload = await client.getMap(
        '/api/v2/creator/clips',
      );
      final List<SponsoredClipDto> clips = GteJson.typedList<SponsoredClipDto>(
        payload,
        const <String>['clips'],
        SponsoredClipDto.fromJson,
      );
      return _stateFromContract<List<SponsoredClipDto>>(
        payload,
        data: clips,
        contractName: 'creator sponsored clips',
        confirmedMessage: 'Sponsored clips loaded from /api/v2/creator/clips.',
        emptyMessage: 'No sponsored clips returned by backend.',
      );
    } on Object catch (error) {
      return _stateFromError<List<SponsoredClipDto>>(
        error,
        contractName: 'creator sponsored clips',
        degradedData: const <SponsoredClipDto>[],
      );
    }
  }

  @override
  Future<CreatorSurfaceState<void>> submitClip(
    SubmitClipRequest request,
  ) async {
    if (!request.hasAuditRef) {
      return CreatorSurfaceState<void>.blocked(
        message: 'Clip submission is blocked without an audit ref.',
        blockedReason: 'creator.audit_ref_missing',
      );
    }
    try {
      final Map<String, Object?> payload = _asMap(
        await client.post('/api/v2/creator/clips', body: request.toJson()),
      );
      return _stateFromContract<void>(
        payload,
        contractName: 'creator clip submission',
        confirmedMessage: 'Clip submission confirmed by backend.',
        emptyMessage: 'Clip submission returned no confirmation payload.',
        allowNullData: true,
        fallbackAuditRef: request.auditRef,
      );
    } on Object catch (error) {
      return _stateFromError<void>(
        error,
        contractName: 'creator clip submission',
        fallbackAuditRef: request.auditRef,
      );
    }
  }

  @override
  Future<CreatorSurfaceState<CreatorAnalyticsDto>> getAnalytics(
    AnalyticsPeriod period,
  ) async {
    try {
      final Map<String, dynamic> payload = await client.getMap(
        '/api/v2/creators/me/insights',
        query: <String, Object?>{'period': period.queryValue},
      );
      final CreatorAnalyticsDto analytics =
          CreatorAnalyticsDto.fromInsightsJson(payload, period: period);
      if (!analytics.hasModuleAnalyticsContract) {
        return CreatorSurfaceState<CreatorAnalyticsDto>.degraded(
          data: analytics,
          message:
              'Creator insights are available, but Module 7 audience analytics fields are not present.',
        );
      }
      return CreatorSurfaceState<CreatorAnalyticsDto>.confirmed(
        analytics,
        message: 'Creator analytics loaded from backend insights.',
      );
    } on Object catch (error) {
      return _stateFromError<CreatorAnalyticsDto>(
        error,
        contractName: 'creator analytics',
      );
    }
  }

  @override
  Future<CreatorSurfaceState<CreatorWalletDto>> getWallet() async {
    try {
      final Map<String, dynamic> payload = await client.getMap(
        '/api/v2/creator/wallet',
      );
      final CreatorWalletDto wallet = CreatorWalletDto.fromFinanceJson(payload);
      if (wallet.balance == null) {
        if (_contractState(payload) != 'confirmed') {
          return _stateFromContract<CreatorWalletDto>(
            payload,
            data: wallet,
            contractName: 'creator wallet',
            confirmedMessage:
                'Creator wallet available balance loaded from backend contract.',
            emptyMessage: 'Creator wallet contract returned no wallet payload.',
          );
        }
        return CreatorSurfaceState<CreatorWalletDto>.blocked(
          data: wallet,
          message:
              'Creator wallet is blocked because backend available balance is null or absent.',
          blockedReason: 'creator.wallet.available_balance_missing',
        );
      }
      return _stateFromContract<CreatorWalletDto>(
        payload,
        data: wallet,
        contractName: 'creator wallet',
        confirmedMessage:
            'Creator wallet available balance loaded from backend contract.',
        emptyMessage: 'Creator wallet contract returned no wallet payload.',
      );
    } on Object catch (error) {
      return _stateFromError<CreatorWalletDto>(
        error,
        contractName: 'creator wallet',
      );
    }
  }

  @override
  Future<CreatorSurfaceState<CreatorWithdrawalReceiptDto>> requestWithdrawal(
    CreatorWithdrawalRequest request,
  ) async {
    if (!request.hasAuditRef) {
      return CreatorSurfaceState<CreatorWithdrawalReceiptDto>.blocked(
        message: 'Creator withdrawal is blocked without an audit ref.',
        blockedReason: 'creator.audit_ref_missing',
      );
    }
    final CreatorSurfaceState<CreatorWalletDto> walletState = await getWallet();
    final CreatorWalletDto? wallet = walletState.data;
    if (wallet == null || wallet.balance == null) {
      return CreatorSurfaceState<CreatorWithdrawalReceiptDto>.blocked(
        message:
            'Creator withdrawal is blocked until backend available balance is returned.',
        blockedReason: 'creator.withdrawal.available_balance_missing',
        auditRef: request.auditRef,
      );
    }
    if (!wallet.canWithdraw(request.amount)) {
      return CreatorSurfaceState<CreatorWithdrawalReceiptDto>.blocked(
        message:
            'Creator withdrawal is blocked because the request exceeds backend available balance.',
        blockedReason: 'creator.withdrawal.exceeds_available_balance',
        auditRef: request.auditRef,
      );
    }
    if ((request.destinationReference ?? '').trim().isEmpty) {
      return CreatorSurfaceState<CreatorWithdrawalReceiptDto>.blocked(
        message:
            'Creator withdrawal is blocked until backend payout destination reference is supplied.',
        blockedReason: 'creator.withdrawal.destination_missing',
        auditRef: request.auditRef,
      );
    }
    try {
      final Map<String, Object?> payload = _asMap(
        await client.post(
          '/api/v2/creator/wallet/withdraw',
          body: request.toJson(),
        ),
      );
      return _stateFromContract<CreatorWithdrawalReceiptDto>(
        payload,
        data: CreatorWithdrawalReceiptDto.fromJson(payload),
        contractName: 'creator withdrawal',
        confirmedMessage: 'Creator withdrawal confirmed by backend.',
        emptyMessage: 'Creator withdrawal returned no receipt.',
        fallbackAuditRef: request.auditRef,
      );
    } on Object catch (error) {
      return _stateFromError<CreatorWithdrawalReceiptDto>(
        error,
        contractName: 'creator withdrawal',
        fallbackAuditRef: request.auditRef,
      );
    }
  }

  @override
  Future<CreatorSurfaceState<List<SettlementDto>>> getSettlements() async {
    try {
      final Map<String, dynamic> payload = await client.getMap(
        '/api/v2/creator/settlements',
      );
      final List<SettlementDto> settlements = GteJson.typedList<SettlementDto>(
        payload,
        const <String>['settlements'],
        SettlementDto.fromJson,
      );
      return _stateFromContract<List<SettlementDto>>(
        payload,
        data: settlements,
        contractName: 'creator settlements',
        confirmedMessage:
            'Creator settlements loaded from /api/v2/creator/settlements.',
        emptyMessage: 'No creator settlements returned by backend.',
      );
    } on Object catch (error) {
      return _stateFromError<List<SettlementDto>>(
        error,
        contractName: 'creator settlements',
        degradedData: const <SettlementDto>[],
      );
    }
  }

  @override
  Future<CreatorSurfaceState<List<ModerationInboxItemDto>>>
  getModerationInbox() async {
    try {
      final Map<String, dynamic> payload = await client.getMap(
        '/api/v2/creator/moderation',
      );
      final List<ModerationInboxItemDto> items =
          GteJson.typedList<ModerationInboxItemDto>(payload, const <String>[
            'items',
          ], ModerationInboxItemDto.fromJson);
      return _stateFromContract<List<ModerationInboxItemDto>>(
        payload,
        data: items,
        contractName: 'creator moderation inbox',
        confirmedMessage:
            'Creator moderation inbox loaded from /api/v2/creator/moderation.',
        emptyMessage: 'No moderation inbox items returned by backend.',
      );
    } on Object catch (error) {
      return _stateFromError<List<ModerationInboxItemDto>>(
        error,
        contractName: 'creator moderation inbox',
        degradedData: const <ModerationInboxItemDto>[],
      );
    }
  }

  @override
  Stream<CreatorWsEvent> subscribeToCreatorEvents() {
    return const Stream<CreatorWsEvent>.empty();
  }

  CreatorSurfaceState<T> _stateFromError<T>(
    Object error, {
    required String contractName,
    T? degradedData,
    String? fallbackAuditRef,
  }) {
    if (error is GteApiException) {
      if (error.type == GteApiErrorType.unauthorized) {
        return CreatorSurfaceState<T>.blocked(
          message:
              'The $contractName contract requires an authenticated creator session.',
          blockedReason: 'creator.auth_required',
          auditRef: fallbackAuditRef,
        );
      }
      if (error.statusCode == 409 || error.type == GteApiErrorType.validation) {
        return CreatorSurfaceState<T>.blocked(
          data: degradedData,
          message: error.message,
          blockedReason: error.message,
          auditRef: fallbackAuditRef,
        );
      }
      if (error.type == GteApiErrorType.notFound) {
        return CreatorSurfaceState<T>.degraded(
          data: degradedData,
          message: 'The $contractName backend contract is not mounted.',
          auditRef: fallbackAuditRef,
        );
      }
      if (error.type == GteApiErrorType.parsing) {
        return CreatorSurfaceState<T>.degraded(
          data: degradedData,
          message: 'The $contractName payload is missing required fields.',
          auditRef: fallbackAuditRef,
        );
      }
    }
    return CreatorSurfaceState<T>.degraded(
      data: degradedData,
      message:
          'The $contractName surface is degraded by the current backend response.',
      auditRef: fallbackAuditRef,
    );
  }

  CreatorSurfaceState<T> _stateFromContract<T>(
    Map<String, Object?> payload, {
    T? data,
    required String contractName,
    required String confirmedMessage,
    required String emptyMessage,
    bool missingDataIsBlocked = false,
    bool allowNullData = false,
    String? fallbackAuditRef,
  }) {
    final String state = _contractState(payload);
    final String? auditRef = _contractAuditRef(payload) ?? fallbackAuditRef;
    final String reason =
        _contractReason(payload) ??
        switch (state) {
          'blocked' => 'The $contractName contract is blocked by backend.',
          'degraded' => 'The $contractName contract is degraded by backend.',
          'empty' => emptyMessage,
          _ => confirmedMessage,
        };

    if (state == 'blocked') {
      return CreatorSurfaceState<T>.blocked(
        data: data,
        message: reason,
        blockedReason: reason,
        auditRef: auditRef,
      );
    }
    if (state == 'degraded') {
      return CreatorSurfaceState<T>.degraded(
        data: data,
        message: reason,
        auditRef: auditRef,
      );
    }
    if (state == 'empty') {
      return CreatorSurfaceState<T>.empty(
        message: emptyMessage,
        auditRef: auditRef,
      );
    }
    if (data == null && allowNullData) {
      return CreatorSurfaceState<T>(
        state: GtexSurfaceState.confirmed,
        message: confirmedMessage,
        auditRef: auditRef,
      );
    }
    if (data == null && missingDataIsBlocked) {
      return CreatorSurfaceState<T>.blocked(
        message:
            'The $contractName contract did not return required backend data.',
        blockedReason:
            'creator.${contractName.replaceAll(' ', '_')}.required_data_missing',
        auditRef: auditRef,
      );
    }
    if (data == null) {
      return CreatorSurfaceState<T>.degraded(
        message:
            'The $contractName contract did not return required backend data.',
        auditRef: auditRef,
      );
    }
    return CreatorSurfaceState<T>.confirmed(
      data,
      message: confirmedMessage,
      auditRef: auditRef,
    );
  }

  Map<String, Object?> _asMap(Object? value) {
    return GteJson.map(value);
  }

  String _contractState(Map<String, Object?> payload) {
    final Object? raw = GteJson.value(payload, const <String>[
      'state',
      'status',
    ]);
    final String normalized = raw?.toString().trim().toLowerCase() ?? '';
    return switch (normalized) {
      'blocked' => 'blocked',
      'degraded' => 'degraded',
      'empty' => 'empty',
      _ => 'confirmed',
    };
  }

  String? _contractReason(Map<String, Object?> payload) {
    final List<String> reasons =
        GteJson.typedList<String>(
          payload,
          const <String>['gap_reasons', 'gapReasons'],
          (Object? value) => value?.toString() ?? '',
        ).where((String value) => value.trim().isNotEmpty).toList();
    return GteJson.stringOrNull(payload, const <String>[
          'blocked_reason',
          'blockedReason',
          'degraded_reason',
          'degradedReason',
          'reason',
          'message',
        ]) ??
        (reasons.isEmpty ? null : reasons.join(' '));
  }

  String? _contractAuditRef(Map<String, Object?> payload) {
    return GteJson.stringOrNull(payload, const <String>[
      'audit_reference',
      'auditReference',
      'audit_ref',
      'auditRef',
    ]);
  }
}
