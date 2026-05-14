import 'gte_api_repository.dart';
import 'gte_authed_api.dart';
import 'gte_http_transport.dart';
import 'gte_models.dart';

class AdminCommandCenterApi {
  AdminCommandCenterApi({required this.client});

  final GteAuthedApi client;

  factory AdminCommandCenterApi.standard({
    required String baseUrl,
    required String accessToken,
    GteBackendMode mode = GteBackendMode.live,
    GteAuthedApi? client,
  }) {
    return AdminCommandCenterApi(
      client:
          client ??
          GteAuthedApi(
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
    final Map<String, dynamic> payload = await client.getMap(
      '/api/admin/treasury/deposits',
      query: <String, Object?>{
        'limit': limit,
        'offset': offset,
        if (status != null && status.trim().isNotEmpty) 'status': status.trim(),
        if (query != null && query.trim().isNotEmpty) 'q': query.trim(),
      },
    );
    return GteAdminQueuePage<GteAdminDeposit>.fromJson(
      payload,
      GteAdminDeposit.fromJson,
    );
  }

  Future<GteDepositRequest> adminReviewDeposit(
    String depositId, {
    String? adminNotes,
  }) async {
    final Object? payload = await client.post(
      '/api/admin/treasury/deposits/$depositId/review',
      body: _notesPayload(adminNotes),
    );
    return GteDepositRequest.fromJson(payload);
  }

  Future<GteDepositRequest> adminConfirmDeposit(
    String depositId, {
    String? adminNotes,
  }) async {
    final Object? payload = await client.post(
      '/api/admin/treasury/deposits/$depositId/confirm',
      body: _notesPayload(adminNotes),
    );
    return GteDepositRequest.fromJson(payload);
  }

  Future<GteDepositRequest> adminRejectDeposit(
    String depositId, {
    String? adminNotes,
  }) async {
    final Object? payload = await client.post(
      '/api/admin/treasury/deposits/$depositId/reject',
      body: _notesPayload(adminNotes),
    );
    return GteDepositRequest.fromJson(payload);
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

  Future<AdminOperationsReadinessSnapshot> fetchOperationsReadiness() async {
    final Map<String, dynamic> payload = await client.getMap(
      '/api/admin/operations-readiness',
    );
    return AdminOperationsReadinessSnapshot.fromJson(payload);
  }

  Future<AdminOperationsReadinessDispatch>
  notifyOperationsReadinessBlockers() async {
    final Object? payload = await client.post(
      '/api/admin/operations-readiness/notify-blockers',
    );
    return AdminOperationsReadinessDispatch.fromJson(payload);
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

  Map<String, Object?>? _notesPayload(String? notes) {
    final String trimmed = notes?.trim() ?? '';
    if (trimmed.isEmpty) {
      return null;
    }
    return <String, Object?>{'admin_notes': trimmed};
  }
}

class AdminOperationsReadinessSnapshot {
  const AdminOperationsReadinessSnapshot({
    required this.status,
    required this.totals,
    required this.queues,
    required this.launchGates,
  });

  final String status;
  final Map<String, Object?> totals;
  final List<AdminOperationsQueue> queues;
  final List<AdminOperationsLaunchGate> launchGates;

  int get alertCount => _intTotal('alerts');
  int get blockedQueueCount => _intTotal('blocked_queues');
  int get attentionQueueCount => _intTotal('attention_queues');
  int get killSwitchCount => _intTotal('kill_switches');

  factory AdminOperationsReadinessSnapshot.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'operations readiness',
    );
    final Map<String, Object?> totals = GteJson.map(
      json['totals'],
      label: 'operations readiness totals',
    );
    return AdminOperationsReadinessSnapshot(
      status: GteJson.string(json, <String>['status'], fallback: 'ok'),
      totals: totals,
      queues: GteJson.typedList(json, <String>[
        'queues',
      ], AdminOperationsQueue.fromJson),
      launchGates: GteJson.typedList(json, <String>[
        'launch_gates',
        'launchGates',
      ], AdminOperationsLaunchGate.fromJson),
    );
  }

  int _intTotal(String key) {
    final Object? value = totals[key];
    if (value is num) {
      return value.round();
    }
    return int.tryParse(value?.toString() ?? '') ?? 0;
  }
}

class AdminOperationsReadinessDispatch {
  const AdminOperationsReadinessDispatch({
    required this.status,
    required this.notificationsCreated,
    required this.queueKeys,
  });

  final String status;
  final int notificationsCreated;
  final List<String> queueKeys;

  bool get sent => status.toLowerCase().trim() == 'sent';

  factory AdminOperationsReadinessDispatch.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'operations readiness dispatch',
    );
    return AdminOperationsReadinessDispatch(
      status: GteJson.string(json, <String>['status'], fallback: 'skipped'),
      notificationsCreated: GteJson.integer(json, <String>[
        'notifications_created',
        'notificationsCreated',
      ]),
      queueKeys: GteJson.typedList<String>(json, <String>[
        'queue_keys',
        'queueKeys',
      ], (Object? value) => value?.toString() ?? ''),
    );
  }
}

