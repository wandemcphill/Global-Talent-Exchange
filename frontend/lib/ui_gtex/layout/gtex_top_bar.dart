import 'package:flutter/material.dart';
import 'package:gte_frontend/features/navigation/model/gtex_shell_navigation_model.dart';

import '../components/gtex_money.dart';
import '../theme/gtex_colors.dart';
import '../theme/gtex_spacing.dart';
import '../theme/gtex_typography.dart';

/// Canonical GTEX Navy Top Bar (Master Plan Document E1, F8 & G1).
///
/// Renders:
/// - Left: Workspace Switcher (when the user holds >1 workspace role, Decision O-05)
///   and/or Active Club Switcher (when the user owns clubs).
/// - Right (max 4 actions on phone `<720 dp`):
///   1. Global Search (`onOpenSearch`)
///   2. Inbox / Attention Bell with numeric-only badge (`attentionCount`, `onOpenAttention`)
///   3. Wallet Balance Chip (`GtexMoney`, tap -> Wallet; shown on medium/expanded or when space permits)
///   4. Profile / Avatar (`onOpenProfile` or Sign-in CTA for guests).
class GtexTopBar extends StatelessWidget {
  const GtexTopBar({
    super.key,
    required this.title,
    this.subtitle,
    this.availableWorkspaces = const <GtexWorkspaceKind>[],
    this.activeWorkspace,
    this.onWorkspaceSelected,
    this.ownedClubs = const <GtexOwnedClubOption>[],
    this.activeClubId,
    this.activeClubName,
    this.onClubSelected,
    this.attentionCount = 0,
    this.onOpenAttention,
    this.onOpenSearch,
    this.walletBalanceGtc,
    this.onOpenWallet,
    this.onOpenProfile,
    this.isAuthenticated = false,
    this.userInitials,
    this.extraActions = const <Widget>[],
  });

  final String title;
  final String? subtitle;
  final List<GtexWorkspaceKind> availableWorkspaces;
  final GtexWorkspaceKind? activeWorkspace;
  final ValueChanged<GtexWorkspaceKind>? onWorkspaceSelected;
  final List<GtexOwnedClubOption> ownedClubs;
  final String? activeClubId;
  final String? activeClubName;
  final ValueChanged<GtexOwnedClubOption>? onClubSelected;
  final int attentionCount;
  final VoidCallback? onOpenAttention;
  final VoidCallback? onOpenSearch;
  final num? walletBalanceGtc;
  final VoidCallback? onOpenWallet;
  final VoidCallback? onOpenProfile;
  final bool isAuthenticated;
  final String? userInitials;
  final List<Widget> extraActions;

  bool get _showWorkspaceSwitcher =>
      availableWorkspaces.length > 1 && onWorkspaceSelected != null;

  bool get _showClubSwitcher =>
      ownedClubs.isNotEmpty && onClubSelected != null;

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens navy = GtexColors.navy;
    final bool compact = GtexBreakpoints.isCompact(context);

