import 'gte_api_repository.dart';
import 'gte_authed_api.dart';
import 'gte_api_contract.dart';
import 'gte_http_transport.dart';
import 'gte_models.dart';
import '../models/creator_application_models.dart';
import '../models/moderation_models.dart';
import '../models/risk_ops_models.dart';

class AdminCommandCenterApi {
  AdminCommandCenterApi({required this.client});

  final GteAuthedApi client;
  final Map<String, Map<String, String>> _depositActionEndpointsById =
      <String, Map<String, String>>{};

  static const String _paymentQueuePath = '/api/v2/admin/finance/payment-queue';

  factory AdminCommandCenterApi.standard({
    required String baseUrl,
    required String accessToken,
    GteBackendMode mode = GteBackendMode.live,
  }) {
    return AdminCommandCenterApi(
      client: GteAuthedApi(
        config: GteRepositoryConfig(baseUrl: baseUrl, mode: mode),
        transport: GteHttpTransport(),
        accessToken: accessToken,
        mode: mode,
      ),
    );
  }

  Future<GteTreasurySettings> fetchTreasurySettings() async {
    final Map<String, dynamic> payload = await client.getMap(
      '/api/admin/treasury/settings',
    );
    return GteTreasurySettings.fromJson(payload);
  }

  Future<GteTreasurySettings> updateTreasurySettings(
    GteTreasurySettingsUpdate request,
  ) async {
    final Object? payload = await client.request(
      'PUT',
      '/api/admin/treasury/settings',
      body: request.toJson(),
    );
    return GteTreasurySettings.fromJson(payload);
  }

  Future<List<GteTreasuryBankAccount>> listTreasuryBankAccounts() async {
    final List<dynamic> payload = await client.getList(
      '/api/admin/treasury/bank-accounts',
    );
    return payload.map(GteTreasuryBankAccount.fromJson).toList(growable: false);
  }

  Future<GteTreasuryBankAccount> createTreasuryBankAccount(
    GteTreasuryBankAccountCreate request,
  ) async {
    final Object? payload = await client.post(
      '/api/admin/treasury/bank-accounts',
      body: request.toJson(),
    );
    return GteTreasuryBankAccount.fromJson(payload);
  }

  Future<GteTreasuryBankAccount> updateTreasuryBankAccount(
    String accountId,
    GteTreasuryBankAccountUpdate request,
  ) async {
    final Object? payload = await client.request(
      'PUT',
      '/api/admin/treasury/bank-accounts/$accountId',
      body: request.toJson(),
    );
    return GteTreasuryBankAccount.fromJson(payload);
  }

  Future<GteAdminQueuePage<GteAdminDeposit>> fetchAdminDeposits({
    int limit = 20,
    int offset = 0,
    String? status,
    String? query,
  }) async {
    final Object? payload = await _requestPaymentQueue(
      'GET',
      _paymentQueuePath,
      query: <String, Object?>{
        'limit': limit,
        'offset': offset,
        if (_paymentQueueTabForStatus(status) case final String tab) 'tab': tab,
        if (query != null && query.trim().isNotEmpty) 'q': query.trim(),
      },
    );
    return _adminDepositPageFromPaymentQueue(
      payload,
      limit: limit,
      offset: offset,
      status: status,
    );
  }

  Future<void> adminReviewDeposit(
    String depositId, {
    String? adminNotes,
  }) async {
    await _runDepositQueueAction(
      depositId,
      preferredActions: const <String>['review', 'reinstate'],
      body: _notesPayload(adminNotes),
    );
  }

  Future<void> adminConfirmDeposit(
    String depositId, {
    String? adminNotes,
  }) async {
    await _runDepositQueueAction(
      depositId,
      preferredActions: const <String>['approve'],
      body: _notesPayload(adminNotes),
    );
  }

  Future<void> adminRejectDeposit(
    String depositId, {
    String? adminNotes,
  }) async {
    await _runDepositQueueAction(
      depositId,
      preferredActions: const <String>['reject'],
      body: _notesPayload(adminNotes),
    );
  }

  Future<GteAdminQueuePage<GteAdminWithdrawal>> fetchAdminWithdrawals({
    int limit = 20,
    int offset = 0,
    String? status,
    String? query,
  }) async {
    final Map<String, dynamic> payload = await client.getMap(
      '/api/admin/treasury/withdrawals',
      query: <String, Object?>{
        'limit': limit,
        'offset': offset,
        if (status != null && status.trim().isNotEmpty) 'status': status.trim(),
        if (query != null && query.trim().isNotEmpty) 'q': query.trim(),
      },
    );
    return GteAdminQueuePage<GteAdminWithdrawal>.fromJson(
      payload,
      GteAdminWithdrawal.fromJson,
    );
  }

  Future<GteAdminQueuePage<GteAdminKyc>> fetchAdminKyc({
    int limit = 20,
    int offset = 0,
    String? status,
    String? query,
  }) async {
    final Map<String, dynamic> payload = await client.getMap(
      '/api/admin/treasury/kyc',
      query: <String, Object?>{
        'limit': limit,
        'offset': offset,
        if (status != null && status.trim().isNotEmpty) 'status': status.trim(),
        if (query != null && query.trim().isNotEmpty) 'q': query.trim(),
      },
    );
    return GteAdminQueuePage<GteAdminKyc>.fromJson(
      payload,
      GteAdminKyc.fromJson,
    );
  }

