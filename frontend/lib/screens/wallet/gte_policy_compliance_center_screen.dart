import 'package:flutter/material.dart';

import '../../data/gte_models.dart';
import '../../providers/gte_exchange_controller.dart';
import '../../widgets/gte_formatters.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';

class GtePolicyComplianceCenterScreen extends StatefulWidget {
  const GtePolicyComplianceCenterScreen({
    super.key,
    required this.controller,
  });

  final GteExchangeController controller;

  @override
  State<GtePolicyComplianceCenterScreen> createState() =>
      _GtePolicyComplianceCenterScreenState();
}

class _GtePolicyComplianceCenterScreenState
    extends State<GtePolicyComplianceCenterScreen> {
  late Future<_PolicyCenterBundle> _bundleFuture;
  final Set<String> _acceptingKeys = <String>{};

  @override
  void initState() {
    super.initState();
    _bundleFuture = _loadBundle();
  }

  Future<_PolicyCenterBundle> _loadBundle() async {
    final List<GtePolicyDocumentSummary> documents =
        await widget.controller.api.fetchPolicyDocuments();
    final GteComplianceStatus compliance =
        await widget.controller.api.fetchComplianceStatus();
    final List<GtePolicyAcceptanceSummary> acceptances =
        await widget.controller.api.fetchMyPolicyAcceptances();
    return _PolicyCenterBundle(
      documents: documents,
      compliance: compliance,
      acceptances: acceptances,
    );
  }

  Future<void> _refresh() async {
    setState(() {
      _bundleFuture = _loadBundle();
    });
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
      await widget.controller.api
          .acceptPolicyDocument(document.documentKey, versionLabel);
      if (!mounted) {
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('${document.title} accepted.'),
        ),
      );
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
    final GtePolicyDocumentDetail detail =
        await widget.controller.api.fetchPolicyDocument(document.documentKey);
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
                    'Version ${detail.latestVersion!.versionLabel} • Effective ${gteFormatDate(detail.latestVersion!.effectiveAt)}',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                const SizedBox(height: 16),
                Expanded(
                  child: SingleChildScrollView(
                    child: Text(detail.bodyMarkdown ?? 'No policy text published.'),
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
        builder: (BuildContext context, AsyncSnapshot<_PolicyCenterBundle> snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (!snapshot.hasData) {
            return const Center(
              child: GteStatePanel(
                title: 'Compliance center unavailable',
                message: 'Unable to load policy and compliance details right now.',
                icon: Icons.gavel_outlined,
              ),
            );
          }
          final _PolicyCenterBundle bundle = snapshot.data!;
          final Set<String> acceptedKeys = bundle.acceptances
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
                      Text('Your access status',
                          style: Theme.of(context).textTheme.titleLarge),
                      const SizedBox(height: 10),
                      Text(
                        bundle.compliance.hasMissingRequiredPolicies
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
                            value: bundle.compliance.countryCode,
                          ),
                          _StatusChip(
                            label: 'Deposits',
                            value: bundle.compliance.canDeposit ? 'Open' : 'Blocked',
                          ),
                          _StatusChip(
                            label: 'Market',
                            value: bundle.compliance.canTradeMarket ? 'Open' : 'Blocked',
                          ),
                          _StatusChip(
                            label: 'Withdrawals',
                            value: bundle.compliance.canWithdrawPlatformRewards
                                ? 'Open'
                                : 'Blocked',
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 18),
                GteSurfacePanel(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: <Widget>[
                      Text('Required actions',
                          style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 12),
                      if (bundle.compliance.missingPolicyAcceptances.isEmpty)
                        const Text('Nothing pending. Your compliance board is clean.')
                      else
                        ...bundle.compliance.missingPolicyAcceptances.map(
                          (GtePolicyRequirementSummary item) => Padding(
                            padding: const EdgeInsets.only(bottom: 10),
                            child: Row(
                              children: <Widget>[
                                const Icon(Icons.warning_amber_outlined,
                                    size: 18),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    '${item.title} (${item.versionLabel})',
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
                      Text('Policy documents',
                          style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 12),
                      ...bundle.documents.map(
                        (GtePolicyDocumentSummary document) {
                          final bool accepted =
                              acceptedKeys.contains(document.documentKey);
                          final bool isBusy =
                              _acceptingKeys.contains(document.documentKey);
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
                                        child: Text(document.title,
                                            style: Theme.of(context)
                                                .textTheme
                                                .titleMedium),
                                      ),
                                      if (document.isMandatory)
                                        Container(
                                          padding: const EdgeInsets.symmetric(
                                              horizontal: 10, vertical: 6),
                                          decoration: BoxDecoration(
                                            borderRadius:
                                                BorderRadius.circular(999),
                                            color: Colors.orange
                                                .withValues(alpha: 0.14),
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
                                        onPressed: accepted || isBusy
                                            ? null
                                            : () => _acceptDocument(document),
                                        child: Text(accepted
                                            ? 'Accepted'
                                            : isBusy
                                                ? 'Saving...'
                                                : 'Accept'),
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                            ),
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
