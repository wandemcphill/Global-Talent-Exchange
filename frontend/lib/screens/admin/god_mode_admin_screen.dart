import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../../core/app_feedback.dart';
import '../../data/gte_api_repository.dart';
import '../../widgets/gtex_branding.dart';
import 'treasury_ops_screen.dart';

class GodModeAdminScreen extends StatefulWidget {
  const GodModeAdminScreen({
    super.key,
    required this.baseUrl,
    required this.accessToken,
    this.backendMode = GteBackendMode.liveThenFixture,
  });

  final String baseUrl;
  final String accessToken;
  final GteBackendMode backendMode;

  @override
  State<GodModeAdminScreen> createState() => _GodModeAdminScreenState();
}

class _GodModeAdminScreenState extends State<GodModeAdminScreen> {
  late final GodModeAdminApi _api;
  GodModeBootstrap? _bootstrap;
  bool _isLoading = true;
  bool _isSaving = false;
  String? _error;

  final TextEditingController _buyCommissionController =
      TextEditingController();
  final TextEditingController _sellCommissionController =
      TextEditingController();
  final TextEditingController _instantSellFeeController =
      TextEditingController();
  final TextEditingController _withdrawalFeeController =
      TextEditingController();
  final TextEditingController _minimumWithdrawalFeeController =
      TextEditingController();
  final TextEditingController _commissionReasonController =
      TextEditingController(text: 'Admin policy refresh');

  final TextEditingController _liquidityUserController =
      TextEditingController();
  final TextEditingController _liquidityPlayerController =
      TextEditingController();
  final TextEditingController _liquidityQuantityController =
      TextEditingController(text: '1');
  final TextEditingController _liquidityPriceController =
      TextEditingController(text: '100');
  final TextEditingController _liquidityReasonController =
      TextEditingController(text: 'Desk rebalancing');
  String _liquidityAction = 'buy_from_user';

  final TextEditingController _treasuryAmountController =
      TextEditingController(text: '10');
  final TextEditingController _treasuryDestinationController =
      TextEditingController();
  final TextEditingController _treasuryReasonController =
      TextEditingController(text: 'Treasury sweep');
  String _treasuryUnit = 'credit';

  final TextEditingController _paymentRailReasonController =
      TextEditingController(text: 'Admin rail toggle update');
  final TextEditingController _competitionPoolTopupController =
      TextEditingController(text: '0');
  final TextEditingController _competitionControlReasonController =
      TextEditingController(text: 'Prize pool policy refresh');
  final TextEditingController _withdrawalControlReasonController =
      TextEditingController(text: 'Withdrawal control refresh');
  bool _egameWithdrawalsEnabled = false;
  bool _tradeWithdrawalsEnabled = true;
  bool _depositsViaBankTransfer = true;
  bool _payoutsViaBankTransfer = true;
  String _processorMode = 'manual_bank_transfer';
  final TextEditingController _liquidityConfirmationController =
      TextEditingController(text: 'CONFIRM LIQUIDITY ACTION');
  final TextEditingController _treasuryConfirmationController =
      TextEditingController(text: 'CONFIRM TREASURY WITHDRAWAL');
  final TextEditingController _auditSearchController = TextEditingController();
  String _withdrawalFilter = 'all';

  final TextEditingController _currentPasswordController =
      TextEditingController();
  final TextEditingController _newPasswordController = TextEditingController();
  final TextEditingController _confirmPasswordController =
      TextEditingController();

  @override
  void initState() {
    super.initState();
    _api = GodModeAdminApi(
      baseUrl: widget.baseUrl,
      accessToken: widget.accessToken,
      mode: widget.backendMode,
    );
    _load();
  }

