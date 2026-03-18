import 'package:flutter/material.dart';

import '../../../core/app_feedback.dart';
import '../../../data/gte_api_repository.dart';
import '../../../widgets/gte_formatters.dart';
import '../../../widgets/gte_metric_chip.dart';
import '../../../widgets/gte_shell_theme.dart';
import '../../../widgets/gte_state_panel.dart';
import '../../../widgets/gte_surface_panel.dart';
import '../../../widgets/gtex_branding.dart';
import '../data/creator_share_market_models.dart';
import 'creator_share_market_controller.dart';

class CreatorShareMarketScreen extends StatefulWidget {
  const CreatorShareMarketScreen({
    super.key,
    this.clubId,
    this.clubName,
    required this.baseUrl,
    required this.backendMode,
    this.accessToken,
    this.currentClubId,
    this.currentUserRole,
    this.onOpenLogin,
  });

  final String? clubId;
  final String? clubName;
  final String baseUrl;
  final GteBackendMode backendMode;
  final String? accessToken;
  final String? currentClubId;
  final String? currentUserRole;
  final VoidCallback? onOpenLogin;

  @override
  State<CreatorShareMarketScreen> createState() =>
      _CreatorShareMarketScreenState();
}

class _CreatorShareMarketScreenState extends State<CreatorShareMarketScreen> {
  late final CreatorShareMarketController _controller;
  late final TextEditingController _clubLookupController;

