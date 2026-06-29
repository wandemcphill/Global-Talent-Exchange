import 'dart:async';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/app_feedback.dart';
import '../../data/admin_command_center_api.dart';
import '../../data/gte_api_repository.dart';
import '../../data/gte_authed_api.dart';
import '../../data/gte_models.dart';
import '../../features/app_routes/gte_navigation_helpers.dart';
import '../../features/app_routes/gte_route_data.dart';
import '../../features/navigation_guards/gte_navigation_guards.dart';
import '../../shared/widgets/gtex_premium_panels.dart';
import '../../ui_gtex/layout/gtex_production_flow_scaffold.dart';
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
    this.api,
    this.authedApi,
  });

  final String baseUrl;
  final String accessToken;
  final GteBackendMode backendMode;
  final AdminCommandCenterApi? api;
  final GteAuthedApi? authedApi;

  @override
  State<AdminCommandCenterScreen> createState() =>
      _AdminCommandCenterScreenState();
}

class _AdminCommandCenterScreenState extends State<AdminCommandCenterScreen> {
  late final AdminCommandCenterApi _api;
  Timer? _liveRefreshTimer;

  bool get _isTestBinding =>
      WidgetsBinding.instance.runtimeType.toString().contains('Test');

  final TextEditingController _depositRateController = TextEditingController();
  final TextEditingController _withdrawalRateController =
      TextEditingController();
  final TextEditingController _minTraderBuyRateController =
      TextEditingController();
  final TextEditingController _maxTraderBuyRateController =
      TextEditingController();
  final TextEditingController _minTraderSellRateController =
      TextEditingController();
  final TextEditingController _maxTraderSellRateController =
      TextEditingController();
  final TextEditingController _maxTraderSpreadController =
      TextEditingController();
  final TextEditingController _maxBuyAboveWithdrawalController =
      TextEditingController();
  final TextEditingController _maxSellBelowDepositController =
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
  final TextEditingController _competitionTemplateController =
      TextEditingController(text: 'user-hosted-cup-8');
  final TextEditingController _competitionTitleController =
      TextEditingController();
  final TextEditingController _competitionPasscodeController =
      TextEditingController();

  bool _loading = true;
  bool _savingTreasury = false;
  bool _savingRails = false;
  bool _savingWithdrawalControls = false;
  bool _creatingBankAccount = false;
  bool _previewingCredit = false;
  bool _runningCredit = false;
  bool _creatingGtexCompetition = false;
  bool _notifyingReadinessBlockers = false;
  String? _error;
  String? _readinessDispatchMessage;

