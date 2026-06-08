import 'package:flutter/material.dart';

import '../../shell/domain/gtex_surface_state.dart';
import '../../shell/widgets/gtex_state_panel.dart';
import '../data/creator_dtos.dart';

class CreatorStudioScreen extends StatelessWidget {
  const CreatorStudioScreen({
    super.key,
    required this.profile,
    required this.campaigns,
    required this.clips,
    required this.analytics,
    required this.wallet,
    required this.settlements,
    required this.moderation,
  });

  final CreatorSurfaceState<CreatorProfileDto> profile;
  final CreatorSurfaceState<List<CampaignDto>> campaigns;
  final CreatorSurfaceState<List<SponsoredClipDto>> clips;
  final CreatorSurfaceState<CreatorAnalyticsDto> analytics;
  final CreatorSurfaceState<CreatorWalletDto> wallet;
  final CreatorSurfaceState<List<SettlementDto>> settlements;
  final CreatorSurfaceState<List<ModerationInboxItemDto>> moderation;

  @override
  Widget build(BuildContext context) {
    final CreatorProfileDto? creator = profile.data;
    if (profile.isBlocked || creator == null) {
      return GtexStatePanel(
        state: GtexSurfaceState.blocked,
        title: 'Creator studio blocked',
        message: profile.blockedReason ?? profile.message,
        icon: Icons.lock_outline_rounded,
      );
    }

    return ListView(
      padding: const EdgeInsets.all(16),
      children: <Widget>[
        _SectionHeader(
          title: 'Creator studio',
          subtitle: creator.displayName,
          state: creator.verificationStatus.surfaceState,
          badgeLabel: creator.verificationStatus.label,
        ),
        const SizedBox(height: 12),
        CreatorWalletCard(wallet: wallet),
        const SizedBox(height: 12),
        CampaignSummaryRow(campaigns: campaigns),
        const SizedBox(height: 12),
        ModerationInboxBadge(moderation: moderation),
        const SizedBox(height: 12),
        _ContractPanel(
          title: 'Sponsored clips',
          state: clips.state,
          message: clips.message,
          value: '${clips.data?.length ?? 0} clips',
          icon: Icons.smart_display_outlined,
        ),
        const SizedBox(height: 12),
        _ContractPanel(
          title: 'Settlements',
          state: settlements.state,
          message: settlements.message,
          value: _settlementLabel(settlements.data),
          icon: Icons.receipt_long_outlined,
        ),
        const SizedBox(height: 12),
        _ContractPanel(
          title: 'Audience analytics',
          state: analytics.state,
          message: analytics.message,
          value: _analyticsLabel(analytics.data),
          icon: Icons.groups_2_outlined,
        ),
        const SizedBox(height: 12),
        _ContractPanel(
          title: 'Referrals',
          state: GtexSurfaceState.blocked,
          message:
              'Creator referral actions stay blocked on this surface until a creator-scoped referral dashboard contract is mounted.',
          value: 'Referral dashboard blocked',
          icon: Icons.link_outlined,
        ),
        const SizedBox(height: 12),
        _QuickNavGrid(
          items: const <_QuickNavItem>[
            _QuickNavItem(Icons.campaign_outlined, 'Campaigns'),
            _QuickNavItem(Icons.smart_display_outlined, 'Clips'),
            _QuickNavItem(Icons.analytics_outlined, 'Analytics'),
            _QuickNavItem(Icons.account_balance_wallet_outlined, 'Wallet'),
            _QuickNavItem(Icons.receipt_long_outlined, 'Settlements'),
            _QuickNavItem(Icons.link_outlined, 'Referrals'),
          ],
        ),
      ],
    );
  }

  String _analyticsLabel(CreatorAnalyticsDto? value) {
    if (value == null) {
      return 'analytics unavailable';
    }
    final int? views = value.totalViews;
    if (views == null) {
      return 'analytics degraded';
    }
    return '$views views';
  }