    return Container(
      key: const Key('gtex-top-bar'),
      height: compact ? 64 : 72,
      padding: EdgeInsets.symmetric(
        horizontal: compact ? GtexSpacing.marginPhone : GtexSpacing.marginTablet,
      ),
      decoration: BoxDecoration(
        color: navy.bgBase,
        border: Border(bottom: BorderSide(color: navy.lineSubtle)),
      ),
      child: LayoutBuilder(
        builder: (BuildContext context, BoxConstraints constraints) {
          final List<Widget> rightActions = _buildRightActions(
            context,
            navy,
            compact: compact,
          );
          final double maxRightWidth =
              constraints.maxWidth * (compact ? 0.44 : 0.56);

          return Row(
            children: <Widget>[
              if (!compact) ...<Widget>[
                _buildBrandCrest(navy),
                const SizedBox(width: GtexSpacing.sm),
              ],
              Expanded(
                child: SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: <Widget>[
                      if (_showWorkspaceSwitcher) ...<Widget>[
                        _WorkspaceSwitcherButton(
                          availableWorkspaces: availableWorkspaces,
                          activeWorkspace:
                              activeWorkspace ?? availableWorkspaces.first,
                          onSelected: onWorkspaceSelected!,
                          compact: compact,
                        ),
                        const SizedBox(width: GtexSpacing.xs),
                      ],
                      if (_showClubSwitcher) ...<Widget>[
                        _ClubSwitcherButton(
                          clubs: ownedClubs,
                          activeClubId: activeClubId,
                          activeClubName: activeClubName,
                          onSelected: onClubSelected!,
                          compact: compact,
                        ),
                        const SizedBox(width: GtexSpacing.xs),
                      ],
                      if (!compact ||
                          (!_showWorkspaceSwitcher && !_showClubSwitcher))
                        Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: <Widget>[
                            Text(
                              title,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: GtexTypography.titleM(
                                color: navy.textPrimary,
                              ),
                            ),
                            if (!compact &&
                                (subtitle ?? '').trim().isNotEmpty)
                              Text(
                                subtitle!.trim(),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: GtexTypography.bodyS(
                                  color: navy.textSecondary,
                                ),
                              ),
                          ],
                        ),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: GtexSpacing.xxs),
              ConstrainedBox(
                constraints: BoxConstraints(maxWidth: maxRightWidth),
                child: SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  reverse: true,
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: rightActions,
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildBrandCrest(GtexColorTokens navy) {
    return Container(
      width: 38,
      height: 38,
      decoration: BoxDecoration(
        color: navy.bgRaised,
        borderRadius: BorderRadius.circular(GtexRadius.card),
        border: Border.all(color: navy.gold700),
      ),
      alignment: Alignment.center,
      child: Text(
        'G',
        style: GtexTypography.titleL(color: navy.gold500),
      ),
    );
  }

  List<Widget> _buildRightActions(
    BuildContext context,
    GtexColorTokens navy, {
    required bool compact,
  }) {
    final List<Widget> items = <Widget>[];

    if (onOpenSearch != null) {
      items.add(
        IconButton(
          key: const Key('gtex-top-bar-search-button'),
          tooltip: 'Search GTEX',
          onPressed: onOpenSearch,
          icon: Icon(Icons.search_rounded, color: navy.textPrimary),
        ),
      );
    }

    if (onOpenAttention != null) {
      items.add(
        _AttentionBellButton(
          attentionCount: attentionCount,
          onPressed: onOpenAttention!,
        ),
      );
    }

    if (walletBalanceGtc != null && onOpenWallet != null) {
      items.add(
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: GtexSpacing.xxs),
          child: InkWell(
            key: const Key('gtex-top-bar-wallet-chip'),
            borderRadius: BorderRadius.circular(GtexRadius.pill),
            onTap: onOpenWallet,
            child: Container(
              height: 36,
              padding: const EdgeInsets.symmetric(horizontal: GtexSpacing.sm),
              decoration: BoxDecoration(
                color: navy.bgRaised,
                borderRadius: BorderRadius.circular(GtexRadius.pill),
                border: Border.all(color: navy.lineSubtle),
              ),
              alignment: Alignment.center,
              child: GtexMoney(
                amount: walletBalanceGtc!,
                unit: GtexCurrencyUnit.gtc,
                size: GtexMoneySize.small,
              ),
            ),
          ),
        ),
      );
    }

    if (onOpenProfile != null) {
      items.add(
        IconButton(
          key: const Key('gtex-top-bar-profile-button'),
          tooltip: isAuthenticated ? 'Profile and settings' : 'Sign in',
          onPressed: onOpenProfile,
          icon:
              isAuthenticated && (userInitials ?? '').trim().isNotEmpty
                  ? CircleAvatar(
                    radius: 14,
                    backgroundColor: navy.bgOverlay,
                    child: Text(
                      userInitials!.trim().toUpperCase(),
                      style: GtexTypography.label(color: navy.gold300),
                    ),
                  )
                  : Icon(
                    isAuthenticated
                        ? Icons.account_circle_outlined
                        : Icons.login_rounded,
                    color: navy.textPrimary,
                  ),
        ),
      );
    }

    if (!compact && extraActions.isNotEmpty) {
      items.addAll(extraActions);
    }

    // Master Plan Document E1: Max 4 actions on phone (<720 dp).
    if (compact && items.length > 4) {
      return items.take(4).toList(growable: false);
    }
    return items;
  }
}

class _WorkspaceSwitcherButton extends StatelessWidget {
  const _WorkspaceSwitcherButton({
    required this.availableWorkspaces,
    required this.activeWorkspace,
    required this.onSelected,
    required this.compact,
  });

  final List<GtexWorkspaceKind> availableWorkspaces;
  final GtexWorkspaceKind activeWorkspace;
  final ValueChanged<GtexWorkspaceKind> onSelected;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens navy = GtexColors.navy;
    return PopupMenuButton<GtexWorkspaceKind>(
      key: const Key('gtex-workspace-switcher-button'),
      tooltip: 'Switch workspace',
      color: navy.bgOverlay,
      onSelected: onSelected,
      itemBuilder: (BuildContext context) {
        return availableWorkspaces
            .map(
              (GtexWorkspaceKind workspace) =>
                  PopupMenuItem<GtexWorkspaceKind>(
                    key: Key('gtex-workspace-option-${workspace.name}'),
                    value: workspace,
                    child: Row(
                      children: <Widget>[
                        Icon(
                          workspace.icon,
                          size: 18,
                          color:
                              workspace == activeWorkspace
                                  ? navy.gold500
                                  : navy.textSecondary,
                        ),
                        const SizedBox(width: GtexSpacing.xs),
                        Expanded(
                          child: Text(
                            workspace.switcherTitle,
                            style: GtexTypography.body(
                              color:
                                  workspace == activeWorkspace
                                      ? navy.gold500
                                      : navy.textPrimary,
                            ),
                          ),
                        ),
                        if (workspace == activeWorkspace)
                          Icon(
                            Icons.check_rounded,
                            size: 16,
                            color: navy.gold500,
                          ),
                      ],
                    ),
                  ),
            )
            .toList(growable: false);
      },
      child: Container(
        height: 38,
        padding: EdgeInsets.symmetric(
          horizontal: compact ? GtexSpacing.xs : GtexSpacing.sm,
        ),
        decoration: BoxDecoration(
          color: navy.bgRaised,
          borderRadius: BorderRadius.circular(GtexRadius.chip),
          border: Border.all(color: navy.lineStrong),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Icon(activeWorkspace.icon, size: 16, color: navy.gold500),
            const SizedBox(width: 6),
            Text(
              activeWorkspace.label,
              style: GtexTypography.label(color: navy.textPrimary),
            ),
            const SizedBox(width: 4),
            Icon(
              Icons.keyboard_arrow_down_rounded,
              size: 16,
              color: navy.textSecondary,
            ),
          ],
        ),
      ),
    );
  }
}

class _ClubSwitcherButton extends StatelessWidget {
  const _ClubSwitcherButton({
    required this.clubs,
    required this.activeClubId,
    required this.activeClubName,
    required this.onSelected,
    required this.compact,
  });

  final List<GtexOwnedClubOption> clubs;
  final String? activeClubId;
  final String? activeClubName;
  final ValueChanged<GtexOwnedClubOption> onSelected;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens navy = GtexColors.navy;
    final GtexOwnedClubOption resolvedActive = clubs.firstWhere(
      (GtexOwnedClubOption club) => club.id == activeClubId,
      orElse: () => clubs.first,
    );
    final String displayLabel =
        (activeClubName ?? '').trim().isNotEmpty
            ? activeClubName!.trim()
            : resolvedActive.name;

    return PopupMenuButton<GtexOwnedClubOption>(
      key: const Key('gtex-club-switcher-button'),
      tooltip: 'Switch active club',
      color: navy.bgOverlay,
      onSelected: onSelected,
      itemBuilder: (BuildContext context) {
        return clubs
            .map(
              (GtexOwnedClubOption club) =>
                  PopupMenuItem<GtexOwnedClubOption>(
                    key: Key('gtex-club-option-${club.id}'),
                    value: club,
                    child: Row(
                      children: <Widget>[
                        Icon(
                          Icons.shield_outlined,
                          size: 18,
                          color:
                              club.id == resolvedActive.id
                                  ? navy.gold500
                                  : navy.textSecondary,
                        ),
                        const SizedBox(width: GtexSpacing.xs),
                        Expanded(
                          child: Text(
                            club.name,
                            style: GtexTypography.body(
                              color:
                                  club.id == resolvedActive.id
                                      ? navy.gold500
                                      : navy.textPrimary,
                            ),
                          ),
                        ),
                        if (club.id == resolvedActive.id)
                          Icon(
                            Icons.check_rounded,
                            size: 16,
                            color: navy.gold500,
                          ),
                      ],
                    ),
                  ),
            )
            .toList(growable: false);
      },
      child: Container(
        height: 38,
        constraints: BoxConstraints(maxWidth: compact ? 132 : 200),
        padding: EdgeInsets.symmetric(
          horizontal: compact ? GtexSpacing.xs : GtexSpacing.sm,
        ),
        decoration: BoxDecoration(
          color: navy.bgRaised,
          borderRadius: BorderRadius.circular(GtexRadius.chip),
          border: Border.all(color: navy.lineSubtle),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Icon(Icons.shield_rounded, size: 15, color: navy.gold500),
            const SizedBox(width: 6),
            Flexible(
              child: Text(
                displayLabel,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: GtexTypography.titleS(color: navy.textPrimary),
              ),
            ),
            const SizedBox(width: 4),
            Icon(
              Icons.keyboard_arrow_down_rounded,
              size: 16,
              color: navy.textSecondary,
            ),
          ],
        ),
      ),
    );
  }
}

