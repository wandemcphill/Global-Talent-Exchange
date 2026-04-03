import 'package:flutter/material.dart';

import '../../core/app_feedback.dart';
import '../../data/admin_command_center_api.dart';
import '../../data/gte_api_repository.dart';
import '../../data/gte_models.dart';
import '../../features/app_routes/gte_navigation_helpers.dart';
import '../../features/app_routes/gte_route_data.dart';
import '../../features/navigation_guards/gte_navigation_guards.dart';
import '../../widgets/gte_formatters.dart';
import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';

class AdminCommandCenterScreen extends StatefulWidget {
  const AdminCommandCenterScreen({
    super.key,
    required this.baseUrl,
    required this.accessToken,
    required this.backendMode,
  });

  final String baseUrl;
  final String accessToken;
  final GteBackendMode backendMode;

  @override
  State<AdminCommandCenterScreen> createState() =>
      _AdminCommandCenterScreenState();
}

class _AdminCommandCenterScreenState extends State<AdminCommandCenterScreen> {
  late final AdminCommandCenterApi _api;

  final TextEditingController _depositRateController = TextEditingController();
  final TextEditingController _withdrawalRateController =
      TextEditingController();
  final TextEditingController _minDepositController = TextEditingController();
  final TextEditingController _maxDepositController = TextEditingController();
  final TextEditingController _minWithdrawalController =
      TextEditingController();
  final TextEditingController _maxWithdrawalController =
      TextEditingController();
  final TextEditingController _whatsappController = TextEditingController();
  final TextEditingController _maintenanceController = TextEditingController();
  final TextEditingController _railsReasonController = TextEditingController();
  final TextEditingController _withdrawalReasonController =
      TextEditingController();
  final TextEditingController _bankNameController = TextEditingController();
  final TextEditingController _bankAccountNumberController =
      TextEditingController();
  final TextEditingController _bankAccountNameController =
      TextEditingController();
  final TextEditingController _bankCodeController = TextEditingController();
  final TextEditingController _creditUserIdController = TextEditingController();
  final TextEditingController _creditAmountController = TextEditingController();
  final TextEditingController _creditNotesController = TextEditingController();

  bool _loading = true;
  bool _savingTreasury = false;
  bool _savingRails = false;
  bool _savingWithdrawalControls = false;
  bool _creatingBankAccount = false;
  bool _previewingCredit = false;
  bool _runningCredit = false;
  String? _error;

  GteTreasurySettings? _treasurySettings;
  List<GteTreasuryBankAccount> _bankAccounts = <GteTreasuryBankAccount>[];
  GteAdminQueuePage<GteAdminDeposit>? _depositQueue;
  List<AdminPaymentRail> _paymentRails = <AdminPaymentRail>[];
  AdminWithdrawalControls? _withdrawalControls;
  AdminMarketTopupQuote? _creditQuote;
  AdminMarketTopup? _lastCreditResult;

  GtePaymentMode _depositMode = GtePaymentMode.manual;
  GtePaymentMode _withdrawalMode = GtePaymentMode.manual;
  String? _activeBankAccountId;
  final Set<String> _depositBusyIds = <String>{};
  final Set<String> _bankBusyIds = <String>{};

  GteNavigationDependencies get _dependencies => GteNavigationDependencies(
    apiBaseUrl: widget.baseUrl,
    backendMode: widget.backendMode,
    accessToken: widget.accessToken,
    isAuthenticated: widget.accessToken.trim().isNotEmpty,
    currentUserRole: 'admin',
  );

  @override
  void initState() {
    super.initState();
    _api = AdminCommandCenterApi.standard(
      baseUrl: widget.baseUrl,
      accessToken: widget.accessToken,
      mode: widget.backendMode,
    );
    _load();
  }

