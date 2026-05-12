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
  static const List<String> _automaticProviders = <String>[
    'paystack',
    'korapay',
  ];

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
  String _automaticProvider = 'paystack';
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

  void _simulateMockFailure() {
    setState(() {
      _verification = null;
      _error =
          'Test payment was marked as failed locally. No wallet credit was applied.';
    });
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
      default:
        return 'Paystack';
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
    return status == 'ready' || status == 'mock';
  }

  String _providerRestrictionMessage(String provider) {
    final String label = _providerLabel(provider);
    switch (_providerStatus(provider)) {
      case 'blocked':
        return 'Instant deposit is currently disabled for this wallet. Use bank transfer below.';
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
        return '$label is available in test payment mode for this environment.';
      case 'blocked':
        return 'Instant deposit is currently routed away from $label. Use bank transfer below.';
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
          'Add capital through instant checkout or manual bank transfer while preserving GTEX compliance controls.',
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
                    'Choose a deposit method',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Instant checkout can buy GTEX Coin or Fan Coin. Manual bank transfer credits GTEX Coin after admin review.',
                    style: Theme.of(context).textTheme.bodyMedium,
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
                        ? 'Automatic checkout supports Paystack and KoraPay deposits.'
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
                        child: Text('GTEX Coin'),
                      ),
                      DropdownMenuItem<GteLedgerUnit>(
                        value: GteLedgerUnit.credit,
                        child: Text('Fan Coin'),
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
                  const SizedBox(height: 16),
                  TextField(
                    controller: _automaticAmountController,
                    keyboardType: TextInputType.numberWithOptions(
                      decimal: _automaticProvider != 'korapay',
                    ),
                    enabled: !_isSubmitting && session == null,
                    decoration: InputDecoration(
                      labelText: 'Amount',
                      helperText:
                          _automaticProvider == 'korapay'
                              ? 'KoraPay currently accepts whole-number NGN amounts.'
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
                    Text('Reference: ${session.reference}'),
                    Text(
                      'Amount: ${gteFormatCompetitionAmount(session.amount, session.currency)}',
                    ),
                    Text('Provider: ${_providerLabel(session.provider)}'),
                    Text('Status: ${_titleCase(session.status)}'),
                    if (session.mockMode)
                      Padding(
                        padding: EdgeInsets.only(top: 10),
                        child: Text(
                          'Test payment mode is active because no live ${_providerLabel(session.provider)} key is configured for this environment.',
                        ),
                      ),
                    const SizedBox(height: 14),
                    Wrap(
                      spacing: 10,
                      runSpacing: 10,
                      children: <Widget>[
                        if (session.mockMode)
                          FilledButton.tonalIcon(
                            onPressed: _isVerifying ? null : _verifyTopUp,
                            icon: const Icon(Icons.check_circle_outline),
                            label: const Text('Mark test payment successful'),
                          )
                        else
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
                        if (session.mockMode)
                          OutlinedButton.icon(
                            onPressed:
                                _isSubmitting || _isVerifying
                                    ? null
                                    : _simulateMockFailure,
                            icon: const Icon(Icons.cancel_outlined),
                            label: const Text('Mark test payment failed'),
                          ),
                        OutlinedButton.icon(
                          onPressed: _isVerifying ? null : _verifyTopUp,
                          icon: const Icon(Icons.verified_outlined),
                          label: Text(
                            _isVerifying
                                ? 'Verifying...'
                                : session.mockMode
                                ? 'Verify test payment'
                                : 'Verify payment',
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
                    'Create a manual bank transfer request to receive admin payment details and the locked reference that credits GTEX Coin after review.',
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: _manualAmountController,
                    keyboardType: const TextInputType.numberWithOptions(
                      decimal: true,
                    ),
                    enabled: !_isCreatingManualDeposit,
                    decoration: const InputDecoration(
                      labelText: 'Amount',
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
                    Text('Reference: ${activeDeposit.reference}'),
                    Text(
                      'Amount: ${gteFormatFiat(activeDeposit.amountFiat, currency: activeDeposit.currencyCode)}',
                    ),
                    Text(
                      'GTEX Coin credited on approval: ${gteFormatCredits(activeDeposit.amountCoin)}',
                    ),
                    Text('Status: ${_titleCase(activeDeposit.status.name)}'),
                    const SizedBox(height: 10),
                    Text('Bank: ${activeDeposit.bankName}'),
                    Text('Account number: ${activeDeposit.bankAccountNumber}'),
                    Text('Account name: ${activeDeposit.bankAccountName}'),
                    if (activeDeposit.expiresAt != null)
                      Text(
                        'Expires: ${gteFormatDateTime(activeDeposit.expiresAt)}',
                      ),
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