  bool get _hasAuth => widget.accessToken?.trim().isNotEmpty == true;
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
    _clubLookupController = TextEditingController(text: widget.clubId ?? '');
    if (widget.clubId != null && _hasAuth) {
      _load(widget.clubId!);
    }
    if (_isAdmin && _hasAuth) {
      _controller.loadControl();
    }
  }

  @override
  void dispose() {
    _clubLookupController.dispose();
    _controller.dispose();
    super.dispose();
  }

  Future<void> _load(String clubId) async {
    await _controller.loadMarket(clubId);
    if (_isAdmin) {
      await _controller.loadControl();
    }
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (BuildContext context, Widget? child) {
        return Container(
          decoration: gteBackdropDecoration(),
          child: Scaffold(
            backgroundColor: Colors.transparent,
            appBar: AppBar(
              title: Text(
                widget.clubId == null
                    ? 'Creator share market'
                    : '${widget.clubName ?? widget.clubId} creator shares',
              ),
              actions: <Widget>[
                IconButton(
                  onPressed: widget.clubId == null || !_hasAuth
                      ? null
                      : () => _load(widget.clubId!),
                  icon: const Icon(Icons.refresh),
                ),
              ],
            ),
            body: widget.clubId == null
                ? _buildBrowseView(context)
                : _buildClubView(context, widget.clubId!),
          ),
        );
      },
    );
  }

  Widget _buildBrowseView(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
      children: <Widget>[
        GtexHeroBanner(
          eyebrow: 'CREATOR SHARE MARKET',
          title:
              'Ownership, governance policy, and fan benefits sit on one ledger.',
          description:
              'This market reads the canonical share market, creator-controlled shares, and preserved ownership ledger from the backend. There is no parallel client-side valuation or treasury logic here.',
          accent: const Color(0xFF79D8C3),
          chips: <Widget>[
            GteMetricChip(
              label: 'Session',
              value: _hasAuth ? 'LIVE' : 'LOGIN',
              positive: _hasAuth,
            ),
            if (_isAdmin)
              const GteMetricChip(
                label: 'Role',
                value: 'ADMIN',
                positive: true,
              ),
          ],
          actions: <Widget>[
            if (widget.currentClubId?.isNotEmpty == true && _hasAuth)
              FilledButton.icon(
                onPressed: () => _openClub(context, widget.currentClubId!),
                icon: const Icon(Icons.shield_outlined),
                label: const Text('Open my club'),
              ),
            if (!_hasAuth && widget.onOpenLogin != null)
              FilledButton.tonalIcon(
                onPressed: widget.onOpenLogin,
                icon: const Icon(Icons.login),
                label: const Text('Sign in'),
              ),
          ],
          sidePanel: Column(
            children: <Widget>[
              TextField(
                controller: _clubLookupController,
                decoration: const InputDecoration(
                  labelText: 'Open club by id',
                  hintText: 'club-123',
                ),
              ),
              const SizedBox(height: 12),
              FilledButton.tonalIcon(
                onPressed: _hasAuth
                    ? () =>
                        _openClub(context, _clubLookupController.text.trim())
                    : widget.onOpenLogin,
                icon: const Icon(Icons.open_in_new),
                label: Text(_hasAuth ? 'Open market' : 'Sign in to open'),
              ),
            ],
          ),
        ),
        const SizedBox(height: 20),
        if (!_hasAuth)
          GteStatePanel(
            title: 'Sign in required',
            message:
                'The creator share market is authenticated because it includes viewer holdings, benefits, and purchase access.',
            actionLabel: widget.onOpenLogin == null ? null : 'Sign in',
            onAction: widget.onOpenLogin,
            icon: Icons.lock_outline,
          )
        else
          const GteStatePanel(
            title: 'Choose a club',
            message:
                'Open a creator club by id or jump straight into your current club share market from the button above.',
            icon: Icons.account_balance_outlined,
          ),
      ],
    );
  }

  Widget _buildClubView(BuildContext context, String clubId) {
    if (!_hasAuth) {
      return Padding(
        padding: const EdgeInsets.all(20),
        child: GteStatePanel(
          title: 'Sign in required',
          message:
              'Creator share holdings, benefits, and purchases are only available to authenticated users.',
          actionLabel: widget.onOpenLogin == null ? null : 'Sign in',
          onAction: widget.onOpenLogin,
          icon: Icons.lock_outline,
        ),
      );
    }

    final CreatorClubShareMarket? market = _controller.market;
    final CreatorClubShareHolding? holding = _controller.holding;
    final CreatorClubShareMarketControl? control = _controller.control;
    final bool canIssue = widget.currentClubId == clubId;

    if (_controller.isLoadingMarket && market == null) {
      return const Padding(
        padding: EdgeInsets.all(20),
        child: GteStatePanel(
          title: 'Loading share market',
          message:
              'Holdings, benefits, governance policy, and distribution history are loading.',
          icon: Icons.candlestick_chart,
          isLoading: true,
        ),
      );
    }

    if (_controller.marketError != null && market == null && !canIssue) {
      return Padding(
        padding: const EdgeInsets.all(20),
        child: GteStatePanel(
          title: 'Creator share market unavailable',
          message: _controller.marketError!,
          actionLabel: 'Retry',
          onAction: () => _load(clubId),
          icon: Icons.candlestick_chart,
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () => _load(clubId),
      child: ListView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
        children: <Widget>[
          GteSurfacePanel(
            emphasized: true,
            accentColor: const Color(0xFF79D8C3),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  widget.clubName ?? clubId,
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                const SizedBox(height: 8),
                Text(
                  market == null
                      ? 'No fan-share issuance is live for this club yet.'
                      : 'Read share price, creator control, holder benefits, governance limits, and revenue distributions from one canonical surface.',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 14),
                Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  children: <Widget>[
                    GteMetricChip(
                      label: 'Share price',
                      value: market == null
                          ? '--'
                          : gteFormatCredits(market.sharePriceCoin),
                    ),
                    GteMetricChip(
                      label: 'Remaining',
                      value: market == null
                          ? '--'
                          : market.sharesRemaining.toString(),
                    ),
                    GteMetricChip(
                      label: 'Creator control',
                      value: market == null
                          ? '--'
                          : '${market.creatorControlledShares} (${(market.creatorControlBps / 100).toStringAsFixed(1)}%)',
                    ),
                    GteMetricChip(
                      label: 'Shareholders',
                      value: market == null
                          ? '--'
                          : market.shareholderCount.toString(),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Wrap(
                  spacing: 12,
                  runSpacing: 12,
                  children: <Widget>[
                    if (market != null)
                      FilledButton.icon(
                        onPressed: () =>
                            _showPurchaseDialog(context, clubId, market),
                        icon: const Icon(Icons.shopping_cart_checkout_outlined),
                        label: const Text('Buy shares'),
                      ),
                    if (market == null && canIssue)
                      FilledButton.tonalIcon(
                        onPressed: () => _showIssueDialog(context, clubId),
                        icon: const Icon(Icons.add_chart_outlined),
                        label: const Text('Issue market'),
                      ),
                    if (_isAdmin)
                      OutlinedButton.icon(
                        onPressed: control == null
                            ? () => _controller.loadControl()
                            : () => _showControlDialog(context, control),
                        icon: const Icon(Icons.admin_panel_settings_outlined),
                        label: Text(
                          control == null
                              ? 'Load admin control'
                              : 'Edit admin control',
                        ),
                      ),
                  ],
                ),
              ],
            ),
          ),
          if (_controller.actionError != null) ...<Widget>[
            const SizedBox(height: 16),
            GteSurfacePanel(
              child: Text(
                _controller.actionError!,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ),
          ],
          const SizedBox(height: 18),
          if (market == null)
            GteStatePanel(
              title: canIssue
                  ? 'No market issued yet'
                  : 'No creator share market is live',
              message: canIssue
                  ? 'Issue the primary share market for this club to expose price, supply, governance, and holder benefits.'
                  : 'This club has not issued creator shares yet.',
              actionLabel: canIssue ? 'Issue market' : null,
              onAction:
                  canIssue ? () => _showIssueDialog(context, clubId) : null,
              icon: Icons.account_balance_outlined,
            )
          else ...<Widget>[
            _MarketSnapshotSection(
              market: market,
              holding: holding,
            ),
            const SizedBox(height: 18),
            _GovernanceSection(market: market),
            const SizedBox(height: 18),
            _DistributionSection(distributions: _controller.distributions),
          ],
          if (_isAdmin) ...<Widget>[
            const SizedBox(height: 18),
            _AdminControlSection(
              control: control,
              isLoading: _controller.isLoadingControl,
              error: _controller.controlError,
              onEdit: control == null
                  ? null
                  : () => _showControlDialog(context, control),
              onRetry: _controller.loadControl,
            ),
          ],
        ],
      ),
    );
  }

  Future<void> _showIssueDialog(BuildContext context, String clubId) async {
    final TextEditingController priceController = TextEditingController();
    final TextEditingController maxSharesController =
        TextEditingController(text: '1000');
    final TextEditingController maxPerFanController =
        TextEditingController(text: '25');
    final bool? submitted = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (BuildContext context) {
        return Padding(
          padding: EdgeInsets.fromLTRB(
            20,
            20,
            20,
            20 + MediaQuery.of(context).viewInsets.bottom,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Issue creator share market',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: priceController,
                keyboardType:
                    const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(labelText: 'Share price'),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: maxSharesController,
                keyboardType: TextInputType.number,
                decoration:
                    const InputDecoration(labelText: 'Max shares issued'),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: maxPerFanController,
                keyboardType: TextInputType.number,
                decoration:
                    const InputDecoration(labelText: 'Max shares per fan'),
              ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: () async {
                  final double? sharePrice =
                      double.tryParse(priceController.text.trim());
                  final int? maxShares =
                      int.tryParse(maxSharesController.text.trim());
                  final int? maxPerFan =
                      int.tryParse(maxPerFanController.text.trim());
                  if (sharePrice == null ||
                      sharePrice <= 0 ||
                      maxShares == null ||
                      maxShares <= 0) {
                    AppFeedback.showError(
                      context,
                      'Enter valid issuance values.',
                    );
                    return;
                  }
                  await _controller.issueMarket(
                    clubId,
                    CreatorClubShareMarketIssueRequest(
                      sharePriceCoin: sharePrice,
                      maxSharesIssued: maxShares,
                      maxSharesPerFan: maxPerFan,
                    ),
                  );
                  if (!mounted || _controller.actionError != null) {
                    return;
                  }
                  Navigator.of(context).pop(true);
                },
                child: const Text('Issue market'),
              ),
            ],
          ),
        );
      },
    );
    priceController.dispose();
    maxSharesController.dispose();
    maxPerFanController.dispose();
    if (submitted == true && mounted) {
      AppFeedback.showSuccess(context, 'Creator share market issued.');
    }
  }

  Future<void> _showPurchaseDialog(
    BuildContext context,
    String clubId,
    CreatorClubShareMarket market,
  ) async {
    final TextEditingController shareCountController =
        TextEditingController(text: '1');
    final bool? submitted = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (BuildContext context) {
        return Padding(
          padding: EdgeInsets.fromLTRB(
            20,
            20,
            20,
            20 + MediaQuery.of(context).viewInsets.bottom,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Buy creator shares',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 10),
              Text(
                'Share price: ${gteFormatCredits(market.sharePriceCoin)} â€¢ Remaining supply: ${market.sharesRemaining}',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: shareCountController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'Share count'),
              ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: () async {
                  final int? count =
                      int.tryParse(shareCountController.text.trim());
                  if (count == null || count <= 0) {
                    AppFeedback.showError(
                      context,
                      'Enter a valid share count.',
                    );
                    return;
                  }
                  await _controller.purchaseShares(
                    clubId,
                    CreatorClubSharePurchaseRequest(shareCount: count),
                  );
                  if (!mounted || _controller.actionError != null) {
                    return;
                  }
                  Navigator.of(context).pop(true);
                },
                child: const Text('Purchase shares'),
              ),
            ],
          ),
        );
      },
    );
    shareCountController.dispose();
    if (submitted == true && mounted) {
      AppFeedback.showSuccess(context, 'Share purchase submitted.');
    }
  }

  Future<void> _showControlDialog(
    BuildContext context,
    CreatorClubShareMarketControl control,
  ) async {
    final TextEditingController maxClubController = TextEditingController(
      text: control.maxSharesPerClub.toString(),
    );
    final TextEditingController maxFanController = TextEditingController(
      text: control.maxSharesPerFan.toString(),
    );
    final TextEditingController revenueShareController = TextEditingController(
      text: control.shareholderRevenueShareBps.toString(),
    );
    final TextEditingController maxPurchaseController = TextEditingController(
      text: control.maxPrimaryPurchaseValueCoin.toStringAsFixed(2),
    );
    bool issuanceEnabled = control.issuanceEnabled;
    bool purchaseEnabled = control.purchaseEnabled;
    final bool? submitted = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (BuildContext context) {
        return Padding(
          padding: EdgeInsets.fromLTRB(
            20,
            20,
            20,
            20 + MediaQuery.of(context).viewInsets.bottom,
          ),
          child: StatefulBuilder(
            builder: (BuildContext context,
                void Function(void Function()) setModalState) {
              return Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    'Edit share market control',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: maxClubController,
                    keyboardType: TextInputType.number,
                    decoration:
                        const InputDecoration(labelText: 'Max shares per club'),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: maxFanController,
                    keyboardType: TextInputType.number,
                    decoration:
                        const InputDecoration(labelText: 'Max shares per fan'),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: revenueShareController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Shareholder revenue share (bps)',
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: maxPurchaseController,
                    keyboardType:
                        const TextInputType.numberWithOptions(decimal: true),
                    decoration: const InputDecoration(
                      labelText: 'Max primary purchase value',
                    ),
                  ),
                  SwitchListTile(
                    value: issuanceEnabled,
                    onChanged: (bool value) {
                      setModalState(() => issuanceEnabled = value);
                    },
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Issuance enabled'),
                  ),
                  SwitchListTile(
                    value: purchaseEnabled,
                    onChanged: (bool value) {
                      setModalState(() => purchaseEnabled = value);
                    },
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Purchase enabled'),
                  ),
                  const SizedBox(height: 16),
                  FilledButton(
                    onPressed: () async {
                      final int? maxClub =
                          int.tryParse(maxClubController.text.trim());
                      final int? maxFan =
                          int.tryParse(maxFanController.text.trim());
                      final int? revenueShare =
                          int.tryParse(revenueShareController.text.trim());
                      final double? maxPurchase =
                          double.tryParse(maxPurchaseController.text.trim());
                      if (maxClub == null ||
                          maxFan == null ||
                          revenueShare == null ||
                          maxPurchase == null) {
                        AppFeedback.showError(
                          context,
                          'Enter valid control values.',
                        );
                        return;
                      }
                      await _controller.updateControl(
                        CreatorClubShareMarketControlUpdateRequest(
                          maxSharesPerClub: maxClub,
                          maxSharesPerFan: maxFan,
                          shareholderRevenueShareBps: revenueShare,
                          issuanceEnabled: issuanceEnabled,
                          purchaseEnabled: purchaseEnabled,
                          maxPrimaryPurchaseValueCoin: maxPurchase,
                        ),
                      );
                      if (!mounted || _controller.actionError != null) {
                        return;
                      }
                      Navigator.of(context).pop(true);
                    },
                    child: const Text('Save control'),
                  ),
                ],
              );
            },
          ),
        );
      },
    );
    maxClubController.dispose();
    maxFanController.dispose();
    revenueShareController.dispose();
    maxPurchaseController.dispose();
    if (submitted == true && mounted) {
      AppFeedback.showSuccess(context, 'Share market control updated.');
    }
  }

  void _openClub(BuildContext context, String clubId) {
    if (clubId.trim().isEmpty) {
      AppFeedback.showError(context, 'Enter a club id.');
      return;
    }
    Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (BuildContext context) => CreatorShareMarketScreen(
          clubId: clubId.trim(),
          clubName:
              widget.currentClubId == clubId.trim() ? widget.clubName : null,
          baseUrl: widget.baseUrl,
          backendMode: widget.backendMode,
          accessToken: widget.accessToken,
          currentClubId: widget.currentClubId,
          currentUserRole: widget.currentUserRole,
          onOpenLogin: widget.onOpenLogin,
        ),
      ),
    );
  }
}