  Future<GteAdminQueuePage<GteDispute>> fetchAdminDisputes({
    int limit = 20,
    int offset = 0,
    String? status,
    String? query,
  }) async {
    final Map<String, dynamic> payload = await client.getMap(
      '/api/admin/treasury/disputes',
      query: <String, Object?>{
        'limit': limit,
        'offset': offset,
        if (status != null && status.trim().isNotEmpty) 'status': status.trim(),
        if (query != null && query.trim().isNotEmpty) 'q': query.trim(),
      },
    );
    return GteAdminQueuePage<GteDispute>.fromJson(payload, GteDispute.fromJson);
  }

  Future<AdminTransferBidReviewFeed> fetchTransferBidReviewFeed() async {
    final Object? payload = await _requestPaymentQueue(
      'GET',
      _paymentQueuePath,
      query: const <String, Object?>{'tab': 'bids', 'limit': 50, 'offset': 0},
    );
    return _transferBidReviewFeedFromPaymentQueue(payload);
  }

  Future<void> adminRunTransferBidAction(
    AdminTransferBid bid, {
    required String action,
    required String adminNotes,
  }) async {
    final String normalizedAction = action.trim().toLowerCase();
    if (normalizedAction.isEmpty) {
      throw const GteApiException(
        type: GteApiErrorType.validation,
        message: 'Choose a bid audit action before submitting.',
      );
    }
    if (bid.availableActions.isNotEmpty &&
        !bid.supportsAction(normalizedAction)) {
      throw GteApiException(
        type: GteApiErrorType.validation,
        message:
            'Backend did not expose $normalizedAction for this bid audit row.',
      );
    }
    final Map<String, Object?>? body = _notesPayload(adminNotes);
    if (body == null) {
      throw const GteApiException(
        type: GteApiErrorType.validation,
        message: 'Admin notes are required for bid audit actions.',
      );
    }
    final String fallbackPath =
        '$_paymentQueuePath/bids/windows/${Uri.encodeComponent(bid.windowId)}/bids/${Uri.encodeComponent(bid.id)}/$normalizedAction';
    await _requestPaymentQueue(
      'POST',
      bid.actionEndpointFor(normalizedAction) ?? fallbackPath,
      body: body,
    );
  }

  AdminTransferBidReviewFeed _transferBidReviewFeedFromPaymentQueue(
    Object? value,
  ) {
    final Map<String, Object?> payload = GteJson.map(
      value,
      label: 'admin payment queue',
    );
    final List<AdminTransferBid> bids = GteJson.list(
      _paymentQueueSectionItems(payload, 'bids'),
      label: 'admin payment queue bid items',
    ).map(AdminTransferBid.fromJson).toList(growable: false);
    final Map<String, AdminTransferWindow> windowsById =
        <String, AdminTransferWindow>{};
    for (final AdminTransferBid bid in bids) {
      windowsById.putIfAbsent(
        bid.windowId,
        () => AdminTransferWindow.fromBidReview(bid),
      );
    }
    return AdminTransferBidReviewFeed(
      windows: windowsById.values.toList(growable: false),
      bids: bids,
    );
  }

  Future<List<ModerationReport>> fetchAdminModerationReports({
    String? status,
    String? priority,
    String? targetType,
  }) async {
    final List<dynamic> payload = await _getListPayload(
      '/api/admin/moderation/reports',
      query: <String, Object?>{
        if (status != null && status.trim().isNotEmpty) 'status': status.trim(),
        if (priority != null && priority.trim().isNotEmpty)
          'priority': priority.trim(),
        if (targetType != null && targetType.trim().isNotEmpty)
          'target_type': targetType.trim(),
      },
    );
    return payload.map(ModerationReport.fromJson).toList(growable: false);
  }

  Future<List<CreatorApplicationView>> fetchAdminCreatorApplications({
    String? status,
  }) async {
    final List<dynamic> payload = await _getListPayload(
      '/api/admin/creator/applications',
      query: <String, Object?>{
        if (status != null && status.trim().isNotEmpty) 'status': status.trim(),
      },
    );
    return payload.map(CreatorApplicationView.fromJson).toList(growable: false);
  }

  Future<RiskOverview> fetchRiskOverview() async {
    final Map<String, dynamic> payload = await client.getMap(
      '/admin/risk-ops/overview',
    );
    return RiskOverview.fromJson(payload);
  }

  Future<List<dynamic>> _getListPayload(
    String path, {
    Map<String, Object?> query = const <String, Object?>{},
  }) async {
    final Object? payload = await client.request('GET', path, query: query);
    if (payload is List) {
      return payload;
    }
    if (payload is Map) {
      final Map<String, Object?> map = Map<String, Object?>.from(payload);
      for (final String key in <String>[
        'items',
        'reports',
        'applications',
        'results',
      ]) {
        final Object? value = map[key];
        if (value is List) {
          return value;
        }
      }
    }
    throw const GteApiException(
      type: GteApiErrorType.parsing,
      message: 'Unexpected queue response shape.',
    );
  }