  @override
  void dispose() {
    _depositRateController.dispose();
    _withdrawalRateController.dispose();
    _minDepositController.dispose();
    _maxDepositController.dispose();
    _minWithdrawalController.dispose();
    _maxWithdrawalController.dispose();
    _whatsappController.dispose();
    _maintenanceController.dispose();
    _railsReasonController.dispose();
    _withdrawalReasonController.dispose();
    _bankNameController.dispose();
    _bankAccountNumberController.dispose();
    _bankAccountNameController.dispose();
    _bankCodeController.dispose();
    _creditUserIdController.dispose();
    _creditAmountController.dispose();
    _creditNotesController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final List<dynamic> payload =
          await Future.wait<dynamic>(<Future<dynamic>>[
            _api.fetchTreasurySettings(),
            _api.listTreasuryBankAccounts(),
            _api.fetchAdminDeposits(limit: 20),
            _api.fetchPaymentRails(),
            _api.fetchWithdrawalControls(),
          ]);
      if (!mounted) {
        return;
      }
      final GteTreasurySettings settings = payload[0] as GteTreasurySettings;
      setState(() {
        _treasurySettings = settings;
        _bankAccounts = payload[1] as List<GteTreasuryBankAccount>;
        _depositQueue = payload[2] as GteAdminQueuePage<GteAdminDeposit>;
        _paymentRails = (payload[3] as AdminPaymentRailsState).rails;
        _withdrawalControls = payload[4] as AdminWithdrawalControls;
        _seedTreasuryEditors(settings);
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
          _loading = false;
        });
      }
    }
  }

  void _seedTreasuryEditors(GteTreasurySettings settings) {
    _depositMode = settings.depositMode;
    _withdrawalMode = settings.withdrawalMode;
    _activeBankAccountId = settings.activeBankAccount?.id;
    _depositRateController.text = settings.depositRateValue.toStringAsFixed(2);
    _withdrawalRateController.text = settings.withdrawalRateValue
        .toStringAsFixed(2);
    _minDepositController.text = settings.minDeposit.toStringAsFixed(2);
    _maxDepositController.text = settings.maxDeposit.toStringAsFixed(2);
    _minWithdrawalController.text = settings.minWithdrawal.toStringAsFixed(2);
    _maxWithdrawalController.text = settings.maxWithdrawal.toStringAsFixed(2);
    _whatsappController.text = settings.whatsappNumber ?? '';
    _maintenanceController.text = settings.maintenanceMessage ?? '';
  }

  Future<void> _openRoute(BuildContext context, GteAppRouteData route) {
    return GteNavigationHelpers.pushRoute<void>(
      context,
      route: route,
      dependencies: _dependencies,
    );
  }

  Widget _buildRouteLauncher({
    required BuildContext context,
    required String label,
    required IconData icon,
    required GteAppRouteData route,
    bool emphasized = false,
  }) {
    void onPressed() {
      _openRoute(context, route);
    }

    if (emphasized) {
      return FilledButton.icon(
        onPressed: onPressed,
        icon: Icon(icon),
        label: Text(label),
      );
    }
    return FilledButton.tonalIcon(
      onPressed: onPressed,
      icon: Icon(icon),
      label: Text(label),
    );
  }

  double? _parseDouble(String raw) => double.tryParse(raw.trim());

  String _paymentModeLabel(GtePaymentMode mode) {
    switch (mode) {
      case GtePaymentMode.manual:
        return 'Manual only';
      case GtePaymentMode.automatic:
        return 'Automatic only';
      case GtePaymentMode.hybrid:
        return 'Hybrid';
    }
  }

  String _providerLabel(String provider) {
    final Map<String, String> labels = <String, String>{
      'bank_transfer_manual': 'Manual bank transfer',
      'paystack': 'Paystack',
      'korapay': 'KoraPay',
      'flutterwave': 'Flutterwave',
      'monnify': 'Monnify',
    };
    return labels[provider.trim().toLowerCase()] ?? _humanize(provider);
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

  String _humanize(String value) {
    final List<String> parts = value
        .split(RegExp(r'[_\s-]+'))
        .map((String part) => part.trim())
        .where((String part) => part.isNotEmpty)
        .toList(growable: false);
    if (parts.isEmpty) {
      return value;
    }
    return parts
        .map(
          (String part) =>
              '${part[0].toUpperCase()}${part.substring(1).toLowerCase()}',
        )
        .join(' ');
  }

  Future<void> _saveTreasurySettings() async {
    final double? depositRate = _parseDouble(_depositRateController.text);
    final double? withdrawalRate = _parseDouble(_withdrawalRateController.text);
    final double? minDeposit = _parseDouble(_minDepositController.text);
    final double? maxDeposit = _parseDouble(_maxDepositController.text);
    final double? minWithdrawal = _parseDouble(_minWithdrawalController.text);
    final double? maxWithdrawal = _parseDouble(_maxWithdrawalController.text);
    if (<double?>[
      depositRate,
      withdrawalRate,
      minDeposit,
      maxDeposit,
      minWithdrawal,
      maxWithdrawal,
    ].contains(null)) {
      AppFeedback.showError(
        context,
        'Enter valid numeric values for treasury settings.',
      );
      return;
    }
    setState(() {
      _savingTreasury = true;
    });
    try {
      final GteTreasurySettings updated = await _api.updateTreasurySettings(
        GteTreasurySettingsUpdate(
          depositRateValue: depositRate,
          withdrawalRateValue: withdrawalRate,
          minDeposit: minDeposit,
          maxDeposit: maxDeposit,
          minWithdrawal: minWithdrawal,
          maxWithdrawal: maxWithdrawal,
          depositMode: _depositMode,
          withdrawalMode: _withdrawalMode,
          whatsappNumber: _whatsappController.text.trim(),
          maintenanceMessage: _maintenanceController.text.trim(),
          activeBankAccountId: _activeBankAccountId,
        ),
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _treasurySettings = updated;
        _seedTreasuryEditors(updated);
      });
      AppFeedback.showSuccess(context, 'Treasury settings updated.');
    } catch (error) {
      if (mounted) {
        AppFeedback.showError(context, error);
      }
    } finally {
      if (mounted) {
        setState(() {
          _savingTreasury = false;
        });
      }
    }
  }

  Future<void> _savePaymentRails() async {
    final String reason = _railsReasonController.text.trim();
    if (reason.length < 4) {
      AppFeedback.showError(
        context,
        'Enter a short reason before saving payment rail changes.',
      );
      return;
    }
    setState(() {
      _savingRails = true;
    });
    try {
      final AdminPaymentRailsState updated = await _api.updatePaymentRails(
        rails: _paymentRails,
        reason: reason,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _paymentRails = updated.rails;
      });
      _railsReasonController.clear();
      AppFeedback.showSuccess(context, 'Payment rails updated.');
    } catch (error) {
      if (mounted) {
        AppFeedback.showError(context, error);
      }
    } finally {
      if (mounted) {
        setState(() {
          _savingRails = false;
        });
      }
    }
  }

  Future<void> _saveWithdrawalControls() async {
    final AdminWithdrawalControls? controls = _withdrawalControls;
    final String reason = _withdrawalReasonController.text.trim();
    if (controls == null) {
      return;
    }
    if (reason.length < 4) {
      AppFeedback.showError(
        context,
        'Enter a short reason before saving payout controls.',
      );
      return;
    }
    setState(() {
      _savingWithdrawalControls = true;
    });
    try {
      final AdminWithdrawalControls updated = await _api
          .updateWithdrawalControls(controls: controls, reason: reason);
      if (!mounted) {
        return;
      }
      setState(() {
        _withdrawalControls = updated;
      });
      _withdrawalReasonController.clear();
      AppFeedback.showSuccess(context, 'Payout controls updated.');
    } catch (error) {
      if (mounted) {
        AppFeedback.showError(context, error);
      }
    } finally {
      if (mounted) {
        setState(() {
          _savingWithdrawalControls = false;
        });
      }
    }
  }

  Future<void> _createBankAccount() async {
    if (_bankNameController.text.trim().isEmpty ||
        _bankAccountNumberController.text.trim().isEmpty ||
        _bankAccountNameController.text.trim().isEmpty) {
      AppFeedback.showError(
        context,
        'Bank name, account number, and account name are required.',
      );
      return;
    }
    setState(() {
      _creatingBankAccount = true;
    });
    try {
      await _api.createTreasuryBankAccount(
        GteTreasuryBankAccountCreate(
          bankName: _bankNameController.text.trim(),
          accountNumber: _bankAccountNumberController.text.trim(),
          accountName: _bankAccountNameController.text.trim(),
          bankCode:
              _bankCodeController.text.trim().isEmpty
                  ? null
                  : _bankCodeController.text.trim(),
        ),
      );
      _bankNameController.clear();
      _bankAccountNumberController.clear();
      _bankAccountNameController.clear();
      _bankCodeController.clear();
      await _load();
      if (mounted) {
        AppFeedback.showSuccess(context, 'Bank account added.');
      }
    } catch (error) {
      if (mounted) {
        AppFeedback.showError(context, error);
      }
    } finally {
      if (mounted) {
        setState(() {
          _creatingBankAccount = false;
        });
      }
    }
  }

  Future<void> _setActiveBankAccount(String accountId) async {
    setState(() {
      _bankBusyIds.add(accountId);
    });
    try {
      final GteTreasurySettings updated = await _api.updateTreasurySettings(
        GteTreasurySettingsUpdate(activeBankAccountId: accountId),
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _treasurySettings = updated;
        _seedTreasuryEditors(updated);
      });
      AppFeedback.showSuccess(context, 'Active bank account updated.');
    } catch (error) {
      if (mounted) {
        AppFeedback.showError(context, error);
      }
    } finally {
      if (mounted) {
        setState(() {
          _bankBusyIds.remove(accountId);
        });
      }
    }
  }

  Future<void> _toggleBankAccount(
    GteTreasuryBankAccount account,
    bool isActive,
  ) async {
    setState(() {
      _bankBusyIds.add(account.id);
    });
    try {
      await _api.updateTreasuryBankAccount(
        account.id,
        GteTreasuryBankAccountUpdate(isActive: isActive),
      );
      await _load();
      if (mounted) {
        AppFeedback.showSuccess(context, 'Bank account status updated.');
      }
    } catch (error) {
      if (mounted) {
        AppFeedback.showError(context, error);
      }
    } finally {
      if (mounted) {
        setState(() {
          _bankBusyIds.remove(account.id);
        });
      }
    }
  }

  Future<String?> _promptForNotes({
    required String title,
    required String confirmLabel,
    required String helperText,
  }) {
    final TextEditingController controller = TextEditingController();
    return showDialog<String?>(
      context: context,
      builder: (BuildContext dialogContext) {
        return AlertDialog(
          title: Text(title),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(helperText),
              const SizedBox(height: 12),
              TextField(
                controller: controller,
                maxLines: 4,
                decoration: const InputDecoration(
                  labelText: 'Admin notes',
                  hintText: 'Optional context for audit history',
                ),
              ),
            ],
          ),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(null),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed:
                  () => Navigator.of(dialogContext).pop(controller.text.trim()),
              child: Text(confirmLabel),
            ),
          ],
        );
      },
    );
  }

  Future<void> _runDepositAction(
    GteAdminDeposit deposit,
    _DepositAdminAction action,
  ) async {
    final String? notes = await _promptForNotes(
      title: action.dialogTitle,
      confirmLabel: action.buttonLabel,
      helperText:
          'Admin notes are optional but useful for audit history and support follow-up.',
    );
    if (!mounted || notes == null) {
      return;
    }
    setState(() {
      _depositBusyIds.add(deposit.id);
    });
    try {
      switch (action) {
        case _DepositAdminAction.review:
          await _api.adminReviewDeposit(deposit.id, adminNotes: notes);
          break;
        case _DepositAdminAction.confirm:
          await _api.adminConfirmDeposit(deposit.id, adminNotes: notes);
          break;
        case _DepositAdminAction.reject:
          await _api.adminRejectDeposit(deposit.id, adminNotes: notes);
          break;
      }
      await _load();
      if (mounted) {
        AppFeedback.showSuccess(context, action.successMessage);
      }
    } catch (error) {
      if (mounted) {
        AppFeedback.showError(context, error);
      }
    } finally {
      if (mounted) {
        setState(() {
          _depositBusyIds.remove(deposit.id);
        });
      }
    }
  }

  Future<void> _previewCredit() async {
    final double? amount = _parseDouble(_creditAmountController.text);
    if (_creditUserIdController.text.trim().isEmpty ||
        amount == null ||
        amount <= 0) {
      AppFeedback.showError(
        context,
        'Enter a target user ID and a valid GTEX Coin amount.',
      );
      return;
    }
    setState(() {
      _previewingCredit = true;
    });
    try {
      final AdminMarketTopupQuote quote = await _api.quoteMarketTopup(
        amount: amount,
        unit: 'credit',
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _creditQuote = quote;
      });
    } catch (error) {
      if (mounted) {
        AppFeedback.showError(context, error);
      }
    } finally {
      if (mounted) {
        setState(() {
          _previewingCredit = false;
        });
      }
    }
  }

  Future<void> _createAndSettleCredit() async {
    final String userId = _creditUserIdController.text.trim();
    final double? amount = _parseDouble(_creditAmountController.text);
    if (userId.isEmpty || amount == null || amount <= 0) {
      AppFeedback.showError(
        context,
        'Enter a target user ID and a valid GTEX Coin amount.',
      );
      return;
    }
    setState(() {
      _runningCredit = true;
    });
    try {
      final AdminMarketTopup created = await _api.createMarketTopup(
        userId: userId,
        amount: amount,
        unit: 'credit',
        sourceScope: 'promotion',
        notes: _creditNotesController.text.trim(),
      );
      final AdminMarketTopup settled = await _api.updateMarketTopupStatus(
        created.id,
        status: 'settled',
        notes: _creditNotesController.text.trim(),
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _lastCreditResult = settled;
      });
      _creditUserIdController.clear();
      _creditAmountController.clear();
      _creditNotesController.clear();
      AppFeedback.showSuccess(context, 'Wallet credit applied.');
      await _load();
    } catch (error) {
      if (mounted) {
        AppFeedback.showError(context, error);
      }
    } finally {
      if (mounted) {
        setState(() {
          _runningCredit = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final bool hasData =
        _treasurySettings != null ||
        _depositQueue != null ||
        _paymentRails.isNotEmpty ||
        _withdrawalControls != null;
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(
          title: const Text('Admin dashboard'),
          actions: <Widget>[
            IconButton(
              tooltip: 'Refresh',
              onPressed: _loading ? null : _load,
              icon: const Icon(Icons.refresh),
            ),
          ],
        ),
        body:
            _loading && !hasData
                ? const Center(child: CircularProgressIndicator())
                : _error != null && !hasData
                ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: GteStatePanel(
                      title: 'Admin dashboard unavailable',
                      message: _error!,
                      actionLabel: 'Retry',
                      onAction: _load,
                      icon: Icons.admin_panel_settings_outlined,
                    ),
                  ),
                )
                : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
                    children: <Widget>[
                      _buildOverviewPanel(context),
                      const SizedBox(height: 18),
                      _buildOperationsRoutesPanel(context),
                      const SizedBox(height: 18),
                      _buildTreasurySettingsPanel(context),
                      const SizedBox(height: 18),
                      _buildPaymentRailsPanel(context),
                      const SizedBox(height: 18),
                      _buildBankAccountsPanel(context),
                      const SizedBox(height: 18),
                      _buildDepositQueuePanel(context),
                      const SizedBox(height: 18),
                      _buildWalletCreditPanel(context),
                    ],
                  ),
                ),
      ),
    );
  }

  Widget _buildOverviewPanel(BuildContext context) {
    final GteTreasurySettings? settings = _treasurySettings;
    final int pendingDeposits =
        _depositQueue?.items
            .where(
              (GteAdminDeposit item) =>
                  item.status != GteDepositStatus.confirmed &&
                  item.status != GteDepositStatus.rejected &&
                  item.status != GteDepositStatus.expired,
            )
            .length ??
        0;
    final int liveRails =
        _paymentRails
            .where(
              (AdminPaymentRail rail) =>
                  rail.isLive &&
                  (rail.depositsEnabled || rail.withdrawalsEnabled),
            )
            .length;
    return GteSurfacePanel(
      emphasized: true,
      accentColor: GteShellTheme.accentAdmin,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Platform operations',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 8),
          Text(
            'Use this dashboard to control payment availability, competition operations, bank-transfer details, manual deposit review, and direct GTEX or Fan Coin wallet funding.',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              _AdminStatTile(
                label: 'Deposit mode',
                value:
                    settings == null
                        ? '--'
                        : _paymentModeLabel(settings.depositMode),
              ),
              _AdminStatTile(
                label: 'Pending deposits',
                value: pendingDeposits.toString(),
              ),
              _AdminStatTile(label: 'Live rails', value: liveRails.toString()),
              _AdminStatTile(
                label: 'Active bank account',
                value: settings?.activeBankAccount?.bankName ?? 'Not set',
              ),
            ],
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              FilledButton.tonalIcon(
                onPressed: _loading ? null : _load,
                icon: const Icon(Icons.refresh),
                label: const Text('Refresh data'),
              ),
              FilledButton.tonalIcon(
                onPressed:
                    () => _openRoute(context, const GiftStabilizerRouteData()),
                icon: const Icon(Icons.card_giftcard_outlined),
                label: const Text('Open gift stabilizer'),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            'Automatic wallet checkout in the app supports Paystack and KoraPay when those rails are live. Manual bank transfer availability follows the treasury modes and active bank account below, and the operations launcher keeps deeper admin routes one tap away.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }

  Widget _buildOperationsRoutesPanel(BuildContext context) {
    return GteSurfacePanel(
      accentColor: GteShellTheme.accentAdmin,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const _SectionHeader(
            title: 'Operations launchers',
            subtitle:
                'Open the live admin and platform routes that were previously buried behind direct links.',
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              _buildRouteLauncher(
                context: context,
                label: 'Create competition',
                icon: Icons.add_circle_outline,
                route: const CompetitionCreateRouteData(),
                emphasized: true,
              ),
              _buildRouteLauncher(
                context: context,
                label: 'Competition lobby',
                icon: Icons.stadium_outlined,
                route: const CompetitionsDiscoveryRouteData(),
              ),
              _buildRouteLauncher(
                context: context,
                label: 'Broadcast desk',
                icon: Icons.podcasts_outlined,
                route: const BroadcastDeskRouteData(),
              ),
              _buildRouteLauncher(
                context: context,
                label: 'GTEX jackpot',
                icon: Icons.celebration_outlined,
                route: const GtexJackpotRouteData(),
              ),
              _buildRouteLauncher(
                context: context,
                label: 'Creator share market',
                icon: Icons.insights_outlined,
                route: const CreatorShareMarketAdminControlRouteData(),
                emphasized: true,
              ),
              _buildRouteLauncher(
                context: context,
                label: 'Creator stadium',
                icon: Icons.theaters_outlined,
                route: const CreatorStadiumAdminControlRouteData(),
              ),
              _buildRouteLauncher(
                context: context,
                label: 'League finance',
                icon: Icons.receipt_long_outlined,
                route: const CreatorLeagueFinancialReportRouteData(),
              ),
              _buildRouteLauncher(
                context: context,
                label: 'League settlements',
                icon: Icons.account_balance_outlined,
                route: const CreatorLeagueSettlementsRouteData(),
              ),
              _buildRouteLauncher(
                context: context,
                label: 'Gift stabilizer',
                icon: Icons.card_giftcard_outlined,
                route: const GiftStabilizerRouteData(),
              ),
              _buildRouteLauncher(
                context: context,
                label: 'Transfer center',
                icon: Icons.swap_horiz_outlined,
                route: const FootballTransferCenterRouteData(),
              ),
              _buildRouteLauncher(
                context: context,
                label: 'National teams',
                icon: Icons.flag_outlined,
                route: const NationalTeamCompetitionsRouteData(),
              ),
              _buildRouteLauncher(
                context: context,
                label: 'Streamer tournaments',
                icon: Icons.live_tv_outlined,
                route: const StreamerTournamentsListRouteData(),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildTreasurySettingsPanel(BuildContext context) {
    final GteTreasurySettings? settings = _treasurySettings;
    return GteSurfacePanel(
      accentColor: GteShellTheme.accentCapital,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const _SectionHeader(
            title: 'Treasury settings',
            subtitle:
                'Control whether funding and payouts are manual, automatic, or hybrid, and keep limits clear.',
          ),
          if (settings == null)
            const SizedBox.shrink()
          else ...<Widget>[
            const SizedBox(height: 16),
            LayoutBuilder(
              builder: (BuildContext context, BoxConstraints constraints) {
                final bool singleColumn = constraints.maxWidth < 760;
                final List<Widget> fields = <Widget>[
                  DropdownButtonFormField<GtePaymentMode>(
                    value: _depositMode,
                    decoration: const InputDecoration(
                      labelText: 'Deposit mode',
                    ),
                    items: GtePaymentMode.values
                        .map(
                          (GtePaymentMode mode) =>
                              DropdownMenuItem<GtePaymentMode>(
                                value: mode,
                                child: Text(_paymentModeLabel(mode)),
                              ),
                        )
                        .toList(growable: false),
                    onChanged: (GtePaymentMode? value) {
                      if (value != null) {
                        setState(() {
                          _depositMode = value;
                        });
                      }
                    },
                  ),
                  DropdownButtonFormField<GtePaymentMode>(
                    value: _withdrawalMode,
                    decoration: const InputDecoration(
                      labelText: 'Withdrawal mode',
                    ),
                    items: GtePaymentMode.values
                        .map(
                          (GtePaymentMode mode) =>
                              DropdownMenuItem<GtePaymentMode>(
                                value: mode,
                                child: Text(_paymentModeLabel(mode)),
                              ),
                        )
                        .toList(growable: false),
                    onChanged: (GtePaymentMode? value) {
                      if (value != null) {
                        setState(() {
                          _withdrawalMode = value;
                        });
                      }
                    },
                  ),
                  TextField(
                    controller: _depositRateController,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    decoration: const InputDecoration(
                      labelText: 'Deposit rate',
                    ),
                  ),
                  TextField(
                    controller: _withdrawalRateController,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    decoration: const InputDecoration(
                      labelText: 'Withdrawal rate',
                    ),
                  ),
                  TextField(
                    controller: _minDepositController,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    decoration: const InputDecoration(
                      labelText: 'Minimum deposit',
                    ),
                  ),
                  TextField(
                    controller: _maxDepositController,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    decoration: const InputDecoration(
                      labelText: 'Maximum deposit',
                    ),
                  ),
                  TextField(
                    controller: _minWithdrawalController,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    decoration: const InputDecoration(
                      labelText: 'Minimum withdrawal',
                    ),
                  ),
                  TextField(
                    controller: _maxWithdrawalController,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    decoration: const InputDecoration(
                      labelText: 'Maximum withdrawal',
                    ),
                  ),
                ];
                if (singleColumn) {
                  return Column(
                    children: fields
                        .map(
                          (Widget field) => Padding(
                            padding: const EdgeInsets.only(bottom: 12),
                            child: field,
                          ),
                        )
                        .toList(growable: false),
                  );
                }
                return Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: fields
                      .map(
                        (Widget field) => SizedBox(
                          width: (constraints.maxWidth - 12) / 2,
                          child: field,
                        ),
                      )
                      .toList(growable: false),
                );
              },
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _whatsappController,
              decoration: const InputDecoration(
                labelText: 'Support WhatsApp number',
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _maintenanceController,
              maxLines: 3,
              decoration: const InputDecoration(
                labelText: 'Maintenance message',
                hintText:
                    'Shown to users when deposits or withdrawals are paused',
              ),
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: _savingTreasury ? null : _saveTreasurySettings,
              icon: const Icon(Icons.save_outlined),
              label: Text(
                _savingTreasury ? 'Saving...' : 'Save treasury settings',
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildPaymentRailsPanel(BuildContext context) {
    final AdminWithdrawalControls? controls = _withdrawalControls;
    return GteSurfacePanel(
      accentColor: GteShellTheme.accentWarm,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const _SectionHeader(
            title: 'Payment methods',
            subtitle:
                'Toggle gateway providers and manual bank transfer routing without leaving the admin dashboard.',
          ),
          const SizedBox(height: 16),
          ..._paymentRails.asMap().entries.map((
            MapEntry<int, AdminPaymentRail> entry,
          ) {
            final int index = entry.key;
            final AdminPaymentRail rail = entry.value;
            return Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: GteSurfacePanel(
                accentColor: GteShellTheme.accentWarm,
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Row(
                      children: <Widget>[
                        Expanded(
                          child: Text(
                            _providerLabel(rail.provider),
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                        ),
                        Chip(label: Text(rail.isLive ? 'Live' : 'Paused')),
                      ],
                    ),
                    if (rail.maintenanceMessage != null &&
                        rail.maintenanceMessage!.trim().isNotEmpty) ...<Widget>[
                      const SizedBox(height: 8),
                      Text(rail.maintenanceMessage!),
                    ],
                    const SizedBox(height: 8),
                    SwitchListTile.adaptive(
                      value: rail.isLive,
                      contentPadding: EdgeInsets.zero,
                      title: const Text('Provider live'),
                      onChanged: (bool value) {
                        setState(() {
                          _paymentRails[index] = rail.copyWith(isLive: value);
                        });
                      },
                    ),
                    SwitchListTile.adaptive(
                      value: rail.depositsEnabled,
                      contentPadding: EdgeInsets.zero,
                      title: const Text('Deposits enabled'),
                      onChanged: (bool value) {
                        setState(() {
                          _paymentRails[index] = rail.copyWith(
                            depositsEnabled: value,
                          );
                        });
                      },
                    ),
                    SwitchListTile.adaptive(
                      value: rail.withdrawalsEnabled,
                      contentPadding: EdgeInsets.zero,
                      title: const Text('Withdrawals enabled'),
                      onChanged: (bool value) {
                        setState(() {
                          _paymentRails[index] = rail.copyWith(
                            withdrawalsEnabled: value,
                          );
                        });
                      },
                    ),
                  ],
                ),
              ),
            );
          }),
          TextField(
            controller: _railsReasonController,
            decoration: const InputDecoration(
              labelText: 'Reason for payment rail change',
            ),
          ),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: _savingRails ? null : _savePaymentRails,
            icon: const Icon(Icons.tune_outlined),
            label: Text(_savingRails ? 'Saving...' : 'Save payment rails'),
          ),
          if (controls != null) ...<Widget>[
            const SizedBox(height: 22),
            const Divider(),
            const SizedBox(height: 12),
            Text(
              'Manual transfer routing',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            DropdownButtonFormField<String>(
              value: controls.processorMode,
              decoration: const InputDecoration(
                labelText: 'Primary payout processor',
              ),
              items: const <DropdownMenuItem<String>>[
                DropdownMenuItem<String>(
                  value: 'automatic_gateway',
                  child: Text('Automatic gateway'),
                ),
                DropdownMenuItem<String>(
                  value: 'manual_bank_transfer',
                  child: Text('Manual bank transfer'),
                ),
              ],
              onChanged: (String? value) {
                if (value != null) {
                  setState(() {
                    _withdrawalControls = controls.copyWith(
                      processorMode: value,
                    );
                  });
                }
              },
            ),
            SwitchListTile.adaptive(
              value: controls.depositsViaBankTransfer,
              contentPadding: EdgeInsets.zero,
              title: const Text('Manual bank transfer for deposits'),
              onChanged: (bool value) {
                setState(() {
                  _withdrawalControls = controls.copyWith(
                    depositsViaBankTransfer: value,
                  );
                });
              },
            ),
            SwitchListTile.adaptive(
              value: controls.payoutsViaBankTransfer,
              contentPadding: EdgeInsets.zero,
              title: const Text('Manual bank transfer for payouts'),
              onChanged: (bool value) {
                setState(() {
                  _withdrawalControls = controls.copyWith(
                    payoutsViaBankTransfer: value,
                  );
                });
              },
            ),
            SwitchListTile.adaptive(
              value: controls.tradeWithdrawalsEnabled,
              contentPadding: EdgeInsets.zero,
              title: const Text('Trade withdrawals enabled'),
              onChanged: (bool value) {
                setState(() {
                  _withdrawalControls = controls.copyWith(
                    tradeWithdrawalsEnabled: value,
                  );
                });
              },
            ),
            SwitchListTile.adaptive(
              value: controls.egameWithdrawalsEnabled,
              contentPadding: EdgeInsets.zero,
              title: const Text('Competition reward withdrawals enabled'),
              onChanged: (bool value) {
                setState(() {
                  _withdrawalControls = controls.copyWith(
                    egameWithdrawalsEnabled: value,
                  );
                });
              },
            ),
            TextField(
              controller: _withdrawalReasonController,
              decoration: const InputDecoration(
                labelText: 'Reason for payout control change',
              ),
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed:
                  _savingWithdrawalControls ? null : _saveWithdrawalControls,
              icon: const Icon(Icons.account_balance_outlined),
              label: Text(
                _savingWithdrawalControls
                    ? 'Saving...'
                    : 'Save payout controls',
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildBankAccountsPanel(BuildContext context) {
    return GteSurfacePanel(
      accentColor: GteShellTheme.accentClub,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const _SectionHeader(
            title: 'Manual payment details',
            subtitle:
                'Manage the bank account details users see when manual bank transfer is enabled.',
          ),
          const SizedBox(height: 16),
          if (_bankAccounts.isEmpty)
            const Text('No treasury bank accounts have been configured yet.')
          else
            ..._bankAccounts.map((GteTreasuryBankAccount account) {
              final bool busy = _bankBusyIds.contains(account.id);
              final bool isSelectedActive = _activeBankAccountId == account.id;
              return Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: GteSurfacePanel(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Row(
                        children: <Widget>[
                          Expanded(
                            child: Text(
                              account.bankName,
                              style: Theme.of(context).textTheme.titleMedium,
                            ),
                          ),
                          if (isSelectedActive)
                            const Chip(label: Text('Primary')),
                          const SizedBox(width: 8),
                          Chip(
                            label: Text(
                              account.isActive ? 'Enabled' : 'Disabled',
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text('${account.accountName} - ${account.accountNumber}'),
                      Text(account.currencyCode),
                      const SizedBox(height: 12),
                      Wrap(
                        spacing: 12,
                        runSpacing: 12,
                        children: <Widget>[
                          FilledButton.tonal(
                            onPressed:
                                busy || isSelectedActive
                                    ? null
                                    : () => _setActiveBankAccount(account.id),
                            child: Text(
                              busy
                                  ? 'Updating...'
                                  : isSelectedActive
                                  ? 'Primary account'
                                  : 'Make primary',
                            ),
                          ),
                          Switch(
                            value: account.isActive,
                            onChanged:
                                busy
                                    ? null
                                    : (bool value) =>
                                        _toggleBankAccount(account, value),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              );
            }),
          const SizedBox(height: 16),
          Text(
            'Add bank account',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 12),
          LayoutBuilder(
            builder: (BuildContext context, BoxConstraints constraints) {
              final bool singleColumn = constraints.maxWidth < 760;
              final List<Widget> fields = <Widget>[
                TextField(
                  controller: _bankNameController,
                  decoration: const InputDecoration(labelText: 'Bank name'),
                ),
                TextField(
                  controller: _bankAccountNumberController,
                  decoration: const InputDecoration(
                    labelText: 'Account number',
                  ),
                ),
                TextField(
                  controller: _bankAccountNameController,
                  decoration: const InputDecoration(labelText: 'Account name'),
                ),
                TextField(
                  controller: _bankCodeController,
                  decoration: const InputDecoration(labelText: 'Bank code'),
                ),
              ];
              if (singleColumn) {
                return Column(
                  children: fields
                      .map(
                        (Widget field) => Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: field,
                        ),
                      )
                      .toList(growable: false),
                );
              }
              return Wrap(
                spacing: 12,
                runSpacing: 12,
                children: fields
                    .map(
                      (Widget field) => SizedBox(
                        width: (constraints.maxWidth - 12) / 2,
                        child: field,
                      ),
                    )
                    .toList(growable: false),
              );
            },
          ),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: _creatingBankAccount ? null : _createBankAccount,
            icon: const Icon(Icons.add_business_outlined),
            label: Text(
              _creatingBankAccount ? 'Adding...' : 'Add bank account',
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDepositQueuePanel(BuildContext context) {
    final List<GteAdminDeposit> items =
        _depositQueue?.items ?? const <GteAdminDeposit>[];
    return GteSurfacePanel(
      accentColor: GteShellTheme.accentArena,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const _SectionHeader(
            title: 'Manual deposit review',
            subtitle:
                'Review bank-transfer deposits, confirm successful payments, or reject invalid submissions.',
          ),
          const SizedBox(height: 16),
          if (items.isEmpty)
            const Text('No deposit requests need attention right now.')
          else
            ...items.map((GteAdminDeposit deposit) {
              final bool busy = _depositBusyIds.contains(deposit.id);
              final bool actionable =
                  deposit.status != GteDepositStatus.confirmed &&
                  deposit.status != GteDepositStatus.rejected &&
                  deposit.status != GteDepositStatus.expired;
              return Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: GteSurfacePanel(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Row(
                        children: <Widget>[
                          Expanded(
                            child: Text(
                              deposit.userFullName?.trim().isNotEmpty == true
                                  ? deposit.userFullName!
                                  : deposit.userEmail,
                              style: Theme.of(context).textTheme.titleMedium,
                            ),
                          ),
                          Chip(
                            label: Text(_depositStatusLabel(deposit.status)),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text('User ID: ${deposit.userId}'),
                      Text('Reference: ${deposit.reference}'),
                      Text(
                        'Amount: ${gteFormatFiat(deposit.amountFiat, currency: deposit.currencyCode)} → ${gteFormatCompetitionAmount(deposit.amountCoin, 'credit')}',
                      ),
                      if (deposit.transferReference?.trim().isNotEmpty == true)
                        Text(
                          'Transfer reference: ${deposit.transferReference}',
                        ),
                      if (deposit.senderBank?.trim().isNotEmpty == true)
                        Text('Sender bank: ${deposit.senderBank}'),
                      if (deposit.adminNotes?.trim().isNotEmpty == true)
                        Padding(
                          padding: const EdgeInsets.only(top: 6),
                          child: Text('Admin notes: ${deposit.adminNotes}'),
                        ),
                      const SizedBox(height: 10),
                      Text(
                        'Submitted: ${gteFormatDateTime(deposit.submittedAt ?? deposit.createdAt)}',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      if (actionable) ...<Widget>[
                        const SizedBox(height: 14),
                        Wrap(
                          spacing: 10,
                          runSpacing: 10,
                          children: <Widget>[
                            FilledButton.tonal(
                              onPressed:
                                  busy
                                      ? null
                                      : () => _runDepositAction(
                                        deposit,
                                        _DepositAdminAction.review,
                                      ),
                              child: Text(
                                busy ? 'Working...' : 'Mark reviewing',
                              ),
                            ),
                            FilledButton(
                              onPressed:
                                  busy
                                      ? null
                                      : () => _runDepositAction(
                                        deposit,
                                        _DepositAdminAction.confirm,
                                      ),
                              child: const Text('Confirm payment'),
                            ),
                            OutlinedButton(
                              onPressed:
                                  busy
                                      ? null
                                      : () => _runDepositAction(
                                        deposit,
                                        _DepositAdminAction.reject,
                                      ),
                              child: const Text('Reject'),
                            ),
                          ],
                        ),
                      ],
                    ],
                  ),
                ),
              );
            }),
        ],
      ),
    );
  }

  Widget _buildWalletCreditPanel(BuildContext context) {
    return GteSurfacePanel(
      accentColor: GteShellTheme.positive,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const _SectionHeader(
            title: 'Admin wallet credit',
            subtitle:
                'Credit GTEX Coin directly to a user wallet by creating and settling an internal top-up.',
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _creditUserIdController,
            decoration: const InputDecoration(
              labelText: 'Target user ID',
              hintText: 'Paste the user ID to credit',
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _creditAmountController,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: const InputDecoration(labelText: 'GTEX Coin amount'),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _creditNotesController,
            maxLines: 3,
            decoration: const InputDecoration(
              labelText: 'Notes',
              hintText: 'Optional internal reason for the credit',
            ),
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              FilledButton.tonalIcon(
                onPressed: _previewingCredit ? null : _previewCredit,
                icon: const Icon(Icons.receipt_long_outlined),
                label: Text(
                  _previewingCredit ? 'Previewing...' : 'Preview credit',
                ),
              ),
              FilledButton.icon(
                onPressed: _runningCredit ? null : _createAndSettleCredit,
                icon: const Icon(Icons.send_outlined),
                label: Text(
                  _runningCredit ? 'Applying...' : 'Create and settle',
                ),
              ),
            ],
          ),
          if (_creditQuote != null) ...<Widget>[
            const SizedBox(height: 16),
            GteSurfacePanel(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'Credit preview',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Gross: ${gteFormatCompetitionAmount(_creditQuote!.grossAmount, _creditQuote!.unit)}',
                  ),
                  Text(
                    'Fee: ${gteFormatCompetitionAmount(_creditQuote!.feeAmount, _creditQuote!.unit)}',
                  ),
                  Text(
                    'Net: ${gteFormatCompetitionAmount(_creditQuote!.netAmount, _creditQuote!.unit)}',
                  ),
                ],
              ),
            ),
          ],
          if (_lastCreditResult != null) ...<Widget>[
            const SizedBox(height: 16),
            GteSurfacePanel(
              accentColor: GteShellTheme.positive,
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'Last credit result',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 8),
                  Text('Reference: ${_lastCreditResult!.reference}'),
                  Text('Status: ${_humanize(_lastCreditResult!.status)}'),
                  Text('User ID: ${_lastCreditResult!.userId}'),
                  Text(
                    'Net credited: ${gteFormatCompetitionAmount(_lastCreditResult!.netAmount, _lastCreditResult!.unit)}',
                  ),
                  Text(
                    'Updated: ${gteFormatDateTime(_lastCreditResult!.updatedAt)}',
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({required this.title, required this.subtitle});

  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        Text(title, style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 6),
        Text(subtitle, style: Theme.of(context).textTheme.bodyMedium),
      ],
    );
  }
}

class _AdminStatTile extends StatelessWidget {
  const _AdminStatTile({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: const Color(0xFF2A3A56)),
        color: Colors.white.withValues(alpha: 0.03),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(label, style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 4),
          Text(value, style: Theme.of(context).textTheme.titleMedium),
        ],
      ),
    );
  }
}

enum _DepositAdminAction {
  review(
    buttonLabel: 'Mark reviewing',
    dialogTitle: 'Mark deposit as under review',
    successMessage: 'Deposit marked as under review.',
  ),
  confirm(
    buttonLabel: 'Confirm payment',
    dialogTitle: 'Confirm deposit payment',
    successMessage: 'Deposit confirmed.',
  ),
  reject(
    buttonLabel: 'Reject deposit',
    dialogTitle: 'Reject deposit',
    successMessage: 'Deposit rejected.',
  );

  const _DepositAdminAction({
    required this.buttonLabel,
    required this.dialogTitle,
    required this.successMessage,
  });

  final String buttonLabel;
  final String dialogTitle;
  final String successMessage;
}
