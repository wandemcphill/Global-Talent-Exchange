import 'package:flutter/material.dart';

import '../../../core/app_feedback.dart';
import '../../../data/gte_api_repository.dart';
import '../../../features/shared/presentation/gte_feature_forms.dart';
import '../../../widgets/gte_metric_chip.dart';
import '../../../widgets/gte_shell_theme.dart';
import '../../../widgets/gte_state_panel.dart';
import '../../../widgets/gte_surface_panel.dart';
import '../data/creator_share_market_models.dart';
import 'creator_share_market_controller.dart';

class CreatorShareMarketAdminControlScreen extends StatefulWidget {
  const CreatorShareMarketAdminControlScreen({
    super.key,
    required this.baseUrl,
    required this.backendMode,
    this.accessToken,
    this.currentUserRole,
    this.onOpenLogin,
  });

  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final String? currentUserRole;
  final VoidCallback? onOpenLogin;

  @override
  State<CreatorShareMarketAdminControlScreen> createState() =>
      _CreatorShareMarketAdminControlScreenState();
}

class _CreatorShareMarketAdminControlScreenState
    extends State<CreatorShareMarketAdminControlScreen> {
  late final CreatorShareMarketController _controller;

  bool get _isAuthenticated => widget.accessToken?.trim().isNotEmpty == true;
  bool get _isAdmin => <String>{'admin', 'super_admin'}
      .contains((widget.currentUserRole ?? '').trim().toLowerCase());

  @override
  void initState() {
    super.initState();
    _controller = CreatorShareMarketController.standard(
      baseUrl: widget.baseUrl,
      backendMode: widget.backendMode,
      accessToken: widget.accessToken,
    );
    if (_isAdmin) {
      _controller.loadControl();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _updateControl() async {
    await showGteFormSheet(
      context,
      title: 'Update creator share control',
      fields: const <GteFormFieldSpec>[
        GteFormFieldSpec(
          key: 'maxSharesPerClub',
          label: 'Max shares per club',
          keyboardType: TextInputType.number,
        ),
        GteFormFieldSpec(
          key: 'maxSharesPerFan',
          label: 'Max shares per fan',
          keyboardType: TextInputType.number,
        ),
        GteFormFieldSpec(
          key: 'revenueBps',
          label: 'Shareholder revenue bps',
          keyboardType: TextInputType.number,
        ),
        GteFormFieldSpec(
          key: 'maxPurchaseValue',
          label: 'Max primary purchase value',
          keyboardType: TextInputType.number,
        ),
      ],
      onSubmit: (Map<String, String> values) async {
        final int? maxSharesPerClub =
            int.tryParse(values['maxSharesPerClub'] ?? '');
        final int? maxSharesPerFan =
            int.tryParse(values['maxSharesPerFan'] ?? '');
        final int? revenueBps = int.tryParse(values['revenueBps'] ?? '');
        final double? maxPurchaseValue =
            double.tryParse(values['maxPurchaseValue'] ?? '');
        if (maxSharesPerClub == null ||
            maxSharesPerFan == null ||
            revenueBps == null ||
            maxPurchaseValue == null) {
          AppFeedback.showError(context, 'Enter valid control values.');
          return false;
        }
        await _controller.updateControl(
          CreatorClubShareMarketControlUpdateRequest(
            maxSharesPerClub: maxSharesPerClub,
            maxSharesPerFan: maxSharesPerFan,
            shareholderRevenueShareBps: revenueBps,
            issuanceEnabled: _controller.control?.issuanceEnabled ?? true,
            purchaseEnabled: _controller.control?.purchaseEnabled ?? true,
            maxPrimaryPurchaseValueCoin: maxPurchaseValue,
          ),
        );
        if (!mounted) {
          return false;
        }
        if (_controller.actionError != null) {
          AppFeedback.showError(context, _controller.actionError!);
          return false;
        }
        AppFeedback.showSuccess(context, 'Creator share control updated.');
        return true;
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    if (!_isAuthenticated) {
      return Container(
        decoration: gteBackdropDecoration(),
        child: Scaffold(
          backgroundColor: Colors.transparent,
          appBar: AppBar(title: const Text('Creator share control')),
          body: Padding(
            padding: const EdgeInsets.all(20),
            child: GteStatePanel(
              title: 'Sign in required',
              message:
                  'Creator share control is an admin-only surface and requires an authenticated session.',
              actionLabel: widget.onOpenLogin == null ? null : 'Sign in',
              onAction: widget.onOpenLogin,
              icon: Icons.lock_outline,
            ),
          ),
        ),
      );
    }
    if (!_isAdmin) {
      return Container(
        decoration: gteBackdropDecoration(),
        child: Scaffold(
          backgroundColor: Colors.transparent,
          appBar: AppBar(title: const Text('Creator share control')),
          body: const Padding(
            padding: EdgeInsets.all(20),
            child: GteStatePanel(
              title: 'Admin permission required',
              message:
                  'Creator share market control is only exposed to admin roles.',
              icon: Icons.admin_panel_settings_outlined,
            ),
          ),
        ),
      );
    }

    return AnimatedBuilder(
      animation: _controller,
      builder: (BuildContext context, Widget? child) {
        final CreatorClubShareMarketControl? control = _controller.control;
        return Container(
          decoration: gteBackdropDecoration(),
          child: Scaffold(
            backgroundColor: Colors.transparent,
            appBar: AppBar(
              title: const Text('Creator share control'),
              actions: <Widget>[
                IconButton(
                  onPressed: _controller.loadControl,
                  icon: const Icon(Icons.refresh),
                ),
              ],
            ),
            body: RefreshIndicator(
              onRefresh: _controller.loadControl,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
                children: <Widget>[
                  GteSurfacePanel(
                    accentColor: GteShellTheme.accentAdmin,
                    emphasized: true,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: <Widget>[
                        Text(
                          'Creator share market control',
                          style: Theme.of(context).textTheme.headlineSmall,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Issuance and purchase policy remain backend-owned. This screen edits only the canonical admin control surface.',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                        const SizedBox(height: 14),
                        Wrap(
                          spacing: 10,
                          runSpacing: 10,
                          children: <Widget>[
                            GteMetricChip(
                              label: 'Issuance',
                              value: control?.issuanceEnabled == true
                                  ? 'Enabled'
                                  : 'Disabled',
                              positive: control?.issuanceEnabled == true,
                            ),
                            GteMetricChip(
                              label: 'Purchases',
                              value: control?.purchaseEnabled == true
                                  ? 'Enabled'
                                  : 'Disabled',
                              positive: control?.purchaseEnabled == true,
                            ),
                            if (control != null)
                              GteMetricChip(
                                label: 'Revenue bps',
                                value: control.shareholderRevenueShareBps
                                    .toString(),
                              ),
                          ],
                        ),
                        const SizedBox(height: 14),
                        FilledButton.tonalIcon(
                          onPressed: _controller.isLoadingControl
                              ? null
                              : _updateControl,
                          icon: const Icon(Icons.tune_outlined),
                          label: const Text('Update control'),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 18),
                  if (_controller.isLoadingControl && control == null)
                    const GteStatePanel(
                      title: 'Loading creator share control',
                      message:
                          'Issuance, purchase, and revenue-share limits are syncing.',
                      icon: Icons.tune_outlined,
                      isLoading: true,
                    )
                  else if (_controller.controlError != null && control == null)
                    GteStatePanel(
                      title: 'Control unavailable',
                      message: _controller.controlError!,
                      icon: Icons.error_outline,
                    )
                  else if (control != null)
                    GteSurfacePanel(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: <Widget>[
                          Text(
                            'Control snapshot',
                            style: Theme.of(context).textTheme.titleLarge,
                          ),
                          const SizedBox(height: 12),
                          Text(
                            'Max shares per club: ${control.maxSharesPerClub}\n'
                            'Max shares per fan: ${control.maxSharesPerFan}\n'
                            'Shareholder revenue share: ${control.shareholderRevenueShareBps} bps\n'
                            'Max primary purchase value: ${control.maxPrimaryPurchaseValueCoin}',
                            style: Theme.of(context).textTheme.bodyMedium,
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}