  Future<AdminPaymentRailsState> fetchPaymentRails() async {
    final Map<String, dynamic> payload = await client.getMap(
      '/api/admin/god-mode/payment-rails',
    );
    return AdminPaymentRailsState.fromJson(payload);
  }

  Future<AdminPaymentRailsState> updatePaymentRails({
    required List<AdminPaymentRail> rails,
    required String reason,
  }) async {
    final Object? payload = await client.request(
      'PUT',
      '/api/admin/god-mode/payment-rails',
      body: <String, Object?>{
        'rails': rails
            .map((AdminPaymentRail rail) => rail.toUpdateJson())
            .toList(growable: false),
        'reason': reason.trim(),
      },
    );
    return AdminPaymentRailsState.fromJson(payload);
  }

  Future<AdminWithdrawalControls> fetchWithdrawalControls() async {
    final Map<String, dynamic> payload = await client.getMap(
      '/api/admin/god-mode/withdrawal-controls',
    );
    return AdminWithdrawalControls.fromJson(payload);
  }

  Future<AdminWithdrawalControls> updateWithdrawalControls({
    required AdminWithdrawalControls controls,
    required String reason,
  }) async {
    final Object? payload = await client.request(
      'PUT',
      '/api/admin/god-mode/withdrawal-controls',
      body: controls.toUpdateJson(reason: reason.trim()),
    );
    return AdminWithdrawalControls.fromJson(payload);
  }

  Future<AdminMarketTopupQuote> quoteMarketTopup({
    required double amount,
    int feeBps = 0,
    String unit = 'coin',
  }) async {
    final Object? payload = await client.post(
      '/api/admin/wallets/market-topups/quote',
      body: <String, Object?>{
        'amount': amount,
        'fee_bps': feeBps,
        'unit': unit,
      },
    );
    return AdminMarketTopupQuote.fromJson(payload);
  }

  Future<AdminMarketTopup> createMarketTopup({
    required String userId,
    required double amount,
    int feeBps = 0,
    String unit = 'coin',
    String sourceScope = 'promotion',
    String? notes,
  }) async {
    final Object? payload = await client.post(
      '/api/admin/wallets/market-topups',
      body: <String, Object?>{
        'user_id': userId.trim(),
        'amount': amount,
        'fee_bps': feeBps,
        'unit': unit,
        'source_scope': sourceScope,
        if (notes != null && notes.trim().isNotEmpty) 'notes': notes.trim(),
      },
    );
    return AdminMarketTopup.fromJson(payload);
  }

  Future<AdminMarketTopup> updateMarketTopupStatus(
    String topupId, {
    required String status,
    String? notes,
  }) async {
    final Object? payload = await client.post(
      '/api/admin/wallets/market-topups/$topupId/status',
      body: <String, Object?>{
        'status': status.trim(),
        if (notes != null && notes.trim().isNotEmpty) 'notes': notes.trim(),
      },
    );
    return AdminMarketTopup.fromJson(payload);
  }

  Future<String> createGtexHostedCompetition({
    required String templateKey,
    required String title,
    String? passcode,
  }) async {
    final Object? payload = await client.post(
      '/api/admin/competitions',
      body: <String, Object?>{
        'name': title.trim(),
        'format':
            templateKey.trim().toLowerCase().contains('cup') ? 'cup' : 'league',
        'visibility':
            passcode != null && passcode.trim().isNotEmpty ? 'gated' : 'public',
        'host_type': 'gtex_hosted',
        'entry_fee': '0.00',
        'buyInAmount': '0.00',
        'capacity': 16,
        'maxPlayers': 16,
        'currency': 'coin',
        'rules':
            'Official GTEX competition. Free entry, published fixtures, standings, results, and prize pool.',
        'specialRules': 'Official GTEX competition. Free entry.',
        if (passcode != null && passcode.trim().isNotEmpty)
          'passcode': passcode.trim(),
      },
    );
    final Map<String, Object?> map =
        payload is Map
            ? Map<String, Object?>.from(payload)
            : const <String, Object?>{};
    return (map['dashboard_summary'] ??
            '${map['name'] ?? title.trim()} created as a GTEX competition.')
        .toString();
  }

  GteAdminQueuePage<GteAdminDeposit> _adminDepositPageFromPaymentQueue(
    Object? value, {
    required int limit,
    required int offset,
    String? status,
  }) {
    final Map<String, Object?> payload = GteJson.map(
      value,
      label: 'admin payment queue',
    );
    final String? normalizedStatus = _normalizeStatusFilter(status);
    final List<Object?> rawItems = <Object?>[
      ..._paymentQueueSectionItems(payload, 'pending'),
      ..._paymentQueueSectionItems(payload, 'approved'),
      ..._paymentQueueSectionItems(payload, 'rejected'),
    ];
    final List<GteAdminDeposit> items = <GteAdminDeposit>[];
    _depositActionEndpointsById.clear();
    for (final Object? rawItem in rawItems) {
      final Map<String, Object?> item = GteJson.map(
        rawItem,
        label: 'admin payment queue deposit',
      );
      _cacheDepositActionEndpoints(item);
      if (normalizedStatus != null &&
          _normalizeStatusFilter(item['status']) != normalizedStatus) {
        continue;
      }
      items.add(GteAdminDeposit.fromJson(item));
    }

    return GteAdminQueuePage<GteAdminDeposit>(
      items: items,
      total:
          _paymentQueueSectionTotal(payload, 'pending') +
          _paymentQueueSectionTotal(payload, 'approved') +
          _paymentQueueSectionTotal(payload, 'rejected'),
      limit: limit,
      offset: offset,
    );
  }