  @override
  void dispose() {
    _buyCommissionController.dispose();
    _sellCommissionController.dispose();
    _instantSellFeeController.dispose();
    _withdrawalFeeController.dispose();
    _minimumWithdrawalFeeController.dispose();
    _commissionReasonController.dispose();
    _liquidityUserController.dispose();
    _liquidityPlayerController.dispose();
    _liquidityQuantityController.dispose();
    _liquidityPriceController.dispose();
    _liquidityReasonController.dispose();
    _treasuryAmountController.dispose();
    _treasuryDestinationController.dispose();
    _treasuryReasonController.dispose();
    _paymentRailReasonController.dispose();
    _competitionPoolTopupController.dispose();
    _competitionControlReasonController.dispose();
    _withdrawalControlReasonController.dispose();
    _liquidityConfirmationController.dispose();
    _treasuryConfirmationController.dispose();
    _auditSearchController.dispose();
    _currentPasswordController.dispose();
    _newPasswordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final GodModeBootstrap bootstrap = await _api.fetchBootstrap();
      _applyBootstrap(bootstrap);
      if (!mounted) {
        return;
      }
      setState(() {
        _bootstrap = bootstrap;
      });
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
          _isLoading = false;
        });
      }
    }
  }

  void _applyBootstrap(GodModeBootstrap bootstrap) {
    _buyCommissionController.text =
        bootstrap.commissions.buyCommissionBps.toString();
    _sellCommissionController.text =
        bootstrap.commissions.sellCommissionBps.toString();
    _instantSellFeeController.text =
        bootstrap.commissions.instantSellFeeBps.toString();
    _withdrawalFeeController.text =
        bootstrap.commissions.withdrawalFeeBps.toString();
    _minimumWithdrawalFeeController.text =
        bootstrap.commissions.minimumWithdrawalFeeCredits.toString();
    _competitionPoolTopupController.text =
        bootstrap.competitionControls.prizePoolTopupPct.toString();
    _egameWithdrawalsEnabled =
        bootstrap.withdrawalControls.egameWithdrawalsEnabled;
    _tradeWithdrawalsEnabled =
        bootstrap.withdrawalControls.tradeWithdrawalsEnabled;
    _depositsViaBankTransfer =
        bootstrap.withdrawalControls.depositsViaBankTransfer;
    _payoutsViaBankTransfer =
        bootstrap.withdrawalControls.payoutsViaBankTransfer;
    _processorMode = bootstrap.withdrawalControls.processorMode;
  }

  List<WithdrawalItem> get _visibleWithdrawals {
    final GodModeBootstrap? bootstrap = _bootstrap;
    if (bootstrap == null) {
      return const <WithdrawalItem>[];
    }
    return bootstrap.withdrawals.where((WithdrawalItem item) {
      return _withdrawalFilter == 'all' || item.status == _withdrawalFilter;
    }).toList(growable: false);
  }

  List<AuditEvent> get _visibleAuditEvents {
    final GodModeBootstrap? bootstrap = _bootstrap;
    if (bootstrap == null) {
      return const <AuditEvent>[];
    }
    final String term = _auditSearchController.text.trim().toLowerCase();
    return bootstrap.auditEvents.where((AuditEvent event) {
      if (term.isEmpty) {
        return true;
      }
      final String haystack =
          '\${event.summary} \${event.eventType} \${event.payload}'
              .toLowerCase();
      return haystack.contains(term);
    }).toList(growable: false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Admin God Mode'),
        actions: <Widget>[
          IconButton(
            onPressed: _isLoading ? null : _load,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading && _bootstrap == null) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error != null && _bootstrap == null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              const Icon(Icons.warning_amber_rounded, size: 40),
              const SizedBox(height: 12),
              Text(
                _error!,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: _load,
                child: const Text('Retry'),
              ),
            ],
          ),
        ),
      );
    }

    final GodModeBootstrap? bootstrap = _bootstrap;
    if (bootstrap == null) {
      return const SizedBox.shrink();
    }

    return ListView(
      padding: const EdgeInsets.all(16),
      children: <Widget>[
        GtexHeroBanner(
          eyebrow: 'CONTROL TOWER',
          title:
              'Admin should feel powerful, visible, and fenced in by integrity.',
          description:
              'This surface controls liquidity, payments, withdrawals, competition levers, and audit visibility. High-risk actions stay behind deliberate confirmation rails.',
          accent: Colors.redAccent,
          chips: <Widget>[
            _AdminHeroChip(label: 'Guardrails', value: 'STRICT'),
            _AdminHeroChip(label: 'Audit', value: 'ALWAYS ON'),
            _AdminHeroChip(label: 'Treasury', value: 'LIVE'),
          ],
        ),
        const SizedBox(height: 16),
        _SectionCard(
          title: 'Treasury Ops',
          icon: Icons.account_balance_outlined,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              const Text(
                'Open the dedicated treasury console for deposits, withdrawals, KYC, disputes, and rate settings.',
              ),
              const SizedBox(height: 12),
              FilledButton.icon(
                onPressed: () {
                  Navigator.of(context).push<void>(
                    MaterialPageRoute<void>(
                      builder: (BuildContext context) => GteTreasuryOpsScreen(
                        baseUrl: widget.baseUrl,
                        accessToken: widget.accessToken,
                        backendMode: widget.backendMode,
                      ),
                    ),
                  );
                },
                icon: const Icon(Icons.open_in_new),
                label: const Text('Open Treasury Ops'),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        _SectionCard(
          title: 'Admin Password',
          icon: Icons.password_outlined,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              const Text(
                'Change the seeded admin password after first login. The initial bootstrap credentials are only meant to get God Mode through the front door.',
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _currentPasswordController,
                obscureText: true,
                decoration:
                    const InputDecoration(labelText: 'Current password'),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _newPasswordController,
                obscureText: true,
                decoration: const InputDecoration(labelText: 'New password'),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _confirmPasswordController,
                obscureText: true,
                decoration:
                    const InputDecoration(labelText: 'Confirm new password'),
              ),
              const SizedBox(height: 12),
              FilledButton.tonal(
                onPressed: _isSaving ? null : _changeAdminPassword,
                child: const Text('Change admin password'),
              ),
            ],
          ),
        ),
        _SectionCard(
          title: 'Role & integrity bounds',
          icon: Icons.admin_panel_settings_outlined,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text('Role: ${bootstrap.profile.roleName}'),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: bootstrap.profile.permissions
                    .map((String permission) => Chip(label: Text(permission)))
                    .toList(growable: false),
              ),
              const SizedBox(height: 12),
              const Text(
                'Integrity rails are welded shut: this console cannot directly set arbitrary player prices or alter match and competition outcomes.',
              ),
            ],
          ),
        ),
        _SectionCard(
          title: 'Control tower snapshot',
          icon: Icons.dashboard_customize_outlined,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: <Widget>[
                  _MetricChip(
                      label: 'Queued withdrawals',
                      value:
                          bootstrap.withdrawalSummary.queuedAmount.toString()),
                  _MetricChip(
                      label: 'Immediate withdrawal eligible',
                      value: bootstrap.withdrawalSummary.immediateEligibleAmount
                          .toString()),
                  _MetricChip(
                      label: 'Manager trade fee revenue',
                      value: bootstrap
                          .treasuryDashboard.managerTradeFeeRevenueCredits
                          .toString()),
                  _MetricChip(
                      label: 'Open manager listings',
                      value: bootstrap.treasuryDashboard.openManagerListingCount
                          .toString()),
                  _MetricChip(
                      label: 'Live rails',
                      value: bootstrap.paymentRailHealth.liveCount.toString()),
                ],
              ),
              const SizedBox(height: 12),
              ...bootstrap.highRiskActions.map(
                (HighRiskAction action) => ListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  leading: const Icon(Icons.shield_outlined),
                  title: Text(action.label),
                  subtitle: Text(action.integrityNote),
                  trailing: Text(action.requiredPermission),
                ),
              ),
            ],
          ),
        ),
        _SectionCard(
          title: 'Treasury / Liquidity Desk',
          icon: Icons.account_balance_outlined,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              ...bootstrap.treasury.balances.map(
                (TreasuryBalance balance) => ListTile(
                  dense: true,
                  contentPadding: EdgeInsets.zero,
                  title: Text(balance.label),
                  subtitle: Text(balance.code),
                  trailing: Text('${balance.balance} ${balance.unit}'),
                ),
              ),
              const Divider(height: 24),
              Text(
                'Platform inventory',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 8),
              if (bootstrap.treasury.liquidityInventory.isEmpty)
                const Text(
                    'No platform position inventory has been created yet.')
              else
                ...bootstrap.treasury.liquidityInventory.map(
                  (LiquidityInventoryItem item) => ListTile(
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                    title: Text('Player ${item.playerId}'),
                    trailing: Text(item.balance.toString()),
                  ),
                ),
              const SizedBox(height: 16),
              Text(
                'Credit ${bootstrap.treasuryDashboard.platformCreditBalance} • Coin ${bootstrap.treasuryDashboard.platformCoinBalance} • Settled manager trades ${bootstrap.treasuryDashboard.settledManagerTradeCount}',
              ),
              const SizedBox(height: 8),
              DropdownButtonFormField<String>(
                initialValue: _liquidityAction,
                decoration: const InputDecoration(labelText: 'Action'),
                items: const <DropdownMenuItem<String>>[
                  DropdownMenuItem(
                    value: 'buy_from_user',
                    child: Text('Buy from user'),
                  ),
                  DropdownMenuItem(
                    value: 'sell_to_user',
                    child: Text('Sell to user'),
                  ),
                ],
                onChanged: (String? value) {
                  if (value == null) {
                    return;
                  }
                  setState(() {
                    _liquidityAction = value;
                  });
                },
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _liquidityUserController,
                decoration:
                    const InputDecoration(labelText: 'Counterparty user id'),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _liquidityPlayerController,
                decoration: const InputDecoration(labelText: 'Player id'),
              ),
              const SizedBox(height: 8),
              Row(
                children: <Widget>[
                  Expanded(
                    child: TextField(
                      controller: _liquidityQuantityController,
                      keyboardType:
                          const TextInputType.numberWithOptions(decimal: true),
                      decoration: const InputDecoration(labelText: 'Quantity'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextField(
                      controller: _liquidityPriceController,
                      keyboardType:
                          const TextInputType.numberWithOptions(decimal: true),
                      decoration: const InputDecoration(
                          labelText: 'Bounded unit price'),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _liquidityReasonController,
                decoration: const InputDecoration(labelText: 'Reason'),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _liquidityConfirmationController,
                decoration: const InputDecoration(
                  labelText: 'Confirmation text',
                  helperText:
                      'Type CONFIRM LIQUIDITY ACTION to unlock this high-risk action.',
                ),
              ),
              const SizedBox(height: 12),
              FilledButton.tonal(
                onPressed: _isSaving ? null : _submitLiquidityIntervention,
                child: const Text('Execute desk intervention'),
              ),
            ],
          ),
        ),
        _SectionCard(
          title: 'Commission Control',
          icon: Icons.percent_outlined,
          child: Column(
            children: <Widget>[
              _numberField(_buyCommissionController, 'Buy commission (bps)'),
              const SizedBox(height: 8),
              _numberField(_sellCommissionController, 'Sell commission (bps)'),
              const SizedBox(height: 8),
              _numberField(_instantSellFeeController, 'Instant sell fee (bps)'),
              const SizedBox(height: 8),
              _numberField(_withdrawalFeeController, 'Withdrawal fee (bps)'),
              const SizedBox(height: 8),
              _numberField(_minimumWithdrawalFeeController,
                  'Minimum withdrawal fee (credits)'),
              const SizedBox(height: 8),
              TextField(
                controller: _commissionReasonController,
                decoration: const InputDecoration(labelText: 'Reason'),
              ),
              const SizedBox(height: 12),
              FilledButton.tonal(
                onPressed: _isSaving ? null : _saveCommissions,
                child: const Text('Save commission settings'),
              ),
            ],
          ),
        ),
        _SectionCard(
          title: 'Withdrawal & Competition Controls',
          icon: Icons.tune_outlined,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              const Text(
                  'Adjust the withdrawal fee policy, decide whether e-game winnings can leave the platform, choose between automatic gateway processing and manual bank transfer operations, and tune the admin prize-pool lift.'),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                initialValue: _processorMode,
                decoration:
                    const InputDecoration(labelText: 'Payment processor mode'),
                items: const <DropdownMenuItem<String>>[
                  DropdownMenuItem(
                      value: 'automatic_gateway',
                      child: Text('Automatic gateway processor')),
                  DropdownMenuItem(
                      value: 'manual_bank_transfer',
                      child: Text('Manual bank transfer')),
                ],
                onChanged: _isSaving
                    ? null
                    : (String? value) => setState(
                        () => _processorMode = value ?? 'manual_bank_transfer'),
              ),
              const SizedBox(height: 8),
              SwitchListTile.adaptive(
                contentPadding: EdgeInsets.zero,
                title: const Text('Allow trade withdrawals'),
                subtitle: const Text(
                    'Toggle whether trade profits can be withdrawn out of the app.'),
                value: _tradeWithdrawalsEnabled,
                onChanged: _isSaving
                    ? null
                    : (bool value) =>
                        setState(() => _tradeWithdrawalsEnabled = value),
              ),
              SwitchListTile.adaptive(
                contentPadding: EdgeInsets.zero,
                title: const Text('Allow e-game winnings withdrawals'),
                subtitle: const Text(
                    'Off keeps the fallback model: winnings remain tradable in-app but cannot be withdrawn directly.'),
                value: _egameWithdrawalsEnabled,
                onChanged: _isSaving
                    ? null
                    : (bool value) =>
                        setState(() => _egameWithdrawalsEnabled = value),
              ),
              SwitchListTile.adaptive(
                contentPadding: EdgeInsets.zero,
                title: const Text('Receive deposits by bank transfer'),
                value: _depositsViaBankTransfer,
                onChanged: _isSaving
                    ? null
                    : (bool value) =>
                        setState(() => _depositsViaBankTransfer = value),
              ),
              SwitchListTile.adaptive(
                contentPadding: EdgeInsets.zero,
                title: const Text('Pay out withdrawals by bank transfer'),
                value: _payoutsViaBankTransfer,
                onChanged: _isSaving
                    ? null
                    : (bool value) =>
                        setState(() => _payoutsViaBankTransfer = value),
              ),
              const SizedBox(height: 8),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.04),
                  borderRadius: BorderRadius.circular(16),
                  border:
                      Border.all(color: Colors.white.withValues(alpha: 0.08)),
                ),
                child: const Text(
                    'Manual bank transfer keeps payouts in review until ops confirms the bank movement. Automatic gateway mode can move supported withdrawal requests straight into processing.'),
              ),
              const SizedBox(height: 8),
              _numberField(_competitionPoolTopupController,
                  'Competition pool top-up (%)'),
              const SizedBox(height: 8),
              TextField(
                controller: _competitionControlReasonController,
                decoration: const InputDecoration(
                    labelText: 'Reason for competition pool update'),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _withdrawalControlReasonController,
                decoration: const InputDecoration(
                    labelText: 'Reason for withdrawal toggle update'),
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: <Widget>[
                  FilledButton.tonal(
                    onPressed: _isSaving ? null : _saveWithdrawalControls,
                    child: const Text('Save withdrawal controls'),
                  ),
                  FilledButton.tonal(
                    onPressed: _isSaving ? null : _saveCompetitionControls,
                    child: const Text('Save competition pool controls'),
                  ),
                ],
              ),
            ],
          ),
        ),
        _SectionCard(
          title: 'Payment Rail Control',
          icon: Icons.credit_card_outlined,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                  'Live ${bootstrap.paymentRailHealth.liveCount} • Deposits ${bootstrap.paymentRailHealth.depositsEnabledCount} • Withdrawals ${bootstrap.paymentRailHealth.withdrawalsEnabledCount}'),
              if (bootstrap
                  .paymentRailHealth.pausedProviders.isNotEmpty) ...<Widget>[
                const SizedBox(height: 8),
                Text(
                    'Paused rails: ${bootstrap.paymentRailHealth.pausedProviders.join(', ')}'),
              ],
              const SizedBox(height: 12),
              ...bootstrap.paymentRails.map(
                (PaymentRail rail) => Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Row(
                          children: <Widget>[
                            Expanded(
                                child: Text(rail.provider,
                                    style: Theme.of(context)
                                        .textTheme
                                        .titleSmall)),
                            Switch.adaptive(
                              value: rail.isLive,
                              onChanged: _isSaving
                                  ? null
                                  : (bool value) {
                                      setState(() {
                                        rail.isLive = value;
                                        if (!value) {
                                          rail.depositsEnabled = false;
                                          rail.withdrawalsEnabled = false;
                                          rail.maintenanceMessage =
                                              'Temporarily paused by admin.';
                                        }
                                      });
                                    },
                            ),
                          ],
                        ),
                        CheckboxListTile(
                          value: rail.depositsEnabled,
                          dense: true,
                          contentPadding: EdgeInsets.zero,
                          title: const Text('Deposits enabled'),
                          onChanged: _isSaving || !rail.isLive
                              ? null
                              : (bool? value) => setState(
                                  () => rail.depositsEnabled = value ?? false),
                        ),
                        CheckboxListTile(
                          value: rail.withdrawalsEnabled,
                          dense: true,
                          contentPadding: EdgeInsets.zero,
                          title: const Text('Withdrawals enabled'),
                          onChanged: _isSaving || !rail.isLive
                              ? null
                              : (bool? value) => setState(() =>
                                  rail.withdrawalsEnabled = value ?? false),
                        ),
                        Text(rail.maintenanceMessage?.isNotEmpty == true
                            ? rail.maintenanceMessage!
                            : 'No maintenance message.'),
                      ],
                    ),
                  ),
                ),
              ),
              TextField(
                controller: _paymentRailReasonController,
                decoration: const InputDecoration(
                    labelText: 'Audit reason for rail changes'),
              ),
              const SizedBox(height: 12),
              FilledButton.tonal(
                onPressed: _isSaving ? null : _savePaymentRails,
                child: const Text('Publish payment rail switches'),
              ),
            ],
          ),
        ),
        _SectionCard(
          title: 'Withdrawal Oversight',
          icon: Icons.outbox_outlined,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: <Widget>[
                  _MetricChip(
                      label: 'Requested',
                      value: bootstrap.withdrawalSummary.requestedCount
                          .toString()),
                  _MetricChip(
                      label: 'Reviewing',
                      value: bootstrap.withdrawalSummary.reviewingCount
                          .toString()),
                  _MetricChip(
                      label: 'Held',
                      value: bootstrap.withdrawalSummary.heldCount.toString()),
                  _MetricChip(
                      label: 'Processing',
                      value: bootstrap.withdrawalSummary.processingCount
                          .toString()),
                  _MetricChip(
                      label: 'Completed',
                      value: bootstrap.withdrawalSummary.completedCount
                          .toString()),
                ],
              ),
              const SizedBox(height: 8),
              DropdownButtonFormField<String>(
                initialValue: _withdrawalFilter,
                decoration:
                    const InputDecoration(labelText: 'Filter by status'),
                items: const <DropdownMenuItem<String>>[
                  DropdownMenuItem(value: 'all', child: Text('All')),
                  DropdownMenuItem(
                      value: 'requested', child: Text('Requested')),
                  DropdownMenuItem(
                      value: 'reviewing', child: Text('Reviewing')),
                  DropdownMenuItem(value: 'held', child: Text('Held')),
                  DropdownMenuItem(
                      value: 'processing', child: Text('Processing')),
                  DropdownMenuItem(
                      value: 'completed', child: Text('Completed')),
                  DropdownMenuItem(value: 'rejected', child: Text('Rejected')),
                  DropdownMenuItem(value: 'failed', child: Text('Failed')),
                ],
                onChanged: (String? value) =>
                    setState(() => _withdrawalFilter = value ?? 'all'),
              ),
              const SizedBox(height: 12),
              if (_visibleWithdrawals.isEmpty)
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 8),
                  child: Text('No payout requests yet.'),
                )
              else
                ..._visibleWithdrawals.map(
                  (WithdrawalItem item) => Card(
                    margin: const EdgeInsets.only(bottom: 8),
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(
                            '${item.username ?? item.userId} • ${item.amount} ${item.unit}',
                            style: Theme.of(context).textTheme.titleSmall,
                          ),
                          const SizedBox(height: 4),
                          Text(
                              'Status: ${item.status} • Source: ${item.sourceScope}'),
                          Text('Destination: ${item.destinationReference}'),
                          Text(
                              'Fee: ${item.feeAmount} • Total debit: ${item.totalDebit}'),
                          const SizedBox(height: 8),
                          Wrap(
                            spacing: 8,
                            children: <Widget>[
                              OutlinedButton(
                                onPressed: _isSaving
                                    ? null
                                    : () =>
                                        _updateWithdrawal(item, 'reviewing'),
                                child: const Text('Review'),
                              ),
                              OutlinedButton(
                                onPressed: _isSaving
                                    ? null
                                    : () => _updateWithdrawal(item, 'held'),
                                child: const Text('Hold'),
                              ),
                              OutlinedButton(
                                onPressed: _isSaving
                                    ? null
                                    : () =>
                                        _updateWithdrawal(item, 'processing'),
                                child: const Text('Process'),
                              ),
                              FilledButton.tonal(
                                onPressed: _isSaving
                                    ? null
                                    : () =>
                                        _updateWithdrawal(item, 'completed'),
                                child: const Text('Complete'),
                              ),
                              TextButton(
                                onPressed: _isSaving
                                    ? null
                                    : () => _updateWithdrawal(item, 'rejected'),
                                child: const Text('Reject'),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
        _SectionCard(
          title: 'Treasury Withdrawal',
          icon: Icons.payments_outlined,
          child: Column(
            children: <Widget>[
              DropdownButtonFormField<String>(
                initialValue: _treasuryUnit,
                decoration: const InputDecoration(labelText: 'Unit'),
                items: const <DropdownMenuItem<String>>[
                  DropdownMenuItem(value: 'credit', child: Text('Credit')),
                  DropdownMenuItem(value: 'coin', child: Text('Coin')),
                ],
                onChanged: (String? value) {
                  if (value != null) {
                    setState(() {
                      _treasuryUnit = value;
                    });
                  }
                },
              ),
              const SizedBox(height: 8),
              _numberField(_treasuryAmountController, 'Amount'),
              const SizedBox(height: 8),
              TextField(
                controller: _treasuryDestinationController,
                decoration:
                    const InputDecoration(labelText: 'Destination reference'),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _treasuryReasonController,
                decoration: const InputDecoration(labelText: 'Reason'),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: _treasuryConfirmationController,
                decoration: const InputDecoration(
                  labelText: 'Confirmation text',
                  helperText:
                      'Type CONFIRM TREASURY WITHDRAWAL to unlock this action.',
                ),
              ),
              const SizedBox(height: 12),
              FilledButton.tonal(
                onPressed: _isSaving ? null : _submitTreasuryWithdrawal,
                child: const Text('Execute treasury withdrawal'),
              ),
            ],
          ),
        ),
        _SectionCard(
          title: 'Audit & Integrity',
          icon: Icons.history_toggle_off_outlined,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              const Text(
                'Every sensitive action is appended to the audit stream. Nothing here can directly edit prices outside bounded mechanisms or rewrite competition outcomes.',
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _auditSearchController,
                decoration:
                    const InputDecoration(labelText: 'Search audit stream'),
                onChanged: (_) => setState(() {}),
              ),
              const SizedBox(height: 12),
              ..._visibleAuditEvents.map(
                (AuditEvent event) => ExpansionTile(
                  tilePadding: EdgeInsets.zero,
                  childrenPadding: const EdgeInsets.only(bottom: 12),
                  title: Text(event.summary),
                  subtitle: Text('${event.eventType} • ${event.createdAt}'),
                  children: <Widget>[
                    Align(
                      alignment: Alignment.centerLeft,
                      child: SelectableText(event.payload.toString()),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _numberField(TextEditingController controller, String label) {
    return TextField(
      controller: controller,
      keyboardType: const TextInputType.numberWithOptions(decimal: true),
      decoration: InputDecoration(labelText: label),
    );
  }

  Future<void> _changeAdminPassword() async {
    if (_newPasswordController.text.trim().isEmpty ||
        _confirmPasswordController.text.trim().isEmpty ||
        _currentPasswordController.text.trim().isEmpty) {
      AppFeedback.showError(
          context, 'Enter current, new, and confirmation passwords.');
      return;
    }
    await _runSavingAction(() async {
      await _api.changePassword(
        currentPassword: _currentPasswordController.text,
        newPassword: _newPasswordController.text,
        confirmNewPassword: _confirmPasswordController.text,
      );
      _currentPasswordController.clear();
      _newPasswordController.clear();
      _confirmPasswordController.clear();
    });
  }

  Future<void> _saveCommissions() async {
    await _runSavingAction(() async {
      await _api.updateCommissions(
        buyCommissionBps: int.parse(_buyCommissionController.text.trim()),
        sellCommissionBps: int.parse(_sellCommissionController.text.trim()),
        instantSellFeeBps: int.parse(_instantSellFeeController.text.trim()),
        withdrawalFeeBps: int.parse(_withdrawalFeeController.text.trim()),
        minimumWithdrawalFeeCredits:
            double.parse(_minimumWithdrawalFeeController.text.trim()),
        reason: _commissionReasonController.text.trim(),
      );
      await _load();
    });
  }

  Future<void> _saveWithdrawalControls() async {
    await _runSavingAction(() async {
      await _api.updateWithdrawalControls(
        egameWithdrawalsEnabled: _egameWithdrawalsEnabled,
        tradeWithdrawalsEnabled: _tradeWithdrawalsEnabled,
        processorMode: _processorMode,
        depositsViaBankTransfer: _depositsViaBankTransfer,
        payoutsViaBankTransfer: _payoutsViaBankTransfer,
        reason: _withdrawalControlReasonController.text.trim(),
      );
      await _load();
    });
  }

  Future<void> _saveCompetitionControls() async {
    await _runSavingAction(() async {
      await _api.updateCompetitionControls(
        prizePoolTopupPct:
            double.parse(_competitionPoolTopupController.text.trim()),
        reason: _competitionControlReasonController.text.trim(),
      );
      await _load();
    });
  }

  Future<void> _savePaymentRails() async {
    final GodModeBootstrap? bootstrap = _bootstrap;
    if (bootstrap == null) {
      return;
    }
    await _runSavingAction(() async {
      await _api.updatePaymentRails(bootstrap.paymentRails,
          reason: _paymentRailReasonController.text.trim());
      await _load();
    });
  }

  Future<void> _submitLiquidityIntervention() async {
    await _runSavingAction(() async {
      await _api.executeLiquidityIntervention(
        action: _liquidityAction,
        userId: _liquidityUserController.text.trim(),
        playerId: _liquidityPlayerController.text.trim(),
        quantity: double.parse(_liquidityQuantityController.text.trim()),
        unitPriceCredits: double.parse(_liquidityPriceController.text.trim()),
        reason: _liquidityReasonController.text.trim(),
        confirmationText: _liquidityConfirmationController.text.trim(),
      );
      await _load();
    });
  }

  Future<void> _updateWithdrawal(WithdrawalItem item, String status) async {
    await _runSavingAction(() async {
      await _api.updateWithdrawal(
        payoutRequestId: item.payoutRequestId,
        status: status,
        notes: 'Updated from control tower',
      );
      await _load();
    });
  }

  Future<void> _submitTreasuryWithdrawal() async {
    await _runSavingAction(() async {
      await _api.createTreasuryWithdrawal(
        unit: _treasuryUnit,
        amount: double.parse(_treasuryAmountController.text.trim()),
        destinationReference: _treasuryDestinationController.text.trim(),
        reason: _treasuryReasonController.text.trim(),
        confirmationText: _treasuryConfirmationController.text.trim(),
      );
      await _load();
    });
  }

  Future<void> _runSavingAction(Future<void> Function() action) async {
    setState(() {
      _isSaving = true;
      _error = null;
    });
    try {
      await action();
      if (!mounted) {
        return;
      }
      AppFeedback.showSuccess(context, 'Admin update applied.');
    } catch (error) {
      if (!mounted) {
        return;
      }
      AppFeedback.showError(context, error);
    } finally {
      if (mounted) {
        setState(() {
          _isSaving = false;
        });
      }
    }
  }
}

class _MetricChip extends StatelessWidget {
  const _MetricChip({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Chip(label: Text('$label: $value'));
  }
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({
    required this.title,
    required this.icon,
    required this.child,
  });

  final String title;
  final IconData icon;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              children: <Widget>[
                Icon(icon),
                const SizedBox(width: 8),
                Text(title, style: Theme.of(context).textTheme.titleMedium),
              ],
            ),
            const SizedBox(height: 12),
            child,
          ],
        ),
      ),
    );
  }
}

class _AdminHeroChip extends StatelessWidget {
  const _AdminHeroChip({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            label,
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: Colors.white70,
                  letterSpacing: 0.6,
                ),
          ),
          const SizedBox(height: 2),
          Text(
            value,
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
                  fontWeight: FontWeight.w700,
                ),
          ),
        ],
      ),
    );
  }
}

