import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/app_feedback.dart';
import '../../../ui_gtex/components/gtex_action_button.dart';
import '../../../ui_gtex/components/gtex_empty_state.dart';
import '../../../ui_gtex/components/gtex_status_chip.dart';
import '../../../ui_gtex/theme/gtex_colors.dart';
import '../../../ui_gtex/theme/gtex_spacing.dart';
import '../../../widgets/gte_shell_theme.dart';
import '../../../widgets/gte_state_panel.dart';
import '../../../widgets/gte_surface_panel.dart';
import '../../player_detail/gtex_player_navigator.dart';
import '../data/gtex_community_pulse_provider.dart';
import '../models/gtex_community_models.dart';

/// The football-first face of GTEX community.
///
/// This is a lane of the existing `/app/community` destination, not a second
/// community screen: it renders the same shell chrome, the same GTEX
/// primitives, and routes into the same canonical player, club and market
/// surfaces. Nothing here recomputes a value, a price or a form - every line
/// is a published number restated.
class GtexCommunityPulsePanel extends ConsumerWidget {
  const GtexCommunityPulsePanel({
    super.key,
    this.onOpenLogin,
    this.onOpenClub,
    this.onOpenMarket,
    this.onOpenRegens,
  });

  final VoidCallback? onOpenLogin;
  final VoidCallback? onOpenClub;
  final VoidCallback? onOpenMarket;
  final VoidCallback? onOpenRegens;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<GtexCommunityPulse> pulse = ref.watch(
      communityPulseProvider,
    );
    return pulse.when(
      loading: () => const GteStatePanel(
        title: 'Reading the football economy',
        message:
            'Collecting market movement, matchday form, club ownership and challenge activity.',
        icon: Icons.public_outlined,
        isLoading: true,
      ),
      error: (Object error, StackTrace _) => GteStatePanel(
        title: 'Community unavailable',
        message: AppFeedback.messageFor(error),
        icon: Icons.error_outline,
        actionLabel: 'Retry',
        onAction: () => ref.invalidate(communityPulseProvider),
      ),
      data: (GtexCommunityPulse data) => _PulseBody(
        pulse: data,
        onOpenLogin: onOpenLogin,
        onOpenClub: onOpenClub,
        onOpenMarket: onOpenMarket,
        onOpenRegens: onOpenRegens,
        onRefresh: () => ref.invalidate(communityPulseProvider),
      ),
    );
  }
}

class _PulseBody extends StatelessWidget {
  const _PulseBody({
    required this.pulse,
    required this.onRefresh,
    this.onOpenLogin,
    this.onOpenClub,
    this.onOpenMarket,
    this.onOpenRegens,
  });

  final GtexCommunityPulse pulse;
  final VoidCallback onRefresh;
  final VoidCallback? onOpenLogin;
  final VoidCallback? onOpenClub;
  final VoidCallback? onOpenMarket;
  final VoidCallback? onOpenRegens;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        GteSurfacePanel(
          accentColor: GteShellTheme.accentCommunity,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              Text(
                'Football world',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 6),
              Text(
                pulse.headline,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
              if (!pulse.isAuthenticated && onOpenLogin != null) ...<Widget>[
                const SizedBox(height: GtexSpacing.sm),
                GtexActionButton(
                  label: 'Sign in',
                  icon: Icons.login_outlined,
                  onPressed: onOpenLogin,
                  accent: GtexColors.mint,
                ),
              ],
            ],
          ),
        ),
        const SizedBox(height: GtexSpacing.md),
        if (pulse.warnings.isNotEmpty) ...<Widget>[
          GteStatePanel(
            eyebrow: 'PARTIAL SYNC',
            title: 'Some community sources did not answer',
            message: pulse.warnings.join('\n'),
            icon: Icons.sync_problem_outlined,
            actionLabel: 'Retry',
            onAction: onRefresh,
          ),
          const SizedBox(height: GtexSpacing.md),
        ],
        if (pulse.isAuthenticated) ...<Widget>[
          _SignalSection(
            title: 'Your community',
            subtitle:
                'Football activity on the players, clubs and regens you own or follow.',
            emptyTitle: 'Nothing has happened around your football yet',
            emptyMessage:
                'When a player you own moves, a club you hold shares in plays, or a '
                'challenge is issued, it shows up here. GTEX does not fill this space '
                'with invented activity.',
            signals: pulse.yourSignals,
            pulse: pulse,
            onOpenClub: onOpenClub,
            onOpenMarket: onOpenMarket,
            onOpenRegens: onOpenRegens,
          ),
          const SizedBox(height: GtexSpacing.md),
        ],
        _SignalSection(
          title: 'Live GTEX activity',
          subtitle:
              'Real player market movement across the whole GTEX economy, last 24 hours.',
          emptyTitle: 'The market has not moved today',
          emptyMessage:
              'No player price has changed in the last 24 hours. This space stays '
              'empty rather than showing placeholder activity.',
          signals: pulse.worldSignals,
          pulse: pulse,
          onOpenClub: onOpenClub,
          onOpenMarket: onOpenMarket,
          onOpenRegens: onOpenRegens,
        ),
      ],
    );
  }
}

class _SignalSection extends StatelessWidget {
  const _SignalSection({
    required this.title,
    required this.subtitle,
    required this.emptyTitle,
    required this.emptyMessage,
    required this.signals,
    required this.pulse,
    this.onOpenClub,
    this.onOpenMarket,
    this.onOpenRegens,
  });

  final String title;
  final String subtitle;
  final String emptyTitle;
  final String emptyMessage;
  final List<GtexCommunitySignal> signals;
  final GtexCommunityPulse pulse;
  final VoidCallback? onOpenClub;
  final VoidCallback? onOpenMarket;
  final VoidCallback? onOpenRegens;

