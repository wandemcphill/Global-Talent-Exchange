import 'package:flutter/material.dart';

import '../../../core/constants/app_spacing.dart';
import '../../../models/creator_models.dart';
import '../../../widgets/gte_formatters.dart';
import '../../../widgets/gte_shell_theme.dart';
import '../../../widgets/gte_state_panel.dart';
import '../../../widgets/gte_surface_panel.dart';

class CreatorCanonicalSurface extends StatelessWidget {
  const CreatorCanonicalSurface({
    super.key,
    required this.profile,
    required this.finance,
    required this.isAuthenticated,
    required this.hasApprovedCreatorAccess,
    this.syncedAt,
    this.isSyncing = false,
    this.onOpenLogin,
    this.onOpenCreatorAccessRequest,
  });

  final CreatorProfile profile;
  final CreatorFinanceSummary? finance;
  final bool isAuthenticated;
  final bool hasApprovedCreatorAccess;
  final DateTime? syncedAt;
  final bool isSyncing;
  final VoidCallback? onOpenLogin;
  final VoidCallback? onOpenCreatorAccessRequest;

  @override
  Widget build(BuildContext context) {
    if (!isAuthenticated) {
      return GteStatePanel(
        eyebrow: 'CREATOR ROLE',
        title: 'Sign in to open creator studio',
        message:
            'Studio, wallet, sponsored clip, audience, and moderation controls require an authenticated creator session.',
        icon: Icons.lock_outline,
        accentColor: GteShellTheme.accentCommunity,
        actionLabel: onOpenLogin == null ? null : 'Sign in',
        onAction: onOpenLogin,
      );
    }
    if (!hasApprovedCreatorAccess) {
      return GteStatePanel(
        eyebrow: 'CREATOR ROLE',
        title: 'Creator access required',
        message:
            'This account can read public creator context, but studio mutations stay locked until creator access is approved.',
        icon: Icons.verified_user_outlined,
        accentColor: GteShellTheme.accentCommunity,
        actionLabel:
            onOpenCreatorAccessRequest == null ? null : 'Request access',
        onAction: onOpenCreatorAccessRequest,
      );
    }

    final CreatorFinanceSummary? currentFinance = finance;
    final String syncLabel =
        isSyncing
            ? 'Syncing now'
            : 'Last sync ${gteFormatRelativeTime(syncedAt)}';

    return SingleChildScrollView(
      child: GteSurfacePanel(
        accentColor: GteShellTheme.accentCommunity,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'Creator canonical surface',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(
              'Role-aware studio, campaign, wallet, sponsored clip, audience, and moderation readiness for ${profile.displayName}.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: spacingSM),
            Wrap(
              spacing: spacingXS,
              runSpacing: spacingXS,
              children: <Widget>[
                _CanonicalPill(
                  icon: Icons.badge_outlined,
                  label: 'Role',
                  value: 'Approved creator',
                ),
                _CanonicalPill(
                  icon: Icons.verified_outlined,
                  label: 'Status',
                  value:
                      profile.status.trim().isEmpty
                          ? 'Backend status unavailable'
                          : profile.status,
                ),
                _CanonicalPill(
                  icon: Icons.sync_outlined,
                  label: 'Realtime',
                  value: syncLabel,
                ),
                _CanonicalPill(
                  icon: Icons.receipt_long_outlined,
                  label: 'Audit',
                  value: 'creator.surface.v1',
                ),
              ],
            ),
            const SizedBox(height: spacingMD),
            _CanonicalReadinessRow(
              title: 'Studio',
              state:
                  profile.shareCode.trim().isEmpty
                      ? 'Profile payload is present, but the backend share code field is empty.'
                      : 'Profile identity and share code are loaded from backend.',
              evidence:
                  profile.shareCode.trim().isEmpty
                      ? 'Share code is empty in the backend profile payload'
                      : 'Share code ${profile.shareCode}',
              icon: Icons.dashboard_customize_outlined,
            ),
            _CanonicalReadinessRow(
              title: 'Campaigns',
              state:
                  profile.competitions.isEmpty
                      ? 'BACKEND-BACKED EMPTY: the creator profile returned no campaigns.'
                      : '${profile.competitions.length} backend campaign${profile.competitions.length == 1 ? '' : 's'} loaded.',
              evidence:
                  profile.competitions.isEmpty
                      ? 'Campaign list is empty'
                      : profile.competitions
                          .map((CreatorCompetition item) => item.title)
                          .join(', '),
              icon: Icons.campaign_outlined,
            ),
            _CanonicalReadinessRow(
              title: 'Wallet',
              state:
                  currentFinance == null
                      ? 'Wallet values are hidden until finance payload syncs.'
                      : !currentFinance.hasCompleteBackendPayload
                      ? 'Finance payload is partial; wallet values stay marked as provisional.'
                      : currentFinance.hasWalletPayload
                      ? 'Wallet balances are sourced from finance payload.'
                      : 'Finance payload is present but wallet fields are not returned.',
              evidence:
                  currentFinance == null
                      ? 'No finance payload'
                      : currentFinance.hasWalletPayload
                      ? gteFormatCompetitionAmount(
                        currentFinance.walletAvailableBalance,
                        currentFinance.walletCurrency,
                      )
                      : 'Wallet payload missing',
              icon: Icons.account_balance_wallet_outlined,
            ),
            _CanonicalReadinessRow(
              title: 'Sponsored clips',
              state:
                  currentFinance == null
                      ? 'Sponsored clip earnings wait for finance sync.'
                      : currentFinance.hasClipEarningsPayload
                      ? 'Clip payout, view, and monetized clip fields are loaded.'
                      : 'Clip earnings endpoint has not returned sponsored clip fields.',
              evidence:
                  currentFinance == null
                      ? 'No clip payload'
                      : currentFinance.hasClipEarningsPayload
                      ? '${currentFinance.monetizedClips} monetized clips, ${currentFinance.totalClipViews} views'
                      : 'Clip metrics missing',
              icon: Icons.smart_display_outlined,
            ),
            _CanonicalReadinessRow(
              title: 'Settlements',
              state:
                  currentFinance == null
                      ? 'Settlement totals wait for finance sync.'
                      : !currentFinance.hasCompleteBackendPayload
                      ? 'Settlement totals stay degraded until backend finance payload is complete.'
                      : 'Withdrawal and settlement totals are sourced from finance payload.',
              evidence:
                  currentFinance == null
                      ? 'No settlement payload'
                      : 'Net withdrawn ${gteFormatCompetitionAmount(currentFinance.totalWithdrawnNet, currentFinance.currency)}, pending ${gteFormatCompetitionAmount(currentFinance.pendingWithdrawals, currentFinance.currency)}',
              icon: Icons.receipt_long_outlined,
            ),
            _CanonicalReadinessRow(
              title: 'Audience',
              state:
                  'Audience stats are backed by creator summary fields: '
                  '${profile.stats.communityInvites} community invite${profile.stats.communityInvites == 1 ? '' : 's'}, '
                  '${profile.stats.qualifiedReferrals} qualified referral${profile.stats.qualifiedReferrals == 1 ? '' : 's'}, '
                  '${profile.stats.contestParticipants} contest participant${profile.stats.contestParticipants == 1 ? '' : 's'}.',
              evidence:
                  'communityInvites=${profile.stats.communityInvites}, '
                  'qualifiedReferrals=${profile.stats.qualifiedReferrals}, '
                  'contestParticipants=${profile.stats.contestParticipants}',
              icon: Icons.groups_2_outlined,
            ),
            _CanonicalReadinessRow(
              title: 'Referrals',
              state:
                  currentFinance == null
                      ? 'Referral attribution is visible from creator stats, but finance attribution payload is still missing.'
                      : currentFinance.hasCompleteBackendPayload
                      ? 'Referral attribution is backed by creator and finance payload fields.'
                      : 'Referral attribution is partially loaded from finance payload and remains provisional.',
              evidence:
                  currentFinance == null
                      ? 'qualifiedReferrals=${profile.stats.qualifiedReferrals}; finance payload missing'
                      : 'qualifiedReferrals=${profile.stats.qualifiedReferrals}, attributedSignups=${currentFinance.attributedSignups}, qualifiedJoins=${currentFinance.qualifiedJoins}',
              icon: Icons.link_outlined,
            ),
            _CanonicalReadinessRow(
              title: 'Moderation',
              state:
                  currentFinance == null
                      ? 'Moderation and payout review context waits for finance sync.'
                      : currentFinance.pendingWithdrawals > 0
                      ? 'Payout review state is visible and auditable.'
                      : 'No pending payout review returned by backend.',
              evidence:
                  currentFinance == null
                      ? 'No moderation finance context'
                      : currentFinance.pendingWithdrawals > 0
                      ? 'Pending withdrawals ${gteFormatCompetitionAmount(currentFinance.pendingWithdrawals, currentFinance.currency)}'
                      : 'Pending withdrawals 0',
              icon: Icons.policy_outlined,
              isLast: true,
            ),
          ],
        ),
      ),
    );
  }
}

