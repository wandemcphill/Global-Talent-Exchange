import 'package:flutter/material.dart';

import '../../../core/constants/app_spacing.dart';
import '../../../models/community_models.dart';
import '../../../widgets/gte_shell_theme.dart';
import '../../../widgets/gte_surface_panel.dart';

class CommunityCanonicalSurface extends StatelessWidget {
  const CommunityCanonicalSurface({
    super.key,
    required this.isAuthenticated,
    required this.hasLiveToken,
    required this.isLoading,
    required this.isMutating,
    required this.watchlist,
    required this.liveThreads,
    required this.privateThreads,
    this.digest,
    this.currentClubId,
    this.currentClubName,
    this.loadError,
  });

  final bool isAuthenticated;
  final bool hasLiveToken;
  final bool isLoading;
  final bool isMutating;
  final CommunityDigest? digest;
  final List<CommunityWatchlistItem> watchlist;
  final List<LiveThread> liveThreads;
  final List<PrivateMessageThread> privateThreads;
  final String? currentClubId;
  final String? currentClubName;
  final String? loadError;

  @override
  Widget build(BuildContext context) {
    final CommunityDigest? currentDigest = digest;
    final String roleLabel =
        isAuthenticated && hasLiveToken
            ? 'Authenticated member'
            : isAuthenticated
            ? 'Authenticated without live token'
            : 'Public reader';
    final String clubLabel =
        (currentClubName?.trim().isNotEmpty ?? false)
            ? currentClubName!.trim()
            : (currentClubId?.trim().isNotEmpty ?? false)
            ? currentClubId!.trim()
            : 'No fan hub context';

    return SingleChildScrollView(
      child: GteSurfacePanel(
        accentColor: GteShellTheme.accentCommunity,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(
              'Community canonical surface',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(
              'Discussions, chat, fan hubs, reports, reactions, and gifting scaffolds render only backend-backed state.',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            const SizedBox(height: spacingSM),
            Wrap(
              spacing: spacingXS,
              runSpacing: spacingXS,
              children: <Widget>[
                _CommunityPill(
                  icon: Icons.badge_outlined,
                  label: 'Role',
                  value: roleLabel,
                ),
                _CommunityPill(
                  icon: Icons.hub_outlined,
                  label: 'Fan hub',
                  value: clubLabel,
                ),
                _CommunityPill(
                  icon: Icons.sync_outlined,
                  label: 'Realtime',
                  value:
                      isLoading
                          ? 'Syncing backend payloads'
                          : isMutating
                          ? 'Mutation in flight'
                          : 'Backend sync idle',
                ),
                _CommunityPill(
                  icon: Icons.receipt_long_outlined,
                  label: 'Audit',
                  value: 'community.surface.v1',
                ),
              ],
            ),
            const SizedBox(height: spacingMD),
            _CommunityReadinessRow(
              title: 'Discussions',
              state:
                  isLoading && liveThreads.isEmpty
                      ? 'SYNCING: live discussion threads are still loading from backend.'
                      : liveThreads.isEmpty
                      ? 'BACKEND-BACKED EMPTY: no live discussion threads returned.'
                      : isLoading
                      ? 'SYNCING: ${liveThreads.length} live discussion thread${liveThreads.length == 1 ? '' : 's'} are attached while the refresh is in flight.'
                      : 'BACKEND-BACKED: ${liveThreads.length} live discussion thread${liveThreads.length == 1 ? '' : 's'} loaded.',
              evidence:
                  liveThreads.isEmpty
                      ? (isLoading
                          ? 'Awaiting community.live_threads'
                          : 'Thread list empty')
                      : liveThreads
                          .map((LiveThread item) => item.threadKey)
                          .join(', '),
              realtimeTopic: 'community.live_threads',
              icon: Icons.forum_outlined,
            ),
            _CommunityReadinessRow(
              title: 'Chat',
              state:
                  !hasLiveToken
                      ? 'BLOCKED: direct chat is locked until a live token is present.'
                      : isLoading && privateThreads.isEmpty
                      ? 'SYNCING: private message threads are still loading from backend.'
                      : privateThreads.isEmpty
                      ? 'BACKEND-BACKED EMPTY: no private message threads returned.'
                      : isLoading
                      ? 'SYNCING: ${privateThreads.length} direct thread${privateThreads.length == 1 ? '' : 's'} are attached while the refresh is in flight.'
                      : 'BACKEND-BACKED: ${privateThreads.length} direct thread${privateThreads.length == 1 ? '' : 's'} loaded.',
              evidence:
                  !hasLiveToken
                      ? 'Authenticated token missing'
                      : privateThreads.isEmpty
                      ? (isLoading
                          ? 'Awaiting community.private_messages'
                          : 'Private thread list empty')
                      : privateThreads
                          .map(
                            (PrivateMessageThread item) =>
                                item.subject.trim().isEmpty
                                    ? item.threadKey
                                    : item.subject,
                          )
                          .join(', '),
              realtimeTopic: 'community.private_messages',
              icon: Icons.chat_bubble_outline,
            ),
            _CommunityReadinessRow(
              title: 'Fan hubs',
              state:
                  (currentClubId?.trim().isNotEmpty ?? false)
                      ? isLoading
                          ? 'SYNCING: fan hub context is attached and watchlist counts are still loading.'
                          : currentDigest == null
                          ? 'BACKEND-BACKED: fan hub context is attached, but no digest payload was returned.'
                          : currentDigest.watchlistCount != watchlist.length
                          ? 'DEGRADED: digest reports ${currentDigest.watchlistCount} watchlist item${currentDigest.watchlistCount == 1 ? '' : 's'}, but the list payload returned ${watchlist.length}.'
                          : watchlist.isEmpty
                          ? 'BACKEND-BACKED EMPTY: fan hub context is attached and the watchlist is empty.'
                          : 'BACKEND-BACKED: fan hub context is attached with ${watchlist.length} watchlist item${watchlist.length == 1 ? '' : 's'}.'
                      : 'BLOCKED: no fan hub context was supplied to this surface.',
              evidence:
                  currentDigest == null
                      ? 'Digest payload missing'
                      : 'Digest watchlistCount=${currentDigest.watchlistCount}, watchlist length=${watchlist.length}',
              realtimeTopic: 'community.fan_hubs',
              icon: Icons.groups_2_outlined,
            ),
            _CommunityReadinessRow(
              title: 'Reports',
              state:
                  isLoading
                      ? 'SYNCING: report actions and counts are waiting on a moderation payload.'
                      : loadError == null
                      ? 'BLOCKED: report actions and counts are not wired to a community moderation payload.'
                      : 'DEGRADED: report actions and counts stay blocked until community sync recovers.',
              evidence:
                  loadError == null ? 'No report count payload' : loadError!,
              realtimeTopic: 'community.reports',
              icon: Icons.flag_outlined,
            ),
            _CommunityReadinessRow(
              title: 'Reactions',
              state:
                  isLoading
                      ? 'SYNCING: reaction aggregates are still loading.'
                      : currentDigest == null
                      ? 'BLOCKED: reaction actions and aggregates are not returned for public digest.'
                      : 'BLOCKED: digest is loaded, but no reaction aggregate payload is present.',
              evidence:
                  currentDigest == null
                      ? 'Digest unavailable'
                      : 'digest unreadHintCount=${currentDigest.unreadHintCount}; no reaction count payload',
              realtimeTopic: 'community.reactions',
              icon: Icons.add_reaction_outlined,
            ),
            _CommunityReadinessRow(
              title: 'Gifting',
              state:
                  hasLiveToken
                      ? 'BLOCKED: gift actions require backend gift ledger target and catalog payloads before settlement.'
                      : 'BLOCKED: gift actions are locked for public readers.',
              evidence: 'No gift ledger payload',
              realtimeTopic: 'community.gifting',
              icon: Icons.card_giftcard_outlined,
              isLast: true,
            ),
          ],
        ),
      ),
    );
  }
}

class _CommunityPill extends StatelessWidget {
  const _CommunityPill({
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

class _CommunityReadinessRow extends StatelessWidget {
  const _CommunityReadinessRow({
    required this.title,
    required this.state,
    required this.evidence,
    required this.realtimeTopic,
    required this.icon,
    this.isLast = false,
  });

  final String title;
  final String state;
  final String evidence;
  final String realtimeTopic;
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
                  '$evidence | $realtimeTopic',
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
