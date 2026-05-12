import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../data/gte_models.dart';
import '../../features/engagement_redesign/engagement_widgets.dart';
import '../../providers/gte_exchange_controller.dart';
import '../../ui_gtex/ui_gtex.dart';

class GtexLiveProfileScreen extends StatefulWidget {
  const GtexLiveProfileScreen({super.key, required this.controller});

  final GteExchangeController controller;

  @override
  State<GtexLiveProfileScreen> createState() => _GtexLiveProfileScreenState();
}

class _GtexLiveProfileScreenState extends State<GtexLiveProfileScreen> {
  _ProfileSection _selected = _ProfileSection.overview;

  @override
  void initState() {
    super.initState();
    _primeAccount();
  }

  Future<void> _primeAccount() async {
    if (!widget.controller.isAuthenticated) {
      return;
    }
    await Future.wait<void>(<Future<void>>[
      widget.controller.refreshAccount(),
      widget.controller.loadOrders(),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: GtexColors.stadiumBlack,
      body: SafeArea(
        child: AnimatedBuilder(
          animation: widget.controller,
          builder: (BuildContext context, _) {
            final GteCurrentUser? user = widget.controller.session?.user;
            if (user == null) {
              return GtexEmptyState(
                title: 'Sign in to open your GTEX profile',
                message:
                    'Your account, KYC, wallet, orders, and club identity live behind the active GTEX session.',
                icon: Icons.account_circle_outlined,
                actionLabel: 'Back to GTEX',
                onAction: () => context.go('/'),
                accent: GtexColors.pitch,
              );
            }

            return GtexMasterDetailScaffold(
              title: 'Profile & Settings',
              subtitle:
                  'Live account command center for identity, trust status, wallet readiness, orders, and support.',
              accent: GtexColors.pitch,
              mobileLeftTitle: 'Profile lanes',
              leftPanel: _ProfileLeftPanel(
                user: user,
                selected: _selected,
                onSelected:
                    (_ProfileSection section) =>
                        setState(() => _selected = section),
              ),
              detail: _ProfileDetail(
                controller: widget.controller,
                user: user,
                section: _selected,
                onRefresh: _primeAccount,
              ),
              rightPanel: _ProfileRightPanel(
                controller: widget.controller,
                user: user,
              ),
              actions: <Widget>[
                IconButton(
                  tooltip: 'Refresh profile',
                  onPressed:
                      widget.controller.isLoadingPortfolio
                          ? null
                          : _primeAccount,
                  icon: const Icon(Icons.refresh),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

enum _ProfileSection {
  overview,
  walletTrust,
  orders,
  security,
  preferences,
  support,
}

extension _ProfileSectionX on _ProfileSection {
  String get label {
    switch (this) {
      case _ProfileSection.overview:
        return 'Overview';
      case _ProfileSection.walletTrust:
        return 'Wallet & KYC';
      case _ProfileSection.orders:
        return 'Orders';
      case _ProfileSection.security:
        return 'Security';
      case _ProfileSection.preferences:
        return 'Preferences';
      case _ProfileSection.support:
        return 'Support';
    }
  }

  String get subtitle {
    switch (this) {
      case _ProfileSection.overview:
        return 'Identity and club status';
      case _ProfileSection.walletTrust:
        return 'Balance, policy, and compliance';
      case _ProfileSection.orders:
        return 'Market order activity';
      case _ProfileSection.security:
        return 'Session and account protection';
      case _ProfileSection.preferences:
        return 'Notifications and interface';
      case _ProfileSection.support:
        return 'Disputes and help desk';
    }
  }

  IconData get icon {
    switch (this) {
      case _ProfileSection.overview:
        return Icons.account_circle_outlined;
      case _ProfileSection.walletTrust:
        return Icons.account_balance_wallet_outlined;
      case _ProfileSection.orders:
        return Icons.receipt_long_outlined;
      case _ProfileSection.security:
        return Icons.security_outlined;
      case _ProfileSection.preferences:
        return Icons.tune_outlined;
      case _ProfileSection.support:
        return Icons.support_agent_outlined;
    }
  }
}

class _ProfileLeftPanel extends StatelessWidget {
  const _ProfileLeftPanel({
    required this.user,
    required this.selected,
    required this.onSelected,
  });

  final GteCurrentUser user;
  final _ProfileSection selected;
  final ValueChanged<_ProfileSection> onSelected;

  @override
  Widget build(BuildContext context) {
    final String display = _displayName(user);
    return ListView(
      padding: const EdgeInsets.all(GtexSpacing.md),
      children: <Widget>[
        GtexPanel(
          accent: GtexColors.pitch,
          title: display,
          subtitle: user.email.isEmpty ? user.username : user.email,
          trailing: CircleAvatar(
            backgroundColor: GtexColors.pitch.withValues(alpha: 0.12),
            foregroundColor: GtexColors.pitch,
            child: Text(_initials(display)),
          ),
          child: Wrap(
            spacing: GtexSpacing.xs,
            runSpacing: GtexSpacing.xs,
            children: <Widget>[
              GtexStatusChip(
                label: user.role.toUpperCase(),
                color: GtexColors.pitch,
                icon: Icons.verified_user_outlined,
              ),
              GtexStatusChip(
                label: (user.kycStatus ?? 'kyc unknown').toUpperCase(),
                color: _kycColor(user.kycStatus),
                icon: Icons.badge_outlined,
              ),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        for (final _ProfileSection section in _ProfileSection.values)
          GtexSectionListTile(
            title: section.label,
            subtitle: section.subtitle,
            icon: section.icon,
            accent: GtexColors.pitch,
            isSelected: selected == section,
            onTap: () => onSelected(section),
          ),
      ],
    );
  }
}

class _ProfileDetail extends StatelessWidget {
  const _ProfileDetail({
    required this.controller,
    required this.user,
    required this.section,
    required this.onRefresh,
  });

  final GteExchangeController controller;
  final GteCurrentUser user;
  final _ProfileSection section;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: onRefresh,
      child: ListView(
        padding: const EdgeInsets.all(GtexSpacing.lg),
        children: <Widget>[
          if (section == _ProfileSection.overview) _overview(context),
          if (section == _ProfileSection.walletTrust) _walletTrust(context),
          if (section == _ProfileSection.orders) _orders(context),
          if (section == _ProfileSection.security) _security(context),
          if (section == _ProfileSection.preferences) _preferences(context),
          if (section == _ProfileSection.support) _support(context),
          const SizedBox(height: GtexSpacing.xl),
        ],
      ),
    );
  }

  Widget _overview(BuildContext context) {
    final String? clubName = _rawString(user.rawJson, <String>[
      'current_club_name',
      'club_name',
      'clubName',
    ]);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        _SectionTitle(title: 'Account overview', icon: section.icon),
        const SizedBox(height: GtexSpacing.md),
        Wrap(
          spacing: GtexSpacing.md,
          runSpacing: GtexSpacing.md,
          children: <Widget>[
            SizedBox(
              width: 220,
              child: GtexMetricTile(
                label: 'Role',
                value: user.role.toUpperCase(),
                helper: user.isActive ? 'Active session' : 'Inactive account',
                icon: Icons.verified_user_outlined,
                accent: GtexColors.pitch,
              ),
            ),
            SizedBox(
              width: 220,
              child: GtexMetricTile(
                label: 'Club',
                value: clubName ?? 'No club linked',
                helper:
                    clubName == null
                        ? 'Create or join a club'
                        : 'Club owner context',
                icon: Icons.shield_outlined,
                accent: GtexColors.cyan,
              ),
            ),
            SizedBox(
              width: 220,
              child: GtexMetricTile(
                label: 'KYC',
                value: (user.kycStatus ?? 'Unknown').toUpperCase(),
                helper: 'Identity status',
                icon: Icons.badge_outlined,
                accent: _kycColor(user.kycStatus),
              ),
            ),
          ],
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Identity record',
          subtitle: 'This is read from the authenticated GTEX user session.',
          accent: GtexColors.pitch,
          child: Column(
            children: <Widget>[
              _InfoRow(label: 'Display name', value: _displayName(user)),
              _InfoRow(label: 'Username', value: user.username),
              _InfoRow(label: 'Email', value: user.email),
              _InfoRow(label: 'Phone', value: user.phoneNumber ?? 'Not added'),
              _InfoRow(label: 'User ID', value: user.id),
            ],
          ),
        ),
      ],
    );
  }

  Widget _walletTrust(BuildContext context) {
    final GteWalletSummary? wallet = controller.walletSummary;
    final GteComplianceStatus? compliance = controller.complianceStatus;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        _SectionTitle(title: 'Wallet and trust', icon: section.icon),
        const SizedBox(height: GtexSpacing.md),
        Wrap(
          spacing: GtexSpacing.md,
          runSpacing: GtexSpacing.md,
          children: <Widget>[
            SizedBox(
              width: 220,
              child: GtexMetricTile(
                label: 'Available',
                value: _balance(wallet?.availableBalance),
                helper: _unit(wallet?.currency),
                icon: Icons.savings_outlined,
                accent: GtexColors.gold,
              ),
            ),
            SizedBox(
              width: 220,
              child: GtexMetricTile(
                label: 'Reserved',
                value: _balance(wallet?.reservedBalance),
                helper: 'Open orders and holds',
                icon: Icons.lock_clock_outlined,
                accent: GtexColors.cyan,
              ),
            ),
            SizedBox(
              width: 220,
              child: GtexMetricTile(
                label: 'Trading',
                value:
                    compliance?.canTradeMarket == false ? 'Blocked' : 'Enabled',
                helper: compliance?.complianceStatus ?? 'Compliance loading',
                icon: Icons.swap_horiz_outlined,
                accent:
                    compliance?.canTradeMarket == false
                        ? GtexColors.red
                        : GtexColors.pitch,
              ),
            ),
          ],
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Compliance state',
          subtitle:
              'Live policy readiness for deposits, withdrawals, and market trading.',
          accent: GtexColors.gold,
          child: Column(
            children: <Widget>[
              _InfoRow(
                label: 'Country bucket',
                value: compliance?.countryPolicyBucket ?? 'Not loaded',
              ),
              _InfoRow(
                label: 'Deposit access',
                value: compliance?.canDeposit == false ? 'Blocked' : 'Enabled',
              ),
              _InfoRow(
                label: 'Reward withdrawals',
                value:
                    compliance?.canWithdrawPlatformRewards == false
                        ? 'Blocked'
                        : 'Enabled',
              ),
              _InfoRow(
                label: 'Missing policies',
                value: '${compliance?.requiredPolicyAcceptancesMissing ?? 0}',
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _orders(BuildContext context) {
    final List<GteOrderRecord> recent = controller.recentOrders;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        _SectionTitle(title: 'Market orders', icon: section.icon),
        const SizedBox(height: GtexSpacing.md),
        Wrap(
          spacing: GtexSpacing.md,
          runSpacing: GtexSpacing.md,
          children: <Widget>[
            SizedBox(
              width: 220,
              child: GtexMetricTile(
                label: 'Recent orders',
                value: '${controller.recentOrderTotal}',
                helper: controller.ordersError ?? 'Live order endpoint',
                icon: Icons.receipt_long_outlined,
                accent: GtexColors.pitch,
              ),
            ),
            SizedBox(
              width: 220,
              child: GtexMetricTile(
                label: 'Open orders',
                value: '${controller.openOrderTotal}',
                helper: 'Cancelable market activity',
                icon: Icons.pending_actions_outlined,
                accent: GtexColors.gold,
              ),
            ),
          ],
        ),
        const SizedBox(height: GtexSpacing.md),
        if (recent.isEmpty)
          GtexEmptyState(
            title: 'No orders loaded',
            message:
                controller.isLoadingOrders
                    ? 'Syncing live market order history.'
                    : 'Market orders will appear here once this account places or receives activity.',
            icon: Icons.receipt_long_outlined,
            accent: GtexColors.pitch,
          )
        else
          for (final GteOrderRecord order in recent.take(12))
            GtexPanel(
              margin: const EdgeInsets.only(bottom: GtexSpacing.sm),
              accent: order.canCancel ? GtexColors.gold : GtexColors.pitch,
              title: '${order.side.name.toUpperCase()} ${order.playerId}',
              subtitle:
                  'Status ${order.status.name} - ${_balance(order.quantity)} units',
              trailing: GtexStatusChip(
                label: order.status.name.toUpperCase(),
                color: order.canCancel ? GtexColors.gold : GtexColors.pitch,
              ),
              child: Column(
                children: <Widget>[
                  _InfoRow(
                    label: 'Reserved',
                    value: _balance(order.reservedAmount),
                  ),
                  _InfoRow(
                    label: 'Max price',
                    value:
                        order.maxPrice == null
                            ? 'Market'
                            : _balance(order.maxPrice),
                  ),
                ],
              ),
            ),
      ],
    );
  }

  Widget _security(BuildContext context) {
    return _SimpleSection(
      title: 'Security',
      icon: section.icon,
      accent: GtexColors.cyan,
      rows: <_SimpleRow>[
        _SimpleRow(
          'Session',
          controller.isAuthenticated ? 'Authenticated' : 'Guest',
        ),
        _SimpleRow('Account active', user.isActive ? 'Yes' : 'No'),
        _SimpleRow(
          'Age confirmation',
          user.ageConfirmedAt == null ? 'Not recorded' : 'Recorded',
        ),
        const _SimpleRow(
          'Password and MFA',
          'Managed through the existing GTEX auth flow.',
        ),
      ],
    );
  }

  Widget _preferences(BuildContext context) {
    return _SimpleSection(
      title: 'Preferences',
      icon: section.icon,
      accent: GtexColors.pitch,
      rows: const <_SimpleRow>[
        _SimpleRow('Interface', 'Premium GTEX command shell'),
        _SimpleRow('Notifications', 'Route available from the top command bar'),
        _SimpleRow(
          'Mobile behavior',
          'Same controller source, drill-down panels',
        ),
      ],
    );
  }

  Widget _support(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        _SectionTitle(title: 'Support', icon: section.icon),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Disputes and help desk',
          subtitle:
              'Live dispute routes remain wired to the existing support APIs.',
          accent: GtexColors.gold,
          child: Wrap(
            spacing: GtexSpacing.sm,
            runSpacing: GtexSpacing.sm,
            children: <Widget>[
              GtexButton(
                label: 'Open disputes',
                icon: Icons.support_agent_outlined,
                onPressed: () => context.go('/disputes'),
              ),
              GtexButton(
                label: 'Open social inbox',
                icon: Icons.mark_chat_unread_outlined,
                variant: GtexButtonVariant.secondary,
                onPressed: () => context.go('/chat'),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _ProfileRightPanel extends StatelessWidget {
  const _ProfileRightPanel({required this.controller, required this.user});

  final GteExchangeController controller;
  final GteCurrentUser user;

  @override
  Widget build(BuildContext context) {
    final GteComplianceStatus? compliance = controller.complianceStatus;
    return ListView(
      padding: const EdgeInsets.all(GtexSpacing.md),
      children: <Widget>[
        GtexPanel(
          title: 'Account readiness',
          subtitle: 'Fast route actions',
          accent: GtexColors.pitch,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: <Widget>[
              GtexStatusChip(
                label:
                    compliance?.canTradeMarket == false
                        ? 'MARKET BLOCKED'
                        : 'MARKET READY',
                color:
                    compliance?.canTradeMarket == false
                        ? GtexColors.red
                        : GtexColors.pitch,
                icon: Icons.swap_horiz_outlined,
              ),
              const SizedBox(height: GtexSpacing.sm),
              GtexButton(
                label: 'Wallet',
                icon: Icons.account_balance_wallet_outlined,
                onPressed: () => context.go('/wallet'),
              ),
              const SizedBox(height: GtexSpacing.xs),
              GtexButton(
                label: 'KYC',
                icon: Icons.badge_outlined,
                variant: GtexButtonVariant.secondary,
                onPressed: () => context.go('/kyc'),
              ),
              const SizedBox(height: GtexSpacing.xs),
              GtexButton(
                label: 'Orders',
                icon: Icons.receipt_long_outlined,
                variant: GtexButtonVariant.secondary,
                onPressed: () => context.go('/orders'),
              ),
              const SizedBox(height: GtexSpacing.xs),
              GtexButton(
                label: 'Support',
                icon: Icons.support_agent_outlined,
                variant: GtexButtonVariant.ghost,
                onPressed: () => context.go('/support'),
              ),
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          title: 'Session',
          subtitle: _displayName(user),
          accent: GtexColors.cyan,
          child: Column(
            children: <Widget>[
              _InfoRow(label: 'Role', value: user.role),
              _InfoRow(label: 'KYC', value: user.kycStatus ?? 'Unknown'),
              _InfoRow(
                label: 'Orders sync',
                value:
                    controller.ordersSyncedAt == null ? 'Not synced' : 'Synced',
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({required this.title, required this.icon});

  final String title;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: <Widget>[
        Icon(icon, color: GtexColors.pitch),
        const SizedBox(width: GtexSpacing.sm),
        Expanded(
          child: Text(
            title,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              color: GtexColors.text,
              fontWeight: FontWeight.w900,
            ),
          ),
        ),
      ],
    );
  }
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: Row(
        children: <Widget>[
          Expanded(
            child: Text(
              label,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                color: GtexColors.textMuted,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
          const SizedBox(width: GtexSpacing.md),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.right,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: GtexColors.text,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _SimpleSection extends StatelessWidget {
  const _SimpleSection({
    required this.title,
    required this.icon,
    required this.accent,
    required this.rows,
  });

  final String title;
  final IconData icon;
  final Color accent;
  final List<_SimpleRow> rows;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        _SectionTitle(title: title, icon: icon),
        const SizedBox(height: GtexSpacing.md),
        GtexPanel(
          accent: accent,
          child: Column(
            children: rows
                .map(
                  (_SimpleRow row) =>
                      _InfoRow(label: row.label, value: row.value),
                )
                .toList(growable: false),
          ),
        ),
      ],
    );
  }
}

class _SimpleRow {
  const _SimpleRow(this.label, this.value);

  final String label;
  final String value;
}

String _displayName(GteCurrentUser user) {
  return (user.displayName?.trim().isNotEmpty ?? false)
      ? user.displayName!.trim()
      : (user.fullName?.trim().isNotEmpty ?? false)
      ? user.fullName!.trim()
      : user.username;
}

String _initials(String value) {
  final List<String> parts =
      value
          .trim()
          .split(RegExp(r'\s+'))
          .where((String item) => item.isNotEmpty)
          .toList();
  if (parts.isEmpty) {
    return 'GT';
  }
  if (parts.length == 1) {
    return parts.first.substring(0, 1).toUpperCase();
  }
  return '${parts.first.substring(0, 1)}${parts.last.substring(0, 1)}'
      .toUpperCase();
}

String? _rawString(Map<String, Object?> json, List<String> keys) {
  for (final String key in keys) {
    final Object? value = json[key];
    if (value is String && value.trim().isNotEmpty) {
      return value.trim();
    }
  }
  return null;
}

Color _kycColor(String? status) {
  switch (status?.toLowerCase()) {
    case 'verified':
    case 'fully_verified':
    case 'fullyverified':
      return GtexColors.pitch;
    case 'pending':
    case 'review':
      return GtexColors.gold;
    case 'rejected':
      return GtexColors.red;
    default:
      return GtexColors.cyan;
  }
}

String _balance(double? value) {
  if (value == null) {
    return '0';
  }
  return value.abs() >= 1000
      ? value.toStringAsFixed(0)
      : value.toStringAsFixed(2);
}

String _unit(GteLedgerUnit? unit) {
  switch (unit) {
    case GteLedgerUnit.credit:
      return 'GTEX credit';
    case GteLedgerUnit.coin:
      return 'GTEX coin';
    case GteLedgerUnit.unknown:
    case null:
      return 'GTEX balance';
  }
}