  String _settlementLabel(List<SettlementDto>? value) {
    if (value == null) {
      return 'settlements unavailable';
    }
    if (value.isEmpty) {
      return '0 settlements';
    }
    final int degraded =
        value.where((SettlementDto item) => item.degradedReason != null).length;
    return degraded == 0
        ? '${value.length} settlements'
        : '${value.length} settlements / $degraded degraded';
  }
}

class CreatorWalletCard extends StatelessWidget {
  const CreatorWalletCard({super.key, required this.wallet, this.onWithdraw});

  final CreatorSurfaceState<CreatorWalletDto> wallet;
  final VoidCallback? onWithdraw;

  @override
  Widget build(BuildContext context) {
    final CreatorWalletDto? data = wallet.data;
    final WalletBalanceDto? balance = data?.balance;
    final bool withdrawalAvailable = data?.withdrawalAvailable ?? false;
    if (wallet.isBlocked || balance == null) {
      return _ContractPanel(
        title: 'Creator wallet blocked',
        state: GtexSurfaceState.blocked,
        message:
            wallet.blockedReason ??
            'Backend available balance is missing; withdrawals stay disabled.',
        value: 'Balance blocked',
        icon: Icons.lock_outline_rounded,
      );
    }

    return _SurfaceCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              const Icon(Icons.account_balance_wallet_outlined),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  'Creator wallet',
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
              const _StateChip(
                state: GtexSurfaceState.confirmed,
                label: 'Backend balance',
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            '${balance.available.toStringAsFixed(2)} ${balance.currency}',
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 4),
          Text('Pending settlements ${data?.pendingSettlements ?? 0}'),
          const SizedBox(height: 4),
          Text(
            withdrawalAvailable
                ? 'Withdrawals are available only through backend payout review.'
                : 'Withdrawals blocked until backend confirms payout availability.',
          ),
          const SizedBox(height: 12),
          FilledButton.icon(
            onPressed:
                withdrawalAvailable && onWithdraw != null ? onWithdraw : null,
            icon: const Icon(Icons.payments_outlined),
            label: Text(
              withdrawalAvailable ? 'Request withdrawal' : 'Withdrawal blocked',
            ),
          ),
        ],
      ),
    );
  }
}

class CampaignSummaryRow extends StatelessWidget {
  const CampaignSummaryRow({super.key, required this.campaigns});

  final CreatorSurfaceState<List<CampaignDto>> campaigns;

  @override
  Widget build(BuildContext context) {
    final List<CampaignDto> items = campaigns.data ?? const <CampaignDto>[];
    final int active =
        items
            .where((CampaignDto item) => item.status == CampaignStatus.active)
            .length;
    return _ContractPanel(
      title: 'Campaigns',
      state: campaigns.state,
      message: campaigns.message,
      value: '$active active / ${items.length} total',
      icon: Icons.campaign_outlined,
    );
  }
}

class ModerationInboxBadge extends StatelessWidget {
  const ModerationInboxBadge({super.key, required this.moderation});

  final CreatorSurfaceState<List<ModerationInboxItemDto>> moderation;

  @override
  Widget build(BuildContext context) {
    final List<ModerationInboxItemDto> items =
        moderation.data ?? const <ModerationInboxItemDto>[];
    final int attention =
        items
            .where(
              (ModerationInboxItemDto item) =>
                  item.status == ClipModerationStatus.flagged ||
                  item.status == ClipModerationStatus.rejected,
            )
            .length;
    return _ContractPanel(
      title: 'Moderation inbox',
      state: moderation.state,
      message: moderation.message,
      value: '$attention need attention',
      icon: Icons.policy_outlined,
    );
  }
}

class ClipModerationStatusCard extends StatelessWidget {
  const ClipModerationStatusCard({super.key, required this.clip});

  final SponsoredClipDto clip;

