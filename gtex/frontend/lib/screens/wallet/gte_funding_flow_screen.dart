import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/app_feedback.dart';
import '../../data/gte_models.dart';
import '../../providers/gte_exchange_controller.dart';
import '../../widgets/gte_formatters.dart';
import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';
import 'gte_policy_compliance_center_screen.dart';
import 'gte_wallet_flow_scaffold.dart';

class GteFundWalletScreen extends StatefulWidget {
  const GteFundWalletScreen({super.key, required this.controller});

  final GteExchangeController controller;

  @override
  State<GteFundWalletScreen> createState() => _GteFundWalletScreenState();
}

class _GteFundWalletScreenState extends State<GteFundWalletScreen> {
  static const List<String> _automaticProviders = <String>['korapay'];

  final TextEditingController _automaticAmountController =
      TextEditingController();
  final TextEditingController _manualAmountController = TextEditingController();
  final TextEditingController _payerNameController = TextEditingController();
  final TextEditingController _senderBankController = TextEditingController();
  final TextEditingController _transferReferenceController =
      TextEditingController();

  bool _isSubmitting = false;
  bool _isVerifying = false;
  bool _isLoadingDeposits = false;
  bool _isCreatingManualDeposit = false;
  bool _isSubmittingManualDeposit = false;
  bool _awaitingInitialComplianceCheck = false;
  String _automaticProvider = 'korapay';
  GteLedgerUnit _automaticUnit = GteLedgerUnit.coin;
  String? _error;
  GteWalletTopUpSession? _session;
  GteWalletTopUpVerificationResult? _verification;
  GteWalletOverview? _walletOverview;
  List<GteDepositRequest> _depositRequests = <GteDepositRequest>[];
  GteDepositRequest? _manualDeposit;
  bool _isLoadingWalletOverview = false;