  @override
  Widget build(BuildContext context) {
    return GteSurfacePanel(
      accentColor: GteShellTheme.accentCommunity,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(title, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 6),
          Text(subtitle, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: GtexSpacing.md),
          if (signals.isEmpty)
            GtexEmptyState(
              title: emptyTitle,
              message: emptyMessage,
              icon: Icons.sports_soccer_outlined,
              accent: GtexColors.mint,
            )
          else
            ...signals.map(
              (GtexCommunitySignal signal) => Padding(
                padding: const EdgeInsets.only(bottom: GtexSpacing.sm),
                child: GtexCommunitySignalCard(
                  signal: signal,
                  isFollowing: pulse.follows(signal.followTarget),
                  canFollow: pulse.isAuthenticated,
                  onOpenClub: onOpenClub,
                  onOpenMarket: onOpenMarket,
                  onOpenRegens: onOpenRegens,
                ),
              ),
            ),
        ],
      ),
    );
  }
}

/// One community signal.
///
/// The card degrades by available width rather than by a breakpoint list: at
/// narrow widths the action controls wrap under the copy instead of squeezing
/// it, so the same card is readable at 390 and at 1920.
class GtexCommunitySignalCard extends ConsumerWidget {
  const GtexCommunitySignalCard({
    super.key,
    required this.signal,
    required this.isFollowing,
    required this.canFollow,
    this.onOpenClub,
    this.onOpenMarket,
    this.onOpenRegens,
  });

  final GtexCommunitySignal signal;
  final bool isFollowing;
  final bool canFollow;
  final VoidCallback? onOpenClub;
  final VoidCallback? onOpenMarket;
  final VoidCallback? onOpenRegens;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final VoidCallback? open = _openAction(context);
    final GtexCommunityFollowTarget? followTarget = signal.followTarget;
    final Set<String> busy = ref.watch(communityFollowControllerProvider);
    final bool isBusy =
        followTarget != null && busy.contains(followTarget.key);

    final List<Widget> actions = <Widget>[
      if (open != null)
        GtexActionButton(
          label: _openLabel,
          icon: Icons.open_in_new_rounded,
          onPressed: open,
          accent: GtexColors.mint,
          secondary: true,
        ),
      if (canFollow && followTarget != null)
        GtexActionButton(
          label: isFollowing ? 'Following' : 'Follow',
          icon: isFollowing
              ? Icons.notifications_active_outlined
              : Icons.add_alert_outlined,
          onPressed: isBusy
              ? null
              : () => _toggleFollow(context, ref, followTarget),
          accent: GtexColors.mint,
          secondary: !isFollowing,
        ),
    ];

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: GteShellTheme.accentCommunity.withValues(alpha: 0.18),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            signal.headline,
            style: Theme.of(context).textTheme.titleSmall,
          ),
          const SizedBox(height: 4),
          Text(signal.detail, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: GtexSpacing.xs),
          Wrap(
            spacing: GtexSpacing.xs,
            runSpacing: GtexSpacing.xs,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: <Widget>[
              GtexStatusChip(
                label: _objectLabel,
                color: GtexColors.mint,
                compact: true,
              ),
              // Only rendered when the backend published a real count: an
              // unknown count is absent, never "0 owners".
              if (signal.socialProof != null)
                GtexStatusChip(
                  label: signal.socialProof!,
                  icon: Icons.groups_outlined,
                  color: GtexColors.accentBlue,
                  compact: true,
                ),
              ...actions,
            ],
          ),
        ],
      ),
    );
  }

  Future<void> _toggleFollow(
    BuildContext context,
    WidgetRef ref,
    GtexCommunityFollowTarget target,
  ) async {
    final bool wasFollowing = isFollowing;
    try {
      final bool accepted = await ref
          .read(communityFollowControllerProvider.notifier)
          .toggle(target: target, currentlyFollowing: wasFollowing);
      if (!accepted || !context.mounted) {
        return;
      }
      AppFeedback.showSuccess(
        context,
        wasFollowing ? 'Unfollowed.' : 'Following. New activity lands here.',
      );
    } catch (error) {
      if (!context.mounted) {
        return;
      }
      AppFeedback.showError(context, AppFeedback.messageFor(error));
    }
  }

  String get _objectLabel {
    switch (signal.object) {
      case GtexCommunityObject.player:
        return 'Player';
      case GtexCommunityObject.club:
        return 'Club';
      case GtexCommunityObject.challenge:
        return 'Challenge';
      case GtexCommunityObject.market:
        return 'Market';
    }
  }

  String get _openLabel {
    switch (signal.action) {
      case GtexCommunityAction.openPlayer:
        return 'Open player';
      case GtexCommunityAction.openClub:
        return 'Open club';
      case GtexCommunityAction.openMarket:
        return 'Open market';
      case GtexCommunityAction.openRegens:
        return 'Open Regen World';
      case GtexCommunityAction.none:
        return 'Open';
    }
  }

  /// Resolves the signal's action to a real destination, or `null` when this
  /// surface cannot route there. A control is never rendered dead.
  VoidCallback? _openAction(BuildContext context) {
    switch (signal.action) {
      case GtexCommunityAction.openPlayer:
        return GtexPlayerNavigator.tapToOpen(context, signal.playerId);
      case GtexCommunityAction.openClub:
        return onOpenClub;
      case GtexCommunityAction.openMarket:
        return onOpenMarket;
      case GtexCommunityAction.openRegens:
        return onOpenRegens;
      case GtexCommunityAction.none:
        return null;
    }
  }
}