class GodModeAdminApi {
  GodModeAdminApi({
    required this.baseUrl,
    required this.accessToken,
    required this.mode,
  });

  final String baseUrl;
  final String accessToken;
  final GteBackendMode mode;

  Uri _uri(String path) {
    final Uri base = Uri.parse(baseUrl.endsWith('/') ? baseUrl : '$baseUrl/');
    return base.resolve(path.startsWith('/') ? path.substring(1) : path);
  }

  Future<Map<String, Object?>> _request(
    String method,
    String path, {
    Object? body,
  }) async {
    final http.Client client = http.Client();
    try {
      final http.Request request = http.Request(method, _uri(path))
        ..headers['Accept'] = 'application/json'
        ..headers['Authorization'] = 'Bearer $accessToken';
      if (body != null) {
        request.headers['Content-Type'] = 'application/json';
        request.body = jsonEncode(body);
      }
      final http.StreamedResponse response =
          await client.send(request).timeout(const Duration(seconds: 8));
      final String text = await response.stream.bytesToString();
      final Object? decoded =
          text.trim().isEmpty ? <String, Object?>{} : jsonDecode(text);
      if (response.statusCode >= 400) {
        throw Exception(_decodeError(decoded));
      }
      if (decoded is Map<String, Object?>) {
        return decoded;
      }
      throw Exception('Unexpected admin response shape.');
    } finally {
      client.close();
    }
  }