  @override
  Widget build(BuildContext context) {
    return _SurfaceCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              const Icon(Icons.smart_display_outlined),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  clip.title,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
              ),
              _StateChip(
                state: clip.status.surfaceState,
                label: clip.status.label,
              ),
            ],
          ),
          if ((clip.moderationNote ?? '').trim().isNotEmpty) ...<Widget>[
            const SizedBox(height: 10),
            Text(clip.moderationNote!),
          ],
          const SizedBox(height: 10),
          Text(clip.status.creatorActionLabel),
          if (clip.canShowPerformance && clip.viewCount != null) ...<Widget>[
            const SizedBox(height: 8),
            Text('${clip.viewCount} views'),
          ],
        ],
      ),
    );
  }
}

class _ContractPanel extends StatelessWidget {
  const _ContractPanel({
    required this.title,
    required this.state,
    required this.message,
    required this.value,
    required this.icon,
  });

  final String title;
  final GtexSurfaceState state;
  final String message;
  final String value;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return _SurfaceCard(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Icon(icon),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Row(
                  children: <Widget>[
                    Expanded(
                      child: Text(
                        title,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                    ),
                    _StateChip(state: state, label: _stateLabel(state)),
                  ],
                ),
                const SizedBox(height: 8),
                Text(value),
                const SizedBox(height: 4),
                Text(message, style: Theme.of(context).textTheme.bodySmall),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({
    required this.title,
    required this.subtitle,
    required this.state,
    required this.badgeLabel,
  });

  final String title;
  final String subtitle;
  final GtexSurfaceState state;
  final String badgeLabel;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: <Widget>[
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(title, style: Theme.of(context).textTheme.headlineSmall),
              const SizedBox(height: 4),
              Text(subtitle),
            ],
          ),
        ),
        _StateChip(state: state, label: badgeLabel),
      ],
    );
  }
}

class _QuickNavGrid extends StatelessWidget {
  const _QuickNavGrid({required this.items});

  final List<_QuickNavItem> items;

  @override
  Widget build(BuildContext context) {
    return GridView.count(
      crossAxisCount: MediaQuery.sizeOf(context).width < 560 ? 2 : 4,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: 8,
      crossAxisSpacing: 8,
      childAspectRatio: 2.4,
      children: <Widget>[
        for (final _QuickNavItem item in items)
          _SurfaceCard(
            child: Row(
              children: <Widget>[
                Icon(item.icon),
                const SizedBox(width: 8),
                Expanded(child: Text(item.label)),
              ],
            ),
          ),
      ],
    );
  }
}

class _QuickNavItem {
  const _QuickNavItem(this.icon, this.label);

  final IconData icon;
  final String label;
}

class _SurfaceCard extends StatelessWidget {
  const _SurfaceCard({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final ColorScheme scheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: scheme.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: scheme.outlineVariant),
      ),
      child: child,
    );
  }
}

class _StateChip extends StatelessWidget {
  const _StateChip({required this.state, required this.label});

  final GtexSurfaceState state;
  final String label;

  @override
  Widget build(BuildContext context) {
    final Color tone = gtexSurfaceToneFor(Theme.of(context), state);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        color: tone.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: tone.withValues(alpha: 0.28)),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
          color: tone,
          fontWeight: FontWeight.w800,
        ),
      ),
    );
  }
}

String _stateLabel(GtexSurfaceState state) {
  return switch (state) {
    GtexSurfaceState.loading => 'Loading',
    GtexSurfaceState.empty => 'Empty',
    GtexSurfaceState.blocked => 'Blocked',
    GtexSurfaceState.pending => 'Pending',
    GtexSurfaceState.syncing => 'Syncing',
    GtexSurfaceState.reconnecting => 'Reconnecting',
    GtexSurfaceState.degraded => 'Degraded',
    GtexSurfaceState.confirmed => 'Live',
    GtexSurfaceState.error => 'Error',
  };
}