  List<Object?> _paymentQueueSectionItems(
    Map<String, Object?> payload,
    String key,
  ) {
    final Map<String, Object?> section = _paymentQueueSection(payload, key);
    return GteJson.list(
      GteJson.value(section, <String>['items']) ?? const <Object?>[],
      label: 'admin payment queue $key items',
    );
  }

  int _paymentQueueSectionTotal(Map<String, Object?> payload, String key) {
    return GteJson.integer(_paymentQueueSection(payload, key), <String>[
      'total',
    ], fallback: 0);
  }

  Map<String, Object?> _paymentQueueSection(
    Map<String, Object?> payload,
    String key,
  ) {
    final Object? sections = GteJson.value(payload, <String>['sections']);
    if (sections is Map && sections[key] is Map) {
      return Map<String, Object?>.from(sections[key] as Map);
    }
    return GteJson.map(
      GteJson.value(payload, <String>[key]) ?? const <String, Object?>{},
      label: 'admin payment queue $key section',
    );
  }

  void _cacheDepositActionEndpoints(Map<String, Object?> item) {
    final String id = GteJson.string(item, <String>['id'], fallback: '');
    if (id.isEmpty) {
      return;
    }
    final Object? rawEndpoints = GteJson.value(item, <String>[
      'action_endpoints',
      'actionEndpoints',
    ]);
    if (rawEndpoints is! Map) {
      return;
    }
    final Map<String, String> endpoints = <String, String>{};
    rawEndpoints.forEach((Object? key, Object? value) {
      final String action = key?.toString().trim().toLowerCase() ?? '';
      final String path = value?.toString().trim() ?? '';
      if (action.isNotEmpty && path.isNotEmpty) {
        endpoints[action] = path;
      }
    });
    if (endpoints.isNotEmpty) {
      _depositActionEndpointsById[id] = endpoints;
    }
  }

  String? _paymentQueueTabForStatus(String? status) {
    final String? normalized = _normalizeStatusFilter(status);
    if (normalized == null) {
      return null;
    }
    switch (normalized) {
      case 'payment_submitted':
      case 'under_review':
      case 'disputed':
        return 'pending';
      case 'confirmed':
        return 'approved';
      case 'rejected':
        return 'rejected';
    }
    return null;
  }

  String? _normalizeStatusFilter(Object? status) {
    final String normalized = status?.toString().trim().toLowerCase() ?? '';
    return normalized.isEmpty ? null : normalized;
  }

  Future<void> _runDepositQueueAction(
    String depositId, {
    required List<String> preferredActions,
    Object? body,
  }) async {
    final Map<String, String> cached =
        _depositActionEndpointsById[depositId] ?? const <String, String>{};
    String? path;
    for (final String action in preferredActions) {
      path = cached[action];
      if (path != null && path.trim().isNotEmpty) {
        break;
      }
    }
    final String fallbackAction = preferredActions.first;
    await _requestPaymentQueue(
      'POST',
      path ?? '$_paymentQueuePath/deposits/$depositId/$fallbackAction',
      body: body,
    );
  }

  Future<Object?> _requestPaymentQueue(
    String method,
    String path, {
    Map<String, Object?> query = const <String, Object?>{},
    Object? body,
  }) async {
    final String accessToken = client.accessToken?.trim() ?? '';
    if (accessToken.isEmpty) {
      throw const GteApiException(
        type: GteApiErrorType.unauthorized,
        message: 'Authentication required for this action.',
      );
    }
    final GteTransportResponse response = await client.transport.send(
      GteTransportRequest(
        method: method,
        uri: _rawUriFor(_canonicalPaymentQueuePath(path), query),
        headers: gteVersionedApiHeaders(<String, String>{
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $accessToken',
        }),
        body: body,
      ),
    );
    if (response.statusCode >= 400) {
      throw GteApiException(
        type: _apiErrorType(response.statusCode),
        message: gteApiErrorMessage(
          response.body,
          fallback: 'Admin payment queue request failed.',
        ),
        statusCode: response.statusCode,
      );
    }
    return gteApiSuccessPayload(response.body);
  }

  Uri _rawUriFor(String path, Map<String, Object?> queryParameters) {
    final Uri baseUri = Uri.parse(
      client.config.baseUrl.endsWith('/')
          ? client.config.baseUrl
          : '${client.config.baseUrl}/',
    );
    final Uri resolved = baseUri.resolve(
      path.startsWith('/') ? path.substring(1) : path,
    );
    final Map<String, String> query = <String, String>{};
    for (final MapEntry<String, Object?> entry in queryParameters.entries) {
      if (entry.value == null) {
        continue;
      }
      query[entry.key] = entry.value.toString();
    }
    return query.isEmpty ? resolved : resolved.replace(queryParameters: query);
  }

