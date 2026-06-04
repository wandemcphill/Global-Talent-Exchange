import 'package:flutter/material.dart';

import 'package:gte_frontend/data/gte_models.dart';
import 'package:gte_frontend/features/capital/wallet/data/capital_wallet_api.dart';
import 'package:gte_frontend/providers/gte_exchange_controller.dart';
import 'package:gte_frontend/widgets/gte_formatters.dart';
import 'package:gte_frontend/widgets/gte_shell_theme.dart';
import 'package:gte_frontend/widgets/gte_state_panel.dart';
import 'package:gte_frontend/widgets/gte_surface_panel.dart';
import 'package:gte_frontend/screens/onboarding/gte_region_selection_screen.dart';

class GtePolicyComplianceCenterScreen extends StatefulWidget {
  const GtePolicyComplianceCenterScreen({super.key, required this.controller});

  final GteExchangeController controller;

  @override
  State<GtePolicyComplianceCenterScreen> createState() =>
      _GtePolicyComplianceCenterScreenState();
}

class _GtePolicyComplianceCenterScreenState
    extends State<GtePolicyComplianceCenterScreen> {
  CapitalWalletApi get _walletApi => widget.controller.walletApi;
  late Future<_PolicyCenterBundle> _bundleFuture;
  final Set<String> _acceptingKeys = <String>{};

  @override
  void initState() {
    super.initState();
    _bundleFuture = _loadBundle();
  }

  Future<_PolicyCenterBundle> _loadBundle() async {
    final List<GtePolicyDocumentSummary> documents =
        await _walletApi.fetchPolicyDocuments();
    final GteComplianceStatus compliance =
        await _walletApi.fetchComplianceStatus();
    final List<GtePolicyAcceptanceSummary> acceptances =
        await _walletApi.fetchMyPolicyAcceptances();
    return _PolicyCenterBundle(
      documents: documents,
      compliance: compliance,
      acceptances: acceptances,
    );
  }

  Future<void> _refresh() async {
    final Future<_PolicyCenterBundle> bundleFuture = _loadBundle();
    setState(() {
      _bundleFuture = bundleFuture;
    });
    await Future.wait<Object?>(<Future<Object?>>[
      bundleFuture,
      widget.controller.refreshCompliance(),
    ]);
  }

  Future<void> _acceptDocument(GtePolicyDocumentSummary document) async {
    final String? versionLabel = document.latestVersion?.versionLabel;
    if (versionLabel == null) {
      return;
    }
    setState(() {
      _acceptingKeys.add(document.documentKey);
    });
    try {
      await _walletApi.acceptPolicyDocument(document.documentKey, versionLabel);
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('${document.title} accepted.')));
      await _refresh();
    } finally {
      if (mounted) {
        setState(() {
          _acceptingKeys.remove(document.documentKey);
        });
      }
    }
  }

  Future<void> _showDocument(GtePolicyDocumentSummary document) async {
    final GtePolicyDocumentDetail detail = await _walletApi.fetchPolicyDocument(
      document.documentKey,
    );
    if (!mounted) {
      return;
    }
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF0B1020),
      builder: (BuildContext context) {
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(
                  children: <Widget>[
                    Expanded(
                      child: Text(
                        detail.title,
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                    ),
                    IconButton(
                      onPressed: () => Navigator.of(context).pop(),
                      icon: const Icon(Icons.close),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                if (detail.latestVersion != null)
                  Text(
                    'Version ${detail.latestVersion!.versionLabel} - Effective ${gteFormatDate(detail.latestVersion!.effectiveAt)}',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                const SizedBox(height: 16),
                Expanded(
                  child: SingleChildScrollView(
                    child: Text(
                      detail.bodyMarkdown ?? 'No policy text published.',
                    ),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Policy & compliance center'),
        actions: <Widget>[
          IconButton(onPressed: _refresh, icon: const Icon(Icons.refresh)),
        ],
      ),
      body: FutureBuilder<_PolicyCenterBundle>(
        future: _bundleFuture,
        builder: (
          BuildContext context,
          AsyncSnapshot<_PolicyCenterBundle> snapshot,
        ) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError && !snapshot.hasData) {
            return Center(
              child: GteStatePanel(
                title: 'Compliance center unavailable',
                message:
                    'We could not sync policy and compliance details from the backend.',
                icon: Icons.sync_problem_outlined,
                actionLabel: 'Retry',
                onAction: _refresh,
              ),
            );
          }
          if (!snapshot.hasData) {
            return Center(
              child: GteStatePanel(
                title: 'Compliance center unavailable',
                message:
                    'Policy and compliance details are pending backend sync.',
                icon: Icons.gavel_outlined,
                actionLabel: 'Retry',
                onAction: _refresh,
              ),
            );
          }
          final _PolicyCenterBundle bundle = snapshot.data!;
          final bool compliancePending = _complianceStatusPending(
            bundle.compliance,
          );
          final Set<String> acceptedKeys =
              bundle.acceptances
                  .map((GtePolicyAcceptanceSummary item) => item.documentKey)
                  .toSet();
          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView(
              padding: const EdgeInsets.all(20),
              children: <Widget>[
                GteSurfacePanel(
                  emphasized: true,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Your access status',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 10),
                      Text(
                        compliancePending
                            ? 'Compliance status is pending backend sync.'
                            : bundle.compliance.hasMissingRequiredPolicies
                            ? '${bundle.compliance.requiredPolicyAcceptancesMissing} required policy acceptance(s) still missing.'
                            : 'All required policy acceptances are in place.',
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                      const SizedBox(height: 14),
                      Wrap(
                        spacing: 12,
                        runSpacing: 12,
                        children: <Widget>[
                          _StatusChip(
                            label: 'Country',
                            value: _complianceCountryLabel(
                              bundle.compliance.countryCode,
                            ),
                          ),
                          _StatusChip(
                            label: 'Deposits',
                            value:
                                compliancePending
                                    ? 'Pending'
                                    : bundle.compliance.canDeposit
                                    ? 'Open'
                                    : 'Blocked',
                          ),
                          _StatusChip(
                            label: 'Market',
                            value:
                                compliancePending
                                    ? 'Pending'
                                    : bundle.compliance.canTradeMarket
                                    ? 'Open'
                                    : 'Blocked',
                          ),
                          _StatusChip(
                            label: 'Withdrawals',
                            value:
                                compliancePending
                                    ? 'Pending'
                                    : bundle
                                        .compliance
                                        .canWithdrawPlatformRewards
                                    ? 'Open'
                                    : 'Blocked',
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      FilledButton.tonalIcon(
                        onPressed: () async {
                          await Navigator.of(context).push(
                            MaterialPageRoute<void>(
                              builder:
                                  (_) => GteRegionSelectionScreen(
                                    controller: widget.controller,
                                    currentCountry:
                                        _complianceCountryForRegionPicker(
                                          bundle.compliance.countryCode,
                                        ),
                                  ),
                            ),
                          );
                          await _refresh();
                        },
                        icon: const Icon(Icons.public_outlined),
                        label: const Text('Select region'),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 18),
                GteSurfacePanel(
                  accentColor:
                      bundle.compliance.hasMissingRequiredPolicies
                          ? GteShellTheme.accentWarm
                          : GteShellTheme.accentCommunity,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Mandatory acceptances',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        bundle.compliance.missingPolicyAcceptances.isEmpty
                            ? compliancePending
                                ? 'Policy requirements are pending backend sync.'
                                : 'Nothing pending. Your compliance board is clean.'
                            : 'Complete the required policy acceptances to unlock deposits, withdrawals, and trading.',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      const SizedBox(height: 12),
                      if (bundle.compliance.missingPolicyAcceptances.isNotEmpty)
                        ...bundle.compliance.missingPolicyAcceptances.map(
                          (GtePolicyRequirementSummary item) => Padding(
                            padding: const EdgeInsets.only(bottom: 10),
                            child: Row(
                              children: <Widget>[
                                const Icon(
                                  Icons.warning_amber_outlined,
                                  size: 18,
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    '${item.title} - ${item.versionLabel}',
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
                const SizedBox(height: 18),
                GteSurfacePanel(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text(
                        'Policy documents',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 12),
                      ...bundle.documents.map((
                        GtePolicyDocumentSummary document,
                      ) {
                        final bool accepted = acceptedKeys.contains(
                          document.documentKey,
                        );
                        final bool isBusy = _acceptingKeys.contains(
                          document.documentKey,
                        );
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 12),
                          child: Container(
                            padding: const EdgeInsets.all(14),
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(16),
                              color: Colors.white.withValues(alpha: 0.03),
                              border: Border.all(
                                color: Colors.white.withValues(alpha: 0.08),
                              ),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: <Widget>[
                                Row(
                                  children: <Widget>[
                                    Expanded(
                                      child: Text(
                                        document.title,
                                        style:
                                            Theme.of(
                                              context,
                                            ).textTheme.titleMedium,
                                      ),
                                    ),
                                    if (document.isMandatory)
                                      Container(
                                        padding: const EdgeInsets.symmetric(
                                          horizontal: 10,
                                          vertical: 6,
                                        ),
                                        decoration: BoxDecoration(
                                          borderRadius: BorderRadius.circular(
                                            999,
                                          ),
                                          color: Colors.orange.withValues(
                                            alpha: 0.14,
                                          ),
                                        ),
                                        child: const Text('Required'),
                                      ),
                                  ],
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  'Latest: ${document.latestVersion?.versionLabel ?? 'Unpublished'}',
                                  style: Theme.of(context).textTheme.bodySmall,
                                ),
                                const SizedBox(height: 12),
                                Row(
                                  children: <Widget>[
                                    OutlinedButton(
                                      onPressed: () => _showDocument(document),
                                      child: const Text('Read'),
                                    ),
                                    const SizedBox(width: 10),
                                    FilledButton(
                                      onPressed:
                                          accepted || isBusy
                                              ? null
                                              : () => _acceptDocument(document),
                                      child: Text(
                                        accepted
                                            ? 'Accepted'
                                            : isBusy
                                            ? 'Saving...'
                                            : 'Accept',
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                        );
                      }),
                    ],
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _PolicyCenterBundle {
  const _PolicyCenterBundle({
    required this.documents,
    required this.compliance,
    required this.acceptances,
  });

  final List<GtePolicyDocumentSummary> documents;
  final GteComplianceStatus compliance;
  final List<GtePolicyAcceptanceSummary> acceptances;
}

bool _complianceStatusPending(GteComplianceStatus compliance) {
  return _isBackendPendingValue(compliance.countryCode) ||
      _isBackendPendingValue(compliance.countryPolicyBucket) ||
      compliance.complianceStatus.trim().toLowerCase() == 'unknown';
}

String _complianceCountryLabel(String countryCode) {
  if (_isBackendPendingValue(countryCode)) {
    return 'Backend pending';
  }
  return countryCode;
}

String? _complianceCountryForRegionPicker(String countryCode) {
  if (_isBackendPendingValue(countryCode)) {
    return null;
  }
  return countryCode;
}

bool _isBackendPendingValue(String value) {
  final String normalized = value.trim().toLowerCase();
  return normalized.isEmpty ||
      normalized == 'backend_pending' ||
      normalized == 'unknown' ||
      normalized == 'unavailable';
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(14),
        color: Colors.white.withValues(alpha: 0.04),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
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