  GteTreasurySettings? _treasurySettings;
  List<GteTreasuryBankAccount> _bankAccounts = <GteTreasuryBankAccount>[];
  GteAdminQueuePage<GteAdminDeposit>? _depositQueue;
  List<AdminPaymentRail> _paymentRails = <AdminPaymentRail>[];
  AdminWithdrawalControls? _withdrawalControls;
  AdminOperationsReadinessSnapshot? _operationsReadiness;
  AdminMarketTopupQuote? _creditQuote;
  AdminMarketTopup? _lastCreditResult;
  String? _lastCompetitionSummary;

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
    _api =
        widget.api ??
        AdminCommandCenterApi.standard(
          baseUrl: widget.baseUrl,
          accessToken: widget.accessToken,
          mode: widget.backendMode,
          client: widget.authedApi,
        );
    _load();
    if (!_isTestBinding) {
      _liveRefreshTimer = Timer.periodic(
        const Duration(seconds: 28),
        (_) => _load(),
      );
    }
  }

  @override
  void dispose() {
    _liveRefreshTimer?.cancel();
    _depositRateController.dispose();
    _withdrawalRateController.dispose();
    _minTraderBuyRateController.dispose();
    _maxTraderBuyRateController.dispose();
    _minTraderSellRateController.dispose();
    _maxTraderSellRateController.dispose();
    _maxTraderSpreadController.dispose();
    _maxBuyAboveWithdrawalController.dispose();
    _maxSellBelowDepositController.dispose();
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
    _competitionTemplateController.dispose();
    _competitionTitleController.dispose();
    _competitionPasscodeController.dispose();
    super.dispose();
  }

  Future<_AdminLoadCapture<T>> _captureLoad<T>(Future<T> future) async {
    try {
      return _AdminLoadCapture<T>(value: await future);
    } catch (error) {
      return _AdminLoadCapture<T>(error: AppFeedback.messageFor(error));
    }
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final Future<_AdminLoadCapture<GteTreasurySettings>> settingsFuture =
          _captureLoad<GteTreasurySettings>(_api.fetchTreasurySettings());
      final Future<_AdminLoadCapture<List<GteTreasuryBankAccount>>>
      bankAccountsFuture = _captureLoad<List<GteTreasuryBankAccount>>(
        _api.listTreasuryBankAccounts(),
      );
      final Future<_AdminLoadCapture<GteAdminQueuePage<GteAdminDeposit>>>
      depositsFuture = _captureLoad<GteAdminQueuePage<GteAdminDeposit>>(
        _api.fetchAdminDeposits(limit: 20),
      );
      final Future<_AdminLoadCapture<AdminPaymentRailsState>>
      paymentRailsFuture = _captureLoad<AdminPaymentRailsState>(
        _api.fetchPaymentRails(),
      );
      final Future<_AdminLoadCapture<AdminWithdrawalControls>>
      withdrawalControlsFuture = _captureLoad<AdminWithdrawalControls>(
        _api.fetchWithdrawalControls(),
      );
      final Future<_AdminLoadCapture<AdminOperationsReadinessSnapshot>>
      operationsReadinessFuture =
          _captureLoad<AdminOperationsReadinessSnapshot>(
            _api.fetchOperationsReadiness(),
          );

      final _AdminLoadCapture<GteTreasurySettings> settingsResult =
          await settingsFuture;
      final _AdminLoadCapture<List<GteTreasuryBankAccount>> bankAccountsResult =
          await bankAccountsFuture;
      final _AdminLoadCapture<GteAdminQueuePage<GteAdminDeposit>>
      depositsResult = await depositsFuture;
      final _AdminLoadCapture<AdminPaymentRailsState> paymentRailsResult =
          await paymentRailsFuture;
      final _AdminLoadCapture<AdminWithdrawalControls>
      withdrawalControlsResult = await withdrawalControlsFuture;
      final _AdminLoadCapture<AdminOperationsReadinessSnapshot>
      operationsReadinessResult = await operationsReadinessFuture;
      if (!mounted) {
        return;
      }

      final List<String> failures = <String>[
        if (settingsResult.error != null) settingsResult.error!,
        if (bankAccountsResult.error != null) bankAccountsResult.error!,
        if (depositsResult.error != null) depositsResult.error!,
        if (paymentRailsResult.error != null) paymentRailsResult.error!,
        if (withdrawalControlsResult.error != null)
          withdrawalControlsResult.error!,
        if (operationsReadinessResult.error != null)
          operationsReadinessResult.error!,
      ];

      setState(() {
        if (settingsResult.value != null) {
          _treasurySettings = settingsResult.value;
          _seedTreasuryEditors(settingsResult.value!);
        }
        if (bankAccountsResult.value != null) {
          _bankAccounts = bankAccountsResult.value!;
        }
        if (depositsResult.value != null) {
          _depositQueue = depositsResult.value!;
        }
        if (paymentRailsResult.value != null) {
          _paymentRails = paymentRailsResult.value!.rails;
        }
        if (withdrawalControlsResult.value != null) {
          _withdrawalControls = withdrawalControlsResult.value!;
        }
        if (operationsReadinessResult.value != null) {
          _operationsReadiness = operationsReadinessResult.value!;
        }
        _error = failures.isEmpty ? null : failures.first;
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
    _minTraderBuyRateController.text = settings.minTraderBuyRateFiat
        .toStringAsFixed(2);
    _maxTraderBuyRateController.text = settings.maxTraderBuyRateFiat
        .toStringAsFixed(2);
    _minTraderSellRateController.text = settings.minTraderSellRateFiat
        .toStringAsFixed(2);
    _maxTraderSellRateController.text = settings.maxTraderSellRateFiat
        .toStringAsFixed(2);
    _maxTraderSpreadController.text = settings.maxTraderSpreadFiat
        .toStringAsFixed(2);
    _maxBuyAboveWithdrawalController.text = settings.maxBuyAboveWithdrawalFiat
        .toStringAsFixed(2);
    _maxSellBelowDepositController.text = settings.maxSellBelowDepositFiat
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

  Future<void> _openRouteString(BuildContext context, String? rawRoute) async {
    final String route = _canonicalOperationsRoute(rawRoute);
    if (route.isEmpty) {
      return;
    }
    final GteAppRouteData? parsed = GteAppRouteParser.parse(route);
    if (parsed != null) {
      await _openRoute(context, parsed);
      return;
    }
    if (context.mounted) {
      context.go(route);
    }
  }

  String _canonicalOperationsRoute(String? rawRoute) {
    final String route = rawRoute?.trim() ?? '';
    switch (route.toLowerCase()) {
      case '':
        return '';
      case '/admin/ops':
      case '/admin/risk-ops':
      case '/admin/policies':
      case '/admin/moderation':
      case '/admin/disputes':
      case '/admin/ops/audit':
        return '/admin/trust-ops';
      case '/broadcast':
        return const BroadcastDeskRouteData().toUri().toString();
      default:
        return route;
    }
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

  Future<void> _createGtexHostedCompetition() async {
    final String title = _competitionTitleController.text.trim();
    final String templateKey = _competitionTemplateController.text.trim();
    if (title.isEmpty || templateKey.isEmpty) {
      AppFeedback.showError(
        context,
        'Add a competition title and template key before creating.',
      );
      return;
    }
    setState(() {
      _creatingGtexCompetition = true;
    });
    try {
      final String summary = await _api.createGtexHostedCompetition(
        templateKey: templateKey,
        title: title,
        passcode: _competitionPasscodeController.text,
      );
      if (!mounted) {
        return;
      }
      setState(() {
        _lastCompetitionSummary = summary;
      });
      AppFeedback.showSuccess(context, summary);
    } catch (error) {
      if (mounted) {
        AppFeedback.showError(context, error);
      }
    } finally {
      if (mounted) {
        setState(() {
          _creatingGtexCompetition = false;
        });
      }
    }
  }

  Future<void> _notifyOperationsReadinessBlockers() async {
    if (_notifyingReadinessBlockers) {
      return;
    }
    setState(() {
      _notifyingReadinessBlockers = true;
      _readinessDispatchMessage = null;
    });
    try {
      final AdminOperationsReadinessDispatch dispatch =
          await _api.notifyOperationsReadinessBlockers();
      if (!mounted) {
        return;
      }
      final int queueCount = dispatch.queueKeys.length;
      final String message =
          dispatch.sent
              ? '${dispatch.notificationsCreated} readiness notification(s) sent for $queueCount queue(s).'
              : 'No readiness blocker notifications were sent.';
      setState(() {
        _readinessDispatchMessage = message;
      });
      AppFeedback.showSuccess(context, message);
    } catch (error) {
      if (mounted) {
        AppFeedback.showError(context, error);
      }
    } finally {
      if (mounted) {
        setState(() {
          _notifyingReadinessBlockers = false;
        });
      }
    }
  }

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

  Widget _buildWarRoomHero(BuildContext context) {
    final int liveDepositCount = _depositQueue?.items.length ?? 0;
    final int liveRailCount =
        _paymentRails
            .where(
              (AdminPaymentRail rail) =>
                  rail.depositsEnabled || rail.withdrawalsEnabled,
            )
            .length;
    return GtexHeroPanel(
      eyebrow: 'ADMIN OPS',
      title: 'Run the GTEX football economy from one operating cockpit.',
      description:
          'Market supply, competition launches, treasury rails, and user-credit interventions stay visible here as one coordinated operations surface.',
      accentColor: GteShellTheme.accentAdmin,
      metrics: <Widget>[
        GtexStatTile(
          label: 'Trade queue',
          value: liveDepositCount == 0 ? 'WATCH' : '$liveDepositCount',
          support: 'Deposits and treasury reviews',
          tone: GtexSurfaceTone.live,
        ),
        GtexStatTile(
          label: 'Rails',
          value: liveRailCount == 0 ? 'OFFLINE' : '$liveRailCount',
          support: 'Active deposit or payout rails',
          tone: GtexSurfaceTone.warning,
        ),
        GtexStatTile(
          label: 'Withdrawals',
          value:
              _withdrawalControls == null
                  ? 'CHECKING'
                  : (_withdrawalControls!.tradeWithdrawalsEnabled
                      ? 'OPEN'
                      : 'PAUSED'),
          support: 'Trade payout posture',
          tone:
              _withdrawalControls?.tradeWithdrawalsEnabled == false
                  ? GtexSurfaceTone.danger
                  : GtexSurfaceTone.success,
        ),
      ],
      actions: <Widget>[
        FilledButton.icon(
          onPressed:
              _creatingGtexCompetition ? null : _createGtexHostedCompetition,
          icon: const Icon(Icons.emoji_events_outlined),
          label: const Text('Launch GTEX arena'),
        ),
        OutlinedButton.icon(
          onPressed: _previewingCredit ? null : _previewCredit,
          icon: const Icon(Icons.toll_outlined),
          label: Text(
            _previewingCredit ? 'Previewing credit' : 'Preview wallet credit',
          ),
        ),
      ],
    );
  }

  String _providerLabel(String provider) {
    final Map<String, String> labels = <String, String>{
      'bank_transfer_manual': 'Manual bank transfer',
      'paystack': 'Paystack (blocked)',
      'korapay': 'KoraPay',
      'flutterwave': 'Flutterwave',
      'monnify': 'Monnify',
    };
    return labels[provider.trim().toLowerCase()] ?? _humanize(provider);
  }

  bool _paymentRailLocked(AdminPaymentRail rail) {
    return rail.provider.trim().toLowerCase() == 'paystack';
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
    final double? minTraderBuyRate = _parseDouble(
      _minTraderBuyRateController.text,
    );
    final double? maxTraderBuyRate = _parseDouble(
      _maxTraderBuyRateController.text,
    );
    final double? minTraderSellRate = _parseDouble(
      _minTraderSellRateController.text,
    );
    final double? maxTraderSellRate = _parseDouble(
      _maxTraderSellRateController.text,
    );
    final double? maxTraderSpread = _parseDouble(
      _maxTraderSpreadController.text,
    );
    final double? maxBuyAboveWithdrawal = _parseDouble(
      _maxBuyAboveWithdrawalController.text,
    );
    final double? maxSellBelowDeposit = _parseDouble(
      _maxSellBelowDepositController.text,
    );
    final double? minDeposit = _parseDouble(_minDepositController.text);
    final double? maxDeposit = _parseDouble(_maxDepositController.text);
    final double? minWithdrawal = _parseDouble(_minWithdrawalController.text);
    final double? maxWithdrawal = _parseDouble(_maxWithdrawalController.text);
    if (<double?>[
      depositRate,
      withdrawalRate,
      minTraderBuyRate,
      maxTraderBuyRate,
      minTraderSellRate,
      maxTraderSellRate,
      maxTraderSpread,
      maxBuyAboveWithdrawal,
      maxSellBelowDeposit,
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
          minTraderBuyRateFiat: minTraderBuyRate,
          maxTraderBuyRateFiat: maxTraderBuyRate,
          minTraderSellRateFiat: minTraderSellRate,
          maxTraderSellRateFiat: maxTraderSellRate,
          maxTraderSpreadFiat: maxTraderSpread,
          maxBuyAboveWithdrawalFiat: maxBuyAboveWithdrawal,
          maxSellBelowDepositFiat: maxSellBelowDeposit,
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
        rails: _paymentRails
            .map(
              (AdminPaymentRail rail) =>
                  _paymentRailLocked(rail)
                      ? rail.copyWith(
                        depositsEnabled: false,
                        withdrawalsEnabled: false,
                        isLive: false,
                        maintenanceMessage:
                            'Paystack is unavailable for production. Use KoraPay or manual bank transfer.',
                      )
                      : rail,
            )
            .toList(growable: false),
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

  Future<void> _showBanUserDialog() async {
    final TextEditingController userIdController = TextEditingController();
    final TextEditingController reasonController = TextEditingController();
    final bool? confirmed = await showDialog<bool>(
      context: context,
      builder: (BuildContext dialogContext) {
        return AlertDialog(
          title: const Text('Ban account'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              TextField(
                controller: userIdController,
                decoration: const InputDecoration(
                  labelText: 'User ID',
                  hintText: 'Account to ban',
                ),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: reasonController,
                minLines: 1,
                maxLines: 3,
                decoration: const InputDecoration(
                  labelText: 'Reason',
                  hintText: 'Shown in the audit trail',
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'Deactivates the account and freezes wallet, trading, and withdrawals pending manual review.',
                style: TextStyle(fontSize: 12),
              ),
            ],
          ),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(dialogContext).pop(true),
              child: const Text('Ban account'),
            ),
          ],
        );
      },
    );
    final String userId = userIdController.text.trim();
    final String reason = reasonController.text.trim();
    userIdController.dispose();
    reasonController.dispose();
    if (confirmed != true) {
      return;
    }
    if (userId.isEmpty || reason.length < 3) {
      if (mounted) {
        AppFeedback.showError(
          context,
          'Enter a user ID and a reason of at least 3 characters.',
        );
      }
      return;
    }
    final GteAuthedApi? api = widget.authedApi;
    if (api == null) {
      if (mounted) {
        AppFeedback.showError(context, 'Admin session is not connected.');
      }
      return;
    }
    try {
      await api.post(
        '/api/admin/ban-user',
        body: <String, Object?>{
          'user_id': userId,
          'reason': reason,
          'deactivate_account': true,
          'freeze_wallet': true,
          'block_trading': true,
          'block_withdrawals': true,
          'require_manual_review': true,
        },
      );
      if (mounted) {
        AppFeedback.showSuccess(context, 'Account banned and restricted.');
      }
    } catch (error) {
      if (mounted) {
        AppFeedback.showError(context, error);
      }
    }
  }

  Future<void> _showJackpotAdminDialog() async {
    final GteAuthedApi? api = widget.authedApi;
    if (api == null) {
      AppFeedback.showError(context, 'Admin session is not connected.');
      return;
    }
    Map<String, dynamic> runtime;
    try {
      runtime = await api.getMap('/api/admin/jackpot/runtime');
    } catch (error) {
      if (mounted) {
        AppFeedback.showError(context, error);
      }
      return;
    }
    if (!mounted) {
      return;
    }
    await showDialog<void>(
      context: context,
      builder: (BuildContext dialogContext) {
        bool busy = false;
        return StatefulBuilder(
          builder: (BuildContext context, void Function(void Function()) setLocal) {
            Future<void> refresh() async {
              final Map<String, dynamic> latest =
                  await api.getMap('/api/admin/jackpot/runtime');
              setLocal(() => runtime = latest);
            }

            Future<void> run(Future<void> Function() action, String success) async {
              setLocal(() => busy = true);
              try {
                await action();
                await refresh();
                if (dialogContext.mounted) {
                  AppFeedback.showSuccess(dialogContext, success);
                }
              } catch (error) {
                if (dialogContext.mounted) {
                  AppFeedback.showError(dialogContext, error);
                }
              } finally {
                setLocal(() => busy = false);
              }
            }

            return AlertDialog(
              title: const Text('Jackpot control'),
              content: SizedBox(
                width: 420,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    _metricRow('Current balance', runtime['balance']),
                    _metricRow('Round', runtime['round_number']),
                    _metricRow('Status', runtime['status']),
                    _metricRow('Participants', runtime['participant_count']),
                    _metricRow('Trigger threshold', runtime['threshold_amount']),
                    _metricRow('Probability cap', runtime['probability_cap']),
                    _metricRow('Contribution rate', runtime['contribution_rate']),
                    _metricRow('Distribution', runtime['distribution_mode']),
                    _metricRow('Failsafe (hours)', runtime['failsafe_hours']),
                    if (busy) ...<Widget>[
                      const SizedBox(height: 12),
                      const LinearProgressIndicator(),
                    ],
                  ],
                ),
              ),
              actions: <Widget>[
                TextButton(
                  onPressed: busy ? null : () => Navigator.of(dialogContext).pop(),
                  child: const Text('Close'),
                ),
                TextButton(
                  onPressed: busy
                      ? null
                      : () async {
                          final ({double balance, String reason})? input =
                              await _promptJackpotBalance(dialogContext);
                          if (input == null) {
                            return;
                          }
                          await run(
                            () => api.request(
                              'PATCH',
                              '/api/admin/jackpot/balance',
                              body: <String, Object?>{
                                'balance': input.balance,
                                if (input.reason.isNotEmpty) 'reason': input.reason,
                              },
                            ),
                            'Jackpot balance updated.',
                          );
                        },
                  child: const Text('Set balance'),
                ),
                TextButton(
                  onPressed: busy
                      ? null
                      : () async {
                          final Map<String, Object?>? settings =
                              await _promptJackpotSettings(dialogContext, runtime);
                          if (settings == null) {
                            return;
                          }
                          await run(
                            () => api.post(
                              '/api/admin/jackpot/runtime',
                              body: settings,
                            ),
                            'Jackpot runtime settings saved.',
                          );
                        },
                  child: const Text('Edit settings'),
                ),
                FilledButton(
                  onPressed: busy
                      ? null
                      : () async {
                          final bool ok = await _confirmDialog(
                            dialogContext,
                            title: 'Trigger jackpot round?',
                            message:
                                'This settles the current round now and pays out winners. This cannot be undone.',
                            confirmLabel: 'Trigger now',
                          );
                          if (!ok) {
                            return;
                          }
                          await run(
                            () async {
                              await api.post('/api/admin/jackpot/trigger');
                            },
                            'Jackpot round triggered.',
                          );
                        },
                  child: const Text('Trigger round'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  Widget _metricRow(String label, Object? value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: <Widget>[
          Text(label, style: const TextStyle(color: Colors.white70)),
          Text(
            value?.toString() ?? '—',
            style: const TextStyle(fontWeight: FontWeight.w700),
          ),
        ],
      ),
    );
  }

  Future<bool> _confirmDialog(
    BuildContext context, {
    required String title,
    required String message,
    required String confirmLabel,
  }) async {
    final bool? result = await showDialog<bool>(
      context: context,
      builder: (BuildContext dialogContext) {
        return AlertDialog(
          title: Text(title),
          content: Text(message),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(dialogContext).pop(true),
              child: Text(confirmLabel),
            ),
          ],
        );
      },
    );
    return result ?? false;
  }

  Future<({double balance, String reason})?> _promptJackpotBalance(
    BuildContext context,
  ) async {
    final TextEditingController balanceController = TextEditingController();
    final TextEditingController reasonController = TextEditingController();
    final ({double balance, String reason})? result =
        await showDialog<({double balance, String reason})>(
      context: context,
      builder: (BuildContext dialogContext) {
        return AlertDialog(
          title: const Text('Set jackpot balance'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              TextField(
                controller: balanceController,
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(
                  labelText: 'New balance',
                  hintText: 'e.g. 25000',
                ),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: reasonController,
                minLines: 1,
                maxLines: 3,
                decoration: const InputDecoration(
                  labelText: 'Reason',
                  hintText: 'Shown in the audit trail',
                ),
              ),
            ],
          ),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () {
                final double? parsed =
                    double.tryParse(balanceController.text.trim());
                if (parsed == null || parsed < 0) {
                  AppFeedback.showError(
                    dialogContext,
                    'Enter a valid non-negative balance.',
                  );
                  return;
                }
                Navigator.of(dialogContext).pop(
                  (balance: parsed, reason: reasonController.text.trim()),
                );
              },
              child: const Text('Save'),
            ),
          ],
        );
      },
    );
    balanceController.dispose();
    reasonController.dispose();
    return result;
  }

  Future<Map<String, Object?>?> _promptJackpotSettings(
    BuildContext context,
    Map<String, dynamic> current,
  ) async {
    String text(String key) => (current[key]?.toString() ?? '');
    final TextEditingController threshold =
        TextEditingController(text: text('threshold_amount'));
    final TextEditingController probabilityLimit =
        TextEditingController(text: text('probability_limit'));
    final TextEditingController probabilityCap =
        TextEditingController(text: text('probability_cap'));
    final TextEditingController failsafeHours =
        TextEditingController(text: text('failsafe_hours'));
    final TextEditingController contributionRate =
        TextEditingController(text: text('contribution_rate'));
    final TextEditingController topSplit =
        TextEditingController(text: text('top_split_percent'));
    final TextEditingController minActivity =
        TextEditingController(text: text('min_activity_score'));
    String distribution = (current['distribution_mode']?.toString() ?? 'single_winner');
    const List<String> modes = <String>[
      'single_winner',
      'top_split',
      'activity_weighted',
    ];
    if (!modes.contains(distribution)) {
      distribution = modes.first;
    }

    Widget numberField(String label, TextEditingController controller) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: TextField(
          controller: controller,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: InputDecoration(labelText: label),
        ),
      );
    }

    final Map<String, Object?>? result = await showDialog<Map<String, Object?>>(
      context: context,
      builder: (BuildContext dialogContext) {
        return StatefulBuilder(
          builder: (BuildContext context, void Function(void Function()) setLocal) {
            return AlertDialog(
              title: const Text('Edit jackpot runtime'),
              content: SizedBox(
                width: 420,
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: <Widget>[
                      numberField('Trigger threshold', threshold),
                      numberField('Probability limit', probabilityLimit),
                      numberField('Probability cap (0-1)', probabilityCap),
                      numberField('Contribution rate (0-1)', contributionRate),
                      numberField('Top split percent (0-1)', topSplit),
                      numberField('Min activity score', minActivity),
                      numberField('Failsafe hours', failsafeHours),
                      const SizedBox(height: 6),
                      DropdownButtonFormField<String>(
                        initialValue: distribution,
                        decoration:
                            const InputDecoration(labelText: 'Distribution mode'),
                        items: modes
                            .map(
                              (String mode) => DropdownMenuItem<String>(
                                value: mode,
                                child: Text(mode.replaceAll('_', ' ')),
                              ),
                            )
                            .toList(),
                        onChanged: (String? value) {
                          if (value != null) {
                            setLocal(() => distribution = value);
                          }
                        },
                      ),
                    ],
                  ),
                ),
              ),
              actions: <Widget>[
                TextButton(
                  onPressed: () => Navigator.of(dialogContext).pop(),
                  child: const Text('Cancel'),
                ),
                FilledButton(
                  onPressed: () {
                    final double? thr = double.tryParse(threshold.text.trim());
                    final double? pLimit =
                        double.tryParse(probabilityLimit.text.trim());
                    final double? pCap =
                        double.tryParse(probabilityCap.text.trim());
                    final double? cRate =
                        double.tryParse(contributionRate.text.trim());
                    final double? split = double.tryParse(topSplit.text.trim());
                    final double? activity =
                        double.tryParse(minActivity.text.trim());
                    final int? hours = int.tryParse(failsafeHours.text.trim());
                    if (thr == null ||
                        thr <= 0 ||
                        pLimit == null ||
                        pLimit <= 0 ||
                        pCap == null ||
                        pCap <= 0 ||
                        pCap > 1 ||
                        cRate == null ||
                        cRate <= 0 ||
                        cRate > 1 ||
                        split == null ||
                        split <= 0 ||
                        split > 1 ||
                        activity == null ||
                        activity <= 0 ||
                        hours == null ||
                        hours < 1) {
                      AppFeedback.showError(
                        dialogContext,
                        'Check the values: rates/caps must be between 0 and 1, '
                        'amounts positive, failsafe at least 1 hour.',
                      );
                      return;
                    }
                    Navigator.of(dialogContext).pop(<String, Object?>{
                      'threshold_amount': thr,
                      'probability_limit': pLimit,
                      'probability_cap': pCap,
                      'contribution_rate': cRate,
                      'top_split_percent': split,
                      'min_activity_score': activity,
                      'failsafe_hours': hours,
                      'distribution_mode': distribution,
                    });
                  },
                  child: const Text('Save'),
                ),
              ],
            );
          },
        );
      },
    );
    for (final TextEditingController controller in <TextEditingController>[
      threshold,
      probabilityLimit,
      probabilityCap,
      failsafeHours,
      contributionRate,
      topSplit,
      minActivity,
    ]) {
      controller.dispose();
    }
    return result;
  }

  Future<void> _showCoinEconomyDialog() async {
    final GteAuthedApi? api = widget.authedApi;
    if (api == null) {
      AppFeedback.showError(context, 'Admin session is not connected.');
      return;
    }
    Map<String, dynamic> governor;
    try {
      governor = await api.getMap('/admin/economy/governor');
    } catch (error) {
      if (mounted) {
        AppFeedback.showError(context, error);
      }
      return;
    }
    if (!mounted) {
      return;
    }
    await showDialog<void>(
      context: context,
      builder: (BuildContext dialogContext) {
        bool busy = false;
        return StatefulBuilder(
          builder: (BuildContext context, void Function(void Function()) setLocal) {
            Future<void> refresh() async {
              final Map<String, dynamic> latest =
                  await api.getMap('/admin/economy/governor');
              setLocal(() => governor = latest);
            }

            Future<void> run(Future<void> Function() action, String success) async {
              setLocal(() => busy = true);
              try {
                await action();
                await refresh();
                if (dialogContext.mounted) {
                  AppFeedback.showSuccess(dialogContext, success);
                }
              } catch (error) {
                if (dialogContext.mounted) {
                  AppFeedback.showError(dialogContext, error);
                }
              } finally {
                setLocal(() => busy = false);
              }
            }

            final Map<String, dynamic> metrics = (governor['metrics'] is Map)
                ? Map<String, dynamic>.from(governor['metrics'] as Map)
                : <String, dynamic>{};
            final List<dynamic> actions =
                (governor['recommended_actions'] is List)
                    ? List<dynamic>.from(governor['recommended_actions'] as List)
                    : <dynamic>[];

            return AlertDialog(
              title: const Text('Coin economy governor'),
              content: SizedBox(
                width: 440,
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      _metricRow('Mode', governor['mode']),
                      _metricRow('GTEX supply', metrics['gtex_supply']),
                      _metricRow('Fan-coin supply', metrics['fan_supply']),
                      _metricRow('Treasury balance', metrics['treasury_balance']),
                      _metricRow('Daily mint', metrics['daily_mint']),
                      _metricRow('Daily burn', metrics['daily_burn']),
                      _metricRow('Inflation rate', metrics['inflation_rate']),
                      const Divider(height: 22),
                      _metricRow('Tournament entry ×',
                          governor['tournament_entry_multiplier']),
                      _metricRow('Match-view cost ×',
                          governor['match_view_cost_multiplier']),
                      _metricRow('Reward payout ×',
                          governor['reward_payout_multiplier']),
                      _metricRow('Free prize ×', governor['free_prize_multiplier']),
                      _metricRow('Agent activity ×',
                          governor['agent_activity_multiplier']),
                      _metricRow('Price-change limit',
                          governor['price_change_limit']),
                      _metricRow('Conversion bonus (bps)',
                          governor['conversion_bonus_bps']),
                      _metricRow('Burn bonus (bps)', governor['burn_bonus_bps']),
                      if (actions.isNotEmpty) ...<Widget>[
                        const Divider(height: 22),
                        const Text(
                          'Recommended actions',
                          style: TextStyle(fontWeight: FontWeight.w700),
                        ),
                        const SizedBox(height: 6),
                        ...actions.map((dynamic action) {
                          final Map<String, dynamic> entry = (action is Map)
                              ? Map<String, dynamic>.from(action)
                              : <String, dynamic>{};
                          return _metricRow(
                            entry['type']?.toString() ?? 'action',
                            entry['value'],
                          );
                        }),
                      ],
                      if (busy) ...<Widget>[
                        const SizedBox(height: 12),
                        const LinearProgressIndicator(),
                      ],
                    ],
                  ),
                ),
              ),
              actions: <Widget>[
                TextButton(
                  onPressed: busy ? null : () => Navigator.of(dialogContext).pop(),
                  child: const Text('Close'),
                ),
                TextButton(
                  onPressed: busy
                      ? null
                      : () => run(
                            () async {
                              await api.post('/admin/economy/governor/evaluate');
                            },
                            'Governor re-evaluated.',
                          ),
                  child: const Text('Re-evaluate'),
                ),
                FilledButton(
                  onPressed: busy
                      ? null
                      : () async {
                          final Map<String, Object?>? policy =
                              await _promptEconomyPolicy(dialogContext, governor);
                          if (policy == null) {
                            return;
                          }
                          await run(
                            () => api.post(
                              '/admin/economy/governor/policy',
                              body: policy,
                            ),
                            'Economy policy saved.',
                          );
                        },
                  child: const Text('Edit policy'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  Future<Map<String, Object?>?> _promptEconomyPolicy(
    BuildContext context,
    Map<String, dynamic> current,
  ) async {
    String text(String key) => (current[key]?.toString() ?? '');
    final TextEditingController tournament =
        TextEditingController(text: text('tournament_entry_multiplier'));
    final TextEditingController matchView =
        TextEditingController(text: text('match_view_cost_multiplier'));
    final TextEditingController reward =
        TextEditingController(text: text('reward_payout_multiplier'));
    final TextEditingController freePrize =
        TextEditingController(text: text('free_prize_multiplier'));
    final TextEditingController agent =
        TextEditingController(text: text('agent_activity_multiplier'));
    final TextEditingController priceLimit =
        TextEditingController(text: text('price_change_limit'));
    final TextEditingController conversionBps =
        TextEditingController(text: text('conversion_bonus_bps'));
    final TextEditingController burnBps =
        TextEditingController(text: text('burn_bonus_bps'));
    String mode = (current['mode']?.toString() ?? 'auto');
    const List<String> modes = <String>['auto', 'manual'];
    if (!modes.contains(mode)) {
      mode = 'auto';
    }

    Widget numberField(String label, TextEditingController controller) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: TextField(
          controller: controller,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: InputDecoration(labelText: label),
        ),
      );
    }

    final Map<String, Object?>? result = await showDialog<Map<String, Object?>>(
      context: context,
      builder: (BuildContext dialogContext) {
        return StatefulBuilder(
          builder: (BuildContext context, void Function(void Function()) setLocal) {
            return AlertDialog(
              title: const Text('Edit economy policy'),
              content: SizedBox(
                width: 440,
                child: SingleChildScrollView(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: <Widget>[
                      DropdownButtonFormField<String>(
                        initialValue: mode,
                        decoration: const InputDecoration(labelText: 'Mode'),
                        items: modes
                            .map(
                              (String value) => DropdownMenuItem<String>(
                                value: value,
                                child: Text(value),
                              ),
                            )
                            .toList(),
                        onChanged: (String? value) {
                          if (value != null) {
                            setLocal(() => mode = value);
                          }
                        },
                      ),
                      numberField('Tournament entry ×', tournament),
                      numberField('Match-view cost ×', matchView),
                      numberField('Reward payout ×', reward),
                      numberField('Free prize ×', freePrize),
                      numberField('Agent activity ×', agent),
                      numberField('Price-change limit (0-1)', priceLimit),
                      numberField('Conversion bonus (bps, 0-5000)', conversionBps),
                      numberField('Burn bonus (bps, 0-5000)', burnBps),
                    ],
                  ),
                ),
              ),
              actions: <Widget>[
                TextButton(
                  onPressed: () => Navigator.of(dialogContext).pop(),
                  child: const Text('Cancel'),
                ),
                FilledButton(
                  onPressed: () {
                    final double? tEntry = double.tryParse(tournament.text.trim());
                    final double? mView = double.tryParse(matchView.text.trim());
                    final double? rPay = double.tryParse(reward.text.trim());
                    final double? fPrize = double.tryParse(freePrize.text.trim());
                    final double? aAct = double.tryParse(agent.text.trim());
                    final double? pLimit = double.tryParse(priceLimit.text.trim());
                    final int? cBps = int.tryParse(conversionBps.text.trim());
                    final int? bBps = int.tryParse(burnBps.text.trim());
                    if (tEntry == null ||
                        tEntry < 0 ||
                        mView == null ||
                        mView < 0 ||
                        rPay == null ||
                        rPay < 0 ||
                        fPrize == null ||
                        fPrize < 0 ||
                        aAct == null ||
                        aAct < 0 ||
                        pLimit == null ||
                        pLimit < 0 ||
                        pLimit > 1 ||
                        cBps == null ||
                        cBps < 0 ||
                        cBps > 5000 ||
                        bBps == null ||
                        bBps < 0 ||
                        bBps > 5000) {
                      AppFeedback.showError(
                        dialogContext,
                        'Check values: multipliers ≥ 0, price limit 0–1, '
                        'bonus bps 0–5000.',
                      );
                      return;
                    }
                    Navigator.of(dialogContext).pop(<String, Object?>{
                      'mode': mode,
                      'tournament_entry_multiplier': tEntry,
                      'match_view_cost_multiplier': mView,
                      'reward_payout_multiplier': rPay,
                      'free_prize_multiplier': fPrize,
                      'agent_activity_multiplier': aAct,
                      'price_change_limit': pLimit,
                      'conversion_bonus_bps': cBps,
                      'burn_bonus_bps': bBps,
                    });
                  },
                  child: const Text('Save'),
                ),
              ],
            );
          },
        );
      },
    );
    for (final TextEditingController controller in <TextEditingController>[
      tournament,
      matchView,
      reward,
      freePrize,
      agent,
      priceLimit,
      conversionBps,
      burnBps,
    ]) {
      controller.dispose();
    }
    return result;
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
        unit: 'coin',
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
        unit: 'coin',
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
      AppFeedback.showSuccess(context, 'GTEX Coin credited.');
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
        _withdrawalControls != null ||
        _operationsReadiness != null;
    return GtexProductionFlowScaffold(
      title: 'Admin command center',
      subtitle:
          'Live treasury rails, user-credit controls, payment queues, and GTEX competition operations.',
      icon: Icons.admin_panel_settings_outlined,
      accent: GteShellTheme.accentAdmin,
      statusLabel: 'Admin dashboard',
      actions: <Widget>[
        IconButton(
          tooltip: 'Refresh admin console',
          onPressed: _load,
          icon: const Icon(Icons.refresh),
        ),
      ],
      child:
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
                    _buildWarRoomHero(context),
                    const SizedBox(height: 18),
                    GtexLiveTickerBar(
                      accentColor: GteShellTheme.accentAdmin,
                      items: <String>[
                        if (_depositQueue != null)
                          '${_depositQueue!.items.length} deposits are sitting in the live review lane',
                        if (_paymentRails.isNotEmpty)
                          '${_paymentRails.where((AdminPaymentRail rail) => rail.depositsEnabled).length} deposit rails are open to users',
                        if (_withdrawalControls != null)
                          'Withdrawal processor is ${_withdrawalControls!.processorMode.toUpperCase()} with trade payouts ${_withdrawalControls!.tradeWithdrawalsEnabled ? 'LIVE' : 'PAUSED'}',
                        if (_lastCompetitionSummary != null)
                          _lastCompetitionSummary!,
                        if (_operationsReadiness != null)
                          'Operations readiness is ${_opsStatusLabel(_operationsReadiness!.status).toUpperCase()} with ${_operationsReadiness!.alertCount} alert signals',
                        if (_error != null)
                          'War room is holding the last stable snapshot while systems recalibrate',
                      ],
                    ),
                    const SizedBox(height: 18),
                    _buildOverviewPanel(context),
                    const SizedBox(height: 18),
                    if (_operationsReadiness != null) ...<Widget>[
                      _buildOperationsReadinessPanel(context),
                      const SizedBox(height: 18),
                    ],
                    _buildOperationsRoutesPanel(context),
                    const SizedBox(height: 18),
                    _buildCompetitionHostPanel(context),
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
            'Use this dashboard to control payment availability, competition operations, bank-transfer details, manual deposit review, and direct GTEX Coin wallet funding.',
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
            'Automatic wallet checkout in the app uses KoraPay when that rail is live. Manual bank transfer availability follows the treasury modes and active bank account below; Paystack is blocked until it is explicitly reintroduced.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }

  Widget _buildOperationsReadinessPanel(BuildContext context) {
    final AdminOperationsReadinessSnapshot snapshot = _operationsReadiness!;
    final List<AdminOperationsQueue> queues = snapshot.queues
        .take(6)
        .toList(growable: false);
    final List<AdminOperationsLaunchGate> launchGates = snapshot.launchGates
        .where(
          (AdminOperationsLaunchGate gate) =>
              gate.killSwitchEnabled ||
              !gate.enabled ||
              gate.launchState != 'public',
        )
        .take(6)
        .toList(growable: false);
    return GteSurfacePanel(
      emphasized: snapshot.status != 'ok',
      accentColor: _opsAccent(snapshot.status),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          _SectionHeader(
            title: 'Operations readiness',
            subtitle:
                'Live trust, risk, policy, diagnostics, infrastructure, payment rails, ledger and worker signals collected from existing GTEX engines.',
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              _AdminStatTile(
                label: 'Readiness',
                value: _opsStatusLabel(snapshot.status),
              ),
              _AdminStatTile(
                label: 'Alerts',
                value: snapshot.alertCount.toString(),
              ),
              _AdminStatTile(
                label: 'Blocked queues',
                value: snapshot.blockedQueueCount.toString(),
              ),
              _AdminStatTile(
                label: 'Kill switches',
                value: snapshot.killSwitchCount.toString(),
              ),
            ],
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              FilledButton.tonalIcon(
                onPressed: () => context.go('/admin/trust-ops'),
                icon: const Icon(Icons.policy_outlined),
                label: const Text('Open trust ops'),
              ),
              FilledButton.tonalIcon(
                onPressed: () => context.go('/admin/launch-control'),
                icon: const Icon(Icons.tune_outlined),
                label: const Text('Open launch control'),
              ),
              FilledButton.tonalIcon(
                onPressed:
                    _notifyingReadinessBlockers
                        ? null
                        : _notifyOperationsReadinessBlockers,
                icon: const Icon(Icons.notifications_active_outlined),
                label: Text(
                  _notifyingReadinessBlockers
                      ? 'Notifying blockers'
                      : 'Notify blockers',
                ),
              ),
            ],
          ),
          if (_readinessDispatchMessage != null) ...<Widget>[
            const SizedBox(height: 10),
            GteSurfacePanel(
              padding: const EdgeInsets.all(12),
              accentColor: GteShellTheme.positive,
              child: Text(_readinessDispatchMessage!),
            ),
          ],
          if (launchGates.isNotEmpty) ...<Widget>[
            const SizedBox(height: 14),
            _SectionHeader(
              title: 'Launch gates',
              subtitle:
                  'Non-public, paused, disabled, beta, maintenance, or kill-switch modules from Batch 34.',
            ),
            const SizedBox(height: 10),
            for (final AdminOperationsLaunchGate gate
                in launchGates) ...<Widget>[
              _OperationsLaunchGateRow(
                gate: gate,
                statusLabel: _launchGateStatusLabel(gate),
                accent: _launchGateAccent(gate),
                onOpen:
                    gate.route == null
                        ? null
                        : () => _openRouteString(context, gate.route),
              ),
              const SizedBox(height: 8),
            ],
          ],
          const SizedBox(height: 14),
          for (final AdminOperationsQueue queue in queues) ...<Widget>[
            _OperationsReadinessRow(
              title: queue.title,
              status: _opsStatusLabel(queue.status),
              detail:
                  queue.alerts.isNotEmpty
                      ? queue.alerts.first
                      : queue.description,
              accent: _opsAccent(queue.status),
              actionRoutes: queue.actionRoutes,
              onOpenActionRoute:
                  (String route) => _openRouteString(context, route),
            ),
            const SizedBox(height: 8),
          ],
        ],
      ),
    );
  }

  String _opsStatusLabel(String status) {
    switch (status) {
      case 'blocked':
        return 'Blocked';
      case 'attention':
        return 'Needs attention';
      case 'gated':
        return 'Gated';
      case 'maintenance':
        return 'Maintenance';
      default:
        return 'Healthy';
    }
  }

  Color _opsAccent(String status) {
    switch (status) {
      case 'blocked':
        return Colors.redAccent;
      case 'attention':
      case 'maintenance':
        return Colors.orangeAccent;
      case 'gated':
        return Colors.amberAccent;
      default:
        return GteShellTheme.accentAdmin;
    }
  }

  String _launchGateStatusLabel(AdminOperationsLaunchGate gate) {
    if (gate.killSwitchEnabled) {
      return 'Kill switch';
    }
    if (!gate.enabled) {
      return 'Off';
    }
    return _opsStatusLabel(gate.launchState);
  }

  Color _launchGateAccent(AdminOperationsLaunchGate gate) {
    if (gate.killSwitchEnabled || !gate.enabled) {
      return Colors.redAccent;
    }
    return _opsAccent(gate.launchState);
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
              FilledButton.tonalIcon(
                onPressed: () => context.go('/admin/launch-control'),
                icon: const Icon(Icons.tune_outlined),
                label: const Text('Launch control'),
              ),
              FilledButton.tonalIcon(
                onPressed: () => context.go('/admin/trust-ops'),
                icon: const Icon(Icons.policy_outlined),
                label: const Text('Trust ops'),
              ),
              FilledButton.tonalIcon(
                onPressed: () => context.go('/admin/matchday-economy'),
                icon: const Icon(Icons.query_stats_outlined),
                label: const Text('Matchday economy'),
              ),
              FilledButton.tonalIcon(
                onPressed: () => context.go('/admin/coin-traders'),
                icon: const Icon(Icons.currency_exchange_outlined),
                label: const Text('Coin trader ops'),
              ),
              FilledButton.tonalIcon(
                onPressed: () => context.go('/admin/notifications'),
                icon: const Icon(Icons.notifications_active_outlined),
                label: const Text('Notification matrix'),
              ),
              FilledButton.tonalIcon(
                onPressed: () => _showBanUserDialog(),
                icon: const Icon(Icons.gpp_bad_outlined),
                label: const Text('Ban account'),
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
              FilledButton.tonalIcon(
                onPressed: () => _showJackpotAdminDialog(),
                icon: const Icon(Icons.celebration_outlined),
                label: const Text('Jackpot control'),
              ),
              FilledButton.tonalIcon(
                onPressed: () => _showCoinEconomyDialog(),
                icon: const Icon(Icons.account_balance_wallet_outlined),
                label: const Text('Coin economy'),
              ),
              _buildRouteLauncher(
                context: context,
                label: 'GTEX jackpot (public)',
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

  Widget _buildCompetitionHostPanel(BuildContext context) {
    return GteSurfacePanel(
      accentColor: GteShellTheme.accent,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const _SectionHeader(
            title: 'GTEX competition hosting',
            subtitle:
                'Create official GTEX hosted competitions from admin. These are free for users to join; user-created competitions use Fan Coin.',
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _competitionTitleController,
            decoration: const InputDecoration(
              labelText: 'Competition title',
              hintText: 'Weekend Manager Cup',
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _competitionTemplateController,
            decoration: const InputDecoration(
              labelText: 'Template key',
              helperText: 'Use a seeded hosted template key.',
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _competitionPasscodeController,
            decoration: const InputDecoration(
              labelText: 'Passcode (optional)',
              helperText: 'Leave empty for open entry.',
            ),
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              FilledButton.icon(
                onPressed:
                    _creatingGtexCompetition
                        ? null
                        : _createGtexHostedCompetition,
                icon: const Icon(Icons.emoji_events_outlined),
                label: Text(
                  _creatingGtexCompetition
                      ? 'Creating...'
                      : 'Create GTEX competition',
                ),
              ),
              OutlinedButton.icon(
                onPressed:
                    _creatingGtexCompetition
                        ? null
                        : () async {
                          try {
                            await _api.client.post(
                              '/api/admin/hosted-competitions/seed',
                            );
                            if (context.mounted) {
                              AppFeedback.showSuccess(
                                context,
                                'Competition templates seeded.',
                              );
                            }
                          } catch (error) {
                            if (context.mounted) {
                              AppFeedback.showError(context, error);
                            }
                          }
                        },
                icon: const Icon(Icons.library_add_check_outlined),
                label: const Text('Seed templates'),
              ),
            ],
          ),
          if (_lastCompetitionSummary != null) ...<Widget>[
            const SizedBox(height: 12),
            Text(_lastCompetitionSummary!),
          ],
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
                    controller: _minTraderBuyRateController,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    decoration: const InputDecoration(
                      labelText: 'Trader buy min',
                    ),
                  ),
                  TextField(
                    controller: _maxTraderBuyRateController,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    decoration: const InputDecoration(
                      labelText: 'Trader buy max',
                    ),
                  ),
                  TextField(
                    controller: _minTraderSellRateController,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    decoration: const InputDecoration(
                      labelText: 'Trader sell min',
                    ),
                  ),
                  TextField(
                    controller: _maxTraderSellRateController,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    decoration: const InputDecoration(
                      labelText: 'Trader sell max',
                    ),
                  ),
                  TextField(
                    controller: _maxTraderSpreadController,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    decoration: const InputDecoration(
                      labelText: 'Max trader spread',
                    ),
                  ),
                  TextField(
                    controller: _maxBuyAboveWithdrawalController,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    decoration: const InputDecoration(
                      labelText: 'Buy above withdrawal limit',
                    ),
                  ),
                  TextField(
                    controller: _maxSellBelowDepositController,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    decoration: const InputDecoration(
                      labelText: 'Sell below deposit limit',
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
                'Toggle KoraPay and manual bank transfer routing without leaving the admin dashboard. Paystack is blocked for now.',
          ),
          const SizedBox(height: 16),
          ..._paymentRails.asMap().entries.map((
            MapEntry<int, AdminPaymentRail> entry,
          ) {
            final int index = entry.key;
            final AdminPaymentRail rail = entry.value;
            final bool locked = _paymentRailLocked(rail);
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
                    if (locked) ...<Widget>[
                      const SizedBox(height: 8),
                      Text(
                        'This provider is unavailable for production funding and cannot be opened from the dashboard.',
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: GteShellTheme.accentWarm,
                        ),
                      ),
                    ],
                    const SizedBox(height: 8),
                    SwitchListTile.adaptive(
                      value: rail.isLive,
                      contentPadding: EdgeInsets.zero,
                      title: const Text('Provider live'),
                      onChanged:
                          locked
                              ? null
                              : (bool value) {
                                setState(() {
                                  _paymentRails[index] = rail.copyWith(
                                    isLive: value,
                                  );
                                });
                              },
                    ),
                    SwitchListTile.adaptive(
                      value: rail.depositsEnabled,
                      contentPadding: EdgeInsets.zero,
                      title: const Text('Deposits enabled'),
                      onChanged:
                          locked
                              ? null
                              : (bool value) {
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
                      onChanged:
                          locked
                              ? null
                              : (bool value) {
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
                        'Amount: ${gteFormatFiat(deposit.amountFiat, currency: deposit.currencyCode)} → ${gteFormatCompetitionAmount(deposit.amountCoin, 'coin')}',
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

class _OperationsReadinessRow extends StatelessWidget {
  const _OperationsReadinessRow({
    required this.title,
    required this.status,
    required this.detail,
    required this.accent,
    required this.actionRoutes,
    required this.onOpenActionRoute,
  });

  final String title;
  final String status;
  final String detail;
  final Color accent;
  final List<String> actionRoutes;
  final ValueChanged<String> onOpenActionRoute;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: accent.withValues(alpha: 0.42)),
        color: Colors.white.withValues(alpha: 0.025),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Container(
                width: 10,
                height: 10,
                decoration: BoxDecoration(
                  color: accent,
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(title, style: Theme.of(context).textTheme.titleSmall),
                    const SizedBox(height: 3),
                    Text(
                      detail,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 10),
              Text(status, style: Theme.of(context).textTheme.labelLarge),
            ],
          ),
          if (actionRoutes.isNotEmpty) ...<Widget>[
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: actionRoutes
                  .take(3)
                  .map(
                    (String route) => TextButton.icon(
                      onPressed: () => onOpenActionRoute(route),
                      icon: const Icon(Icons.open_in_new_outlined),
                      label: Text(_opsRouteLabel(route)),
                    ),
                  )
                  .toList(growable: false),
            ),
          ],
        ],
      ),
    );
  }
}

class _OperationsLaunchGateRow extends StatelessWidget {
  const _OperationsLaunchGateRow({
    required this.gate,
    required this.statusLabel,
    required this.accent,
    required this.onOpen,
  });

  final AdminOperationsLaunchGate gate;
  final String statusLabel;
  final Color accent;
  final VoidCallback? onOpen;

  @override
  Widget build(BuildContext context) {
    final String route = gate.route?.trim() ?? '';
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: accent.withValues(alpha: 0.42)),
        color: accent.withValues(alpha: 0.05),
      ),
      child: Row(
        children: <Widget>[
          Icon(Icons.flag_outlined, color: accent, size: 20),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(gate.title, style: Theme.of(context).textTheme.titleSmall),
                const SizedBox(height: 3),
                Text(
                  '${gate.featureKey} · ${gate.launchState} · ${gate.audience}',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                if (gate.maintenanceMessage?.trim().isNotEmpty == true)
                  Text(
                    gate.maintenanceMessage!,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
              ],
            ),
          ),
          const SizedBox(width: 10),
          Text(statusLabel, style: Theme.of(context).textTheme.labelLarge),
          if (route.isNotEmpty) ...<Widget>[
            const SizedBox(width: 8),
            IconButton(
              tooltip: 'Open ${_opsRouteLabel(route)}',
              onPressed: onOpen,
              icon: const Icon(Icons.open_in_new_outlined),
            ),
          ],
        ],
      ),
    );
  }
}

String _opsRouteLabel(String route) {
  final String cleaned = route.trim();
  if (cleaned.isEmpty) {
    return 'Open';
  }
  final List<String> parts = cleaned
      .split('/')
      .where((String part) => part.trim().isNotEmpty)
      .toList(growable: false);
  if (parts.isEmpty) {
    return cleaned;
  }
  return parts.last
      .split(RegExp(r'[-_]+'))
      .where((String part) => part.isNotEmpty)
      .map((String part) => '${part[0].toUpperCase()}${part.substring(1)}')
      .join(' ');
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

class _AdminLoadCapture<T> {
  const _AdminLoadCapture({this.value, this.error});

  final T? value;
  final String? error;
}