  String _canonicalPaymentQueuePath(String path) {
    final String trimmed = path.trim();
    final String normalized = trimmed.startsWith('/') ? trimmed : '/$trimmed';
    if (normalized.startsWith('/api/admin/finance/payment-queue')) {
      return normalized.replaceFirst(
        '/api/admin/finance/payment-queue',
        _paymentQueuePath,
      );
    }
    return normalized;
  }

  GteApiErrorType _apiErrorType(int statusCode) {
    if (statusCode == 401 || statusCode == 403) {
      return GteApiErrorType.unauthorized;
    }
    if (statusCode == 404) {
      return GteApiErrorType.notFound;
    }
    if (statusCode == 422) {
      return GteApiErrorType.validation;
    }
    if (statusCode >= 500) {
      return GteApiErrorType.unavailable;
    }
    return GteApiErrorType.unknown;
  }

  Map<String, Object?>? _notesPayload(String? notes) {
    final String trimmed = notes?.trim() ?? '';
    if (trimmed.isEmpty) {
      return null;
    }
    return <String, Object?>{'admin_notes': trimmed};
  }
}

class AdminTransferBidReviewFeed {
  const AdminTransferBidReviewFeed({required this.windows, required this.bids});

  final List<AdminTransferWindow> windows;
  final List<AdminTransferBid> bids;

  int get submittedCount =>
      bids.where((AdminTransferBid bid) => bid.isSubmitted).length;
}

class AdminTransferWindow {
  const AdminTransferWindow({
    required this.id,
    required this.territoryCode,
    required this.label,
    required this.status,
    required this.opensOn,
    required this.closesOn,
  });

  final String id;
  final String territoryCode;
  final String label;
  final String status;
  final String opensOn;
  final String closesOn;

  factory AdminTransferWindow.fromBidReview(AdminTransferBid bid) {
    return AdminTransferWindow(
      id: bid.windowId,
      territoryCode: 'GLOBAL',
      label: bid.windowLabel,
      status: 'review',
      opensOn: 'unknown',
      closesOn: 'unknown',
    );
  }

  factory AdminTransferWindow.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'transfer window',
    );
    return AdminTransferWindow(
      id: GteJson.string(json, <String>['id']),
      territoryCode: GteJson.string(json, <String>[
        'territory_code',
        'territoryCode',
      ], fallback: 'GLOBAL'),
      label: GteJson.string(json, <String>['label'], fallback: 'Window'),
      status: GteJson.string(json, <String>['status'], fallback: 'unknown'),
      opensOn: GteJson.string(json, <String>[
        'opens_on',
        'opensOn',
      ], fallback: 'unknown'),
      closesOn: GteJson.string(json, <String>[
        'closes_on',
        'closesOn',
      ], fallback: 'unknown'),
    );
  }
}

class AdminTransferBid {
  const AdminTransferBid({
    required this.id,
    required this.windowId,
    required this.windowLabel,
    required this.playerId,
    required this.status,
    required this.bidAmount,
    required this.structuredTermsJson,
    this.availableActions = const <String>[],
    this.actionEndpoints = const <String, String>{},
    this.sellingClubId,
    this.buyingClubId,
    this.wageOfferAmount,
    this.sellOnClausePct,
    this.walletReservationStatus,
    this.walletReservedAmount,
    this.walletReservationReference,
    this.actionState,
    this.businessActionState,
    this.blockedReason,
    this.auditReference,
    this.auditTrail = const <String>[],
    this.severity,
    this.escalationState,
    this.notes,
    this.updatedAt,
  });

  final String id;
  final String windowId;
  final String windowLabel;
  final String playerId;
  final String? sellingClubId;
  final String? buyingClubId;
  final String status;
  final double bidAmount;
  final List<String> availableActions;
  final Map<String, String> actionEndpoints;
  final double? wageOfferAmount;
  final double? sellOnClausePct;
  final Map<String, Object?> structuredTermsJson;
  final String? walletReservationStatus;
  final double? walletReservedAmount;
  final String? walletReservationReference;
  final String? actionState;
  final String? businessActionState;
  final String? blockedReason;
  final String? auditReference;
  final List<String> auditTrail;
  final String? severity;
  final String? escalationState;
  final String? notes;
  final DateTime? updatedAt;

  String get normalizedStatus => status.trim().toLowerCase();
  bool get isSubmitted => normalizedStatus == 'submitted';
  bool supportsAction(String action) =>
      availableActions.contains(action.trim().toLowerCase());
  String? actionEndpointFor(String action) =>
      actionEndpoints[action.trim().toLowerCase()];
  Map<String, Object?> get walletReservationTerms => GteJson.map(
    structuredTermsJson,
    keys: <String>['wallet_reservation', 'walletReservation'],
  );
  bool get hasWalletReservationPayload {
    if (walletReservationStatus?.trim().isNotEmpty == true ||
        walletReservedAmount != null ||
        walletReservationReference?.trim().isNotEmpty == true) {
      return true;
    }
    final Map<String, Object?> reservation = walletReservationTerms;
    return reservation.isNotEmpty ||
        structuredTermsJson.containsKey('reservation_id') ||
        structuredTermsJson.containsKey('wallet_reservation_id') ||
        structuredTermsJson.containsKey('reserved_amount');
  }