class _MarketSnapshotSection extends StatelessWidget {
  const _MarketSnapshotSection({
    required this.market,
    required this.holding,
  });

  final CreatorClubShareMarket market;
  final CreatorClubShareHolding? holding;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Holder snapshot',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <Widget>[
              GteMetricChip(
                label: 'Viewer holding',
                value: holding == null ? '0' : holding!.shareCount.toString(),
              ),
              GteMetricChip(
                label: 'Revenue distributed',
                value: gteFormatCredits(market.totalRevenueDistributedCoin),
              ),
              GteMetricChip(
                label: 'Purchase volume',
                value: gteFormatCredits(market.totalPurchaseVolumeCoin),
              ),
              GteMetricChip(
                label: 'Benefits',
                value: market.viewerBenefits.shareholder ? 'ACTIVE' : 'NONE',
                positive: market.viewerBenefits.shareholder,
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            'Priority chat visibility: ${market.viewerBenefits.hasPriorityChatVisibility ? 'enabled' : 'disabled'} â€¢ Early ticket access: ${market.viewerBenefits.hasEarlyTicketAccess ? 'enabled' : 'disabled'} â€¢ Cosmetic voting: ${market.viewerBenefits.hasCosmeticVotingRights ? 'enabled' : 'disabled'}',
            style: Theme.of(context).textTheme.bodyMedium,
          ),
        ],
      ),
    );
  }
}

