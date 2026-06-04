import 'dart:async';

import 'package:flutter/material.dart';

import '../../core/app_feedback.dart';
import '../../data/admin_command_center_api.dart';
import '../../data/gte_api_repository.dart';
import '../../data/gte_models.dart';
import '../../features/app_routes/gte_navigation_helpers.dart';
import '../../features/app_routes/gte_route_data.dart';
import '../../features/navigation_guards/gte_navigation_guards.dart';
import '../../models/creator_application_models.dart';
import '../../models/moderation_models.dart';
import '../../models/risk_ops_models.dart';
import '../../shared/widgets/gtex_premium_panels.dart';
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
  Timer? _liveRefreshTimer;

  bool get _isTestBinding =>
      WidgetsBinding.instance.runtimeType.toString().contains('Test');

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
  final TextEditingController _competitionTemplateController =
      TextEditingController(text: 'user-hosted-cup-8');
  final TextEditingController _competitionTitleController =
      TextEditingController();
  final TextEditingController _competitionPasscodeController =
      TextEditingController();
  final TextEditingController _commandSearchController =
      TextEditingController();

  bool _loading = true;
  bool _savingTreasury = false;
  bool _savingRails = false;
  bool _savingWithdrawalControls = false;
  bool _creatingBankAccount = false;
  bool _previewingCredit = false;
  bool _runningCredit = false;
  bool _creatingGtexCompetition = false;
  String? _error;

  GteTreasurySettings? _treasurySettings;
  List<GteTreasuryBankAccount> _bankAccounts = <GteTreasuryBankAccount>[];
  GteAdminQueuePage<GteAdminDeposit>? _depositQueue;
  GteAdminQueuePage<GteAdminWithdrawal>? _withdrawalQueue;
  GteAdminQueuePage<GteAdminKyc>? _traderOnboardingQueue;
  GteAdminQueuePage<GteDispute>? _disputeQueue;
  List<ModerationReport>? _moderationQueue;
  List<CreatorApplicationView>? _creatorReviewQueue;
  RiskOverview? _riskOverview;
  AdminTransferBidReviewFeed? _transferBidReviewFeed;
  List<AdminPaymentRail> _paymentRails = <AdminPaymentRail>[];
  AdminWithdrawalControls? _withdrawalControls;
  AdminMarketTopupQuote? _creditQuote;
  AdminMarketTopup? _lastCreditResult;
  String? _lastCompetitionSummary;
  String? _depositQueueError;
  String? _withdrawalQueueError;
  String? _traderOnboardingQueueError;
  String? _disputeQueueError;
  String? _moderationQueueError;
  String? _creatorReviewQueueError;
  String? _riskOverviewError;
  String? _transferBidReviewError;

  GtePaymentMode _depositMode = GtePaymentMode.manual;
  GtePaymentMode _withdrawalMode = GtePaymentMode.manual;
  String? _activeBankAccountId;
  String _commandSeverityFilter = 'all';
  String _commandEscalationFilter = 'all';
  _AdminPaymentQueueTab _adminPaymentQueueTab = _AdminPaymentQueueTab.pending;
  bool _commandLockedOnly = false;
  bool _commandBulkMode = false;
  final Set<String> _depositBusyIds = <String>{};
  final Set<String> _bidBusyIds = <String>{};
  final Set<String> _bankBusyIds = <String>{};
  final Set<String> _selectedCommandRows = <String>{};

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
    _commandSearchController.dispose();
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
      final Future<_AdminLoadCapture<GteAdminQueuePage<GteAdminWithdrawal>>>
      withdrawalsFuture = _captureLoad<GteAdminQueuePage<GteAdminWithdrawal>>(
        _api.fetchAdminWithdrawals(limit: 20),
      );
      final Future<_AdminLoadCapture<GteAdminQueuePage<GteAdminKyc>>>
      traderOnboardingFuture = _captureLoad<GteAdminQueuePage<GteAdminKyc>>(
        _api.fetchAdminKyc(limit: 20),
      );
      final Future<_AdminLoadCapture<GteAdminQueuePage<GteDispute>>>
      disputesFuture = _captureLoad<GteAdminQueuePage<GteDispute>>(
        _api.fetchAdminDisputes(limit: 20),
      );
      final Future<_AdminLoadCapture<List<ModerationReport>>> moderationFuture =
          _captureLoad<List<ModerationReport>>(
            _api.fetchAdminModerationReports(),
          );
      final Future<_AdminLoadCapture<List<CreatorApplicationView>>>
      creatorReviewFuture = _captureLoad<List<CreatorApplicationView>>(
        _api.fetchAdminCreatorApplications(),
      );
      final Future<_AdminLoadCapture<RiskOverview>> riskOverviewFuture =
          _captureLoad<RiskOverview>(_api.fetchRiskOverview());
      final Future<_AdminLoadCapture<AdminPaymentRailsState>>
      paymentRailsFuture = _captureLoad<AdminPaymentRailsState>(
        _api.fetchPaymentRails(),
      );
      final Future<_AdminLoadCapture<AdminWithdrawalControls>>
      withdrawalControlsFuture = _captureLoad<AdminWithdrawalControls>(
        _api.fetchWithdrawalControls(),
      );
      final Future<_AdminLoadCapture<AdminTransferBidReviewFeed>>
      transferBidReviewFuture = _captureLoad<AdminTransferBidReviewFeed>(
        _api.fetchTransferBidReviewFeed(),
      );

      final _AdminLoadCapture<GteTreasurySettings> settingsResult =
          await settingsFuture;
      final _AdminLoadCapture<List<GteTreasuryBankAccount>> bankAccountsResult =
          await bankAccountsFuture;
      final _AdminLoadCapture<GteAdminQueuePage<GteAdminDeposit>>
      depositsResult = await depositsFuture;
      final _AdminLoadCapture<GteAdminQueuePage<GteAdminWithdrawal>>
      withdrawalsResult = await withdrawalsFuture;
      final _AdminLoadCapture<GteAdminQueuePage<GteAdminKyc>>
      traderOnboardingResult = await traderOnboardingFuture;
      final _AdminLoadCapture<GteAdminQueuePage<GteDispute>> disputesResult =
          await disputesFuture;
      final _AdminLoadCapture<List<ModerationReport>> moderationResult =
          await moderationFuture;
      final _AdminLoadCapture<List<CreatorApplicationView>>
      creatorReviewResult = await creatorReviewFuture;
      final _AdminLoadCapture<RiskOverview> riskOverviewResult =
          await riskOverviewFuture;
      final _AdminLoadCapture<AdminPaymentRailsState> paymentRailsResult =
          await paymentRailsFuture;
      final _AdminLoadCapture<AdminWithdrawalControls>
      withdrawalControlsResult = await withdrawalControlsFuture;
      final _AdminLoadCapture<AdminTransferBidReviewFeed>
      transferBidReviewResult = await transferBidReviewFuture;
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
        } else if (depositsResult.error != null) {
          _depositQueue = null;
        }
        _depositQueueError = depositsResult.error;
        if (withdrawalsResult.value != null) {
          _withdrawalQueue = withdrawalsResult.value!;
        }
        if (traderOnboardingResult.value != null) {
          _traderOnboardingQueue = traderOnboardingResult.value!;
        }
        if (disputesResult.value != null) {
          _disputeQueue = disputesResult.value!;
        }
        if (moderationResult.value != null) {
          _moderationQueue = moderationResult.value!;
        }
        if (creatorReviewResult.value != null) {
          _creatorReviewQueue = creatorReviewResult.value!;
        }
        if (riskOverviewResult.value != null) {
          _riskOverview = riskOverviewResult.value!;
        }
        _withdrawalQueueError = withdrawalsResult.error;
        _traderOnboardingQueueError = traderOnboardingResult.error;
        _disputeQueueError = disputesResult.error;
        _moderationQueueError = moderationResult.error;
        _creatorReviewQueueError = creatorReviewResult.error;
        _riskOverviewError = riskOverviewResult.error;
        _transferBidReviewError = transferBidReviewResult.error;
        if (transferBidReviewResult.value != null) {
          _transferBidReviewFeed = transferBidReviewResult.value!;
        } else if (transferBidReviewResult.error != null) {
          _transferBidReviewFeed = null;
        }
        if (paymentRailsResult.value != null) {
          _paymentRails = _canonicalPaymentRails(
            paymentRailsResult.value!.rails,
          );
        }
        if (withdrawalControlsResult.value != null) {
          _withdrawalControls = withdrawalControlsResult.value!;
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
      eyebrow: 'GOD MODE',
      title: 'Control the global football economy from one war room.',
      description:
          'Market supply, competition ignition, treasury rails, and user-credit interventions stay visible here as one coordinated control surface.',
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
      'korapay': 'KoraPay',
    };
    return labels[provider.trim().toLowerCase()] ?? _humanize(provider);
  }

  List<AdminPaymentRail> _canonicalPaymentRails(List<AdminPaymentRail> rails) {
    return rails
        .where(
          (AdminPaymentRail rail) => _isCanonicalPaymentProvider(rail.provider),
        )
        .toList(growable: false);
  }

  bool _isCanonicalPaymentProvider(String provider) {
    switch (provider.trim().toLowerCase()) {
      case 'korapay':
      case 'bank_transfer_manual':
        return true;
      default:
        return false;
    }
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

  String _transferBidStatusLabel(String status) => _humanize(status);

  String _transferBidQueueMetric() {
    final AdminTransferBidReviewFeed? feed = _transferBidReviewFeed;
    if (feed != null) {
      return feed.submittedCount == 0
          ? '${feed.bids.length}'
          : '${feed.submittedCount}';
    }
    if (_transferBidReviewError != null) {
      return 'BLOCKED';
    }
    return _loading ? 'SYNCING' : 'EMPTY';
  }

  String _transferBidTabLabel() {
    final AdminTransferBidReviewFeed? feed = _transferBidReviewFeed;
    if (feed != null) {
      return 'Bids (${feed.bids.length})';
    }
    if (_transferBidReviewError != null) {
      return 'Bids blocked';
    }
    return _loading ? 'Bids syncing' : 'Bids';
  }

  String _depositQueueMetric(int count) {
    if (_depositQueue == null && _depositQueueError != null) {
      return 'BLOCKED';
    }
    if (_depositQueue == null && _loading) {
      return 'SYNCING';
    }
    return '$count';
  }

  String _depositQueueTabLabel(String label, int count) {
    if (_depositQueue == null && _depositQueueError != null) {
      return '$label (blocked)';
    }
    if (_depositQueue == null && _loading) {
      return '$label (syncing)';
    }
    return '$label ($count)';
  }

  Widget? _buildDepositQueueAvailabilityPanel(String lane) {
    if (_depositQueue == null && _loading) {
      return GteStatePanel(
        eyebrow: 'SYNCING',
        title: '$lane payment queue syncing',
        message:
            'GTEX is reconnecting to treasury review state before exposing payment actions.',
        isLoading: true,
      );
    }
    if (_depositQueue == null && _depositQueueError != null) {
      return GteStatePanel(
        eyebrow: 'BLOCKED',
        title: 'Payment queue unavailable',
        message:
            '$lane payment state could not be loaded from the treasury deposit endpoint: $_depositQueueError',
        icon: Icons.cloud_off_outlined,
        accentColor: GteShellTheme.warning,
      );
    }
    if (_depositQueue == null) {
      return const GteStatePanel(
        eyebrow: 'BLOCKED',
        title: 'Payment queue not mounted',
        message:
            'Treasury deposit state is unavailable, so GTEX is not rendering synthetic payment rows.',
        icon: Icons.lock_outline,
        accentColor: GteShellTheme.warning,
      );
    }
    return null;
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
        return 'Pending review';
      case GteKycStatus.partialVerifiedNoId:
        return 'Partial verification';
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

  _AdminCommandSurfaceState _queueStateFor(Object? value, String? error) {
    if (error != null && value == null) {
      return _AdminCommandSurfaceState.error;
    }
    if (error != null) {
      return _AdminCommandSurfaceState.degraded;
    }
    if (value == null) {
      return _loading
          ? _AdminCommandSurfaceState.syncing
          : _AdminCommandSurfaceState.blocked;
    }
    return _AdminCommandSurfaceState.empty;
  }

  List<String> _timeline(List<MapEntry<String, DateTime?>> entries) {
    return entries
        .where((MapEntry<String, DateTime?> entry) => entry.value != null)
        .map(
          (MapEntry<String, DateTime?> entry) =>
              '${entry.key}: ${gteFormatDateTime(entry.value)}',
        )
        .toList(growable: false);
  }

  _AdminCommandSeverity _depositSeverity(GteAdminDeposit deposit) {
    switch (deposit.status) {
      case GteDepositStatus.disputed:
        return _AdminCommandSeverity.critical;
      case GteDepositStatus.paymentSubmitted:
        return _AdminCommandSeverity.high;
      case GteDepositStatus.underReview:
        return _AdminCommandSeverity.medium;
      case GteDepositStatus.awaitingPayment:
      case GteDepositStatus.confirmed:
      case GteDepositStatus.rejected:
      case GteDepositStatus.expired:
        return _AdminCommandSeverity.low;
    }
  }

  _AdminCommandEscalation _depositEscalation(GteAdminDeposit deposit) {
    switch (deposit.status) {
      case GteDepositStatus.disputed:
        return _AdminCommandEscalation.escalated;
      case GteDepositStatus.underReview:
      case GteDepositStatus.paymentSubmitted:
        return _AdminCommandEscalation.watching;
      case GteDepositStatus.confirmed:
      case GteDepositStatus.rejected:
      case GteDepositStatus.expired:
        return _AdminCommandEscalation.locked;
      case GteDepositStatus.awaitingPayment:
        return _AdminCommandEscalation.none;
    }
  }

  _AdminCommandSeverity _transferBidSeverity(AdminTransferBid bid) {
    final String severity = bid.severity?.trim().toLowerCase() ?? '';
    if (severity.isNotEmpty) {
      return _severityFromPriority(severity);
    }
    switch (bid.normalizedStatus) {
      case 'submitted':
      case 'counter':
      case 'countered':
      case 'pending':
        return _AdminCommandSeverity.high;
      case 'accepted':
      case 'rejected':
      case 'withdrawn':
        return _AdminCommandSeverity.low;
      default:
        return _AdminCommandSeverity.medium;
    }
  }

  _AdminCommandEscalation _transferBidEscalation(AdminTransferBid bid) {
    final String escalation = bid.escalationState?.trim().toLowerCase() ?? '';
    if (escalation.isNotEmpty) {
      return _escalationFromStatus(escalation);
    }
    final String actionState =
        bid.businessActionState?.trim().toLowerCase().isNotEmpty == true
            ? bid.businessActionState!.trim().toLowerCase()
            : bid.actionState?.trim().toLowerCase() ?? '';
    if (actionState.isNotEmpty) {
      return _escalationFromStatus(actionState);
    }
    switch (bid.normalizedStatus) {
      case 'submitted':
      case 'counter':
      case 'countered':
      case 'pending':
        return _AdminCommandEscalation.watching;
      case 'accepted':
      case 'rejected':
      case 'withdrawn':
        return _AdminCommandEscalation.locked;
      default:
        return _AdminCommandEscalation.none;
    }
  }

  _AdminCommandSeverity _withdrawalSeverity(GteAdminWithdrawal withdrawal) {
    switch (withdrawal.status) {
      case GteWithdrawalStatus.disputed:
        return _AdminCommandSeverity.critical;
      case GteWithdrawalStatus.pendingReview:
      case GteWithdrawalStatus.processing:
        return _AdminCommandSeverity.high;
      case GteWithdrawalStatus.pendingKyc:
      case GteWithdrawalStatus.approved:
        return _AdminCommandSeverity.medium;
      case GteWithdrawalStatus.draft:
      case GteWithdrawalStatus.rejected:
      case GteWithdrawalStatus.paid:
      case GteWithdrawalStatus.cancelled:
        return _AdminCommandSeverity.low;
    }
  }

  _AdminCommandEscalation _withdrawalEscalation(GteAdminWithdrawal withdrawal) {
    switch (withdrawal.status) {
      case GteWithdrawalStatus.disputed:
        return _AdminCommandEscalation.escalated;
      case GteWithdrawalStatus.pendingReview:
      case GteWithdrawalStatus.pendingKyc:
      case GteWithdrawalStatus.approved:
      case GteWithdrawalStatus.processing:
        return _AdminCommandEscalation.watching;
      case GteWithdrawalStatus.rejected:
      case GteWithdrawalStatus.paid:
      case GteWithdrawalStatus.cancelled:
        return _AdminCommandEscalation.locked;
      case GteWithdrawalStatus.draft:
        return _AdminCommandEscalation.none;
    }
  }

  _AdminCommandSeverity _kycSeverity(GteAdminKyc profile) {
    switch (profile.status) {
      case GteKycStatus.pending:
      case GteKycStatus.rejected:
        return _AdminCommandSeverity.high;
      case GteKycStatus.partialVerifiedNoId:
        return _AdminCommandSeverity.medium;
      case GteKycStatus.unverified:
      case GteKycStatus.fullyVerified:
        return _AdminCommandSeverity.low;
    }
  }

  _AdminCommandEscalation _kycEscalation(GteAdminKyc profile) {
    switch (profile.status) {
      case GteKycStatus.pending:
      case GteKycStatus.partialVerifiedNoId:
        return _AdminCommandEscalation.watching;
      case GteKycStatus.rejected:
      case GteKycStatus.fullyVerified:
        return _AdminCommandEscalation.locked;
      case GteKycStatus.unverified:
        return _AdminCommandEscalation.none;
    }
  }

  _AdminCommandSeverity _disputeSeverity(GteDispute dispute) {
    switch (dispute.status) {
      case GteDisputeStatus.awaitingAdmin:
      case GteDisputeStatus.open:
        return _AdminCommandSeverity.high;
      case GteDisputeStatus.awaitingUser:
        return _AdminCommandSeverity.medium;
      case GteDisputeStatus.resolved:
      case GteDisputeStatus.closed:
        return _AdminCommandSeverity.low;
    }
  }

  _AdminCommandEscalation _disputeEscalation(GteDispute dispute) {
    switch (dispute.status) {
      case GteDisputeStatus.awaitingAdmin:
        return _AdminCommandEscalation.escalated;
      case GteDisputeStatus.open:
      case GteDisputeStatus.awaitingUser:
        return _AdminCommandEscalation.watching;
      case GteDisputeStatus.resolved:
      case GteDisputeStatus.closed:
        return _AdminCommandEscalation.locked;
    }
  }

  _AdminCommandSeverity _severityFromPriority(String priority) {
    switch (priority.trim().toLowerCase()) {
      case 'critical':
      case 'urgent':
        return _AdminCommandSeverity.critical;
      case 'high':
        return _AdminCommandSeverity.high;
      case 'low':
        return _AdminCommandSeverity.low;
      default:
        return _AdminCommandSeverity.medium;
    }
  }

  _AdminCommandEscalation _escalationFromStatus(String status) {
    switch (status.trim().toLowerCase()) {
      case 'critical':
      case 'escalated':
      case 'awaiting_admin':
      case 'awaiting-admin':
        return _AdminCommandEscalation.escalated;
      case 'resolved':
      case 'closed':
      case 'approved':
      case 'rejected':
      case 'actioned':
      case 'dismissed':
        return _AdminCommandEscalation.locked;
      case 'in_review':
      case 'under_review':
      case 'pending':
      case 'open':
      case 'watching':
        return _AdminCommandEscalation.watching;
      default:
        return _AdminCommandEscalation.none;
    }
  }

  List<_AdminCommandQueueRow> _depositRows() {
    return (_depositQueue?.items ?? const <GteAdminDeposit>[])
        .map((GteAdminDeposit deposit) {
          final bool disputed = deposit.status == GteDepositStatus.disputed;
          final bool terminal =
              deposit.status == GteDepositStatus.confirmed ||
              deposit.status == GteDepositStatus.rejected ||
              deposit.status == GteDepositStatus.expired;
          final bool actionable = !terminal && !disputed;
          final String actor =
              deposit.userFullName?.trim().isNotEmpty == true
                  ? deposit.userFullName!
                  : deposit.userEmail;
          return _AdminCommandQueueRow(
            id: 'payment-proof:${deposit.id}',
            surface: 'Payment proofs',
            reference: deposit.reference,
            title: 'Manual bank-transfer proof',
            actor: actor,
            timestamp: deposit.submittedAt ?? deposit.createdAt,
            severity: _depositSeverity(deposit),
            escalation: _depositEscalation(deposit),
            status: _depositStatusLabel(deposit.status),
            notes:
                disputed
                    ? 'Disputed payment proof is blocked from direct treasury approval until the dispute lane resolves it.'
                    : deposit.adminNotes?.trim().isNotEmpty == true
                    ? deposit.adminNotes!
                    : 'No admin notes captured yet.',
            auditTrail: <String>[
              'User ID: ${deposit.userId}',
              'Amount: ${gteFormatFiat(deposit.amountFiat, currency: deposit.currencyCode)} -> ${gteFormatCompetitionAmount(deposit.amountCoin, 'coin')}',
              if (deposit.senderBank?.trim().isNotEmpty == true)
                'Sender bank: ${deposit.senderBank}',
              if (deposit.transferReference?.trim().isNotEmpty == true)
                'Transfer reference: ${deposit.transferReference}',
              ..._timeline(<MapEntry<String, DateTime?>>[
                MapEntry<String, DateTime?>('Created', deposit.createdAt),
                MapEntry<String, DateTime?>('Submitted', deposit.submittedAt),
                MapEntry<String, DateTime?>('Reviewed', deposit.reviewedAt),
                MapEntry<String, DateTime?>('Confirmed', deposit.confirmedAt),
                MapEntry<String, DateTime?>('Rejected', deposit.rejectedAt),
              ]),
            ],
            isLocked: terminal || disputed,
            actions: <_AdminCommandAction>[
              if (disputed)
                const _AdminCommandAction(
                  label: 'Dispute review required',
                  icon: Icons.lock_outline,
                )
              else ...<_AdminCommandAction>[
                _AdminCommandAction(
                  label: 'Mark reviewing',
                  icon: Icons.visibility_outlined,
                  onPressed:
                      actionable && !_depositBusyIds.contains(deposit.id)
                          ? () => _runDepositAction(
                            deposit,
                            _DepositAdminAction.review,
                          )
                          : null,
                ),
                _AdminCommandAction(
                  label: 'Confirm payment',
                  icon: Icons.check_circle_outline,
                  emphasized: true,
                  onPressed:
                      actionable && !_depositBusyIds.contains(deposit.id)
                          ? () => _runDepositAction(
                            deposit,
                            _DepositAdminAction.confirm,
                          )
                          : null,
                ),
                _AdminCommandAction(
                  label: 'Reject',
                  icon: Icons.block_outlined,
                  onPressed:
                      actionable && !_depositBusyIds.contains(deposit.id)
                          ? () => _runDepositAction(
                            deposit,
                            _DepositAdminAction.reject,
                          )
                          : null,
                ),
              ],
            ],
          );
        })
        .toList(growable: false);
  }

  List<_AdminCommandQueueRow> _withdrawalRows() {
    return (_withdrawalQueue?.items ?? const <GteAdminWithdrawal>[])
        .map((GteAdminWithdrawal withdrawal) {
          final String actor =
              withdrawal.userFullName?.trim().isNotEmpty == true
                  ? withdrawal.userFullName!
                  : withdrawal.userEmail;
          return _AdminCommandQueueRow(
            id: 'withdrawal:${withdrawal.id}',
            surface: 'Withdrawals',
            reference: withdrawal.reference,
            title: 'Manual payout request',
            actor: actor,
            timestamp: withdrawal.createdAt,
            severity: _withdrawalSeverity(withdrawal),
            escalation: _withdrawalEscalation(withdrawal),
            status: _withdrawalStatusLabel(withdrawal.status),
            notes: 'Bank payout review must use canonical withdrawal status.',
            auditTrail: <String>[
              'User ID: ${withdrawal.userId}',
              'Amount: ${gteFormatCompetitionAmount(withdrawal.amountCoin, 'coin')} -> ${gteFormatFiat(withdrawal.amountFiat, currency: withdrawal.currencyCode)}',
              'Bank: ${withdrawal.bankName}',
              'Account: ${withdrawal.bankAccountName}',
              ..._timeline(<MapEntry<String, DateTime?>>[
                MapEntry<String, DateTime?>('Created', withdrawal.createdAt),
                MapEntry<String, DateTime?>('Reviewed', withdrawal.reviewedAt),
                MapEntry<String, DateTime?>('Approved', withdrawal.approvedAt),
                MapEntry<String, DateTime?>(
                  'Processed',
                  withdrawal.processedAt,
                ),
                MapEntry<String, DateTime?>('Paid', withdrawal.paidAt),
                MapEntry<String, DateTime?>('Rejected', withdrawal.rejectedAt),
                MapEntry<String, DateTime?>(
                  'Cancelled',
                  withdrawal.cancelledAt,
                ),
              ]),
            ],
            isLocked:
                withdrawal.status == GteWithdrawalStatus.paid ||
                withdrawal.status == GteWithdrawalStatus.rejected ||
                withdrawal.status == GteWithdrawalStatus.cancelled,
            actions: _pendingBackendActions(<MapEntry<String, IconData>>[
              const MapEntry<String, IconData>(
                'Approve',
                Icons.check_circle_outline,
              ),
              const MapEntry<String, IconData>('Reject', Icons.block_outlined),
              const MapEntry<String, IconData>(
                'Mark paid',
                Icons.payments_outlined,
              ),
            ]),
          );
        })
        .toList(growable: false);
  }

  List<_AdminCommandQueueRow> _traderOnboardingRows() {
    return (_traderOnboardingQueue?.items ?? const <GteAdminKyc>[])
        .map((GteAdminKyc profile) {
          final String actor =
              profile.userFullName?.trim().isNotEmpty == true
                  ? profile.userFullName!
                  : profile.userEmail;
          return _AdminCommandQueueRow(
            id: 'trader-onboarding:${profile.id}',
            surface: 'Trader onboarding',
            reference: profile.id,
            title: 'KYC and trader access review',
            actor: actor,
            timestamp: profile.submittedAt,
            severity: _kycSeverity(profile),
            escalation: _kycEscalation(profile),
            status: _kycStatusLabel(profile.status),
            notes:
                profile.rejectionReason?.trim().isNotEmpty == true
                    ? profile.rejectionReason!
                    : 'No reviewer notes captured yet.',
            auditTrail: <String>[
              'User ID: ${profile.userId}',
              if (profile.country?.trim().isNotEmpty == true)
                'Country: ${profile.country}',
              ..._timeline(<MapEntry<String, DateTime?>>[
                MapEntry<String, DateTime?>('Submitted', profile.submittedAt),
                MapEntry<String, DateTime?>('Reviewed', profile.reviewedAt),
              ]),
            ],
            isLocked:
                profile.status == GteKycStatus.fullyVerified ||
                profile.status == GteKycStatus.rejected,
            actions: _pendingBackendActions(<MapEntry<String, IconData>>[
              const MapEntry<String, IconData>(
                'Approve',
                Icons.verified_user_outlined,
              ),
              const MapEntry<String, IconData>(
                'Request docs',
                Icons.assignment_late_outlined,
              ),
              const MapEntry<String, IconData>('Reject', Icons.block_outlined),
            ]),
          );
        })
        .toList(growable: false);
  }

  List<_AdminCommandQueueRow> _disputeRows() {
    return (_disputeQueue?.items ?? const <GteDispute>[])
        .map((GteDispute dispute) {
          final String actor =
              dispute.userFullName?.trim().isNotEmpty == true
                  ? dispute.userFullName!
                  : dispute.userEmail;
          return _AdminCommandQueueRow(
            id: 'dispute:${dispute.id}',
            surface: 'Disputes',
            reference: dispute.reference,
            title:
                dispute.subject?.trim().isNotEmpty == true
                    ? dispute.subject!
                    : 'Treasury dispute',
            actor: actor,
            timestamp: dispute.lastMessageAt ?? dispute.createdAt,
            severity: _disputeSeverity(dispute),
            escalation: _disputeEscalation(dispute),
            status: _disputeStatusLabel(dispute.status),
            notes: '${dispute.messages.length} messages in audit thread.',
            auditTrail: <String>[
              'Resource: ${dispute.resourceType}/${dispute.resourceId}',
              'User ID: ${dispute.userId}',
              ..._timeline(<MapEntry<String, DateTime?>>[
                MapEntry<String, DateTime?>('Created', dispute.createdAt),
                MapEntry<String, DateTime?>('Updated', dispute.updatedAt),
                MapEntry<String, DateTime?>(
                  'Last message',
                  dispute.lastMessageAt,
                ),
              ]),
            ],
            isLocked:
                dispute.status == GteDisputeStatus.resolved ||
                dispute.status == GteDisputeStatus.closed,
            actions: _pendingBackendActions(<MapEntry<String, IconData>>[
              const MapEntry<String, IconData>(
                'Assign',
                Icons.person_add_alt_outlined,
              ),
              const MapEntry<String, IconData>('Respond', Icons.reply_outlined),
              const MapEntry<String, IconData>(
                'Resolve',
                Icons.task_alt_outlined,
              ),
            ]),
          );
        })
        .toList(growable: false);
  }

  List<_AdminCommandQueueRow> _moderationRows({required bool abuseOnly}) {
    return (_moderationQueue ?? const <ModerationReport>[])
        .where(
          (ModerationReport report) =>
              !abuseOnly || report.reasonCode.toLowerCase().contains('abuse'),
        )
        .map((ModerationReport report) {
          final String surface = abuseOnly ? 'Abuse reports' : 'Moderation';
          return _AdminCommandQueueRow(
            id: '${abuseOnly ? 'abuse' : 'moderation'}:${report.id}',
            surface: surface,
            reference: report.targetId,
            title: '${_humanize(report.reasonCode)} report',
            actor:
                report.subjectUserId?.trim().isNotEmpty == true
                    ? report.subjectUserId!
                    : report.reporterUserId,
            timestamp: report.updatedAt,
            severity: _severityFromPriority(report.priority),
            escalation: _escalationFromStatus(report.status),
            status: _humanize(report.status),
            notes:
                report.resolutionNote?.trim().isNotEmpty == true
                    ? report.resolutionNote!
                    : report.description,
            auditTrail: <String>[
              'Reporter: ${report.reporterUserId}',
              if (report.subjectUserId?.trim().isNotEmpty == true)
                'Subject: ${report.subjectUserId}',
              'Target: ${report.targetType}/${report.targetId}',
              'Reports for target: ${report.reportCountForTarget}',
              if (report.evidenceUrl?.trim().isNotEmpty == true)
                'Evidence URL: ${report.evidenceUrl}',
              ..._timeline(<MapEntry<String, DateTime?>>[
                MapEntry<String, DateTime?>('Created', report.createdAt),
                MapEntry<String, DateTime?>('Updated', report.updatedAt),
              ]),
            ],
            isLocked:
                report.status == 'actioned' ||
                report.status == 'dismissed' ||
                report.status == 'resolved',
            actions: _pendingBackendActions(<MapEntry<String, IconData>>[
              const MapEntry<String, IconData>(
                'Assign',
                Icons.person_add_alt_outlined,
              ),
              const MapEntry<String, IconData>(
                'Escalate',
                Icons.priority_high_outlined,
              ),
              const MapEntry<String, IconData>(
                'Resolve',
                Icons.task_alt_outlined,
              ),
            ]),
          );
        })
        .toList(growable: false);
  }

  List<_AdminCommandQueueRow> _creatorReviewRows() {
    return (_creatorReviewQueue ?? const <CreatorApplicationView>[])
        .map((CreatorApplicationView application) {
          return _AdminCommandQueueRow(
            id: 'creator-review:${application.applicationId}',
            surface: 'Creator review',
            reference: application.applicationId,
            title: application.displayName,
            actor: application.userId,
            timestamp: application.updatedAt,
            severity:
                application.isPending
                    ? _AdminCommandSeverity.high
                    : application.needsVerificationUpdate
                    ? _AdminCommandSeverity.medium
                    : _AdminCommandSeverity.low,
            escalation: _escalationFromStatus(application.status),
            status: _humanize(application.status),
            notes:
                application.reviewNotes?.trim().isNotEmpty == true
                    ? application.reviewNotes!
                    : 'Requested handle: ${application.requestedHandle}',
            auditTrail: <String>[
              'Platform: ${application.platform}',
              'Followers: ${application.followerCount}',
              'Email verified: ${application.emailVerifiedAt != null}',
              'Phone verified: ${application.phoneVerifiedAt != null}',
              ..._timeline(<MapEntry<String, DateTime?>>[
                MapEntry<String, DateTime?>('Created', application.createdAt),
                MapEntry<String, DateTime?>('Updated', application.updatedAt),
                MapEntry<String, DateTime?>('Reviewed', application.reviewedAt),
                MapEntry<String, DateTime?>('Approved', application.approvedAt),
                MapEntry<String, DateTime?>('Rejected', application.rejectedAt),
              ]),
            ],
            isLocked: application.isApproved || application.isRejected,
            actions: _pendingBackendActions(<MapEntry<String, IconData>>[
              const MapEntry<String, IconData>(
                'Approve',
                Icons.check_circle_outline,
              ),
              const MapEntry<String, IconData>(
                'Verify',
                Icons.fact_check_outlined,
              ),
              const MapEntry<String, IconData>('Reject', Icons.block_outlined),
            ]),
          );
        })
        .toList(growable: false);
  }

  List<_AdminCommandQueueRow> _fraudRows() {
    final RiskOverview? overview = _riskOverview;
    if (overview == null || overview.openFraudCases == 0) {
      return const <_AdminCommandQueueRow>[];
    }
    return <_AdminCommandQueueRow>[
      _AdminCommandQueueRow(
        id: 'fraud-alerts:overview',
        surface: 'Fraud alerts',
        reference: 'risk-overview',
        title: '${overview.openFraudCases} open fraud cases',
        actor: 'Risk engine',
        timestamp: null,
        severity:
            overview.openFraudCases > 3 || overview.highRiskUsers > 0
                ? _AdminCommandSeverity.critical
                : _AdminCommandSeverity.high,
        escalation: _AdminCommandEscalation.escalated,
        status: 'Summary only',
        notes:
            overview.lastScanSummary?.trim().isNotEmpty == true
                ? overview.lastScanSummary!
                : 'Fraud case rows are not exposed to this command surface.',
        auditTrail: <String>[
          'Open AML cases: ${overview.openAmlCases}',
          'Open fraud cases: ${overview.openFraudCases}',
          'System events: ${overview.openSystemEvents}',
          'High-risk users: ${overview.highRiskUsers}',
          'Active scans: ${overview.activeScans}',
        ],
        isLocked: false,
        actions: _pendingBackendActions(<MapEntry<String, IconData>>[
          const MapEntry<String, IconData>('Open cases', Icons.policy_outlined),
          const MapEntry<String, IconData>('Lock users', Icons.lock_outline),
        ]),
      ),
    ];
  }

  List<_AdminCommandAction> _pendingBackendActions(
    List<MapEntry<String, IconData>> actions,
  ) {
    return actions
        .map(
          (MapEntry<String, IconData> action) =>
              _AdminCommandAction(label: action.key, icon: action.value),
        )
        .toList(growable: false);
  }

  List<_AdminCommandQueueSurface> _commandSurfaces() {
    return <_AdminCommandQueueSurface>[
      _AdminCommandQueueSurface(
        title: 'Payment proofs',
        subtitle: 'Manual bank-transfer and proof-review queue.',
        icon: Icons.receipt_long_outlined,
        state: _queueStateFor(
          _depositQueue,
          _depositQueue == null ? _error : null,
        ),
        stateMessage:
            _depositQueue == null && _error != null
                ? _error!
                : 'No payment proofs need review right now.',
        rows: _depositRows(),
      ),
      _AdminCommandQueueSurface(
        title: 'Withdrawals',
        subtitle: 'Manual payout requests, KYC posture, and payout status.',
        icon: Icons.account_balance_wallet_outlined,
        state: _queueStateFor(_withdrawalQueue, _withdrawalQueueError),
        stateMessage:
            _withdrawalQueueError ??
            'No withdrawal requests need review right now.',
        rows: _withdrawalRows(),
      ),
      _AdminCommandQueueSurface(
        title: 'Moderation',
        subtitle: 'Platform content and conduct reports.',
        icon: Icons.shield_outlined,
        state: _queueStateFor(_moderationQueue, _moderationQueueError),
        stateMessage:
            _moderationQueueError ?? 'No moderation reports are open.',
        rows: _moderationRows(abuseOnly: false),
      ),
      _AdminCommandQueueSurface(
        title: 'Abuse reports',
        subtitle: 'Abuse-tagged moderation reports isolated for escalation.',
        icon: Icons.report_gmailerrorred_outlined,
        state: _queueStateFor(_moderationQueue, _moderationQueueError),
        stateMessage: _moderationQueueError ?? 'No abuse reports are open.',
        rows: _moderationRows(abuseOnly: true),
      ),
      _AdminCommandQueueSurface(
        title: 'Disputes',
        subtitle: 'Treasury dispute cases and message audit threads.',
        icon: Icons.support_agent_outlined,
        state: _queueStateFor(_disputeQueue, _disputeQueueError),
        stateMessage: _disputeQueueError ?? 'No dispute cases are open.',
        rows: _disputeRows(),
      ),
      _AdminCommandQueueSurface(
        title: 'Creator review',
        subtitle: 'Creator applications and verification requests.',
        icon: Icons.verified_outlined,
        state: _queueStateFor(_creatorReviewQueue, _creatorReviewQueueError),
        stateMessage:
            _creatorReviewQueueError ?? 'No creator applications need review.',
        rows: _creatorReviewRows(),
      ),
      _AdminCommandQueueSurface(
        title: 'Trader onboarding',
        subtitle: 'KYC review gates used before trader access is unlocked.',
        icon: Icons.badge_outlined,
        state: _queueStateFor(
          _traderOnboardingQueue,
          _traderOnboardingQueueError,
        ),
        stateMessage:
            _traderOnboardingQueueError ??
            'No trader onboarding reviews are pending.',
        rows: _traderOnboardingRows(),
      ),
      _AdminCommandQueueSurface(
        title: 'Settlements',
        subtitle: 'Creator-league and reward settlement review lane.',
        icon: Icons.account_balance_outlined,
        state: _AdminCommandSurfaceState.blocked,
        stateMessage:
            'Settlement detail stays in the canonical creator-league settlement route until a queue summary endpoint is mounted here.',
        rows: const <_AdminCommandQueueRow>[],
        route: const CreatorLeagueSettlementsRouteData(),
        routeLabel: 'Open settlements',
      ),
      _AdminCommandQueueSurface(
        title: 'Fraud alerts',
        subtitle: 'Risk overview signals without synthetic case rows.',
        icon: Icons.policy_outlined,
        state:
            _riskOverviewError != null
                ? _AdminCommandSurfaceState.error
                : _riskOverview == null
                ? (_loading
                    ? _AdminCommandSurfaceState.syncing
                    : _AdminCommandSurfaceState.blocked)
                : _AdminCommandSurfaceState.degraded,
        stateMessage:
            _riskOverviewError ??
            'Risk overview is synced; fraud case rows are not exposed in this command surface.',
        rows: _fraudRows(),
      ),
    ];
  }

  List<_AdminCommandQueueRow> _filterCommandRows(
    List<_AdminCommandQueueRow> rows,
  ) {
    final String query = _commandSearchController.text.trim().toLowerCase();
    return rows
        .where((_AdminCommandQueueRow row) {
          if (_commandSeverityFilter != 'all' &&
              row.severity.name != _commandSeverityFilter) {
            return false;
          }
          if (_commandEscalationFilter != 'all' &&
              row.escalation.name != _commandEscalationFilter) {
            return false;
          }
          if (_commandLockedOnly && !row.isLocked) {
            return false;
          }
          if (query.isEmpty) {
            return true;
          }
          return row.searchText.toLowerCase().contains(query);
        })
        .toList(growable: false);
  }

  int _visibleCommandRowCount(List<_AdminCommandQueueSurface> surfaces) {
    return surfaces.fold<int>(
      0,
      (int count, _AdminCommandQueueSurface surface) =>
          count + _filterCommandRows(surface.rows).length,
    );
  }

  void _clearCommandFilters() {
    setState(() {
      _commandSearchController.clear();
      _commandSeverityFilter = 'all';
      _commandEscalationFilter = 'all';
      _commandLockedOnly = false;
    });
  }

  void _exportVisibleCommandRows(List<_AdminCommandQueueSurface> surfaces) {
    final int count = _visibleCommandRowCount(surfaces);
    AppFeedback.showError(
      context,
      count == 0
          ? 'No visible command rows are available for export.'
          : 'Backend export is not connected here yet; $count visible rows remain on screen.',
    );
  }

  void _lockSelectedCommandRows() {
    AppFeedback.showError(
      context,
      _selectedCommandRows.isEmpty
          ? 'Select rows before requesting a queue lock.'
          : 'Backend lock endpoint is not connected here yet; no rows were changed.',
    );
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
        _paymentRails = _canonicalPaymentRails(updated.rails);
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
    bool notesRequired = false,
  }) {
    String notes = '';
    return showDialog<String?>(
      context: context,
      builder: (BuildContext dialogContext) {
        return StatefulBuilder(
          builder: (BuildContext context, StateSetter setDialogState) {
            final bool canSubmit = !notesRequired || notes.trim().isNotEmpty;
            return AlertDialog(
              title: Text(title),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(helperText),
                  const SizedBox(height: 12),
                  TextField(
                    maxLines: 4,
                    onChanged:
                        (String value) => setDialogState(() => notes = value),
                    decoration: InputDecoration(
                      labelText: 'Admin notes',
                      hintText:
                          notesRequired
                              ? 'Required before this action is auditable'
                              : 'Optional context for audit history',
                      helperText:
                          notesRequired
                              ? 'Required for auditable action'
                              : null,
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
                      canSubmit
                          ? () => Navigator.of(dialogContext).pop(notes.trim())
                          : null,
                  child: Text(confirmLabel),
                ),
              ],
            );
          },
        );
      },
    );
  }

  Future<void> _runDepositAction(
    GteAdminDeposit deposit,
    _DepositAdminAction action,
  ) async {
    final bool notesRequired = _depositActionRequiresNotes(deposit, action);
    final String? notes = await _promptForNotes(
      title: action.dialogTitle,
      confirmLabel: action.buttonLabel,
      helperText:
          notesRequired
              ? 'Add the audit reason before changing treasury state. This note is part of the payment review trail.'
              : 'Admin notes are optional but useful for audit history and support follow-up.',
      notesRequired: notesRequired,
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
        case _DepositAdminAction.reinstate:
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

  bool _depositActionRequiresNotes(
    GteAdminDeposit deposit,
    _DepositAdminAction action,
  ) {
    if (action == _DepositAdminAction.confirm ||
        action == _DepositAdminAction.reject ||
        action == _DepositAdminAction.reinstate) {
      return true;
    }
    return deposit.status == GteDepositStatus.rejected &&
        action == _DepositAdminAction.review;
  }

  Future<void> _runBidAction(
    AdminTransferBid bid,
    _TransferBidAdminAction action,
  ) async {
    final String? notes = await _promptForNotes(
      title: action.dialogTitle,
      confirmLabel: action.buttonLabel,
      helperText:
          'This is an audit-only payment queue action. Add the operator reason before GTEX records the bid review decision.',
      notesRequired: true,
    );
    if (!mounted || notes == null) {
      return;
    }
    setState(() {
      _bidBusyIds.add(bid.id);
    });
    try {
      await _api.adminRunTransferBidAction(
        bid,
        action: action.apiKey,
        adminNotes: notes,
      );
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
          _bidBusyIds.remove(bid.id);
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
        _withdrawalControls != null;
    return Container(
      decoration: gteBackdropDecoration(),
      child: Scaffold(
        backgroundColor: Colors.transparent,
        appBar: AppBar(title: const Text('Admin dashboard')),
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
                          if (_error != null)
                            'War room is holding the last stable snapshot while systems recalibrate',
                        ],
                      ),
                      const SizedBox(height: 18),
                      _buildOverviewPanel(context),
                      const SizedBox(height: 18),
                      _buildDepositQueuePanel(context),
                      const SizedBox(height: 18),
                      _buildCommandQueuesPanel(context),
                      const SizedBox(height: 18),
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
            'Automatic wallet checkout in the app supports KoraPay when that rail is live. Manual bank transfer availability follows the treasury modes and active bank account below, and the operations launcher keeps deeper admin routes one tap away.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }

  Widget _buildCommandQueuesPanel(BuildContext context) {
    final List<_AdminCommandQueueSurface> surfaces = _commandSurfaces();
    final int visibleRows = _visibleCommandRowCount(surfaces);
    final int selectedVisibleRows =
        _selectedCommandRows
            .where(
              (String id) => surfaces.any(
                (_AdminCommandQueueSurface surface) => _filterCommandRows(
                  surface.rows,
                ).any((_AdminCommandQueueRow row) => row.id == id),
              ),
            )
            .length;
    final int degradedSurfaces =
        surfaces
            .where(
              (_AdminCommandQueueSurface surface) =>
                  surface.state == _AdminCommandSurfaceState.degraded ||
                  surface.state == _AdminCommandSurfaceState.error ||
                  surface.state == _AdminCommandSurfaceState.blocked,
            )
            .length;

    return GteSurfacePanel(
      accentColor: GteShellTheme.accentAdmin,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const _SectionHeader(
            title: 'Command queues',
            subtitle:
                'Payment proofs, payouts, disputes, moderation, creator review, trader onboarding, settlement, fraud, and abuse surfaces stay explicit about live, empty, blocked, syncing, degraded, or error state.',
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              _AdminStatTile(label: 'Visible rows', value: '$visibleRows'),
              _AdminStatTile(label: 'Selected', value: '$selectedVisibleRows'),
              _AdminStatTile(
                label: 'Blocked/degraded',
                value: '$degradedSurfaces',
              ),
            ],
          ),
          const SizedBox(height: 16),
          _buildCommandQueueControls(context, surfaces),
          const SizedBox(height: 16),
          ...surfaces.map(
            (_AdminCommandQueueSurface surface) => Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: _buildCommandSurface(context, surface),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCommandQueueControls(
    BuildContext context,
    List<_AdminCommandQueueSurface> surfaces,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        TextField(
          controller: _commandSearchController,
          decoration: const InputDecoration(
            labelText: 'Search command queues',
            prefixIcon: Icon(Icons.search),
          ),
          onChanged: (_) => setState(() {}),
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 12,
          runSpacing: 12,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: <Widget>[
            SizedBox(
              width: 220,
              child: DropdownButtonFormField<String>(
                value: _commandSeverityFilter,
                decoration: const InputDecoration(labelText: 'Severity'),
                items: const <DropdownMenuItem<String>>[
                  DropdownMenuItem<String>(value: 'all', child: Text('All')),
                  DropdownMenuItem<String>(
                    value: 'critical',
                    child: Text('Critical'),
                  ),
                  DropdownMenuItem<String>(value: 'high', child: Text('High')),
                  DropdownMenuItem<String>(
                    value: 'medium',
                    child: Text('Medium'),
                  ),
                  DropdownMenuItem<String>(value: 'low', child: Text('Low')),
                ],
                onChanged: (String? value) {
                  if (value != null) {
                    setState(() {
                      _commandSeverityFilter = value;
                    });
                  }
                },
              ),
            ),
            SizedBox(
              width: 220,
              child: DropdownButtonFormField<String>(
                value: _commandEscalationFilter,
                decoration: const InputDecoration(labelText: 'Escalation'),
                items: const <DropdownMenuItem<String>>[
                  DropdownMenuItem<String>(value: 'all', child: Text('All')),
                  DropdownMenuItem<String>(value: 'none', child: Text('None')),
                  DropdownMenuItem<String>(
                    value: 'watching',
                    child: Text('Watching'),
                  ),
                  DropdownMenuItem<String>(
                    value: 'escalated',
                    child: Text('Escalated'),
                  ),
                  DropdownMenuItem<String>(
                    value: 'locked',
                    child: Text('Locked'),
                  ),
                ],
                onChanged: (String? value) {
                  if (value != null) {
                    setState(() {
                      _commandEscalationFilter = value;
                    });
                  }
                },
              ),
            ),
            FilterChip(
              label: const Text('Locked only'),
              selected: _commandLockedOnly,
              onSelected: (bool value) {
                setState(() {
                  _commandLockedOnly = value;
                });
              },
            ),
            FilterChip(
              label: const Text('Bulk select'),
              selected: _commandBulkMode,
              onSelected: (bool value) {
                setState(() {
                  _commandBulkMode = value;
                  if (!value) {
                    _selectedCommandRows.clear();
                  }
                });
              },
            ),
            OutlinedButton.icon(
              onPressed: _clearCommandFilters,
              icon: const Icon(Icons.filter_alt_off_outlined),
              label: const Text('Clear filters'),
            ),
            OutlinedButton.icon(
              onPressed: () => _exportVisibleCommandRows(surfaces),
              icon: const Icon(Icons.download_outlined),
              label: const Text('Export visible'),
            ),
            FilledButton.tonalIcon(
              onPressed:
                  _selectedCommandRows.isEmpty
                      ? null
                      : _lockSelectedCommandRows,
              icon: const Icon(Icons.lock_outline),
              label: const Text('Lock selected'),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildCommandSurface(
    BuildContext context,
    _AdminCommandQueueSurface surface,
  ) {
    final List<_AdminCommandQueueRow> rows = _filterCommandRows(surface.rows);
    final bool filtersActive =
        _commandSearchController.text.trim().isNotEmpty ||
        _commandSeverityFilter != 'all' ||
        _commandEscalationFilter != 'all' ||
        _commandLockedOnly;
    final _AdminCommandSurfaceState renderedState =
        rows.isEmpty && surface.rows.isNotEmpty
            ? _AdminCommandSurfaceState.empty
            : surface.state;
    final String renderedMessage =
        rows.isEmpty && surface.rows.isNotEmpty && filtersActive
            ? 'No rows match the current filters.'
            : surface.stateMessage;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFF2A3A56)),
        color: Colors.black.withValues(alpha: 0.18),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Icon(surface.icon, color: GteShellTheme.accentAdmin),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      surface.title,
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      surface.subtitle,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
              _buildSurfaceStateChip(renderedState),
            ],
          ),
          const SizedBox(height: 12),
          if (rows.isEmpty)
            _buildQueueStateCard(
              context,
              surface,
              renderedState,
              renderedMessage,
            )
          else ...<Widget>[
            if (surface.state == _AdminCommandSurfaceState.degraded ||
                surface.state == _AdminCommandSurfaceState.error) ...<Widget>[
              _buildQueueStateCard(
                context,
                surface,
                surface.state,
                surface.stateMessage,
                compact: true,
              ),
              const SizedBox(height: 12),
            ],
            ...rows.map(
              (_AdminCommandQueueRow row) => Padding(
                padding: const EdgeInsets.only(bottom: 10),
                child: _buildCommandQueueRow(context, row),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildSurfaceStateChip(_AdminCommandSurfaceState state) {
    final Color color = switch (state) {
      _AdminCommandSurfaceState.syncing => GteShellTheme.accentArena,
      _AdminCommandSurfaceState.empty => GteShellTheme.positive,
      _AdminCommandSurfaceState.blocked => GteShellTheme.accentWarm,
      _AdminCommandSurfaceState.degraded => GteShellTheme.accentCapital,
      _AdminCommandSurfaceState.error => GteShellTheme.negative,
    };
    return Chip(
      avatar: Icon(_surfaceStateIcon(state), size: 18, color: color),
      label: Text(_surfaceStateLabel(state)),
      side: BorderSide(color: color.withValues(alpha: 0.5)),
    );
  }

  Widget _buildQueueStateCard(
    BuildContext context,
    _AdminCommandQueueSurface surface,
    _AdminCommandSurfaceState state,
    String message, {
    bool compact = false,
  }) {
    return Container(
      width: double.infinity,
      padding: EdgeInsets.all(compact ? 12 : 16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
        color: Colors.white.withValues(alpha: 0.04),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Icon(_surfaceStateIcon(state), size: 20),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  _surfaceStateLabel(state),
                  style: Theme.of(context).textTheme.titleSmall,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(message),
          if (surface.route != null) ...<Widget>[
            const SizedBox(height: 12),
            OutlinedButton.icon(
              onPressed: () => _openRoute(context, surface.route!),
              icon: const Icon(Icons.open_in_new_outlined),
              label: Text(surface.routeLabel ?? 'Open route'),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildCommandQueueRow(
    BuildContext context,
    _AdminCommandQueueRow row,
  ) {
    final bool selected = _selectedCommandRows.contains(row.id);
    return Container(
      key: Key('admin-command-row-${row.id}'),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
        color: Colors.white.withValues(alpha: 0.035),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              if (_commandBulkMode)
                Checkbox(
                  value: selected,
                  onChanged: (bool? value) {
                    setState(() {
                      if (value == true) {
                        _selectedCommandRows.add(row.id);
                      } else {
                        _selectedCommandRows.remove(row.id);
                      }
                    });
                  },
                ),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      row.title,
                      style: Theme.of(context).textTheme.titleSmall,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${row.surface} | ${row.reference}',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: <Widget>[
                  _buildSeverityChip(row.severity),
                  _buildEscalationChip(row.escalation),
                  if (row.isLocked) const Chip(label: Text('Locked')),
                ],
              ),
            ],
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 10,
            runSpacing: 8,
            children: <Widget>[
              _buildMetadataPill(Icons.person_outline, 'Actor: ${row.actor}'),
              _buildMetadataPill(
                Icons.schedule_outlined,
                'Timestamp: ${gteFormatDateTime(row.timestamp)}',
              ),
              _buildMetadataPill(Icons.flag_outlined, 'Status: ${row.status}'),
            ],
          ),
          const SizedBox(height: 10),
          Text('Audit trail', style: Theme.of(context).textTheme.labelLarge),
          const SizedBox(height: 6),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: row.auditTrail
                .map(
                  (String item) => Chip(
                    label: Text(item),
                    visualDensity: VisualDensity.compact,
                  ),
                )
                .toList(growable: false),
          ),
          const SizedBox(height: 10),
          Text('Notes', style: Theme.of(context).textTheme.labelLarge),
          const SizedBox(height: 4),
          Text(row.notes),
          const SizedBox(height: 12),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: row.actions
                .map((_AdminCommandAction action) {
                  if (action.emphasized) {
                    return FilledButton.icon(
                      onPressed: action.onPressed,
                      icon: Icon(action.icon),
                      label: Text(action.label),
                    );
                  }
                  return OutlinedButton.icon(
                    onPressed: action.onPressed,
                    icon: Icon(action.icon),
                    label: Text(action.label),
                  );
                })
                .toList(growable: false),
          ),
        ],
      ),
    );
  }

  Widget _buildSeverityChip(_AdminCommandSeverity severity) {
    final Color color = switch (severity) {
      _AdminCommandSeverity.critical => GteShellTheme.negative,
      _AdminCommandSeverity.high => GteShellTheme.accentWarm,
      _AdminCommandSeverity.medium => GteShellTheme.accentCapital,
      _AdminCommandSeverity.low => GteShellTheme.positive,
    };
    return Chip(
      label: Text('Severity: ${_humanize(severity.name)}'),
      side: BorderSide(color: color.withValues(alpha: 0.55)),
    );
  }

  Widget _buildEscalationChip(_AdminCommandEscalation escalation) {
    return Chip(label: Text('Escalation: ${_humanize(escalation.name)}'));
  }

  Widget _buildMetadataPill(IconData icon, String label) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        color: Colors.white.withValues(alpha: 0.05),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(icon, size: 16),
          const SizedBox(width: 6),
          Text(label),
        ],
      ),
    );
  }

  String _surfaceStateLabel(_AdminCommandSurfaceState state) {
    switch (state) {
      case _AdminCommandSurfaceState.syncing:
        return 'Syncing';
      case _AdminCommandSurfaceState.empty:
        return 'Empty';
      case _AdminCommandSurfaceState.blocked:
        return 'Blocked';
      case _AdminCommandSurfaceState.degraded:
        return 'Degraded';
      case _AdminCommandSurfaceState.error:
        return 'Error';
    }
  }

  IconData _surfaceStateIcon(_AdminCommandSurfaceState state) {
    switch (state) {
      case _AdminCommandSurfaceState.syncing:
        return Icons.sync_outlined;
      case _AdminCommandSurfaceState.empty:
        return Icons.check_circle_outline;
      case _AdminCommandSurfaceState.blocked:
        return Icons.lock_outline;
      case _AdminCommandSurfaceState.degraded:
        return Icons.warning_amber_outlined;
      case _AdminCommandSurfaceState.error:
        return Icons.error_outline;
    }
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
                'Toggle KoraPay checkout and manual bank transfer routing without leaving the admin dashboard.',
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
                  child: Text('KoraPay checkout'),
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
    final List<GteAdminDeposit> pending = items
        .where(
          (GteAdminDeposit deposit) =>
              deposit.status == GteDepositStatus.paymentSubmitted ||
              deposit.status == GteDepositStatus.underReview ||
              deposit.status == GteDepositStatus.disputed,
        )
        .toList(growable: false);
    final List<GteAdminDeposit> approved = items
        .where(
          (GteAdminDeposit deposit) =>
              deposit.status == GteDepositStatus.confirmed,
        )
        .toList(growable: false);
    final List<GteAdminDeposit> rejected = items
        .where(
          (GteAdminDeposit deposit) =>
              deposit.status == GteDepositStatus.rejected,
        )
        .toList(growable: false);

    return GteSurfacePanel(
      accentColor: GteShellTheme.accentArena,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const _SectionHeader(
            title: 'Payment Review Queue',
            subtitle:
                'Canonical v13 payment operations: Pending, Approved, Rejected, and Bids stay separated so every approval, rejection, reinstatement, or blocked backend lane is auditable.',
          ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: <Widget>[
              _AdminStatTile(
                label: 'Pending',
                value: _depositQueueMetric(pending.length),
              ),
              _AdminStatTile(
                label: 'Approved',
                value: _depositQueueMetric(approved.length),
              ),
              _AdminStatTile(
                label: 'Rejected',
                value: _depositQueueMetric(rejected.length),
              ),
              _AdminStatTile(label: 'Bids', value: _transferBidQueueMetric()),
            ],
          ),
          const SizedBox(height: 16),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: SegmentedButton<_AdminPaymentQueueTab>(
              selected: <_AdminPaymentQueueTab>{_adminPaymentQueueTab},
              onSelectionChanged: (Set<_AdminPaymentQueueTab> selected) {
                setState(() {
                  _adminPaymentQueueTab = selected.single;
                });
              },
              segments: <ButtonSegment<_AdminPaymentQueueTab>>[
                ButtonSegment<_AdminPaymentQueueTab>(
                  value: _AdminPaymentQueueTab.pending,
                  icon: const Icon(Icons.hourglass_top_outlined),
                  label: Text(_depositQueueTabLabel('Pending', pending.length)),
                ),
                ButtonSegment<_AdminPaymentQueueTab>(
                  value: _AdminPaymentQueueTab.approved,
                  icon: const Icon(Icons.verified_outlined),
                  label: Text(
                    _depositQueueTabLabel('Approved', approved.length),
                  ),
                ),
                ButtonSegment<_AdminPaymentQueueTab>(
                  value: _AdminPaymentQueueTab.rejected,
                  icon: const Icon(Icons.block_outlined),
                  label: Text(
                    _depositQueueTabLabel('Rejected', rejected.length),
                  ),
                ),
                ButtonSegment<_AdminPaymentQueueTab>(
                  value: _AdminPaymentQueueTab.bids,
                  icon: const Icon(Icons.bolt_outlined),
                  label: Text(_transferBidTabLabel()),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          _buildAdminPaymentQueueTab(
            context,
            pending: pending,
            approved: approved,
            rejected: rejected,
          ),
        ],
      ),
    );
  }

  Widget _buildAdminPaymentQueueTab(
    BuildContext context, {
    required List<GteAdminDeposit> pending,
    required List<GteAdminDeposit> approved,
    required List<GteAdminDeposit> rejected,
  }) {
    switch (_adminPaymentQueueTab) {
      case _AdminPaymentQueueTab.pending:
        final Widget? pendingAvailability = _buildDepositQueueAvailabilityPanel(
          'Pending',
        );
        if (pendingAvailability != null) {
          return pendingAvailability;
        }
        if (pending.isEmpty) {
          return const GteStatePanel(
            eyebrow: 'CONFIRMED',
            title: 'Queue clear',
            message: 'No pending or under-review payments require action.',
            icon: Icons.check_circle_outline,
            accentColor: GteShellTheme.positive,
          );
        }
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            _buildPaymentQueueBanner(
              context,
              icon: Icons.policy_outlined,
              message:
                  'Review each payment carefully. Manual bank transfers require audit notes before approval or rejection.',
            ),
            const SizedBox(height: 12),
            ...pending.map(
              (GteAdminDeposit deposit) => _buildAdminPaymentQueueRow(
                context,
                deposit,
                tab: _AdminPaymentQueueTab.pending,
              ),
            ),
          ],
        );
      case _AdminPaymentQueueTab.approved:
        final Widget? approvedAvailability =
            _buildDepositQueueAvailabilityPanel('Approved');
        if (approvedAvailability != null) {
          return approvedAvailability;
        }
        if (approved.isEmpty) {
          return const GteStatePanel(
            eyebrow: 'EMPTY',
            title: 'No approved payments',
            message:
                'Approved manual deposits will settle here with references and timestamps.',
            icon: Icons.receipt_long_outlined,
          );
        }
        return Column(
          children: approved
              .map(
                (GteAdminDeposit deposit) => _buildAdminPaymentQueueRow(
                  context,
                  deposit,
                  tab: _AdminPaymentQueueTab.approved,
                ),
              )
              .toList(growable: false),
        );
      case _AdminPaymentQueueTab.rejected:
        final Widget? rejectedAvailability =
            _buildDepositQueueAvailabilityPanel('Rejected');
        if (rejectedAvailability != null) {
          return rejectedAvailability;
        }
        if (rejected.isEmpty) {
          return const GteStatePanel(
            eyebrow: 'EMPTY',
            title: 'No rejected payments',
            message:
                'Rejected transfer proofs will appear here with reinstatement controls.',
            icon: Icons.block_outlined,
          );
        }
        return Column(
          children: rejected
              .map(
                (GteAdminDeposit deposit) => _buildAdminPaymentQueueRow(
                  context,
                  deposit,
                  tab: _AdminPaymentQueueTab.rejected,
                ),
              )
              .toList(growable: false),
        );
      case _AdminPaymentQueueTab.bids:
        final AdminTransferBidReviewFeed? feed = _transferBidReviewFeed;
        if (feed == null && _loading) {
          return const GteStatePanel(
            eyebrow: 'SYNCING',
            title: 'Bid review feed syncing',
            message:
                'GTEX is loading transfer windows and backend transfer bid state before exposing bid intelligence.',
            icon: Icons.sync_outlined,
            isLoading: true,
          );
        }
        if (feed == null && _transferBidReviewError != null) {
          return GteStatePanel(
            eyebrow: 'DEGRADED',
            title: 'Bid review feed unavailable',
            message:
                'Transfer bid state could not be loaded: $_transferBidReviewError',
            icon: Icons.cloud_off_outlined,
            accentColor: GteShellTheme.warning,
          );
        }
        if (feed == null || feed.bids.isEmpty) {
          return const GteStatePanel(
            eyebrow: 'CONFIRMED',
            title: 'No transfer bids under review',
            message:
                'The canonical payment queue has no transfer bids awaiting audit review.',
            icon: Icons.check_circle_outline,
            accentColor: GteShellTheme.positive,
          );
        }
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            _buildPaymentQueueBanner(
              context,
              icon: Icons.account_tree_outlined,
              message:
                  'Transfer bid controls are audit-only payment queue actions. Backend-provided approve, reject, and counter actions require admin notes and then refresh from canonical state.',
            ),
            const SizedBox(height: 12),
            ...feed.bids.map(
              (AdminTransferBid bid) => _buildAdminBidQueueRow(context, bid),
            ),
          ],
        );
    }
  }

  Widget _buildPaymentQueueBanner(
    BuildContext context, {
    required IconData icon,
    required String message,
  }) {
    final Color accent = GteShellTheme.accentAdmin;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.10),
        border: Border.all(color: accent.withValues(alpha: 0.22)),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(icon, color: accent),
          const SizedBox(width: 10),
          Expanded(child: Text(message)),
        ],
      ),
    );
  }

  Widget _buildAdminBidQueueRow(BuildContext context, AdminTransferBid bid) {
    final String actor =
        bid.buyingClubId?.trim().isNotEmpty == true
            ? bid.buyingClubId!
            : 'Buying club pending';
    final String updatedLabel =
        bid.updatedAt == null
            ? 'unknown update time'
            : gteFormatDateTime(bid.updatedAt);
    final String reservationLabel = _adminBidReservationLabel(bid);
    final IconData reservationIcon = _adminBidReservationIcon(bid);
    final bool busy = _bidBusyIds.contains(bid.id);
    final List<_TransferBidAdminAction> actions = _TransferBidAdminAction.values
        .where(
          (_TransferBidAdminAction action) => bid.supportsAction(action.apiKey),
        )
        .toList(growable: false);
    final List<String> auditTrail =
        bid.auditTrail.isNotEmpty
            ? bid.auditTrail
            : <String>[
              'Window ID: ${bid.windowId}',
              'Player ID: ${bid.playerId}',
              if (bid.walletReservationReference?.trim().isNotEmpty == true)
                'Reservation reference: ${bid.walletReservationReference}',
              if (bid.walletReservationStatus?.trim().isNotEmpty == true)
                'Wallet reservation: ${bid.walletReservationStatus}',
            ];

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: GteSurfacePanel(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              children: <Widget>[
                CircleAvatar(
                  radius: 19,
                  backgroundColor: GteShellTheme.accentAdmin.withValues(
                    alpha: 0.16,
                  ),
                  child: const Icon(Icons.bolt_outlined, size: 19),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Transfer bid ${bid.id}',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 2),
                      Text(
                        'Player ${bid.playerId} - updated $updatedLabel',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
                Chip(label: Text(_transferBidStatusLabel(bid.status))),
              ],
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: <Widget>[
                _buildSeverityChip(_transferBidSeverity(bid)),
                _buildEscalationChip(_transferBidEscalation(bid)),
                _PaymentQueueChip(
                  label: 'Actor',
                  value: actor,
                  icon: Icons.person_outline,
                ),
                _PaymentQueueChip(
                  label: 'Timestamp',
                  value: updatedLabel,
                  icon: Icons.schedule_outlined,
                ),
                _PaymentQueueChip(
                  label: 'Window',
                  value: bid.windowLabel,
                  icon: Icons.event_available_outlined,
                ),
                _PaymentQueueChip(
                  label: 'Bid amount',
                  value: gteFormatCompetitionAmount(bid.bidAmount, 'coin'),
                  icon: Icons.payments_outlined,
                ),
                _PaymentQueueChip(
                  label: 'Buyer',
                  value: actor,
                  icon: Icons.shield_outlined,
                ),
                _PaymentQueueChip(
                  label: 'Reservation',
                  value: reservationLabel,
                  icon: reservationIcon,
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              <String>[
                'Window ID: ${bid.windowId}',
                if (bid.sellingClubId?.trim().isNotEmpty == true)
                  'Selling club: ${bid.sellingClubId}',
                if (bid.buyingClubId?.trim().isNotEmpty == true)
                  'Buying club: ${bid.buyingClubId}',
                if (bid.wageOfferAmount != null)
                  'Wage offer: ${gteFormatCompetitionAmount(bid.wageOfferAmount!, 'coin')}',
                if (bid.sellOnClausePct != null)
                  'Sell-on clause: ${bid.sellOnClausePct!.toStringAsFixed(2)}%',
                if (bid.walletReservationStatus?.trim().isNotEmpty == true)
                  'Wallet reservation: ${bid.walletReservationStatus}',
                if (bid.walletReservedAmount != null)
                  'Reserved amount: ${gteFormatCompetitionAmount(bid.walletReservedAmount!, 'coin')}',
                if (bid.walletReservationReference?.trim().isNotEmpty == true)
                  'Reservation reference: ${bid.walletReservationReference}',
                if (bid.auditReference?.trim().isNotEmpty == true)
                  'Audit reference: ${bid.auditReference}',
                if (bid.actionState?.trim().isNotEmpty == true)
                  'Action state: ${_humanize(bid.actionState!)}',
                if (bid.businessActionState?.trim().isNotEmpty == true)
                  'Business action state: ${_humanize(bid.businessActionState!)}',
                if (bid.notes?.trim().isNotEmpty == true) 'Notes: ${bid.notes}',
              ].join('\n'),
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 12),
            Text('Audit trail', style: Theme.of(context).textTheme.labelLarge),
            const SizedBox(height: 6),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: auditTrail
                  .map(
                    (String item) => Chip(
                      label: Text(item),
                      visualDensity: VisualDensity.compact,
                    ),
                  )
                  .toList(growable: false),
            ),
            const SizedBox(height: 12),
            if (actions.isEmpty)
              GteStatePanel(
                eyebrow: 'BLOCKED',
                title: 'No bid audit actions exposed',
                message:
                    bid.blockedReason?.trim().isNotEmpty == true
                        ? bid.blockedReason!
                        : 'The backend did not expose approve, reject, or counter controls for this transfer bid.',
                icon: Icons.lock_outline,
                accentColor: GteShellTheme.warning,
              )
            else ...<Widget>[
              Text(
                'Audit-only bid actions',
                style: Theme.of(context).textTheme.labelLarge,
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: actions
                    .map((_TransferBidAdminAction action) {
                      final VoidCallback? onPressed =
                          busy ? null : () => _runBidAction(bid, action);
                      if (action.emphasized) {
                        return FilledButton.icon(
                          onPressed: onPressed,
                          icon: Icon(action.icon),
                          label: Text(busy ? 'Working...' : action.buttonLabel),
                        );
                      }
                      return OutlinedButton.icon(
                        onPressed: onPressed,
                        icon: Icon(action.icon),
                        label: Text(busy ? 'Working...' : action.buttonLabel),
                      );
                    })
                    .toList(growable: false),
              ),
            ],
          ],
        ),
      ),
    );
  }

  String _adminBidReservationLabel(AdminTransferBid bid) {
    if (!bid.hasWalletReservationPayload) {
      return 'Not exposed';
    }
    final String? status = bid.walletReservationStatus?.trim();
    final String? normalizedStatus = status?.toLowerCase();
    final String? amount =
        bid.walletReservedAmount == null
            ? null
            : gteFormatCompetitionAmount(bid.walletReservedAmount!, 'coin');
    if (normalizedStatus == 'reserved' || normalizedStatus == 'active') {
      return amount == null ? 'Reserved' : 'Reserved $amount';
    }
    if (normalizedStatus == 'released') {
      return amount == null ? 'Released' : 'Released $amount';
    }
    if (normalizedStatus == 'settled') {
      return amount == null ? 'Settled' : 'Settled $amount';
    }
    if (status?.isNotEmpty == true) {
      return amount == null ? status! : '$status $amount';
    }
    if (amount != null) {
      return 'Amount exposed $amount';
    }
    return 'Reference exposed';
  }

  IconData _adminBidReservationIcon(AdminTransferBid bid) {
    final String normalizedStatus =
        bid.walletReservationStatus?.trim().toLowerCase() ?? '';
    if (normalizedStatus == 'reserved' || normalizedStatus == 'active') {
      return Icons.lock_outline;
    }
    if (normalizedStatus == 'released') {
      return Icons.lock_open_outlined;
    }
    if (normalizedStatus == 'settled') {
      return Icons.verified_outlined;
    }
    return bid.hasWalletReservationPayload
        ? Icons.fact_check_outlined
        : Icons.lock_outline;
  }

  Widget _buildAdminPaymentQueueRow(
    BuildContext context,
    GteAdminDeposit deposit, {
    required _AdminPaymentQueueTab tab,
  }) {
    final bool busy = _depositBusyIds.contains(deposit.id);
    final String actor =
        deposit.userFullName?.trim().isNotEmpty == true
            ? deposit.userFullName!
            : deposit.userEmail;
    final String submittedLabel = gteFormatDateTime(
      deposit.submittedAt ?? deposit.createdAt,
    );
    final bool hasProof =
        deposit.transferReference?.trim().isNotEmpty == true ||
        deposit.senderBank?.trim().isNotEmpty == true;
    final bool isDisputed = deposit.status == GteDepositStatus.disputed;
    final List<String> auditTrail = <String>[
      'User ID: ${deposit.userId}',
      'Email: ${deposit.userEmail}',
      'Audit reference: deposit:${deposit.id}',
      ..._timeline(<MapEntry<String, DateTime?>>[
        MapEntry<String, DateTime?>('Created', deposit.createdAt),
        MapEntry<String, DateTime?>('Submitted', deposit.submittedAt),
        MapEntry<String, DateTime?>('Reviewed', deposit.reviewedAt),
        MapEntry<String, DateTime?>('Confirmed', deposit.confirmedAt),
        MapEntry<String, DateTime?>('Rejected', deposit.rejectedAt),
      ]),
    ];

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: GteSurfacePanel(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              children: <Widget>[
                CircleAvatar(
                  radius: 19,
                  backgroundColor: GteShellTheme.accentAdmin.withValues(
                    alpha: 0.16,
                  ),
                  child: Text(_initialsForActor(actor)),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        actor,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 2),
                      Text(
                        'Ref ${deposit.reference} - submitted $submittedLabel',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
                Chip(label: Text(_depositStatusLabel(deposit.status))),
              ],
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: <Widget>[
                _buildSeverityChip(_depositSeverity(deposit)),
                _buildEscalationChip(_depositEscalation(deposit)),
                _PaymentQueueChip(
                  label: 'Actor',
                  value: actor,
                  icon: Icons.person_outline,
                ),
                _PaymentQueueChip(
                  label: 'Timestamp',
                  value: submittedLabel,
                  icon: Icons.schedule_outlined,
                ),
                const _PaymentQueueChip(
                  label: 'Method',
                  value: 'Manual bank transfer',
                  icon: Icons.account_balance_outlined,
                ),
                _PaymentQueueChip(
                  label: 'Amount',
                  value:
                      '${gteFormatFiat(deposit.amountFiat, currency: deposit.currencyCode)} -> ${gteFormatCompetitionAmount(deposit.amountCoin, 'coin')}',
                  icon: Icons.payments_outlined,
                ),
                _PaymentQueueChip(
                  label: 'Proof',
                  value: hasProof ? 'Attached' : 'Pending',
                  icon:
                      hasProof
                          ? Icons.attach_file_outlined
                          : Icons.pending_actions_outlined,
                ),
              ],
            ),
            if (deposit.transferReference?.trim().isNotEmpty == true ||
                deposit.senderBank?.trim().isNotEmpty == true ||
                deposit.adminNotes?.trim().isNotEmpty == true) ...<Widget>[
              const SizedBox(height: 12),
              Text(
                <String>[
                  if (deposit.senderBank?.trim().isNotEmpty == true)
                    'Sender bank: ${deposit.senderBank}',
                  if (deposit.transferReference?.trim().isNotEmpty == true)
                    'Transfer reference: ${deposit.transferReference}',
                  if (deposit.adminNotes?.trim().isNotEmpty == true)
                    'Admin notes: ${deposit.adminNotes}',
                ].join('\n'),
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
            const SizedBox(height: 12),
            Text(
              'Audit reference: deposit:${deposit.id}',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 10),
            Text('Audit trail', style: Theme.of(context).textTheme.labelLarge),
            const SizedBox(height: 6),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: auditTrail
                  .map(
                    (String item) => Chip(
                      label: Text(item),
                      visualDensity: VisualDensity.compact,
                    ),
                  )
                  .toList(growable: false),
            ),
            const SizedBox(height: 10),
            Text('Notes', style: Theme.of(context).textTheme.labelLarge),
            const SizedBox(height: 4),
            Text(
              isDisputed
                  ? 'Disputed payment proof is blocked from direct treasury approval until the dispute lane resolves it.'
                  : deposit.adminNotes?.trim().isNotEmpty == true
                  ? deposit.adminNotes!
                  : 'No admin notes captured yet.',
            ),
            if (tab == _AdminPaymentQueueTab.pending && isDisputed) ...<Widget>[
              const SizedBox(height: 14),
              const GteStatePanel(
                eyebrow: 'BLOCKED',
                title: 'Dispute review required',
                message:
                    'This payment proof is disputed. Direct treasury approval and rejection controls stay locked until the dispute lane resolves the escalation.',
                icon: Icons.lock_outline,
                accentColor: GteShellTheme.warning,
              ),
            ] else if (tab == _AdminPaymentQueueTab.pending) ...<Widget>[
              const SizedBox(height: 14),
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: <Widget>[
                  FilledButton.tonalIcon(
                    onPressed:
                        busy
                            ? null
                            : () => _runDepositAction(
                              deposit,
                              _DepositAdminAction.review,
                            ),
                    icon: const Icon(Icons.visibility_outlined),
                    label: Text(busy ? 'Working...' : 'Mark reviewing'),
                  ),
                  FilledButton.icon(
                    onPressed:
                        busy
                            ? null
                            : () => _runDepositAction(
                              deposit,
                              _DepositAdminAction.confirm,
                            ),
                    icon: const Icon(Icons.check_circle_outline),
                    label: const Text('Approve'),
                  ),
                  OutlinedButton.icon(
                    onPressed:
                        busy
                            ? null
                            : () => _runDepositAction(
                              deposit,
                              _DepositAdminAction.reject,
                            ),
                    icon: const Icon(Icons.cancel_outlined),
                    label: const Text('Reject'),
                  ),
                ],
              ),
            ] else if (tab == _AdminPaymentQueueTab.rejected) ...<Widget>[
              const SizedBox(height: 14),
              OutlinedButton.icon(
                onPressed:
                    busy
                        ? null
                        : () => _runDepositAction(
                          deposit,
                          _DepositAdminAction.reinstate,
                        ),
                icon: const Icon(Icons.restore_outlined),
                label: Text(busy ? 'Working...' : 'Reinstate'),
              ),
            ],
          ],
        ),
      ),
    );
  }

  String _initialsForActor(String actor) {
    final List<String> parts = actor
        .trim()
        .split(RegExp(r'\s+'))
        .where((String part) => part.isNotEmpty)
        .toList(growable: false);
    if (parts.isEmpty) {
      return 'GT';
    }
    return parts.take(2).map((String part) => part[0].toUpperCase()).join();
  }

  // ignore: unused_element
  Widget _buildLegacyDepositQueuePanel(BuildContext context) {
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

class _PaymentQueueChip extends StatelessWidget {
  const _PaymentQueueChip({
    required this.label,
    required this.value,
    required this.icon,
  });

  final String label;
  final String value;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minWidth: 160),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFF2A3A56)),
        color: Colors.white.withValues(alpha: 0.035),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(icon, size: 18, color: GteShellTheme.accentAdmin),
          const SizedBox(width: 8),
          Flexible(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(label, style: Theme.of(context).textTheme.bodySmall),
                const SizedBox(height: 2),
                Text(value, style: Theme.of(context).textTheme.labelLarge),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

enum _AdminPaymentQueueTab { pending, approved, rejected, bids }

enum _AdminCommandSurfaceState { syncing, empty, blocked, degraded, error }

enum _AdminCommandSeverity { low, medium, high, critical }

enum _AdminCommandEscalation { none, watching, escalated, locked }

enum _TransferBidAdminAction {
  approve(
    apiKey: 'approve',
    buttonLabel: 'Audit approve',
    dialogTitle: 'Audit approve transfer bid',
    successMessage: 'Transfer bid approval audit recorded.',
    icon: Icons.check_circle_outline,
    emphasized: true,
  ),
  reject(
    apiKey: 'reject',
    buttonLabel: 'Audit reject',
    dialogTitle: 'Audit reject transfer bid',
    successMessage: 'Transfer bid rejection audit recorded.',
    icon: Icons.block_outlined,
  ),
  counter(
    apiKey: 'counter',
    buttonLabel: 'Audit counter',
    dialogTitle: 'Audit counter transfer bid',
    successMessage: 'Transfer bid counter audit recorded.',
    icon: Icons.swap_horiz_outlined,
  );

  const _TransferBidAdminAction({
    required this.apiKey,
    required this.buttonLabel,
    required this.dialogTitle,
    required this.successMessage,
    required this.icon,
    this.emphasized = false,
  });

  final String apiKey;
  final String buttonLabel;
  final String dialogTitle;
  final String successMessage;
  final IconData icon;
  final bool emphasized;
}

class _AdminCommandQueueSurface {
  const _AdminCommandQueueSurface({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.state,
    required this.stateMessage,
    required this.rows,
    this.route,
    this.routeLabel,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final _AdminCommandSurfaceState state;
  final String stateMessage;
  final List<_AdminCommandQueueRow> rows;
  final GteAppRouteData? route;
  final String? routeLabel;
}

class _AdminCommandQueueRow {
  const _AdminCommandQueueRow({
    required this.id,
    required this.surface,
    required this.reference,
    required this.title,
    required this.actor,
    required this.timestamp,
    required this.severity,
    required this.escalation,
    required this.status,
    required this.notes,
    required this.auditTrail,
    required this.isLocked,
    required this.actions,
  });

  final String id;
  final String surface;
  final String reference;
  final String title;
  final String actor;
  final DateTime? timestamp;
  final _AdminCommandSeverity severity;
  final _AdminCommandEscalation escalation;
  final String status;
  final String notes;
  final List<String> auditTrail;
  final bool isLocked;
  final List<_AdminCommandAction> actions;

  String get searchText => <String>[
    id,
    surface,
    reference,
    title,
    actor,
    status,
    severity.name,
    escalation.name,
    notes,
    ...auditTrail,
  ].join(' ');
}

class _AdminCommandAction {
  const _AdminCommandAction({
    required this.label,
    required this.icon,
    this.onPressed,
    this.emphasized = false,
  });

  final String label;
  final IconData icon;
  final VoidCallback? onPressed;
  final bool emphasized;
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
  ),
  reinstate(
    buttonLabel: 'Reinstate',
    dialogTitle: 'Reinstate rejected deposit',
    successMessage: 'Deposit reinstated for review.',
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