  factory AdminTransferBid.fromJson(Object? value, {String? windowLabel}) {
    final Map<String, Object?> json = GteJson.map(value, label: 'transfer bid');
    final Map<String, Object?> structuredTermsJson = GteJson.map(
      json,
      keys: <String>['structured_terms_json', 'structuredTermsJson'],
    );
    final Map<String, Object?> walletReservation = GteJson.map(
      structuredTermsJson,
      keys: <String>['wallet_reservation', 'walletReservation'],
    );
    return AdminTransferBid(
      id: GteJson.string(json, <String>['id']),
      windowId: GteJson.string(json, <String>['window_id', 'windowId']),
      windowLabel:
          windowLabel?.trim().isNotEmpty == true
              ? windowLabel!.trim()
              : GteJson.string(json, <String>[
                'window_label',
                'windowLabel',
              ], fallback: 'Transfer window'),
      playerId: GteJson.string(json, <String>['player_id', 'playerId']),
      sellingClubId: GteJson.stringOrNull(json, <String>[
        'selling_club_id',
        'sellingClubId',
      ]),
      buyingClubId: GteJson.stringOrNull(json, <String>[
        'buying_club_id',
        'buyingClubId',
      ]),
      status: GteJson.string(json, <String>['status'], fallback: 'unknown'),
      bidAmount: GteJson.number(json, <String>['bid_amount', 'bidAmount']),
      availableActions: _adminNormalizedStringList(json, <String>[
        'available_actions',
        'availableActions',
      ]),
      actionEndpoints: _adminStringMap(json, <String>[
        'action_endpoints',
        'actionEndpoints',
      ]),
      wageOfferAmount: _adminOptionalNumber(json, <String>[
        'wage_offer_amount',
        'wageOfferAmount',
      ]),
      sellOnClausePct: _adminOptionalNumber(json, <String>[
        'sell_on_clause_pct',
        'sellOnClausePct',
      ]),
      structuredTermsJson: structuredTermsJson,
      walletReservationStatus:
          GteJson.stringOrNull(json, <String>[
            'wallet_reservation_status',
            'walletReservationStatus',
          ]) ??
          GteJson.stringOrNull(walletReservation, <String>['status']),
      walletReservedAmount:
          _adminOptionalNumber(json, <String>[
            'wallet_reserved_amount',
            'walletReservedAmount',
          ]) ??
          _adminOptionalNumber(walletReservation, <String>[
            'amount_gtex_coin',
            'amountGtexCoin',
            'reserved_amount',
            'reservedAmount',
            'amount',
          ]),
      walletReservationReference:
          GteJson.stringOrNull(json, <String>[
            'wallet_reservation_reference',
            'walletReservationReference',
          ]) ??
          GteJson.stringOrNull(walletReservation, <String>[
            'reference',
            'reservation_id',
            'reservationId',
            'key',
          ]),
      actionState: GteJson.stringOrNull(json, <String>[
        'action_state',
        'actionState',
      ]),
      businessActionState: GteJson.stringOrNull(json, <String>[
        'business_action_state',
        'businessActionState',
      ]),
      blockedReason: GteJson.stringOrNull(json, <String>[
        'blocked_reason',
        'blockedReason',
      ]),
      auditReference: GteJson.stringOrNull(json, <String>[
        'audit_reference',
        'auditReference',
      ]),
      auditTrail: _adminStringList(json, <String>['audit_trail', 'auditTrail']),
      severity: GteJson.stringOrNull(json, <String>['severity']),
      escalationState: GteJson.stringOrNull(json, <String>[
        'escalation_state',
        'escalationState',
      ]),
      notes: GteJson.stringOrNull(json, <String>['notes']),
      updatedAt: GteJson.dateTimeOrNull(json, <String>[
        'updated_at',
        'updatedAt',
      ]),
    );
  }
}

class AdminPaymentRailsState {
  const AdminPaymentRailsState({required this.rails, this.reason});

  final List<AdminPaymentRail> rails;
  final String? reason;

  factory AdminPaymentRailsState.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'payment rails',
    );
    return AdminPaymentRailsState(
      rails: GteJson.typedList(json, <String>[
        'rails',
      ], AdminPaymentRail.fromJson),
      reason: GteJson.stringOrNull(json, <String>['reason']),
    );
  }
}

List<String> _adminNormalizedStringList(
  Map<String, Object?> json,
  List<String> keys,
) {
  final Object? value = GteJson.value(json, keys);
  final Iterable<Object?> values =
      value is List ? value : <Object?>[if (value != null) value];
  final List<String> items = <String>[];
  for (final Object? item in values) {
    final String normalized = item?.toString().trim().toLowerCase() ?? '';
    if (normalized.isNotEmpty && !items.contains(normalized)) {
      items.add(normalized);
    }
  }
  return items;
}

