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

class GteFundWalletScreen extends StatefulWidget {
  const GteFundWalletScreen({super.key, required this.controller});

  final GteExchangeController controller;

  @override
  State<GteFundWalletScreen> createState() => _GteFundWalletScreenState();
}

class _GteFundWalletScreenState extends State<GteFundWalletScreen> {
  final TextEditingController _amountController = TextEditingController();
  bool _isSubmitting = false;
  bool _isVerifying = false;
  String? _error;
  GteWalletTopUpSession? _session;
  GteWalletTopUpVerificationResult? _verification;

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

  Future<void> _initiateTopUp() async {
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
      final GteWalletTopUpSession session = await widget.controller.api
          .initiateWalletTopUp(GteWalletTopUpInitiateRequest(amount: amount));
      if (!mounted) {
        return;
      }
      setState(() {
        _session = session;
        _verification = null;
      });
      if (session.paymentLink.trim().isNotEmpty) {
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
      await widget.controller.loadPortfolio();
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

  void _resetFlow() {
    setState(() {
      _amountController.clear();
      _error = null;
      _session = null;
      _verification = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    final GteWalletTopUpSession? session = _session;
    final GteWalletTopUpVerificationResult? verification = _verification;
    return Scaffold(
      appBar: AppBar(title: const Text('Top up wallet')),
      body: ListView(
        padding: const EdgeInsets.all(20),
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
          ],
          GteSurfacePanel(
            accentColor: GteShellTheme.accentCapital,
            emphasized: true,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'Fund with Paystack',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 8),
                Text(
                  'Create a payment session, complete payment in Paystack, then verify it here to update your live wallet balance.',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: _amountController,
                  keyboardType: const TextInputType.numberWithOptions(
                    decimal: true,
                  ),
                  enabled: !_isSubmitting && session == null,
                  decoration: const InputDecoration(
                    labelText: 'Amount',
                    prefixIcon: Icon(Icons.payments_outlined),
                  ),
                ),
                const SizedBox(height: 16),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    onPressed:
                        _isSubmitting || session != null
                            ? null
                            : _initiateTopUp,
                    icon: const Icon(Icons.open_in_new_outlined),
                    label: Text(
                      _isSubmitting
                          ? 'Creating payment session...'
                          : 'Continue to Paystack',
                    ),
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
                    'Payment session ready',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 10),
                  Text('Reference: ${session.reference}'),
                  const SizedBox(height: 6),
                  Text('Amount: ${gteFormatCredits(session.amount)}'),
                  const SizedBox(height: 6),
                  Text('Status: ${_titleCase(session.status)}'),
                  if (session.mockMode) ...<Widget>[
                    const SizedBox(height: 10),
                    const Text(
                      'Mock mode is active because no Paystack secret key is configured locally.',
                    ),
                  ],
                  const SizedBox(height: 14),
                  Wrap(
                    spacing: 10,
                    runSpacing: 10,
                    children: <Widget>[
                      FilledButton.icon(
                        onPressed:
                            _isVerifying
                                ? null
                                : () => _launchPaymentLink(session.paymentLink),
                        icon: const Icon(Icons.open_in_browser_outlined),
                        label: const Text('Open Paystack'),
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
                            _isSubmitting || _isVerifying ? null : _resetFlow,
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
                    'New balance: ${gteFormatCredits(verification.wallet.balance)}',
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'Transaction status: ${_titleCase(verification.transaction.status)}',
                  ),
                  const SizedBox(height: 14),
                  FilledButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('Back to wallet'),
                  ),
                ],
              ),
            ),
          ],
          if (_error != null) ...<Widget>[
            const SizedBox(height: 18),
            GteStatePanel(
              title: 'Top-up issue',
              message: _error!,
              icon: Icons.warning_amber_rounded,
            ),
          ],
        ],
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
