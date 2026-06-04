import 'package:flutter/material.dart';

import '../../controllers/creator_controller.dart';
import '../../features/creator/presentation/creator_canonical_surface.dart';
import '../../models/creator_models.dart';
import '../../widgets/gte_formatters.dart';
import '../../widgets/gte_shell_theme.dart';
import '../../widgets/gte_state_panel.dart';
import '../../widgets/gte_surface_panel.dart';

class CreatorDashboardScreen extends StatefulWidget {
  const CreatorDashboardScreen({
    super.key,
    required this.controller,
    this.isAuthenticated = true,
    this.hasApprovedCreatorAccess = true,
    this.onOpenLogin,
    this.onOpenCreatorAccessRequest,
  });

  final CreatorController controller;
  final bool isAuthenticated;
  final bool hasApprovedCreatorAccess;
  final VoidCallback? onOpenLogin;
  final VoidCallback? onOpenCreatorAccessRequest;

  @override
  State<CreatorDashboardScreen> createState() => _CreatorDashboardScreenState();
}

class _CreatorDashboardScreenState extends State<CreatorDashboardScreen> {
  @override
  void initState() {
    super.initState();
    widget.controller.attachStateSync();
    widget.controller.load();
  }

  @override
  void dispose() {
    widget.controller.detachStateSync();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: widget.controller,
      builder: (BuildContext context, Widget? child) {
        final CreatorProfile? profile = widget.controller.profile;
        final CreatorFinanceSummary? finance =
            widget.controller.financeSummary ?? profile?.financeSummary;
        if (profile == null && widget.controller.isLoading) {
          return const Center(child: CircularProgressIndicator());
        }
        if (profile == null) {
          return Padding(
            padding: const EdgeInsets.all(20),
            child: GteStatePanel(
              title: 'Creator dashboard unavailable',
              message:
                  widget.controller.errorMessage ??
                  'Creator data is still syncing.',
              actionLabel: 'Retry',
              onAction: () => widget.controller.load(force: true),
              icon: Icons.auto_graph_outlined,
              accentColor: GteShellTheme.accentCommunity,
            ),
          );
        }
        if (!widget.isAuthenticated || !widget.hasApprovedCreatorAccess) {
          return Padding(
            padding: const EdgeInsets.all(20),
            child: CreatorCanonicalSurface(
              profile: profile,
              finance: finance,
              isAuthenticated: widget.isAuthenticated,
              hasApprovedCreatorAccess: widget.hasApprovedCreatorAccess,
              syncedAt: widget.controller.syncedAt,
              isSyncing: widget.controller.isSyncing,
              onOpenLogin: widget.onOpenLogin,
              onOpenCreatorAccessRequest: widget.onOpenCreatorAccessRequest,
            ),
          );
        }
        return ListView(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 120),
          children: <Widget>[
            GteSurfacePanel(
              emphasized: true,
              accentColor: GteShellTheme.accentCommunity,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    profile.displayName,
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 8),
                  Text(profile.headline),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 12,
                    runSpacing: 12,
                    children: <Widget>[
                      Chip(label: Text(profile.handleLabel)),
                      Chip(
                        label: Text(
                          profile.tier.trim().isEmpty
                              ? 'Tier: awaiting backend'
                              : 'Tier: ${profile.tier}',
                        ),
                      ),
                      Chip(
                        label: Text(
                          profile.shareCode.trim().isEmpty
                              ? 'Share code: awaiting backend'
                              : 'Share code: ${profile.shareCode}',
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
            CreatorCanonicalSurface(
              profile: profile,
              finance: finance,
              isAuthenticated: widget.isAuthenticated,
              hasApprovedCreatorAccess: widget.hasApprovedCreatorAccess,
              syncedAt: widget.controller.syncedAt,
              isSyncing: widget.controller.isSyncing,
              onOpenLogin: widget.onOpenLogin,
              onOpenCreatorAccessRequest: widget.onOpenCreatorAccessRequest,
            ),
            const SizedBox(height: 18),
            GteSurfacePanel(
              accentColor: GteShellTheme.accentCommunity,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text('Growth', style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 8),
                  Text(profile.growthSummary.growthDetail),
                  const SizedBox(height: 12),
                  Text(profile.growthSummary.weeklyInviteLift),
                  Text(profile.growthSummary.inviteAttributionRate),
                ],
              ),
            ),
            if (finance != null) ...<Widget>[
              const SizedBox(height: 18),
              GteSurfacePanel(
                accentColor: GteShellTheme.accentCapital,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      'Finance',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'Wallet available: ${gteFormatCompetitionAmount(finance.walletAvailableBalance, finance.walletCurrency)}',
                    ),
                    Text(
                      'Gift income: ${gteFormatCompetitionAmount(finance.totalGiftIncome, finance.currency)}',
                    ),
                    Text(
                      'Reward income: ${gteFormatCompetitionAmount(finance.totalRewardIncome, finance.currency)}',
                    ),
                  ],
                ),
              ),
            ],
          ],
        );
      },
    );
  }
}