List<String> _adminStringList(Map<String, Object?> json, List<String> keys) {
  final Object? value = GteJson.value(json, keys);
  final Iterable<Object?> values =
      value is List ? value : <Object?>[if (value != null) value];
  final List<String> items = <String>[];
  for (final Object? item in values) {
    final String stringValue = item?.toString().trim() ?? '';
    if (stringValue.isNotEmpty && !items.contains(stringValue)) {
      items.add(stringValue);
    }
  }
  return items;
}

Map<String, String> _adminStringMap(
  Map<String, Object?> json,
  List<String> keys,
) {
  final Object? value = GteJson.value(json, keys);
  if (value is! Map) {
    return const <String, String>{};
  }
  final Map<String, String> map = <String, String>{};
  value.forEach((Object? key, Object? rawValue) {
    final String normalizedKey = key?.toString().trim().toLowerCase() ?? '';
    final String stringValue = rawValue?.toString().trim() ?? '';
    if (normalizedKey.isNotEmpty && stringValue.isNotEmpty) {
      map[normalizedKey] = stringValue;
    }
  });
  return map;
}

double? _adminOptionalNumber(Map<String, Object?> json, List<String> keys) {
  final Object? value = GteJson.value(json, keys);
  if (value == null) {
    return null;
  }
  if (value is num) {
    return value.toDouble();
  }
  return double.tryParse(value.toString());
}

class AdminPaymentRail {
  const AdminPaymentRail({
    required this.provider,
    required this.depositsEnabled,
    required this.withdrawalsEnabled,
    required this.isLive,
    this.maintenanceMessage,
    this.updatedAt,
    this.updatedBy,
  });

  final String provider;
  final bool depositsEnabled;
  final bool withdrawalsEnabled;
  final bool isLive;
  final String? maintenanceMessage;
  final DateTime? updatedAt;
  final String? updatedBy;

  factory AdminPaymentRail.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'payment rail');
    return AdminPaymentRail(
      provider: GteJson.string(json, <String>['provider']),
      depositsEnabled: GteJson.boolean(json, <String>[
        'deposits_enabled',
        'depositsEnabled',
      ], fallback: true),
      withdrawalsEnabled: GteJson.boolean(json, <String>[
        'withdrawals_enabled',
        'withdrawalsEnabled',
      ], fallback: true),
      isLive: GteJson.boolean(json, <String>[
        'is_live',
        'isLive',
      ], fallback: true),
      maintenanceMessage: GteJson.stringOrNull(json, <String>[
        'maintenance_message',
        'maintenanceMessage',
      ]),
      updatedAt: GteJson.dateTimeOrNull(json, <String>[
        'updated_at',
        'updatedAt',
      ]),
      updatedBy: GteJson.stringOrNull(json, <String>[
        'updated_by',
        'updatedBy',
      ]),
    );
  }

  AdminPaymentRail copyWith({
    bool? depositsEnabled,
    bool? withdrawalsEnabled,
    bool? isLive,
    String? maintenanceMessage,
  }) {
    return AdminPaymentRail(
      provider: provider,
      depositsEnabled: depositsEnabled ?? this.depositsEnabled,
      withdrawalsEnabled: withdrawalsEnabled ?? this.withdrawalsEnabled,
      isLive: isLive ?? this.isLive,
      maintenanceMessage: maintenanceMessage ?? this.maintenanceMessage,
      updatedAt: updatedAt,
      updatedBy: updatedBy,
    );
  }

  Map<String, Object?> toUpdateJson() => <String, Object?>{
    'provider': provider,
    'deposits_enabled': depositsEnabled,
    'withdrawals_enabled': withdrawalsEnabled,
    'is_live': isLive,
    'maintenance_message':
        maintenanceMessage?.trim().isEmpty ?? true
            ? null
            : maintenanceMessage!.trim(),
  };
}

class AdminWithdrawalControls {
  const AdminWithdrawalControls({
    required this.egameWithdrawalsEnabled,
    required this.tradeWithdrawalsEnabled,
    required this.processorMode,
    required this.depositsViaBankTransfer,
    required this.payoutsViaBankTransfer,
    this.updatedAt,
    this.updatedBy,
    this.reason,
  });

  final bool egameWithdrawalsEnabled;
  final bool tradeWithdrawalsEnabled;
  final String processorMode;
  final bool depositsViaBankTransfer;
  final bool payoutsViaBankTransfer;
  final DateTime? updatedAt;
  final String? updatedBy;
  final String? reason;

