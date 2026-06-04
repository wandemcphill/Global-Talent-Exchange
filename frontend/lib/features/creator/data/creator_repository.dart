import '../../../data/gte_api_repository.dart';
import '../../../data/gte_authed_api.dart';
import '../../../data/gte_models.dart';
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
        '/api/v2/creators/me/summary',
      );
      return CreatorSurfaceState<CreatorProfileDto>.confirmed(
        CreatorProfileDto.fromSummaryJson(payload),
        message: 'Creator profile loaded from /api/v2/creators/me/summary.',
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
      final List<dynamic> payload = await client.getList(
        '/api/v2/creators/me/competitions',
      );
      final List<CampaignDto> campaigns = payload
          .map(CampaignDto.fromJson)
          .toList(growable: false);
      return CreatorSurfaceState<List<CampaignDto>>.degraded(
        data: campaigns,
        message:
            'Creator competitions are available, but the Module 7 campaign contract is not mounted yet.',
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
    final CreatorSurfaceState<List<CampaignDto>> campaigns =
        await getCampaigns();
    final String targetId = id.trim();
    for (final CampaignDto campaign
        in campaigns.data ?? const <CampaignDto>[]) {
      if (campaign.id == targetId) {
        return CreatorSurfaceState<CampaignDto>.degraded(
          data: campaign,
          message:
              'Campaign detail is projected from the creator competitions contract; campaign detail fields are not fully mounted.',
          auditRef: campaign.auditRef,
        );
      }
    }
    return CreatorSurfaceState<CampaignDto>.blocked(
      message:
          'Campaign detail is blocked because no backend detail contract returned campaign "$targetId".',
      blockedReason: 'creator.campaign.detail_unavailable',
    );
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
    return CreatorSurfaceState<CampaignDto>.blocked(
      message:
          'Campaign creation is blocked because the backend create-campaign contract is not mounted.',
      blockedReason: 'creator.campaign.create_unavailable',
      auditRef: request.auditRef,
    );
  }

  @override
  Future<CreatorSurfaceState<List<SponsoredClipDto>>> getClips() async {
    return CreatorSurfaceState<List<SponsoredClipDto>>.degraded(
      data: const <SponsoredClipDto>[],
      message:
          'Sponsored clips are degraded because no creator clips contract is mounted.',
    );
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
    return CreatorSurfaceState<void>.blocked(
      message:
          'Clip submission is blocked because the backend submit-clip contract is not mounted.',
      blockedReason: 'creator.clip.submit_unavailable',
      auditRef: request.auditRef,
    );
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
        '/api/v2/creators/me/finance',
      );
      final CreatorWalletDto wallet = CreatorWalletDto.fromFinanceJson(payload);
      if (wallet.balance == null) {
        return CreatorSurfaceState<CreatorWalletDto>.blocked(
          data: wallet,
          message:
              'Creator wallet is blocked because backend available balance is null or absent.',
          blockedReason: 'creator.wallet.available_balance_missing',
        );
      }
      return CreatorSurfaceState<CreatorWalletDto>.confirmed(
        wallet,
        message:
            'Creator wallet available balance loaded from backend finance payload.',
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
    return CreatorSurfaceState<CreatorWithdrawalReceiptDto>.blocked(
      message:
          'Creator withdrawal is blocked because the creator-specific withdrawal contract is not mounted.',
      blockedReason: 'creator.withdrawal.contract_unavailable',
      auditRef: request.auditRef,
    );
  }

  @override
  Future<CreatorSurfaceState<List<SettlementDto>>> getSettlements() async {
    return CreatorSurfaceState<List<SettlementDto>>.degraded(
      data: const <SettlementDto>[],
      message:
          'Creator settlements are degraded because no creator settlement contract is mounted.',
    );
  }

  @override
  Future<CreatorSurfaceState<List<ModerationInboxItemDto>>>
  getModerationInbox() async {
    return CreatorSurfaceState<List<ModerationInboxItemDto>>.degraded(
      data: const <ModerationInboxItemDto>[],
      message:
          'Moderation inbox is degraded because no creator moderation contract is mounted.',
    );
  }

  @override
  Stream<CreatorWsEvent> subscribeToCreatorEvents() {
    return const Stream<CreatorWsEvent>.empty();
  }

  CreatorSurfaceState<T> _stateFromError<T>(
    Object error, {
    required String contractName,
    T? degradedData,
  }) {
    if (error is GteApiException) {
      if (error.type == GteApiErrorType.unauthorized) {
        return CreatorSurfaceState<T>.blocked(
          message:
              'The $contractName contract requires an authenticated creator session.',
          blockedReason: 'creator.auth_required',
        );
      }
      if (error.type == GteApiErrorType.notFound) {
        return CreatorSurfaceState<T>.degraded(
          data: degradedData,
          message: 'The $contractName backend contract is not mounted.',
        );
      }
      if (error.type == GteApiErrorType.parsing) {
        return CreatorSurfaceState<T>.degraded(
          data: degradedData,
          message: 'The $contractName payload is missing required fields.',
        );
      }
    }
    return CreatorSurfaceState<T>.degraded(
      data: degradedData,
      message:
          'The $contractName surface is degraded by the current backend response.',
    );
  }
}