class _AttentionBellButton extends StatelessWidget {
  const _AttentionBellButton({
    required this.attentionCount,
    required this.onPressed,
  });

  final int attentionCount;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    final GtexColorTokens navy = GtexColors.navy;
    final bool hasBadge = attentionCount > 0;
    final String badgeText =
        attentionCount > 99 ? '99+' : attentionCount.toString();

    return Semantics(
      button: true,
      label:
          hasBadge
              ? 'Inbox and attention, $attentionCount unread'
              : 'Inbox and attention',
      child: IconButton(
        key: const Key('gtex-top-bar-attention-bell'),
        tooltip: 'Inbox & Notifications',
        onPressed: onPressed,
        icon: Stack(
          clipBehavior: Clip.none,
          children: <Widget>[
            Icon(
              hasBadge
                  ? Icons.notifications_active_outlined
                  : Icons.notifications_none_rounded,
              color: hasBadge ? navy.gold500 : navy.textPrimary,
            ),
            if (hasBadge)
              Positioned(
                right: -6,
                top: -5,
                child: Container(
                  key: const Key('gtex-top-bar-attention-badge'),
                  padding: const EdgeInsets.symmetric(
                    horizontal: 5,
                    vertical: 1,
                  ),
                  decoration: BoxDecoration(
                    color: navy.gold500,
                    borderRadius: BorderRadius.circular(GtexRadius.pill),
                  ),
                  child: Text(
                    badgeText,
                    style: GtexTypography.numericS(color: navy.bgBase),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

/// Lightweight ownership option for top bar and workspace club switchers.
class GtexOwnedClubOption {
  const GtexOwnedClubOption({
    required this.id,
    required this.name,
    this.slug,
  });

  final String id;
  final String name;
  final String? slug;

  factory GtexOwnedClubOption.fromJson(Object? value) {
    final Map<String, Object?> root =
        value is Map<String, Object?>
            ? value
            : value is Map
            ? Map<String, Object?>.from(value)
            : const <String, Object?>{};
    final Object? profileRaw = root['profile'] ?? root;
    final Map<String, Object?> profile =
        profileRaw is Map
            ? Map<String, Object?>.from(profileRaw)
            : const <String, Object?>{};
    final String id =
        (profile['id'] ?? profile['club_id'] ?? profile['clubId'] ?? '')
            .toString()
            .trim();
    final String name =
        (profile['club_name'] ??
                profile['clubName'] ??
                profile['name'] ??
                id)
            .toString()
            .trim();
    final String? slug =
        (profile['slug'] ?? profile['club_slug'] ?? profile['clubSlug'])
            ?.toString()
            .trim();
    return GtexOwnedClubOption(
      id: id,
      name: name.isEmpty ? id : name,
      slug: (slug == null || slug.isEmpty) ? null : slug,
    );
  }
}