  Future<List<Object?>> _requestList(String method, String path,
      {Object? body}) async {
    final http.Client client = http.Client();
    try {
      final http.Request request = http.Request(method, _uri(path))
        ..headers['Accept'] = 'application/json'
        ..headers['Authorization'] = 'Bearer $accessToken';
      if (body != null) {
        request.headers['Content-Type'] = 'application/json';
        request.body = jsonEncode(body);
      }
      final http.StreamedResponse response =
          await client.send(request).timeout(const Duration(seconds: 8));
      final String text = await response.stream.bytesToString();
      final Object? decoded =
          text.trim().isEmpty ? <Object?>[] : jsonDecode(text);
      if (response.statusCode >= 400) {
        throw Exception(_decodeError(decoded));
      }
      if (decoded is List<Object?>) {
        return decoded;
      }
      throw Exception('Unexpected admin list response shape.');
    } finally {
      client.close();
    }
  }

  Future<GodModeBootstrap> fetchBootstrap() async {
    final Map<String, Object?> json = await _request(
      'GET',
      '/api/admin/god-mode/bootstrap',
    );
    return GodModeBootstrap.fromJson(json);
  }

  Future<void> changePassword({
    required String currentPassword,
    required String newPassword,
    required String confirmNewPassword,
  }) async {
    await _request('POST', '/api/auth/change-password', body: <String, Object?>{
      'current_password': currentPassword,
      'new_password': newPassword,
      'confirm_new_password': confirmNewPassword,
    });
  }

