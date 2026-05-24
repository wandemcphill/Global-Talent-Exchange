import 'package:flutter/foundation.dart';

import '../../../data/admin_command_center_api.dart';
import '../models/gtex_admin_command_models.dart';

class GtexAdminCommandController extends ChangeNotifier {
  GtexAdminCommandController({
    AdminCommandCenterApi? api,
    GtexAdminCommandSnapshot? initialSnapshot,
  }) : _api = api,
       _snapshot =
           initialSnapshot ?? GtexAdminCommandSnapshot.liveUnavailable();

  final AdminCommandCenterApi? _api;
  GtexAdminCommandSnapshot _snapshot;
  GtexAdminModuleType _selectedModule = GtexAdminModuleType.overview;
  String? _selectedQueueItemId;
  String _searchQuery = '';
  bool _loading = false;
  bool _actionLoading = false;
  String? _error;
  String? _actionMessage;
  String? _actionError;

  GtexAdminCommandSnapshot get snapshot => _snapshot;
  GtexAdminModuleType get selectedModule => _selectedModule;
  String? get selectedQueueItemId => _selectedQueueItemId;
  String get searchQuery => _searchQuery;
  bool get loading => _loading;
  bool get actionLoading => _actionLoading;
  String? get error => _error;
  String? get actionMessage => _actionMessage;
  String? get actionError => _actionError;

  List<GtexAdminModule> get modules {
    if (_searchQuery.trim().isEmpty) {
      return _snapshot.modules;
    }

    final query = _searchQuery.toLowerCase();
    return _snapshot.modules
        .where(
          (module) =>
              module.title.toLowerCase().contains(query) ||
              module.description.toLowerCase().contains(query),
        )
        .toList(growable: false);
  }

  List<GtexAdminQueueItem> get queueItems {
    if (_searchQuery.trim().isEmpty) {
      return _snapshot.queues;
    }

    final query = _searchQuery.toLowerCase();
    return _snapshot.queues
        .where(
          (item) =>
              item.title.toLowerCase().contains(query) ||
              item.subtitle.toLowerCase().contains(query) ||
              item.status.toLowerCase().contains(query),
        )
        .toList(growable: false);
  }

  GtexAdminQueueItem? get selectedQueueItem {
    final id = _selectedQueueItemId;
    if (id == null) {
      return queueItems.isEmpty ? null : queueItems.first;
    }
    for (final item in queueItems) {
      if (item.id == id) return item;
    }
    return queueItems.isEmpty ? null : queueItems.first;
  }

  void selectModule(GtexAdminModuleType module) {
    if (_selectedModule == module) return;
    _selectedModule = module;
    notifyListeners();
  }

  void selectQueueItem(String id) {
    if (_selectedQueueItemId == id) return;
    _selectedQueueItemId = id;
    notifyListeners();
  }

  void updateSearch(String value) {
    if (_searchQuery == value) return;
    _searchQuery = value;
    notifyListeners();
  }

  void replaceSnapshot(GtexAdminCommandSnapshot snapshot) {
    _snapshot = snapshot;
    notifyListeners();
  }

  @visibleForTesting
  void replaceWithOperationsReadiness(
    AdminOperationsReadinessSnapshot readiness,
  ) {
    _snapshot = _snapshotFromReadiness(readiness);
    notifyListeners();
  }