class _CanonicalPill extends StatelessWidget {
  const _CanonicalPill({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        color: GteShellTheme.accentCommunity.withValues(alpha: 0.1),
        border: Border.all(
          color: GteShellTheme.accentCommunity.withValues(alpha: 0.18),
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          Icon(icon, size: 16, color: GteShellTheme.accentCommunity),
          const SizedBox(width: 8),
          Text(
            '$label: ',
            style: Theme.of(
              context,
            ).textTheme.labelMedium?.copyWith(color: tokens.textMuted),
          ),
          Text(value, style: Theme.of(context).textTheme.labelMedium),
        ],
      ),
    );
  }
}

class _CanonicalReadinessRow extends StatelessWidget {
  const _CanonicalReadinessRow({
    required this.title,
    required this.state,
    required this.evidence,
    required this.icon,
    this.isLast = false,
  });

  final String title;
  final String state;
  final String evidence;
  final IconData icon;
  final bool isLast;

  @override
  Widget build(BuildContext context) {
    final tokens = GteShellTheme.tokensOf(context);
    return Container(
      padding: EdgeInsets.only(bottom: isLast ? 0 : spacingSM),
      margin: EdgeInsets.only(bottom: isLast ? 0 : spacingSM),
      decoration: BoxDecoration(
        border:
            isLast
                ? null
                : Border(
                  bottom: BorderSide(
                    color: tokens.stroke.withValues(alpha: 0.45),
                  ),
                ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Container(
            width: 34,
            height: 34,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(8),
              color: GteShellTheme.accentCommunity.withValues(alpha: 0.11),
            ),
            child: Icon(icon, size: 18, color: GteShellTheme.accentCommunity),
          ),
          const SizedBox(width: spacingSM),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(title, style: Theme.of(context).textTheme.titleSmall),
                const SizedBox(height: 4),
                Text(state, style: Theme.of(context).textTheme.bodyMedium),
                const SizedBox(height: 4),
                Text(
                  evidence,
                  style: Theme.of(
                    context,
                  ).textTheme.bodySmall?.copyWith(color: tokens.textMuted),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