  Future<void> updateCommissions({
    required int buyCommissionBps,
    required int sellCommissionBps,
    required int instantSellFeeBps,
    required int withdrawalFeeBps,
    required double minimumWithdrawalFeeCredits,
    required String reason,
  }) async {
    await _request('PUT', '/api/admin/god-mode/commissions',
        body: <String, Object?>{
          'buy_commission_bps': buyCommissionBps,
          'sell_commission_bps': sellCommissionBps,
          'instant_sell_fee_bps': instantSellFeeBps,
          'withdrawal_fee_bps': withdrawalFeeBps,
          'minimum_withdrawal_fee_credits': minimumWithdrawalFeeCredits,
          'reason': reason,
        });
  }

  Future<void> updatePaymentRails(List<PaymentRail> rails,
      {required String reason}) async {
    await _request('PUT', '/api/admin/god-mode/payment-rails',
        body: <String, Object?>{
          'reason': reason,
          'rails': rails
              .map((PaymentRail rail) => rail.toJson())
              .toList(growable: false),
        });
  }

  Future<void> updateWithdrawalControls({
    required bool egameWithdrawalsEnabled,
    required bool tradeWithdrawalsEnabled,
    required String processorMode,
    required bool depositsViaBankTransfer,
    required bool payoutsViaBankTransfer,
    required String reason,
  }) async {
    await _request('PUT', '/api/admin/god-mode/withdrawal-controls',
        body: <String, Object?>{
          'egame_withdrawals_enabled': egameWithdrawalsEnabled,
          'trade_withdrawals_enabled': tradeWithdrawalsEnabled,
          'processor_mode': processorMode,
          'deposits_via_bank_transfer': depositsViaBankTransfer,
          'payouts_via_bank_transfer': payoutsViaBankTransfer,
          'reason': reason,
        });
  }