  Future<void> refresh() async {
    final api = _api;
    if (api == null) {
      notifyListeners();
      return;
    }
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      final readiness = await api.fetchOperationsReadiness();
      _snapshot = _snapshotFromReadiness(readiness);
    } catch (error) {
      _error = error.toString();
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<void> approveSelectedQueueItem() async {
    // Adapter point for KYC/order/dispute/admin action APIs.
    notifyListeners();
  }

  Future<void> escalateSelectedQueueItem() async {
    final api = _api;
    if (_actionLoading) {
      return;
    }
    _actionLoading = true;
    _actionMessage = null;
    _actionError = null;
    notifyListeners();
    try {
      if (api == null) {
        _actionMessage = 'Readiness blocker notification adapter is ready.';
        return;
      }
      final dispatch = await api.notifyOperationsReadinessBlockers();
      final queueCount = dispatch.queueKeys.length;
      _actionMessage =
          dispatch.sent
              ? '${dispatch.notificationsCreated} readiness notification(s) sent for $queueCount queue(s).'
              : 'No readiness blocker notifications were sent.';
    } catch (error) {
      _actionError = error.toString();
    } finally {
      _actionLoading = false;
      notifyListeners();
    }
  }

  static GtexAdminCommandSnapshot _snapshotFromReadiness(
    AdminOperationsReadinessSnapshot readiness,
  ) {
    final metrics = <GtexAdminMetric>[
      GtexAdminMetric(
        label: 'Readiness',
        value: readiness.status,
        delta: '${readiness.alertCount} alert(s)',
        severity: _severityForStatus(readiness.status),
      ),
      GtexAdminMetric(
        label: 'Blocked queues',
        value: readiness.blockedQueueCount.toString(),
        severity:
            readiness.blockedQueueCount > 0
                ? GtexAdminSeverity.critical
                : GtexAdminSeverity.calm,
      ),
      GtexAdminMetric(
        label: 'Attention queues',
        value: readiness.attentionQueueCount.toString(),
        severity:
            readiness.attentionQueueCount > 0
                ? GtexAdminSeverity.watch
                : GtexAdminSeverity.calm,
      ),
      GtexAdminMetric(
        label: 'Kill switches',
        value: readiness.killSwitchCount.toString(),
        severity:
            readiness.killSwitchCount > 0
                ? GtexAdminSeverity.critical
                : GtexAdminSeverity.calm,
      ),
    ];

    final queueModules = readiness.queues
        .map(
          (queue) => GtexAdminModule(
            type: _moduleTypeForQueue(queue.key),
            title: queue.title,
            description: queue.description,
            countLabel: queue.status,
            severity: _severityForStatus(queue.status),
          ),
        )
        .toList(growable: true);
    final gateModules = readiness.launchGates
        .map(
          (gate) => GtexAdminModule(
            type: _moduleTypeForFeature(gate.featureKey),
            title: gate.title,
            description:
                'Launch state: ${gate.launchState}; audience: ${gate.audience}.',
            countLabel:
                gate.killSwitchEnabled
                    ? 'Kill switch'
                    : gate.enabled
                    ? gate.launchState
                    : 'off',
            severity:
                gate.killSwitchEnabled
                    ? GtexAdminSeverity.critical
                    : _severityForStatus(gate.launchState),
          ),
        )
        .toList(growable: false);

    final queueItems = readiness.queues
        .map(
          (queue) => GtexAdminQueueItem(
            id: queue.key,
            title: queue.title,
            subtitle:
                queue.alerts.isNotEmpty
                    ? queue.alerts.first
                    : queue.description,
            status: queue.status,
            createdAtLabel: 'Live snapshot',
            amountLabel:
                queue.metrics.isEmpty
                    ? null
                    : '${queue.metrics.first.label}: ${queue.metrics.first.displayValue}',
            ownerLabel: queue.owner,
            severity: _severityForStatus(queue.status),
          ),
        )
        .toList(growable: false);

    final healthSignals = <GtexSystemHealthSignal>[
      ...readiness.queues.map(
        (queue) => GtexSystemHealthSignal(
          name: queue.title,
          status: queue.status,
          detail:
              queue.alerts.isNotEmpty
                  ? queue.alerts.first
                  : '${queue.metrics.length} metric(s) tracked',
          severity: _severityForStatus(queue.status),
        ),
      ),
      ...readiness.launchGates
          .where((gate) => gate.killSwitchEnabled)
          .map(
            (gate) => GtexSystemHealthSignal(
              name: gate.title,
              status: 'kill_switch',
              detail: gate.maintenanceMessage ?? 'Kill switch is enabled.',
              severity: GtexAdminSeverity.critical,
            ),
          ),
    ];

    return GtexAdminCommandSnapshot(
      metrics: metrics,
      modules: <GtexAdminModule>[
        const GtexAdminModule(
          type: GtexAdminModuleType.overview,
          title: 'Overview',
          description: 'Live operations snapshot from readiness diagnostics.',
          countLabel: 'Live',
        ),
        ...queueModules,
        ...gateModules,
      ],
      queues: queueItems,
      jackpots: const <GtexJackpotRound>[],
      coinEconomy: const GtexCoinEconomySnapshot(
        circulatingSupply: 'Unavailable',
        treasuryBalance: 'Unavailable',
        pendingWithdrawals: 'Unavailable',
        topupVolumeToday: 'Unavailable',
        riskStatus: 'Live treasury endpoint required',
      ),
      healthSignals: healthSignals,
    );
  }

  static GtexAdminModuleType _moduleTypeForQueue(String key) {
    switch (key) {
      case 'risk_compliance':
        return GtexAdminModuleType.kyc;
      case 'moderation_disputes':
        return GtexAdminModuleType.disputes;
      case 'policy_launch_control':
        return GtexAdminModuleType.launchControl;
      case 'production_data_diagnostics':
        return GtexAdminModuleType.operationsReadiness;
      case 'infrastructure_payment_rails':
        return GtexAdminModuleType.systemHealth;
      case 'ledger_worker_health':
        return GtexAdminModuleType.systemHealth;
      default:
        return GtexAdminModuleType.overview;
    }
  }

  static GtexAdminModuleType _moduleTypeForFeature(String featureKey) {
    switch (featureKey) {
      case 'transfer_hub':
        return GtexAdminModuleType.transferHub;
      case 'coin_traders':
        return GtexAdminModuleType.coinTraders;
      case 'club_lifecycle':
        return GtexAdminModuleType.clubLifecycle;
      case 'staff_marketplace':
        return GtexAdminModuleType.staffMarketplace;
      case 'academy_regens':
      case 'newgen_portraits':
        return GtexAdminModuleType.academy;
      case 'sponsorships':
        return GtexAdminModuleType.sponsorships;
      case 'federations':
        return GtexAdminModuleType.federations;
      case 'fan_coin':
      case 'fan_wars':
      case 'predictions':
        return GtexAdminModuleType.fanEconomy;
      case 'broadcast':
      case 'viral_clips':
        return GtexAdminModuleType.broadcast;
      case 'ticketing':
        return GtexAdminModuleType.ticketing;
      case 'player_card_marketplace':
        return GtexAdminModuleType.playerCards;
      case 'global_search':
        return GtexAdminModuleType.globalSearch;
      case 'operations_readiness':
        return GtexAdminModuleType.operationsReadiness;
      case 'launch_control':
        return GtexAdminModuleType.launchControl;
      default:
        return GtexAdminModuleType.launchControl;
    }
  }

  static GtexAdminSeverity _severityForStatus(String status) {
    switch (status.toLowerCase().trim()) {
      case 'blocked':
      case 'critical':
      case 'kill_switch':
      case 'disabled':
        return GtexAdminSeverity.critical;
      case 'attention':
      case 'warning':
      case 'maintenance':
      case 'paused':
        return GtexAdminSeverity.warning;
      case 'watch':
      case 'beta':
      case 'internal':
      case 'gated':
        return GtexAdminSeverity.watch;
      default:
        return GtexAdminSeverity.calm;
    }
  }
}