  factory AdminWithdrawalControls.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'withdrawal controls',
    );
    return AdminWithdrawalControls(
      egameWithdrawalsEnabled: GteJson.boolean(json, <String>[
        'egame_withdrawals_enabled',
        'egameWithdrawalsEnabled',
      ]),
      tradeWithdrawalsEnabled: GteJson.boolean(json, <String>[
        'trade_withdrawals_enabled',
        'tradeWithdrawalsEnabled',
      ], fallback: true),
      processorMode: GteJson.string(json, <String>[
        'processor_mode',
        'processorMode',
      ], fallback: 'manual_bank_transfer'),
      depositsViaBankTransfer: GteJson.boolean(json, <String>[
        'deposits_via_bank_transfer',
        'depositsViaBankTransfer',
      ], fallback: true),
      payoutsViaBankTransfer: GteJson.boolean(json, <String>[
        'payouts_via_bank_transfer',
        'payoutsViaBankTransfer',
      ], fallback: true),
      updatedAt: GteJson.dateTimeOrNull(json, <String>[
        'updated_at',
        'updatedAt',
      ]),
      updatedBy: GteJson.stringOrNull(json, <String>[
        'updated_by',
        'updatedBy',
      ]),
      reason: GteJson.stringOrNull(json, <String>['reason']),
    );
  }

  AdminWithdrawalControls copyWith({
    bool? egameWithdrawalsEnabled,
    bool? tradeWithdrawalsEnabled,
    String? processorMode,
    bool? depositsViaBankTransfer,
    bool? payoutsViaBankTransfer,
  }) {
    return AdminWithdrawalControls(
      egameWithdrawalsEnabled:
          egameWithdrawalsEnabled ?? this.egameWithdrawalsEnabled,
      tradeWithdrawalsEnabled:
          tradeWithdrawalsEnabled ?? this.tradeWithdrawalsEnabled,
      processorMode: processorMode ?? this.processorMode,
      depositsViaBankTransfer:
          depositsViaBankTransfer ?? this.depositsViaBankTransfer,
      payoutsViaBankTransfer:
          payoutsViaBankTransfer ?? this.payoutsViaBankTransfer,
      updatedAt: updatedAt,
      updatedBy: updatedBy,
      reason: reason,
    );
  }

  Map<String, Object?> toUpdateJson({required String reason}) =>
      <String, Object?>{
        'egame_withdrawals_enabled': egameWithdrawalsEnabled,
        'trade_withdrawals_enabled': tradeWithdrawalsEnabled,
        'processor_mode': processorMode,
        'deposits_via_bank_transfer': depositsViaBankTransfer,
        'payouts_via_bank_transfer': payoutsViaBankTransfer,
        'reason': reason,
      };
}

class AdminMarketTopupQuote {
  const AdminMarketTopupQuote({
    required this.grossAmount,
    required this.feeAmount,
    required this.netAmount,
    required this.unit,
  });

  final double grossAmount;
  final double feeAmount;
  final double netAmount;
  final String unit;

  factory AdminMarketTopupQuote.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'market topup quote',
    );
    return AdminMarketTopupQuote(
      grossAmount: GteJson.number(json, <String>[
        'gross_amount',
        'grossAmount',
      ]),
      feeAmount: GteJson.number(json, <String>['fee_amount', 'feeAmount']),
      netAmount: GteJson.number(json, <String>['net_amount', 'netAmount']),
      unit: GteJson.string(json, <String>['unit'], fallback: 'coin'),
    );
  }
}

class AdminMarketTopup {
  const AdminMarketTopup({
    required this.id,
    required this.reference,
    required this.status,
    required this.userId,
    required this.unit,
    required this.grossAmount,
    required this.feeAmount,
    required this.netAmount,
    required this.sourceScope,
    required this.processorMode,
    required this.payoutChannel,
    required this.createdAt,
    required this.updatedAt,
    this.notes,
    this.settledAt,
  });

  final String id;
  final String reference;
  final String status;
  final String userId;
  final String unit;
  final double grossAmount;
  final double feeAmount;
  final double netAmount;
  final String sourceScope;
  final String processorMode;
  final String payoutChannel;
  final String? notes;
  final DateTime? createdAt;
  final DateTime? updatedAt;
  final DateTime? settledAt;

  factory AdminMarketTopup.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(value, label: 'market topup');
    return AdminMarketTopup(
      id: GteJson.string(json, <String>['id']),
      reference: GteJson.string(json, <String>['reference']),
      status: GteJson.string(json, <String>['status']),
      userId: GteJson.string(json, <String>['user_id', 'userId']),
      unit: GteJson.string(json, <String>['unit'], fallback: 'coin'),
      grossAmount: GteJson.number(json, <String>[
        'gross_amount',
        'grossAmount',
      ]),
      feeAmount: GteJson.number(json, <String>['fee_amount', 'feeAmount']),
      netAmount: GteJson.number(json, <String>['net_amount', 'netAmount']),
      sourceScope: GteJson.string(json, <String>[
        'source_scope',
        'sourceScope',
      ], fallback: 'promotion'),
      processorMode: GteJson.string(json, <String>[
        'processor_mode',
        'processorMode',
      ], fallback: 'manual_admin_credit'),
      payoutChannel: GteJson.string(json, <String>[
        'payout_channel',
        'payoutChannel',
      ], fallback: 'internal_wallet'),
      notes: GteJson.stringOrNull(json, <String>['notes']),
      createdAt: GteJson.dateTimeOrNull(json, <String>[
        'created_at',
        'createdAt',
      ]),
      updatedAt: GteJson.dateTimeOrNull(json, <String>[
        'updated_at',
        'updatedAt',
      ]),
      settledAt: GteJson.dateTimeOrNull(json, <String>[
        'settled_at',
        'settledAt',
      ]),
    );
  }
}