  Future<void> updateCompetitionControls({
    required double prizePoolTopupPct,
    required String reason,
  }) async {
    await _request('PUT', '/api/admin/god-mode/competition-controls',
        body: <String, Object?>{
          'prize_pool_topup_pct': prizePoolTopupPct,
          'reason': reason,
        });
  }

  Future<void> executeLiquidityIntervention({
    required String action,
    required String userId,
    required String playerId,
    required double quantity,
    required double unitPriceCredits,
    required String reason,
    required String confirmationText,
  }) async {
    await _request('POST', '/api/admin/god-mode/liquidity/interventions',
        body: <String, Object?>{
          'action': action,
          'user_id': userId,
          'player_id': playerId,
          'quantity': quantity,
          'unit_price_credits': unitPriceCredits,
          'reason': reason,
          'confirmation_text': confirmationText,
        });
  }

  Future<void> updateWithdrawal({
    required String payoutRequestId,
    required String status,
    String? notes,
  }) async {
    await _request('PATCH', '/api/admin/god-mode/withdrawals/$payoutRequestId',
        body: <String, Object?>{'status': status, 'notes': notes});
  }

  Future<void> createTreasuryWithdrawal({
    required String unit,
    required double amount,
    required String destinationReference,
    required String reason,
    required String confirmationText,
  }) async {
    await _request('POST', '/api/admin/god-mode/treasury/withdrawals',
        body: <String, Object?>{
          'unit': unit,
          'amount': amount,
          'destination_reference': destinationReference,
          'reason': reason,
          'confirmation_text': confirmationText,
        });
  }

  String _decodeError(Object? decoded) {
    if (decoded is Map<String, Object?>) {
      final Object? detail = decoded['detail'];
      if (detail is String && detail.trim().isNotEmpty) {
        return detail;
      }
    }
    return 'Admin request failed.';
  }
}

class GodModeBootstrap {
  GodModeBootstrap({
    required this.profile,
    required this.commissions,
    required this.paymentRails,
    required this.withdrawalControls,
    required this.competitionControls,
    required this.treasury,
    required this.withdrawals,
    required this.withdrawalSummary,
    required this.paymentRailHealth,
    required this.treasuryDashboard,
    required this.highRiskActions,
    required this.auditEvents,
  });