  @override
  void initState() {
    super.initState();
    _awaitingInitialComplianceCheck =
        widget.controller.isAuthenticated &&
        widget.controller.complianceStatus == null;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !widget.controller.isAuthenticated) {
        return;
      }
      _refreshFundingContext();
      _refreshDepositRequests();
    });
  }

  @override
  void dispose() {
    _automaticAmountController.dispose();
    _manualAmountController.dispose();
    _payerNameController.dispose();
    _senderBankController.dispose();
    _transferReferenceController.dispose();
    super.dispose();
  }

  GteDepositRequest? get _activeManualDeposit {
    final List<GteDepositRequest> ranked = <GteDepositRequest>[
      if (_manualDeposit != null) _manualDeposit!,
      ..._depositRequests,
    ]..sort((GteDepositRequest left, GteDepositRequest right) {
      final DateTime leftStamp =
          left.createdAt ?? DateTime.fromMillisecondsSinceEpoch(0, isUtc: true);
      final DateTime rightStamp =
          right.createdAt ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true);
      return rightStamp.compareTo(leftStamp);
    });
    for (final GteDepositRequest deposit in ranked) {
      if (deposit.status == GteDepositStatus.awaitingPayment ||
          deposit.status == GteDepositStatus.paymentSubmitted ||
          deposit.status == GteDepositStatus.underReview) {
        return deposit;
      }
    }
    return ranked.isEmpty ? null : ranked.first;
  }

  Future<void> _launchPaymentLink(String link) async {
    final Uri uri = Uri.parse(link);
    final bool launched = await launchUrl(
      uri,
      mode: LaunchMode.externalApplication,
    );
    if (!launched && mounted) {
      setState(() {
        _error = 'Unable to open the payment link on this device.';
      });
    }
  }

  Future<void> _refreshDepositRequests() async {
    setState(() {
      _isLoadingDeposits = true;
    });
    try {
      final List<GteDepositRequest> deposits =
          await widget.controller.api.listDepositRequests();
      if (!mounted) {
        return;
      }
      setState(() {
        _depositRequests = deposits;
        _manualDeposit = _resolveManualDeposit(deposits);
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
          _isLoadingDeposits = false;
        });
      }
    }
  }

  Future<void> _refreshFundingContext() async {
    setState(() {
      _isLoadingWalletOverview = true;
    });
    try {
      final Future<void> complianceTask = widget.controller.refreshCompliance();
      final GteWalletOverview overview =
          await widget.controller.api.fetchWalletOverview();
      await complianceTask;
      if (!mounted) {
        return;
      }
      setState(() {
        _walletOverview = overview;
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
          _isLoadingWalletOverview = false;
          _awaitingInitialComplianceCheck = false;
        });
      }
    }
  }

  Future<void> _refreshFundingSurface() async {
    await Future.wait<void>(<Future<void>>[
      _refreshFundingContext(),
      _refreshDepositRequests(),
    ]);
  }

  GteDepositRequest? _resolveManualDeposit(List<GteDepositRequest> deposits) {
    final List<GteDepositRequest> sorted = List<GteDepositRequest>.from(
      deposits,
    )..sort((GteDepositRequest left, GteDepositRequest right) {
      final DateTime leftStamp =
          left.createdAt ?? DateTime.fromMillisecondsSinceEpoch(0, isUtc: true);
      final DateTime rightStamp =
          right.createdAt ??
          DateTime.fromMillisecondsSinceEpoch(0, isUtc: true);
      return rightStamp.compareTo(leftStamp);
    });
    for (final GteDepositRequest deposit in sorted) {
      if (deposit.status == GteDepositStatus.awaitingPayment ||
          deposit.status == GteDepositStatus.paymentSubmitted ||
          deposit.status == GteDepositStatus.underReview) {
        return deposit;
      }
    }
    return sorted.isEmpty ? null : sorted.first;
  }

  Future<void> _initiateTopUp() async {
    final double? amount = double.tryParse(
      _automaticAmountController.text.trim(),
    );
    if (amount == null || amount <= 0) {
      setState(() {
        _error = 'Enter a valid amount to continue.';
      });
      return;
    }
    if (!_providerSupportsCheckout(_automaticProvider)) {
      setState(() {
        _error = _providerRestrictionMessage(_automaticProvider);
      });
      return;
    }
    if (_automaticProvider == 'korapay' &&
        amount != amount.truncateToDouble()) {
      setState(() {
        _error =
            'KoraPay currently accepts whole-number NGN amounts. Enter a whole number like 5000.';
      });
      return;
    }
    setState(() {
      _error = null;
      _isSubmitting = true;
    });
    try {
      final GteWalletTopUpSession session = await widget.controller.api
          .initiateWalletTopUp(
            GteWalletTopUpInitiateRequest(
              amount: amount,
              provider: _automaticProvider,
              unit: _automaticUnit,
            ),
          );
      if (!mounted) {
        return;
      }
      if (session.mockMode) {
        setState(() {
          _session = null;
          _verification = null;
          _error =
              'Live payment provider returned a mock session. Strict-live funding is blocked until KoraPay or manual bank transfer is configured.';
        });
        return;
      }
      setState(() {
        _session = session;
        _verification = null;
      });
      if (!session.mockMode && session.paymentLink.trim().isNotEmpty) {
        await _launchPaymentLink(session.paymentLink);
      }
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
          _isSubmitting = false;
        });
      }
    }
  }

  Future<void> _verifyTopUp() async {
    final GteWalletTopUpSession? session = _session;
    if (session == null) {
      return;
    }
    setState(() {
      _error = null;
      _isVerifying = true;
    });
    try {
      final GteWalletTopUpVerificationResult result = await widget
          .controller
          .api
          .verifyWalletTopUp(session.reference);
      await Future.wait<void>(<Future<void>>[
        widget.controller.loadPortfolio(),
        _refreshFundingSurface(),
      ]);
      if (!mounted) {
        return;
      }
      setState(() {
        _verification = result;
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
          _isVerifying = false;
        });
      }
    }
  }

  Future<void> _createManualDeposit() async {
    final double? amount = double.tryParse(_manualAmountController.text.trim());
    if (amount == null || amount <= 0) {
      setState(() {
        _error = 'Enter a valid amount for the bank transfer request.';
      });
      return;
    }
    setState(() {
      _error = null;
      _isCreatingManualDeposit = true;
    });
    try {
      final GteDepositRequest deposit = await widget.controller.api
          .createDepositRequest(
            GteDepositCreateRequest(amount: amount, inputUnit: 'fiat'),
          );
      if (!mounted) {
        return;
      }
      setState(() {
        _manualDeposit = deposit;
      });
      await Future.wait<void>(<Future<void>>[
        _refreshDepositRequests(),
        _refreshFundingContext(),
      ]);
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
          _isCreatingManualDeposit = false;
        });
      }
    }
  }

  Future<void> _submitManualDeposit() async {
    final GteDepositRequest? deposit = _activeManualDeposit;
    if (deposit == null) {
      return;
    }
    setState(() {
      _error = null;
      _isSubmittingManualDeposit = true;
    });
    try {
      final GteDepositRequest updated = await widget.controller.api
          .submitDepositRequest(
            deposit.id,
            GteDepositSubmitRequest(
              payerName:
                  _payerNameController.text.trim().isEmpty
                      ? null
                      : _payerNameController.text.trim(),
              senderBank:
                  _senderBankController.text.trim().isEmpty
                      ? null
                      : _senderBankController.text.trim(),
              transferReference:
                  _transferReferenceController.text.trim().isEmpty
                      ? null
                      : _transferReferenceController.text.trim(),
            ),
          );
      if (!mounted) {
        return;
      }
      setState(() {
        _manualDeposit = updated;
      });
      _payerNameController.clear();
      _senderBankController.clear();
      _transferReferenceController.clear();
      await Future.wait<void>(<Future<void>>[
        _refreshDepositRequests(),
        _refreshFundingContext(),
      ]);
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
          _isSubmittingManualDeposit = false;
        });
      }
    }
  }

  void _resetAutomaticFlow() {
    setState(() {
      _automaticAmountController.clear();
      _error = null;
      _session = null;
      _verification = null;
    });
  }

  String _providerLabel(String provider) {
    switch (provider.trim().toLowerCase()) {
      case 'korapay':
        return 'KoraPay';
      case 'paystack':
        return 'Unavailable payment rail';
      default:
        return provider;
    }
  }

  String _providerStatus(String provider) {
    return _walletOverview?.paymentProviderStatus[provider
            .trim()
            .toLowerCase()] ??
        'unknown';
  }

  bool _providerSupportsCheckout(String provider) {
    final String status = _providerStatus(provider);
    return status == 'ready';
  }

  String _providerRestrictionMessage(String provider) {
    final String label = _providerLabel(provider);
    switch (_providerStatus(provider)) {
      case 'blocked':
        return '$label is not available for live wallet deposits. Use KoraPay or bank transfer below.';
      case 'unavailable':
        return '$label is unavailable until live gateway credentials are configured.';
      default:
        return '$label checkout is not ready yet. Refresh the wallet state and try again.';
    }
  }

  String _providerStatusSummary(String provider) {
    final String label = _providerLabel(provider);
    switch (_providerStatus(provider)) {
      case 'ready':
        return '$label checkout is ready for deposits.';
      case 'mock':
        return '$label is not enabled for live production deposits.';
      case 'blocked':
        return '$label is blocked for production. Use KoraPay or bank transfer below.';
      case 'unavailable':
        return '$label is unavailable until live gateway credentials are configured.';
      default:
        return 'Loading current $label deposit status...';
    }
  }

  @override
  Widget build(BuildContext context) {
    final GteWalletTopUpSession? session = _session;
    final GteWalletTopUpVerificationResult? verification = _verification;
    final GteWalletOverview? walletOverview = _walletOverview;
    final GteComplianceStatus? compliance = widget.controller.complianceStatus;
    final GteDepositRequest? activeDeposit = _activeManualDeposit;
    final bool blocked = compliance != null && !compliance.canDeposit;
    final String blockedMessage =
        compliance == null
            ? 'Wallet deposit is currently unavailable.'
            : compliance.requiredPolicyAcceptancesMissing > 0
            ? compliance.requiredPolicyAcceptancesMissing == 1
                ? 'Complete 1 policy item to unlock deposits.'
                : 'Complete ${compliance.requiredPolicyAcceptancesMissing} policy items to unlock deposits.'
            : walletOverview?.policyBlockReason ??
                'Deposits are currently restricted for this club wallet.';
    final bool instantFundingReady =
        !_isLoadingWalletOverview &&
        !blocked &&
        _providerSupportsCheckout(_automaticProvider) &&
        session == null;
    return GteWalletFlowScaffold(
      title: 'Deposit',
      subtitle:
          'Add live wallet value through KoraPay checkout or manual bank transfer review.',
      icon: Icons.add_card_outlined,
      statusLabel: 'FUND WALLET',
      child: RefreshIndicator(
        onRefresh: _refreshFundingSurface,
        child: ListView(
          padding: const EdgeInsets.all(20),
          physics: const AlwaysScrollableScrollPhysics(),
          children: <Widget>[
            if (blocked) ...<Widget>[
              GteSurfacePanel(
                accentColor: GteShellTheme.accentWarm,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Compliance action required',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 8),
                    Text(blockedMessage),
                    const SizedBox(height: 12),
                    FilledButton.tonalIcon(
                      onPressed: () async {
                        await Navigator.of(context).push(
                          MaterialPageRoute<void>(
                            builder:
                                (_) => GtePolicyComplianceCenterScreen(
                                  controller: widget.controller,
                                ),
                          ),
                        );
                        await _refreshFundingContext();
                      },
                      icon: const Icon(Icons.gavel_outlined),
                      label: const Text('Open compliance center'),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
            ],
            GteSurfacePanel(
              emphasized: true,
              accentColor: GteShellTheme.accentCapital,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'Choose live funding rail',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'GTC and FNC stay separate. KoraPay follows the selected live wallet unit; manual bank transfer credits GTC only after admin review.',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 10,
                    runSpacing: 10,
                    children: <Widget>[
                      _FundingRailChip(
                        label: 'KoraPay',
                        value: _providerStatusSummary('korapay'),
                        icon: Icons.open_in_new_outlined,
                        accent: GteShellTheme.accentCapital,
                      ),
                      _FundingRailChip(
                        label: 'Manual bank transfer',
                        value: 'GTC credited after review',
                        icon: Icons.account_balance_outlined,
                        accent: GteShellTheme.accentWarm,
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
            GteSurfacePanel(
              accentColor: GteShellTheme.accentCapital,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'Instant payment',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    walletOverview == null
                        ? 'Loading the live deposit rail and gateway availability.'
                        : walletOverview.depositMode == 'gateway' ||
                            walletOverview.depositMode == 'hybrid'
                        ? 'Automatic checkout uses KoraPay deposits. Manual bank transfer remains available below.'
                        : 'Instant checkout is currently unavailable because deposits are routed through manual bank transfer review.',
                  ),
                  if (walletOverview != null) ...<Widget>[
                    const SizedBox(height: 8),
                    Text(
                      _providerStatusSummary(_automaticProvider),
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                  const SizedBox(height: 16),
                  DropdownButtonFormField<String>(
                    value: _automaticProvider,
                    decoration: const InputDecoration(
                      labelText: 'Provider',
                      prefixIcon: Icon(Icons.account_balance_wallet_outlined),
                    ),
                    items: _automaticProviders
                        .map(
                          (String provider) => DropdownMenuItem<String>(
                            value: provider,
                            child: Text(_providerLabel(provider)),
                          ),
                        )
                        .toList(growable: false),
                    onChanged:
                        _isSubmitting || session != null
                            ? null
                            : (String? value) {
                              if (value == null) {
                                return;
                              }
                              setState(() {
                                _automaticProvider = value;
                              });
                            },
                  ),
                  const SizedBox(height: 16),
                  DropdownButtonFormField<GteLedgerUnit>(
                    value: _automaticUnit,
                    decoration: const InputDecoration(
                      labelText: 'Wallet',
                      prefixIcon: Icon(Icons.sports_soccer_outlined),
                    ),
                    items: const <DropdownMenuItem<GteLedgerUnit>>[
                      DropdownMenuItem<GteLedgerUnit>(
                        value: GteLedgerUnit.coin,
                        child: Text('GTEX Coin (GTC)'),
                      ),
                      DropdownMenuItem<GteLedgerUnit>(
                        value: GteLedgerUnit.credit,
                        child: Text('Fan Coin (FNC)'),
                      ),
                    ],
                    onChanged:
                        _isSubmitting || session != null
                            ? null
                            : (GteLedgerUnit? value) {
                              if (value == null) {
                                return;
                              }
                              setState(() {
                                _automaticUnit = value;
                              });
                            },
                  ),
                  const SizedBox(height: 10),
                  Text(
                    _fundingUnitDescription(_automaticUnit),
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: _automaticAmountController,
                    keyboardType: TextInputType.numberWithOptions(
                      decimal: _automaticProvider != 'korapay',
                    ),
                    enabled: !_isSubmitting && session == null,
                    decoration: InputDecoration(
                      labelText:
                          'Amount (${gteLedgerUnitCode(_automaticUnit)})',
                      helperText:
                          _automaticProvider == 'korapay'
                              ? 'KoraPay sessions are confirmed by the live backend before any balance changes.'
                              : 'Enter the deposit amount to route through the selected gateway.',
                      prefixIcon: const Icon(Icons.payments_outlined),
                    ),
                  ),
                  const SizedBox(height: 16),
                  FilledButton.icon(
                    onPressed:
                        _isSubmitting || !instantFundingReady
                            ? null
                            : _initiateTopUp,
                    icon: const Icon(Icons.open_in_new_outlined),
                    label: Text(
                      _isSubmitting
                          ? 'Creating deposit session...'
                          : 'Continue to ${_providerLabel(_automaticProvider)}',
                    ),
                  ),
                ],
              ),
            ),
            if (session != null) ...<Widget>[
              const SizedBox(height: 18),
              GteSurfacePanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Instant payment session',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 10),
                    SelectableText('Reference: ${session.reference}'),
                    Text(
                      'Amount: ${gteFormatCompetitionAmount(session.amount, session.currency)}',
                    ),
                    Text('Provider: ${_providerLabel(session.provider)}'),
                    Text('Status: ${_titleCase(session.status)}'),
                    const SizedBox(height: 8),
                    const Text(
                      'GTEX credits this wallet only after the backend confirms the gateway callback or verification result.',
                    ),
                    const SizedBox(height: 14),
                    Wrap(
                      spacing: 10,
                      runSpacing: 10,
                      children: <Widget>[
                        FilledButton.tonalIcon(
                          onPressed:
                              _isVerifying
                                  ? null
                                  : () =>
                                      _launchPaymentLink(session.paymentLink),
                          icon: const Icon(Icons.open_in_browser_outlined),
                          label: Text(
                            'Open ${_providerLabel(session.provider)}',
                          ),
                        ),
                        OutlinedButton.icon(
                          onPressed: _isVerifying ? null : _verifyTopUp,
                          icon: const Icon(Icons.verified_outlined),
                          label: Text(
                            _isVerifying ? 'Verifying...' : 'Verify payment',
                          ),
                        ),
                        OutlinedButton(
                          onPressed:
                              _isSubmitting || _isVerifying
                                  ? null
                                  : _resetAutomaticFlow,
                          child: const Text('Start again'),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
            if (verification != null) ...<Widget>[
              const SizedBox(height: 18),
              GteSurfacePanel(
                accentColor: GteShellTheme.positive,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Wallet updated',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Wallet balance: ${gteFormatCompetitionAmount(verification.wallet.balance, verification.wallet.currency)}',
                    ),
                    Text(
                      'Transaction status: ${_titleCase(verification.transaction.status)}',
                    ),
                  ],
                ),
              ),
            ],
            const SizedBox(height: 18),
            GteSurfacePanel(
              accentColor: GteShellTheme.accentWarm,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'Bank transfer',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Create a manual bank transfer request to receive real treasury account details and a locked reference. Transfer exactly the shown NGN amount and submit the bank reference for review.',
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: _manualAmountController,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    enabled: !_isCreatingManualDeposit,
                    decoration: const InputDecoration(
                      labelText: 'GTC amount requested',
                      helperText:
                          'Manual bank transfer credits GTC after admin review.',
                      prefixIcon: Icon(Icons.account_balance_outlined),
                    ),
                  ),
                  const SizedBox(height: 16),
                  FilledButton.icon(
                    onPressed:
                        _isCreatingManualDeposit ? null : _createManualDeposit,
                    icon: const Icon(Icons.receipt_long_outlined),
                    label: Text(
                      _isCreatingManualDeposit
                          ? 'Creating request...'
                          : 'Create bank transfer request',
                    ),
                  ),
                ],
              ),
            ),
            if (activeDeposit != null) ...<Widget>[
              const SizedBox(height: 18),
              GteSurfacePanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Active bank transfer request',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 10),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(16),
                        color: GteShellTheme.accentWarm.withValues(alpha: 0.1),
                        border: Border.all(
                          color: GteShellTheme.accentWarm.withValues(
                            alpha: 0.22,
                          ),
                        ),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(
                            'Reference code',
                            style: Theme.of(context).textTheme.labelLarge,
                          ),
                          const SizedBox(height: 6),
                          SelectableText(
                            activeDeposit.reference,
                            style: Theme.of(context).textTheme.titleLarge,
                          ),
                          const SizedBox(height: 8),
                          Text(
                            'Transfer exactly ${gteFormatFiat(activeDeposit.amountFiat, currency: activeDeposit.currencyCode)} using this reference.',
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 10),
                    Text(
                      'Amount: ${gteFormatFiat(activeDeposit.amountFiat, currency: activeDeposit.currencyCode)}',
                    ),
                    Text(
                      'GTC on approval: ${gteFormatGtc(activeDeposit.amountCoin)}',
                    ),
                    Text('Status: ${_titleCase(activeDeposit.status.name)}'),
                    const SizedBox(height: 8),
                    Text(_manualDepositReviewMessage(activeDeposit)),
                    const SizedBox(height: 10),
                    Text('Bank: ${activeDeposit.bankName}'),
                    Text('Account number: ${activeDeposit.bankAccountNumber}'),
                    Text('Account name: ${activeDeposit.bankAccountName}'),
                    if (activeDeposit.expiresAt != null)
                      Text(
                        'Expires: ${gteFormatDateTime(activeDeposit.expiresAt)}',
                      ),
                    if (activeDeposit.proofAttachmentId != null) ...<Widget>[
                      const SizedBox(height: 8),
                      Text(
                        'Proof attached: ${activeDeposit.proofAttachmentId}',
                      ),
                    ],
                    if (activeDeposit.adminNotes != null) ...<Widget>[
                      const SizedBox(height: 8),
                      Text('Review note: ${activeDeposit.adminNotes}'),
                    ],
                    if (activeDeposit.status ==
                        GteDepositStatus.awaitingPayment) ...<Widget>[
                      const SizedBox(height: 16),
                      TextField(
                        controller: _payerNameController,
                        decoration: const InputDecoration(
                          labelText: 'Payer name',
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _senderBankController,
                        decoration: const InputDecoration(
                          labelText: 'Sender bank',
                        ),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: _transferReferenceController,
                        decoration: const InputDecoration(
                          labelText: 'Transfer reference',
                        ),
                      ),
                      const SizedBox(height: 16),
                      FilledButton.icon(
                        onPressed:
                            _isSubmittingManualDeposit
                                ? null
                                : _submitManualDeposit,
                        icon: const Icon(Icons.task_alt_outlined),
                        label: Text(
                          _isSubmittingManualDeposit
                              ? 'Submitting...'
                              : 'Submit payment details',
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
            if (_isLoadingDeposits) ...<Widget>[
              const SizedBox(height: 18),
              const Center(child: CircularProgressIndicator()),
            ] else if (_depositRequests.isNotEmpty) ...<Widget>[
              const SizedBox(height: 18),
              GteSurfacePanel(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Recent bank transfer requests',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 12),
                    ..._depositRequests
                        .take(3)
                        .map(
                          (GteDepositRequest deposit) => Padding(
                            padding: const EdgeInsets.only(bottom: 10),
                            child: Text(
                              '${deposit.reference} - ${_titleCase(deposit.status.name)} - ${gteFormatFiat(deposit.amountFiat, currency: deposit.currencyCode)}',
                            ),
                          ),
                        ),
                  ],
                ),
              ),
            ],
            if (_error != null) ...<Widget>[
              const SizedBox(height: 18),
              GteStatePanel(
                title: 'Deposit issue',
                message: _error!,
                icon: Icons.warning_amber_rounded,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _FundingRailChip extends StatelessWidget {
  const _FundingRailChip({
    required this.label,
    required this.value,
    required this.icon,
    required this.accent,
  });

  final String label;
  final String value;
  final IconData icon;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 240,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        color: accent.withValues(alpha: 0.08),
        border: Border.all(color: accent.withValues(alpha: 0.18)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(icon, color: accent),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(label, style: Theme.of(context).textTheme.titleSmall),
                const SizedBox(height: 4),
                Text(value, style: Theme.of(context).textTheme.bodySmall),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

String _fundingUnitDescription(GteLedgerUnit unit) {
  switch (unit) {
    case GteLedgerUnit.coin:
      return 'GTC is the capital coin for transfers, trader settlement, player purchases, and withdrawals.';
    case GteLedgerUnit.credit:
      return 'FNC is the fan-economy coin for gifts, reactions, community entries, and activity rewards.';
    case GteLedgerUnit.unknown:
      return 'Select a live wallet unit before creating a payment session.';
  }
}

String _manualDepositReviewMessage(GteDepositRequest deposit) {
  switch (deposit.status) {
    case GteDepositStatus.awaitingPayment:
      return 'Awaiting your bank transfer details. Balance will not change until review is complete.';
    case GteDepositStatus.paymentSubmitted:
      return 'Payment details submitted. GTEX is waiting for admin review.';
    case GteDepositStatus.underReview:
      return 'Under review by GTEX treasury. Review state comes from the live backend.';
    case GteDepositStatus.confirmed:
      return 'Approved. GTC should be reflected in the wallet ledger.';
    case GteDepositStatus.rejected:
      return deposit.adminNotes ??
          'Rejected by admin review. You can create a new request if needed.';
    case GteDepositStatus.expired:
      return 'Expired. Create a fresh request to receive a valid reference.';
    case GteDepositStatus.disputed:
      return 'Disputed. Contact support with the bank transfer proof and reference.';
  }
}

String _titleCase(String value) {
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
