import 'package:flutter/material.dart';
import 'package:gte_frontend/ui_gtex/ui_gtex.dart';

import '../models/gtex_club_redesign_models.dart';
import '../widgets/gtex_club_workspace_widgets.dart';
import 'gtex_club_workspace_controller.dart';

class GtexPublicClubProfileV2 extends StatefulWidget {
  const GtexPublicClubProfileV2({
    super.key,
    required this.clubId,
    this.clubName,
    this.baseUrl,
    this.backendMode,
    this.accessToken,
    this.initialSnapshot,
    this.isAuthenticated = true,
    this.onOpenLogin,
  });

  final String clubId;
  final String? clubName;
  final String? baseUrl;
  final Object? backendMode;
  final String? accessToken;
  final GtexClubWorkspaceSnapshot? initialSnapshot;
  final bool isAuthenticated;
  final VoidCallback? onOpenLogin;

  @override
  State<GtexPublicClubProfileV2> createState() =>
      _GtexPublicClubProfileV2State();
}

class _GtexPublicClubProfileV2State extends State<GtexPublicClubProfileV2> {
  late final GtexClubWorkspaceController _controller;

  @override
  void initState() {
    super.initState();
    _controller = GtexClubWorkspaceController(
      clubId: widget.clubId,
      clubName: widget.clubName,
      initialSnapshot: widget.initialSnapshot,
    );
  }

  @override
  void didUpdateWidget(covariant GtexPublicClubProfileV2 oldWidget) {
    super.didUpdateWidget(oldWidget);
    final GtexClubWorkspaceSnapshot? snapshot = widget.initialSnapshot;
    if (snapshot != null && snapshot != oldWidget.initialSnapshot) {
      _controller.replaceSnapshot(snapshot);
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (BuildContext context, _) {
        final GtexClubWorkspaceSnapshot snapshot = _controller.snapshot;
        return GtexMasterDetailScaffold(
          title: 'Club profile',
          subtitle: '${snapshot.clubName} - public view',
          accent: GtexColors.pitch,
          mobileLeftTitle: 'Club profile sections',
          leftPanel: GtexClubSectionList<GtexPublicClubSection>(
            items: GtexPublicClubSection.values,
            selected: _controller.publicSection,
            labelBuilder: (GtexPublicClubSection section) => section.label,
            descriptionBuilder:
                (GtexPublicClubSection section) => section.description,
            onSelected: _controller.selectPublicSection,
          ),
          detail: _PublicDetail(
            snapshot: snapshot,
            section: _controller.publicSection,
            isFollowing: _controller.isFollowing,
            onFollow: _controller.toggleFollow,
            onBuyShares: _openBuyShares,
          ),
          rightPanel: GtexClubRightRail(
            snapshot: snapshot,
            ownerFacing: false,
            onBuyShares: _openBuyShares,
          ),
          actions: <Widget>[
            GtexActionButton(
              label: _controller.isFollowing ? 'Following' : 'Follow',
              icon:
                  _controller.isFollowing
                      ? Icons.notifications_active
                      : Icons.add_alert_outlined,
              onPressed: _controller.toggleFollow,
              accent: GtexColors.pitch,
            ),
            GtexActionButton(
              label: 'Buy shares',
              icon: Icons.ssid_chart_outlined,
              onPressed: _openBuyShares,
              accent: GtexColors.gold,
            ),
          ],
        );
      },
    );
  }

