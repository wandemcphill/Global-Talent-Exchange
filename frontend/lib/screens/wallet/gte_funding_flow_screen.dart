import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../../core/app_feedback.dart';
import '../../data/gte_models.dart';
import '../../providers/gte_exchange_controller.dart';
import '../../widgets/gte_formatters.dart';
import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';
import 'gte_policy_compliance_center_screen.dart';

class GteFundWalletScreen extends StatefulWidget {
  const GteFundWalletScreen({
    super.key,
    required this.controller,
  });

  final GteExchangeController controller;

  @override
  State<GteFundWalletScreen> createState() => _GteFundWalletScreenState();
}

class _GteFundWalletScreenState extends State<GteFundWalletScreen> {
  final TextEditingController _amountController = TextEditingController();
  bool _inputFiat = true;
  bool _isSubmitting = false;
  bool _awaitingInitialComplianceCheck = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _awaitingInitialComplianceCheck = widget.controller.isAuthenticated &&
        widget.controller.complianceStatus == null;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !widget.controller.isAuthenticated) {
        return;
      }
      widget.controller.refreshCompliance().whenComplete(() {
        if (!mounted || !_awaitingInitialComplianceCheck) {
          return;
        }
        setState(() {
          _awaitingInitialComplianceCheck = false;
        });
      });
    });
  }

  @override
  void dispose() {
    _amountController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final GteComplianceStatus? compliance = widget.controller.complianceStatus;
    if (widget.controller.isLoadingCompliance && compliance == null) {
      setState(() {
        _error = 'Compliance status is still loading. Please retry.';
      });
      return;
    }
    if (widget.controller.complianceError != null && compliance == null) {
      setState(() {
        _error =
            'Deposit access could not be verified. Retry the compliance check.';
      });
      return;
    }
    if (compliance == null) {
      setState(() {
        _error = 'Deposit access is still syncing. Please retry in a moment.';
      });
      return;
    }
    if (!compliance.canDeposit) {
      setState(() {
        _error =
            'Deposits are blocked until compliance requirements are completed.';
      });
      return;
    }
    final double? amount = double.tryParse(_amountController.text.trim());
    if (amount == null || amount <= 0) {
      setState(() {
        _error = 'Enter a valid amount to continue.';
      });
      return;
    }
    setState(() {
      _error = null;
      _isSubmitting = true;
    });
    try {
      final GteDepositRequest deposit =
          await widget.controller.api.createDepositRequest(
        GteDepositCreateRequest(
          amount: amount,
          inputUnit: _inputFiat ? 'fiat' : 'coin',
        ),
      );
      if (!mounted) {
        return;
      }
      await Navigator.of(context).push<void>(
        MaterialPageRoute<void>(
          builder: (BuildContext context) => GteDepositInstructionsScreen(
            controller: widget.controller,
            deposit: deposit,
          ),
        ),
      );
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Fund wallet')),
      body: AnimatedBuilder(
        animation: widget.controller,
        builder: (BuildContext context, Widget? child) {
          final GteComplianceStatus? compliance =
              widget.controller.complianceStatus;
          final bool compliancePending = _awaitingInitialComplianceCheck ||
              (widget.controller.isLoadingCompliance && compliance == null);
          final bool complianceUnavailable =
              widget.controller.complianceError != null && compliance == null;
          final bool blocked = compliance != null && !compliance.canDeposit;
          return ListView(
            padding: const EdgeInsets.all(20),
            children: <Widget>[
              if (compliancePending) ...<Widget>[
                const GteSurfacePanel(
                  accentColor: GteShellTheme.accentCapital,
                  child: Text(
                    'Checking deposit access before manual funding opens...',
                  ),
                ),
                const SizedBox(height: 16),
              ],
              if (complianceUnavailable) ...<Widget>[
                GteStatePanel(
                  title: 'Deposit access unavailable',
                  message:
                      'We could not verify whether this account can create a manual deposit request. Retry the compliance check before continuing.',
                  icon: Icons.sync_problem_outlined,
                  actionLabel: 'Retry',
                  onAction: widget.controller.refreshCompliance,
                ),
                const SizedBox(height: 16),
              ],
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
                      Text(
                        compliance?.requiredPolicyAcceptancesMissing == null
                            ? 'Complete required policy acceptances to unlock deposits.'
                            : 'Complete ${compliance!.requiredPolicyAcceptancesMissing} policy items to unlock deposits.',
                      ),
                      const SizedBox(height: 12),
                      FilledButton.tonalIcon(
                        onPressed: () async {
                          await Navigator.of(context).push(
                            MaterialPageRoute<void>(
                              builder: (_) => GtePolicyComplianceCenterScreen(
                                controller: widget.controller,
                              ),
                            ),
                          );
                        },
                        icon: const Icon(Icons.gavel_outlined),
                        label: const Text('Open compliance center'),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),
                const GteStatePanel(
                  title: 'Deposit requests stay locked',
                  message:
                      'Manual bank transfer instructions and exact payment references appear only after compliance review unlocks deposits for this account.',
                  icon: Icons.lock_outline,
                ),
              ] else if (!compliancePending && !complianceUnavailable)
                GteSurfacePanel(
                  emphasized: true,
                  accentColor: GteShellTheme.accentCapital,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text('Create a deposit request',
                          style: Theme.of(context).textTheme.titleLarge),
                      const SizedBox(height: 8),
                      Text(
                        'Manual bank transfers require an exact payment reference. We will generate the amount and reference for you.',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 16),
                      ToggleButtons(
                        isSelected: <bool>[_inputFiat, !_inputFiat],
                        onPressed: _isSubmitting
                            ? null
                            : (int index) {
                                setState(() {
                                  _inputFiat = index == 0;
                                });
                              },
                        children: const <Widget>[
                          Padding(
                            padding: EdgeInsets.symmetric(horizontal: 16),
                            child: Text('NGN'),
                          ),
                          Padding(
                            padding: EdgeInsets.symmetric(horizontal: 16),
                            child: Text('Coins'),
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      TextField(
                        controller: _amountController,
                        keyboardType: const TextInputType.numberWithOptions(
                            decimal: true),
                        decoration: InputDecoration(
                          labelText:
                              _inputFiat ? 'Amount in NGN' : 'Amount in coins',
                          prefixIcon: const Icon(Icons.payments_outlined),
                        ),
                      ),
                      if (_error != null) ...<Widget>[
                        const SizedBox(height: 12),
                        GteStatePanel(
                          title: 'Deposit error',
                          message: _error!,
                          icon: Icons.warning_amber_rounded,
                        ),
                      ],
                      const SizedBox(height: 18),
                      SizedBox(
                        width: double.infinity,
                        child: FilledButton.icon(
                          onPressed: _isSubmitting ? null : _submit,
                          icon: const Icon(Icons.account_balance_outlined),
                          label: Text(
                            _isSubmitting
                                ? 'Generating instructions...'
                                : 'Generate payment instructions',
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          );
        },
      ),
    );
  }
}

class GteDepositInstructionsScreen extends StatefulWidget {
  const GteDepositInstructionsScreen({
    super.key,
    required this.controller,
    required this.deposit,
  });

  final GteExchangeController controller;
  final GteDepositRequest deposit;

  @override
  State<GteDepositInstructionsScreen> createState() =>
      _GteDepositInstructionsScreenState();
}

class _GteDepositInstructionsScreenState
    extends State<GteDepositInstructionsScreen> {
  late final TextEditingController _payerNameController;
  late final TextEditingController _senderBankController;
  late final TextEditingController _transferRefController;
  GteAttachment? _attachment;
  bool _isSubmitting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _payerNameController =
        TextEditingController(text: widget.deposit.payerName ?? '');
    _senderBankController =
        TextEditingController(text: widget.deposit.senderBank ?? '');
    _transferRefController =
        TextEditingController(text: widget.deposit.transferReference ?? '');
  }

  @override
  void dispose() {
    _payerNameController.dispose();
    _senderBankController.dispose();
    _transferRefController.dispose();
    super.dispose();
  }

  Future<void> _pickAttachment() async {
    final FilePickerResult? result = await FilePicker.platform.pickFiles();
    if (result == null || result.files.isEmpty) {
      return;
    }
    final PlatformFile file = result.files.first;
    final List<int> bytes = file.bytes ?? await File(file.path!).readAsBytes();
    final GteAttachment attachment =
        await widget.controller.api.uploadAttachment(file.name, bytes);
    if (!mounted) {
      return;
    }
    setState(() {
      _attachment = attachment;
    });
  }

  Future<void> _submitPayment() async {
    setState(() {
      _isSubmitting = true;
      _error = null;
    });
    try {
      final GteDepositRequest updated =
          await widget.controller.api.submitDepositRequest(
        widget.deposit.id,
        GteDepositSubmitRequest(
          payerName: _payerNameController.text.trim().isEmpty
              ? null
              : _payerNameController.text.trim(),
          senderBank: _senderBankController.text.trim().isEmpty
              ? null
              : _senderBankController.text.trim(),
          transferReference: _transferRefController.text.trim().isEmpty
              ? null
              : _transferRefController.text.trim(),
          proofAttachmentId: _attachment?.id,
        ),
      );
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
              'Payment submitted for ${updated.reference}. Await admin confirmation.'),
        ),
      );
      Navigator.of(context).pop();
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

  @override
  Widget build(BuildContext context) {
    final GteDepositRequest deposit = widget.deposit;
    return Scaffold(
      appBar: AppBar(title: const Text('Payment instructions')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: <Widget>[
          GteSurfacePanel(
            emphasized: true,
            accentColor: GteShellTheme.accentCapital,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text('Transfer exact amount',
                    style: Theme.of(context).textTheme.titleLarge),
                const SizedBox(height: 8),
                Text(
                  'Reference: ${deposit.reference}',
                  style: Theme.of(context)
                      .textTheme
                      .bodyMedium
                      ?.copyWith(color: GteShellTheme.accentCapital),
                ),
                const SizedBox(height: 16),
                _InstructionRow(
                  label: 'Amount (NGN)',
                  value: gteFormatFiat(deposit.amountFiat,
                      currency: deposit.currencyCode),
                ),
                _InstructionRow(
                  label: 'Coins credited',
                  value: gteFormatCredits(deposit.amountCoin),
                ),
                const Divider(height: 28),
                _InstructionRow(label: 'Bank', value: deposit.bankName),
                _InstructionRow(
                    label: 'Account number', value: deposit.bankAccountNumber),
                _InstructionRow(
                    label: 'Account name', value: deposit.bankAccountName),
                if (deposit.bankCode != null)
                  _InstructionRow(label: 'Bank code', value: deposit.bankCode!),
                const SizedBox(height: 12),
                Text(
                  'Use the reference exactly so the treasury team can match your transfer.',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          GteSurfacePanel(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text('Confirm payment',
                    style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 12),
                TextField(
                  controller: _payerNameController,
                  decoration: const InputDecoration(
                    labelText: 'Payer name (optional)',
                    prefixIcon: Icon(Icons.person_outline),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _senderBankController,
                  decoration: const InputDecoration(
                    labelText: 'Sender bank (optional)',
                    prefixIcon: Icon(Icons.account_balance_outlined),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _transferRefController,
                  decoration: const InputDecoration(
                    labelText: 'Transfer note/reference (optional)',
                    prefixIcon: Icon(Icons.receipt_long_outlined),
                  ),
                ),
                const SizedBox(height: 12),
                Row(
                  children: <Widget>[
                    Expanded(
                      child: OutlinedButton.icon(
                        onPressed: _pickAttachment,
                        icon: const Icon(Icons.attach_file),
                        label: Text(
                          _attachment == null
                              ? 'Upload proof'
                              : 'Proof: ${_attachment!.filename}',
                        ),
                      ),
                    ),
                  ],
                ),
                if (_error != null) ...<Widget>[
                  const SizedBox(height: 12),
                  GteStatePanel(
                    title: 'Submission error',
                    message: _error!,
                    icon: Icons.warning_amber_rounded,
                  ),
                ],
                const SizedBox(height: 18),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    onPressed: _isSubmitting ? null : _submitPayment,
                    child: Text(_isSubmitting
                        ? 'Submitting...'
                        : 'I have made payment'),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _InstructionRow extends StatelessWidget {
  const _InstructionRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        children: <Widget>[
          Expanded(
            child: Text(label, style: Theme.of(context).textTheme.bodySmall),
          ),
          Text(value, style: Theme.of(context).textTheme.titleMedium),
        ],
      ),
    );
  }
}