  final GodModeProfile profile;
  final CommissionSettings commissions;
  final List<PaymentRail> paymentRails;
  final WithdrawalControls withdrawalControls;
  final CompetitionControls competitionControls;
  final TreasurySummary treasury;
  final List<WithdrawalItem> withdrawals;
  final WithdrawalSummary withdrawalSummary;
  final PaymentRailHealth paymentRailHealth;
  final TreasuryDashboard treasuryDashboard;
  final List<HighRiskAction> highRiskActions;
  final List<AuditEvent> auditEvents;

  factory GodModeBootstrap.fromJson(Map<String, Object?> json) {
    return GodModeBootstrap(
      profile: GodModeProfile.fromJson(_map(json['profile'])),
      commissions: CommissionSettings.fromJson(_map(json['commissions'])),
      paymentRails: _list(json['payment_rails'])
          .map((Object? value) => PaymentRail.fromJson(_map(value)))
          .toList(growable: true),
      withdrawalControls:
          WithdrawalControls.fromJson(_map(json['withdrawal_controls'])),
      competitionControls:
          CompetitionControls.fromJson(_map(json['competition_controls'])),
      treasury: TreasurySummary.fromJson(_map(json['treasury'])),
      withdrawals: _list(json['withdrawals'])
          .map((Object? value) => WithdrawalItem.fromJson(_map(value)))
          .toList(growable: false),
      withdrawalSummary:
          WithdrawalSummary.fromJson(_map(json['withdrawal_summary'])),
      paymentRailHealth:
          PaymentRailHealth.fromJson(_map(json['payment_rail_health'])),
      treasuryDashboard:
          TreasuryDashboard.fromJson(_map(json['treasury_dashboard'])),
      highRiskActions: _list(json['high_risk_actions'])
          .map((Object? value) => HighRiskAction.fromJson(_map(value)))
          .toList(growable: false),
      auditEvents: _list(json['audit_events'])
          .map((Object? value) => AuditEvent.fromJson(_map(value)))
          .toList(growable: false),
    );
  }
}

class GodModeProfile {
  GodModeProfile({required this.roleName, required this.permissions});

  final String roleName;
  final List<String> permissions;

  factory GodModeProfile.fromJson(Map<String, Object?> json) => GodModeProfile(
        roleName: (json['role_name'] ?? 'god_mode').toString(),
        permissions: _list(json['permissions'])
            .map((Object? value) => value.toString())
            .toList(growable: false),
      );
}

class CommissionSettings {
  CommissionSettings({
    required this.buyCommissionBps,
    required this.sellCommissionBps,
    required this.instantSellFeeBps,
    required this.withdrawalFeeBps,
    required this.minimumWithdrawalFeeCredits,
  });

  final int buyCommissionBps;
  final int sellCommissionBps;
  final int instantSellFeeBps;
  final int withdrawalFeeBps;
  final num minimumWithdrawalFeeCredits;

  factory CommissionSettings.fromJson(Map<String, Object?> json) =>
      CommissionSettings(
        buyCommissionBps: (json['buy_commission_bps'] ?? 0) as int,
        sellCommissionBps: (json['sell_commission_bps'] ?? 0) as int,
        instantSellFeeBps: (json['instant_sell_fee_bps'] ?? 0) as int,
        withdrawalFeeBps: (json['withdrawal_fee_bps'] ?? 0) as int,
        minimumWithdrawalFeeCredits:
            _num(json['minimum_withdrawal_fee_credits']),
      );
}

class PaymentRail {
  PaymentRail({
    required this.provider,
    required this.depositsEnabled,
    required this.withdrawalsEnabled,
    required this.isLive,
    required this.maintenanceMessage,
  });

  final String provider;
  bool depositsEnabled;
  bool withdrawalsEnabled;
  bool isLive;
  String? maintenanceMessage;

  factory PaymentRail.fromJson(Map<String, Object?> json) => PaymentRail(
        provider: (json['provider'] ?? '').toString(),
        depositsEnabled: json['deposits_enabled'] as bool? ?? true,
        withdrawalsEnabled: json['withdrawals_enabled'] as bool? ?? true,
        isLive: json['is_live'] as bool? ?? true,
        maintenanceMessage: json['maintenance_message'] as String?,
      );

  Map<String, Object?> toJson() => <String, Object?>{
        'provider': provider,
        'deposits_enabled': depositsEnabled,
        'withdrawals_enabled': withdrawalsEnabled,
        'is_live': isLive,
        'maintenance_message': maintenanceMessage,
      };
}

class WithdrawalControls {
  WithdrawalControls({
    required this.egameWithdrawalsEnabled,
    required this.tradeWithdrawalsEnabled,
    required this.processorMode,
    required this.depositsViaBankTransfer,
    required this.payoutsViaBankTransfer,
  });

  final bool egameWithdrawalsEnabled;
  final bool tradeWithdrawalsEnabled;
  final String processorMode;
  final bool depositsViaBankTransfer;
  final bool payoutsViaBankTransfer;

  factory WithdrawalControls.fromJson(Map<String, Object?> json) =>
      WithdrawalControls(
        egameWithdrawalsEnabled:
            json['egame_withdrawals_enabled'] as bool? ?? false,
        tradeWithdrawalsEnabled:
            json['trade_withdrawals_enabled'] as bool? ?? true,
        processorMode:
            (json['processor_mode'] ?? 'manual_bank_transfer').toString(),
        depositsViaBankTransfer:
            json['deposits_via_bank_transfer'] as bool? ?? true,
        payoutsViaBankTransfer:
            json['payouts_via_bank_transfer'] as bool? ?? true,
      );
}

class CompetitionControls {
  CompetitionControls({required this.prizePoolTopupPct});

  final num prizePoolTopupPct;

  factory CompetitionControls.fromJson(Map<String, Object?> json) =>
      CompetitionControls(
        prizePoolTopupPct: _num(json['prize_pool_topup_pct']),
      );
}

class WithdrawalSummary {
  WithdrawalSummary({
    required this.requestedCount,
    required this.reviewingCount,
    required this.heldCount,
    required this.processingCount,
    required this.completedCount,
    required this.queuedAmount,
    required this.immediateEligibleAmount,
  });

  final int requestedCount;
  final int reviewingCount;
  final int heldCount;
  final int processingCount;
  final int completedCount;
  final num queuedAmount;
  final num immediateEligibleAmount;

  factory WithdrawalSummary.fromJson(Map<String, Object?> json) =>
      WithdrawalSummary(
        requestedCount: (json['requested_count'] ?? 0) as int,
        reviewingCount: (json['reviewing_count'] ?? 0) as int,
        heldCount: (json['held_count'] ?? 0) as int,
        processingCount: (json['processing_count'] ?? 0) as int,
        completedCount: (json['completed_count'] ?? 0) as int,
        queuedAmount: _num(json['queued_amount']),
        immediateEligibleAmount: _num(json['immediate_eligible_amount']),
      );
}