class AdminOperationsQueue {
  const AdminOperationsQueue({
    required this.key,
    required this.title,
    required this.description,
    required this.status,
    required this.owner,
    required this.alerts,
    required this.metrics,
    this.actionRoutes = const <String>[],
    this.route,
  });

  final String key;
  final String title;
  final String description;
  final String status;
  final String owner;
  final String? route;
  final List<String> alerts;
  final List<AdminOperationsMetric> metrics;
  final List<String> actionRoutes;

  factory AdminOperationsQueue.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'operations queue',
    );
    return AdminOperationsQueue(
      key: GteJson.string(json, <String>['key']),
      title: GteJson.string(json, <String>['title']),
      description: GteJson.string(json, <String>['description']),
      status: GteJson.string(json, <String>['status'], fallback: 'ok'),
      owner: GteJson.string(json, <String>['owner'], fallback: 'operations'),
      route: GteJson.stringOrNull(json, <String>['route']),
      alerts: GteJson.typedList<String>(json, <String>[
            'alerts',
          ], (Object? value) => value?.toString() ?? '')
          .where((String value) => value.trim().isNotEmpty)
          .toList(growable: false),
      metrics: GteJson.typedList(json, <String>[
        'metrics',
      ], AdminOperationsMetric.fromJson),
      actionRoutes: GteJson.typedList<String>(json, <String>[
            'action_routes',
            'actionRoutes',
          ], (Object? value) => value?.toString() ?? '')
          .where((String value) => value.trim().isNotEmpty)
          .toList(growable: false),
    );
  }
}

class AdminOperationsMetric {
  const AdminOperationsMetric({
    required this.key,
    required this.label,
    required this.value,
    required this.displayValue,
    required this.status,
    this.unit,
  });

  final String key;
  final String label;
  final double value;
  final String displayValue;
  final String status;
  final String? unit;

  factory AdminOperationsMetric.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'operations metric',
    );
    return AdminOperationsMetric(
      key: GteJson.string(json, <String>['key']),
      label: GteJson.string(json, <String>['label']),
      value: GteJson.number(json, <String>['value']),
      displayValue: GteJson.string(json, <String>[
        'display_value',
        'displayValue',
      ]),
      status: GteJson.string(json, <String>['status'], fallback: 'ok'),
      unit: GteJson.stringOrNull(json, <String>['unit']),
    );
  }
}

class AdminOperationsLaunchGate {
  const AdminOperationsLaunchGate({
    required this.featureKey,
    required this.title,
    required this.enabled,
    required this.launchState,
    required this.killSwitchEnabled,
    required this.audience,
    this.route,
    this.maintenanceMessage,
  });

  final String featureKey;
  final String title;
  final bool enabled;
  final String launchState;
  final bool killSwitchEnabled;
  final String audience;
  final String? route;
  final String? maintenanceMessage;

  factory AdminOperationsLaunchGate.fromJson(Object? value) {
    final Map<String, Object?> json = GteJson.map(
      value,
      label: 'operations launch gate',
    );
    return AdminOperationsLaunchGate(
      featureKey: GteJson.string(json, <String>['feature_key', 'featureKey']),
      title: GteJson.string(json, <String>['title']),
      enabled: GteJson.boolean(json, <String>['enabled']),
      launchState: GteJson.string(json, <String>[
        'launch_state',
        'launchState',
      ], fallback: 'public'),
      killSwitchEnabled: GteJson.boolean(json, <String>[
        'kill_switch_enabled',
        'killSwitchEnabled',
      ]),
      audience: GteJson.string(json, <String>['audience'], fallback: 'global'),
      route: GteJson.stringOrNull(json, <String>['route']),
      maintenanceMessage: GteJson.stringOrNull(json, <String>[
        'maintenance_message',
        'maintenanceMessage',
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
