import 'package:flutter/material.dart';

import '../../core/app_feedback.dart';
import '../../data/gte_api_repository.dart';
import '../../data/gte_exchange_api_client.dart';
import '../../data/gte_http_transport.dart';
import '../../data/gte_mock_api.dart';
import '../../data/gte_models.dart';
import '../../screens/support/gte_support_dispute_screens.dart';
import '../../widgets/gte_formatters.dart';
import '../../widgets/gte_metric_chip.dart';
import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';

class GteTreasuryOpsScreen extends StatefulWidget {
  const GteTreasuryOpsScreen({
    super.key,
    required this.baseUrl,
    required this.accessToken,
    this.backendMode = GteBackendMode.liveThenFixture,
  });

  final String baseUrl;
  final String accessToken;
  final GteBackendMode backendMode;

  @override
  State<GteTreasuryOpsScreen> createState() => _GteTreasuryOpsScreenState();
}

class _GteTreasuryOpsScreenState extends State<GteTreasuryOpsScreen> {
  late final GteExchangeApiClient _api;

  @override
  void initState() {
    super.initState();
    final GteRepositoryConfig config = GteRepositoryConfig(
      baseUrl: widget.baseUrl,
      mode: widget.backendMode,
    );
    final GteMemoryTokenStore tokenStore = GteMemoryTokenStore();
    tokenStore.writeToken(widget.accessToken);
    final GteTransport transport = GteHttpTransport();
    _api = GteExchangeApiClient(
      config: config,
      transport: transport,
      repository: GteReliableApiRepository(
        config: config,
        transport: transport,
        fixtures: GteMockApi(),
        tokenStore: tokenStore,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 6,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('Treasury ops'),
          bottom: const TabBar(
            isScrollable: true,
            tabs: <Tab>[
              Tab(text: 'Dashboard'),
              Tab(text: 'Deposits'),
              Tab(text: 'Withdrawals'),
              Tab(text: 'KYC'),
              Tab(text: 'Disputes'),
              Tab(text: 'Settings'),
            ],
          ),
        ),
        body: TabBarView(
          children: <Widget>[
            _TreasuryDashboardTab(api: _api),
            _TreasuryDepositsTab(api: _api),
            _TreasuryWithdrawalsTab(api: _api),
            _TreasuryKycTab(api: _api),
            _TreasuryDisputesTab(api: _api),
            _TreasurySettingsTab(api: _api),
          ],
        ),
      ),
    );
  }
}

class _TreasuryDashboardTab extends StatefulWidget {
  const _TreasuryDashboardTab({required this.api});

  final GteExchangeApiClient api;

  @override
  State<_TreasuryDashboardTab> createState() => _TreasuryDashboardTabState();
}

class _TreasuryDashboardTabState extends State<_TreasuryDashboardTab> {
  late Future<GteTreasuryDashboard> _dashboardFuture;
  late Future<GteTreasurySettings> _settingsFuture;

  @override
  void initState() {
    super.initState();
    _dashboardFuture = widget.api.fetchTreasuryDashboard();
    _settingsFuture = widget.api.fetchTreasurySettings();
  }

  Future<void> _refresh() async {
    setState(() {
      _dashboardFuture = widget.api.fetchTreasuryDashboard();
      _settingsFuture = widget.api.fetchTreasurySettings();
    });
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<GteTreasuryDashboard>(
      future: _dashboardFuture,
      builder: (BuildContext context,
          AsyncSnapshot<GteTreasuryDashboard> snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }
        if (!snapshot.hasData) {
          return const Center(
            child: GteStatePanel(
              title: 'Treasury dashboard unavailable',
              message: 'Unable to load treasury metrics right now.',
              icon: Icons.account_balance_outlined,
            ),
          );
        }
        final GteTreasuryDashboard dashboard = snapshot.data!;
        return RefreshIndicator(
          onRefresh: _refresh,
          child: ListView(
            padding: const EdgeInsets.all(20),
            children: <Widget>[
              GteSurfacePanel(
                emphasized: true,
                accentColor: GteShellTheme.accentCapital,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text('Treasury snapshot',
                        style: Theme.of(context).textTheme.titleLarge),
                    const SizedBox(height: 16),
                    Wrap(
                      spacing: 12,
                      runSpacing: 12,
                      children: <Widget>[
                        GteMetricChip(
                          label: 'Total users',
                          value: dashboard.totalUsers.toString(),
                        ),
                        GteMetricChip(
                          label: 'Active users',
                          value: dashboard.activeUsers.toString(),
                        ),
                        GteMetricChip(
                          label: 'Pending deposits',
                          value: dashboard.pendingDeposits.toString(),
                          positive: false,
                        ),
                        GteMetricChip(
                          label: 'Pending withdrawals',
                          value: dashboard.pendingWithdrawals.toString(),
                          positive: false,
                        ),
                        GteMetricChip(
                          label: 'Pending KYC',
                          value: dashboard.pendingKyc.toString(),
                          positive: false,
                        ),
                        GteMetricChip(
                          label: 'Open disputes',
                          value: dashboard.openDisputes.toString(),
                          positive: false,
                        ),
                        GteMetricChip(
                          label: 'Deposits today',
                          value: dashboard.depositsConfirmedToday.toString(),
                        ),
                        GteMetricChip(
                          label: 'Withdrawals today',
                          value: dashboard.withdrawalsPaidToday.toString(),
                        ),
                        GteMetricChip(
                          label: 'Wallet liability',
                          value: gteFormatCredits(dashboard.walletLiability),
                        ),
                        GteMetricChip(
                          label: 'Pending exposure',
                          value: gteFormatCredits(
                              dashboard.pendingTreasuryExposure),
                          positive: false,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 18),
              FutureBuilder<GteTreasurySettings>(
                future: _settingsFuture,
                builder: (BuildContext context,
                    AsyncSnapshot<GteTreasurySettings> settingsSnapshot) {
                  if (!settingsSnapshot.hasData) {
                    return const GteSurfacePanel(
                      child: Text('Loading treasury settings...'),
                    );
                  }
                  final GteTreasurySettings settings =
                      settingsSnapshot.data!;
                  final GteTreasuryBankAccount? bank =
                      settings.activeBankAccount;
                  return GteSurfacePanel(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text('Active treasury settings',
                            style: Theme.of(context).textTheme.titleMedium),
                        const SizedBox(height: 12),
                        Text(
                          'Deposit rate: ${settings.depositRateValue} (${_rateDirectionLabel(settings.depositRateDirection)})',
                        ),
                        Text(
                          'Withdrawal rate: ${settings.withdrawalRateValue} (${_rateDirectionLabel(settings.withdrawalRateDirection)})',
                        ),
                        Text(
                          'Deposit limits: ${settings.minDeposit} - ${settings.maxDeposit} ${settings.currencyCode}',
                        ),
                        Text(
                          'Withdrawal limits: ${settings.minWithdrawal} - ${settings.maxWithdrawal} ${settings.currencyCode}',
                        ),
                        Text(
                          'Deposit mode: ${_paymentModeLabel(settings.depositMode)}',
                        ),
                        Text(
                          'Withdrawal mode: ${_paymentModeLabel(settings.withdrawalMode)}',
                        ),
                        if (settings.maintenanceMessage != null &&
                            settings.maintenanceMessage!.trim().isNotEmpty)
                          Padding(
                            padding: const EdgeInsets.only(top: 8),
                            child: Text(
                              'Maintenance: ${settings.maintenanceMessage}',
                            ),
                          ),
                        const SizedBox(height: 12),
                        Text(
                          bank == null
                              ? 'Active bank: None'
                              : 'Active bank: ${bank.bankName} - ${bank.accountNumber} (${bank.accountName})',
                        ),
                        Text(
                          settings.whatsappNumber == null ||
                                  settings.whatsappNumber!.trim().isEmpty
                              ? 'WhatsApp: Not configured'
                              : 'WhatsApp: ${settings.whatsappNumber}',
                        ),
                      ],
                    ),
                  );
                },
              ),
            ],
          ),
        );
      },
    );
  }
}
class _TreasuryDepositsTab extends StatefulWidget {
  const _TreasuryDepositsTab({required this.api});