class PaymentRailHealth {
  PaymentRailHealth({
    required this.liveCount,
    required this.depositsEnabledCount,
    required this.withdrawalsEnabledCount,
    required this.pausedProviders,
  });

  final int liveCount;
  final int depositsEnabledCount;
  final int withdrawalsEnabledCount;
  final List<String> pausedProviders;

  factory PaymentRailHealth.fromJson(Map<String, Object?> json) =>
      PaymentRailHealth(
        liveCount: (json['live_count'] ?? 0) as int,
        depositsEnabledCount: (json['deposits_enabled_count'] ?? 0) as int,
        withdrawalsEnabledCount:
            (json['withdrawals_enabled_count'] ?? 0) as int,
        pausedProviders: _list(json['paused_providers'])
            .map((Object? value) => value.toString())
            .toList(growable: false),
      );
}

class TreasuryDashboard {
  TreasuryDashboard({
    required this.platformCreditBalance,
    required this.platformCoinBalance,
    required this.managerTradeFeeRevenueCredits,
    required this.openManagerListingCount,
    required this.settledManagerTradeCount,
  });

  final num platformCreditBalance;
  final num platformCoinBalance;
  final num managerTradeFeeRevenueCredits;
  final int openManagerListingCount;
  final int settledManagerTradeCount;

  factory TreasuryDashboard.fromJson(Map<String, Object?> json) =>
      TreasuryDashboard(
        platformCreditBalance: _num(json['platform_credit_balance']),
        platformCoinBalance: _num(json['platform_coin_balance']),
        managerTradeFeeRevenueCredits:
            _num(json['manager_trade_fee_revenue_credits']),
        openManagerListingCount:
            (json['open_manager_listing_count'] ?? 0) as int,
        settledManagerTradeCount:
            (json['settled_manager_trade_count'] ?? 0) as int,
      );
}

class HighRiskAction {
  HighRiskAction({
    required this.label,
    required this.requiredPermission,
    required this.integrityNote,
  });

  final String label;
  final String requiredPermission;
  final String integrityNote;

  factory HighRiskAction.fromJson(Map<String, Object?> json) => HighRiskAction(
        label: (json['label'] ?? '').toString(),
        requiredPermission: (json['required_permission'] ?? '').toString(),
        integrityNote: (json['integrity_note'] ?? '').toString(),
      );
}

class TreasurySummary {
  TreasurySummary({
    required this.balances,
    required this.liquidityInventory,
  });

  final List<TreasuryBalance> balances;
  final List<LiquidityInventoryItem> liquidityInventory;

  factory TreasurySummary.fromJson(Map<String, Object?> json) =>
      TreasurySummary(
        balances: _list(json['balances'])
            .map((Object? value) => TreasuryBalance.fromJson(_map(value)))
            .toList(growable: false),
        liquidityInventory: _list(json['liquidity_inventory'])
            .map(
                (Object? value) => LiquidityInventoryItem.fromJson(_map(value)))
            .toList(growable: false),
      );
}

class TreasuryBalance {
  TreasuryBalance({
    required this.code,
    required this.label,
    required this.unit,
    required this.balance,
  });

  final String code;
  final String label;
  final String unit;
  final num balance;

  factory TreasuryBalance.fromJson(Map<String, Object?> json) =>
      TreasuryBalance(
        code: (json['code'] ?? '').toString(),
        label: (json['label'] ?? '').toString(),
        unit: (json['unit'] ?? '').toString(),
        balance: _num(json['balance']),
      );
}

class LiquidityInventoryItem {
  LiquidityInventoryItem({required this.playerId, required this.balance});

  final String playerId;
  final num balance;

  factory LiquidityInventoryItem.fromJson(Map<String, Object?> json) =>
      LiquidityInventoryItem(
        playerId: (json['player_id'] ?? '').toString(),
        balance: _num(json['balance']),
      );
}

class WithdrawalItem {
  WithdrawalItem({
    required this.payoutRequestId,
    required this.userId,
    required this.username,
    required this.amount,
    required this.feeAmount,
    required this.totalDebit,
    required this.sourceScope,
    required this.unit,
    required this.status,
    required this.destinationReference,
  });

  final String payoutRequestId;
  final String userId;
  final String? username;
  final num amount;
  final num feeAmount;
  final num totalDebit;
  final String sourceScope;
  final String unit;
  final String status;
  final String destinationReference;

  factory WithdrawalItem.fromJson(Map<String, Object?> json) => WithdrawalItem(
        payoutRequestId: (json['payout_request_id'] ?? '').toString(),
        userId: (json['user_id'] ?? '').toString(),
        username: json['username'] as String?,
        amount: _num(json['amount']),
        feeAmount: _num(json['fee_amount']),
        totalDebit: _num(json['total_debit']),
        sourceScope: (json['source_scope'] ?? 'trade').toString(),
        unit: (json['unit'] ?? '').toString(),
        status: (json['status'] ?? '').toString(),
        destinationReference: (json['destination_reference'] ?? '').toString(),
      );
}

class AuditEvent {
  AuditEvent({
    required this.eventType,
    required this.summary,
    required this.createdAt,
    required this.payload,
  });

  final String eventType;
  final String summary;
  final String createdAt;
  final Map<String, Object?> payload;

  factory AuditEvent.fromJson(Map<String, Object?> json) => AuditEvent(
        eventType: (json['event_type'] ?? '').toString(),
        summary: (json['summary'] ?? '').toString(),
        createdAt: (json['created_at'] ?? '').toString(),
        payload: _auditPayload(json),
      );
}

Map<String, Object?> _auditPayload(Map<String, Object?> json) {
  for (final String key in <String>[
    'payload',
    'payload_json',
    'metadata',
    'metadata_json',
  ]) {
    final Object? value = json[key];
    if (value == null) {
      continue;
    }
    return _map(value);
  }
  return const <String, Object?>{};
}

Map<String, Object?> _map(Object? value) {
  if (value is Map<String, Object?>) {
    return value;
  }
  if (value is Map) {
    return value
        .map((Object? key, Object? item) => MapEntry(key.toString(), item));
  }
  return <String, Object?>{};
}

num _num(Object? value) {
  if (value is num) {
    return value;
  }
  return num.tryParse((value ?? '0').toString()) ?? 0;
}

List<Object?> _list(Object? value) {
  if (value is List<Object?>) {
    return value;
  }
  if (value is List) {
    return value.cast<Object?>();
  }
  return const <Object?>[];
}