class _GovernanceSection extends StatelessWidget {
  const _GovernanceSection({
    required this.market,
  });

  final CreatorClubShareMarket market;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Governance and ownership ledger',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: <Widget>[
              GteMetricChip(
                label: 'Mode',
                value: market.governancePolicy.governanceMode.toUpperCase(),
              ),
              GteMetricChip(
                label: 'Quorum bps',
                value: market.governancePolicy.quorumShareBps.toString(),
              ),
              GteMetricChip(
                label: 'Proposal threshold',
                value:
                    market.governancePolicy.proposalShareThreshold.toString(),
              ),
              GteMetricChip(
                label: 'Anti-takeover',
                value:
                    market.governancePolicy.antiTakeoverEnabled ? 'ON' : 'OFF',
                positive: market.governancePolicy.antiTakeoverEnabled,
              ),
            ],
          ),
          const SizedBox(height: 16),
          if (market.ownershipLedger.recentEntries.isEmpty)
            const Text('No recent ledger movements yet.')
          else
            ...market.ownershipLedger.recentEntries.take(5).map(
                  (CreatorClubOwnershipLedgerEntry entry) => ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.account_balance_outlined),
                    title: Text(entry.summary),
                    subtitle: Text(
                      '${entry.entryType} â€¢ ${gteFormatDateTime(entry.createdAt)}',
                    ),
                    trailing: Text(
                      '${entry.shareDelta >= 0 ? '+' : ''}${entry.shareDelta}',
                    ),
                  ),
                ),
        ],
      ),
    );
  }
}