  final GteExchangeApiClient api;

  @override
  State<_TreasuryDepositsTab> createState() => _TreasuryDepositsTabState();
}

class _TreasuryDepositsTabState extends State<_TreasuryDepositsTab> {
  final TextEditingController _searchController = TextEditingController();
  String _statusFilter = 'all';
  int _offset = 0;
  final int _limit = 50;
  bool _isActionRunning = false;
  String? _actionId;
  late Future<GteAdminQueuePage<GteAdminDeposit>> _queueFuture;

  @override
  void initState() {
    super.initState();
    _queueFuture = _fetchQueue();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<GteAdminQueuePage<GteAdminDeposit>> _fetchQueue() {
    return widget.api.fetchAdminDeposits(
      limit: _limit,
      offset: _offset,
      status: _statusFilter == 'all' ? null : _statusFilter,
      query: _searchController.text.trim().isEmpty
          ? null
          : _searchController.text.trim(),
    );
  }

  Future<void> _refresh() async {
    setState(() {
      _queueFuture = _fetchQueue();
    });
  }

  void _updateStatusFilter(String? value) {
    if (value == null) {
      return;
    }
    setState(() {
      _statusFilter = value;
      _offset = 0;
      _queueFuture = _fetchQueue();
    });
  }

  void _search() {
    setState(() {
      _offset = 0;
      _queueFuture = _fetchQueue();
    });
  }

  Future<void> _runAction(
    String actionId,
    Future<void> Function() task,
  ) async {
    setState(() {
      _isActionRunning = true;
      _actionId = actionId;
    });
    try {
      await task();
      if (!mounted) {
        return;
      }
      await _refresh();
    } catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(AppFeedback.messageFor(error))),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isActionRunning = false;
          _actionId = null;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<GteAdminQueuePage<GteAdminDeposit>>(
      future: _queueFuture,
      builder: (BuildContext context,
          AsyncSnapshot<GteAdminQueuePage<GteAdminDeposit>> snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }
        final GteAdminQueuePage<GteAdminDeposit> page =
            snapshot.data ??
                GteAdminQueuePage<GteAdminDeposit>(
                  items: <GteAdminDeposit>[],
                  total: 0,
                  limit: 50,
                  offset: 0,
                );
        final List<GteAdminDeposit> items = page.items;
        return RefreshIndicator(
          onRefresh: _refresh,
          child: ListView(
            padding: const EdgeInsets.all(20),
            children: <Widget>[
              GteSurfacePanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text('Deposit queue',
                        style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _searchController,
                      decoration: const InputDecoration(
                        labelText: 'Search by reference, user, bank, payer',
                        prefixIcon: Icon(Icons.search),
                      ),
                      onSubmitted: (_) => _search(),
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<String>(
                      value: _statusFilter,
                      items: _depositStatusFilters
                          .map((GteStatusFilter filter) =>
                              DropdownMenuItem<String>(
                                value: filter.value,
                                child: Text(filter.label),
                              ))
                          .toList(),
                      onChanged: _updateStatusFilter,
                      decoration:
                          const InputDecoration(labelText: 'Status filter'),
                    ),
                    const SizedBox(height: 12),
                    Align(
                      alignment: Alignment.centerRight,
                      child: FilledButton.tonal(
                        onPressed: _search,
                        child: const Text('Search'),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              if (items.isEmpty)
                const GteStatePanel(
                  title: 'No deposits',
                  message: 'No deposit requests match this filter.',
                  icon: Icons.savings_outlined,
                )
              else
                ...items.map((GteAdminDeposit deposit) {
                  final bool isFinal = deposit.status ==
                          GteDepositStatus.confirmed ||
                      deposit.status == GteDepositStatus.rejected ||
                      deposit.status == GteDepositStatus.expired;
                  final bool isBusy =
                      _isActionRunning && _actionId == deposit.id;
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: GteSurfacePanel(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(deposit.reference,
                              style: Theme.of(context).textTheme.titleMedium),
                          const SizedBox(height: 6),
                          Text(
                            'Status: ${_depositStatusLabel(deposit.status)}',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                          const SizedBox(height: 8),
                          Text(
                            '${deposit.userFullName ?? deposit.userEmail} - ${deposit.userEmail}',
                          ),
                          if (deposit.userPhoneNumber != null)
                            Text('Phone: ${deposit.userPhoneNumber}'),
                          const SizedBox(height: 8),
                          Text(
                            'Amount: ${gteFormatFiat(deposit.amountFiat, currency: deposit.currencyCode)} for ${gteFormatCredits(deposit.amountCoin)}',
                          ),
                          const SizedBox(height: 6),
                          if (deposit.payerName != null ||
                              deposit.senderBank != null)
                            Text(
                              'Payer: ${deposit.payerName ?? 'Unknown'} - ${deposit.senderBank ?? 'Bank n/a'}',
                            ),
                          if (deposit.transferReference != null)
                            Text('Transfer ref: ${deposit.transferReference}'),
                          Text(
                            'Created: ${gteFormatDateTime(deposit.createdAt)}',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                          const SizedBox(height: 12),
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: <Widget>[
                              FilledButton(
                                onPressed: isFinal || isBusy
                                    ? null
                                    : () async {
                                        final String? notes =
                                            await _promptForNotes(
                                          context,
                                          title: 'Confirm deposit',
                                          hintText: 'Optional admin notes',
                                        );
                                        await _runAction(deposit.id, () async {
                                          await widget.api.adminConfirmDeposit(
                                            deposit.id,
                                            adminNotes: notes,
                                          );
                                        });
                                      },
                                child: isBusy
                                    ? const SizedBox(
                                        width: 16,
                                        height: 16,
                                        child: CircularProgressIndicator(
                                            strokeWidth: 2),
                                      )
                                    : const Text('Confirm'),
                              ),
                              OutlinedButton(
                                onPressed: isFinal || isBusy
                                    ? null
                                    : () async {
                                        final String? notes =
                                            await _promptForNotes(
                                          context,
                                          title: 'Mark under review',
                                          hintText: 'Optional review notes',
                                        );
                                        await _runAction(deposit.id, () async {
                                          await widget.api.adminReviewDeposit(
                                            deposit.id,
                                            adminNotes: notes,
                                          );
                                        });
                                      },
                                child: const Text('Review'),
                              ),
                              OutlinedButton(
                                onPressed: isFinal || isBusy
                                    ? null
                                    : () async {
                                        final String? notes =
                                            await _promptForNotes(
                                          context,
                                          title: 'Reject deposit',
                                          hintText: 'Reason for rejection',
                                        );
                                        await _runAction(deposit.id, () async {
                                          await widget.api.adminRejectDeposit(
                                            deposit.id,
                                            adminNotes: notes,
                                          );
                                        });
                                      },
                                child: const Text('Reject'),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  );
                }),
              _QueuePager(
                total: page.total,
                limit: page.limit,
                offset: page.offset,
                onPageChanged: (int nextOffset) {
                  setState(() {
                    _offset = nextOffset;
                    _queueFuture = _fetchQueue();
                  });
                },
              ),
            ],
          ),
        );
      },
    );
  }
}
class _TreasuryWithdrawalsTab extends StatefulWidget {
  const _TreasuryWithdrawalsTab({required this.api});

  final GteExchangeApiClient api;

  @override
  State<_TreasuryWithdrawalsTab> createState() =>
      _TreasuryWithdrawalsTabState();
}

class _TreasuryWithdrawalsTabState extends State<_TreasuryWithdrawalsTab> {
  final TextEditingController _searchController = TextEditingController();
  String _statusFilter = 'all';
  int _offset = 0;
  final int _limit = 50;
  bool _isActionRunning = false;
  String? _actionId;
  late Future<GteAdminQueuePage<GteAdminWithdrawal>> _queueFuture;

  @override
  void initState() {
    super.initState();
    _queueFuture = _fetchQueue();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<GteAdminQueuePage<GteAdminWithdrawal>> _fetchQueue() {
    return widget.api.fetchAdminWithdrawals(
      limit: _limit,
      offset: _offset,
      status: _statusFilter == 'all' ? null : _statusFilter,
      query: _searchController.text.trim().isEmpty
          ? null
          : _searchController.text.trim(),
    );
  }

  Future<void> _refresh() async {
    setState(() {
      _queueFuture = _fetchQueue();
    });
  }

  void _updateStatusFilter(String? value) {
    if (value == null) {
      return;
    }
    setState(() {
      _statusFilter = value;
      _offset = 0;
      _queueFuture = _fetchQueue();
    });
  }

  void _search() {
    setState(() {
      _offset = 0;
      _queueFuture = _fetchQueue();
    });
  }

  Future<void> _runAction(
    String actionId,
    Future<void> Function() task,
  ) async {
    setState(() {
      _isActionRunning = true;
      _actionId = actionId;
    });
    try {
      await task();
      if (!mounted) {
        return;
      }
      await _refresh();
    } catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(AppFeedback.messageFor(error))),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isActionRunning = false;
          _actionId = null;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<GteAdminQueuePage<GteAdminWithdrawal>>(
      future: _queueFuture,
      builder: (BuildContext context,
          AsyncSnapshot<GteAdminQueuePage<GteAdminWithdrawal>> snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }
        final GteAdminQueuePage<GteAdminWithdrawal> page =
            snapshot.data ??
                GteAdminQueuePage<GteAdminWithdrawal>(
                  items: <GteAdminWithdrawal>[],
                  total: 0,
                  limit: 50,
                  offset: 0,
                );
        final List<GteAdminWithdrawal> items = page.items;
        return RefreshIndicator(
          onRefresh: _refresh,
          child: ListView(
            padding: const EdgeInsets.all(20),
            children: <Widget>[
              GteSurfacePanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text('Withdrawal queue',
                        style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _searchController,
                      decoration: const InputDecoration(
                        labelText: 'Search by reference, user, bank',
                        prefixIcon: Icon(Icons.search),
                      ),
                      onSubmitted: (_) => _search(),
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<String>(
                      value: _statusFilter,
                      items: _withdrawalStatusFilters
                          .map((GteStatusFilter filter) =>
                              DropdownMenuItem<String>(
                                value: filter.value,
                                child: Text(filter.label),
                              ))
                          .toList(),
                      onChanged: _updateStatusFilter,
                      decoration:
                          const InputDecoration(labelText: 'Status filter'),
                    ),
                    const SizedBox(height: 12),
                    Align(
                      alignment: Alignment.centerRight,
                      child: FilledButton.tonal(
                        onPressed: _search,
                        child: const Text('Search'),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              if (items.isEmpty)
                const GteStatePanel(
                  title: 'No withdrawals',
                  message: 'No withdrawal requests match this filter.',
                  icon: Icons.account_balance_wallet_outlined,
                )
              else
                ...items.map((GteAdminWithdrawal withdrawal) {
                  final bool isFinal = withdrawal.status ==
                          GteWithdrawalStatus.paid ||
                      withdrawal.status == GteWithdrawalStatus.rejected ||
                      withdrawal.status == GteWithdrawalStatus.cancelled;
                  final bool isBusy =
                      _isActionRunning && _actionId == withdrawal.id;
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: GteSurfacePanel(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(withdrawal.reference,
                              style: Theme.of(context).textTheme.titleMedium),
                          const SizedBox(height: 6),
                          Text(
                            'Status: ${_withdrawalStatusLabel(withdrawal.status)}',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                          const SizedBox(height: 8),
                          Text(
                            '${withdrawal.userFullName ?? withdrawal.userEmail} - ${withdrawal.userEmail}',
                          ),
                          if (withdrawal.userPhoneNumber != null)
                            Text('Phone: ${withdrawal.userPhoneNumber}'),
                          const SizedBox(height: 8),
                          Text(
                            'Amount: ${gteFormatFiat(withdrawal.amountFiat, currency: withdrawal.currencyCode)} for ${gteFormatCredits(withdrawal.amountCoin)}',
                          ),
                          const SizedBox(height: 6),
                          Text(
                            'Bank: ${withdrawal.bankName} - ${withdrawal.bankAccountNumber} (${withdrawal.bankAccountName})',
                          ),
                          Text(
                            'Created: ${gteFormatDateTime(withdrawal.createdAt)}',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                          const SizedBox(height: 12),
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: <Widget>[
                              FilledButton(
                                onPressed: isFinal || isBusy
                                    ? null
                                    : () async {
                                        final String? notes =
                                            await _promptForNotes(
                                          context,
                                          title: 'Approve withdrawal',
                                          hintText: 'Optional admin notes',
                                        );
                                        await _runAction(withdrawal.id, () async {
                                          await widget.api
                                              .adminUpdateWithdrawalStatus(
                                            withdrawal.id,
                                            status: GteWithdrawalStatus.approved,
                                            adminNotes: notes,
                                          );
                                        });
                                      },
                                child: isBusy
                                    ? const SizedBox(
                                        width: 16,
                                        height: 16,
                                        child: CircularProgressIndicator(
                                            strokeWidth: 2),
                                      )
                                    : const Text('Approve'),
                              ),
                              OutlinedButton(
                                onPressed: isFinal || isBusy
                                    ? null
                                    : () async {
                                        final String? notes =
                                            await _promptForNotes(
                                          context,
                                          title: 'Mark processing',
                                          hintText: 'Optional admin notes',
                                        );
                                        await _runAction(withdrawal.id, () async {
                                          await widget.api
                                              .adminUpdateWithdrawalStatus(
                                            withdrawal.id,
                                            status:
                                                GteWithdrawalStatus.processing,
                                            adminNotes: notes,
                                          );
                                        });
                                      },
                                child: const Text('Processing'),
                              ),
                              OutlinedButton(
                                onPressed: isFinal || isBusy
                                    ? null
                                    : () async {
                                        final String? notes =
                                            await _promptForNotes(
                                          context,
                                          title: 'Mark paid',
                                          hintText: 'Optional admin notes',
                                        );
                                        await _runAction(withdrawal.id, () async {
                                          await widget.api
                                              .adminUpdateWithdrawalStatus(
                                            withdrawal.id,
                                            status: GteWithdrawalStatus.paid,
                                            adminNotes: notes,
                                          );
                                        });
                                      },
                                child: const Text('Paid'),
                              ),
                              OutlinedButton(
                                onPressed: isFinal || isBusy
                                    ? null
                                    : () async {
                                        final String? notes =
                                            await _promptForNotes(
                                          context,
                                          title: 'Reject withdrawal',
                                          hintText: 'Reason for rejection',
                                        );
                                        await _runAction(withdrawal.id, () async {
                                          await widget.api
                                              .adminUpdateWithdrawalStatus(
                                            withdrawal.id,
                                            status: GteWithdrawalStatus.rejected,
                                            adminNotes: notes,
                                          );
                                        });
                                      },
                                child: const Text('Reject'),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  );
                }),
              _QueuePager(
                total: page.total,
                limit: page.limit,
                offset: page.offset,
                onPageChanged: (int nextOffset) {
                  setState(() {
                    _offset = nextOffset;
                    _queueFuture = _fetchQueue();
                  });
                },
              ),
            ],
          ),
        );
      },
    );
  }
}
class _TreasuryKycTab extends StatefulWidget {
  const _TreasuryKycTab({required this.api});

  final GteExchangeApiClient api;

  @override
  State<_TreasuryKycTab> createState() => _TreasuryKycTabState();
}

class _TreasuryKycTabState extends State<_TreasuryKycTab> {
  final TextEditingController _searchController = TextEditingController();
  String _statusFilter = 'all';
  int _offset = 0;
  final int _limit = 50;
  bool _isActionRunning = false;
  String? _actionId;
  late Future<GteAdminQueuePage<GteAdminKyc>> _queueFuture;

  @override
  void initState() {
    super.initState();
    _queueFuture = _fetchQueue();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<GteAdminQueuePage<GteAdminKyc>> _fetchQueue() {
    return widget.api.fetchAdminKyc(
      limit: _limit,
      offset: _offset,
      status: _statusFilter == 'all' ? null : _statusFilter,
      query: _searchController.text.trim().isEmpty
          ? null
          : _searchController.text.trim(),
    );
  }

  Future<void> _refresh() async {
    setState(() {
      _queueFuture = _fetchQueue();
    });
  }

  void _updateStatusFilter(String? value) {
    if (value == null) {
      return;
    }
    setState(() {
      _statusFilter = value;
      _offset = 0;
      _queueFuture = _fetchQueue();
    });
  }

  void _search() {
    setState(() {
      _offset = 0;
      _queueFuture = _fetchQueue();
    });
  }

  Future<void> _runAction(
    String actionId,
    Future<void> Function() task,
  ) async {
    setState(() {
      _isActionRunning = true;
      _actionId = actionId;
    });
    try {
      await task();
      if (!mounted) {
        return;
      }
      await _refresh();
    } catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(AppFeedback.messageFor(error))),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isActionRunning = false;
          _actionId = null;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<GteAdminQueuePage<GteAdminKyc>>(
      future: _queueFuture,
      builder: (BuildContext context,
          AsyncSnapshot<GteAdminQueuePage<GteAdminKyc>> snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }
        final GteAdminQueuePage<GteAdminKyc> page = snapshot.data ??
            GteAdminQueuePage<GteAdminKyc>(
              items: <GteAdminKyc>[],
              total: 0,
              limit: 50,
              offset: 0,
            );
        final List<GteAdminKyc> items = page.items;
        return RefreshIndicator(
          onRefresh: _refresh,
          child: ListView(
            padding: const EdgeInsets.all(20),
            children: <Widget>[
              GteSurfacePanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text('KYC queue',
                        style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _searchController,
                      decoration: const InputDecoration(
                        labelText: 'Search by user, email, NIN, BVN',
                        prefixIcon: Icon(Icons.search),
                      ),
                      onSubmitted: (_) => _search(),
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<String>(
                      value: _statusFilter,
                      items: _kycStatusFilters
                          .map((GteStatusFilter filter) =>
                              DropdownMenuItem<String>(
                                value: filter.value,
                                child: Text(filter.label),
                              ))
                          .toList(),
                      onChanged: _updateStatusFilter,
                      decoration:
                          const InputDecoration(labelText: 'Status filter'),
                    ),
                    const SizedBox(height: 12),
                    Align(
                      alignment: Alignment.centerRight,
                      child: FilledButton.tonal(
                        onPressed: _search,
                        child: const Text('Search'),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              if (items.isEmpty)
                const GteStatePanel(
                  title: 'No KYC submissions',
                  message: 'No KYC submissions match this filter.',
                  icon: Icons.verified_user_outlined,
                )
              else
                ...items.map((GteAdminKyc kyc) {
                  final bool isBusy =
                      _isActionRunning && _actionId == kyc.id;
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: GteSurfacePanel(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(kyc.userFullName ?? kyc.userEmail,
                              style: Theme.of(context).textTheme.titleMedium),
                          const SizedBox(height: 6),
                          Text(
                            'Status: ${_kycStatusLabel(kyc.status)}',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                          const SizedBox(height: 8),
                          Text('Email: ${kyc.userEmail}'),
                          if (kyc.userPhoneNumber != null)
                            Text('Phone: ${kyc.userPhoneNumber}'),
                          if (kyc.nin != null) Text('NIN: ${kyc.nin}'),
                          if (kyc.bvn != null) Text('BVN: ${kyc.bvn}'),
                          if (kyc.addressLine1 != null)
                            Text('Address: ${kyc.addressLine1}'),
                          if (kyc.city != null || kyc.state != null)
                            Text(
                              'City/state: ${kyc.city ?? ''} ${kyc.state ?? ''}',
                            ),
                          if (kyc.country != null)
                            Text('Country: ${kyc.country}'),
                          if (kyc.rejectionReason != null)
                            Text('Rejection: ${kyc.rejectionReason}'),
                          Text(
                            'Submitted: ${gteFormatDateTime(kyc.submittedAt)}',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                          const SizedBox(height: 12),
                          Wrap(
                            spacing: 8,
                            runSpacing: 8,
                            children: <Widget>[
                              FilledButton(
                                onPressed: isBusy
                                    ? null
                                    : () async {
                                        await _runAction(kyc.id, () async {
                                          await widget.api.adminReviewKyc(
                                            kyc.id,
                                            const GteKycReviewRequest(
                                              status:
                                                  GteKycStatus.fullyVerified,
                                            ),
                                          );
                                        });
                                      },
                                child: isBusy
                                    ? const SizedBox(
                                        width: 16,
                                        height: 16,
                                        child: CircularProgressIndicator(
                                            strokeWidth: 2),
                                      )
                                    : const Text('Approve full'),
                              ),
                              OutlinedButton(
                                onPressed: isBusy
                                    ? null
                                    : () async {
                                        await _runAction(kyc.id, () async {
                                          await widget.api.adminReviewKyc(
                                            kyc.id,
                                            const GteKycReviewRequest(
                                              status: GteKycStatus
                                                  .partialVerifiedNoId,
                                            ),
                                          );
                                        });
                                      },
                                child: const Text('Approve partial'),
                              ),
                              OutlinedButton(
                                onPressed: isBusy
                                    ? null
                                    : () async {
                                        final String? reason =
                                            await _promptForNotes(
                                          context,
                                          title: 'Reject KYC',
                                          hintText: 'Rejection reason',
                                        );
                                        await _runAction(kyc.id, () async {
                                          await widget.api.adminReviewKyc(
                                            kyc.id,
                                            GteKycReviewRequest(
                                              status: GteKycStatus.rejected,
                                              rejectionReason: reason,
                                            ),
                                          );
                                        });
                                      },
                                child: const Text('Reject'),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  );
                }),
              _QueuePager(
                total: page.total,
                limit: page.limit,
                offset: page.offset,
                onPageChanged: (int nextOffset) {
                  setState(() {
                    _offset = nextOffset;
                    _queueFuture = _fetchQueue();
                  });
                },
              ),
            ],
          ),
        );
      },
    );
  }
}

class _TreasuryDisputesTab extends StatefulWidget {
  const _TreasuryDisputesTab({required this.api});

  final GteExchangeApiClient api;

  @override
  State<_TreasuryDisputesTab> createState() => _TreasuryDisputesTabState();
}

class _TreasuryDisputesTabState extends State<_TreasuryDisputesTab> {
  final TextEditingController _searchController = TextEditingController();
  String _statusFilter = 'all';
  int _offset = 0;
  final int _limit = 50;
  late Future<GteAdminQueuePage<GteDispute>> _queueFuture;

  @override
  void initState() {
    super.initState();
    _queueFuture = _fetchQueue();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<GteAdminQueuePage<GteDispute>> _fetchQueue() {
    return widget.api.fetchAdminDisputes(
      limit: _limit,
      offset: _offset,
      status: _statusFilter == 'all' ? null : _statusFilter,
      query: _searchController.text.trim().isEmpty
          ? null
          : _searchController.text.trim(),
    );
  }

  Future<void> _refresh() async {
    setState(() {
      _queueFuture = _fetchQueue();
    });
  }

  void _updateStatusFilter(String? value) {
    if (value == null) {
      return;
    }
    setState(() {
      _statusFilter = value;
      _offset = 0;
      _queueFuture = _fetchQueue();
    });
  }

  void _search() {
    setState(() {
      _offset = 0;
      _queueFuture = _fetchQueue();
    });
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<GteAdminQueuePage<GteDispute>>(
      future: _queueFuture,
      builder: (BuildContext context,
          AsyncSnapshot<GteAdminQueuePage<GteDispute>> snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }
        final GteAdminQueuePage<GteDispute> page = snapshot.data ??
            GteAdminQueuePage<GteDispute>(
              items: <GteDispute>[],
              total: 0,
              limit: 50,
              offset: 0,
            );
        final List<GteDispute> items = page.items;
        return RefreshIndicator(
          onRefresh: _refresh,
          child: ListView(
            padding: const EdgeInsets.all(20),
            children: <Widget>[
              GteSurfacePanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text('Dispute queue',
                        style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _searchController,
                      decoration: const InputDecoration(
                        labelText: 'Search by reference or user',
                        prefixIcon: Icon(Icons.search),
                      ),
                      onSubmitted: (_) => _search(),
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<String>(
                      value: _statusFilter,
                      items: _disputeStatusFilters
                          .map((GteStatusFilter filter) =>
                              DropdownMenuItem<String>(
                                value: filter.value,
                                child: Text(filter.label),
                              ))
                          .toList(),
                      onChanged: _updateStatusFilter,
                      decoration:
                          const InputDecoration(labelText: 'Status filter'),
                    ),
                    const SizedBox(height: 12),
                    Align(
                      alignment: Alignment.centerRight,
                      child: FilledButton.tonal(
                        onPressed: _search,
                        child: const Text('Search'),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              if (items.isEmpty)
                const GteStatePanel(
                  title: 'No disputes',
                  message: 'No disputes match this filter.',
                  icon: Icons.support_agent_outlined,
                )
              else
                ...items.map((GteDispute dispute) {
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: GteSurfacePanel(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(dispute.reference,
                              style: Theme.of(context).textTheme.titleMedium),
                          const SizedBox(height: 6),
                          Text(
                            'Status: ${_disputeStatusLabel(dispute.status)}',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                          const SizedBox(height: 8),
                          Text(
                            dispute.subject ??
                                'Support thread for ${dispute.resourceType}',
                          ),
                          Text(
                            'User: ${dispute.userFullName ?? dispute.userEmail}',
                          ),
                          Text(
                            'Updated: ${gteFormatDateTime(dispute.lastMessageAt)}',
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                          const SizedBox(height: 12),
                          OutlinedButton(
                            onPressed: () {
                              Navigator.of(context).push<void>(
                                MaterialPageRoute<void>(
                                  builder: (BuildContext context) =>
                                      GteDisputeThreadScreen(
                                    api: widget.api,
                                    disputeId: dispute.id,
                                    isAdmin: true,
                                  ),
                                ),
                              );
                            },
                            child: const Text('Open thread'),
                          ),
                        ],
                      ),
                    ),
                  );
                }),
              _QueuePager(
                total: page.total,
                limit: page.limit,
                offset: page.offset,
                onPageChanged: (int nextOffset) {
                  setState(() {
                    _offset = nextOffset;
                    _queueFuture = _fetchQueue();
                  });
                },
              ),
            ],
          ),
        );
      },
    );
  }
}
class _TreasurySettingsTab extends StatefulWidget {
  const _TreasurySettingsTab({required this.api});

  final GteExchangeApiClient api;

  @override
  State<_TreasurySettingsTab> createState() => _TreasurySettingsTabState();
}

class _TreasurySettingsTabState extends State<_TreasurySettingsTab> {
  late Future<GteTreasurySettings> _settingsFuture;
  late Future<List<GteTreasuryBankAccount>> _bankAccountsFuture;

  final TextEditingController _depositRateController =
      TextEditingController();
  final TextEditingController _withdrawalRateController =
      TextEditingController();
  final TextEditingController _minDepositController = TextEditingController();
  final TextEditingController _maxDepositController = TextEditingController();
  final TextEditingController _minWithdrawalController =
      TextEditingController();
  final TextEditingController _maxWithdrawalController =
      TextEditingController();
  final TextEditingController _maintenanceController = TextEditingController();
  final TextEditingController _whatsappController = TextEditingController();

  GteRateDirection _depositDirection = GteRateDirection.fiatPerCoin;
  GteRateDirection _withdrawalDirection = GteRateDirection.fiatPerCoin;
  GtePaymentMode _depositMode = GtePaymentMode.manual;
  GtePaymentMode _withdrawalMode = GtePaymentMode.manual;

  bool _isSaving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _settingsFuture = widget.api.fetchTreasurySettings();
    _bankAccountsFuture = widget.api.listTreasuryBankAccounts();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    try {
      final GteTreasurySettings settings =
          await widget.api.fetchTreasurySettings();
      if (!mounted) {
        return;
      }
      setState(() {
        _depositRateController.text = settings.depositRateValue.toString();
        _withdrawalRateController.text =
            settings.withdrawalRateValue.toString();
        _minDepositController.text = settings.minDeposit.toString();
        _maxDepositController.text = settings.maxDeposit.toString();
        _minWithdrawalController.text = settings.minWithdrawal.toString();
        _maxWithdrawalController.text = settings.maxWithdrawal.toString();
        _maintenanceController.text = settings.maintenanceMessage ?? '';
        _whatsappController.text = settings.whatsappNumber ?? '';
        _depositDirection = settings.depositRateDirection;
        _withdrawalDirection = settings.withdrawalRateDirection;
        _depositMode = settings.depositMode;
        _withdrawalMode = settings.withdrawalMode;
      });
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = AppFeedback.messageFor(error);
      });
    }
  }

  @override
  void dispose() {
    _depositRateController.dispose();
    _withdrawalRateController.dispose();
    _minDepositController.dispose();
    _maxDepositController.dispose();
    _minWithdrawalController.dispose();
    _maxWithdrawalController.dispose();
    _maintenanceController.dispose();
    _whatsappController.dispose();
    super.dispose();
  }

  Future<void> _refresh() async {
    setState(() {
      _settingsFuture = widget.api.fetchTreasurySettings();
      _bankAccountsFuture = widget.api.listTreasuryBankAccounts();
    });
    await _loadSettings();
  }

  double? _parseAmount(String value) {
    final String trimmed = value.trim();
    if (trimmed.isEmpty) {
      return null;
    }
    return double.tryParse(trimmed);
  }

  Future<void> _saveSettings() async {
    setState(() {
      _isSaving = true;
      _error = null;
    });
    try {
      final double? depositRate = _parseAmount(_depositRateController.text);
      final double? withdrawalRate =
          _parseAmount(_withdrawalRateController.text);
      final double? minDeposit = _parseAmount(_minDepositController.text);
      final double? maxDeposit = _parseAmount(_maxDepositController.text);
      final double? minWithdrawal =
          _parseAmount(_minWithdrawalController.text);
      final double? maxWithdrawal =
          _parseAmount(_maxWithdrawalController.text);
      if (depositRate == null ||
          withdrawalRate == null ||
          minDeposit == null ||
          maxDeposit == null ||
          minWithdrawal == null ||
          maxWithdrawal == null) {
        throw Exception('All numeric fields must be valid numbers.');
      }
      final GteTreasurySettingsUpdate request = GteTreasurySettingsUpdate(
        depositRateValue: depositRate,
        depositRateDirection: _depositDirection,
        withdrawalRateValue: withdrawalRate,
        withdrawalRateDirection: _withdrawalDirection,
        minDeposit: minDeposit,
        maxDeposit: maxDeposit,
        minWithdrawal: minWithdrawal,
        maxWithdrawal: maxWithdrawal,
        depositMode: _depositMode,
        withdrawalMode: _withdrawalMode,
        maintenanceMessage: _maintenanceController.text.trim().isEmpty
            ? null
            : _maintenanceController.text.trim(),
        whatsappNumber: _whatsappController.text.trim().isEmpty
            ? null
            : _whatsappController.text.trim(),
      );
      await widget.api.updateTreasurySettings(request);
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Treasury settings updated.')),
      );
      await _refresh();
    } catch (error) {
      if (!mounted) {
        return;
      }
      setState(() {
        _error = AppFeedback.messageFor(error);
      });
    } finally {
      if (mounted) {
        setState(() {
          _isSaving = false;
        });
      }
    }
  }

  Future<void> _createBankAccount() async {
    final _BankAccountDraft? draft =
        await _promptForBankAccount(context);
    if (draft == null) {
      return;
    }
    try {
      await widget.api.createTreasuryBankAccount(
        GteTreasuryBankAccountCreate(
          bankName: draft.bankName,
          accountNumber: draft.accountNumber,
          accountName: draft.accountName,
          bankCode: draft.bankCode,
          currencyCode: draft.currencyCode,
          isActive: draft.isActive,
        ),
      );
      await _refresh();
    } catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(AppFeedback.messageFor(error))),
      );
    }
  }

  Future<void> _editBankAccount(GteTreasuryBankAccount account) async {
    final _BankAccountDraft? draft =
        await _promptForBankAccount(context, existing: account);
    if (draft == null) {
      return;
    }
    try {
      await widget.api.updateTreasuryBankAccount(
        account.id,
        GteTreasuryBankAccountUpdate(
          bankName: draft.bankName,
          accountNumber: draft.accountNumber,
          accountName: draft.accountName,
          bankCode: draft.bankCode,
          currencyCode: draft.currencyCode,
          isActive: draft.isActive,
        ),
      );
      await _refresh();
    } catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(AppFeedback.messageFor(error))),
      );
    }
  }

  Future<void> _setActiveBank(GteTreasuryBankAccount account) async {
    try {
      await widget.api.updateTreasuryBankAccount(
        account.id,
        const GteTreasuryBankAccountUpdate(isActive: true),
      );
      await _refresh();
    } catch (error) {
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(AppFeedback.messageFor(error))),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<GteTreasurySettings>(
      future: _settingsFuture,
      builder: (BuildContext context,
          AsyncSnapshot<GteTreasurySettings> snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Center(child: CircularProgressIndicator());
        }
        return RefreshIndicator(
          onRefresh: _refresh,
          child: ListView(
            padding: const EdgeInsets.all(20),
            children: <Widget>[
              if (_error != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: GteStatePanel(
                    title: 'Settings error',
                    message: _error!,
                    icon: Icons.error_outline,
                  ),
                ),
              GteSurfacePanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text('Treasury settings',
                        style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _depositRateController,
                      keyboardType:
                          const TextInputType.numberWithOptions(decimal: true),
                      decoration:
                          const InputDecoration(labelText: 'Deposit rate'),
                    ),
                    const SizedBox(height: 8),
                    DropdownButtonFormField<GteRateDirection>(
                      value: _depositDirection,
                      items: GteRateDirection.values
                          .map((GteRateDirection direction) =>
                              DropdownMenuItem<GteRateDirection>(
                                value: direction,
                                child: Text(_rateDirectionLabel(direction)),
                              ))
                          .toList(),
                      onChanged: (GteRateDirection? value) {
                        if (value == null) {
                          return;
                        }
                        setState(() {
                          _depositDirection = value;
                        });
                      },
                      decoration:
                          const InputDecoration(labelText: 'Deposit rate type'),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _withdrawalRateController,
                      keyboardType:
                          const TextInputType.numberWithOptions(decimal: true),
                      decoration:
                          const InputDecoration(labelText: 'Withdrawal rate'),
                    ),
                    const SizedBox(height: 8),
                    DropdownButtonFormField<GteRateDirection>(
                      value: _withdrawalDirection,
                      items: GteRateDirection.values
                          .map((GteRateDirection direction) =>
                              DropdownMenuItem<GteRateDirection>(
                                value: direction,
                                child: Text(_rateDirectionLabel(direction)),
                              ))
                          .toList(),
                      onChanged: (GteRateDirection? value) {
                        if (value == null) {
                          return;
                        }
                        setState(() {
                          _withdrawalDirection = value;
                        });
                      },
                      decoration: const InputDecoration(
                          labelText: 'Withdrawal rate type'),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: <Widget>[
                        Expanded(
                          child: TextField(
                            controller: _minDepositController,
                            keyboardType: const TextInputType.numberWithOptions(
                                decimal: true),
                            decoration: const InputDecoration(
                                labelText: 'Min deposit'),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: TextField(
                            controller: _maxDepositController,
                            keyboardType: const TextInputType.numberWithOptions(
                                decimal: true),
                            decoration: const InputDecoration(
                                labelText: 'Max deposit'),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: <Widget>[
                        Expanded(
                          child: TextField(
                            controller: _minWithdrawalController,
                            keyboardType: const TextInputType.numberWithOptions(
                                decimal: true),
                            decoration: const InputDecoration(
                                labelText: 'Min withdrawal'),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: TextField(
                            controller: _maxWithdrawalController,
                            keyboardType: const TextInputType.numberWithOptions(
                                decimal: true),
                            decoration: const InputDecoration(
                                labelText: 'Max withdrawal'),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    DropdownButtonFormField<GtePaymentMode>(
                      value: _depositMode,
                      items: GtePaymentMode.values
                          .map((GtePaymentMode mode) =>
                              DropdownMenuItem<GtePaymentMode>(
                                value: mode,
                                child: Text(_paymentModeLabel(mode)),
                              ))
                          .toList(),
                      onChanged: (GtePaymentMode? value) {
                        if (value == null) {
                          return;
                        }
                        setState(() {
                          _depositMode = value;
                        });
                      },
                      decoration:
                          const InputDecoration(labelText: 'Deposit mode'),
                    ),
                    const SizedBox(height: 8),
                    DropdownButtonFormField<GtePaymentMode>(
                      value: _withdrawalMode,
                      items: GtePaymentMode.values
                          .map((GtePaymentMode mode) =>
                              DropdownMenuItem<GtePaymentMode>(
                                value: mode,
                                child: Text(_paymentModeLabel(mode)),
                              ))
                          .toList(),
                      onChanged: (GtePaymentMode? value) {
                        if (value == null) {
                          return;
                        }
                        setState(() {
                          _withdrawalMode = value;
                        });
                      },
                      decoration:
                          const InputDecoration(labelText: 'Withdrawal mode'),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _maintenanceController,
                      decoration: const InputDecoration(
                        labelText: 'Maintenance message',
                      ),
                      maxLines: 2,
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _whatsappController,
                      decoration: const InputDecoration(
                        labelText: 'WhatsApp support number',
                      ),
                    ),
                    const SizedBox(height: 16),
                    Align(
                      alignment: Alignment.centerRight,
                      child: FilledButton(
                        onPressed: _isSaving ? null : _saveSettings,
                        child: _isSaving
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child:
                                    CircularProgressIndicator(strokeWidth: 2),
                              )
                            : const Text('Save settings'),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              GteSurfacePanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text('Bank instructions',
                        style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 12),
                    FutureBuilder<List<GteTreasuryBankAccount>>(
                      future: _bankAccountsFuture,
                      builder: (BuildContext context,
                          AsyncSnapshot<List<GteTreasuryBankAccount>>
                              snapshot) {
                        final List<GteTreasuryBankAccount> accounts =
                            snapshot.data ?? <GteTreasuryBankAccount>[];
                        return Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            if (accounts.isEmpty)
                              const Padding(
                                padding: EdgeInsets.only(bottom: 12),
                                child: Text(
                                  'No bank accounts configured yet.',
                                ),
                              )
                            else
                              ...accounts.map((GteTreasuryBankAccount account) {
                                return Padding(
                                  padding: const EdgeInsets.only(bottom: 12),
                                  child: Container(
                                    padding: const EdgeInsets.all(12),
                                    decoration: BoxDecoration(
                                      borderRadius: BorderRadius.circular(16),
                                      border: Border.all(
                                        color: GteShellTheme.stroke,
                                      ),
                                    ),
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: <Widget>[
                                        Text(
                                          '${account.bankName} - ${account.accountNumber}',
                                          style: Theme.of(context)
                                              .textTheme
                                              .titleSmall,
                                        ),
                                        Text(account.accountName),
                                        if (account.bankCode != null)
                                          Text('Bank code: ${account.bankCode}'),
                                        Text(
                                          'Currency: ${account.currencyCode}',
                                        ),
                                        Text(
                                          account.isActive
                                              ? 'Active'
                                              : 'Inactive',
                                          style: Theme.of(context)
                                              .textTheme
                                              .bodySmall,
                                        ),
                                        const SizedBox(height: 8),
                                        Wrap(
                                          spacing: 8,
                                          runSpacing: 8,
                                          children: <Widget>[
                                            OutlinedButton(
                                              onPressed: () =>
                                                  _editBankAccount(account),
                                              child: const Text('Edit'),
                                            ),
                                            if (!account.isActive)
                                              OutlinedButton(
                                                onPressed: () =>
                                                    _setActiveBank(account),
                                                child: const Text('Set active'),
                                              ),
                                          ],
                                        ),
                                      ],
                                    ),
                                  ),
                                );
                              }),
                            Align(
                              alignment: Alignment.centerRight,
                              child: FilledButton.tonal(
                                onPressed: _createBankAccount,
                                child: const Text('Add bank account'),
                              ),
                            ),
                          ],
                        );
                      },
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
class _QueuePager extends StatelessWidget {
  const _QueuePager({
    required this.total,
    required this.limit,
    required this.offset,
    required this.onPageChanged,
  });

  final int total;
  final int limit;
  final int offset;
  final ValueChanged<int> onPageChanged;

  @override
  Widget build(BuildContext context) {
    if (total <= limit) {
      return const SizedBox.shrink();
    }
    final int currentStart = offset + 1;
    final int currentEnd = (offset + limit) > total ? total : offset + limit;
    final bool hasPrev = offset > 0;
    final bool hasNext = offset + limit < total;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: <Widget>[
          Text('Showing $currentStart-$currentEnd of $total'),
          Row(
            children: <Widget>[
              OutlinedButton(
                onPressed:
                    hasPrev ? () => onPageChanged(offset - limit) : null,
                child: const Text('Prev'),
              ),
              const SizedBox(width: 8),
              OutlinedButton(
                onPressed:
                    hasNext ? () => onPageChanged(offset + limit) : null,
                child: const Text('Next'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

Future<String?> _promptForNotes(
  BuildContext context, {
  required String title,
  String? hintText,
}) async {
  final TextEditingController controller = TextEditingController();
  final String? result = await showDialog<String>(
    context: context,
    builder: (BuildContext context) {
      return AlertDialog(
        title: Text(title),
        content: TextField(
          controller: controller,
          decoration: InputDecoration(
            labelText: hintText ?? 'Notes',
          ),
          maxLines: 3,
        ),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () =>
                Navigator.of(context).pop(controller.text.trim()),
            child: const Text('Continue'),
          ),
        ],
      );
    },
  );
  controller.dispose();
  if (result == null || result.trim().isEmpty) {
    return null;
  }
  return result.trim();
}

Future<_BankAccountDraft?> _promptForBankAccount(
  BuildContext context, {
  GteTreasuryBankAccount? existing,
}) async {
  final TextEditingController bankNameController = TextEditingController(
    text: existing?.bankName ?? '',
  );
  final TextEditingController accountNumberController = TextEditingController(
    text: existing?.accountNumber ?? '',
  );
  final TextEditingController accountNameController = TextEditingController(
    text: existing?.accountName ?? '',
  );
  final TextEditingController bankCodeController = TextEditingController(
    text: existing?.bankCode ?? '',
  );
  final TextEditingController currencyController = TextEditingController(
    text: existing?.currencyCode ?? 'NGN',
  );
  bool isActive = existing?.isActive ?? true;

  final _BankAccountDraft? draft = await showDialog<_BankAccountDraft>(
    context: context,
    builder: (BuildContext context) {
      return StatefulBuilder(
        builder: (BuildContext context, void Function(void Function()) setModal) {
          return AlertDialog(
            title:
                Text(existing == null ? 'Add bank account' : 'Edit bank account'),
            content: SingleChildScrollView(
              child: Column(
                children: <Widget>[
                  TextField(
                    controller: bankNameController,
                    decoration: const InputDecoration(labelText: 'Bank name'),
                  ),
                  TextField(
                    controller: accountNumberController,
                    decoration:
                        const InputDecoration(labelText: 'Account number'),
                  ),
                  TextField(
                    controller: accountNameController,
                    decoration:
                        const InputDecoration(labelText: 'Account name'),
                  ),
                  TextField(
                    controller: bankCodeController,
                    decoration: const InputDecoration(
                        labelText: 'Bank code (optional)'),
                  ),
                  TextField(
                    controller: currencyController,
                    decoration:
                        const InputDecoration(labelText: 'Currency code'),
                  ),
                  const SizedBox(height: 12),
                  SwitchListTile(
                    value: isActive,
                    onChanged: (bool value) {
                      setModal(() {
                        isActive = value;
                      });
                    },
                    title: const Text('Active'),
                  ),
                ],
              ),
            ),
            actions: <Widget>[
              TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('Cancel'),
              ),
              FilledButton(
                onPressed: () {
                  final String bankName = bankNameController.text.trim();
                  final String accountNumber =
                      accountNumberController.text.trim();
                  final String accountName = accountNameController.text.trim();
                  if (bankName.isEmpty ||
                      accountNumber.isEmpty ||
                      accountName.isEmpty) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                          content: Text('Fill all required fields.')),
                    );
                    return;
                  }
                  Navigator.of(context).pop(_BankAccountDraft(
                    bankName: bankName,
                    accountNumber: accountNumber,
                    accountName: accountName,
                    bankCode: bankCodeController.text.trim().isEmpty
                        ? null
                        : bankCodeController.text.trim(),
                    currencyCode: currencyController.text.trim().isEmpty
                        ? 'NGN'
                        : currencyController.text.trim(),
                    isActive: isActive,
                  ));
                },
                child: const Text('Save'),
              ),
            ],
          );
        },
      );
    },
  );

  bankNameController.dispose();
  accountNumberController.dispose();
  accountNameController.dispose();
  bankCodeController.dispose();
  currencyController.dispose();
  return draft;
}

class _BankAccountDraft {
  const _BankAccountDraft({
    required this.bankName,
    required this.accountNumber,
    required this.accountName,
    required this.bankCode,
    required this.currencyCode,
    required this.isActive,
  });

  final String bankName;
  final String accountNumber;
  final String accountName;
  final String? bankCode;
  final String currencyCode;
  final bool isActive;
}

String _depositStatusLabel(GteDepositStatus status) {
  switch (status) {
    case GteDepositStatus.awaitingPayment:
      return 'Awaiting payment';
    case GteDepositStatus.paymentSubmitted:
      return 'Payment submitted';
    case GteDepositStatus.underReview:
      return 'Under review';
    case GteDepositStatus.confirmed:
      return 'Confirmed';
    case GteDepositStatus.rejected:
      return 'Rejected';
    case GteDepositStatus.expired:
      return 'Expired';
    case GteDepositStatus.disputed:
      return 'Disputed';
  }
}

String _withdrawalStatusLabel(GteWithdrawalStatus status) {
  switch (status) {
    case GteWithdrawalStatus.draft:
      return 'Draft';
    case GteWithdrawalStatus.pendingKyc:
      return 'Pending KYC';
    case GteWithdrawalStatus.pendingReview:
      return 'Pending review';
    case GteWithdrawalStatus.approved:
      return 'Approved';
    case GteWithdrawalStatus.rejected:
      return 'Rejected';
    case GteWithdrawalStatus.processing:
      return 'Processing';
    case GteWithdrawalStatus.paid:
      return 'Paid';
    case GteWithdrawalStatus.disputed:
      return 'Disputed';
    case GteWithdrawalStatus.cancelled:
      return 'Cancelled';
  }
}

String _kycStatusLabel(GteKycStatus status) {
  switch (status) {
    case GteKycStatus.unverified:
      return 'Unverified';
    case GteKycStatus.pending:
      return 'Pending';
    case GteKycStatus.partialVerifiedNoId:
      return 'Partial (no ID)';
    case GteKycStatus.fullyVerified:
      return 'Fully verified';
    case GteKycStatus.rejected:
      return 'Rejected';
  }
}

String _disputeStatusLabel(GteDisputeStatus status) {
  switch (status) {
    case GteDisputeStatus.open:
      return 'Open';
    case GteDisputeStatus.awaitingUser:
      return 'Awaiting user';
    case GteDisputeStatus.awaitingAdmin:
      return 'Awaiting admin';
    case GteDisputeStatus.resolved:
      return 'Resolved';
    case GteDisputeStatus.closed:
      return 'Closed';
  }
}

String _rateDirectionLabel(GteRateDirection direction) {
  switch (direction) {
    case GteRateDirection.fiatPerCoin:
      return 'Fiat per coin';
    case GteRateDirection.coinPerFiat:
      return 'Coin per fiat';
  }
}

String _paymentModeLabel(GtePaymentMode mode) {
  switch (mode) {
    case GtePaymentMode.manual:
      return 'Manual';
    case GtePaymentMode.automatic:
      return 'Automatic';
  }
}

class GteStatusFilter {
  const GteStatusFilter(this.value, this.label);

  final String value;
  final String label;
}

const List<GteStatusFilter> _depositStatusFilters = <GteStatusFilter>[
  GteStatusFilter('all', 'All deposits'),
  GteStatusFilter('awaiting_payment', 'Awaiting payment'),
  GteStatusFilter('payment_submitted', 'Payment submitted'),
  GteStatusFilter('under_review', 'Under review'),
  GteStatusFilter('confirmed', 'Confirmed'),
  GteStatusFilter('rejected', 'Rejected'),
  GteStatusFilter('expired', 'Expired'),
  GteStatusFilter('disputed', 'Disputed'),
];

const List<GteStatusFilter> _withdrawalStatusFilters = <GteStatusFilter>[
  GteStatusFilter('all', 'All withdrawals'),
  GteStatusFilter('pending_kyc', 'Pending KYC'),
  GteStatusFilter('pending_review', 'Pending review'),
  GteStatusFilter('approved', 'Approved'),
  GteStatusFilter('processing', 'Processing'),
  GteStatusFilter('paid', 'Paid'),
  GteStatusFilter('rejected', 'Rejected'),
  GteStatusFilter('disputed', 'Disputed'),
  GteStatusFilter('cancelled', 'Cancelled'),
];

const List<GteStatusFilter> _kycStatusFilters = <GteStatusFilter>[
  GteStatusFilter('all', 'All KYC'),
  GteStatusFilter('unverified', 'Unverified'),
  GteStatusFilter('pending', 'Pending'),
  GteStatusFilter('partial_verified_no_id', 'Partial (no ID)'),
  GteStatusFilter('fully_verified', 'Fully verified'),
  GteStatusFilter('rejected', 'Rejected'),
];

const List<GteStatusFilter> _disputeStatusFilters = <GteStatusFilter>[
  GteStatusFilter('all', 'All disputes'),
  GteStatusFilter('open', 'Open'),
  GteStatusFilter('awaiting_user', 'Awaiting user'),
  GteStatusFilter('awaiting_admin', 'Awaiting admin'),
  GteStatusFilter('resolved', 'Resolved'),
  GteStatusFilter('closed', 'Closed'),
];
