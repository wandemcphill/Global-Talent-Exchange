import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/app_feedback.dart';
import '../../core/constants/app_spacing.dart';
import '../../features/shared/data/gte_feature_support.dart';
import '../../navigation/app_destinations.dart';
import '../../shared/models/data_source_status.dart';
import '../../shared/providers/auth_provider.dart';
import '../../shared/widgets/app_page_layout.dart';
import '../../shared/widgets/data_source_badge.dart';
import '../../shared/widgets/gtex_premium_panels.dart';
import '../../widgets/gte_state_panel.dart';
import 'live_profile_provider.dart';

class ProfileAdminScreen extends ConsumerStatefulWidget {
  const ProfileAdminScreen({super.key});

  @override
  ConsumerState<ProfileAdminScreen> createState() => _ProfileAdminScreenState();
}

class _ProfileAdminScreenState extends ConsumerState<ProfileAdminScreen> {
  final TextEditingController _providerController = TextEditingController(
    text: 'football_data',
  );
  bool _busy = false;

  @override
  void dispose() {
    _providerController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final bool authenticated = ref.watch(isAuthenticatedProvider);
    final bool isAdmin = ref.watch(isAdminProvider);
    final bool isSuperAdmin = ref.watch(isSuperAdminProvider);
    final bool isDelegatedAdmin = ref.watch(isDelegatedAdminProvider);
    final bool canManageCatalog = ref.watch(canManageManagerCatalogProvider);
    final bool canManageSupply = ref.watch(canManageManagerSupplyProvider);
    final bool canAccessGodMode = ref.watch(canAccessGodModeProvider);
    final String? godModeBlockedReason = ref.watch(
      godModeBlockedReasonProvider,
    );
    final bool hasAdminCapability =
        canManageCatalog || canManageSupply || canAccessGodMode;
    final AsyncValue<AdminImportOverviewData>? overview =
        authenticated && isAdmin && canManageCatalog
            ? ref.watch(adminImportOverviewProvider)
            : null;
    final DataSourceStatus status =
        !authenticated || !isAdmin || !hasAdminCapability
            ? DataSourceStatus.blocked
            : DataSourceStatus.live;

    return AppPageLayout(
      title: 'Profile > Admin',
      subtitle:
          'The active shell only exposes import, supply, and God Mode controls when the authenticated admin session carries the matching backend permission.',
      trailing: DataSourceBadge(status: status),
      children: <Widget>[
        if (!authenticated)
          const _BlockedCard(
            title: 'Admin tooling is blocked',
            message: 'You are not signed in.',
          )
        else if (!isAdmin)
          const _BlockedCard(
            title: 'Admin tooling is blocked',
            message: 'This session does not carry admin permissions.',
          )
        else if (!hasAdminCapability)
          const _BlockedCard(
            title: 'Admin tooling is blocked',
            message:
                'This admin session is authenticated, but it does not carry catalog, supply, or audit permissions for the active shell.',
          )
        else ...<Widget>[
          GtexHeroPanel(
            eyebrow: 'ADMIN CONTROL TOWER',
            title:
                isSuperAdmin
                    ? 'Super-admin controls are live.'
                    : isDelegatedAdmin
                    ? 'Delegated admin controls are live.'
                    : 'Admin controls are live.',
            description:
                'Import, supply, and God Mode actions remain gated by explicit backend permissions carried on the authenticated session.',
            metrics: <Widget>[
              GtexPill(
                label:
                    isSuperAdmin
                        ? 'SUPER_ADMIN'
                        : isDelegatedAdmin
                        ? 'DELEGATED_ADMIN'
                        : 'ADMIN',
                tone: GtexSurfaceTone.live,
              ),
              if (!canManageCatalog)
                const GtexPill(
                  label: 'Catalog blocked',
                  tone: GtexSurfaceTone.warning,
                ),
              if (!canManageSupply)
                const GtexPill(
                  label: 'Supply blocked',
                  tone: GtexSurfaceTone.warning,
                ),
              if (!canAccessGodMode)
                GtexPill(
                  label: 'God Mode ${godModeBlockedReason ?? 'blocked'}',
                  tone: GtexSurfaceTone.warning,
                ),
            ],
            actions: <Widget>[
              if (canManageCatalog)
                FilledButton(
                  onPressed: _busy ? null : _triggerImport,
                  child: const Text('Trigger import'),
                ),
              if (canAccessGodMode)
                OutlinedButton(
                  onPressed:
                      _busy
                          ? null
                          : () => context.push(AppRoutes.profileGodMode),
                  child: const Text('Open God Mode'),
                ),
              if (canManageCatalog)
                OutlinedButton(
                  onPressed: _busy ? null : _resumeSelectedBatch,
                  child: const Text('Resume selected batch'),
                ),
              if (canManageSupply)
                OutlinedButton(
                  onPressed: _busy ? null : _issueShareMarket,
                  child: const Text('Issue share market'),
                ),
            ],
          ),
          const SizedBox(height: spacingMD),
          GtexSectionPanel(
            eyebrow: 'PROVIDER',
            title: 'Import provider',
            subtitle:
                canManageCatalog
                    ? 'Manage the provider backing live real-player import batches.'
                    : 'Real-player import controls are hidden until this session carries manage_manager_catalog.',
            child:
                canManageCatalog
                    ? TextField(
                      controller: _providerController,
                      decoration: const InputDecoration(
                        labelText: 'Provider name',
                      ),
                      onSubmitted: (String value) {
                        ref
                            .read(adminImportProviderNameProvider.notifier)
                            .setProviderName(value);
                      },
                    )
                    : const Text(
                      'Real-player import controls are hidden until this session carries manage_manager_catalog.',
                    ),
          ),
          if (!canManageCatalog) ...<Widget>[
            const SizedBox(height: spacingMD),
            const _BlockedCard(
              title: 'Player import is blocked',
              message:
                  'This session lacks the manage_manager_catalog permission required by the active-shell import surface.',
            ),
          ],
          if (!canManageSupply) ...<Widget>[
            const SizedBox(height: spacingMD),
            const _BlockedCard(
              title: 'Share issuance is blocked',
              message:
                  'This session lacks the manage_manager_supply permission required to issue live player share markets.',
            ),
          ],
          if (!canAccessGodMode) ...<Widget>[
            const SizedBox(height: spacingMD),
            _BlockedCard(
              title: 'God Mode is blocked',
              message: godModeBlockedReason ?? 'missing session claims',
            ),
          ],
          if (overview != null) ...<Widget>[
            const SizedBox(height: spacingMD),
            overview.when(
              data:
                  (AdminImportOverviewData value) => Column(
                    children: <Widget>[
                      _JsonCard(
                        title: 'Provider health',
                        payload: value.health,
                      ),
                      const SizedBox(height: spacingMD),
                      _JsonCard(title: 'Import status', payload: value.status),
                      const SizedBox(height: spacingMD),
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(spacingLG),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: <Widget>[
                              Text(
                                'Recent batches',
                                style: Theme.of(context).textTheme.titleLarge,
                              ),
                              const SizedBox(height: spacingSM),
                              if (value.batches.isEmpty)
                                const Text('No import batches returned yet.')
                              else
                                ...value.batches.map(
                                  (JsonMap batch) => RadioListTile<String>(
                                    value: stringValue(batch['id']),
                                    groupValue: ref.watch(
                                      adminSelectedBatchIdProvider,
                                    ),
                                    onChanged: (String? next) {
                                      ref
                                          .read(
                                            adminSelectedBatchIdProvider
                                                .notifier,
                                          )
                                          .select(next);
                                    },
                                    title: Text(
                                      stringValue(
                                        batch['batch_key'],
                                        fallback: stringValue(batch['id']),
                                      ),
                                    ),
                                    subtitle: Text(
                                      'status ${stringValue(batch['status'])} | created ${intValue(batch['created_player_count'])} | updated ${intValue(batch['updated_player_count'])} | failed ${intValue(batch['failed_row_count'])}',
                                    ),
                                  ),
                                ),
                            ],
                          ),
                        ),
                      ),
                      if (value.selectedBatch != null) ...<Widget>[
                        const SizedBox(height: spacingMD),
                        _JsonCard(
                          title: 'Selected batch',
                          payload: value.selectedBatch!,
                        ),
                      ],
                      if (value.selectedBatchIssues.isNotEmpty) ...<Widget>[
                        const SizedBox(height: spacingMD),
                        Card(
                          child: Padding(
                            padding: const EdgeInsets.all(spacingLG),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: <Widget>[
                                Text(
                                  'Selected batch issues',
                                  style: Theme.of(context).textTheme.titleLarge,
                                ),
                                const SizedBox(height: spacingSM),
                                ...value.selectedBatchIssues
                                    .take(12)
                                    .map(
                                      (JsonMap issue) => ListTile(
                                        dense: true,
                                        contentPadding: EdgeInsets.zero,
                                        title: Text(
                                          stringValue(
                                            issue['canonical_name'],
                                            fallback: stringValue(
                                              issue['row_id'],
                                            ),
                                          ),
                                        ),
                                        subtitle: Text(
                                          '${stringValue(issue['issue_type'])} | ${stringValue(issue['required_action'])}',
                                        ),
                                      ),
                                    ),
                              ],
                            ),
                          ),
                        ),
                      ],
                      if (value.selectedBatchValuation != null) ...<Widget>[
                        const SizedBox(height: spacingMD),
                        _JsonCard(
                          title: 'Selected batch valuation status',
                          payload: value.selectedBatchValuation!,
                        ),
                      ],
                    ],
                  ),
              loading:
                  () => const GteStatePanel(
                    title: 'Loading admin import surface',
                    message: 'Syncing provider health and batch status.',
                    isLoading: true,
                  ),
              error:
                  (Object error, StackTrace stackTrace) => _BlockedCard(
                    title: 'Admin import surface is blocked',
                    message: AppFeedback.messageFor(error),
                  ),
            ),
          ],
        ],
      ],
    );
  }

  Future<void> _triggerImport() async {
    if (!ref.read(canManageManagerCatalogProvider)) {
      _showMessage(
        'Real-player import is blocked: manage_manager_catalog required.',
      );
      return;
    }
    await _runAction(() async {
      final String providerName = _resolvedProviderName();
      await ref
          .read(authedApiProvider)
          .post(
            '/internal/ingestion/real-players/import',
            body: <String, Object?>{
              'provider_name': providerName,
              'batch_size': 100,
            },
          );
      ref.invalidate(adminImportOverviewProvider);
    });
  }

  Future<void> _resumeSelectedBatch() async {
    if (!ref.read(canManageManagerCatalogProvider)) {
      _showMessage('Batch resume is blocked: manage_manager_catalog required.');
      return;
    }
    final String? batchId = ref.read(adminSelectedBatchIdProvider);
    if (batchId == null || batchId.trim().isEmpty) {
      _showMessage('Select an import batch first.');
      return;
    }
    await _runAction(() async {
      await ref
          .read(authedApiProvider)
          .post(
            '/internal/ingestion/real-players/batches/$batchId/resume',
            body: const <String, Object?>{'mode': 'write'},
          );
      ref.invalidate(adminImportOverviewProvider);
    });
  }

  Future<void> _issueShareMarket() async {
    if (!ref.read(canManageManagerSupplyProvider)) {
      _showMessage(
        'Share issuance is blocked: manage_manager_supply required.',
      );
      return;
    }
    final TextEditingController playerController = TextEditingController();
    final TextEditingController sharesController = TextEditingController(
      text: '1000',
    );
    final TextEditingController priceController = TextEditingController(
      text: '10',
    );
    final bool? confirmed = await showDialog<bool>(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: const Text('Issue player share market'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              TextField(
                controller: playerController,
                decoration: const InputDecoration(labelText: 'Player ID'),
              ),
              TextField(
                controller: sharesController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'Total shares'),
              ),
              TextField(
                controller: priceController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'Share price'),
              ),
            ],
          ),
          actions: <Widget>[
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Issue'),
            ),
          ],
        );
      },
    );
    if (confirmed != true) {
      return;
    }
    await _runAction(() async {
      final String playerId = playerController.text.trim();
      if (playerId.isEmpty) {
        throw const FormatException('Player ID is required.');
      }
      await ref
          .read(authedApiProvider)
          .post(
            '/players/$playerId/shares/issue',
            body: <String, Object?>{
              'total_shares':
                  int.tryParse(sharesController.text.trim()) ?? 1000,
              'share_price_coin':
                  double.tryParse(priceController.text.trim()) ?? 10,
              'status': 'active',
            },
          );
    });
  }

  Future<void> _runAction(Future<void> Function() action) async {
    setState(() {
      _busy = true;
    });
    try {
      ref
          .read(adminImportProviderNameProvider.notifier)
          .setProviderName(_resolvedProviderName());
      await action();
      if (mounted) {
        _showMessage('Admin action completed.');
      }
    } catch (error) {
      if (mounted) {
        _showMessage(AppFeedback.messageFor(error));
      }
    } finally {
      if (mounted) {
        setState(() {
          _busy = false;
        });
      }
    }
  }

  String _resolvedProviderName() {
    final String value = _providerController.text.trim();
    return value.isEmpty ? 'football_data' : value;
  }

  void _showMessage(String message) {
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }
}

class _JsonCard extends StatelessWidget {
  const _JsonCard({required this.title, required this.payload});

  final String title;
  final JsonMap payload;

  @override
  Widget build(BuildContext context) {
    return GtexSectionPanel(
      eyebrow: 'ADMIN DATA',
      title: title,
      subtitle: 'Live backend payload',
      child: Text(
        payload.entries
            .map(
              (MapEntry<String, Object?> entry) =>
                  '${entry.key}: ${entry.value}',
            )
            .join('\n'),
      ),
    );
  }
}

class _BlockedCard extends StatelessWidget {
  const _BlockedCard({required this.title, required this.message});

  final String title;
  final String message;

  @override
  Widget build(BuildContext context) {
    return GteStatePanel(
      title: title,
      message: message,
      icon: Icons.lock_outline_rounded,
      accentColor: Theme.of(context).colorScheme.error,
    );
  }
}