class _DistributionSection extends StatelessWidget {
  const _DistributionSection({
    required this.distributions,
  });

  final List<CreatorClubShareDistribution> distributions;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            'Revenue distributions',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 12),
          if (distributions.isEmpty)
            const Text('No distributions have settled yet.')
          else
            ...distributions.take(5).map(
                  (CreatorClubShareDistribution distribution) => ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.payments_outlined),
                    title: Text(gteFormatCredits(distribution.totalPayoutCoin)),
                    subtitle: Text(
                      'Funded by ${distribution.sourceType} â€¢ ${gteFormatDateTime(distribution.createdAt)}',
                    ),
                  ),
                ),
        ],
      ),
    );
  }
}

class _AdminControlSection extends StatelessWidget {
  const _AdminControlSection({
    required this.control,
    required this.isLoading,
    required this.error,
    required this.onEdit,
    required this.onRetry,
  });

  final CreatorClubShareMarketControl? control;
  final bool isLoading;
  final String? error;
  final VoidCallback? onEdit;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    if (isLoading && control == null) {
      return const GteStatePanel(
        title: 'Loading admin control',
        message: 'Canonical market limits and issuance controls are loading.',
        icon: Icons.admin_panel_settings_outlined,
        isLoading: true,
      );
    }
    return GteSurfacePanel(
      accentColor: const Color(0xFFF0A94E),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Text(
                  'Admin market control',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
              if (control != null)
                OutlinedButton.icon(
                  onPressed: onEdit,
                  icon: const Icon(Icons.edit_outlined),
                  label: const Text('Edit'),
                )
              else
                OutlinedButton.icon(
                  onPressed: onRetry,
                  icon: const Icon(Icons.refresh),
                  label: const Text('Retry'),
                ),
            ],
          ),
          if (error != null) ...<Widget>[
            const SizedBox(height: 8),
            Text(error!, style: Theme.of(context).textTheme.bodyMedium),
          ],
          if (control != null) ...<Widget>[
            const SizedBox(height: 12),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: <Widget>[
                GteMetricChip(
                  label: 'Club cap',
                  value: control!.maxSharesPerClub.toString(),
                ),
                GteMetricChip(
                  label: 'Fan cap',
                  value: control!.maxSharesPerFan.toString(),
                ),
                GteMetricChip(
                  label: 'Revenue share bps',
                  value: control!.shareholderRevenueShareBps.toString(),
                ),
                GteMetricChip(
                  label: 'Max purchase',
                  value: gteFormatCredits(control!.maxPrimaryPurchaseValueCoin),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