  void _openBuyShares() {
    if (!widget.isAuthenticated) {
      widget.onOpenLogin?.call();
      return;
    }
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: GtexColors.panel,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(
          top: Radius.circular(GtexSpacing.radiusLg),
        ),
      ),
      builder: (BuildContext context) {
        return AnimatedBuilder(
          animation: _controller,
          builder: (BuildContext context, _) {
            final GtexClubWorkspaceSnapshot snapshot = _controller.snapshot;
            return SafeArea(
              child: Padding(
                padding: const EdgeInsets.all(GtexSpacing.lg),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Buy ${snapshot.clubName} shares',
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        color: GtexColors.text,
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: GtexSpacing.sm),
                    Text(
                      'Share price: ${gtexFormatCredits(snapshot.finances.sharePriceCredits)} each',
                      style: const TextStyle(color: GtexColors.textMuted),
                    ),
                    const SizedBox(height: GtexSpacing.md),
                    Slider(
                      value: _controller.selectedShares.toDouble(),
                      min: 1,
                      max: 500,
                      divisions: 499,
                      label: '${_controller.selectedShares}',
                      onChanged:
                          (double value) =>
                              _controller.setSelectedShares(value.round()),
                    ),
                    const SizedBox(height: GtexSpacing.sm),
                    GtexPanel(
                      accent: GtexColors.gold,
                      child: Row(
                        children: <Widget>[
                          Expanded(
                            child: Text(
                              '${_controller.selectedShares} shares',
                              style: const TextStyle(
                                color: GtexColors.text,
                                fontWeight: FontWeight.w900,
                              ),
                            ),
                          ),
                          Text(
                            gtexFormatCredits(
                              _controller.selectedShareCostCredits,
                            ),
                            style: const TextStyle(
                              color: GtexColors.gold,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: GtexSpacing.md),
                    Row(
                      children: <Widget>[
                        Expanded(
                          child: OutlinedButton(
                            onPressed: () => Navigator.of(context).pop(),
                            child: const Text('Cancel'),
                          ),
                        ),
                        const SizedBox(width: GtexSpacing.sm),
                        Expanded(
                          child: FilledButton.icon(
                            onPressed: () => Navigator.of(context).pop(),
                            icon: const Icon(Icons.lock_outline),
                            label: const Text('Review purchase'),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }
}

class _PublicDetail extends StatelessWidget {
  const _PublicDetail({
    required this.snapshot,
    required this.section,
    required this.isFollowing,
    required this.onFollow,
    required this.onBuyShares,
  });

  final GtexClubWorkspaceSnapshot snapshot;
  final GtexPublicClubSection section;
  final bool isFollowing;
  final VoidCallback onFollow;
  final VoidCallback onBuyShares;

  @override
  Widget build(BuildContext context) {
    return ListView(
      children: <Widget>[
        if (section == GtexPublicClubSection.overview) ...<Widget>[
          GtexClubHero(
            snapshot: snapshot,
            ownerFacing: false,
            isFollowing: isFollowing,
            onFollow: onFollow,
            onBuyShares: onBuyShares,
          ),
          const SizedBox(height: GtexSpacing.md),
          _PublicStory(snapshot: snapshot),
        ] else if (section == GtexPublicClubSection.squad) ...<Widget>[
          _PublicHeader(
            title: 'Public squad',
            subtitle: 'Players this club wants the world to see.',
            icon: Icons.groups_2_outlined,
          ),
          const SizedBox(height: GtexSpacing.md),
          GtexClubSquadList(squad: snapshot.squad),
        ] else if (section == GtexPublicClubSection.trophies) ...<Widget>[
          _PublicHeader(
            title: 'Trophy cabinet',
            subtitle: 'Honors and competitive history.',
            icon: Icons.emoji_events_outlined,
          ),
          const SizedBox(height: GtexSpacing.md),
          GtexClubTrophyGrid(trophies: snapshot.trophies),
        ] else if (section == GtexPublicClubSection.news) ...<Widget>[
          _PublicHeader(
            title: 'News mentions',
            subtitle: 'AI newsroom stories about this club.',
            icon: Icons.newspaper_outlined,
          ),
          const SizedBox(height: GtexSpacing.md),
          GtexClubNewsList(news: snapshot.news),
        ] else if (section == GtexPublicClubSection.shares) ...<Widget>[
          _PublicHeader(
            title: 'Club shares',
            subtitle: 'Follow the club and buy shares from the public profile.',
            icon: Icons.ssid_chart_outlined,
          ),
          const SizedBox(height: GtexSpacing.md),
          GtexPanel(
            accent: GtexColors.gold,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  'Share price',
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: GtexColors.textMuted,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                Text(
                  gtexFormatCredits(snapshot.finances.sharePriceCredits),
                  style: Theme.of(context).textTheme.displaySmall?.copyWith(
                    color: GtexColors.gold,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: GtexSpacing.sm),
                Text(
                  '${snapshot.shareholders} shareholders - ${snapshot.followers} followers',
                  style: const TextStyle(color: GtexColors.textMuted),
                ),
                const SizedBox(height: GtexSpacing.md),
                GtexActionButton(
                  label: 'Buy shares',
                  icon: Icons.ssid_chart_outlined,
                  onPressed: onBuyShares,
                  accent: GtexColors.gold,
                ),
              ],
            ),
          ),
        ] else ...<Widget>[
          _PublicHeader(
            title: 'Community',
            subtitle:
                'Followers, fans, club updates, and conversation entry points.',
            icon: Icons.forum_outlined,
          ),
          const SizedBox(height: GtexSpacing.md),
          GtexPanel(
            accent: GtexColors.pitch,
            child: Text(
              '${snapshot.followers} users follow ${snapshot.clubName}. Community updates, club news, and share momentum are shown from the live club profile.',
              style: const TextStyle(color: GtexColors.textMuted),
            ),
          ),
        ],
      ],
    );
  }
}

class _PublicStory extends StatelessWidget {
  const _PublicStory({required this.snapshot});

  final GtexClubWorkspaceSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      title: 'Club story',
      subtitle: 'Public-facing identity, investment, and football reputation.',
      accent: GtexColors.pitch,
      child: Text(
        '${snapshot.clubName} is a user-created GTEX club competing in ${snapshot.division}. The public profile should sell the story: who owns the club, who follows it, who plays for it, what it has won, and why users should follow or buy shares.',
        style: Theme.of(context).textTheme.bodyMedium?.copyWith(
          color: GtexColors.textMuted,
          height: 1.5,
        ),
      ),
    );
  }
}

class _PublicHeader extends StatelessWidget {
  const _PublicHeader({
    required this.title,
    required this.subtitle,
    required this.icon,
  });

  final String title;
  final String subtitle;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return GtexPanel(
      accent: GtexColors.pitch,
      child: Row(
        children: <Widget>[
          Icon(icon, color: GtexColors.pitch, size: 32),
          const SizedBox(width: GtexSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  title,
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    color: GtexColors.text,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                Text(
                  subtitle,
                  style: Theme.of(
                    context,
                  ).textTheme.bodyMedium?.copyWith(color: GtexColors.textMuted),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
